"""Tests for the embedding wrapper.

The fastembed model is an external boundary (a ~90 MB download), so the unit
tests mock it for speed and determinism. A single real-model test runs only
when RUN_MODEL_TESTS=1 is set, so CI stays fast and offline.
"""

import os
from collections.abc import Iterator

import pytest

import rag.embeddings as embeddings_module
from rag.embeddings import Embedder


class _FakeModel:
    """Stand-in for fastembed.TextEmbedding with deterministic output."""

    instances = 0

    def __init__(self, model_name: str) -> None:
        type(self).instances += 1
        self.model_name = model_name

    def embed(self, texts: list[str]) -> Iterator[list[float]]:
        for t in texts:
            yield [float(len(t)), 1.0, 2.0]


@pytest.fixture
def fake_model(monkeypatch: pytest.MonkeyPatch) -> type[_FakeModel]:
    _FakeModel.instances = 0
    monkeypatch.setattr(embeddings_module, "TextEmbedding", _FakeModel)
    return _FakeModel


def test_embed_returns_one_vector_per_text(fake_model: type[_FakeModel]) -> None:
    vectors = Embedder().embed(["a", "bb", "ccc"])
    assert len(vectors) == 3
    assert vectors[0] == [1.0, 1.0, 2.0]
    assert vectors[2][0] == 3.0


def test_embed_query_returns_single_vector(fake_model: type[_FakeModel]) -> None:
    assert Embedder().embed_query("hello") == [5.0, 1.0, 2.0]


def test_values_are_plain_floats(fake_model: type[_FakeModel]) -> None:
    vectors = Embedder().embed(["x"])
    assert all(isinstance(x, float) for x in vectors[0])


def test_model_is_loaded_lazily_and_only_once(fake_model: type[_FakeModel]) -> None:
    embedder = Embedder()
    assert fake_model.instances == 0  # not built at construction time
    embedder.embed(["one"])
    embedder.embed(["two"])
    embedder.embed_query("three")
    assert fake_model.instances == 1  # built once, then cached


def test_custom_model_name_is_used(fake_model: type[_FakeModel]) -> None:
    embedder = Embedder(model_name="custom/model")
    assert embedder.model.model_name == "custom/model"


@pytest.mark.skipif(
    os.getenv("RUN_MODEL_TESTS") != "1",
    reason="set RUN_MODEL_TESTS=1 to run the real fastembed model (downloads ~90 MB)",
)
def test_real_model_produces_consistent_vectors() -> None:
    embedder = Embedder()
    a = embedder.embed_query("the cat sat on the mat")
    b = embedder.embed_query("the cat sat on the mat")
    c = embedder.embed_query("quantum chromodynamics")
    assert len(a) == len(c) > 0
    assert a == b  # deterministic
    assert a != c  # different text -> different vector
