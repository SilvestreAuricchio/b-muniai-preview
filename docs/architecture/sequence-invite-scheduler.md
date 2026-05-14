# UC-02: Invite a Scheduler (with Hospital) — Sequence Diagram

> **Relationship to UC-01:** UC-02 extends the SA invite flow. Phases 3a (OTP verification) and 3b (PSA approval) are identical to UC-01 — see `sequence-create-sa.md`. This diagram focuses on the differences: the Hospital section in the invite form and the two-step hospital-then-invite write.

---

## Actors & Participants

| Symbol | Meaning |
|---|---|
| **PSA** | Previous System Administrator — authenticated SA-root who initiates the invitation |
| **NSched** | New Scheduler — receives OTP email; activates account via public link |
| **UI** | Frontend application (React + Vite) |
| **BFF** | Backend for Frontend — JWT validation, request forwarding (Flask) |
| **Backend** | Core API — business logic, RBAC enforcement, OPERATION_LOG writes (Flask) |
| **DB** | PostgreSQL — persists USER, HOSPITAL, USER_HOSPITAL, OPERATION_LOG |
| **Redis** | OTP challenge store |
| **RabbitMQ** | Message broker — `otp.challenge` queue |
| **Dispatcher** | OTP consumer — delivers via email + WhatsApp + SMS |
| **NI** | Notification Inbox — in-memory per-PSA event inbox |

---

## Design Decisions

| # | Question | Answer |
|---|---|---|
| 1 | Can the PSA link a Scheduler to an existing hospital? | **Yes** — Hospital section shows Tax ID search and name search; PSA selects one. |
| 2 | Can the PSA register a new hospital at invite time? | **Yes** — clicking "+ Create new hospital" opens a full-screen overlay (`CreateHospitalOverlay`). The hospital is created via `POST /hospitals` *before* the invite is submitted. The overlay returns the new hospital UUID to the invite form. |
| 3 | Is the hospital mandatory for Schedulers? | **Yes** — submit button is disabled until a hospital is confirmed. |
| 4 | How many hospitals can be linked at invite? | **One.** Additional hospital links are a separate operation. |
| 5 | Are Hospital creation and UserHospital link atomic with user creation? | **Partially.** Hospital creation is a separate prior request. The `USER_HOSPITAL` link is written atomically with the user record inside `CreateUserUseCase`. |
| 6 | What are the valid slot types? | `UTI` · `PS` · `PA` · `CC` · `ENF` (multi-select at hospital creation). |
| 7 | What OPERATION_LOG entries are written? | `CREATE_HOSPITAL` (if new hospital, separate request); `CREATE_USER` always; `LINK_USER_HOSPITAL` always for Schedulers. |
| 8 | What is the Hospital primary key? | `uuid` (surrogate key). `cnpj` is the alternate key (UNIQUE, immutable after creation). |

---

## Mermaid — quick preview

```mermaid
sequenceDiagram
    autonumber
    actor PSA as SA-root [PSA]
    actor NSched as New Scheduler [NSched]
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
        Note over PSA,Disp: Phase 2 — Invite New Scheduler + Hospital
        PSA->>UI: Open "Invite User" form, select role: Scheduler
        UI->>BFF: GET /bff/hospitals
        BFF->>BE: Forward
        BE-->>BFF: 200 [{uuid, cnpj, name, …}]
        BFF-->>UI: Hospital list
        UI-->>PSA: Render form — user fields + Hospital section (search or create)

        alt Existing hospital
            PSA->>UI: Search by Tax ID or name, click Select
            UI-->>PSA: Hospital chip shown (uuid stored)
        else New hospital — CreateHospitalOverlay
            PSA->>UI: Click "+ Create new hospital"
            UI-->>PSA: Full-screen overlay opens (two-column form)
            PSA->>UI: Enter CNPJ, name, address, slot types
            PSA->>UI: Click "Create Hospital"
            UI->>BFF: POST /bff/hospitals {cnpj, name, address, slotTypes}
            BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
            BE->>DB: INSERT hospital {uuid, cnpj, name, address, slot_types}
            DB-->>BE: Hospital saved {uuid}
            BE->>DB: INSERT operation_log {CREATE_HOSPITAL, entity_id: uuid}
            BE-->>BFF: 201 {uuid, cnpj, name, …}
            BFF-->>UI: Hospital created
            UI-->>PSA: Overlay closes — hospital auto-selected in invite form
        end

        PSA->>UI: Fill user fields (name, telephone, email), submit
        UI->>BFF: POST /bff/users {name, telephone, email,<br/>role: Scheduler, hospitalUuid}
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role, X-App-Base-URL

        BE->>DB: INSERT user {uuid, …, status: pending}
        DB-->>BE: Row created {uuid}
        BE->>DB: INSERT operation_log {CREATE_USER, performedBy: PSA-uuid}
        DB-->>BE: Logged

        BE->>DB: INSERT user_hospital {user_uuid, hospital_uuid, scope: Scheduler}
        DB-->>BE: Linked
        BE->>DB: INSERT operation_log {LINK_USER_HOSPITAL, performedBy: PSA-uuid}
        DB-->>BE: Logged

        BE->>Redis: HSET otp:{uuid} {otp, psa_uuid}  EXPIRE ttl
        Redis-->>BE: Stored
        BE->>MQ: Publish otp.challenge {uuid, email, telephone, otp, ttl, base_url}
        BE->>DB: UPDATE user SET otp_dispatched_at = now
        MQ-->>Disp: Deliver message
        Disp-->>NSched: OTP email (includes /activate/:uuid button + code)
        BE-->>BFF: 202 Accepted {uuid, status: pending}
        BFF-->>UI: Invitation sent
        UI-->>PSA: Confirmation displayed
    end

    rect rgb(255,251,235)
        Note over NSched,NI: Phase 3a — NSched Verifies OTP (same as UC-01)
        NSched->>UI: Open /activate/:uuid (no login required)
        NSched->>BFF: POST /bff/users/{uuid}/verify {otp}
        BFF->>BE: Forward
        BE->>Redis: HGETALL otp:{uuid}
        Redis-->>BE: {otp, psa_uuid}
        BE->>DB: UPDATE user SET status=pending_approval, otp_verified_at=now
        BE->>DB: INSERT operation_log {VERIFY_OTP}
        BE->>NI: push USER_OTP_VERIFIED → PSA inbox
        BE-->>BFF: 200 OK {status: pending_approval}
        BFF-->>UI: Awaiting PSA approval
        UI-->>NSched: Verification successful — awaiting approval
    end

    rect rgb(240,253,244)
        Note over PSA,NSched: Phase 3b — PSA Approves (same as UC-01)
        NI-->>UI: USER_OTP_VERIFIED event (polled)
        UI-->>PSA: "Scheduler verified OTP — click Approve"
        PSA->>UI: Click Approve
        UI->>BFF: POST /bff/users/{uuid}/approve [cookie]
        BFF->>BE: Forward + PSA claims
        BE->>DB: UPDATE user SET status=active, activated_at=now
        BE->>DB: INSERT operation_log {APPROVE_USER, performedBy: PSA-uuid}
        BE-->>NSched: Activation confirmation email
        BE-->>BFF: 201 Created {status: active}
        BFF-->>UI: User activated
        UI-->>PSA: Confirmation — Scheduler is now active
        Note over NSched: NSched can now sign in via Google OAuth
    end
```

---

## PlantUML — canonical diagram

```plantuml
@startuml UC02-Invite-Scheduler
!theme plain
skinparam sequenceMessageAlign center
skinparam defaultFontSize 12
skinparam BoxPadding 12
skinparam ParticipantPadding 20
skinparam SequenceGroupBodyBackgroundColor transparent

title UC-02: Invite a Scheduler (with Hospital)

actor "SA-root\n[PSA]"          as PSA
actor "New Scheduler\n[NSched]" as NSched
participant "UI"                as UI
participant "BFF"               as BFF
participant "Backend"           as BE
database    "Database"          as DB
database    "Redis"             as Redis
participant "RabbitMQ"          as MQ
participant "OTP Dispatcher"    as Disp
participant "Notification\nInbox" as NI

autonumber

== Phase 1: PSA Session Validation ==

PSA  ->  UI   : Open Admin Panel
UI   ->  BFF  : GET /bff/auth/me [cookie]
BFF  --> UI   : 200 {sub, name, role: SA-root}
UI   --> PSA  : Render Admin Panel

== Phase 2: Invite New Scheduler + Hospital ==

PSA  ->  UI   : Open "Invite User" form\nSelect role: Scheduler
UI   ->  BFF  : GET /bff/hospitals
BFF  ->  BE   : Forward
BE   --> BFF  : 200 [{uuid, cnpj, name, …}]
BFF  --> UI   : Hospital list
UI   --> PSA  : Form with user fields + Hospital section\n(search by Tax ID / Name, or create new)

alt Existing hospital
    PSA  ->  UI   : Search and select existing hospital
    UI   --> PSA  : Hospital chip shown (uuid stored)
else New hospital — CreateHospitalOverlay
    PSA  ->  UI   : Click "+ Create new hospital"
    UI   --> PSA  : Full-screen overlay opens (two-column form)
    PSA  ->  UI   : Enter CNPJ, name, address, slot types\nClick "Create Hospital"
    UI   ->  BFF  : POST /bff/hospitals\n{cnpj, name, address, slotTypes}
    BFF  ->  BE   : Forward + X-Auth-Sub, X-Auth-Role
    BE   ->  DB   : INSERT hospital\n{uuid, cnpj, name, address, slot_types}
    DB   --> BE   : Saved {uuid}
    BE   ->  DB   : INSERT operation_log\n{CREATE_HOSPITAL, entity_id: uuid}
    DB   --> BE   : Logged
    BE   --> BFF  : 201 {uuid, cnpj, name, …}
    BFF  --> UI   : Hospital created
    UI   --> PSA  : Overlay closes\nHospital auto-selected in invite form
end

PSA  ->  UI   : Fill user fields, submit
UI   ->  BFF  : POST /bff/users\n{name, telephone, email,\nrole: Scheduler, hospitalUuid}
BFF  ->  BE   : Forward + X-Auth-Sub\nX-Auth-Role, X-App-Base-URL

BE   ->  DB   : INSERT user\n{uuid, …, status: pending}
DB   --> BE   : Row created {uuid}
BE   ->  DB   : INSERT operation_log\n{CREATE_USER, performedBy: PSA-uuid}
DB   --> BE   : Logged

BE   ->  DB   : INSERT user_hospital\n{user_uuid, hospital_uuid, scope: Scheduler}
DB   --> BE   : Linked
BE   ->  DB   : INSERT operation_log\n{LINK_USER_HOSPITAL, performedBy: PSA-uuid}
DB   --> BE   : Logged

BE   ->  Redis : HSET otp:{uuid} {otp, psa_uuid}\nEXPIRE ttl
Redis --> BE   : Stored
BE   ->  MQ   : Publish otp.challenge\n{uuid, email, telephone, otp, ttl, base_url}
BE   ->  DB   : UPDATE user\nSET otp_dispatched_at = now
MQ   --> Disp : Deliver message
Disp --> NSched : OTP email\n(button → /activate/:uuid\n+ 6-digit code)

BE   --> BFF  : 202 Accepted {uuid, status: pending}
BFF  --> UI   : Invitation sent
UI   --> PSA  : Confirmation displayed

== Phase 3a: NSched Verifies OTP (public page — identical to UC-01) ==

NSched ->  UI   : Open /activate/:uuid
UI     --> NSched : Show OTP input form
NSched ->  BFF  : POST /bff/users/{uuid}/verify {otp}
BFF    ->  BE   : Forward
BE     ->  Redis : HGETALL otp:{uuid}
Redis  --> BE   : {otp, psa_uuid}
BE     ->  DB   : UPDATE user\nSET status = pending_approval\notp_verified_at = now
BE     ->  DB   : INSERT operation_log {VERIFY_OTP}
BE     ->  NI   : push USER_OTP_VERIFIED → PSA inbox
BE     --> BFF  : 200 OK {status: pending_approval}
BFF    --> UI   : Awaiting PSA approval
UI     --> NSched : Verification successful — awaiting approval

== Phase 3b: PSA Approves (identical to UC-01) ==

NI   --> UI   : USER_OTP_VERIFIED event (polled)
UI   --> PSA  : "Scheduler verified OTP — click Approve"
PSA  ->  UI   : Click Approve
UI   ->  BFF  : POST /bff/users/{uuid}/approve [cookie]
BFF  ->  BE   : Forward + PSA claims
BE   ->  DB   : UPDATE user\nSET status = active\nactivated_at = now
BE   ->  DB   : INSERT operation_log\n{APPROVE_USER, performedBy: PSA-uuid}
BE   --> NSched : Activation confirmation email
BE   --> BFF  : 201 Created {status: active}
BFF  --> UI   : User activated
UI   --> PSA  : Confirmation — Scheduler is now active

note over NSched : NSched can now sign in\nvia Google OAuth\n(BFF resolves from DB)

@enduml
```

---

## OPERATION_LOG Entries (UC-02)

| Action | Entity type | Entity ID | Written when |
|---|---|---|---|
| `CREATE_HOSPITAL` | `HOSPITAL` | `hospital.uuid` | Only when new hospital created (separate prior request) |
| `CREATE_USER` | `USER` | `user.uuid` | Always — Scheduler record inserted |
| `LINK_USER_HOSPITAL` | `USER_HOSPITAL` | `user_uuid:hospital_uuid` | Always for Scheduler invites |
| `VERIFY_OTP` | `USER` | `user.uuid` | Invitee submits correct OTP |
| `APPROVE_USER` | `USER` | `user.uuid` | PSA clicks Approve |

---

## Hospital Field Validation

| Field | Rule |
|---|---|
| `cnpj` | 14 chars, no punctuation (stripped server-side); positions 1–8 alphanumeric per IN RFB 2.229/2024. Alternate key — immutable after creation. |
| `name` | Required, non-empty |
| `address` | Required, non-empty |
| `slot_types` | Zero or more values from `SlotType` enum; empty is allowed |

---

## Hospital Endpoints (SA-root only)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/hospitals` | List all hospitals with scheduler counts |
| `POST` | `/hospitals` | Create hospital; returns `{uuid, cnpj, name, …}` |
| `GET` | `/hospitals/<uuid>` | Get single hospital by UUID |
| `PUT` | `/hospitals/<uuid>` | Update name, address, slot_types (CNPJ immutable) |
