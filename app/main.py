import asyncio
import logging
import os
import sys
import time

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging.handlers import RotatingFileHandler

from app.config import (
    CORS_ORIGINS,
    DEBUG,
    GOOGLE_API_KEY,
    JWT_SECRET,
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    get_connection_string,
)
from app.db import close_pool, get_pool
from app.logging_handlers import DBLogHandler
from app.modules.admin import admin_router
from app.modules.auth import auth_router
from app.modules.dashboard import dashboard_router
from app.modules.orgs import orgs_router
from app.modules.rag import rag_router
from app.modules.rag.public_router import router as rag_public_router
from app.services.rag import DEFAULT_RAG_PROMPT, RAG_PROMPT_KEY

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
log_level = getattr(logging, LOG_LEVEL, logging.INFO)
handlers = [logging.StreamHandler(sys.stdout)]
if LOG_FILE:
    try:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(fh)
    except OSError:
        pass
try:
    handlers.append(DBLogHandler())
except Exception:
    pass
logging.basicConfig(level=log_level, format=LOG_FORMAT, handlers=handlers, force=True)
logger = logging.getLogger("app")
if LOG_FILE:
    logger.info("Logging to file: %s", LOG_FILE)

app = FastAPI(
    title="RAG System",
    description="Org-scoped PDF RAG with Gemini and PostgreSQL pgvector",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(orgs_router)
app.include_router(rag_router)
app.include_router(rag_public_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"method": request.method, "path": request.url.path, "status_code": response.status_code, "duration_ms": duration_ms},
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled error: %s",
        exc,
        extra={"path": request.url.path, "method": request.method, "error": str(exc)},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if DEBUG else "Internal server error"},
    )


_db_init_done = False
_db_init_lock = asyncio.Lock()


async def _ensure_db_async():
    if not DEBUG and (not JWT_SECRET or JWT_SECRET == "change-me-in-production"):
        raise RuntimeError(
            "JWT_SECRET must be set to a secure random value in production (DEBUG=0). "
            "Use e.g. openssl rand -hex 32 and set JWT_SECRET in .env."
        )
    conn = await asyncpg.connect(get_connection_string())
    try:
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            if "vector" in str(e).lower() or "extension" in str(e).lower():
                logger.warning(
                    "pgvector extension not available; RAG upload/query will fail. "
                    "On Railway use 'Postgres with pgVector Engine'."
                )
            else:
                raise
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orgs (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        await conn.execute("ALTER TABLE orgs ADD COLUMN IF NOT EXISTS custom_prompt TEXT")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                key TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        await conn.execute(
            "INSERT INTO prompts (key, content) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
            RAG_PROMPT_KEY, DEFAULT_RAG_PROMPT,
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ DEFAULT now(),
                level VARCHAR(20) NOT NULL,
                logger VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                extra JSONB
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'org')),
                org_id UUID REFERENCES orgs(id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id BIGSERIAL PRIMARY KEY,
                org_id UUID NOT NULL REFERENCES orgs(id),
                filename VARCHAR(500) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS org_api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID NOT NULL REFERENCES orgs(id),
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise
    finally:
        await conn.close()


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


@app.middleware("http")
async def lazy_db_init(request: Request, call_next):
    global _db_init_done
    if not _db_init_done:
        async with _db_init_lock:
            if not _db_init_done:
                await _ensure_db_async()
                _db_init_done = True
    return await call_next(request)


@app.get("/")
async def root():
    return {
        "message": "RAG API (org-scoped). Create org: POST /orgs. Upload: POST /orgs/{org_id}/rag/upload. Query: POST /orgs/{org_id}/rag/query.",
    }


@app.get("/health")
async def health():
    db_ok = False
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception as e:
        logger.warning("Health check DB: %s", e)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "gemini_configured": bool(GOOGLE_API_KEY),
    }
