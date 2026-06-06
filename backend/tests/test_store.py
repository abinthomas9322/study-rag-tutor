"""Tests for the sqlite-vec vector store.

These use a real (in-memory or temp-file) SQLite database — sqlite-vec is our
own storage layer, not an external boundary, so we exercise it for real with
small deterministic vectors rather than mocking it.
"""

from pathlib import Path

import pytest

from rag.store import SearchHit, VectorStore

DIM = 4


def _store() -> VectorStore:
    return VectorStore(db_path=":memory:", dim=DIM)


def test_add_returns_one_id_per_chunk() -> None:
    store = _store()
    ids = store.add("CS101", "doc1", ["a", "b"], [[1, 0, 0, 0], [0, 1, 0, 0]])
    assert len(ids) == 2
    assert ids[0] != ids[1]


def test_search_ranks_by_similarity() -> None:
    store = _store()
    store.add(
        "CS101",
        "doc1",
        ["near", "far"],
        [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
    )
    hits = store.search("CS101", [1.0, 0.0, 0.0, 0.0], k=2)
    assert [h.text for h in hits] == ["near", "far"]
    assert isinstance(hits[0], SearchHit)
    assert hits[0].distance <= hits[1].distance


def test_search_is_scoped_to_the_course() -> None:
    store = _store()
    # Identical vectors in two different courses.
    store.add("CS101", "doc1", ["cs chunk"], [[1, 0, 0, 0]])
    store.add("BIO", "doc2", ["bio chunk"], [[1, 0, 0, 0]])
    hits = store.search("CS101", [1, 0, 0, 0], k=5)
    assert [h.text for h in hits] == ["cs chunk"]
    assert all(h.document_id == "doc1" for h in hits)


def test_search_returns_at_most_k() -> None:
    store = _store()
    store.add("C", "d", [f"c{i}" for i in range(6)], [[i, 0, 0, 0] for i in range(6)])
    assert len(store.search("C", [0, 0, 0, 0], k=3)) == 3


def test_count_is_per_course() -> None:
    store = _store()
    store.add("C", "d", ["a", "b"], [[1, 0, 0, 0], [0, 1, 0, 0]])
    store.add("D", "d", ["c"], [[1, 0, 0, 0]])
    assert store.count("C") == 2
    assert store.count("D") == 1
    assert store.count("MISSING") == 0


def test_empty_course_returns_no_hits() -> None:
    assert _store().search("NONE", [1, 0, 0, 0], k=4) == []


# --- Validation ------------------------------------------------------------
def test_mismatched_chunks_and_vectors_raise() -> None:
    with pytest.raises(ValueError, match="same length"):
        _store().add("C", "d", ["a", "b"], [[1, 0, 0, 0]])


def test_wrong_vector_dimension_raises() -> None:
    with pytest.raises(ValueError, match="expected 4-dim"):
        _store().add("C", "d", ["a"], [[1, 0, 0]])


def test_wrong_query_dimension_raises() -> None:
    with pytest.raises(ValueError, match="expected 4-dim query"):
        _store().search("C", [1, 0, 0])


@pytest.mark.parametrize("k", [0, -1])
def test_non_positive_k_raises(k: int) -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        _store().search("C", [1, 0, 0, 0], k=k)


# --- Persistence -----------------------------------------------------------
def test_data_persists_to_disk_across_reopen(tmp_path: Path) -> None:
    db = str(tmp_path / "tutor.db")
    store = VectorStore(db_path=db, dim=DIM)
    store.add("C", "d", ["persisted chunk"], [[1, 0, 0, 0]])
    store.close()

    reopened = VectorStore(db_path=db, dim=DIM)
    hits = reopened.search("C", [1, 0, 0, 0], k=1)
    assert hits[0].text == "persisted chunk"
    reopened.close()


def test_connect_creates_missing_parent_dirs(tmp_path: Path) -> None:
    db = str(tmp_path / "nested" / "dir" / "tutor.db")
    store = VectorStore(db_path=db, dim=DIM)
    store.add("C", "d", ["x"], [[1, 0, 0, 0]])
    store.close()
    assert Path(db).exists()
