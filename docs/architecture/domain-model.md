# Domain Model

```mermaid
erDiagram
    USER {
        uuid      uuid             PK
        string    name
        string    telephone
        string    email
        string    role             "SA-root | Scheduler | Mediciner"
        string    status           "pending | pending_approval | active | inactive"
        timestamp created_at       "UTC — when the invitation was created"
        timestamp otp_dispatched_at "UTC — when OTP was published to the queue (nullable)"
        timestamp otp_verified_at   "UTC — when invitee submitted the correct OTP (nullable)"
        timestamp activated_at      "UTC — when SA approved and account became active (nullable)"
    }
    USER_HOSPITAL {
        uuid   userId     FK
        string hospitalId FK
        string scope      "Scheduler | Mediciner"
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
        string cnpj PK
        string nome
        string localizacao
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
    MEDICINER {
        string  cpf          PK
        uuid    userId       FK
        string  matricula
        string  crm
        string  especialidade
        int     anoFormatura
        boolean kycVerified
    }
    SLOT {
        string  id           PK
        date    periodo
        string  tipo         "PM | PE | CC | CM"
        string  especialidade
        int     totalAlocar
        decimal valorPagar
        string  departmentId FK
    }
    ESCALA {
        string id         PK
        date   data
        string hospitalId FK
    }

    USER           ||--o{  USER_HOSPITAL  : "scoped to"
    HOSPITAL       ||--o{  USER_HOSPITAL  : "scoped by"
    USER           ||--o{  OPERATION_LOG  : "performs"
    USER           ||--o|  SCHEDULER      : "is"
    USER           ||--o|  MEDICINER      : "is"
    HOSPITAL       ||--o{  DEPARTMENT     : "contains"
    HOSPITAL       }o--o{  SCHEDULER      : "managed by"
    HOSPITAL       }o--o{  MEDICINER      : "employs / contracts"
    DEPARTMENT     ||--o{  SLOT           : "owns"
    ESCALA         ||--o{  SLOT           : "groups"
```

## Entity Notes

| Entity | Notes |
|---|---|
| `User` | Base auth entity for all actors. `uuid` is the platform identity — embedded in JWT `sub` and in every `OPERATION_LOG` entry. The four timestamp fields track the full invitation lifecycle; all nullable except `created_at`. SA-root has no separate domain entity. |
| `User.status` | `pending` → OTP issued, awaiting invitee verification. `pending_approval` → invitee verified OTP, awaiting SA approval. `active` → SA approved, user can log in. `inactive` → invitation cancelled by SA (can be re-invited; same UUID preserved). |
| `User_Hospital` | Junction table that restricts Scheduler and Mediciner to their assigned hospitals. SA-root bypasses this check (platform-wide access). A Scheduler managing two hospitals has two rows. |
| `Permission` | Internal RBAC table seeded at deployment, managed by SA-root. Maps role → resource → action. Checked by Backend on every protected request. Example seed rows: `(SA-root, USER, CREATE)` · `(Scheduler, SLOT, CREATE)` · `(Mediciner, SLOT, UPDATE)`. |
| `Operation_Log` | Append-only audit table. Written in the **same DB transaction** as the main operation. Never updated or deleted. `performedBy` is the USER.uuid of the actor. `correlationId` matches the `X-Correlation-ID` header injected by the BFF. |
| `Hospital` | Registered by SysAdmin. CNPJ is the Brazilian legal entity identifier. |
| `Department` | Three confirmed types: **UTI** (Unidade de Terapia Intensiva / ICU) · **PA** (Pronto Atendimento / Urgent Care) · **PS** (Pronto Socorro / Emergency Room). |
| `Scheduler` | Registered by SysAdmin. Extends USER. `tipos` field scope TBD. |
| `Mediciner` | Extends USER. KYC verification process TBD. |
| `Slot` | Unit of work. Types: **PM** Physician On-Call · **PE** Nursing Duty · **CC** Operating Room · **CM** Outpatient Consultation. |
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
