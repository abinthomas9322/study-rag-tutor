"""HTTP routes for documents (upload + listing)."""

from fastapi import APIRouter, HTTPException, UploadFile

from app.deps import (
    DbDep,
    EmbedderDep,
    GeneratorDep,
    QuizGeneratorDep,
    SettingsDep,
    StoreDep,
)
from app.schemas import (
    AnswerOut,
    AskRequest,
    AttemptOut,
    CourseOut,
    CreateCourseRequest,
    DocumentOut,
    JoinRequest,
    QuestionResultOut,
    QuizOut,
    QuizQuestionOut,
    QuizRequest,
    SourceOut,
    StudentOut,
    SubmitAttemptRequest,
)
from app.services import answer_question, generate_quiz, ingest_pdf, submit_attempt

router = APIRouter()


@router.post("/courses", status_code=201, response_model=CourseOut, tags=["courses"])
def create_course(body: CreateCourseRequest, db: DbDep) -> CourseOut:
    """Create a new course space; 409 if the join code is already taken."""
    try:
        course = db.create_course(body.id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CourseOut.model_validate(course)


@router.get("/courses", response_model=list[CourseOut], tags=["courses"])
def list_courses(db: DbDep) -> list[CourseOut]:
    """List all course spaces."""
    return [CourseOut.model_validate(c) for c in db.list_courses()]


@router.get("/courses/{course_id}", response_model=CourseOut, tags=["courses"])
def get_course(course_id: str, db: DbDep) -> CourseOut:
    """Fetch a single course; 404 if it doesn't exist."""
    course = db.get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"course {course_id!r} not found")
    return CourseOut.model_validate(course)


@router.post(
    "/courses/{course_id}/join",
    status_code=201,
    response_model=StudentOut,
    tags=["courses"],
)
def join_course(course_id: str, body: JoinRequest, db: DbDep) -> StudentOut:
    """Join a course as a student; idempotent. 404 if the course is unknown."""
    try:
        student = db.join_course(course_id, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StudentOut.model_validate(student)


@router.get("/courses/{course_id}/students", response_model=list[StudentOut], tags=["courses"])
def list_students(course_id: str, db: DbDep) -> list[StudentOut]:
    """List the students enrolled in a course."""
    return [StudentOut.model_validate(s) for s in db.list_students(course_id)]


@router.post(
    "/courses/{course_id}/documents",
    status_code=201,
    response_model=DocumentOut,
    tags=["documents"],
)
async def upload_document(
    course_id: str,
    file: UploadFile,
    db: DbDep,
    store: StoreDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
) -> DocumentOut:
    """Upload a PDF into a course; it is chunked, embedded, and indexed."""
    name = file.filename or "upload.pdf"
    is_pdf = (file.content_type or "") == "application/pdf" or name.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="only PDF files are supported")

    data = await file.read()
    try:
        doc = ingest_pdf(
            data,
            course_id=course_id,
            filename=name,
            db=db,
            store=store,
            embedder=embedder,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentOut.model_validate(doc)


@router.get(
    "/courses/{course_id}/documents",
    response_model=list[DocumentOut],
    tags=["documents"],
)
def list_documents(course_id: str, db: DbDep) -> list[DocumentOut]:
    """List the documents uploaded to a course."""
    return [DocumentOut.model_validate(d) for d in db.list_documents(course_id)]


@router.post(
    "/courses/{course_id}/ask",
    response_model=AnswerOut,
    tags=["qa"],
)
def ask(
    course_id: str,
    body: AskRequest,
    store: StoreDep,
    embedder: EmbedderDep,
    generator: GeneratorDep,
    settings: SettingsDep,
) -> AnswerOut:
    """Answer a question grounded in the course's materials, with citations."""
    result = answer_question(
        body.question,
        course_id,
        store=store,
        embedder=embedder,
        generator=generator,
        settings=settings,
    )
    sources = [
        SourceOut(document_id=h.document_id, text=h.text, distance=h.distance)
        for h in result.sources
    ]
    return AnswerOut(answer=result.text, sources=sources)


@router.post(
    "/courses/{course_id}/quiz",
    response_model=QuizOut,
    tags=["quiz"],
)
def quiz(
    course_id: str,
    body: QuizRequest,
    db: DbDep,
    store: StoreDep,
    embedder: EmbedderDep,
    quiz_generator: QuizGeneratorDep,
    settings: SettingsDep,
) -> QuizOut:
    """Generate a practice quiz grounded in a course's materials.

    With a ``topic`` the quiz focuses on the most relevant chunks; without one
    it samples broadly across the course. The quiz is persisted (with its answer
    key) and a ``quiz_id`` is returned so it can be taken and scored; the correct
    answers are not included here. Returns an empty quiz (null id) when the
    course has no materials; 502 if the model returns an unusable response.
    """
    try:
        quiz_id, result = generate_quiz(
            course_id,
            num_questions=body.num_questions,
            topic=body.topic,
            db=db,
            store=store,
            embedder=embedder,
            generator=quiz_generator,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    sources = [
        SourceOut(document_id=h.document_id, text=h.text, distance=h.distance)
        for h in result.sources
    ]
    questions = [QuizQuestionOut(stem=q.stem, options=q.options) for q in result.questions]
    return QuizOut(id=quiz_id, questions=questions, sources=sources)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts",
    status_code=201,
    response_model=AttemptOut,
    tags=["quiz"],
)
def submit_quiz_attempt(
    course_id: str,
    quiz_id: str,
    body: SubmitAttemptRequest,
    db: DbDep,
) -> AttemptOut:
    """Submit answers for a quiz; score them and store the attempt.

    Returns the score plus per-question feedback (revealing the correct answer
    and explanation). 404 if the quiz or student isn't part of the course; 422
    if the number of answers doesn't match the number of questions.
    """
    try:
        attempt, questions = submit_attempt(
            course_id,
            quiz_id,
            student_id=body.student_id,
            answers=body.answers,
            db=db,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    results = [
        QuestionResultOut(
            stem=q.stem,
            options=q.options,
            your_answer=attempt.answers[i],
            correct_index=q.correct_index,
            is_correct=attempt.answers[i] == q.correct_index,
            explanation=q.explanation,
        )
        for i, q in enumerate(questions)
    ]
    return AttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        student_id=attempt.student_id,
        score=attempt.score,
        total=attempt.total,
        submitted_at=attempt.submitted_at,
        results=results,
    )
