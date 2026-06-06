"""Tests for the PDF upload + ingest endpoint.

A fake embedder stands in for the real model (an external download) so these
run fast and offline; the rest of the pipeline (extract, chunk, store, record)
runs for real against an in-memory shared connection.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from rag.config import Settings
from rag.store import VectorStore, connect

DIM = 8


class _FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7)] * DIM for t in texts]


def _client() -> tuple[TestClient, Database, VectorStore]:
    conn = connect(":memory:")
    db = Database(connection=conn)
    store = VectorStore(dim=DIM, connection=conn)
    app = create_app(
        db=db,
        store=store,
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        settings=Settings(_env_file=None),
    )
    return TestClient(app), db, store


def _pdf_upload(
    client: TestClient, course: str, name: str, data: bytes, ctype: str = "application/pdf"
):
    return client.post(f"/courses/{course}/documents", files={"file": (name, data, ctype)})


def test_upload_indexes_pdf_and_creates_course(make_pdf: Callable[..., bytes]) -> None:
    client, db, store = _client()
    pdf = make_pdf("Photosynthesis converts light energy into chemical energy in plants")
    resp = _pdf_upload(client, "CS101", "lecture1.pdf", pdf)

    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "lecture1.pdf"
    assert body["course_id"] == "CS101"
    assert body["num_chunks"] >= 1
    # Course auto-created and chunks actually stored in the vector store.
    assert db.get_course("CS101") is not None
    assert store.count("CS101") == body["num_chunks"]


def test_uploaded_content_is_retrievable(make_pdf: Callable[..., bytes]) -> None:
    client, _db, store = _client()
    pdf = make_pdf("The mitochondrion is the powerhouse of the cell")
    _pdf_upload(client, "BIO", "cells.pdf", pdf)
    hits = store.search("BIO", [0.0] * DIM, k=5)
    assert any("mitochondrion" in h.text for h in hits)


def test_list_documents_returns_uploaded(make_pdf: Callable[..., bytes]) -> None:
    client, _db, _store = _client()
    _pdf_upload(client, "CS101", "a.pdf", make_pdf("alpha content here"))
    _pdf_upload(client, "CS101", "b.pdf", make_pdf("beta content here"))
    listing = client.get("/courses/CS101/documents").json()
    assert {d["filename"] for d in listing} == {"a.pdf", "b.pdf"}


def test_list_documents_empty_for_unknown_course() -> None:
    client, _db, _store = _client()
    assert client.get("/courses/GHOST/documents").json() == []


def test_non_pdf_is_rejected() -> None:
    client, _db, _store = _client()
    resp = _pdf_upload(client, "CS101", "notes.txt", b"just text", ctype="text/plain")
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_pdf_without_text_is_rejected(make_pdf: Callable[..., bytes]) -> None:
    client, _db, _store = _client()
    resp = _pdf_upload(client, "CS101", "blank.pdf", make_pdf(""))
    assert resp.status_code == 400
    assert "no extractable text" in resp.json()["detail"]
