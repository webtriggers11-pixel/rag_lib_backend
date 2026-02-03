import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import DEBUG, ORG_NAME_MAX_LENGTH
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.orgs.orgs_service import DuplicateOrgNameError, create_org, get_org

logger = logging.getLogger("app")
router = APIRouter(prefix="/orgs", tags=["orgs"])


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


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=ORG_NAME_MAX_LENGTH)


@router.post("", response_model=dict)
def create_org_route(req: CreateOrgRequest, current_user: dict = Depends(require_admin)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        org = create_org(name)
        logger.info(
            "org_created id=%s name=%s",
            org["id"], name,
            extra={"event": "org_created", "org_id": org["id"], "org_name": name},
        )
        return org
    except DuplicateOrgNameError:
        raise HTTPException(status_code=409, detail="Organization name already exists")
    except Exception as e:
        logger.exception(
            "org_create name=%s error=%s",
            name, e,
            extra={"event": "org_create_error", "org_name": name, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail=str(e) if DEBUG else "Failed to create org. Please try again.",
        )


@router.get("/{org_id}", response_model=dict)
def get_org_route(org_id: str, current_user: dict = Depends(get_current_user)):
    _validate_org_id(org_id)
    _require_org_access(org_id, current_user)
    org = get_org(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    return org
