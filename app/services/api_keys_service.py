import hashlib
import secrets
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import get_connection_string


MAX_API_KEYS_PER_ORG = 3


class ApiKeyLimitError(Exception):
    pass


def _hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def count_api_keys(org_id: str) -> int:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS n FROM org_api_keys WHERE org_id = %s", (org_id,))
            row = cur.fetchone()
            return int(row["n"]) if row else 0
    finally:
        conn.close()


def create_api_key(org_id: str) -> tuple[str, str, str]:
    if count_api_keys(org_id) >= MAX_API_KEYS_PER_ORG:
        raise ApiKeyLimitError(f"Maximum {MAX_API_KEYS_PER_ORG} API keys per org. Delete one to create another.")
    plain = "rag_" + secrets.token_urlsafe(32)
    key_hash = _hash_key(plain)
    prefix = plain[:12] + "..."
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO org_api_keys (id, org_id, key_hash, key_prefix, created_at) VALUES (%s, %s, %s, %s, now()) RETURNING id, created_at",
                (str(uuid.uuid4()), org_id, key_hash, prefix),
            )
            row = cur.fetchone()
            conn.commit()
            created_at = row["created_at"].isoformat() if row.get("created_at") else None
            return plain, prefix, created_at
    finally:
        conn.close()


def get_org_id_by_key(plain_key: str) -> str | None:
    if not plain_key or not plain_key.strip():
        return None
    key_hash = _hash_key(plain_key.strip())
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT org_id FROM org_api_keys WHERE key_hash = %s", (key_hash,))
            row = cur.fetchone()
            return str(row["org_id"]) if row else None
    finally:
        conn.close()


def list_api_keys(org_id: str) -> list[dict]:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, key_prefix, created_at FROM org_api_keys WHERE org_id = %s ORDER BY created_at DESC",
                (org_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "key_prefix": r["key_prefix"],
                    "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                }
                for r in rows
            ]
    finally:
        conn.close()
