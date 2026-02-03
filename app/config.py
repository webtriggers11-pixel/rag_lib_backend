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

POSTGRES_HOST: str = (os.getenv("POSTGRES_HOST", "localhost") or "localhost").strip() or "localhost"
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "rag")
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
    url = os.getenv("DATABASE_URL", "").strip()
    host = POSTGRES_HOST
    if url:
        url = url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url
        if "@/" in url:
            url = url.replace("@/", f"@{host}/", 1)
        if "@:" in url:
            url = url.replace("@:", f"@{host}:", 1)
        if ":/" in url:
            url = url.replace(":/", f":{POSTGRES_PORT}/", 1)
        return url
    return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{host}:{POSTGRES_PORT}/{POSTGRES_DB}"
