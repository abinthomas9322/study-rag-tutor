"""Tests for grounded quiz generation (rag.quiz) and the /quiz endpoint.

The Groq LLM is an external boundary, so a fake chat client stands in for it
and returns canned JSON. Retrieval, sampling, JSON parsing/validation, the
empty-context short-circuit, and response shaping all run for real.
"""

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from rag.config import Settings
from rag.quiz import (
    OPTIONS_PER_QUESTION,
    QUIZ_SYSTEM_PROMPT,
    Quiz,
    QuizGenerator,
    QuizQuestion,
    QuizScore,
    build_quiz_messages,
    parse_quiz,
    score_quiz,
)
from rag.store import SearchHit, VectorStore, connect

DIM = 8


def _hit(text: str = "ctx", doc: str = "doc1", cid: int = 1, dist: float = 0.1) -> SearchHit:
    return SearchHit(chunk_id=cid, document_id=doc, text=text, distance=dist)


def _question(stem: str = "Q?", correct: int = 0, explanation: str = "because") -> dict[str, Any]:
    return {
        "stem": stem,
        "options": ["opt0", "opt1", "opt2", "opt3"],
        "correct_index": correct,
        "explanation": explanation,
    }


def _quiz_json(*questions: dict[str, Any]) -> str:
    return json.dumps({"questions": list(questions) or [_question()]})


# --- Fakes -----------------------------------------------------------------
class _FakeCompletions:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    def __init__(self, content: str | None) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def _generator(content: str | None) -> QuizGenerator:
    settings = Settings(_env_file=None, llm_model="test-model")
    return QuizGenerator(client=_FakeClient(content), settings=settings)


# --- Prompt construction ---------------------------------------------------
def test_system_prompt_enforces_grounding_and_json() -> None:
    lowered = QUIZ_SYSTEM_PROMPT.lower()
    assert "only" in lowered
    assert "json" in lowered
    assert "correct_index" in lowered


def test_build_messages_includes_count_topic_and_context() -> None:
    messages = build_quiz_messages(3, [_hit("photosynthesis is...")], topic="photosynthesis")
    assert messages[0] == {"role": "system", "content": QUIZ_SYSTEM_PROMPT}
    user = messages[1]["content"]
    assert "3 multiple-choice" in user
    assert "about photosynthesis" in user
    assert "[Source 1]" in user


def test_build_messages_without_topic_omits_focus() -> None:
    user = build_quiz_messages(2, [_hit()])[1]["content"]
    assert "about" not in user.split("based only")[0]


# --- Parsing & validation --------------------------------------------------
def test_parse_quiz_builds_typed_questions() -> None:
    quiz = parse_quiz(_quiz_json(_question("What is X?", 2)), [_hit()], limit=5)
    assert isinstance(quiz, Quiz)
    assert len(quiz.questions) == 1
    q = quiz.questions[0]
    assert isinstance(q, QuizQuestion)
    assert q.stem == "What is X?"
    assert q.correct_index == 2
    assert len(q.options) == OPTIONS_PER_QUESTION
    assert quiz.sources == [_hit()]


def test_parse_quiz_clamps_to_limit() -> None:
    content = _quiz_json(_question("a"), _question("b"), _question("c"))
    quiz = parse_quiz(content, [_hit()], limit=2)
    assert [q.stem for q in quiz.questions] == ["a", "b"]


def test_parse_quiz_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_quiz("not json at all", [_hit()], limit=5)


def test_parse_quiz_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_quiz("", [_hit()], limit=5)


def test_parse_quiz_requires_questions_list() -> None:
    with pytest.raises(ValueError, match="'questions' list"):
        parse_quiz(json.dumps({"items": []}), [_hit()], limit=5)


def test_parse_quiz_rejects_top_level_array() -> None:
    with pytest.raises(ValueError, match="'questions' list"):
        parse_quiz(json.dumps([_question()]), [_hit()], limit=5)


def test_parse_quiz_rejects_no_questions() -> None:
    with pytest.raises(ValueError, match="no quiz questions"):
        parse_quiz(json.dumps({"questions": []}), [_hit()], limit=5)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda q: q.update(stem=""), "stem"),
        (lambda q: q.pop("stem"), "stem"),
        (lambda q: q.update(options=["a", "b", "c"]), "options"),
        (lambda q: q.update(options=["a", "b", "c", ""]), "options"),
        (lambda q: q.update(options=["a", "b", "c", 4]), "options"),
        (lambda q: q.update(correct_index="0"), "must be an integer"),
        (lambda q: q.update(correct_index=True), "must be an integer"),
        (lambda q: q.update(correct_index=9), "out of range"),
        (lambda q: q.update(correct_index=-1), "out of range"),
        (lambda q: q.update(explanation=123), "explanation"),
    ],
)
def test_parse_quiz_rejects_malformed_question(
    mutate: Callable[[dict[str, Any]], Any], match: str
) -> None:
    q = _question()
    mutate(q)
    with pytest.raises(ValueError, match=match):
        parse_quiz(json.dumps({"questions": [q]}), [_hit()], limit=5)


def test_parse_quiz_rejects_non_object_question() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_quiz(json.dumps({"questions": ["nope"]}), [_hit()], limit=5)


def test_parse_quiz_defaults_missing_explanation() -> None:
    q = _question()
    q.pop("explanation")
    quiz = parse_quiz(json.dumps({"questions": [q]}), [_hit()], limit=5)
    assert quiz.questions[0].explanation == ""


# --- Generation ------------------------------------------------------------
def test_generate_returns_quiz_with_sources() -> None:
    hits = [_hit("the mitochondria is the powerhouse")]
    quiz = _generator(_quiz_json(_question("What is the powerhouse?"))).generate(1, hits)
    assert quiz.questions[0].stem == "What is the powerhouse?"
    assert quiz.sources == hits


def test_generate_requests_json_mode_and_model() -> None:
    gen = _generator(_quiz_json())
    gen.generate(2, [_hit()], topic="cells")
    kwargs = gen.client.chat.completions.last_kwargs
    assert kwargs is not None
    assert kwargs["model"] == "test-model"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0.3


def test_generate_empty_hits_short_circuits_without_calling_llm() -> None:
    gen = _generator(_quiz_json())
    quiz = gen.generate(5, [])
    assert quiz.questions == []
    assert quiz.sources == []
    assert gen.client.chat.completions.last_kwargs is None


def test_generate_propagates_parse_error() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        _generator(None).generate(3, [_hit()])


def test_client_is_built_lazily_without_api_key() -> None:
    gen = QuizGenerator(settings=Settings(_env_file=None))
    assert gen._client is None


def test_injected_client_is_reused() -> None:
    fake = _FakeClient(_quiz_json())
    gen = QuizGenerator(client=fake, settings=Settings(_env_file=None))
    assert gen.client is fake


def test_lazy_client_builds_a_real_openai_object() -> None:
    from openai import OpenAI

    gen = QuizGenerator(settings=Settings(_env_file=None, groq_api_key="dummy-key"))
    assert isinstance(gen.client, OpenAI)


# --- Endpoint --------------------------------------------------------------
class _FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7)] * DIM for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * DIM


def _app_client(quiz_content: str | None) -> TestClient:
    conn = connect(":memory:")
    db = Database(connection=conn)
    store = VectorStore(dim=DIM, connection=conn)
    quiz_generator = QuizGenerator(
        client=_FakeClient(quiz_content), settings=Settings(_env_file=None)
    )
    app = create_app(
        db=db,
        store=store,
        embedder=_FakeEmbedder(),  # type: ignore[arg-type]
        quiz_generator=quiz_generator,
        settings=Settings(_env_file=None),
    )
    return TestClient(app)


def _upload(client: TestClient, course: str, name: str, data: bytes) -> None:
    client.post(f"/courses/{course}/documents", files={"file": (name, data, "application/pdf")})


def test_quiz_endpoint_focused_returns_questions(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_quiz_json(_question("What controls entry to the cell?")))
    _upload(client, "BIO", "cells.pdf", make_pdf("The cell membrane controls what enters the cell"))
    resp = client.post("/courses/BIO/quiz", json={"topic": "cell membrane", "num_questions": 1})

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["id"], str) and body["id"]  # quiz persisted, id returned
    assert len(body["questions"]) == 1
    q = body["questions"][0]
    assert q["stem"] == "What controls entry to the cell?"
    assert len(q["options"]) == OPTIONS_PER_QUESTION
    # The answer key is hidden until the student submits an attempt.
    assert "correct_index" not in q
    assert "explanation" not in q
    assert len(body["sources"]) >= 1


def test_quiz_endpoint_broad_uses_sampled_sources(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_quiz_json())
    _upload(client, "BIO", "cells.pdf", make_pdf("Chunk one about cells", "Chunk two about energy"))
    resp = client.post("/courses/BIO/quiz", json={})  # defaults: no topic, 5 questions

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sources"]) >= 1
    # Sampled sources aren't ranked against a query vector, so distance is 0.0.
    assert all(s["distance"] == 0.0 for s in body["sources"])


def test_quiz_endpoint_empty_course_returns_empty_quiz() -> None:
    client = _app_client(_quiz_json())
    resp = client.post("/courses/EMPTY/quiz", json={"num_questions": 3})

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is None  # nothing persisted for an empty course
    assert body["questions"] == []
    assert body["sources"] == []


def test_quiz_endpoint_is_scoped_to_course(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_quiz_json())
    _upload(client, "BIO", "b.pdf", make_pdf("Biology content about enzymes"))
    resp = client.post("/courses/CHEM/quiz", json={"topic": "enzymes", "num_questions": 2})
    assert resp.json()["questions"] == []


def test_quiz_endpoint_bad_model_output_returns_502(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client("this is not json")
    _upload(client, "BIO", "b.pdf", make_pdf("Some real course content here"))
    resp = client.post("/courses/BIO/quiz", json={"topic": "content", "num_questions": 1})
    assert resp.status_code == 502
    assert "JSON" in resp.json()["detail"]


@pytest.mark.parametrize("num", [0, 11, -3])
def test_quiz_endpoint_rejects_out_of_range_count(num: int) -> None:
    client = _app_client(_quiz_json())
    resp = client.post("/courses/BIO/quiz", json={"num_questions": num})
    assert resp.status_code == 422


def test_quiz_endpoint_rejects_overlong_topic() -> None:
    client = _app_client(_quiz_json())
    resp = client.post("/courses/BIO/quiz", json={"topic": "x" * 201, "num_questions": 1})
    assert resp.status_code == 422


# --- Scoring (pure) --------------------------------------------------------
def test_score_quiz_all_correct() -> None:
    result = score_quiz([0, 1, 2], [0, 1, 2])
    assert result == QuizScore(score=3, total=3, correct=[True, True, True])


def test_score_quiz_none_correct() -> None:
    result = score_quiz([0, 1, 2], [3, 3, 3])
    assert result.score == 0
    assert result.total == 3
    assert result.correct == [False, False, False]


def test_score_quiz_partial() -> None:
    result = score_quiz([0, 1, 2], [0, 3, 2])
    assert result.score == 2
    assert result.correct == [True, False, True]


def test_score_quiz_out_of_range_answer_is_wrong() -> None:
    assert score_quiz([0], [99]).score == 0


def test_score_quiz_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="expected 3 answers, got 2"):
        score_quiz([0, 1, 2], [0, 1])


# --- Submit-attempt endpoint -----------------------------------------------
def _two_question_quiz() -> str:
    return _quiz_json(
        _question("Q1?", correct=0, explanation="because A"),
        _question("Q2?", correct=2, explanation="because C"),
    )


def _make_quiz_and_student(client: TestClient, make_pdf: Callable[..., bytes]) -> tuple[str, int]:
    _upload(client, "BIO", "cells.pdf", make_pdf("Course material about cells and energy"))
    quiz_resp = client.post("/courses/BIO/quiz", json={"topic": "cells", "num_questions": 2})
    quiz_id = quiz_resp.json()["id"]
    student_id = client.post("/courses/BIO/join", json={"display_name": "Alice"}).json()["id"]
    return quiz_id, student_id


def test_submit_attempt_scores_and_reveals_key(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, student_id = _make_quiz_and_student(client, make_pdf)

    resp = client.post(
        f"/courses/BIO/quizzes/{quiz_id}/attempts",
        json={"student_id": student_id, "answers": [0, 0]},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["score"] == 1  # Q1 right (0), Q2 wrong (chose 0, correct 2)
    assert body["total"] == 2
    assert body["quiz_id"] == quiz_id
    assert body["student_id"] == student_id
    first, second = body["results"]
    assert first["your_answer"] == 0
    assert first["correct_index"] == 0
    assert first["is_correct"] is True
    assert second["is_correct"] is False
    assert second["correct_index"] == 2
    assert second["explanation"] == "because C"  # key revealed after submitting


def test_submit_attempt_all_correct(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, student_id = _make_quiz_and_student(client, make_pdf)
    resp = client.post(
        f"/courses/BIO/quizzes/{quiz_id}/attempts",
        json={"student_id": student_id, "answers": [0, 2]},
    )
    assert resp.json()["score"] == 2


def test_submit_attempt_unknown_quiz_is_404(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    _, student_id = _make_quiz_and_student(client, make_pdf)
    resp = client.post(
        "/courses/BIO/quizzes/does-not-exist/attempts",
        json={"student_id": student_id, "answers": [0, 0]},
    )
    assert resp.status_code == 404


def test_submit_attempt_quiz_from_other_course_is_404(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, student_id = _make_quiz_and_student(client, make_pdf)
    # The quiz belongs to BIO; submitting it under CHEM must not resolve.
    resp = client.post(
        f"/courses/CHEM/quizzes/{quiz_id}/attempts",
        json={"student_id": student_id, "answers": [0, 0]},
    )
    assert resp.status_code == 404


def test_submit_attempt_student_not_enrolled_is_404(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, _ = _make_quiz_and_student(client, make_pdf)
    resp = client.post(
        f"/courses/BIO/quizzes/{quiz_id}/attempts",
        json={"student_id": 9999, "answers": [0, 0]},
    )
    assert resp.status_code == 404


def test_submit_attempt_wrong_answer_count_is_422(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, student_id = _make_quiz_and_student(client, make_pdf)
    resp = client.post(
        f"/courses/BIO/quizzes/{quiz_id}/attempts",
        json={"student_id": student_id, "answers": [0]},  # quiz has 2 questions
    )
    assert resp.status_code == 422


# --- List attempts (progress) ----------------------------------------------
def test_list_attempts_returns_history_with_topic(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    quiz_id, student_id = _make_quiz_and_student(client, make_pdf)  # quiz topic "cells"
    client.post(
        f"/courses/BIO/quizzes/{quiz_id}/attempts",
        json={"student_id": student_id, "answers": [0, 2]},
    )

    resp = client.get(f"/courses/BIO/students/{student_id}/attempts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["score"] == 2
    assert body[0]["total"] == 2
    assert body[0]["topic"] == "cells"
    assert body[0]["quiz_id"] == quiz_id


def test_list_attempts_empty_for_new_student(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    _make_quiz_and_student(client, make_pdf)
    student_id = client.post("/courses/BIO/join", json={"display_name": "Bob"}).json()["id"]
    resp = client.get(f"/courses/BIO/students/{student_id}/attempts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_attempts_unknown_student_is_404() -> None:
    client = _app_client(_two_question_quiz())
    resp = client.get("/courses/BIO/students/9999/attempts")
    assert resp.status_code == 404


def test_list_attempts_student_from_other_course_is_404(make_pdf: Callable[..., bytes]) -> None:
    client = _app_client(_two_question_quiz())
    _, student_id = _make_quiz_and_student(client, make_pdf)  # enrolled in BIO
    resp = client.get(f"/courses/CHEM/students/{student_id}/attempts")
    assert resp.status_code == 404
