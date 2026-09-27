"""Tests for the retrieval-mode switch in the service layer."""

import pytest

from app.services import retrieve
from rag.config import Settings
from rag.store import VectorStore


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
