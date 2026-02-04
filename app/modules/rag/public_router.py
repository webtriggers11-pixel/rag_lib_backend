import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import DEBUG, QUESTION_MAX_LENGTH
from app.modules.orgs.orgs_service import get_org
from app.services.api_keys_service import get_org_id_by_key
from app.services.rag import query_rag

logger = logging.getLogger("app")
router = APIRouter(prefix="/rag", tags=["rag-public"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=QUESTION_MAX_LENGTH)


class QueryResponse(BaseModel):
    answer: str


async def get_org_id_from_api_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )
    org_id = await get_org_id_by_key(api_key.strip())
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    if await get_org(org_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    return org_id


@router.post("/query", response_model=QueryResponse)
async def query_with_api_key(
    req: QueryRequest,
    org_id: str = Depends(get_org_id_from_api_key),
):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        answer = await asyncio.to_thread(
            query_rag,
            question,
            4,
            {"org_id": org_id},
        )
        logger.info(
            "query api_key org_id=%s question_len=%d",
            org_id, len(question),
            extra={"event": "query_api_key", "org_id": org_id, "question_len": len(question)},
        )
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.exception(
            "query api_key org_id=%s error=%s",
            org_id, e,
            extra={"event": "query_api_key_error", "org_id": org_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail=str(e) if DEBUG else "Query failed. Please try again.",
        )
