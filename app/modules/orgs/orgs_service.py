import uuid

import asyncpg

from app.db import get_pool


class DuplicateOrgNameError(Exception):
    pass


async def create_org(name: str) -> dict:
    pool = await get_pool()
    org_id = str(uuid.uuid4())
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO orgs (id, name) VALUES ($1, $2) RETURNING id, name, created_at, custom_prompt",
                org_id, name,
            )
            r = dict(row)
            return {"id": str(r["id"]), "name": r["name"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None, "custom_prompt": r.get("custom_prompt")}
    except asyncpg.UniqueViolationError as e:
        if e.code == "23505":
            raise DuplicateOrgNameError("Organization name already exists") from e
        raise


async def get_org(org_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, created_at, custom_prompt FROM orgs WHERE id = $1",
            org_id,
        )
        if not row:
            return None
        r = dict(row)
        return {"id": str(r["id"]), "name": r["name"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None, "custom_prompt": r.get("custom_prompt")}


async def list_orgs(limit: int = 500) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, created_at, custom_prompt FROM orgs ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [
            {"id": str(r["id"]), "name": r["name"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None, "custom_prompt": r.get("custom_prompt")}
            for r in rows
        ]


async def set_org_prompt(org_id: str, content: str | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orgs SET custom_prompt = $1 WHERE id = $2",
            content if content and content.strip() else None, org_id,
        )
