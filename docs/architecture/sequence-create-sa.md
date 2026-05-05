# UC-01: Create System Administrator — Sequence Diagram

> **Bootstrap note:** the initial SA (`sa-0`) is seeded via IaC. All subsequent SAs are created by an existing SA-root through this flow.

---

## Actors & Participants

| Symbol | Meaning |
|---|---|
| **PSA** | Previous System Administrator — authenticated SA-root who initiates the creation |
| **NSA** | New System Administrator — not yet a user; receives the OTP out-of-band |
| **UI** | Frontend application |
| **BFF** | Backend for Frontend — session validation, request forwarding |
| **Backend** | Core API — business logic, authorization enforcement, OPERATION_LOG writes |
| **Auth Service** | Issues and validates tokens; enforces RBAC via claims + PERMISSION table |
| **Database** | Persists USER, OPERATION_LOG (same transaction) |
| **Challenge Service** | Publishes OTP to message queue; async consumer delivers via **email + WhatsApp + SMS** (all channels). Single-channel failure does not fail the flow. OTP TTL: **4 days**. |
| **Notification Inbox** | In-memory (dev) / persistent (prod) per-PSA event inbox, polled by the UI |

---

## Resolved Decisions

| # | Question | Answer |
|---|---|---|
| 1 | Default challenge channel? | **All channels** — email + WhatsApp + SMS dispatched asynchronously via message consumer to avoid single-channel unavailability failing the invitation |
| 2 | Challenge TTL? | **4 days** (345 600 s) |
| 3 | Does PSA receive notification when NSA activates? | **Yes** — `USER_OTP_VERIFIED` event when NSA verifies OTP (prompts PSA to approve); `USER_ACTIVATED` confirmation after PSA approves |
| 4 | Can PSA cancel a pending invitation? | **Yes** — from both `pending` and `pending_approval` states |

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
    participant Auth as Auth Service
    participant DB as Database
    participant Ch as Challenge Service
    participant NI as Notification Inbox

    rect rgb(241,245,249)
        Note over PSA,Auth: Phase 1 — PSA Session Validation
        PSA->>UI: Open Admin Panel
        UI->>BFF: GET /session [PSA bearer token]
        BFF->>BE: Validate token
        BE->>Auth: Verify PSA claims
        Auth-->>BE: Valid · role: SA-root · sub: PSA-UUID
        BE-->>BFF: 200 OK {PSA context}
        BFF-->>UI: Render Admin Panel
    end

    rect rgb(240,253,244)
        Note over PSA,Ch: Phase 2 — Invite New SA
        PSA->>UI: Fill form (name, telephone, e-mail, role)
        UI->>BFF: POST /users {name, telephone, email, role: SA-root}
        BFF->>BE: Forward request + PSA claims
        BE->>Auth: Check PERMISSION {SA-root, USER, CREATE}
        Auth-->>BE: Authorized
        BE->>DB: INSERT user {UUID, name, telephone, email, status: pending, role: SA-root}
        DB-->>BE: Row created {UUID}
        BE->>DB: INSERT operation_log {CREATE_USER, performedBy: PSA-UUID}
        DB-->>BE: Logged
        BE->>Ch: issue_challenge {UUID, email, telephone, otp, ttl: 4 days}
        Ch-->>NSA: OTP delivered via email + WhatsApp + SMS (async consumer)
        BE-->>BFF: 202 Accepted {uuid, status: pending}
        BFF-->>UI: Invitation sent
        UI-->>PSA: Confirmation displayed
    end

    rect rgb(255,251,235)
        Note over NSA,NI: Phase 3a — NSA Verifies OTP
        NSA->>UI: Submit OTP code
        UI->>BFF: POST /users/{uuid}/verify {otp}
        BFF->>BE: Forward verification
        BE->>Ch: verify_otp {uuid, otp}
        Ch-->>BE: Valid + psa_uuid
        BE->>DB: UPDATE user SET status = pending_approval WHERE uuid = UUID
        DB-->>BE: Updated
        BE->>DB: INSERT operation_log {VERIFY_OTP, performedBy: USER-UUID}
        DB-->>BE: Logged
        BE->>NI: push USER_OTP_VERIFIED → PSA inbox
        BE-->>BFF: 200 OK {status: pending_approval}
        BFF-->>UI: Awaiting PSA approval
        UI-->>NSA: Verification successful — awaiting approval
    end

    rect rgb(240,253,244)
        Note over PSA,NI: Phase 3b — PSA Approves
        NI-->>UI: USER_OTP_VERIFIED event (polled)
        UI-->>PSA: "NSA verified OTP — click Approve"
        PSA->>UI: Click Approve
        UI->>BFF: POST /users/{uuid}/approve
        BFF->>BE: Forward + PSA claims
        BE->>DB: UPDATE user SET status = active WHERE uuid = UUID
        DB-->>BE: Updated
        BE->>DB: INSERT operation_log {APPROVE_USER, performedBy: PSA-UUID}
        DB-->>BE: Logged
        BE->>NI: push USER_ACTIVATED → PSA inbox (confirmation)
        BE-->>BFF: 201 Created {status: active}
        BFF-->>UI: User activated
        UI-->>PSA: Confirmation — NSA is now active
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

actor "Previous SA\n[PSA]" as PSA
actor "New SA\n[NSA]"       as NSA
participant "UI"             as UI
participant "BFF"            as BFF
participant "Backend"        as BE
participant "Auth Service"   as Auth
database    "Database"       as DB
participant "Challenge\nService"      as Ch
participant "Notification\nInbox"     as NI

autonumber

== Phase 1: PSA Session Validation ==

PSA  ->  UI   : Open Admin Panel
UI   ->  BFF  : GET /session\n[PSA bearer token]
BFF  ->  BE   : Validate token
BE   ->  Auth : Verify PSA claims
Auth --> BE   : Valid · role: SA-root\nsub: PSA-UUID
BE   --> BFF  : 200 OK {PSA context}
BFF  --> UI   : Render Admin Panel

== Phase 2: Invite New SA ==

PSA  ->  UI   : Fill form\n(name, telephone, e-mail, role)
UI   ->  BFF  : POST /users\n{name, telephone, email, role: SA-root}
BFF  ->  BE   : Forward request + PSA claims
BE   ->  Auth : Check PERMISSION\n{SA-root, USER, CREATE}
Auth --> BE   : Authorized

BE   ->  DB   : INSERT user\n{UUID, name, telephone, email,\nstatus: pending, role: SA-root}
DB   --> BE   : Row created {UUID}

BE   ->  DB   : INSERT operation_log\n{CREATE_USER, performedBy: PSA-UUID,\nentityId: USER-UUID}
DB   --> BE   : Logged

BE   ->  Ch   : issue_challenge\n{UUID, email, telephone, otp,\nttl: 4 days}
Ch   --> NSA  : OTP via email + WhatsApp + SMS\n(async consumer — all channels)

BE   --> BFF  : 202 Accepted\n{uuid, status: pending}
BFF  --> UI   : Invitation sent
UI   --> PSA  : Confirmation displayed

== Phase 3a: NSA Verifies OTP ==

NSA  ->  UI   : Submit OTP code
UI   ->  BFF  : POST /users/{uuid}/verify\n{otp}
BFF  ->  BE   : Forward verification
BE   ->  Ch   : verify_otp {uuid, otp}
Ch   --> BE   : Valid + psa_uuid

BE   ->  DB   : UPDATE user\nSET status = pending_approval\nWHERE uuid = UUID
DB   --> BE   : Updated

BE   ->  DB   : INSERT operation_log\n{VERIFY_OTP, performedBy: USER-UUID,\nentityId: USER-UUID}
DB   --> BE   : Logged

BE   ->  NI   : push USER_OTP_VERIFIED\n→ PSA inbox

BE   --> BFF  : 200 OK {status: pending_approval}
BFF  --> UI   : Awaiting PSA approval
UI   --> NSA  : Verification successful\n— awaiting approval

== Phase 3b: PSA Approves ==

NI   --> UI   : USER_OTP_VERIFIED event (polled)
UI   --> PSA  : "NSA verified OTP — click Approve"
PSA  ->  UI   : Click Approve
UI   ->  BFF  : POST /users/{uuid}/approve
BFF  ->  BE   : Forward + PSA claims

BE   ->  DB   : UPDATE user\nSET status = active\nWHERE uuid = UUID
DB   --> BE   : Updated

BE   ->  DB   : INSERT operation_log\n{APPROVE_USER, performedBy: PSA-UUID,\nentityId: USER-UUID}
DB   --> BE   : Logged

BE   ->  NI   : push USER_ACTIVATED\n→ PSA inbox (confirmation)

BE   --> BFF  : 201 Created {status: active}
BFF  --> UI   : User activated
UI   --> PSA  : Confirmation — NSA is now active

@enduml
```

---

## USER Entity (introduced in this use case)

| Field | Type | Notes |
|---|---|---|
| `uuid` | UUID | Primary key — generated by backend on creation |
| `name` | string | Full name |
| `telephone` | string | Used for WhatsApp / SMS challenge delivery |
| `email` | string | Used for email OTP challenge and login |
| `role` | enum | `SA-root` · `Scheduler` · `Mediciner` (extensible) |
| `status` | enum | `pending` → `pending_approval` → `active` → `inactive` |

> The `uuid` is embedded in JWT claims and in every `OPERATION_LOG` entry, providing a traceable identity for all platform actions.
