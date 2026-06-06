"""Pydantic response schemas for the API."""

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Public view of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    filename: str
    num_chunks: int
    uploaded_at: str
