# API Reference

Base URL: `http://localhost:8000`

---

## Root & Health

### GET /ping

No DB, no deps. Use to confirm the app receives requests (e.g. health checks).

```bash
curl http://localhost:8000/ping
```

**Response (200):** `{ "ping": "pong" }`

---

### GET /

Root info.

```bash
curl http://localhost:8000/
```

---

### GET /health

Health check (database, Gemini config).

```bash
curl http://localhost:8000/health
```

---

## Auth

### POST /auth/register

Register first user as admin. Only allowed when no users exist.

**Body:** `{ "email": "string", "password": "string" }` (password min 8 chars)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

---

### POST /auth/login

Login with email and password. Returns JWT and user.

**Body:** `{ "email": "string", "password": "string" }`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

---

### POST /auth/register-org

Admin only: create org and org user. Returns JWT for the new org user.

**Headers:** `Authorization: Bearer <admin_token>`

**Body:** `{ "name": "string", "email": "string", "password": "string" }` (password min 8 chars)

```bash
curl -X POST http://localhost:8000/auth/register-org \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme", "email": "acme@example.com", "password": "orgpassword"}'
```

---

### GET /auth/me

Current user (requires valid JWT).

**Headers:** `Authorization: Bearer <token>`

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Admin

All admin endpoints require `Authorization: Bearer <admin_token>`.

### GET /admin/dashboard

List all orgs with upload count.

```bash
curl http://localhost:8000/admin/dashboard \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### GET /admin/orgs

List all orgs.

```bash
curl http://localhost:8000/admin/orgs \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### GET /admin/orgs/{org_id}

Get org detail and its uploads.

```bash
curl http://localhost:8000/admin/orgs/ORG_UUID \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### GET /admin/prompt

Get default RAG prompt.

```bash
curl http://localhost:8000/admin/prompt \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response (200):** `{ "content": "string" }`

---

### PUT /admin/orgs/{org_id}/prompt

Set custom prompt for an org.

**Body:** `{ "content": "string" | null }` (null clears custom prompt)

```bash
curl -X PUT http://localhost:8000/admin/orgs/ORG_UUID/prompt \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "You are a helpful assistant."}'
```

**Response (200):** `{ "ok": true }`

---

## Org Dashboard

### GET /org/dashboard

Org user only: own org info and uploads.

**Headers:** `Authorization: Bearer <org_user_token>`

```bash
curl http://localhost:8000/org/dashboard \
  -H "Authorization: Bearer YOUR_ORG_TOKEN"
```

---

## Orgs

### POST /orgs

Admin only: create org (name only, no user).

**Headers:** `Authorization: Bearer <admin_token>`

**Body:** `{ "name": "string" }`

```bash
curl -X POST http://localhost:8000/orgs \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Org"}'
```

---

### GET /orgs/{org_id}

Get org by ID. Admin can access any org; org user only their own.

**Headers:** `Authorization: Bearer <token>`

```bash
curl http://localhost:8000/orgs/ORG_UUID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## RAG

Base path: `/orgs/{org_id}/rag`. Admin can use any `org_id`; org user only their own. Replace `ORG_UUID` and `YOUR_TOKEN` in curls.

### POST /orgs/{org_id}/rag/upload

Upload a PDF for the org. File must be PDF; max size from `MAX_UPLOAD_SIZE_MB` (default 50 MB).

**Headers:** `Authorization: Bearer <token>`

**Body:** multipart form, field `file` = PDF file

```bash
curl -X POST http://localhost:8000/orgs/ORG_UUID/rag/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

---

### POST /orgs/{org_id}/rag/query

Ask a question over the org’s ingested documents.

**Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`

**Body:** `{ "question": "string" }` (max length from `QUESTION_MAX_LENGTH`, default 2000)

```bash
curl -X POST http://localhost:8000/orgs/ORG_UUID/rag/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

---

## RAG (public – API key)

For the chat UI lib: no JWT; use an API key created per org in the dashboard.

### POST /rag/query

Ask a question over the org's documents. Org is resolved from the API key.

**Headers:** `X-API-Key: <org_api_key>`, `Content-Type: application/json`

**Body:** `{ "question": "string" }` (max length from `QUESTION_MAX_LENGTH`, default 2000)

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "X-API-Key: YOUR_ORG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

---

## Admin – API keys

Admin only. Create/list API keys for an org (used by the chat UI lib).

### POST /admin/orgs/{org_id}/api-keys

Create an API key for the org. Returns `api_key` (plain) once; store it securely. Not shown again. Max 3 per org.

**Headers:** `Authorization: Bearer <admin_token>`

```bash
curl -X POST http://localhost:8000/admin/orgs/ORG_UUID/api-keys \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response (200):** `{ "api_key": "rag_...", "key_prefix": "rag_xxxx...", "created_at": "..." }`

### GET /admin/orgs/{org_id}/api-keys

List API keys for the org (prefix and date only; full key is never returned).

**Headers:** `Authorization: Bearer <admin_token>`

```bash
curl http://localhost:8000/admin/orgs/ORG_UUID/api-keys \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response (200):** `{ "api_keys": [ { "id": "...", "key_prefix": "rag_xxxx...", "created_at": "..." } ] }`

**Limit:** Max 3 API keys per org. Creating when already at 3 returns 400.

---

## Org – API keys (org user)

Org user only. Create/list API keys for own org. Same 3-per-org limit.

### POST /org/api-keys

Create API key for own org. Returns plain key once. Max 3 per org.

**Headers:** `Authorization: Bearer <org_user_token>`

```bash
curl -X POST http://localhost:8000/org/api-keys \
  -H "Authorization: Bearer YOUR_ORG_TOKEN"
```

**Response (200):** `{ "api_key": "rag_...", "key_prefix": "rag_xxxx...", "created_at": "..." }`  
**Response (400):** When org already has 3 keys.

### GET /org/api-keys

List API keys for own org (prefix and date only).

**Headers:** `Authorization: Bearer <org_user_token>`

```bash
curl http://localhost:8000/org/api-keys \
  -H "Authorization: Bearer YOUR_ORG_TOKEN"
```

**Response (200):** `{ "api_keys": [ { "id": "...", "key_prefix": "rag_xxxx...", "created_at": "..." } ] }`

---

## Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /ping | — | Ping (no DB) |
| GET | / | — | Root |
| GET | /health | — | Health check |
| POST | /auth/register | — | Register first admin |
| POST | /auth/login | — | Login |
| POST | /auth/register-org | Admin | Create org + org user |
| GET | /auth/me | Any | Current user |
| GET | /admin/dashboard | Admin | Orgs + upload counts |
| GET | /admin/orgs | Admin | List orgs |
| GET | /admin/orgs/{org_id} | Admin | Org detail + uploads |
| GET | /admin/prompt | Admin | Get default RAG prompt |
| PUT | /admin/orgs/{org_id}/prompt | Admin | Set org custom prompt |
| GET | /org/dashboard | Org | Own org + uploads |
| POST | /orgs | Admin | Create org |
| GET | /orgs/{org_id} | Admin/Org | Get org |
| POST | /orgs/{org_id}/rag/upload | Admin/Org | Upload PDF |
| POST | /orgs/{org_id}/rag/query | Admin/Org | RAG query |
| POST | /rag/query | X-API-Key | RAG query (chat UI lib) |
| POST | /admin/orgs/{org_id}/api-keys | Admin | Create API key (max 3/org) |
| GET | /admin/orgs/{org_id}/api-keys | Admin | List API keys |
| POST | /org/api-keys | Org | Create API key for own org (max 3/org) |
| GET | /org/api-keys | Org | List API keys for own org |
