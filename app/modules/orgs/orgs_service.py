import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import get_connection_string


class DuplicateOrgNameError(Exception):
    pass


def create_org(name: str) -> dict:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            org_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO orgs (id, name) VALUES (%s, %s) RETURNING id, name, created_at, custom_prompt",
                (org_id, name),
            )
            row = cur.fetchone()
            conn.commit()
            return {"id": str(row["id"]), "name": row["name"], "created_at": row["created_at"].isoformat() if row.get("created_at") else None, "custom_prompt": row.get("custom_prompt")}
    except psycopg2.IntegrityError as e:
        if e.pgcode == "23505":
            raise DuplicateOrgNameError("Organization name already exists") from e
        raise
    finally:
        conn.close()


def get_org(org_id: str) -> dict | None:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, created_at, custom_prompt FROM orgs WHERE id = %s",
                (org_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"id": str(row["id"]), "name": row["name"], "created_at": row["created_at"].isoformat() if row.get("created_at") else None, "custom_prompt": row.get("custom_prompt")}
    finally:
        conn.close()


def list_orgs(limit: int = 500) -> list[dict]:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, created_at, custom_prompt FROM orgs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
            return [
                {"id": str(r["id"]), "name": r["name"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None, "custom_prompt": r.get("custom_prompt")}
                for r in rows
            ]
    finally:
        conn.close()


def set_org_prompt(org_id: str, content: str | None) -> None:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orgs SET custom_prompt = %s WHERE id = %s",
                (content if content and content.strip() else None, org_id),
            )
            conn.commit()
    finally:
        conn.close()
