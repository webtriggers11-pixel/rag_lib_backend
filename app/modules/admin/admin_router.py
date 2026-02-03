from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.modules.auth.dependencies import require_admin
from app.modules.orgs.orgs_service import get_org, list_orgs, set_org_prompt
from app.services.api_keys_service import ApiKeyLimitError, create_api_key, list_api_keys
from app.services.rag import get_rag_prompt
from app.services.uploads_service import count_uploads_by_org, list_uploads

router = APIRouter(prefix="/admin", tags=["admin"])


class SetOrgPromptRequest(BaseModel):
    content: str | None = None


@router.get("/dashboard")
def admin_dashboard(current_user: dict = Depends(require_admin)):
    """Admin: list all orgs with upload count."""
    orgs = list_orgs()
    for org in orgs:
        org["upload_count"] = count_uploads_by_org(org["id"])
    return {"orgs": orgs}


@router.get("/orgs")
def admin_list_orgs(current_user: dict = Depends(require_admin)):
    """Admin: list all orgs."""
    return {"orgs": list_orgs()}


@router.get("/orgs/{org_id}")
def admin_get_org(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: get org detail and its uploads."""
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    uploads = list_uploads(org_id)
    org["uploads"] = uploads
    org["upload_count"] = len(uploads)
    return org


@router.get("/prompt")
def admin_get_default_prompt(current_user: dict = Depends(require_admin)):
    """Admin: get default RAG prompt."""
    return {"content": get_rag_prompt()}


@router.put("/orgs/{org_id}/prompt")
def admin_set_org_prompt(org_id: str, req: SetOrgPromptRequest, current_user: dict = Depends(require_admin)):
    """Admin: set custom prompt for org (from outside)."""
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    set_org_prompt(org_id, req.content)
    return {"ok": True}


@router.post("/orgs/{org_id}/api-keys")
def admin_create_api_key(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: create API key for org. Returns plain key once; store it securely. Max 3 per org."""
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    try:
        plain_key, prefix, created_at = create_api_key(org_id)
        return {"api_key": plain_key, "key_prefix": prefix, "created_at": created_at}
    except ApiKeyLimitError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orgs/{org_id}/api-keys")
def admin_list_api_keys(org_id: str, current_user: dict = Depends(require_admin)):
    """Admin: list API keys for org (prefix and date only; full key is never returned)."""
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return {"api_keys": list_api_keys(org_id)}
