"""Tests for the retrieval evaluation metrics."""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from rag.evaluation import GoldenItem, evaluate, first_relevant_rank, load_golden
from rag.store import SearchHit


def _hits(*texts: str) -> list[SearchHit]:
    return [SearchHit(i, "doc", t, 0.0) for i, t in enumerate(texts)]


def test_first_relevant_rank_is_case_and_whitespace_insensitive() -> None:
    hits = _hits("nothing here", "The Calvin   cycle\ntakes place in the STROMA")
    assert first_relevant_rank(hits, "takes place in the stroma") == 2


def test_first_relevant_rank_none_when_missing() -> None:
    assert first_relevant_rank(_hits("a", "b"), "stroma") is None


def test_load_golden_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    row = {"id": "q1", "question": "Where?", "expected": "stroma"}
    path.write_text(json.dumps(row) + "\n\n", encoding="utf-8")
    assert load_golden(path) == [GoldenItem("q1", "Where?", "stroma")]


def test_evaluate_computes_hit_rate_and_mrr() -> None:
    corpus = {
        "q1": _hits("stroma", "x"),  # rank 1
        "q2": _hits("x", "thylakoid"),  # rank 2
        "q3": _hits("x", "y"),  # miss
        "q4": _hits("x", "y", "z", "late"),  # relevant only past k=3 -> miss
    }
    items = [
        GoldenItem("q1", "q1", "stroma"),
        GoldenItem("q2", "q2", "thylakoid"),
        GoldenItem("q3", "q3", "granum"),
        GoldenItem("q4", "q4", "late"),
    ]

    def retriever(question: str, k: int) -> Sequence[SearchHit]:
        return corpus[question]

    report = evaluate(retriever, items, k=3)

    assert report.k == 3
    assert report.hit_rate == pytest.approx(2 / 4)
    assert report.mrr == pytest.approx((1 + 0.5) / 4)
    assert report.misses == ["q3", "q4"]
    assert report.mean_latency_ms >= 0


def test_evaluate_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate(lambda q, k: [], [])
    with pytest.raises(ValueError, match="positive"):
        evaluate(lambda q, k: [], [GoldenItem("q", "q", "x")], k=0)
