from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.rag import ingest_pdf_into_store, query_rag

router = APIRouter(prefix="/rag", tags=["rag"])


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


class UploadResponse(BaseModel):
    message: str
    chunks_stored: int


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        meta = {"filename": str(file.filename)} if file.filename else {}
        count = ingest_pdf_into_store(contents, metadata=meta)
        return UploadResponse(
            message="PDF ingested successfully",
            chunks_stored=count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def ask_question(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        answer = query_rag(req.question)
        return QueryResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
