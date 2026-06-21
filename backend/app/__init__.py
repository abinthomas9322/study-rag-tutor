"""FastAPI application layer: HTTP endpoints over the rag core engine."""

# Single source of truth for the API's reported version, surfaced by /health
# and used as the OpenAPI ``info.version``. Kept in sync with ``pyproject.toml``
# by hand — bumping is a 1-line edit across the two files.
__version__ = "0.1.0"
