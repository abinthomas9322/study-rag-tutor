"""Application services that compose the rag core with the relational store."""

import io
import uuid

from app.db import Attempt, Database, Document, QuestionRecord
from rag.answer import Answer, AnswerGenerator
from rag.chunking import chunk_text
from rag.config import Settings
from rag.embeddings import Embedder
from rag.pdf import extract_text
from rag.quiz import Quiz, QuizGenerator, score_quiz
from rag.store import VectorStore


def ingest_pdf(
    data: bytes,
    *,
    course_id: str,
    filename: str,
    db: Database,
    store: VectorStore,
    embedder: Embedder,
    settings: Settings,
) -> Document:
    """Ingest one uploaded PDF into a course's shared knowledge base.

    Extracts text, chunks it, embeds the chunks, stores the vectors, and
    records the document. The course is auto-created on first upload.

    Raises:
        ValueError: If the PDF has no extractable text (e.g. a scanned image).
    """
    if db.get_course(course_id) is None:
        db.create_course(course_id, name=course_id)

    text = extract_text(io.BytesIO(data))
    chunks = chunk_text(text, size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        raise ValueError("no extractable text found in the PDF")

    vectors = embedder.embed(chunks)
    doc_id = uuid.uuid4().hex
    # Store vectors first; the document row is the last write, so a failure
    # mid-embedding never leaves a document recorded without its chunks.
    store.add(course_id, doc_id, chunks, vectors)
    return db.add_document(course_id, filename, num_chunks=len(chunks), doc_id=doc_id)


def answer_question(
    question: str,
    course_id: str,
    *,
    store: VectorStore,
    embedder: Embedder,
    generator: AnswerGenerator,
    settings: Settings,
) -> Answer:
    """Answer a question grounded in a course's indexed materials.

    Embeds the question, retrieves the top-k most relevant chunks for that
    course, and asks the LLM to answer using only those chunks.
    """
    query_vector = embedder.embed_query(question)
    hits = store.search(course_id, query_vector, k=settings.top_k)
    return generator.generate(question, hits)


def generate_quiz(
    course_id: str,
    *,
    num_questions: int,
    topic: str | None,
    db: Database,
    store: VectorStore,
    embedder: Embedder,
    generator: QuizGenerator,
    settings: Settings,
) -> tuple[str | None, Quiz]:
    """Generate a grounded quiz and persist it; return ``(quiz_id, quiz)``.

    With a ``topic`` we retrieve the chunks most relevant to it (focused quiz);
    without one we sample evenly across the course (broad quiz). Either way the
    questions are written only from the retrieved chunks. The quiz — including
    its answer key — is stored so attempts can be scored server-side; an empty
    quiz (course has no materials) is not persisted and yields ``(None, quiz)``.
    """
    if topic:
        query_vector = embedder.embed_query(topic)
        hits = store.search(course_id, query_vector, k=settings.top_k)
    else:
        hits = store.sample(course_id, n=settings.top_k)
    quiz = generator.generate(num_questions, hits, topic=topic)
    if not quiz.questions:
        return None, quiz
    quiz_id = db.save_quiz(course_id, topic, quiz.questions)
    return quiz_id, quiz


def submit_attempt(
    course_id: str,
    quiz_id: str,
    *,
    student_id: int,
    answers: list[int],
    db: Database,
) -> tuple[Attempt, list[QuestionRecord]]:
    """Score and store a student's attempt; return the attempt and questions.

    The questions are returned so the caller can build per-question feedback
    (the correct answers are only revealed here, after submission).

    Raises:
        LookupError: If the quiz isn't found in this course, or the student is
            not enrolled in it.
        ValueError: If the number of answers doesn't match the question count.
    """
    quiz = db.get_quiz(quiz_id)
    if quiz is None or quiz.course_id != course_id:
        raise LookupError(f"quiz {quiz_id!r} not found in course {course_id!r}")
    student = db.get_student(student_id)
    if student is None or student.course_id != course_id:
        raise LookupError(f"student {student_id} is not enrolled in course {course_id!r}")

    questions = db.list_quiz_questions(quiz_id)
    result = score_quiz([q.correct_index for q in questions], answers)
    attempt = db.record_attempt(
        quiz_id, student_id, score=result.score, total=result.total, answers=answers
    )
    return attempt, questions
