import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
from jose import JWTError, jwt
from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor

from app.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
    get_connection_string,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_user(email: str, password: str, role: str, org_id: str | None = None) -> dict:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            user_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO users (id, email, password_hash, role, org_id)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id, email, role, org_id, created_at""",
                (user_id, email.lower().strip(), hash_password(password), role, org_id),
            )
            row = cur.fetchone()
            conn.commit()
            return _user_row_to_dict(row)
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, password_hash, role, org_id, created_at FROM users WHERE email = %s",
                (email.lower().strip(),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return _user_row_to_dict(row, include_hash=True)
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, password_hash, role, org_id, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return _user_row_to_dict(row)
    finally:
        conn.close()


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
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def count_users() -> int:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]
    finally:
        conn.close()
