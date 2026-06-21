"""Tests for the FastAPI app factory and /health endpoint.

The health endpoint is a liveness probe that also self-reports build metadata
so the Render dashboard can confirm a deploy finished the seed step without
reading the API logs.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import __version__
from app.main import DEMO_COURSE_ID, create_app
from rag.config import Settings


def _app(*, db_path: str = ":memory:") -> FastAPI:
    # In-memory settings so building the app never touches the filesystem.
    return create_app(settings=Settings(_env_file=None, db_path=db_path))


def test_create_app_returns_fastapi_instance() -> None:
    assert isinstance(_app(), FastAPI)


def test_health_returns_200_and_status_ok() -> None:
    response = TestClient(_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_health_reports_api_version() -> None:
    body = TestClient(_app()).get("/health").json()
    assert body["version"] == __version__


def test_health_reports_demo_seeded_false_when_no_courses_exist() -> None:
    body = TestClient(_app()).get("/health").json()
    assert body["demo_seeded"] is False


def test_health_reports_demo_seeded_true_when_demo_course_exists() -> None:
    app = _app()
    # Create the demo course id the way the seed script does.
    app.state.db.create_course(DEMO_COURSE_ID, "Biology 101 — OpenStax")
    body = TestClient(app).get("/health").json()
    assert body["demo_seeded"] is True


def test_health_reports_db_kind_and_path() -> None:
    body = TestClient(_app(db_path=":memory:")).get("/health").json()
    assert body["db_kind"] == "sqlite"
    assert body["db_path"] == ":memory:"


def test_health_reports_non_default_db_path() -> None:
    # A non-default path proves the endpoint is reading from settings, not
    # returning a hard-coded string.
    body = TestClient(_app(db_path="/tmp/tutor.db")).get("/health").json()
    assert body["db_path"] == "/tmp/tutor.db"


def test_openapi_schema_is_served() -> None:
    schema = TestClient(_app()).get("/openapi.json").json()
    assert schema["info"]["title"] == "Study-Group RAG Tutor"
    # Version is shared between /health and OpenAPI so dashboards line up.
    assert schema["info"]["version"] == __version__


def test_create_app_rejects_partial_injection() -> None:
    import pytest

    from app.db import Database

    with pytest.raises(ValueError, match="both db and store"):
        create_app(db=Database(db_path=":memory:"))
