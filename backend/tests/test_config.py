"""Tests for typed settings: defaults and environment overrides."""

import pytest

from rag.config import Settings, get_settings


def test_defaults_are_sensible() -> None:
    # _env_file=None keeps the test deterministic regardless of any local .env.
    s = Settings(_env_file=None)
    assert s.llm_base_url.startswith("https://")
    assert s.llm_model
    assert s.embed_model
    assert s.chunk_size == 800
    assert s.chunk_overlap == 120
    assert s.top_k == 4
    assert s.groq_api_key == ""


def test_env_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    monkeypatch.setenv("TOP_K", "7")
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    s = Settings(_env_file=None)
    assert s.groq_api_key == "test-key-123"
    assert s.top_k == 7
    assert s.llm_model == "some-other-model"


def test_get_settings_returns_a_settings_instance() -> None:
    assert isinstance(get_settings(), Settings)
