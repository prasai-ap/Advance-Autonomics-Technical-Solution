# Expense Claim API

## Overview

A secure FastAPI/PostgreSQL API for registering employees, authenticating with short-lived
JWTs, submitting claims, approving direct reports, and administering users. It uses Python
3.11, synchronous SQLAlchemy 2, Pydantic v2, Argon2, PyJWT, `uv`, pytest, Ruff, and Docker.

## Run with Docker

```bash
docker compose up --build
```

Open `http://localhost:8000/docs` or `http://localhost:8000/health`. Compose defaults are
deliberately local-development credentials and must be replaced in production. PostgreSQL
data persists in `postgres_data`; the API waits for database health, creates tables, and
idempotently seeds users and one pending claim for each employee.

| User | Password | Role |
|---|---|---|
| admin@test.com | Admin@123 | ADMIN |
| manager@test.com | Manager@123 | MANAGER |
| emp1@test.com | Emp@123 | EMPLOYEE |
| emp2@test.com | Emp@123 | EMPLOYEE |
| emp3@test.com | Emp@123 | EMPLOYEE |

## Local development

Copy `.env.example` to `.env`, point `DATABASE_URL` at PostgreSQL, and replace the JWT secret.

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pytest -v
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## API

- `POST /auth/register` and `POST /auth/login`
- `GET /me`
- `POST /claims`, `GET /claims`, `GET /claims/{id}`
- `PATCH /claims/{id}/status`
- `DELETE /users/{id}`
- `GET /health`

Employees create and see only their claims. Managers see themselves plus direct reports and
may change only a direct report's pending claim. Admins see/update all claims and delete other
users. Existing forbidden claims return 403; absent claims return 404. Status transitions use
a conditional `UPDATE ... WHERE status = PENDING`, so only one concurrent transition wins.

JWTs use HS256, contain only string `sub` and UTC `exp`, expire in at most 15 minutes, and are
decoded with an explicit algorithm. Every request reloads the user, making the database the
role source of truth. Login errors are generic and unknown users perform a dummy Argon2 check.

The process-local, thread-safe sliding-window limiter returns 429 on the sixth failed login in
60 seconds and includes `Retry-After`. One Uvicorn worker preserves its state. Production needs
a shared atomic store such as Redis for multiple workers/instances. Direct client IP is used;
only a correctly configured trusted proxy should supply forwarded addresses.

## Data and deletion assumptions

Money is `Decimal`/`NUMERIC(12,2)` and timestamps are UTC-aware. User email is unique. Deleting
a user cascades their claims; deleting a manager sets reports' `manager_id` to null. Admin
self-deletion is blocked with 409 to avoid accidental lockout.

## Production improvements

Use migrations (Alembic), a secrets manager, Redis rate limiting, trusted-proxy configuration,
audit logs, refresh-token/key rotation policy, observability, backups, and multiple instances.
