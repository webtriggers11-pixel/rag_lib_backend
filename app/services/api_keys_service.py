import hashlib
import secrets
import uuid

from app.db import get_pool


MAX_API_KEYS_PER_ORG = 1


class ApiKeyLimitError(Exception):
    pass


def _hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


async def revoke_all_api_keys(org_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM org_api_keys WHERE org_id = $1", org_id)


async def count_api_keys(org_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS n FROM org_api_keys WHERE org_id = $1", org_id)
        return int(row["n"]) if row else 0


async def create_api_key(org_id: str) -> tuple[str, str, str]:
    await revoke_all_api_keys(org_id)
    plain = "rag_" + secrets.token_urlsafe(32)
    key_hash = _hash_key(plain)
    prefix = plain[:12] + "..."
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO org_api_keys (id, org_id, key_hash, key_prefix, created_at) VALUES ($1, $2, $3, $4, now()) RETURNING id, created_at",
            str(uuid.uuid4()), org_id, key_hash, prefix,
        )
        created_at = row["created_at"].isoformat() if row.get("created_at") else None
        return plain, prefix, created_at


async def get_org_id_by_key(plain_key: str) -> str | None:
    if not plain_key or not plain_key.strip():
        return None
    key_hash = _hash_key(plain_key.strip())
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT org_id FROM org_api_keys WHERE key_hash = $1", key_hash)
        return str(row["org_id"]) if row else None


async def list_api_keys(org_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, key_prefix, created_at FROM org_api_keys WHERE org_id = $1 ORDER BY created_at DESC",
            org_id,
        )
        return [
            {
                "id": str(r["id"]),
                "key_prefix": r["key_prefix"],
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in rows
        ]
