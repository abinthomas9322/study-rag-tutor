"""FastAPI dependencies that expose the shared app-state services to routes."""

from typing import Annotated

from fastapi import Depends, Request

from app.db import Database
from rag.answer import AnswerGenerator
from rag.config import Settings
from rag.embeddings import Embedder
from rag.store import VectorStore


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_store(request: Request) -> VectorStore:
    return request.app.state.store


def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


def get_generator(request: Request) -> AnswerGenerator:
    return request.app.state.generator


def get_settings_state(request: Request) -> Settings:
    return request.app.state.settings


# Annotated aliases keep route signatures clean and avoid the B008 "call in
# default" pattern that the bare `= Depends(...)` form trips.
DbDep = Annotated[Database, Depends(get_db)]
StoreDep = Annotated[VectorStore, Depends(get_store)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
GeneratorDep = Annotated[AnswerGenerator, Depends(get_generator)]
SettingsDep = Annotated[Settings, Depends(get_settings_state)]
