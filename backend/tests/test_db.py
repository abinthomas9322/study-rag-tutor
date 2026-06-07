"""Tests for the relational database (courses, students, documents)."""

import pytest

from app.db import Attempt, Course, Database, Document, QuestionRecord, QuizRecord, Student
from rag.quiz import QuizQuestion
from rag.store import VectorStore, connect


def _db() -> Database:
    return Database(db_path=":memory:")


def _questions() -> list[QuizQuestion]:
    return [
        QuizQuestion("Q1?", ["a", "b", "c", "d"], 0, "because a"),
        QuizQuestion("Q2?", ["w", "x", "y", "z"], 2, "because y"),
    ]


# --- Courses ---------------------------------------------------------------
def test_create_and_get_course() -> None:
    db = _db()
    course = db.create_course("CS101", "Intro to CS")
    assert isinstance(course, Course)
    assert course.id == "CS101"
    assert course.name == "Intro to CS"
    assert course.created_at  # timestamp populated by SQLite
    assert db.get_course("CS101") == course


def test_get_missing_course_returns_none() -> None:
    assert _db().get_course("NOPE") is None


def test_duplicate_course_raises() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    with pytest.raises(ValueError, match="already exists"):
        db.create_course("CS101", "Other")


def test_list_courses() -> None:
    db = _db()
    db.create_course("A", "Course A")
    db.create_course("B", "Course B")
    assert {c.id for c in db.list_courses()} == {"A", "B"}


# --- Students --------------------------------------------------------------
def test_join_course_creates_student() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    student = db.join_course("CS101", "Alice")
    assert isinstance(student, Student)
    assert student.course_id == "CS101"
    assert student.display_name == "Alice"


def test_join_course_is_idempotent() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    first = db.join_course("CS101", "Alice")
    again = db.join_course("CS101", "Alice")
    assert first.id == again.id
    assert len(db.list_students("CS101")) == 1


def test_same_name_in_different_courses_are_distinct_students() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    db.create_course("BIO", "Biology")
    a = db.join_course("CS101", "Alice")
    b = db.join_course("BIO", "Alice")
    assert a.id != b.id


def test_join_missing_course_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        _db().join_course("GHOST", "Alice")


def test_list_students_is_scoped_to_course() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    db.create_course("BIO", "Biology")
    db.join_course("CS101", "Alice")
    db.join_course("CS101", "Bob")
    db.join_course("BIO", "Carol")
    assert {s.display_name for s in db.list_students("CS101")} == {"Alice", "Bob"}
    assert len(db.list_students("BIO")) == 1


# --- Documents -------------------------------------------------------------
def test_add_document_generates_id_and_stores_fields() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    doc = db.add_document("CS101", "week1.pdf", num_chunks=12)
    assert isinstance(doc, Document)
    assert doc.id  # uuid generated
    assert doc.filename == "week1.pdf"
    assert doc.num_chunks == 12


def test_add_document_accepts_explicit_id() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    doc = db.add_document("CS101", "f.pdf", doc_id="fixed-id")
    assert doc.id == "fixed-id"


def test_add_document_missing_course_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        _db().add_document("GHOST", "f.pdf")


def test_list_documents_is_scoped_to_course() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    db.create_course("BIO", "Biology")
    db.add_document("CS101", "a.pdf")
    db.add_document("CS101", "b.pdf")
    db.add_document("BIO", "c.pdf")
    assert {d.filename for d in db.list_documents("CS101")} == {"a.pdf", "b.pdf"}
    assert len(db.list_documents("BIO")) == 1


# --- Students: lookup ------------------------------------------------------
def test_get_student_returns_record() -> None:
    db = _db()
    db.create_course("CS101", "Intro")
    student = db.join_course("CS101", "Alice")
    assert db.get_student(student.id) == student


def test_get_missing_student_returns_none() -> None:
    assert _db().get_student(123) is None


# --- Quizzes ---------------------------------------------------------------
def test_save_quiz_persists_questions_in_order() -> None:
    db = _db()
    db.create_course("BIO", "Biology")
    quiz_id = db.save_quiz("BIO", "cells", _questions())

    quiz = db.get_quiz(quiz_id)
    assert isinstance(quiz, QuizRecord)
    assert quiz.course_id == "BIO"
    assert quiz.topic == "cells"

    questions = db.list_quiz_questions(quiz_id)
    assert [q.stem for q in questions] == ["Q1?", "Q2?"]
    assert [q.position for q in questions] == [0, 1]
    first = questions[0]
    assert isinstance(first, QuestionRecord)
    assert first.options == ["a", "b", "c", "d"]  # round-tripped through JSON
    assert first.correct_index == 0
    assert questions[1].correct_index == 2


def test_save_quiz_accepts_null_topic() -> None:
    db = _db()
    db.create_course("BIO", "Biology")
    quiz_id = db.save_quiz("BIO", None, _questions())
    assert db.get_quiz(quiz_id).topic is None


def test_save_quiz_missing_course_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        _db().save_quiz("GHOST", "t", _questions())


def test_get_missing_quiz_returns_none() -> None:
    assert _db().get_quiz("nope") is None


def test_list_questions_of_missing_quiz_is_empty() -> None:
    assert _db().list_quiz_questions("nope") == []


# --- Quiz attempts ---------------------------------------------------------
def _seed_attempt_world() -> tuple[Database, str, int]:
    db = _db()
    db.create_course("BIO", "Biology")
    quiz_id = db.save_quiz("BIO", "cells", _questions())
    student = db.join_course("BIO", "Alice")
    return db, quiz_id, student.id


def test_record_attempt_stores_score_and_answers() -> None:
    db, quiz_id, student_id = _seed_attempt_world()
    attempt = db.record_attempt(quiz_id, student_id, score=1, total=2, answers=[0, 1])
    assert isinstance(attempt, Attempt)
    assert attempt.score == 1
    assert attempt.total == 2
    assert attempt.answers == [0, 1]  # round-tripped through JSON
    assert attempt.submitted_at


def test_list_attempts_for_student_is_scoped() -> None:
    db, quiz_id, alice = _seed_attempt_world()
    bob = db.join_course("BIO", "Bob").id
    db.record_attempt(quiz_id, alice, score=2, total=2, answers=[0, 2])
    db.record_attempt(quiz_id, bob, score=0, total=2, answers=[1, 1])
    alice_attempts = db.list_attempts_for_student(alice)
    assert len(alice_attempts) == 1
    assert alice_attempts[0].student_id == alice


def test_deleting_course_cascades_to_quizzes_and_attempts() -> None:
    db, quiz_id, student_id = _seed_attempt_world()
    db.record_attempt(quiz_id, student_id, score=1, total=2, answers=[0, 0])
    db.conn.execute("delete from courses where id = 'BIO'")
    db.conn.commit()
    assert db.get_quiz(quiz_id) is None
    assert db.list_quiz_questions(quiz_id) == []
    assert db.list_attempts_for_student(student_id) == []


# --- Shared connection with the vector store -------------------------------
def test_shares_one_connection_with_vector_store() -> None:
    # The whole point of sqlite-vec: relational rows and vectors in one file,
    # written through one connection.
    conn = connect(":memory:")
    db = Database(connection=conn)
    store = VectorStore(dim=4, connection=conn)

    db.create_course("CS101", "Intro")
    doc = db.add_document("CS101", "w1.pdf", num_chunks=1)
    store.add("CS101", doc.id, ["a chunk"], [[1.0, 0.0, 0.0, 0.0]])

    hits = store.search("CS101", [1.0, 0.0, 0.0, 0.0], k=1)
    assert hits[0].document_id == doc.id
    assert db.list_documents("CS101")[0].id == doc.id
    conn.close()


def test_closing_db_with_injected_conn_leaves_it_open() -> None:
    conn = connect(":memory:")
    db = Database(connection=conn)
    db.create_course("X", "x")
    db.close()
    assert conn.execute("select count(*) from courses").fetchone()[0] == 1
    conn.close()


def test_closing_owned_connection_closes_it() -> None:
    import sqlite3

    db = Database(db_path=":memory:")
    db.create_course("X", "x")
    db.close()
    with pytest.raises(sqlite3.ProgrammingError):
        db.conn.execute("select 1")
