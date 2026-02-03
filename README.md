# RAG System (FastAPI + PostgreSQL pgvector + Gemini)

Org-scoped RAG with **admin** and **org** roles. Email + password auth (JWT). Only admin can register orgs; orgs can upload and query their own data.

## Roles

- **Admin:** First user to register becomes admin. Can register orgs (name + org email + password), see all orgs and their uploads (admin dashboard), create orgs.
- **Org:** Created by admin via “register org” (org name + email + password). Can upload PDFs and ask questions for their org only (org dashboard).

## Flow

1. **Register admin** (once): `POST /auth/register` with email + password → returns JWT. No users must exist.
2. **Login:** `POST /auth/login` with email + password → returns JWT.
3. **Admin registers org:** `POST /auth/register-org` (admin token) with name, email, password → creates org and org user, returns JWT for that org user.
4. **Admin dashboard:** `GET /admin/dashboard` (admin token) → list orgs with upload count. `GET /admin/orgs/{org_id}` → org detail + uploads.
5. **Org dashboard:** `GET /org/dashboard` (org token) → own org info + uploads.
6. **Upload / query:** `POST /orgs/{org_id}/rag/upload`, `POST /orgs/{org_id}/rag/query` (Bearer token: admin or org user for that `org_id`).

## Run

1. **Start PostgreSQL (Docker)**

   ```bash
   docker compose up -d
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` (and optional Gemini/Postgres vars).

   ```bash
   cp .env.example .env
   # Edit .env and set GOOGLE_API_KEY=your_key
   ```

3. **Install and run**

   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Scanned / image-only PDFs (optional)**  
   For PDFs that are just images (scanned docs), install Tesseract so the app can run OCR:
   - **Mac:** `brew install tesseract`
   - **Ubuntu/Debian:** `sudo apt install tesseract-ocr`
   - **Windows:** [Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)

## API

- Docs: http://localhost:8000/docs  
- PostgreSQL: host port **5433**

### Curl

**Register admin (first user only)**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

**Login**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

**Admin: Register org** (creates org + org user; use admin token)

```bash
curl -X POST http://localhost:8000/auth/register-org \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme", "email": "acme@example.com", "password": "orgpassword"}'
```

**Admin: Create org only** (optional; admin token)

```bash
curl -X POST http://localhost:8000/orgs \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Org"}'
```

**Admin dashboard** (list orgs + upload count)

```bash
curl http://localhost:8000/admin/dashboard \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Org dashboard** (org user token)

```bash
curl http://localhost:8000/org/dashboard \
  -H "Authorization: Bearer YOUR_ORG_TOKEN"
```

**Upload PDF** (admin or org user for that org_id)

```bash
curl -X POST http://localhost:8000/orgs/{org_id}/rag/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

**Ask question**

```bash
curl -X POST http://localhost:8000/orgs/{org_id}/rag/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

**Get org** (admin or org user for that org_id)

```bash
curl http://localhost:8000/orgs/{org_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## RAG prompt (DB)

The system prompt used for Q&A is stored in the `prompts` table and can be changed in the DB.

- **Table:** `prompts` — columns: `key` (TEXT PRIMARY KEY), `content` (TEXT), `updated_at` (TIMESTAMPTZ)
- **Key:** `rag_system` — the RAG Q&A prompt. The template must include `{context}` and `{question}`.
- **Update:** `UPDATE prompts SET content = '...', updated_at = now() WHERE key = 'rag_system';` — changes apply on the next query.

The default prompt is strict: answers only from context, refuses off-topic/inappropriate/sensitive requests, no hallucination.

## Production

- **Railway:** Use **Postgres with pgVector Engine** for the database (https://railway.com/deploy/postgres-with-pgvector-engine). The default Railway PostgreSQL does not include the pgvector extension; the app requires it for RAG.
- **JWT_SECRET:** With `DEBUG=0`, the app will not start unless `JWT_SECRET` is set to a secure random value (not `change-me-in-production`). Use e.g. `openssl rand -hex 32` and set it in `.env`.
- **Health:** `GET /health` returns `status`, `database`, `gemini_configured`. Use for load balancers and readiness probes.
- **Limits:** PDF upload max size (default 50 MB, `MAX_UPLOAD_SIZE_MB`), question max length (default 2000, `QUESTION_MAX_LENGTH`), org name max length (default 255, `ORG_NAME_MAX_LENGTH`). Enforced with 413/400.
- **Errors:** When `DEBUG=0`, 500 responses return a generic message; when `DEBUG=1`, full error detail is returned. Exceptions are logged.
- **CORS:** Set `CORS_ORIGINS=https://your-frontend.com` (comma-separated). Leave empty for same-origin only. With `DEBUG=1`, origins allow all.
- **Run:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` (omit `--reload` in production).
- **Logs:** Set `LOG_FILE` (e.g. `logs/app.log`) to write all logs to a file. Uses `RotatingFileHandler` (`LOG_MAX_BYTES` default 10 MB, `LOG_BACKUP_COUNT` default 5). `LOG_LEVEL` controls level (default INFO). Every request (method, path, status, duration), org create, upload, query, and errors are logged.
- **Audit logs in DB:** All log records are also written to the `audit_logs` table (level, logger, message, extra JSONB). The `extra` column stores structured audit data (e.g. `method`, `path`, `status_code`, `duration_ms` for requests; `event`, `org_id`, `upload_filename`, `chunks_stored` for uploads; `event`, `org_id`, `question_len` for queries). Query with `SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;` or filter by `extra->>'event'`, `extra->>'org_id'`, etc.

## Structure (modular)

- `app/modules/auth/` — register (first user = admin), login (JWT), register-org (admin only), get_current_user, require_admin
- `app/modules/admin/` — admin dashboard: list orgs, org detail + uploads
- `app/modules/dashboard/` — org dashboard: own org + uploads
- `app/modules/orgs/` — create org (admin only), get org (admin or org); list_orgs for admin
- `app/modules/rag/` — upload, query (admin or org for that org_id); records uploads in `uploads` table
- `app/services/rag.py` — vector store, ingest, query; loads prompt from DB via `get_rag_prompt()`
- `app/services/uploads_service.py` — record_upload, list_uploads, count_uploads_by_org
- `app/main.py` — FastAPI app, DB startup (users, uploads, audit_logs, etc.), router includes
- `app/logging_handlers.py` — DBLogHandler: writes every log record to `audit_logs`
# rag_backend
