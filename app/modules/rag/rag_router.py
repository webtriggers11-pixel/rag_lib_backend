import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import DEBUG, MAX_UPLOAD_SIZE_MB, QUESTION_MAX_LENGTH
from app.modules.auth.dependencies import get_current_user
from app.modules.orgs.orgs_service import get_org
from app.services.rag import ingest_pdf_into_store, query_rag
from app.services.uploads_service import record_upload

logger = logging.getLogger("app")
router = APIRouter(prefix="/orgs/{org_id}/rag", tags=["rag"])
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _require_org_access(org_id: str, current_user: dict) -> None:
    if current_user.get("role") == "admin":
        return
    if current_user.get("org_id") != org_id:
        raise HTTPException(status_code=403, detail="Access denied to this org")


def _validate_org_id(org_id: str) -> None:
    try:
        uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid org_id format")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=QUESTION_MAX_LENGTH)


class QueryResponse(BaseModel):
    answer: str


class UploadResponse(BaseModel):
    message: str
    chunks_stored: int


def _ensure_org(org_id: str) -> None:
    _validate_org_id(org_id)
    if get_org(org_id) is None:
        raise HTTPException(status_code=404, detail="Org not found")


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(org_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    _require_org_access(org_id, current_user)
    _ensure_org(org_id)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB} MB",
        )
    try:
        meta = {"filename": str(file.filename)} if file.filename else {}
        count = ingest_pdf_into_store(contents, metadata=meta, org_id=org_id)
        record_upload(org_id, file.filename or "document.pdf")
        logger.info(
            "upload org_id=%s filename=%s chunks_stored=%d size_bytes=%d",
            org_id, file.filename, count, len(contents),
            extra={"event": "upload", "org_id": org_id, "upload_filename": file.filename, "chunks_stored": count, "size_bytes": len(contents)},
        )
        return UploadResponse(
            message="PDF ingested successfully",
            chunks_stored=count,
        )
    except ValueError as e:
        logger.warning(
            "upload org_id=%s filename=%s error=%s",
            org_id, file.filename, e,
            extra={"event": "upload_error", "org_id": org_id, "upload_filename": file.filename, "error": str(e)},
        )
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(
            "upload org_id=%s filename=%s error=%s",
            org_id, file.filename, e,
            extra={"event": "upload_error", "org_id": org_id, "upload_filename": file.filename, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail=str(e) if DEBUG else "Upload failed. Please try again.",
        )


@router.post("/query", response_model=QueryResponse)
async def ask_question(org_id: str, req: QueryRequest, current_user: dict = Depends(get_current_user)):
    _require_org_access(org_id, current_user)
    _ensure_org(org_id)
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        answer = query_rag(
            question,
            filter_metadata={"org_id": org_id},
        )
        logger.info(
            "query org_id=%s question_len=%d",
            org_id, len(question),
            extra={"event": "query", "org_id": org_id, "question_len": len(question)},
        )
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.exception(
            "query org_id=%s error=%s",
            org_id, e,
            extra={"event": "query_error", "org_id": org_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail=str(e) if DEBUG else "Query failed. Please try again.",
        )
