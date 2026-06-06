"""HTTP routes for documents (upload + listing)."""

from fastapi import APIRouter, HTTPException, UploadFile

from app.deps import DbDep, EmbedderDep, SettingsDep, StoreDep
from app.schemas import DocumentOut
from app.services import ingest_pdf

router = APIRouter()


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
