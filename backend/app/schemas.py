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


class CreateCourseRequest(BaseModel):
    """Payload to create a new course space."""

    id: str = Field(min_length=1, max_length=64, description="Course join code, e.g. CS101")
    name: str = Field(min_length=1, max_length=200, description="Human-readable course name")


class CourseOut(BaseModel):
    """Public view of a course."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: str


class JoinRequest(BaseModel):
    """Payload for a student joining a course."""

    display_name: str = Field(min_length=1, max_length=80)


class StudentOut(BaseModel):
    """Public view of an enrolled student."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: str
    display_name: str
    joined_at: str


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


class QuizRequest(BaseModel):
    """A request to generate a practice quiz from a course's materials."""

    topic: str | None = Field(
        default=None,
        max_length=200,
        description="Optional topic to focus the quiz on; omit for a broad quiz",
    )
    num_questions: int = Field(
        default=5, ge=1, le=10, description="How many questions to generate (1–10)"
    )


class QuizQuestionOut(BaseModel):
    """One generated multiple-choice question."""

    stem: str
    options: list[str]
    correct_index: int
    explanation: str


class QuizOut(BaseModel):
    """A generated quiz plus the sources its questions were grounded in."""

    questions: list[QuizQuestionOut]
    sources: list[SourceOut]
