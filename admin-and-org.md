# Admin and Org

## Overview

The RAG API has two user roles and an organization (org) model:

- **Admin**: Global role; can manage all orgs and create orgs/users.
- **Org**: Scoped to one organization; can only access that org’s data.

---

## Admin

### Role

- `role`: `"admin"`
- No `org_id` (global access).
- Required for: creating orgs, registering org users, admin dashboard, listing/viewing all orgs and their uploads.

### How to get an admin

- **First user**: `POST /auth/register` is only allowed when there are no users. That user is created with `role=admin` and no `org_id`. After that, registration is closed.
- No other way to become admin in this flow (no self-service admin creation).

### Admin endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | List all orgs with upload count per org. Requires `Authorization: Bearer <token>` (admin). |
| GET | `/admin/orgs` | List all orgs. Admin only. |
| GET | `/admin/orgs/{org_id}` | Get one org plus its uploads. Admin only. |

All require a valid JWT and `require_admin` (role must be `admin`).

---

## Org (Organization)

### Model

- **Table**: `orgs`  
  - `id` (UUID), `name` (unique), `created_at`
- Orgs own **uploads** (and thus RAG data) via `uploads.org_id`.
- **Users** with `role=org` have one `org_id` and can only access that org’s resources.

### Org user

- `role`: `"org"`
- `org_id`: UUID of the org they belong to.
- Can: access `/orgs/{org_id}` only when `org_id` matches their `org_id`, and use RAG/upload endpoints for that org.
- Cannot: create orgs, register other users, or access other orgs.

### How orgs and org users are created

- **Admin only**:
  - Create org: `POST /orgs` (body: `{"name": "Org Name"}`).
  - Create org + org user in one step: `POST /auth/register-org` (body: `name`, `email`, `password`). This creates the org and a user with `role=org` and that org’s `org_id`.

### Org endpoints

| Method | Path | Who | Description |
|--------|------|-----|-------------|
| POST | `/orgs` | Admin | Create org. Body: `{"name": "..."}`. |
| GET | `/orgs/{org_id}` | Admin or org user for that org | Get org by id. Org users only for their own `org_id`. |

Access to `GET /orgs/{org_id}`: admin can access any org; org user only when `current_user.org_id == org_id`.

---

## Login details

**Endpoint:** `POST /auth/login`

**Request body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response (200):**
```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "user": {
    "id": "<uuid>",
    "email": "user@example.com",
    "role": "admin",
    "org_id": null
  }
}
```
(For org users, `role` is `"org"` and `org_id` is the org UUID.)

**Using the token:** Send in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

**How to get credentials:**
- **Admin:** If no users exist, call `POST /auth/register` with `{"email": "...", "password": "..."}` (min 8 chars). That user is admin; then use the same email/password with `POST /auth/login`.
- **Org user:** Admin calls `POST /auth/register-org` with `{"name": "Org Name", "email": "...", "password": "..."}`. That user can then log in with `POST /auth/login` using that email and password.

---

## Auth summary

| Endpoint | Purpose |
|----------|---------|
| `POST /auth/register` | First user only → becomes admin. |
| `POST /auth/register-org` | Admin only → create org + org user. |
| `POST /auth/login` | Login; returns JWT with `sub`, `role`, and (for org) `org_id`. |
| `GET /auth/me` | Current user (excl. password). |

---

## Dependencies (backend)

- **Admin-only routes**: `Depends(require_admin)` (from `app.modules.auth.dependencies`).
- **Org-scoped routes**: `get_current_user` then check `org_id` (or use helpers that allow admin or matching org).

Admin and org behavior is implemented in:

- `app/modules/admin/admin_router.py` — admin dashboard and org listing.
- `app/modules/orgs/orgs_router.py` — create org, get org (with org access check).
- `app/modules/orgs/orgs_service.py` — create_org, get_org, list_orgs.
- `app/modules/auth/dependencies.py` — get_current_user, require_admin, org access.
