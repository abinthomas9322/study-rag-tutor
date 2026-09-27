"""Retrieval evaluation: score a retriever against a hand-labelled golden set.

Each golden item is a question plus a short ``expected`` phrase copied verbatim
from the course material. A retrieved chunk counts as relevant when it contains
that phrase, so scoring needs no LLM and no API key — it is fast, free and
deterministic, which lets it run in CI on every change.

Metrics:
    Hit@k: share of questions where a relevant chunk appears in the top ``k``.
    MRR:   mean of ``1 / rank`` of the first relevant chunk (0 when none is
           found), so ranking the right chunk higher scores better.
"""

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rag.store import SearchHit

Retriever = Callable[[str, int], Sequence[SearchHit]]


@dataclass(frozen=True)
class GoldenItem:
    """One labelled question and the phrase a relevant chunk must contain."""

    id: str
    question: str
    expected: str


@dataclass(frozen=True)
class ItemResult:
    """How the retriever did on a single golden item."""

    id: str
    rank: int | None  # 1-based rank of the first relevant chunk, None if missed
    latency_ms: float


@dataclass(frozen=True)
class EvalReport:
    """Aggregate retrieval metrics over a whole golden set."""

    k: int
    hit_rate: float
    mrr: float
    mean_latency_ms: float
    items: list[ItemResult]

    @property
    def misses(self) -> list[str]:
        """Ids of the questions whose relevant chunk was not retrieved."""
        return [r.id for r in self.items if r.rank is None]


def _normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def load_golden(path: str | Path) -> list[GoldenItem]:
    """Read a JSONL golden set (one object per line; blank lines ignored)."""
    items: list[GoldenItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            items.append(GoldenItem(row["id"], row["question"], row["expected"]))
    return items


def first_relevant_rank(hits: Sequence[SearchHit], expected: str) -> int | None:
    """Return the 1-based rank of the first hit containing ``expected``."""
    needle = _normalise(expected)
    for rank, hit in enumerate(hits, start=1):
        if needle in _normalise(hit.text):
            return rank
    return None


def evaluate(retriever: Retriever, items: Sequence[GoldenItem], k: int = 4) -> EvalReport:
    """Run every golden question through ``retriever`` and score the results."""
    if not items:
        raise ValueError("golden set is empty")
    if k <= 0:
        raise ValueError("k must be positive")

    results: list[ItemResult] = []
    for item in items:
        start = time.perf_counter()
        hits = list(retriever(item.question, k))[:k]
        latency_ms = (time.perf_counter() - start) * 1000
        results.append(ItemResult(item.id, first_relevant_rank(hits, item.expected), latency_ms))

    n = len(results)
    return EvalReport(
        k=k,
        hit_rate=sum(r.rank is not None for r in results) / n,
        mrr=sum(1 / r.rank for r in results if r.rank is not None) / n,
        mean_latency_ms=sum(r.latency_ms for r in results) / n,
        items=results,
    )
