"""Re-score retrieved chunks with a cross-encoder (fastembed ONNX, CPU).

Vector and keyword search score the query and each chunk separately, which is
fast but coarse. A cross-encoder reads the question and a chunk *together* and
outputs one relevance score, which is more accurate but too slow to run over a
whole course — so it only re-orders a short candidate list from the first-stage
search. Like ``Embedder``, the model is loaded lazily on first use.
"""

from collections.abc import Sequence

from fastembed.rerank.cross_encoder import TextCrossEncoder

from rag.config import get_settings
from rag.store import SearchHit


class Reranker:
    """Lazy wrapper around a fastembed cross-encoder model."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().rerank_model
        self._model: TextCrossEncoder | None = None

    @property
    def model(self) -> TextCrossEncoder:
        """The underlying model, built on first access and cached thereafter."""
        if self._model is None:
            self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def rerank(self, query: str, hits: Sequence[SearchHit], k: int) -> list[SearchHit]:
        """Return the ``k`` hits the cross-encoder judges most relevant to ``query``."""
        if k <= 0:
            raise ValueError("k must be positive")
        if not hits:
            return []
        scores = list(self.model.rerank(query, [h.text for h in hits]))
        order = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)
        return [hits[i] for i in order[:k]]
