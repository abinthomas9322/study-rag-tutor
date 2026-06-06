"""Generate grounded, cited answers from retrieved context using Groq.

The model is instructed to answer *only* from the supplied course-material
context and to admit when the answer isn't there, which is what keeps the
assistant from hallucinating. When retrieval finds nothing, we short-circuit
with an honest "I don't know" and never call the LLM at all.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from rag.config import Settings, get_settings
from rag.store import SearchHit

SYSTEM_PROMPT = (
    "You are a study assistant for a university course. Answer the student's "
    "question using ONLY the context from the course materials provided below. "
    "If the answer is not contained in the context, say you don't know — do not "
    "use outside knowledge or guess. Cite the sources you rely on as [Source N]."
)

NO_CONTEXT_MESSAGE = "I don't know — I couldn't find anything about that in the course materials."


@dataclass(frozen=True)
class Answer:
    """A generated answer plus the source chunks it was grounded in."""

    text: str
    sources: list[SearchHit]


class _ChatClient(Protocol):
    """Structural type for the bit of the OpenAI client we use."""

    @property
    def chat(self) -> Any: ...


def format_context(hits: Sequence[SearchHit]) -> str:
    """Render retrieved chunks as a numbered, citable context block."""
    return "\n\n".join(f"[Source {i}]\n{hit.text}" for i, hit in enumerate(hits, start=1))


def build_messages(question: str, hits: Sequence[SearchHit]) -> list[dict[str, str]]:
    """Build the system + user chat messages for a grounded answer."""
    context = format_context(hits)
    user = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


class AnswerGenerator:
    """Turns a question + retrieved chunks into a cited answer via Groq."""

    def __init__(self, client: _ChatClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self) -> _ChatClient:
        """The chat client, created lazily so construction needs no API key."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.settings.groq_api_key, base_url=self.settings.llm_base_url
            )
        return self._client

    def generate(self, question: str, hits: Sequence[SearchHit]) -> Answer:
        """Answer ``question`` grounded in ``hits``; honest 'don't know' if empty."""
        if not hits:
            return Answer(NO_CONTEXT_MESSAGE, [])

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=build_messages(question, hits),
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        return Answer(content, list(hits))
