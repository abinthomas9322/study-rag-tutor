"""Tests for the cross-encoder reranker wrapper (model replaced by a fake)."""

from collections.abc import Iterable, Sequence

import pytest

from app.main import create_app
from rag.config import Settings
from rag.rerank import Reranker
from rag.store import SearchHit


class _FakeCrossEncoder:
    """Scores a passage by how many query words it contains."""

    def rerank(self, query: str, documents: Sequence[str]) -> Iterable[float]:
        words = set(query.lower().split())
        return [float(len(words & set(d.lower().split()))) for d in documents]


def _reranker() -> Reranker:
    reranker = Reranker("fake-model")
    reranker._model = _FakeCrossEncoder()  # type: ignore[assignment]
    return reranker


def _hits(*texts: str) -> list[SearchHit]:
    return [SearchHit(i, "doc", t, float(i)) for i, t in enumerate(texts)]


def test_rerank_orders_by_cross_encoder_score_and_truncates() -> None:
    hits = _hits("nothing relevant", "the stroma", "calvin cycle in the stroma")
    result = _reranker().rerank("calvin cycle stroma", hits, k=2)
    assert [h.text for h in result] == ["calvin cycle in the stroma", "the stroma"]


def test_rerank_empty_hits_returns_empty() -> None:
    assert _reranker().rerank("q", [], k=3) == []


def test_rerank_non_positive_k_raises() -> None:
    with pytest.raises(ValueError):
        _reranker().rerank("q", _hits("a"), k=0)


def test_model_is_built_lazily_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[str] = []

    class _Stub:
        def __init__(self, model_name: str) -> None:
            built.append(model_name)

    monkeypatch.setattr("rag.rerank.TextCrossEncoder", _Stub)
    reranker = Reranker("some-model")
    assert built == []
    assert reranker.model is reranker.model
    assert built == ["some-model"]


def test_default_model_name_comes_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANK_MODEL", "custom/reranker")
    assert Reranker().model_name == "custom/reranker"


def test_create_app_builds_reranker_only_when_enabled() -> None:
    on = create_app(settings=Settings(_env_file=None, db_path=":memory:", rerank=True))
    off = create_app(settings=Settings(_env_file=None, db_path=":memory:", rerank=False))
    assert isinstance(on.state.reranker, Reranker)
    assert off.state.reranker is None
