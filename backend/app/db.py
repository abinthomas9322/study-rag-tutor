"""Relational data access for courses, students, and documents on SQLite.

Shares a single connection with the vector store (see :func:`rag.store.connect`)
so the entire application lives in one SQLite file and a document plus its
chunks can be written under one connection. Raw SQL keeps the dependency
footprint small; an ORM would not earn its place here.
"""

import json
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from rag.quiz import QuizQuestion
from rag.store import connect

_SCHEMA = """
create table if not exists courses (
    id          text primary key,
    name        text not null,
    created_at  text not null default (datetime('now'))
);

create table if not exists students (
    id            integer primary key autoincrement,
    course_id     text not null references courses(id) on delete cascade,
    display_name  text not null,
    joined_at     text not null default (datetime('now')),
    unique (course_id, display_name)
);

create table if not exists documents (
    id           text primary key,
    course_id    text not null references courses(id) on delete cascade,
    filename     text not null,
    num_chunks   integer not null default 0,
    uploaded_at  text not null default (datetime('now'))
);

create table if not exists quizzes (
    id          text primary key,
    course_id   text not null references courses(id) on delete cascade,
    topic       text,
    created_at  text not null default (datetime('now'))
);

create table if not exists quiz_questions (
    id             integer primary key autoincrement,
    quiz_id        text not null references quizzes(id) on delete cascade,
    position       integer not null,
    stem           text not null,
    options_json   text not null,
    correct_index  integer not null,
    explanation    text not null default ''
);

create table if not exists quiz_attempts (
    id            integer primary key autoincrement,
    quiz_id       text not null references quizzes(id) on delete cascade,
    student_id    integer not null references students(id) on delete cascade,
    score         integer not null,
    total         integer not null,
    answers_json  text not null,
    submitted_at  text not null default (datetime('now'))
);
"""


@dataclass(frozen=True)
class Course:
    """A course space that students join and documents belong to."""

    id: str
    name: str
    created_at: str


@dataclass(frozen=True)
class Student:
    """A student enrolled in a course."""

    id: int
    course_id: str
    display_name: str
    joined_at: str


@dataclass(frozen=True)
class Document:
    """An uploaded source document belonging to a course."""

    id: str
    course_id: str
    filename: str
    num_chunks: int
    uploaded_at: str


@dataclass(frozen=True)
class QuizRecord:
    """A persisted quiz: its identity, course, and optional focus topic."""

    id: str
    course_id: str
    topic: str | None
    created_at: str


@dataclass(frozen=True)
class QuestionRecord:
    """A persisted quiz question, including its answer key."""

    id: int
    quiz_id: str
    position: int
    stem: str
    options: list[str]
    correct_index: int
    explanation: str


@dataclass(frozen=True)
class Attempt:
    """One student's scored attempt at a quiz."""

    id: int
    quiz_id: str
    student_id: int
    score: int
    total: int
    answers: list[int]
    submitted_at: str


class Database:
    """Relational store for courses, students, and documents.

    Pass ``connection`` to share an existing (sqlite-vec-loaded) connection;
    the caller then owns it. Otherwise one is opened for ``db_path``.
    """

    def __init__(self, db_path: str = ":memory:", connection: sqlite3.Connection | None = None):
        self._owns_conn = connection is None
        self.conn = connection if connection is not None else connect(db_path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- Courses ----------------------------------------------------------
    def create_course(self, course_id: str, name: str) -> Course:
        """Create a new course; raise ValueError if the id is already taken."""
        try:
            row = self.conn.execute(
                "insert into courses(id, name) values (?, ?) returning id, name, created_at",
                (course_id, name),
            ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"course {course_id!r} already exists") from exc
        self.conn.commit()
        return Course(*row)

    def get_course(self, course_id: str) -> Course | None:
        row = self.conn.execute(
            "select id, name, created_at from courses where id = ?", (course_id,)
        ).fetchone()
        return Course(*row) if row else None

    def list_courses(self) -> list[Course]:
        rows = self.conn.execute(
            "select id, name, created_at from courses order by created_at, id"
        ).fetchall()
        return [Course(*r) for r in rows]

    # --- Students ---------------------------------------------------------
    def join_course(self, course_id: str, display_name: str) -> Student:
        """Enrol a student; idempotent — re-joining returns the same record."""
        if self.get_course(course_id) is None:
            raise ValueError(f"course {course_id!r} not found")
        row = self.conn.execute(
            "insert into students(course_id, display_name) values (?, ?) "
            "on conflict(course_id, display_name) do update set display_name = display_name "
            "returning id, course_id, display_name, joined_at",
            (course_id, display_name),
        ).fetchone()
        self.conn.commit()
        return Student(*row)

    def list_students(self, course_id: str) -> list[Student]:
        rows = self.conn.execute(
            "select id, course_id, display_name, joined_at from students "
            "where course_id = ? order by id",
            (course_id,),
        ).fetchall()
        return [Student(*r) for r in rows]

    def get_student(self, student_id: int) -> Student | None:
        """Fetch a single student by id, or None if no such student exists."""
        row = self.conn.execute(
            "select id, course_id, display_name, joined_at from students where id = ?",
            (student_id,),
        ).fetchone()
        return Student(*row) if row else None

    # --- Documents --------------------------------------------------------
    def add_document(
        self, course_id: str, filename: str, num_chunks: int = 0, doc_id: str | None = None
    ) -> Document:
        """Record an uploaded document for a course; returns the new record."""
        if self.get_course(course_id) is None:
            raise ValueError(f"course {course_id!r} not found")
        doc_id = doc_id or uuid.uuid4().hex
        row = self.conn.execute(
            "insert into documents(id, course_id, filename, num_chunks) values (?, ?, ?, ?) "
            "returning id, course_id, filename, num_chunks, uploaded_at",
            (doc_id, course_id, filename, num_chunks),
        ).fetchone()
        self.conn.commit()
        return Document(*row)

    def list_documents(self, course_id: str) -> list[Document]:
        rows = self.conn.execute(
            "select id, course_id, filename, num_chunks, uploaded_at from documents "
            "where course_id = ? order by uploaded_at, id",
            (course_id,),
        ).fetchall()
        return [Document(*r) for r in rows]

    # --- Quizzes ----------------------------------------------------------
    def save_quiz(
        self, course_id: str, topic: str | None, questions: Sequence[QuizQuestion]
    ) -> str:
        """Persist a generated quiz and its questions; return the new quiz id.

        Raises:
            ValueError: If the course doesn't exist.
        """
        if self.get_course(course_id) is None:
            raise ValueError(f"course {course_id!r} not found")
        quiz_id = uuid.uuid4().hex
        self.conn.execute(
            "insert into quizzes(id, course_id, topic) values (?, ?, ?)",
            (quiz_id, course_id, topic),
        )
        self.conn.executemany(
            "insert into quiz_questions"
            "(quiz_id, position, stem, options_json, correct_index, explanation) "
            "values (?, ?, ?, ?, ?, ?)",
            [
                (quiz_id, pos, q.stem, json.dumps(q.options), q.correct_index, q.explanation)
                for pos, q in enumerate(questions)
            ],
        )
        self.conn.commit()
        return quiz_id

    def get_quiz(self, quiz_id: str) -> QuizRecord | None:
        """Fetch a quiz's metadata by id, or None if it doesn't exist."""
        row = self.conn.execute(
            "select id, course_id, topic, created_at from quizzes where id = ?", (quiz_id,)
        ).fetchone()
        return QuizRecord(*row) if row else None

    def list_quiz_questions(self, quiz_id: str) -> list[QuestionRecord]:
        """Return a quiz's questions (with answer key) in presentation order."""
        rows = self.conn.execute(
            "select id, quiz_id, position, stem, options_json, correct_index, explanation "
            "from quiz_questions where quiz_id = ? order by position",
            (quiz_id,),
        ).fetchall()
        return [
            QuestionRecord(qid, qz, pos, stem, json.loads(opts), ci, expl)
            for qid, qz, pos, stem, opts, ci, expl in rows
        ]

    def record_attempt(
        self, quiz_id: str, student_id: int, score: int, total: int, answers: Sequence[int]
    ) -> Attempt:
        """Persist a student's scored attempt at a quiz; returns the record."""
        row = self.conn.execute(
            "insert into quiz_attempts(quiz_id, student_id, score, total, answers_json) "
            "values (?, ?, ?, ?, ?) "
            "returning id, quiz_id, student_id, score, total, answers_json, submitted_at",
            (quiz_id, student_id, score, total, json.dumps(list(answers))),
        ).fetchone()
        self.conn.commit()
        qid, qz, sid, sc, tot, ans_json, submitted = row
        return Attempt(qid, qz, sid, sc, tot, json.loads(ans_json), submitted)

    def list_attempts_for_student(self, student_id: int) -> list[Attempt]:
        """Return a student's quiz attempts, most recent first."""
        rows = self.conn.execute(
            "select id, quiz_id, student_id, score, total, answers_json, submitted_at "
            "from quiz_attempts where student_id = ? order by submitted_at desc, id desc",
            (student_id,),
        ).fetchall()
        return [
            Attempt(qid, qz, sid, sc, tot, json.loads(ans), sub)
            for qid, qz, sid, sc, tot, ans, sub in rows
        ]

    def close(self) -> None:
        """Close the connection unless it was injected (owned by the caller)."""
        if self._owns_conn:
            self.conn.close()
