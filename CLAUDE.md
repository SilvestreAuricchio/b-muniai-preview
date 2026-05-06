# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**MuniAI** — a medical staffing marketplace for Brazilian hospitals. Two goals: maximize shift coverage for hospitals and help medical professionals allocate their working time across institutions.

## Domain Summary

| Actor | Registered by | Role |
|---|---|---|
| System Administrator (SA-root) | Bootstrap YAML / invited by existing SA | Manages hospitals and schedulers; approves invitations |
| Mediciner (Doctor) | Self-invited via SA | Registers credentials; browses and accepts shift slots |
| Scheduler | SA-root | Creates and manages shift slots for one or more hospitals |
| Patient User | TBD | Role not yet defined |

Core entities: `User` → (`Scheduler` | `Mediciner`), `Hospital` → `Department` → `Slot` → `Escala`. See `docs/architecture/domain-model.md`.

**Authentication vs Authorization split:**
- Google OAuth handles authentication — the BFF checks the bootstrap YAML first, then queries the backend for any active DB user. JWT `sub` = DB `User.uuid` (or Google sub for bootstrap SA).
- JWT carries `sub` (USER.uuid) + `role` (SA-root | Scheduler | Mediciner). No hospital IDs or permissions in the token.
- Authorization is fully internal: coarse via `PERMISSION` table (role → resource → action); hospital scope via `USER_HOSPITAL` table.
- Every protected request: validate JWT → check PERMISSION → check USER_HOSPITAL (scoped roles only) → execute + write OPERATION_LOG atomically.

**Bootstrap SA:** `services/bff/resources/authorized_psas.yaml` lists the initial SA email(s). All subsequent SAs are created via UC-01 invitation and stored in the database.

**OPERATION_LOG convention:** every significant write (CREATE, UPDATE, DELETE on domain entities) must insert one OPERATION_LOG row in the same DB transaction. Never update or delete log rows.

## Tech Stack

| Concern | Technology |
|---|---|
| Frontend | React + Vite (TypeScript), Tailwind CSS |
| BFF | Python · Flask · Authlib (Google OAuth) |
| Backend API | Python · Flask · Flasgger (Swagger UI at `/apidocs`) |
| OTP Dispatcher | Python worker · pika (RabbitMQ consumer) |
| Cache / OTP store | Redis |
| Message broker | RabbitMQ (AMQP) with Dead Letter Queue |
| SQL Database | PostgreSQL (planned; currently in-memory repo) |
| Document DB | MongoDB (planned; for OPERATION_LOG) |
| Observability | Prometheus + Grafana |
| API Gateway | nginx (SSL termination, upstream routing) |
| Local deploy | Docker Compose |

## Commands

```bash
# Start full stack
docker compose up --build

# Scale backend horizontally
docker compose up --scale backend=3

# Rebuild a single service
docker compose build backend
docker compose up -d backend

# Run backend unit tests
docker compose exec backend pytest tests/unit/

# View logs
docker compose logs otp-dispatcher -f
docker compose logs backend -f

# Manage RabbitMQ queues
docker compose exec rabbitmq rabbitmqctl list_queues name durable arguments
docker compose exec rabbitmq rabbitmqctl delete_queue otp.challenge   # force topology reset
```

**Local access after `docker compose up`:**

| Service | URL |
|---|---|
| App | https://localhost |
| Backend Swagger | https://localhost/api/apidocs |
| BFF Swagger | https://localhost/bff/apidocs |
| RabbitMQ UI | https://localhost/rabbitmq (guest/guest) |
| Grafana | https://localhost/grafana (admin/admin) |

## Repository Structure

```
services/
  web/        React + Vite SPA
    src/
      shell/          Layout, LoginPage, ActivatePage (public), Sidebar, Header
      dashboard/      Card-grid dashboard
      modules/
        crud/users/   UserManagement, CreateSAModal, VerifyOTPModal
        reports/
        logs/
      shared/         api.ts, AuthContext, components
  bff/        Flask BFF
    src/
      infrastructure/http/blueprints/  auth, users, session, health
      infrastructure/clients/          HttpBackendClient
    resources/
      authorized_psas.yaml             Bootstrap SA email allowlist
  backend/    Flask Backend
    src/
      domain/entities/user.py
      application/
        ports/        UserRepository, ChallengePort, NotificationPort, LogPort, OTPSenderPort
        use_cases/    CreateUser, VerifyOTP, ApproveUser, CancelInvitation, FindUserByEmail, ListUsers
      infrastructure/
        persistence/  InMemoryUserRepository (→ PostgresUserRepository)
        cache/        RabbitMQOTPPublisher, NoOpOTPAdapter, NoOpNotificationAdapter
        messaging/    otp_dispatcher_consumer, smtp_otp_sender, smtp_notification_adapter,
                      noop_otp_sender, otp_queue_setup, rabbitmq_log_adapter
        http/         Flask blueprints, middleware
infra/
  docker/     docker-compose.yml, .env (gitignored)
  nginx/      nginx.conf, Dockerfile
docs/         Architecture documentation (this viewer: python -m http.server → http://localhost:8000/docs/)
```

## Hexagonal Architecture Pattern

Every Python service follows ports-and-adapters:

```
HTTP blueprint → Use Case ← Port (ABC)
                               ↑
                        Infrastructure adapter
```

- `domain/` — pure Python dataclasses, no framework imports
- `application/ports/` — ABCs only, no infrastructure
- `application/use_cases/` — depends on ports only
- `infrastructure/` — implements ports; only place where Flask/SQLAlchemy/pika/redis are imported
- `main.py` — wires concrete adapters into use cases (DI composition root)

## UC-01 Invitation Flow (implemented)

```
PSA invites → User record created (status: pending)
            → OTP published to RabbitMQ → consumer delivers via email + WhatsApp + SMS
            → Email contains /activate/:uuid link + OTP code

NSA visits /activate/:uuid (public, no auth)
            → Submits 6-digit OTP
            → status: pending_approval
            → PSA notified via in-app notification

PSA clicks Approve
            → status: active
            → Activation confirmation email sent to NSA
            → NSA can now log in via Google OAuth (BFF resolves from DB)
```

**OTP retry semantics:**
- Transient failure (network) → NACK requeue=True → re-delivered
- Permanent failure (bad SMTP credentials, invalid email) → NACK requeue=False → routed to `otp.challenge.failed` DLQ

## Architecture Documentation

| File | Contents |
|---|---|
| `docs/index.html` | Local docs viewer — serve with `python -m http.server` then open `http://localhost:8000/docs/`. Add new files to `docs/manifest.json`. |
| `docs/architecture/c4-diagrams.md` | C4 Level 1 (System Context) and Level 2 (Containers) diagrams |
| `docs/architecture/domain-model.md` | Entity model with field-level notes |
| `docs/architecture/sequence-create-sa.md` | UC-01 full sequence diagram (Mermaid + PlantUML) |
| `Notes.md` | Running architectural proposal log |
