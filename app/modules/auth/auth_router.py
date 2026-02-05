import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.config import ORG_NAME_MAX_LENGTH
from app.modules.auth.auth_service import (
    count_users,
    create_access_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    verify_password,
)
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.orgs.orgs_service import DuplicateOrgNameError, create_org

logger = logging.getLogger("app")
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=ORG_NAME_MAX_LENGTH)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register first user as admin. Only allowed when no users exist."""
    if await count_users() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration closed. Only admin can register new orgs.",
        )
    if await get_user_by_email(req.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await create_user(req.email, req.password, role="admin", org_id=None)
    token = create_access_token({"sub": user["id"], "role": "admin"})
    logger.info("admin_registered email=%s", req.email, extra={"event": "admin_registered", "email": req.email})
    return TokenResponse(access_token=token, user=user)


@router.post("/register-org", response_model=TokenResponse)
async def register_org(req: RegisterOrgRequest, current_user: dict = Depends(require_admin)):
    """Admin only: create org and register org user (email+password)."""
    if await get_user_by_email(req.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    try:
        org = await create_org(req.name.strip())
    except DuplicateOrgNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")
    user = await create_user(req.email, req.password, role="org", org_id=org["id"])
    token = create_access_token({"sub": user["id"], "role": "org", "org_id": org["id"]})
    logger.info(
        "org_registered org_id=%s email=%s",
        org["id"], req.email,
        extra={"event": "org_registered", "org_id": org["id"], "email": req.email},
    )
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    password_hash = user.get("password_hash") or ""
    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    u = await get_user_by_id(user["id"])
    if u is None:
        u = {k: v for k, v in user.items() if k != "password_hash"}
    token = create_access_token({"sub": user["id"], "role": user["role"], "org_id": user.get("org_id")})
    return TokenResponse(access_token=token, user=u)


@router.get("/me", response_model=dict)
async def me(current_user: dict = Depends(get_current_user)):
    return {k: v for k, v in current_user.items() if k != "password_hash"}
