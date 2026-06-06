"""FastAPI application factory for the Study-Group RAG Tutor backend.

A factory (rather than a module-level app only) lets tests build a fresh,
isolated application instance whenever they need one. A module-level ``app``
is also exposed for the ASGI server (``uvicorn app.main:app``).
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Study-Group RAG Tutor",
        version="0.1.0",
        description="Shared, course-scoped RAG study assistant.",
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness probe — returns ok when the service is up."""
        return {"status": "ok"}

    return app


app = create_app()
