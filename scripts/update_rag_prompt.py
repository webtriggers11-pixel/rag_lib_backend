#!/usr/bin/env python3
"""Update RAG system prompt in DB to current default. Run from rag_lib: python scripts/update_rag_prompt.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_connection_string
from app.services.rag import DEFAULT_RAG_PROMPT, RAG_PROMPT_KEY


def update_rag_prompt():
    import psycopg2
    conn = psycopg2.connect(get_connection_string())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE prompts SET content = %s, updated_at = now() WHERE key = %s",
                (DEFAULT_RAG_PROMPT, RAG_PROMPT_KEY),
            )
            conn.commit()
            if cur.rowcount:
                print("RAG prompt updated in DB.")
            else:
                cur.execute(
                    "INSERT INTO prompts (key, content, updated_at) VALUES (%s, %s, now())",
                    (RAG_PROMPT_KEY, DEFAULT_RAG_PROMPT),
                )
                conn.commit()
                print("RAG prompt inserted in DB.")
    finally:
        conn.close()


if __name__ == "__main__":
    update_rag_prompt()
