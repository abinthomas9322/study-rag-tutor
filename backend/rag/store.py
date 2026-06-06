"""Persistent vector store backed by SQLite + the sqlite-vec extension.

Each chunk's text lives in an ordinary ``chunks`` table; its embedding lives
in a ``vec0`` virtual table that shares the same ``chunk_id``. Vectors are
partitioned by ``course_id`` so a similarity search only ever ranks chunks
from the course being queried — one class never sees another's material.
"""

import sqlite3
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec

# Embedding dimensions for all-MiniLM-L6-v2.
DEFAULT_DIM = 384


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


class VectorStore:
    """Stores chunk text and embeddings, scoped per course, in one SQLite file."""

    def __init__(self, db_path: str = ":memory:", dim: int = DEFAULT_DIM) -> None:
        self.dim = dim
        self._conn = self._connect(db_path)
        self._init_schema()

    @staticmethod
    def _connect(db_path: str) -> sqlite3.Connection:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

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

    def count(self, course_id: str) -> int:
        """How many chunks are stored for a course."""
        (n,) = self._conn.execute(
            "select count(*) from chunks where course_id = ?", (course_id,)
        ).fetchone()
        return int(n)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
