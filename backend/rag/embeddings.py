"""Turn text into vectors with fastembed (ONNX, CPU — no PyTorch).

The model is loaded lazily on first use and cached on the instance, so
constructing an ``Embedder`` is cheap and the ~90 MB model download/load
happens only when embeddings are actually needed.
"""

from collections.abc import Sequence

from fastembed import TextEmbedding

from rag.config import get_settings


class Embedder:
    """Lazy wrapper around a fastembed text-embedding model."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().embed_model
        self._model: TextEmbedding | None = None

    @property
    def model(self) -> TextEmbedding:
        """The underlying model, built on first access and cached thereafter."""
        if self._model is None:
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts into a list of float vectors."""
        return [[float(x) for x in vec] for vec in self.model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into one float vector."""
        return self.embed([text])[0]
