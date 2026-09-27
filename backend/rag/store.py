"""Persistent vector store backed by SQLite + the sqlite-vec extension.

Each chunk's text lives in an ordinary ``chunks`` table; its embedding lives
in a ``vec0`` virtual table that shares the same ``chunk_id``. Vectors are
partitioned by ``course_id`` so a similarity search only ever ranks chunks
from the course being queried — one class never sees another's material.
"""

import re
import sqlite3
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec

# Embedding dimensions for all-MiniLM-L6-v2.
DEFAULT_DIM = 384

# Reciprocal Rank Fusion constant; 60 is the value from the original RRF paper
# and damps the influence of any single list's top ranks.
RRF_K = 60

# Question words and fillers that carry no topic signal. Dropping them keeps
# BM25 from rewarding chunks just for containing "what" or "the".
STOPWORDS = frozenset(
    """
    a about an and are as at be been by can do does did for from has have how i if in
    into is it its more most much of on or so than that the their them then there these
    they this those to up was we were what when where which who whom why will with you
    your
    """.split()  # noqa: SIM905
)


@dataclass(frozen=True)
class SearchHit:
    """One retrieved chunk and how close it was to the query."""

    chunk_id: int
    document_id: str
    text: str
    distance: float


def _serialize(vector: Sequence[float]) -> bytes:
    """Pack a float vector into the little-endian bytes sqlite-vec expects."""
    return struct.pack(f"{len(vector)}f", *vector)


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with sqlite-vec loaded and foreign keys on.

    This is the single place the vector extension is loaded, so any other
    layer (e.g. the relational database) can share the very same connection.
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the single shared connection is reached from
    # FastAPI's worker threads. SQLite serialises access internally; the app's
    # write load (one class) is light enough that this is safe.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("pragma foreign_keys = ON")
    return conn


class VectorStore:
    """Stores chunk text and embeddings, scoped per course, in one SQLite file.

    Pass ``connection`` to share an existing connection (it must already have
    sqlite-vec loaded — use :func:`connect`); in that case the caller owns the
    connection and is responsible for closing it. Otherwise a connection is
    opened for ``db_path`` and owned by this store.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        dim: int = DEFAULT_DIM,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.dim = dim
        self._owns_conn = connection is None
        self._conn = connection if connection is not None else connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            f"""create virtual table if not exists vec_chunks using vec0(
                chunk_id integer primary key,
                course_id text partition key,
                embedding float[{self.dim}]
            )"""
        )
        self._conn.execute(
            """create table if not exists chunks(
                chunk_id integer primary key autoincrement,
                course_id text not null,
                document_id text not null,
                text text not null
            )"""
        )
        # Keyword index for BM25 search. Only ``text`` is tokenised; the ids are
        # stored alongside so results can be filtered by course and joined back.
        self._conn.execute(
            """create virtual table if not exists fts_chunks using fts5(
                text, chunk_id unindexed, course_id unindexed,
                tokenize = 'porter unicode61'
            )"""
        )
        # Backfill databases created before the keyword index existed.
        (indexed,) = self._conn.execute("select count(*) from fts_chunks").fetchone()
        if indexed == 0:
            self._conn.execute(
                "insert into fts_chunks(text, chunk_id, course_id) "
                "select text, chunk_id, course_id from chunks"
            )
        self._conn.commit()

    def add(
        self,
        course_id: str,
        document_id: str,
        chunks: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> list[int]:
        """Store chunks and their vectors for a course; return new chunk ids."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        ids: list[int] = []
        for text, vector in zip(chunks, vectors, strict=True):
            if len(vector) != self.dim:
                raise ValueError(f"expected {self.dim}-dim vectors, got {len(vector)}")
            cursor = self._conn.execute(
                "insert into chunks(course_id, document_id, text) values (?, ?, ?)",
                (course_id, document_id, text),
            )
            chunk_id = cursor.lastrowid
            if chunk_id is None:  # pragma: no cover - sqlite always sets this on insert
                raise RuntimeError("failed to obtain chunk id after insert")
            self._conn.execute(
                "insert into vec_chunks(chunk_id, course_id, embedding) values (?, ?, ?)",
                (chunk_id, course_id, _serialize(vector)),
            )
            self._conn.execute(
                "insert into fts_chunks(text, chunk_id, course_id) values (?, ?, ?)",
                (text, chunk_id, course_id),
            )
            ids.append(chunk_id)
        self._conn.commit()
        return ids

    def search(self, course_id: str, query_vector: Sequence[float], k: int = 4) -> list[SearchHit]:
        """Return the ``k`` chunks in ``course_id`` closest to the query vector."""
        if len(query_vector) != self.dim:
            raise ValueError(f"expected {self.dim}-dim query, got {len(query_vector)}")
        if k <= 0:
            raise ValueError("k must be positive")

        rows = self._conn.execute(
            """select v.chunk_id, c.document_id, c.text, v.distance
               from vec_chunks v
               join chunks c on c.chunk_id = v.chunk_id
               where v.embedding match ? and k = ? and v.course_id = ?
               order by v.distance""",
            (_serialize(query_vector), k, course_id),
        ).fetchall()
        return [SearchHit(cid, doc, text, dist) for cid, doc, text, dist in rows]

    def keyword_search(self, course_id: str, query: str, k: int = 4) -> list[SearchHit]:
        """Return the ``k`` chunks in ``course_id`` that best match ``query`` by BM25.

        The query is reduced to its words, minus stopwords, and OR-ed together,
        so punctuation in a student's question can never be parsed as FTS5
        query syntax. The index uses the Porter stemmer, so "absorbs" matches
        "absorb". The returned ``distance`` is the BM25 score (lower is better).
        """
        if k <= 0:
            raise ValueError("k must be positive")
        terms = [t for t in re.findall(r"\w+", query.lower()) if t not in STOPWORDS]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in terms)
        rows = self._conn.execute(
            """select f.chunk_id, c.document_id, c.text, bm25(fts_chunks)
               from fts_chunks f
               join chunks c on c.chunk_id = f.chunk_id
               where fts_chunks match ? and f.course_id = ?
               order by bm25(fts_chunks)
               limit ?""",
            (match, course_id, k),
        ).fetchall()
        return [SearchHit(cid, doc, text, score) for cid, doc, text, score in rows]

    def hybrid_search(
        self,
        course_id: str,
        query: str,
        query_vector: Sequence[float],
        k: int = 4,
        candidates: int = 20,
    ) -> list[SearchHit]:
        """Fuse vector and BM25 rankings with Reciprocal Rank Fusion.

        Each list contributes ``1 / (RRF_K + rank)`` per chunk, so a chunk that
        ranks well in both wins, while one found by only one method can still
        make the cut. Only ranks are used, so the two methods' very different
        score scales never need to be compared. Hits keep the distance from
        whichever search found them first (vector search takes precedence).
        """
        if k <= 0:
            raise ValueError("k must be positive")
        depth = max(k, candidates)
        ranked = (
            self.search(course_id, query_vector, k=depth),
            self.keyword_search(course_id, query, k=depth),
        )
        scores: dict[int, float] = {}
        hits: dict[int, SearchHit] = {}
        for results in ranked:
            for rank, hit in enumerate(results, start=1):
                scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1 / (RRF_K + rank)
                hits.setdefault(hit.chunk_id, hit)
        best = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:k]
        return [hits[cid] for cid in best]

    def sample(self, course_id: str, n: int) -> list[SearchHit]:
        """Return up to ``n`` chunks spread evenly across a course's material.

        Used to seed a quiz when no topic is given: rather than the first ``n``
        chunks (which would all come from the start of one document), pick
        evenly-spaced chunks ordered by id so the sample covers the breadth of
        the course. Deterministic — the same store yields the same sample.
        """
        if n <= 0:
            raise ValueError("n must be positive")
        rows = self._conn.execute(
            "select chunk_id, document_id, text from chunks where course_id = ? order by chunk_id",
            (course_id,),
        ).fetchall()
        if not rows:
            return []
        total = len(rows)
        # Evenly spaced indices across [0, total): i * total // n lands one pick
        # in each of n equal-width buckets, so the sample spans the material.
        picked = rows if n >= total else [rows[i * total // n] for i in range(n)]
        # distance is 0.0: these chunks weren't ranked against a query vector.
        return [SearchHit(cid, doc, text, 0.0) for cid, doc, text in picked]

    def count(self, course_id: str) -> int:
        """How many chunks are stored for a course."""
        (n,) = self._conn.execute(
            "select count(*) from chunks where course_id = ?", (course_id,)
        ).fetchone()
        return int(n)

    def close(self) -> None:
        """Close the connection, unless it was injected and owned by the caller."""
        if self._owns_conn:
            self._conn.close()
