from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.dependencies import get_current_user
from app.modules.orgs.orgs_service import get_org
from app.services.api_keys_service import ApiKeyLimitError, create_api_key, list_api_keys
from app.services.uploads_service import list_uploads

router = APIRouter(prefix="/org", tags=["dashboard"])


@router.get("/dashboard")
def org_dashboard(current_user: dict = Depends(get_current_user)):
    """Org user: get own org info and uploads. Admin cannot use this for org view; use /admin/orgs/{id}."""
    if current_user.get("role") != "org":
        raise HTTPException(status_code=403, detail="Org dashboard is for org users only")
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="No org assigned")
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    uploads = list_uploads(org_id)
    return {"org": org, "uploads": uploads}


@router.post("/api-keys")
def org_create_api_key(current_user: dict = Depends(get_current_user)):
    """Org user: create API key for own org. Returns plain key once. Max 3 per org."""
    if current_user.get("role") != "org":
        raise HTTPException(status_code=403, detail="Org users only")
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="No org assigned")
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    try:
        plain_key, prefix, created_at = create_api_key(org_id)
        return {"api_key": plain_key, "key_prefix": prefix, "created_at": created_at}
    except ApiKeyLimitError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys")
def org_list_api_keys(current_user: dict = Depends(get_current_user)):
    """Org user: list API keys for own org (prefix and date only)."""
    if current_user.get("role") != "org":
        raise HTTPException(status_code=403, detail="Org users only")
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="No org assigned")
    org = get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return {"api_keys": list_api_keys(org_id)}
