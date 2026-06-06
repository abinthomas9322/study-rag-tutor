"""Typed application configuration, loaded from environment variables / .env.

Centralises every tunable knob so the rest of the code never reads os.environ
directly. Values can be overridden per-environment without touching code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the RAG tutor backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM (Groq, via its OpenAI-compatible API) ---
    groq_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    # --- Embeddings (fastembed: ONNX, CPU, light on memory) ---
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Chunking (characters per chunk and overlap between them) ---
    chunk_size: int = 800
    chunk_overlap: int = 120

    # --- Retrieval (passages returned per question) ---
    top_k: int = 4

    # --- Storage (SQLite file holds both relational data and vectors) ---
    db_path: str = "backend/tutor.db"


def get_settings() -> Settings:
    """Build a Settings instance, reading the environment at call time."""
    return Settings()
