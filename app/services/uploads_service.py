from app.db import get_pool


async def record_upload(org_id: str, filename: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO uploads (org_id, filename) VALUES ($1, $2)",
            org_id, filename,
        )


async def list_uploads(org_id: str, limit: int = 100) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, org_id, filename, created_at FROM uploads WHERE org_id = $1 ORDER BY created_at DESC LIMIT $2",
            org_id, limit,
        )
        return [
            {"id": r["id"], "org_id": str(r["org_id"]), "filename": r["filename"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None}
            for r in rows
        ]


async def count_uploads_by_org(org_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS n FROM uploads WHERE org_id = $1", org_id)
        return row["n"] if row else 0
