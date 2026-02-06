import uuid

import asyncpg

from app.config import DEFAULT_ORG_MAX_CHARS, DEFAULT_ORG_MAX_PDFS
from app.db import get_pool


class DuplicateOrgNameError(Exception):
    pass


def _org_row_to_dict(r: dict) -> dict:
    return {
        "id": str(r["id"]),
        "name": r["name"],
        "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        "custom_prompt": r.get("custom_prompt"),
        "max_pdfs": r.get("max_pdfs") if r.get("max_pdfs") is not None else DEFAULT_ORG_MAX_PDFS,
        "max_chars": r.get("max_chars") if r.get("max_chars") is not None else DEFAULT_ORG_MAX_CHARS,
        "upload_enabled": r.get("upload_enabled") if r.get("upload_enabled") is not None else True,
    }


async def create_org(name: str) -> dict:
    pool = await get_pool()
    org_id = str(uuid.uuid4())
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO orgs (id, name, max_pdfs, max_chars, upload_enabled) VALUES ($1, $2, $3, $4, $5) RETURNING id, name, created_at, custom_prompt, max_pdfs, max_chars, upload_enabled",
                org_id, name, DEFAULT_ORG_MAX_PDFS, DEFAULT_ORG_MAX_CHARS, True,
            )
            r = dict(row)
            return _org_row_to_dict(r)
    except asyncpg.UniqueViolationError as e:
        if e.code == "23505":
            raise DuplicateOrgNameError("Organization name already exists") from e
        raise


async def get_org(org_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, created_at, custom_prompt, max_pdfs, max_chars, upload_enabled FROM orgs WHERE id = $1",
            org_id,
        )
        if not row:
            return None
        return _org_row_to_dict(dict(row))


async def list_orgs(limit: int = 500) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, created_at, custom_prompt, max_pdfs, max_chars, upload_enabled FROM orgs ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [_org_row_to_dict(dict(r)) for r in rows]


async def set_org_limits(org_id: str, max_pdfs: int | None = None, max_chars: int | None = None, upload_enabled: bool | None = None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        args = []
        i = 1
        if max_pdfs is not None:
            updates.append(f"max_pdfs = ${i}")
            args.append(max_pdfs)
            i += 1
        if max_chars is not None:
            updates.append(f"max_chars = ${i}")
            args.append(max_chars)
            i += 1
        if upload_enabled is not None:
            updates.append(f"upload_enabled = ${i}")
            args.append(upload_enabled)
            i += 1
        if updates:
            args.append(org_id)
            await conn.execute(
                f"UPDATE orgs SET {', '.join(updates)} WHERE id = ${i}",
                *args,
            )


async def set_org_prompt(org_id: str, content: str | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orgs SET custom_prompt = $1 WHERE id = $2",
            content if content and content.strip() else None, org_id,
        )
