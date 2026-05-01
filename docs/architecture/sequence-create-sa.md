# UC-01: Create System Administrator — Sequence Diagram

> **Bootstrap note:** the initial SA (`sa-0`) is seeded via IaC. All subsequent SAs are created by an existing SA-root through this flow.  
> Tech stack is TBD — participants are logical, not implementation-bound.

---

## Actors & Participants

| Symbol | Meaning |
|---|---|
| **PSA** | Previous System Administrator — authenticated SA-root who initiates the creation |
| **NSA** | New System Administrator — not yet a user; receives the challenge out-of-band |
| **UI** | Frontend application |
| **BFF** | Backend for Frontend — session validation, request forwarding |
| **Backend** | Core API — business logic, authorization enforcement, OPERATION_LOG writes |
| **Auth Service** | Issues and validates tokens; enforces RBAC via claims + PERMISSION table |
| **Database** | Persists USER, OPERATION_LOG (same transaction) |
| **Challenge Service** | Delivers OTP to NSA via email, WhatsApp, or SMS (channel TBD) |

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
        Note over PSA,Ch: Phase 2 — Create New SA
        PSA->>UI: Fill form (name, telephone, e-mail)
        UI->>BFF: POST /users {name, telephone, email, role: SA-root}
        BFF->>BE: Forward request + PSA claims
        BE->>Auth: Check PERMISSION {SA-root, USER, CREATE}
        Auth-->>BE: Authorized
        BE->>DB: INSERT user {UUID, name, telephone, email, status: pending, role: SA-root}
        DB-->>BE: Row created {UUID}
        BE->>DB: INSERT operation_log {CREATE_USER, performedBy: PSA-UUID, entityId: USER-UUID, payload}
        DB-->>BE: Logged
        BE->>Ch: Issue challenge {UUID, email, telephone}
        Ch-->>NSA: Deliver OTP (email / WhatsApp / SMS)
        BE-->>BFF: 202 Accepted {uuid, status: pending}
        BFF-->>UI: Invitation sent
        UI-->>PSA: Confirmation displayed
    end

    rect rgb(255,251,235)
        Note over NSA,DB: Phase 3 — NSA Verifies Challenge
        NSA->>UI: Submit OTP code
        UI->>BFF: POST /users/{uuid}/verify {otp}
        BFF->>BE: Forward verification
        BE->>Ch: Verify OTP {uuid, otp}
        Ch-->>BE: Valid
        BE->>DB: UPDATE user SET status=active WHERE uuid=UUID
        DB-->>BE: Updated
        BE->>DB: INSERT operation_log {ACTIVATE_USER, performedBy: USER-UUID, entityId: USER-UUID}
        DB-->>BE: Logged
        BE-->>BFF: 201 Created
        BFF-->>UI: Render success
        UI-->>NSA: Account activated
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
participant "Challenge\nService" as Ch

autonumber

== Phase 1: PSA Session Validation ==

PSA  ->  UI   : Open Admin Panel
UI   ->  BFF  : GET /session\n[PSA bearer token]
BFF  ->  BE   : Validate token
BE   ->  Auth : Verify PSA claims
Auth --> BE   : Valid · role: SA-root\nsub: PSA-UUID
BE   --> BFF  : 200 OK {PSA context}
BFF  --> UI   : Render Admin Panel

== Phase 2: Create New SA ==

PSA  ->  UI   : Fill form\n(name, telephone, e-mail)
UI   ->  BFF  : POST /users\n{name, telephone, email,\nrole: SA-root}
BFF  ->  BE   : Forward request + PSA claims
BE   ->  Auth : Check PERMISSION\n{SA-root, USER, CREATE}
Auth --> BE   : Authorized

BE   ->  DB   : INSERT user\n{UUID, name, telephone,\nemail, status: pending,\nrole: SA-root}
DB   --> BE   : Row created {UUID}

BE   ->  DB   : INSERT operation_log\n{CREATE_USER, performedBy: PSA-UUID,\nentityId: USER-UUID, payload}
DB   --> BE   : Logged

BE   ->  Ch   : Issue challenge\n{UUID, email, telephone}
Ch   --> NSA  : Deliver OTP\n(email / WhatsApp / SMS)

BE   --> BFF  : 202 Accepted\n{uuid, status: pending}
BFF  --> UI   : Invitation sent
UI   --> PSA  : Confirmation displayed

== Phase 3: NSA Verifies Challenge ==

NSA  ->  UI   : Submit OTP code
UI   ->  BFF  : POST /users/{uuid}/verify\n{otp}
BFF  ->  BE   : Forward verification
BE   ->  Ch   : Verify OTP {uuid, otp}
Ch   --> BE   : Valid

BE   ->  DB   : UPDATE user\nSET status = active\nWHERE uuid = UUID
DB   --> BE   : Updated

BE   ->  DB   : INSERT operation_log\n{ACTIVATE_USER, performedBy: USER-UUID,\nentityId: USER-UUID}
DB   --> BE   : Logged

BE   --> BFF  : 201 Created
BFF  --> UI   : Render success
UI   --> NSA  : Account activated

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
| `status` | enum | `pending` → `active` → `inactive` |

> The `uuid` is embedded in JWT claims and in every `OPERATION_LOG` entry, providing a traceable identity for all platform actions.

## Open Decisions

| # | Question |
|---|---|
| 1 | Which challenge channel is the default: email OTP, WhatsApp, or SMS? |
| 2 | Challenge TTL (expiry of the OTP code)? |
| 3 | Does PSA receive a notification when NSA activates the account? |
| 4 | Can PSA cancel / revoke a pending invitation? |
