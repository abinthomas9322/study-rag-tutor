"""FastAPI application factory for the Study-Group RAG Tutor backend.

The factory wires up the shared services — one SQLite connection used by both
the relational Database and the sqlite-vec VectorStore, plus a lazy Embedder —
and stores them on app.state for dependency injection. Tests can inject their
own db/store/embedder; production builds them from settings.

Run with: ``uvicorn app.main:create_app --factory``. There is deliberately no
module-level app instance, so importing this module has no side effects (it
won't open a database).
"""

from fastapi import FastAPI

from app.db import Database
from app.routes import router
from rag.answer import AnswerGenerator
from rag.config import Settings, get_settings
from rag.embeddings import Embedder
from rag.quiz import QuizGenerator
from rag.store import DEFAULT_DIM, VectorStore, connect


def create_app(
    *,
    db: Database | None = None,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    generator: AnswerGenerator | None = None,
    quiz_generator: QuizGenerator | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application.

    Pass ``db`` and ``store`` together (sharing one connection) to inject test
    doubles; otherwise both are built from settings on a shared connection.
    """
    settings = settings or get_settings()

    if db is None and store is None:
        conn = connect(settings.db_path)
        db = Database(connection=conn)
        store = VectorStore(connection=conn, dim=DEFAULT_DIM)
    elif db is None or store is None:
        raise ValueError("provide both db and store (sharing a connection), or neither")

    embedder = embedder or Embedder(settings.embed_model)
    generator = generator or AnswerGenerator(settings=settings)
    quiz_generator = quiz_generator or QuizGenerator(settings=settings)

    app = FastAPI(
        title="Study-Group RAG Tutor",
        version="0.1.0",
        description="Shared, course-scoped RAG study assistant.",
    )
    app.state.db = db
    app.state.store = store
    app.state.embedder = embedder
    app.state.generator = generator
    app.state.quiz_generator = quiz_generator
    app.state.settings = settings

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness probe — returns ok when the service is up."""
        return {"status": "ok"}

    app.include_router(router)
    return app
