import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
)
from app.db import get_pool

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def create_user(email: str, password: str, role: str, org_id: str | None = None) -> dict:
    pool = await get_pool()
    user_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO users (id, email, password_hash, role, org_id)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id, email, role, org_id, created_at""",
            user_id, email.lower().strip(), hash_password(password), role, org_id,
        )
        return _user_row_to_dict(dict(row))


async def get_user_by_email(email: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, role, org_id, created_at FROM users WHERE email = $1",
            email.lower().strip(),
        )
        if not row:
            return None
        return _user_row_to_dict(dict(row), include_hash=True)


async def get_user_by_id(user_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, role, org_id, created_at FROM users WHERE id = $1",
            user_id,
        )
        if not row:
            return None
        return _user_row_to_dict(dict(row))


def _user_row_to_dict(row: dict, include_hash: bool = False) -> dict:
    out = {
        "id": str(row["id"]),
        "email": row["email"],
        "role": row["role"],
        "org_id": str(row["org_id"]) if row.get("org_id") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if include_hash:
        out["password_hash"] = row["password_hash"]
    return out


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def count_users() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS n FROM users")
        return row["n"] if row else 0
