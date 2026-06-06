"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    """Public view of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    filename: str
    num_chunks: int
    uploaded_at: str


class AskRequest(BaseModel):
    """A student's question about a course's materials."""

    question: str = Field(min_length=1, description="The question to answer")


class SourceOut(BaseModel):
    """One retrieved chunk cited in an answer."""

    document_id: str
    text: str
    distance: float


class AnswerOut(BaseModel):
    """A grounded answer plus the sources it cited."""

    answer: str
    sources: list[SourceOut]
