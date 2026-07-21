# Interview cheatsheet

## 60-second introduction

This FastAPI expense API prioritizes authentication and authorization. Schemas reject extra
fields, Argon2 protects passwords, HS256 JWTs contain only `sub` and `exp`, and every request
reloads the database user. A centralized claim policy implements employee ownership, manager
direct reports, self-approval prevention, and admin access. SQLAlchemy uses exact money and an
atomic pending-only transition. Docker Compose starts healthy PostgreSQL and idempotent seeds.

## Architecture (ten lines)

1. `main.py` assembles the application.
2. Schemas validate and forbid extras.
3. Dependencies validate JWT/reload users.
4. `require_roles` gates endpoint roles.
5. Thin routes call services.
6. Services own business states.
7. `ClaimAccessPolicy` owns resources.
8. Repositories own SQLAlchemy queries.
9. `get_db` owns request sessions.
10. PostgreSQL owns constraints/cascades.

## Key facts

- Auth: normalize → lookup → real/dummy Argon2 → JWT; reload user on every request.
- Ownership: `ClaimAccessPolicy.ensure_can_view_claim`; direct reports check owner.manager_id.
- 403 vs 404: load by ID first, 404 if absent, then policy gives 403 if forbidden.
- Transitions: only PENDING → APPROVED/REJECTED; conditional update makes one winner.
- Rate limit: failures only, sliding 60 seconds, sixth is 429, Retry-After, success clears.
- Docker: locked production deps, slim Python, non-root, healthy DB dependency, one worker.

| Role | Create | View | Update | Delete user |
|---|---|---|---|---|
| Employee | own | own | no | no |
| Manager | no | own + direct reports | direct reports only | no |
| Admin | no | all | all pending | yes, except self |

## Five strongest tests

Foreign existing claim gives 403; manager excludes emp3; manager self-update is 403; second
transition is 409; expired/tampered/deleted-user tokens are 401.

## Five honest limitations

Metadata creation instead of migrations; in-memory single-process limiter; SQLite unit tests;
single symmetric JWT key; no audit log.

## Rapid fire

1. Role in JWT? No—database is current authority.
2. Money type? Decimal and NUMERIC(12,2).
3. Password algorithm? Argon2 through pwdlib.
4. Sixth failure? 429 with Retry-After.
5. Manager query? Join owner, filter self or owner.manager_id.
6. Race defense? Conditional PENDING update and rowcount.
7. User deletion? Claims cascade.
8. Manager deletion? Reports set null.
9. Why one worker? Limiter is process-local.
10. First production upgrades? Alembic, Redis, secret store, audit logs, PostgreSQL CI.

## Demo and pre-call checklist

Demo employee `/me`/claims/403, manager visibility/approve/403/409, then admin all/delete a
disposable user. Before the call: run Compose, open Swagger, locate the five walkthrough files,
memorize status semantics, retain seed credentials, and never delete a required seed user.
