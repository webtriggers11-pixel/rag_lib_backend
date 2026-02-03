#!/usr/bin/env python3
"""Clear all database data. Run from project root: python scripts/clear_db.py"""

import sys

# Allow importing app when run as script
sys.path.insert(0, ".")

import psycopg2

from app.config import get_connection_string


def clear_db():
    conn = psycopg2.connect(get_connection_string())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE audit_logs, prompts, orgs
                RESTART IDENTITY CASCADE
            """)
            try:
                cur.execute("""
                    TRUNCATE langchain_pg_embedding, langchain_pg_collection
                    RESTART IDENTITY CASCADE
                """)
            except psycopg2.ProgrammingError as e:
                if "does not exist" not in str(e):
                    raise
        print("All database data cleared.")
    finally:
        conn.close()


if __name__ == "__main__":
    clear_db()
