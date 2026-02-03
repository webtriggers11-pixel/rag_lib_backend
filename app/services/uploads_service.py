import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import get_connection_string


def record_upload(org_id: str, filename: str) -> None:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO uploads (org_id, filename) VALUES (%s, %s)",
                (org_id, filename),
            )
        conn.commit()
    finally:
        conn.close()


def list_uploads(org_id: str, limit: int = 100) -> list[dict]:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, org_id, filename, created_at FROM uploads WHERE org_id = %s ORDER BY created_at DESC LIMIT %s",
                (org_id, limit),
            )
            rows = cur.fetchall()
            return [
                {"id": r["id"], "org_id": str(r["org_id"]), "filename": r["filename"], "created_at": r["created_at"].isoformat() if r.get("created_at") else None}
                for r in rows
            ]
    finally:
        conn.close()


def count_uploads_by_org(org_id: str) -> int:
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM uploads WHERE org_id = %s", (org_id,))
            return cur.fetchone()[0]
    finally:
        conn.close()
