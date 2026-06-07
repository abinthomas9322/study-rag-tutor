"""Seed a demo course with real, open-licensed OpenStax Biology content.

This is explicitly labelled example/seed data (see ``seed/data/SOURCE.md`` for
the source and licence). It ingests the committed demo PDF(s) into a ``BIO101``
course so the whole app can be run end-to-end against genuine material — not
fabricated data. The text comes verbatim from the source PDF; nothing here is
invented.

Run from the ``backend`` directory::

    python -m seed.seed_demo
"""

from pathlib import Path

from app.db import Database
from app.services import ingest_pdf
from rag.config import get_settings
from rag.embeddings import Embedder
from rag.store import DEFAULT_DIM, VectorStore, connect

COURSE_ID = "BIO101"
COURSE_NAME = "Biology 101 — OpenStax Concepts of Biology"
DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    """Create the BIO101 course (if needed) and ingest every demo PDF."""
    settings = get_settings()
    conn = connect(settings.db_path)
    db = Database(connection=conn)
    store = VectorStore(connection=conn, dim=DEFAULT_DIM)
    embedder = Embedder(settings.embed_model)

    if db.get_course(COURSE_ID) is None:
        db.create_course(COURSE_ID, COURSE_NAME)
        print(f"created course {COURSE_ID}")

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no demo PDFs found in {DATA_DIR} — run the extraction step first")

    existing = {d.filename for d in db.list_documents(COURSE_ID)}
    for pdf in pdfs:
        if pdf.name in existing:
            print(f"skipping {pdf.name} (already ingested)")
            continue
        doc = ingest_pdf(
            pdf.read_bytes(),
            course_id=COURSE_ID,
            filename=pdf.name,
            db=db,
            store=store,
            embedder=embedder,
            settings=settings,
        )
        print(f"ingested {pdf.name}: {doc.num_chunks} chunks")

    print(f"done — {COURSE_ID} has {store.count(COURSE_ID)} chunks total")
    conn.close()


if __name__ == "__main__":
    main()
