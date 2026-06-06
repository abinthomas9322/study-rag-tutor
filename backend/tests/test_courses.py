"""Tests for course management and the student join-a-class flow.

These routes only touch the relational database, so a plain in-memory app is
enough — no embedder or LLM involved.
"""

from fastapi.testclient import TestClient

from app.main import create_app
from rag.config import Settings


def _client() -> TestClient:
    return TestClient(create_app(settings=Settings(_env_file=None, db_path=":memory:")))


# --- Course creation -------------------------------------------------------
def test_create_course() -> None:
    client = _client()
    resp = client.post("/courses", json={"id": "CS101", "name": "Intro to CS"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "CS101"
    assert body["name"] == "Intro to CS"
    assert body["created_at"]


def test_create_duplicate_course_conflicts() -> None:
    client = _client()
    client.post("/courses", json={"id": "CS101", "name": "Intro"})
    resp = client.post("/courses", json={"id": "CS101", "name": "Again"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_create_course_validates_input() -> None:
    client = _client()
    assert client.post("/courses", json={"id": "", "name": "x"}).status_code == 422
    assert client.post("/courses", json={"id": "X", "name": ""}).status_code == 422


def test_list_and_get_courses() -> None:
    client = _client()
    client.post("/courses", json={"id": "A", "name": "Course A"})
    client.post("/courses", json={"id": "B", "name": "Course B"})
    assert {c["id"] for c in client.get("/courses").json()} == {"A", "B"}
    assert client.get("/courses/A").json()["name"] == "Course A"


def test_get_unknown_course_is_404() -> None:
    assert _client().get("/courses/GHOST").status_code == 404


# --- Joining ---------------------------------------------------------------
def test_join_course() -> None:
    client = _client()
    client.post("/courses", json={"id": "CS101", "name": "Intro"})
    resp = client.post("/courses/CS101/join", json={"display_name": "Alice"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["display_name"] == "Alice"
    assert body["course_id"] == "CS101"


def test_join_is_idempotent() -> None:
    client = _client()
    client.post("/courses", json={"id": "CS101", "name": "Intro"})
    first = client.post("/courses/CS101/join", json={"display_name": "Alice"}).json()
    again = client.post("/courses/CS101/join", json={"display_name": "Alice"}).json()
    assert first["id"] == again["id"]
    assert len(client.get("/courses/CS101/students").json()) == 1


def test_join_unknown_course_is_404() -> None:
    client = _client()
    resp = client.post("/courses/GHOST/join", json={"display_name": "Alice"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_list_students_is_scoped_to_course() -> None:
    client = _client()
    client.post("/courses", json={"id": "CS101", "name": "Intro"})
    client.post("/courses", json={"id": "BIO", "name": "Biology"})
    client.post("/courses/CS101/join", json={"display_name": "Alice"})
    client.post("/courses/CS101/join", json={"display_name": "Bob"})
    client.post("/courses/BIO/join", json={"display_name": "Carol"})
    assert {s["display_name"] for s in client.get("/courses/CS101/students").json()} == {
        "Alice",
        "Bob",
    }
    assert len(client.get("/courses/BIO/students").json()) == 1


def test_join_validates_display_name() -> None:
    client = _client()
    client.post("/courses", json={"id": "CS101", "name": "Intro"})
    assert client.post("/courses/CS101/join", json={"display_name": ""}).status_code == 422
