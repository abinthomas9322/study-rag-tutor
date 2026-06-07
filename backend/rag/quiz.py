"""Generate multiple-choice quizzes grounded in retrieved course material.

Like :mod:`rag.answer`, the model is told to write questions *only* from the
supplied context, so a quiz never tests material the class hasn't been given.
The model is asked for a strict JSON object (Groq's JSON mode) which we parse
into typed questions; malformed output raises a clear error rather than being
passed off as a usable quiz. When retrieval finds nothing we short-circuit to
an empty quiz and never call the LLM at all.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from rag.answer import _ChatClient, format_context
from rag.config import Settings, get_settings
from rag.store import SearchHit

QUIZ_SYSTEM_PROMPT = (
    "You are a study assistant writing a practice quiz for a university course. "
    "Write multiple-choice questions using ONLY the context from the course "
    "materials provided below. Do not use outside knowledge or invent facts not "
    "present in the context. Each question must have exactly four options with "
    "exactly one correct answer, and a brief explanation grounded in the context. "
    'Respond with ONLY a JSON object of the form: {"questions": [{"stem": str, '
    '"options": [str, str, str, str], "correct_index": int, "explanation": str}]} '
    "where correct_index is the 0-based index of the correct option."
)

OPTIONS_PER_QUESTION = 4


@dataclass(frozen=True)
class QuizQuestion:
    """One multiple-choice question with its options and the correct answer."""

    stem: str
    options: list[str]
    correct_index: int
    explanation: str


@dataclass(frozen=True)
class Quiz:
    """A generated quiz plus the source chunks its questions were grounded in."""

    questions: list[QuizQuestion]
    sources: list[SearchHit]


@dataclass(frozen=True)
class QuizScore:
    """The result of scoring a set of answers against a quiz's answer key."""

    score: int
    total: int
    correct: list[bool]


def score_quiz(correct_indices: Sequence[int], answers: Sequence[int]) -> QuizScore:
    """Score ``answers`` against the quiz's ``correct_indices``.

    A pure, side-effect-free comparison: the i-th answer is correct when it
    equals the i-th correct option index. Out-of-range answers simply count as
    wrong (they never match a valid index).

    Raises:
        ValueError: If the number of answers doesn't match the number of
            questions — a half-answered quiz can't be scored coherently.
    """
    if len(answers) != len(correct_indices):
        raise ValueError(f"expected {len(correct_indices)} answers, got {len(answers)}")
    correct = [a == c for c, a in zip(correct_indices, answers, strict=True)]
    return QuizScore(score=sum(correct), total=len(correct), correct=correct)


def build_quiz_messages(
    num_questions: int, hits: Sequence[SearchHit], topic: str | None = None
) -> list[dict[str, str]]:
    """Build the system + user chat messages for a grounded quiz request."""
    context = format_context(hits)
    focus = f" about {topic}" if topic else ""
    user = (
        f"Context:\n{context}\n\n"
        f"Write {num_questions} multiple-choice question(s){focus} based only on the "
        f"context above. Return the JSON object described in the system message."
    )
    return [
        {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _parse_question(raw: object) -> QuizQuestion:
    """Validate one raw question object from the model into a QuizQuestion.

    Raises:
        ValueError: If the shape is wrong (missing fields, not four string
            options, or a correct_index that doesn't point at an option).
    """
    if not isinstance(raw, dict):
        raise ValueError("each question must be a JSON object")
    stem = raw.get("stem")
    options = raw.get("options")
    correct_index = raw.get("correct_index")
    explanation = raw.get("explanation", "")
    if not isinstance(stem, str) or not stem.strip():
        raise ValueError("question is missing a non-empty 'stem'")
    if (
        not isinstance(options, list)
        or len(options) != OPTIONS_PER_QUESTION
        or not all(isinstance(o, str) and o.strip() for o in options)
    ):
        raise ValueError(f"question must have exactly {OPTIONS_PER_QUESTION} text options")
    # bool is an int subclass; reject it so True/False can't masquerade as an index.
    if not isinstance(correct_index, int) or isinstance(correct_index, bool):
        raise ValueError("question 'correct_index' must be an integer")
    if not 0 <= correct_index < len(options):
        raise ValueError("question 'correct_index' is out of range")
    if not isinstance(explanation, str):
        raise ValueError("question 'explanation' must be a string")
    return QuizQuestion(
        stem=stem, options=options, correct_index=correct_index, explanation=explanation
    )


def parse_quiz(content: str, hits: Sequence[SearchHit], limit: int) -> Quiz:
    """Parse the model's JSON into a Quiz of at most ``limit`` valid questions.

    Raises:
        ValueError: If the content isn't a JSON object with a non-empty list of
            valid questions under a ``questions`` key.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("the model did not return valid JSON for the quiz") from exc
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise ValueError("the model's quiz JSON must be an object with a 'questions' list")
    questions = [_parse_question(q) for q in data["questions"][:limit]]
    if not questions:
        raise ValueError("the model returned no quiz questions")
    return Quiz(questions=questions, sources=list(hits))


class QuizGenerator:
    """Turns retrieved chunks into a grounded multiple-choice quiz via Groq."""

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

    def generate(
        self, num_questions: int, hits: Sequence[SearchHit], topic: str | None = None
    ) -> Quiz:
        """Generate a quiz grounded in ``hits``; empty quiz if there are none.

        Raises:
            ValueError: If the model's response can't be parsed into questions.
        """
        if not hits:
            return Quiz(questions=[], sources=[])

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=build_quiz_messages(num_questions, hits, topic),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return parse_quiz(content, hits, limit=num_questions)
