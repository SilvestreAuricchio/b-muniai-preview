# Domain Model

> Derived from the initial Miro board and use-case definitions. Fields marked `TBD` require a decision.

```mermaid
erDiagram
    USER {
        uuid   uuid   PK
        string name
        string telephone
        string email
        string role   "SA-root | Scheduler | Mediciner"
        string status "pending | active | inactive"
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
        uuid      id          PK
        uuid      performedBy FK
        string    action      "CREATE_USER | ACTIVATE_USER | CREATE_HOSPITAL …"
        string    entityType
        uuid      entityId
        json      payload
        timestamp performedAt "UTC"
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
| `User` | Base auth entity for all actors. `uuid` is the platform identity — embedded in JWT `sub` claim and in every `OPERATION_LOG` entry. `role` (coarse grain) is also carried in the JWT. SA-root has no separate domain entity. |
| `User_Hospital` | Junction table that restricts Scheduler and Mediciner to their assigned hospitals. SA-root bypasses this check (platform-wide access). A Scheduler managing two hospitals has two rows. |
| `Permission` | Internal RBAC table seeded at deployment, managed by SA-root. Maps role → resource → action. Checked by Backend on every protected request. Supports future field-level constraints via the `constraint` JSON column. Example seed rows: `(SA-root, USER, CREATE)` · `(Scheduler, SLOT, CREATE)` · `(Mediciner, SLOT, UPDATE)`. |
| `Operation_Log` | Append-only audit table. Written in the **same DB transaction** as the main operation — if the main write rolls back, the log entry rolls back with it. Never updated or deleted. `performedBy` is the USER.uuid of the actor; for system-initiated actions (e.g. IaC seed), a reserved system UUID is used. |
| `Hospital` | Registered by SysAdmin. CNPJ is the Brazilian legal entity identifier. |
| `Department` | Three confirmed types: **UTI** (Unidade de Terapia Intensiva / ICU) · **PA** (Pronto Atendimento / Urgent Care) · **PS** (Pronto Socorro / Emergency Room). Additional types TBD. |
| `Scheduler` | Registered by SysAdmin. Extends USER. `tipos` field scope TBD. |
| `Mediciner` | Extends USER. KYC verification process TBD. |
| `Slot` | Unit of work. Types: **PM** Physician On-Call · **PE** Nursing Duty · **CC** Operating Room · **CM** Outpatient Consultation. |
| `Escala` | Schedule grouping slots for a hospital period. Sub-modules TBD. |

## Authorization Flow (every protected request)

1. Validate JWT signature (IdP public key).
2. Extract `sub` (USER.uuid) and `role` from claims.
3. Check `PERMISSION` — deny if `(role, resource, action)` has no matching row.
4. For Scheduler / Mediciner: check `USER_HOSPITAL` — deny if user has no row for the target hospital.
5. Execute operation; write `OPERATION_LOG` in the same transaction.
