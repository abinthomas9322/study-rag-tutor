"""Relational data access for courses, students, and documents on SQLite.

Shares a single connection with the vector store (see :func:`rag.store.connect`)
so the entire application lives in one SQLite file and a document plus its
chunks can be written under one connection. Raw SQL keeps the dependency
footprint small; an ORM would not earn its place here.
"""

import sqlite3
import uuid
from dataclasses import dataclass

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

    def close(self) -> None:
        """Close the connection unless it was injected (owned by the caller)."""
        if self._owns_conn:
            self.conn.close()
