from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.modules.auth.dependencies import require_admin
from app.modules.orgs.orgs_service import get_org, list_orgs, set_org_prompt
from app.services.api_keys_service import ApiKeyLimitError, create_api_key, list_api_keys
from app.services.rag import get_rag_prompt_async
from app.services.uploads_service import count_uploads_by_org, list_uploads

router = APIRouter(prefix="/admin", tags=["admin"])


class SetOrgPromptRequest(BaseModel):
    content: str | None = None


@router.get("/dashboard")
async def admin_dashboard(current_user: dict = Depends(require_admin)):
    """Admin: list all orgs with upload count."""
    orgs = await list_orgs()
    for org in orgs:
        org["upload_count"] = await count_uploads_by_org(org["id"])
    return {"orgs": orgs}


@router.get("/orgs")
async def admin_list_orgs(current_user: dict = Depends(require_admin)):
    """Admin: list all orgs."""
    return {"orgs": await list_orgs()}


@router.get("/orgs/{org_id}")
async def admin_get_org(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: get org detail and its uploads."""
    org = await get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    uploads = await list_uploads(org_id)
    org["uploads"] = uploads
    org["upload_count"] = len(uploads)
    return org


@router.get("/prompt")
async def admin_get_default_prompt(current_user: dict = Depends(require_admin)):
    """Admin: get default RAG prompt."""
    return {"content": await get_rag_prompt_async()}


@router.put("/orgs/{org_id}/prompt")
async def admin_set_org_prompt(org_id: str, req: SetOrgPromptRequest, current_user: dict = Depends(require_admin)):
    """Admin: set custom prompt for org (from outside)."""
    org = await get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    await set_org_prompt(org_id, req.content)
    return {"ok": True}


@router.post("/orgs/{org_id}/api-keys")
async def admin_create_api_key(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: create API key for org. Returns plain key once; store it securely. Max 3 per org."""
    org = await get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    try:
        plain_key, prefix, created_at = await create_api_key(org_id)
        return {"api_key": plain_key, "key_prefix": prefix, "created_at": created_at}
    except ApiKeyLimitError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orgs/{org_id}/api-keys")
async def admin_list_api_keys(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: list API keys for org (prefix and date only; full key is never returned)."""
    org = await get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return {"api_keys": await list_api_keys(org_id)}
