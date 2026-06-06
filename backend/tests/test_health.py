"""Tests for the FastAPI app factory and health endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    assert isinstance(create_app(), FastAPI)


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_served() -> None:
    client = TestClient(create_app())
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Study-Group RAG Tutor"
