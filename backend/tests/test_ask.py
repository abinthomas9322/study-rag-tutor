"""Tests for the /ask endpoint (retrieve + grounded answer).

The embedder and the Groq client are external boundaries, so both are faked;
retrieval, scoping, the empty-context short-circuit, and response shaping run
for real.
"""

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from rag.answer import NO_CONTEXT_MESSAGE, AnswerGenerator
from rag.config import Settings
from rag.store import VectorStore, connect

DIM = 8
LLM_REPLY = "Grounded answer [Source 1]."


class _FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7)] * DIM for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * DIM


class _FakeCompletions:
    def create(self, **kwargs: Any) -> Any:
        message = SimpleNamespace(content=LLM_REPLY)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def _client() -> TestClient:
    conn = connect(":memory:")
    db = Database(connection=conn)
    store = VectorStore(dim=DIM, connection=conn)
    generator = AnswerGenerator(client=_FakeClient(), settings=Settings(_env_file=None))
    app = create_app(
        db=db,
        store=store,
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        generator=generator,
        settings=Settings(_env_file=None),
    )
    return TestClient(app)


def _upload(client: TestClient, course: str, name: str, data: bytes) -> None:
    client.post(f"/courses/{course}/documents", files={"file": (name, data, "application/pdf")})


def test_ask_returns_grounded_answer_with_sources(make_pdf: Callable[..., bytes]) -> None:
    client = _client()
    _upload(client, "BIO", "cells.pdf", make_pdf("The cell membrane controls what enters the cell"))
    resp = client.post("/courses/BIO/ask", json={"question": "What does the cell membrane do?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == LLM_REPLY
    assert len(body["sources"]) >= 1
    assert "cell membrane" in body["sources"][0]["text"]
    assert "document_id" in body["sources"][0]


def test_ask_with_no_materials_says_dont_know() -> None:
    client = _client()
    resp = client.post("/courses/EMPTY/ask", json={"question": "anything at all?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == NO_CONTEXT_MESSAGE
    assert body["sources"] == []


def test_ask_is_scoped_to_course(make_pdf: Callable[..., bytes]) -> None:
    client = _client()
    _upload(client, "BIO", "b.pdf", make_pdf("Biology content about enzymes"))
    # A different course has no materials, so it must not see BIO's chunks.
    resp = client.post("/courses/CHEM/ask", json={"question": "enzymes?"})
    assert resp.json()["sources"] == []


def test_ask_empty_question_is_rejected() -> None:
    client = _client()
    resp = client.post("/courses/BIO/ask", json={"question": ""})
    assert resp.status_code == 422
