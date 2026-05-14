# Domain Model

```mermaid
erDiagram
    USER {
        uuid      uuid             PK
        string    name
        string    telephone
        string    email
        string    role             "SA-root | Scheduler | Mediciner"
        string    status           "pending | pending_approval | active | disabled | inactive"
        timestamp created_at       "UTC — when the invitation was created"
        timestamp otp_dispatched_at "UTC — when OTP was published to the queue (nullable)"
        timestamp otp_verified_at   "UTC — when invitee submitted the correct OTP (nullable)"
        timestamp activated_at      "UTC — when SA approved and account became active (nullable)"
    }
    USER_HOSPITAL {
        uuid   user_uuid     FK
        uuid   hospital_uuid FK
        string scope         "Scheduler | Mediciner"
    }
    PERMISSION {
        uuid   id       PK
        string role     "SA-root | Scheduler | Mediciner"
        string resource "USER | HOSPITAL | SLOT | ESCALA | REPORT …"
        string action   "CREATE | READ | UPDATE | DELETE | REPORT | APPROVE …"
        json   constraint "optional field-level restriction (future)"
    }
    OPERATION_LOG {
        uuid      id            PK
        uuid      performedBy   FK
        string    action        "CREATE_USER | VERIFY_OTP | APPROVE_USER | CREATE_HOSPITAL …"
        string    entityType
        uuid      entityId
        json      payload
        timestamp performedAt   "UTC"
        string    correlationId "X-Correlation-ID propagated from BFF"
    }
    HOSPITAL {
        uuid     uuid       PK   "surrogate key — generated on creation"
        string   cnpj       AK   "alternate key — 14 chars, no punctuation, UNIQUE"
        string   name
        string   address
        string[] slot_types      "UTI | PS | PA | CC | ENF — required slot types"
    }
    DEPARTMENT {
        string id         PK
        string tipo       "UTI | PA | PS"
        string hospitalId FK
    }
    SCHEDULER {
        string cpf       PK
        uuid   userId    FK
        string matricula
        string tipos     "TBD — scope of departments managed"
    }
    MEDICINER_PROFILE {
        uuid   user_uuid  PK "FK → app_user.uuid"
        string cpf        "11 digits UNIQUE — CPF (official check-digit validated)"
        string email      "UNIQUE — mirrors app_user.email"
        string specialty  "free text, nullable"
        string crm_state  "2-letter UF code, nullable"
        string crm_number "numeric string, nullable"
    }
    SLOT {
        uuid      uuid          PK
        uuid      hospital_uuid FK
        string    department    "UTI | PA | PS"
        string    type          "PM | PE | CC | CM"
        date      date
        string    mediciner_crm "nullable — CRM/UF XXXXXX when filled"
        uuid      created_by    FK
        timestamp created_at
    }
    HOSPITAL_AUDIT_LOG {
        string    _id          "MongoDB ObjectId"
        uuid      hospitalId   "indexed asc"
        uuid      userId       "indexed asc"
        string    action       "CREATED | UPDATED"
        timestamp timestamp    "indexed desc"
        json      before       "null for CREATED; previous state for UPDATED"
        json      after        "full hospital state after the operation"
    }
    ESCALA {
        string id         PK
        date   data
        string hospitalId FK
    }

    USER           ||--o{  USER_HOSPITAL      : "scoped to"
    HOSPITAL       ||--o{  USER_HOSPITAL      : "scoped by"
    USER           ||--o{  OPERATION_LOG      : "performs"
    USER           ||--o|  SCHEDULER          : "is"
    USER           ||--|{  MEDICINER_PROFILE  : "has"
    HOSPITAL       ||--o{  DEPARTMENT         : "contains"
    HOSPITAL       }o--o{  SCHEDULER          : "managed by"
    HOSPITAL       ||--o{  SLOT               : "has"
    HOSPITAL       ||--o{  HOSPITAL_AUDIT_LOG : "audited by"
    SLOT           }o--o|  MEDICINER_PROFILE  : "assigned to"
    ESCALA         ||--o{  SLOT               : "groups"
```

## Entity Notes

| Entity | Notes |
|---|---|
| `User` | Base auth entity for all actors. `uuid` is the platform identity — embedded in JWT `sub` and in every `OPERATION_LOG` entry. The four timestamp fields track the full invitation lifecycle; all nullable except `created_at`. SA-root has no separate domain entity. Persisted in PostgreSQL table `app_user`. |
| `User.status` | `pending` → OTP issued, awaiting invitee verification. `pending_approval` → invitee verified OTP, awaiting SA approval. `active` → SA approved, user can log in. `disabled` → SA temporarily suspended the account; user cannot log in; reversible via Re-enable. `inactive` → permanently deactivated by SA (or invitation cancelled); record preserved for audit; can be re-invited. |
| `User_Hospital` | Junction table that restricts Scheduler and Mediciner to their assigned hospitals. SA-root bypasses this check (platform-wide access). A Scheduler managing two hospitals has two rows. |
| `Permission` | Internal RBAC table seeded at deployment, managed by SA-root. Maps role → resource → action. Checked by Backend on every protected request. Example seed rows: `(SA-root, USER, CREATE)` · `(Scheduler, SLOT, CREATE)` · `(Mediciner, SLOT, UPDATE)`. |
| `Operation_Log` | Append-only audit table. Written in the **same DB transaction** as the main operation. Never updated or deleted. `performedBy` is the USER.uuid of the actor. `correlationId` matches the `X-Correlation-ID` header injected by the BFF. |
| `Hospital` | `uuid` is the surrogate primary key (generated on creation). `cnpj` is the Brazilian legal entity identifier (14 chars, no punctuation); per IN RFB 2.229/2024 positions 1–12 may be alphanumeric [A-Z0-9], only positions 13–14 (check digits) must remain numeric. Character value formula: `ord(c) − 48`. CNPJ is the alternate key — unique, immutable after creation. Validated server-side via `domain/validation/tax_id.py` and client-side via `shared/taxId.ts`; country controlled by `APP_COUNTRY` env var (default `BR`). Created standalone via `POST /hospitals` (SA-root only). Editable via `PUT /hospitals/<uuid>` (name, address, slot_types). `slot_types` is multi-value from `SlotType` enum: **UTI** (ICU) · **PS** (Emergency Room) · **PA** (Urgent Care) · **CC** (Operating Room) · **ENF** (Ward). Persisted in PostgreSQL `hospital` (uuid PK, cnpj UNIQUE) and `user_hospital` (hospital_uuid FK). **UI:** list at `/hospitals` shows a status dot per row; "View →" opens `HospitalDetailOverlay` (modal with unified view/edit card). Detail route `/hospitals/:uuid` also uses the unified card. Address lookup via ViaCEP — neighborhood rendered as `- bairro -`. `status` (active / inactive / disabled) is UI-ready but not yet a backend-persisted field. |
| `Department` | Three confirmed types: **UTI** (Unidade de Terapia Intensiva / ICU) · **PA** (Pronto Atendimento / Urgent Care) · **PS** (Pronto Socorro / Emergency Room). |
| `Scheduler` | Registered by SysAdmin. Extends USER. `tipos` field scope TBD. |
| `Mediciner_Profile` | Profile table for Mediciner-role users. `user_uuid` is both the PK and FK to `app_user`. `cpf` (11-digit Brazilian individual tax ID) is UNIQUE and validated with the official two-check-digit algorithm on both backend (`domain/validation/tax_id.py`) and frontend (`taxId.ts`). `crm_state` is the 2-letter UF code; `crm_number` is the numeric council registration number. CRM auto-fill (CFM API) requires a formal agreement — a documented no-op adapter is in place pending licensing. Invitation reuses UC-01 with `role=Mediciner`; profile row is created atomically in the same request. |
| `Slot` | Unit of work assigned to a hospital. `department` enum: **UTI** (ICU) · **PA** (Urgent Care) · **PS** (Emergency Room). `type` enum: **PM** (Physician On-Call) · **PE** (Nursing Duty) · **CC** (Operating Room) · **CM** (Outpatient). `mediciner_crm` is nullable — set when a Mediciner is assigned. Frontend warns before deleting an occupied slot. Visible on the Scheduler's `/slots` page in Table and Agenda views. |
| `Hospital_Audit_Log` | MongoDB collection (`hospital_audit_log`) — async audit trail for all hospital mutations. Published to RabbitMQ queue `hospital.audit` by the backend use cases; consumed and persisted by `hospital-audit-worker`. `before=null` for CREATED; previous full state for UPDATED. Three indexes: `hospitalId` asc, `userId` asc, `timestamp` desc. Never updated or deleted. |
| `Escala` | Schedule grouping slots for a hospital period. Sub-modules TBD. |

## Authorization Flow (every protected request)

1. Validate JWT signature (BFF secret key / IdP public key).
2. Extract `sub` (USER.uuid) and `role` from claims.
3. Check `PERMISSION` — deny if `(role, resource, action)` has no matching row.
4. For Scheduler / Mediciner: check `USER_HOSPITAL` — deny if user has no row for the target hospital.
5. Execute operation; write `OPERATION_LOG` in the same transaction.

## Bootstrap vs Invited Users

| Type | Auth | Source of truth |
|---|---|---|
| **Bootstrap SA** | Email in `authorized_psas.yaml` | Static file; JWT sub = Google sub |
| **Invited user** | Active record in database | UC-01 flow; JWT sub = USER.uuid |
