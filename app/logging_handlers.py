import logging
import sys

import psycopg2
from psycopg2.extras import Json

from app.config import get_connection_string

_LOG_RECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "stack_info", "exc_info", "exc_text", "taskName", "msg", "args",
    }
)


def _serialize_extra(record: logging.LogRecord) -> dict:
    extra = {}
    for k, v in record.__dict__.items():
        if k in _LOG_RECORD_ATTRS:
            continue
        try:
            if v is None or isinstance(v, (str, int, float, bool)):
                extra[k] = v
            elif isinstance(v, (list, dict)):
                extra[k] = v
            else:
                extra[k] = str(v)
        except Exception:
            extra[k] = str(v)
    return extra


class DBLogHandler(logging.Handler):
    """Logging handler that writes log records to the audit_logs table."""

    def __init__(self):
        super().__init__()
        self._ensure_table()

    def _ensure_table(self):
        try:
            conn = psycopg2.connect(get_connection_string())
            conn.autocommit = True
            with conn.cursor() as cur:
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
            conn.close()
        except Exception:
            pass

    def emit(self, record: logging.LogRecord):
        try:
            message = self.format(record)
            if not message:
                message = record.getMessage()
            extra = _serialize_extra(record)
            conn = psycopg2.connect(get_connection_string())
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO audit_logs (level, logger, message, extra) VALUES (%s, %s, %s, %s)",
                        (record.levelname, record.name, message, Json(extra) if extra else None),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            sys.stderr.write("DBLogHandler: failed to write log to database\n")
