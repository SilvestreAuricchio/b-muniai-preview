# MuniAI — Session Bootstrap

Load this file at the start of any new conversation to restore full working context.

---

## What This Project Is

**MuniAI** — medical staffing marketplace for Brazilian hospitals.
- Hospitals post shift slots; medical professionals (Medicineres) accept them.
- SAs (System Administrators) manage the platform, invite users, approve activations.

**Current branch:** `feat/initial-steps`
**Git user:** Silvestre Auricchio (silvestre@muninai.com.br) — project owner and System Engineer.

---

## Actors & Domain

| Actor | Created by | Role |
|---|---|---|
| SA-root | Bootstrap YAML or invited SA | Manages hospitals, schedulers, approves invitations |
| Mediciner | SA-invited | Browses and accepts shift slots |
| Scheduler | SA-root | Creates shift slots for hospitals |
| Patient User | TBD | Not yet defined |

**Core entities:** `User` → (`Scheduler` | `Mediciner`), `Hospital` → `Department` → `Slot` → `Escala`

**Slot types:** PM (Physician On-Call), PE (Nursing Duty), CC (Operating Room), CM (Outpatient)
**Department types:** UTI (ICU), PA (Urgent Care), PS (Emergency Room)

---

## Auth & Authorization

- **Google OAuth** = authentication only (IdP)
- **JWT** (BFF-issued, httpOnly cookie, 88-min TTL, sliding renewal every 44 min):
  - `sub` = User.uuid (Google OAuth sub for bootstrap SA)
  - `role` = SA-root | Scheduler | Mediciner
  - `itk` = invite_token UUID (DB users only; bootstrap SA has no `itk`)
- **BFF login flow:** checks `authorized_psas.yaml` first, then queries backend DB for active users. Bootstrap SA also checks DB for disable/deactivate status.
- **Session revocation (Redis DB 2):**
  - `itk:{uuid}` = invite_token UUID or `"REVOKED"` — checked against JWT `itk` claim on every BFF request (only for tokens that carry `itk`)
  - `blocked:{email}` = `"1"` — email blocklist, covers ALL sessions including bootstrap SA and legacy tokens without `itk`
  - `_sync_revoked_users()` runs at backend startup: blocks inactive/disabled users, clears blocks for active users (self-healing)
  - `approve_user` → `cache.activate(uuid, email, token)` — sets itk AND clears email block
  - `disable_user` / `deactivate_user` → `cache.revoke(uuid, email)` — sets `"REVOKED"` + blocks email
  - `enable_user` → `cache.unblock(uuid, email)` + `cache.set(uuid, token)`
  - Three-state logic: `stored=None` → allow (new deployment); `stored="REVOKED"` → block; `stored≠itk_claim` → block
- **Auto-renew:** `GET /bff/auth/refresh` re-issues JWT; `AuthContext` calls every 44 min via `setInterval`
- **Frontend global 401 handler:** `api.ts` — any 401 response from BFF triggers immediate `window.location.replace()` to login page; no partial state, no further operations possible
- **Authorization** is fully internal:
  - Coarse: `PERMISSION` table (role → resource → action)
  - Scoped: `USER_HOSPITAL` table
  - Every protected request: validate JWT → check PERMISSION → check USER_HOSPITAL → execute + write OPERATION_LOG atomically
- **OPERATION_LOG:** append-only. One row per write (CREATE/UPDATE/DELETE), same DB transaction. Never update or delete log rows.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| BFF | Python 3.12 · Flask · Authlib · PyJWT · Redis |
| Backend API | Python 3.12 · Flask · Flasgger · SQLAlchemy 2.0 Core · Pika |
| OTP Dispatcher | Python worker · pika (RabbitMQ consumer) |
| Cache | Redis DB 0: OTP store; DB 2: invite-token / session revocation |
| Broker | RabbitMQ with DLQ `otp.challenge.failed` |
| SQL DB | **PostgreSQL 16 — ACTIVE** (`app_user`, `hospital`, `user_hospital`, `invite_history`) |
| Document DB | MongoDB 7 (planned for OPERATION_LOG) |
| Observability | Prometheus + Grafana |
| Gateway | nginx (SSL termination + upstream routing) |
| Deploy | Docker Compose (13 services) |

---

## Hexagonal Architecture (both BFF and Backend)

```
HTTP blueprint → Use Case ← Port (ABC)
                               ↑
                        Infrastructure adapter
```

- `domain/` — pure Python dataclasses, zero framework imports
- `application/ports/` — ABCs only
- `application/use_cases/` — depends on ports only
- `infrastructure/` — Flask / SQLAlchemy / pika / redis imports live here only
- `main.py` — DI composition root

---

## What Is Implemented

### UC-01 Invitation Flow (complete)
```
PSA invites → User(status=pending) created
            → OTP published to RabbitMQ → delivered email + WhatsApp + SMS
            → Email has /activate/:uuid link + 6-digit OTP

NSA visits /activate/:uuid (public) → submits OTP
            → status: pending_approval → PSA notified

PSA approves → status: active → confirmation email → NSA can log in via Google
```
Reinvite: invite same email → old cycle snapshotted to `invite_history` → user reset to pending.
**OTP retry:** transient → NACK requeue=True; permanent → NACK requeue=False → DLQ.

### UC-03 Manage User Status (complete)
- `active → disabled` (Disable), `disabled → active` (Re-enable), `active|disabled → inactive` (Deactivate)
- Immediate session revocation via Redis email blocklist + itk on disable/deactivate
- UI: `⋯` action menu per row with confirmation dialogs

### Backend use cases (`application/use_cases/`)
`create_user`, `verify_otp`, `approve_user`, `cancel_invitation`, `find_user_by_email`, `list_users`, `disable_user`, `enable_user`, `deactivate_user`, `list_invite_history`, `create_hospital`, `list_hospitals`, `get_hospital`, `update_hospital`

### Frontend routes
| Route | Component |
|---|---|
| `/` | Dashboard — user stats card + hospital stats card, quick actions |
| `/users` | UserManagement — invite, approve, disable, re-enable, deactivate, reinvite, invite history |
| `/hospitals` | HospitalManagement — flat table, "View →" action per row |
| `/hospitals/:uuid` | HospitalDetail — two-column profile card, full edit, stat cards |
| `/activate/:uuid` | ActivatePage (public, OTP entry) |
| `/crud/hospitals` | Redirects to `/hospitals` |

### PostgreSQL Schema (active, auto-created on startup)
```
app_user(uuid PK, name, telephone, email UNIQUE, role, status, created_at,
         otp_dispatched_at, otp_verified_at, activated_at, invite_token)
hospital(uuid PK, cnpj VARCHAR(14) UNIQUE, name, address, slot_types TEXT[])
user_hospital(user_uuid FK→app_user.uuid, hospital_uuid FK→hospital.uuid, scope, PK composite)
invite_history(id PK, user_uuid FK, invited_at, otp_dispatched_at, otp_verified_at, activated_at)
```
**Note:** `hospital.cnpj` is the alternate key (immutable after creation). Nuke required when migrating from old `cnpj PK` schema.

---

## Service File Layout (key paths)

```
services/
  web/src/
    shell/             LoginPage.tsx, ActivatePage.tsx, Shell.tsx, Header.tsx, Sidebar.tsx
    dashboard/         Dashboard.tsx (stats card, fixed tooltip), InsightCard.tsx
    modules/crud/users/    UserManagement.tsx, CreateSAModal.tsx, VerifyOTPModal.tsx
    modules/crud/hospitals/ HospitalManagement.tsx, HospitalDetail.tsx, CreateHospitalOverlay.tsx
    shared/            api.ts (global 401 handler + credentials:include + put()),
                       context/AuthContext.tsx (auth + 44min refresh interval),
                       components/RedCross.tsx
  bff/src/
    main.py
    infrastructure/clients/http_backend_client.py
    infrastructure/cache/token_cache.py        ← Redis itk + email blocklist reader
    infrastructure/http/middleware.py          ← JWT validation + revocation check + debug logs
    infrastructure/http/blueprints/auth.py     ← OAuth, /auth/me, /auth/refresh, /auth/logout
    infrastructure/http/blueprints/users.py    ← proxy to backend
    infrastructure/http/blueprints/hospitals.py ← GET/POST/GET<uuid>/PUT<uuid> forwarding
    infrastructure/clients/http_backend_client.py ← put() method added
    application/ports/backend_client.py        ← put() abstract method added
    resources/authorized_psas.yaml             ← bootstrap SA allowlist (sauricchiopv@gmail.com)
  backend/src/
    main.py                                    ← DI wiring + _sync_revoked_users()
    domain/entities/user.py                    ← User, InviteHistory, UserRole, UserStatus
    domain/entities/hospital.py                ← Hospital, UserHospital
    domain/validation/tax_id.py                ← CNPJ validator (alphanumeric IN RFB 2.229/2024)
    application/ports/                         user_repository, hospital_repository, challenge_port, ...
    application/use_cases/                     (12 use cases above)
    infrastructure/persistence/schema.py       ← SQLAlchemy table defs + create_schema()
    infrastructure/persistence/postgres_user_repository.py
    infrastructure/persistence/postgres_hospital_repository.py
    infrastructure/cache/invite_token_cache.py ← set/activate/revoke/unblock methods
    infrastructure/cache/rabbitmq_otp_publisher.py
    infrastructure/messaging/otp_dispatcher_consumer.py
    infrastructure/http/blueprints/users.py    ← all user endpoints incl. /users/by-email?anyStatus
    infrastructure/http/blueprints/hospitals.py ← GET/POST /hospitals, GET/PUT /hospitals/<uuid>
    application/use_cases/get_hospital.py      ← find by uuid
    application/use_cases/update_hospital.py   ← mutate name/address/slot_types + log
infra/nginx/nginx.conf
docs/architecture/  c4-diagrams.md, domain-model.md, sequence-create-sa.md,
                    sequence-manage-user-status.md, sequence-invite-scheduler.md
```

---

## Local Access

| Service | URL |
|---|---|
| App | https://localhost or https://muninai.com.aw |
| Backend Swagger | https://localhost/api/apidocs |
| BFF Swagger | https://localhost/bff/apidocs |
| RabbitMQ UI | https://localhost/rabbitmq (guest/guest) |
| Grafana | https://localhost/grafana (admin/admin) |

**Stack (Windows):** `.\stack.ps1 <up|down|restart|logs|build|clean|nuke>`
**Stack (Linux/macOS):** `make <up|down|restart|logs|build|clean|nuke>`

**After any partial rebuild:** always `docker compose restart nginx` to flush DNS cache.

**Persistent storage (bind mounts):** `./data/postgres/`, `./data/mongodb/`, `./data/prometheus/`

---

## Working Rules (PROJECT RULES — always apply)

1. **Docs sync:** Every implementation change → update `docs/architecture/` and `Notes.md` in the same response.
2. **Plan gate:** Any change touching more than one service, a new layer, auth/authz, or existing use-case refactors requires a written plan + explicit confirmation before writing code.
3. **English feedback coach:** Apply `.claude/english-feedback-coach.md` to every user message without exception. Structure: original → PT direct translation → PT comprehension → improved EN → score (0.0–4.0, steps of 0.4) + one tip. Place feedback at the **bottom** of each response.
4. **PostgreSQL default:** All entities default to PostgreSQL. Never use in-memory or MongoDB unless explicitly requested.
5. **UTF-8 only:** All files must use UTF-8 without BOM. Never write UTF-16 LE.
6. **Ask before doubts:** When uncertain about design or intent, ask before implementing.
7. **Persist all project rules:** Every PROJECT RULE stated by the user must be saved to memory immediately.
8. **Warn before data-loss changes:** Always warn and confirm before any change that causes data loss on restart.
9. **Notes.md order:** Most recent date entry always at the top of Notes.md.
10. **English corrections at bottom:** Always place English feedback corrections at the bottom of responses.

---

## What Comes Next (likely)

- Scheduler and Mediciner invitation/activation flows
- Department and Slot CRUD endpoints (Hospital detail stubs: Mediciners, Open Slots)
- PERMISSION and USER_HOSPITAL enforcement
- MongoDB OPERATION_LOG adapter
- Mediciner dashboard
