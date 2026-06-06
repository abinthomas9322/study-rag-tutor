"""Tests for the FastAPI app factory and health endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from rag.config import Settings


def _app() -> FastAPI:
    # In-memory settings so building the app never touches the filesystem.
    return create_app(settings=Settings(_env_file=None, db_path=":memory:"))


def test_create_app_returns_fastapi_instance() -> None:
    assert isinstance(_app(), FastAPI)


def test_health_returns_ok() -> None:
    response = TestClient(_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_served() -> None:
    schema = TestClient(_app()).get("/openapi.json").json()
    assert schema["info"]["title"] == "Study-Group RAG Tutor"


def test_create_app_rejects_partial_injection() -> None:
    import pytest

    from app.db import Database

    with pytest.raises(ValueError, match="both db and store"):
        create_app(db=Database(db_path=":memory:"))
