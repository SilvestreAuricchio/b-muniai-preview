# UC-01: Create System Administrator — Sequence Diagram

> **Bootstrap note:** the initial SA is listed in `services/bff/resources/authorized_psas.yaml`. All subsequent SAs are created by an existing SA-root through this flow and stored in the database.

---

## Actors & Participants

| Symbol | Meaning |
|---|---|
| **PSA** | Previous System Administrator — authenticated SA-root who initiates the invitation |
| **NSA** | New System Administrator — receives OTP email; activates account via public link |
| **UI** | Frontend application (React + Vite) |
| **BFF** | Backend for Frontend — Google OAuth, JWT issuance, request forwarding (Flask) |
| **Backend** | Core API — business logic, RBAC enforcement, OPERATION_LOG writes (Flask) |
| **DB** | PostgreSQL — persists USER, OPERATION_LOG |
| **Redis** | OTP challenge store — immediate persistence so `verify()` is independent of the queue |
| **RabbitMQ** | Message broker — `otp.challenge` queue with DLX → `otp.challenge.failed` DLQ |
| **Dispatcher** | OTP consumer — delivers via email + WhatsApp + SMS; ACK on success, NACK on failure |
| **NI** | Notification Inbox — in-memory per-PSA event inbox, polled by the UI |

---

## Resolved Decisions

| # | Question | Answer |
|---|---|---|
| 1 | Default challenge channels? | **All channels** — email + WhatsApp + SMS dispatched asynchronously |
| 2 | Challenge TTL? | **4 days** (345 600 s) |
| 3 | Does PSA receive notification when NSA verifies OTP? | **Yes** — `USER_OTP_VERIFIED` pushed to PSA inbox; UI polls and shows "click Approve" |
| 4 | Does NSA receive a confirmation email on activation? | **Yes** — `send_activation_email()` called by `ApproveUserUseCase` after activation |
| 5 | Can PSA cancel a pending invitation? | **Yes** — from both `pending` and `pending_approval` states; INACTIVE record preserved for audit trail and can be re-invited |
| 6 | How does NSA verify OTP? | Via public `/activate/:uuid` page (no login required); email contains direct link + code |
| 7 | Permanent delivery failures? | NACKed with `requeue=False` → routed to `otp.challenge.failed` DLQ via dead-letter exchange |

---

## Mermaid — quick preview

```mermaid
sequenceDiagram
    autonumber
    actor PSA as Previous SA [PSA]
    actor NSA as New SA [NSA]
    participant UI
    participant BFF
    participant BE as Backend
    participant DB as Database
    participant Redis
    participant MQ as RabbitMQ
    participant Disp as OTP Dispatcher
    participant NI as Notification Inbox

    rect rgb(241,245,249)
        Note over PSA,BFF: Phase 1 — PSA Session Validation
        PSA->>UI: Open Admin Panel
        UI->>BFF: GET /bff/auth/me [cookie]
        BFF-->>UI: 200 {sub, name, role: SA-root}
        UI-->>PSA: Render Admin Panel
    end

    rect rgb(240,253,244)
        Note over PSA,Disp: Phase 2 — Invite New SA
        PSA->>UI: Fill form (name, telephone, email, role)
        UI->>BFF: POST /bff/users {name, telephone, email, role}
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
        BE->>DB: INSERT user {uuid, name, telephone, email, status: pending, created_at}
        DB-->>BE: Row created {uuid}
        BE->>DB: INSERT operation_log {CREATE_USER, performedBy: PSA-uuid}
        DB-->>BE: Logged
        BE->>Redis: HSET otp:{uuid} {otp, psa_uuid}  EXPIRE ttl
        Redis-->>BE: Stored
        BE->>MQ: Publish otp.challenge {uuid, email, telephone, otp, ttl}
        BE->>DB: UPDATE user SET otp_dispatched_at = now
        DB-->>BE: Updated
        MQ-->>Disp: Deliver message
        Disp-->>NSA: OTP email (includes /activate/:uuid button + code)
        BE-->>BFF: 202 Accepted {uuid, status: pending}
        BFF-->>UI: Invitation sent
        UI-->>PSA: Confirmation displayed
    end

    rect rgb(255,251,235)
        Note over NSA,NI: Phase 3a — NSA Verifies OTP (public page)
        NSA->>UI: Open /activate/:uuid (no login required)
        UI-->>NSA: Show OTP input form
        NSA->>BFF: POST /bff/users/{uuid}/verify {otp}
        BFF->>BE: Forward (no auth headers required)
        BE->>Redis: HGETALL otp:{uuid}
        Redis-->>BE: {otp, psa_uuid}
        BE->>DB: UPDATE user SET status=pending_approval, otp_verified_at=now
        DB-->>BE: Updated
        BE->>Redis: DEL otp:{uuid}
        BE->>DB: INSERT operation_log {VERIFY_OTP, performedBy: USER-uuid}
        DB-->>BE: Logged
        BE->>NI: push USER_OTP_VERIFIED → PSA inbox
        BE-->>BFF: 200 OK {status: pending_approval}
        BFF-->>UI: Awaiting PSA approval
        UI-->>NSA: Verification successful — awaiting approval
    end

    rect rgb(240,253,244)
        Note over PSA,NSA: Phase 3b — PSA Approves
        NI-->>UI: USER_OTP_VERIFIED event (polled)
        UI-->>PSA: "NSA verified OTP — click Approve"
        PSA->>UI: Click Approve
        UI->>BFF: POST /bff/users/{uuid}/approve [cookie]
        BFF->>BE: Forward + PSA claims
        BE->>DB: UPDATE user SET status=active, activated_at=now
        DB-->>BE: Updated
        BE->>DB: INSERT operation_log {APPROVE_USER, performedBy: PSA-uuid}
        DB-->>BE: Logged
        BE->>NI: push USER_ACTIVATED → PSA inbox
        BE-->>NSA: Activation confirmation email ("Your account is active")
        BE-->>BFF: 201 Created {status: active}
        BFF-->>UI: User activated
        UI-->>PSA: Confirmation — NSA is now active
        Note over NSA: NSA can now sign in via Google OAuth
    end
```

---

## PlantUML — canonical diagram

```plantuml
@startuml UC01-Create-System-Administrator
!theme plain
skinparam sequenceMessageAlign center
skinparam defaultFontSize 12
skinparam BoxPadding 12
skinparam ParticipantPadding 20
skinparam SequenceGroupBodyBackgroundColor transparent

title UC-01: Create System Administrator

actor "Previous SA\n[PSA]"  as PSA
actor "New SA\n[NSA]"        as NSA
participant "UI"              as UI
participant "BFF"             as BFF
participant "Backend"         as BE
database    "Database"        as DB
database    "Redis"           as Redis
participant "RabbitMQ"        as MQ
participant "OTP Dispatcher"  as Disp
participant "Notification\nInbox" as NI

autonumber

== Phase 1: PSA Session Validation ==

PSA  ->  UI   : Open Admin Panel
UI   ->  BFF  : GET /bff/auth/me [cookie]
BFF  --> UI   : 200 {sub, name, role: SA-root}
UI   --> PSA  : Render Admin Panel

== Phase 2: Invite New SA ==

PSA  ->  UI   : Fill form\n(name, telephone, email, role)
UI   ->  BFF  : POST /bff/users\n{name, telephone, email, role}
BFF  ->  BE   : Forward + X-Auth-Sub, X-Auth-Role

BE   ->  DB   : INSERT user\n{uuid, name, telephone, email,\nstatus: pending, created_at}
DB   --> BE   : Row created {uuid}

BE   ->  DB   : INSERT operation_log\n{CREATE_USER, performedBy: PSA-uuid}
DB   --> BE   : Logged

BE   ->  Redis : HSET otp:{uuid} {otp, psa_uuid}\nEXPIRE ttl
Redis --> BE   : Stored

BE   ->  MQ   : Publish otp.challenge\n{uuid, email, telephone, otp, ttl}
BE   ->  DB   : UPDATE user\nSET otp_dispatched_at = now

MQ   --> Disp : Deliver message
Disp --> NSA  : OTP email\n(button → /activate/:uuid\n+ 6-digit code)

BE   --> BFF  : 202 Accepted {uuid, status: pending}
BFF  --> UI   : Invitation sent
UI   --> PSA  : Confirmation displayed

== Phase 3a: NSA Verifies OTP (public page) ==

NSA  ->  UI   : Open /activate/:uuid\n(no login required)
UI   --> NSA  : Show OTP input form

NSA  ->  BFF  : POST /bff/users/{uuid}/verify {otp}
BFF  ->  BE   : Forward (no auth required)

BE   ->  Redis : HGETALL otp:{uuid}
Redis --> BE   : {otp, psa_uuid}

BE   ->  DB   : UPDATE user\nSET status = pending_approval\notp_verified_at = now
DB   --> BE   : Updated

BE   ->  Redis : DEL otp:{uuid}

BE   ->  DB   : INSERT operation_log\n{VERIFY_OTP, performedBy: USER-uuid}
DB   --> BE   : Logged

BE   ->  NI   : push USER_OTP_VERIFIED → PSA inbox

BE   --> BFF  : 200 OK {status: pending_approval}
BFF  --> UI   : Awaiting PSA approval
UI   --> NSA  : Verification successful\n— awaiting approval

== Phase 3b: PSA Approves ==

NI   --> UI   : USER_OTP_VERIFIED event (polled)
UI   --> PSA  : "NSA verified OTP — click Approve"
PSA  ->  UI   : Click Approve
UI   ->  BFF  : POST /bff/users/{uuid}/approve [cookie]
BFF  ->  BE   : Forward + PSA claims

BE   ->  DB   : UPDATE user\nSET status = active\nactivated_at = now
DB   --> BE   : Updated

BE   ->  DB   : INSERT operation_log\n{APPROVE_USER, performedBy: PSA-uuid}
DB   --> BE   : Logged

BE   ->  NI   : push USER_ACTIVATED → PSA inbox
BE   --> NSA  : Activation confirmation email\n("Your account is active")

BE   --> BFF  : 201 Created {status: active}
BFF  --> UI   : User activated
UI   --> PSA  : Confirmation — NSA is now active

note over NSA : NSA can now sign in\nvia Google OAuth\n(BFF resolves from DB)

@enduml
```

---

## USER Entity Timestamps

| Field | Set when |
|---|---|
| `created_at` | Record created (invitation sent) or re-invited |
| `otp_dispatched_at` | `issue_challenge()` returns successfully |
| `otp_verified_at` | Invitee submits correct OTP via `/activate/:uuid` |
| `activated_at` | SA clicks Approve |

---

## OTP Retry & DLQ

```
otp.challenge  ──► dispatcher consumer
     │
     │ NACK requeue=True  (transient failure — network, timeout)
     │   └─► message requeued, redelivered to next consumer
     │
     │ NACK requeue=False  (PermanentDeliveryError — bad credentials, invalid address)
     │   └─► broker routes via otp.challenge.dlx exchange
     │           └─► otp.challenge.failed  (DLQ)
     │                 inspect at /rabbitmq management UI
```
