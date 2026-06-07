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
    """One quiz question as shown to a student taking it (no answer key)."""

    stem: str
    options: list[str]


class QuizOut(BaseModel):
    """A generated quiz: its id, its questions, and the sources behind them.

    ``id`` is null when the course has no materials and no quiz was created.
    The correct answers are deliberately omitted here — they're revealed only
    after the student submits an attempt.
    """

    id: str | None
    questions: list[QuizQuestionOut]
    sources: list[SourceOut]


class SubmitAttemptRequest(BaseModel):
    """A student's submitted answers for a quiz (one option index per question)."""

    student_id: int = Field(ge=1, description="The enrolled student's id")
    answers: list[int] = Field(min_length=1, description="Chosen option index per question")


class QuestionResultOut(BaseModel):
    """Per-question feedback after an attempt, including the correct answer."""

    stem: str
    options: list[str]
    your_answer: int
    correct_index: int
    is_correct: bool
    explanation: str


class AttemptOut(BaseModel):
    """A scored quiz attempt plus per-question feedback."""

    id: int
    quiz_id: str
    student_id: int
    score: int
    total: int
    submitted_at: str
    results: list[QuestionResultOut]
