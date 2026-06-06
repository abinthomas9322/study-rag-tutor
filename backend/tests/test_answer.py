"""Tests for grounded answer generation.

The Groq LLM is an external boundary, so a fake chat client stands in for it.
We assert on the prompt we build and how the response is wrapped, not on the
model's wording.
"""

from types import SimpleNamespace
from typing import Any

from rag.answer import (
    NO_CONTEXT_MESSAGE,
    SYSTEM_PROMPT,
    Answer,
    AnswerGenerator,
    build_messages,
    format_context,
)
from rag.config import Settings
from rag.store import SearchHit


def _hit(text: str, doc: str = "doc1", cid: int = 1, dist: float = 0.1) -> SearchHit:
    return SearchHit(chunk_id=cid, document_id=doc, text=text, distance=dist)


class _FakeCompletions:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    def __init__(self, content: str | None = "Paris is the capital [Source 1].") -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def _generator(content: str | None = "Paris is the capital [Source 1].") -> AnswerGenerator:
    settings = Settings(_env_file=None, llm_model="test-model")
    return AnswerGenerator(client=_FakeClient(content), settings=settings)


# --- Prompt construction ---------------------------------------------------
def test_format_context_numbers_sources_from_one() -> None:
    ctx = format_context([_hit("alpha"), _hit("beta")])
    assert "[Source 1]\nalpha" in ctx
    assert "[Source 2]\nbeta" in ctx


def test_build_messages_has_system_and_user_with_question() -> None:
    messages = build_messages("What is the capital?", [_hit("Paris is the capital.")])
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"
    assert "What is the capital?" in messages[1]["content"]
    assert "[Source 1]" in messages[1]["content"]


def test_system_prompt_enforces_grounding() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "only" in lowered
    assert "don't know" in lowered
    assert "[source n]" in lowered


# --- Generation ------------------------------------------------------------
def test_generate_returns_answer_with_sources() -> None:
    hits = [_hit("Paris is the capital of France.")]
    answer = _generator().generate("What is the capital of France?", hits)
    assert isinstance(answer, Answer)
    assert answer.text == "Paris is the capital [Source 1]."
    assert answer.sources == hits


def test_generate_passes_model_and_low_temperature() -> None:
    gen = _generator()
    gen.generate("q", [_hit("x")])
    kwargs = gen.client.chat.completions.last_kwargs
    assert kwargs is not None
    assert kwargs["model"] == "test-model"
    assert kwargs["temperature"] == 0.1
    assert kwargs["messages"][0]["role"] == "system"


def test_empty_hits_short_circuit_without_calling_llm() -> None:
    gen = _generator()
    answer = gen.generate("anything", [])
    assert answer.text == NO_CONTEXT_MESSAGE
    assert answer.sources == []
    # The LLM was never called.
    assert gen.client.chat.completions.last_kwargs is None


def test_none_content_becomes_empty_string() -> None:
    answer = _generator(content=None).generate("q", [_hit("x")])
    assert answer.text == ""


def test_client_is_built_lazily_without_api_key() -> None:
    # Constructing a generator with no client and no key must not raise.
    gen = AnswerGenerator(settings=Settings(_env_file=None))
    assert gen._client is None


def test_injected_client_is_reused() -> None:
    fake = _FakeClient()
    gen = AnswerGenerator(client=fake, settings=Settings(_env_file=None))
    assert gen.client is fake


def test_lazy_client_builds_a_real_openai_object() -> None:
    # Constructing the OpenAI client makes no network call; this just exercises
    # the lazy-build branch so the real wiring is covered.
    from openai import OpenAI

    gen = AnswerGenerator(settings=Settings(_env_file=None, groq_api_key="dummy-key"))
    assert isinstance(gen.client, OpenAI)
