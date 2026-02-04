#!/usr/bin/env python3
"""Run DB migration (create tables) and seed admin. Set DATABASE_URL and POSTGRES_HOST/POSTGRES_PORT as needed. Run from project root: python scripts/migrate_and_seed.py"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2 import errors as psycopg2_errors

from app.config import get_connection_string
from app.services.rag import DEFAULT_RAG_PROMPT, RAG_PROMPT_KEY
from scripts.seed_admin import seed_admin


def migrate():
    conn = psycopg2.connect(get_connection_string())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            except psycopg2_errors.FeatureNotSupported:
                print("Warning: pgvector extension not available (use Railway 'Postgres with pgVector Engine' for RAG). Skipping.")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orgs (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("ALTER TABLE orgs ADD COLUMN IF NOT EXISTS custom_prompt TEXT")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute(
                "INSERT INTO prompts (key, content) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                (RAG_PROMPT_KEY, DEFAULT_RAG_PROMPT),
            )
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    level VARCHAR(20) NOT NULL,
                    logger VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    extra JSONB
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'org')),
                    org_id UUID REFERENCES orgs(id),
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS uploads (
                    id BIGSERIAL PRIMARY KEY,
                    org_id UUID NOT NULL REFERENCES orgs(id),
                    filename VARCHAR(500) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS org_api_keys (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id UUID NOT NULL REFERENCES orgs(id),
                    key_hash TEXT NOT NULL UNIQUE,
                    key_prefix TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
        print("Database migrated.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
    asyncio.run(seed_admin())
