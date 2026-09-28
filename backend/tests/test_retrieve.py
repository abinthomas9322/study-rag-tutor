"""Tests for the retrieval-mode switch in the service layer."""

import pytest

from app.services import retrieve
from rag.config import Settings
from rag.store import SearchHit, VectorStore


class _FakeEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]


def _store() -> VectorStore:
    store = VectorStore(dim=4)
    store.add(
        "c1",
        "d",
        ["The stroma surrounds the grana.", "The rough ER is studded with ribosomes."],
        [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
    )
    return store


@pytest.mark.parametrize(
    ("mode", "first"),
    [
        ("vector", "The stroma surrounds the grana."),
        # The ER chunk is found by both searches, so fusion ranks it first.
        ("hybrid", "The rough ER is studded with ribosomes."),
    ],
)
def test_retrieve_uses_configured_mode(mode: str, first: str) -> None:
    settings = Settings(_env_file=None, retrieval_mode=mode, top_k=2)  # type: ignore[arg-type]
    hits = retrieve(
        "rough ER",
        "c1",
        store=_store(),
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        settings=settings,
    )
    assert hits[0].text == first
    assert len(hits) == 2


class _ReverseReranker:
    """Stands in for the cross-encoder: returns candidates in reverse order."""

    def __init__(self) -> None:
        self.seen: int = 0

    def rerank(self, query: str, hits: list[SearchHit], k: int) -> list[SearchHit]:
        self.seen = len(hits)
        return list(reversed(hits))[:k]


def test_retrieve_reranks_a_wider_candidate_list() -> None:
    settings = Settings(_env_file=None, top_k=1, rerank_candidates=5)
    reranker = _ReverseReranker()
    hits = retrieve(
        "grana",
        "c1",
        store=_store(),
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        settings=settings,
        reranker=reranker,  # type: ignore[arg-type]
    )
    assert reranker.seen == 2  # both chunks fetched, not just top_k=1
    assert len(hits) == 1
