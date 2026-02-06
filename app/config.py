import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

DEBUG: bool = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
max_tokens_env = os.getenv("GEMINI_MAX_TOKENS", "").strip()
GEMINI_MAX_TOKENS: Optional[int] = int(max_tokens_env) if max_tokens_env else None
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
EMBEDDING_DIMENSION: int = max(256, min(3072, int(os.getenv("EMBEDDING_DIMENSION", "3072"))))

POSTGRES_HOST: str = (os.getenv("POSTGRES_HOST", "localhost") or "localhost").strip() or "localhost"
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "ragpass")
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ragdb")

MAX_UPLOAD_SIZE_MB: int = max(1, min(100, int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))))
QUESTION_MAX_LENGTH: int = max(10, min(10000, int(os.getenv("QUESTION_MAX_LENGTH", "2000"))))
ORG_NAME_MAX_LENGTH: int = max(1, min(500, int(os.getenv("ORG_NAME_MAX_LENGTH", "255"))))
CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

LOG_FILE: str = os.getenv("LOG_FILE", "").strip()
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()
LOG_MAX_BYTES: int = max(1024 * 1024, int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))))  # 10 MB
LOG_BACKUP_COUNT: int = max(1, int(os.getenv("LOG_BACKUP_COUNT", "5")))

JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES: int = max(1, int(os.getenv("JWT_EXPIRE_MINUTES", "60")))

def get_connection_string() -> str:
    url = (os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_PRIVATE_URL") or os.getenv("DATABASE_URL_PRIVATE") or os.getenv("DATABASE_URL", "")).strip()
    if url:
        url = url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url
        if "@/" in url or "@:" in url:
            host = os.getenv("POSTGRES_PUBLIC_HOST") or os.getenv("POSTGRES_HOST") or "postgres.railway.internal"
            host = host.strip() or "postgres.railway.internal"
            port = int(os.getenv("POSTGRES_PUBLIC_PORT") or os.getenv("POSTGRES_PORT") or "5432")
            if "@/" in url:
                url = url.replace("@/", f"@{host}/", 1)
            if "@:" in url:
                url = url.replace("@:", f"@{host}:", 1)
            if f"@{host}:/" in url:
                url = url.replace(f"@{host}:/", f"@{host}:{port}/", 1)
        if "sslmode=" not in url and url.startswith("postgresql://"):
            sslmode = "sslmode=disable" if "rlwy.net" in url else "sslmode=require"
            url = url + ("&" if "?" in url else "?") + sslmode
        return url
    return f"postgresql://postgres:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def get_connection_string_async() -> str:
    """Connection string for asyncpg. Same as get_connection_string() (Railway uses sslmode=disable)."""
    return get_connection_string()
