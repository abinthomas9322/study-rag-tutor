"""Typed application configuration, loaded from environment variables / .env.

Centralises every tunable knob so the rest of the code never reads os.environ
directly. Values can be overridden per-environment without touching code.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the RAG tutor backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM (Groq, via its OpenAI-compatible API) ---
    groq_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"

    # --- Embeddings (fastembed: ONNX, CPU, light on memory) ---
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Chunking (characters per chunk and overlap between them) ---
    chunk_size: int = 800
    chunk_overlap: int = 120

    # --- Retrieval (passages returned per question) ---
    top_k: int = 4
    # "hybrid" fuses BM25 keyword search with vector search (Reciprocal Rank
    # Fusion); "vector" is embeddings only. Measured on eval/golden_set.jsonl:
    # hybrid Hit@4 88.0% vs vector 86.0% — see eval/run.py.
    retrieval_mode: Literal["vector", "hybrid"] = "hybrid"

    # --- Reranking (cross-encoder re-orders the first-stage candidates) ---
    # Measured on eval/golden_set.jsonl: hybrid+rerank Hit@4 98.0% vs 88.0%
    # without, at ~0.5 s extra per question. Adds an ~80 MB model in memory;
    # set RERANK=false on very small hosts.
    rerank: bool = True
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    rerank_candidates: int = 20

    # --- Storage (SQLite file holds both relational data and vectors) ---
    db_path: str = "backend/tutor.db"

    # --- CORS (comma-separated origins; "*" allows any — fine for a public demo) ---
    cors_origins: str = "*"


def get_settings() -> Settings:
    """Build a Settings instance, reading the environment at call time."""
    return Settings()
