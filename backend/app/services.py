"""Application services that compose the rag core with the relational store."""

import io
import uuid

from app.db import Database, Document
from rag.chunking import chunk_text
from rag.config import Settings
from rag.embeddings import Embedder
from rag.pdf import extract_text
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
