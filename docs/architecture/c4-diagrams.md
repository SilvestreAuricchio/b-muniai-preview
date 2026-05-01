# C4 Architecture Diagrams

> Design phase — technology choices are marked **TBD**. Diagrams will be updated as decisions are made.

---

## Level 1 — System Context

Who uses MuniAI and what external systems does it depend on.

```mermaid
C4Context
    title MuniAI — System Context

    Person(sysAdmin, "System Administrator", "Registers and manages hospitals and schedulers on the platform")
    Person(mediciner, "Mediciner (Doctor)", "Registers credentials and profile; browses and accepts shift slots")
    Person(scheduler, "Scheduler", "Creates and manages shift slots (escalas) on behalf of hospitals")
    Person(patient, "Patient User", "Role TBD — scope and interactions not yet defined")

    System(muniAI, "MuniAI", "Medical staffing and shift-scheduling platform for Brazilian hospitals")

    System_Ext(googleId, "Google Identity", "Provides authentication and authorization for all users (OAuth 2.0 / OIDC)")

    Rel(sysAdmin, muniAI, "Manages hospitals and schedulers")
    Rel(mediciner, muniAI, "Registers profile; browses and accepts slots")
    Rel(scheduler, muniAI, "Creates and manages shift slots")
    Rel(patient, muniAI, "TBD")
    Rel(muniAI, googleId, "Delegates authentication", "OAuth 2.0 / OIDC")
```

---

## Level 2 — Containers

Internal building blocks of the MuniAI platform.

```mermaid
C4Container
    title MuniAI — Containers

    Person(sysAdmin, "System Administrator")
    Person(mediciner, "Mediciner (Doctor)")
    Person(scheduler, "Scheduler")

    System_Ext(googleId, "Google Identity", "OAuth 2.0 / OIDC")

    System_Boundary(muniAI, "MuniAI Platform") {
        Container(webApp, "Web Application", "TBD", "Role-based UI for Admin, Mediciner, and Scheduler; renders escalas, slots, and financial views")
        Container(apiServer, "API Server", "TBD", "REST API — exposes /hospital, /mediciner, /scheduler, /slot endpoints; enforces RBAC; orchestrates slot matching and escala logic")
        ContainerDb(db, "Database", "TBD", "Persists hospitals, departments, medicineres, schedulers, slots, and escalas")
        Container(authService, "Auth Service", "TBD", "Exchanges Google ID tokens for scoped platform sessions; enforces role-based access control")
    }

    Rel(sysAdmin, webApp, "Uses", "HTTPS")
    Rel(mediciner, webApp, "Uses", "HTTPS")
    Rel(scheduler, webApp, "Uses", "HTTPS")
    Rel(webApp, apiServer, "API calls", "HTTPS / JSON")
    Rel(webApp, authService, "Initiates login / token exchange", "OAuth 2.0 redirect")
    Rel(apiServer, db, "Reads / writes")
    Rel(apiServer, authService, "Validates session token on each request")
    Rel(authService, googleId, "Validates tokens and fetches user identity", "OIDC")
```

---

## Open Questions

See `Notes.md` for unresolved design decisions that may affect these diagrams.
