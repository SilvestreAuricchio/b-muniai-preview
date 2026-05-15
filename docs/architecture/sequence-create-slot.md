# UC-03: Scheduler Manages Slots — Sequence Diagram

> Covers the full Slot lifecycle for an authenticated Scheduler (or SA-root): **Create**, **List** (Table and Agenda views), **Update**, and **Delete**. Pre-condition: Scheduler is active (UC-02 completed) and has at least one hospital linked via `USER_HOSPITAL`.

---

## Actors & Participants

| Symbol | Meaning |
|---|---|
| **Sched** | Scheduler — authenticated actor; JWT cookie already set |
| **SA** | SA-root — may perform the same slot operations platform-wide |
| **UI** | Frontend application — `/slots` page (SlotManagement) |
| **BFF** | Backend for Frontend — JWT validation, request forwarding |
| **Backend** | Core API — business logic, RBAC, OPERATION_LOG writes |
| **DB** | PostgreSQL — `slot`, `hospital`, `user_hospital`, `operation_log` |

---

## Design Decisions

| # | Question | Answer |
|---|---|---|
| 1 | Who can create slots? | Scheduler (scoped to their hospitals via `USER_HOSPITAL`) and SA-root (all hospitals). |
| 2 | How does the hospital list get scoped? | `GET /hospitals` — Backend checks `g.auth_role`; returns only `USER_HOSPITAL`-linked hospitals for Schedulers; all hospitals for SA-root. |
| 3 | What are valid `department` values? | Enum: `UTI` (ICU) · `PA` (Urgent Care) · `PS` (Emergency Room). |
| 4 | What are valid `type` values? | Enum: `PM` (Physician On-Call) · `PE` (Nursing Duty) · `CC` (Operating Room) · `CM` (Outpatient). |
| 5 | Is `mediciner_crm` validated at slot creation? | No — it is stored as-is (free text, format `CRM/UF XXXXXX`). Live CRM lookup via CFM API is not yet available (licence required). |
| 6 | What happens when deleting an occupied slot? | The frontend shows a pre-DELETE confirmation dialog with an extra warning when `mediciner_crm` is set. The backend DELETE always succeeds; there is no server-side block. |
| 7 | What OPERATION_LOG entries are written? | `CREATE_SLOT`, `UPDATE_SLOT`, `DELETE_SLOT` — one row per write, same transaction. |
| 8 | Is pagination server-side? | Yes — `GET /slots` returns `{items, total, page, per_page, pages}`. Default 20 per page. |
| 9 | What is the Agenda view's default period? | Current calendar week (Monday–Sunday). Other options: +2d, +4d, +8d, 1W, 2W, 1M, Custom date range. |

---

## Mermaid — quick preview

```mermaid
sequenceDiagram
    autonumber
    actor Sched as Scheduler [Sched]
    participant UI
    participant BFF
    participant BE as Backend
    participant DB as Database

    rect rgb(241,245,249)
        Note over Sched,BFF: Phase 1 — Session Check (Scheduler already authenticated)
        Sched->>UI: Navigate to /slots
        UI->>BFF: GET /bff/auth/me [cookie]
        BFF-->>UI: 200 {sub, name, role: Scheduler}
        UI-->>Sched: Render Slot Management page (Table view, current week)
    end

    rect rgb(240,253,244)
        Note over Sched,DB: Phase 2 — Create a Slot
        Sched->>UI: Click "+ New Slot"
        UI->>BFF: GET /bff/hospitals [cookie]
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
        BE->>DB: SELECT hospital JOIN user_hospital WHERE user_uuid = sub
        DB-->>BE: [{uuid, name, …}]
        BE-->>BFF: 200 [{uuid, name, …}]
        BFF-->>UI: Scoped hospital list
        UI-->>Sched: Create Slot modal — hospital dropdown, date, type, department, CRM (optional)
        Sched->>UI: Fill fields, click Save
        UI->>BFF: POST /bff/slots {hospital_uuid, department, type, date, mediciner_crm?} [cookie]
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
        BE->>DB: INSERT slot {uuid, hospital_uuid, department, type, date, mediciner_crm, created_by, created_at}
        DB-->>BE: Row created {uuid}
        BE->>DB: INSERT operation_log {CREATE_SLOT, entity_id: slot.uuid, performedBy: sub}
        DB-->>BE: Logged
        BE-->>BFF: 201 {uuid, hospital_uuid, department, type, date, mediciner_crm, created_at}
        BFF-->>UI: Slot created
        UI-->>Sched: Modal closes — slot appears in current view
    end

    rect rgb(241,245,249)
        Note over Sched,DB: Phase 3 — List Slots (Table view)
        Sched->>UI: Navigate date window (← / Today / →)
        UI->>BFF: GET /bff/slots?from_date=&to_date=&page=&per_page=20 [cookie]
        BFF->>BE: Forward
        BE->>DB: SELECT slot WHERE date BETWEEN from AND to ORDER BY date ASC LIMIT 20 OFFSET n
        DB-->>BE: [{slot rows}] + total count
        BE-->>BFF: 200 {items, total, page, per_page, pages}
        BFF-->>UI: Paginated slot list
        UI-->>Sched: Table with type badges + department tags + Edit / Delete actions
    end

    rect rgb(241,245,249)
        Note over Sched,DB: Phase 3b — List Slots (Agenda view)
        Sched->>UI: Switch to Agenda, select period (e.g. "2 Weeks")
        UI->>BFF: GET /bff/slots?from_date=&to_date=&per_page=500 [cookie]
        BFF->>BE: Forward
        BE->>DB: SELECT slot WHERE date BETWEEN from AND to ORDER BY date ASC
        DB-->>BE: [{slot rows}]
        BE-->>BFF: 200 {items, …}
        BFF-->>UI: All slots for period
        UI-->>Sched: Day-card grid — each card shows slot type badges + department tags
    end

    rect rgb(255,251,235)
        Note over Sched,DB: Phase 4 — Update a Slot
        Sched->>UI: Click Edit on a slot row
        UI-->>Sched: Edit Slot modal — pre-filled with current values
        Sched->>UI: Change fields, click Save
        UI->>BFF: PUT /bff/slots/{uuid} {department?, type?, date?, mediciner_crm?} [cookie]
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
        BE->>DB: UPDATE slot SET … WHERE uuid = {uuid}
        DB-->>BE: Updated
        BE->>DB: INSERT operation_log {UPDATE_SLOT, entity_id: uuid, performedBy: sub}
        DB-->>BE: Logged
        BE-->>BFF: 200 {updated slot}
        BFF-->>UI: Slot updated
        UI-->>Sched: Row / card refreshed in-place
    end

    rect rgb(254,242,242)
        Note over Sched,DB: Phase 5 — Delete a Slot
        Sched->>UI: Click Delete on a slot row
        alt Slot has mediciner_crm set (occupied)
            UI-->>Sched: Confirm dialog — "This slot is assigned to CRM/SP 12345. Delete anyway?"
        else Slot is unoccupied
            UI-->>Sched: Confirm dialog — "Delete this slot?"
        end
        Sched->>UI: Confirm
        UI->>BFF: DELETE /bff/slots/{uuid} [cookie]
        BFF->>BE: Forward + X-Auth-Sub, X-Auth-Role
        BE->>DB: DELETE FROM slot WHERE uuid = {uuid}
        DB-->>BE: Deleted
        BE->>DB: INSERT operation_log {DELETE_SLOT, entity_id: uuid, performedBy: sub}
        DB-->>BE: Logged
        BE-->>BFF: 200 {deleted: true}
        BFF-->>UI: Slot removed
        UI-->>Sched: Slot disappears from current view
    end
```

---

## PlantUML — canonical diagram

```plantuml
@startuml UC03-Scheduler-Manages-Slots
!theme plain
skinparam sequenceMessageAlign center
skinparam defaultFontSize 12
skinparam BoxPadding 12
skinparam ParticipantPadding 20
skinparam SequenceGroupBodyBackgroundColor transparent

title UC-03: Scheduler Manages Slots (Create / List / Update / Delete)

actor "Scheduler\n[Sched]" as Sched
participant "UI"           as UI
participant "BFF"          as BFF
participant "Backend"      as BE
database    "Database"     as DB

autonumber

== Phase 1: Session Check ==

Sched ->  UI   : Navigate to /slots
UI    ->  BFF  : GET /bff/auth/me [cookie]
BFF   --> UI   : 200 {sub, name, role: Scheduler}
UI    --> Sched : Slot Management page (Table, current week)

== Phase 2: Create a Slot ==

Sched ->  UI   : Click "+ New Slot"
UI    ->  BFF  : GET /bff/hospitals [cookie]
BFF   ->  BE   : Forward + X-Auth-Sub, X-Auth-Role
BE    ->  DB   : SELECT hospital JOIN user_hospital\nWHERE user_uuid = sub
DB    --> BE   : [{uuid, name, …}]
BE    --> BFF  : 200 [{uuid, name, …}]
BFF   --> UI   : Scoped hospital list
UI    --> Sched : Create Slot modal

Sched ->  UI   : Fill fields (hospital, date, type, department,\noptional mediciner_crm), click Save
UI    ->  BFF  : POST /bff/slots\n{hospital_uuid, department, type,\ndate, mediciner_crm?} [cookie]
BFF   ->  BE   : Forward + X-Auth-Sub, X-Auth-Role
BE    ->  DB   : INSERT slot\n{uuid, hospital_uuid, department, type,\ndate, mediciner_crm, created_by, created_at}
DB    --> BE   : Row created {uuid}
BE    ->  DB   : INSERT operation_log\n{CREATE_SLOT, entity_id: uuid, performedBy: sub}
DB    --> BE   : Logged
BE    --> BFF  : 201 {slot JSON}
BFF   --> UI   : Slot created
UI    --> Sched : Modal closes — slot visible in view

== Phase 3: List Slots (Table view) ==

Sched ->  UI   : Navigate date window (← / Today / →)
UI    ->  BFF  : GET /bff/slots?from_date=&to_date=\n&page=&per_page=20 [cookie]
BFF   ->  BE   : Forward
BE    ->  DB   : SELECT slot WHERE date BETWEEN ...\nORDER BY date ASC LIMIT 20 OFFSET n
DB    --> BE   : [{slot rows}] + total
BE    --> BFF  : 200 {items, total, page, per_page, pages}
BFF   --> UI   : Paginated list
UI    --> Sched : Table — type badges, department tags, Edit/Delete

== Phase 3b: List Slots (Agenda view) ==

Sched ->  UI   : Switch to Agenda, select period
UI    ->  BFF  : GET /bff/slots?from_date=&to_date=\n&per_page=500 [cookie]
BFF   ->  BE   : Forward
BE    ->  DB   : SELECT slot WHERE date BETWEEN ...\nORDER BY date ASC
DB    --> BE   : [{slot rows}]
BE    --> BFF  : 200 {items, …}
BFF   --> UI   : All slots for period
UI    --> Sched : Day-card grid with slot summaries

== Phase 4: Update a Slot ==

Sched ->  UI   : Click Edit on a row
UI    --> Sched : Edit Slot modal (pre-filled)
Sched ->  UI   : Change fields, click Save
UI    ->  BFF  : PUT /bff/slots/{uuid}\n{department?, type?, date?, mediciner_crm?} [cookie]
BFF   ->  BE   : Forward + X-Auth-Sub, X-Auth-Role
BE    ->  DB   : UPDATE slot SET …\nWHERE uuid = {uuid}
DB    --> BE   : Updated
BE    ->  DB   : INSERT operation_log\n{UPDATE_SLOT, entity_id: uuid, performedBy: sub}
DB    --> BE   : Logged
BE    --> BFF  : 200 {updated slot}
BFF   --> UI   : Slot updated
UI    --> Sched : Row / card refreshed in-place

== Phase 5: Delete a Slot ==

Sched ->  UI   : Click Delete on a row

alt Slot has mediciner_crm set (occupied)
    UI    --> Sched : Confirm dialog with occupied-slot warning
else Slot is unoccupied
    UI    --> Sched : Standard confirm dialog
end

Sched ->  UI   : Confirm
UI    ->  BFF  : DELETE /bff/slots/{uuid} [cookie]
BFF   ->  BE   : Forward + X-Auth-Sub, X-Auth-Role
BE    ->  DB   : DELETE FROM slot WHERE uuid = {uuid}
DB    --> BE   : Deleted
BE    ->  DB   : INSERT operation_log\n{DELETE_SLOT, entity_id: uuid, performedBy: sub}
DB    --> BE   : Logged
BE    --> BFF  : 200 {deleted: true}
BFF   --> UI   : Removed
UI    --> Sched : Slot disappears from view

note over Sched : SA-root follows the same flow\nbut sees all hospitals (no USER_HOSPITAL scope)

@enduml
```

---

## API Endpoints (UC-03)

| Method | Path | Body / Params | Success | Error |
|---|---|---|---|---|
| `GET` | `/bff/hospitals` | — | 200 `[{uuid, name, cnpj, …}]` scoped by role | 401 |
| `POST` | `/bff/slots` | `{hospital_uuid, department, type, date, mediciner_crm?}` | 201 `{slot JSON}` | 400 invalid enum · 401 |
| `GET` | `/bff/slots` | `?hospital_uuid&from_date&to_date&page&per_page` | 200 `{items, total, page, per_page, pages}` | 401 |
| `PUT` | `/bff/slots/{uuid}` | `{department?, type?, date?, mediciner_crm?}` | 200 `{slot JSON}` | 400 · 404 · 401 |
| `DELETE` | `/bff/slots/{uuid}` | — | 200 `{deleted: true}` | 404 · 401 |

---

## OPERATION_LOG Entries (UC-03)

| Action | Entity type | Entity ID | Written when |
|---|---|---|---|
| `CREATE_SLOT` | `SLOT` | `slot.uuid` | Slot inserted |
| `UPDATE_SLOT` | `SLOT` | `slot.uuid` | Any field mutated |
| `DELETE_SLOT` | `SLOT` | `slot.uuid` | Slot removed |
