# C4 Architecture Diagrams

---

## Level 1 — System Context

Who uses MuniAI and what external systems does it depend on.

```mermaid
C4Context
    title MuniAI — System Context

    Person(sysAdmin,   "System Administrator", "Manages hospitals, schedulers, and invitations")
    Person(mediciner,  "Mediciner (Doctor)",   "Registers credentials; browses and accepts shift slots")
    Person(scheduler,  "Scheduler",            "Creates and manages shift slots for hospitals")
    Person(patient,    "Patient User",         "Role TBD")

    System(muniAI, "MuniAI", "Medical staffing and shift-scheduling platform for Brazilian hospitals")

    System_Ext(googleId, "Google Identity", "OAuth 2.0 / OIDC — authenticates all platform users")
    System_Ext(smtp,     "SMTP Server",     "Delivers OTP invitation emails and activation confirmations")

    Rel(sysAdmin,  muniAI,   "Manages hospitals, schedulers, and invitations")
    Rel(mediciner, muniAI,   "Registers profile; browses and accepts slots")
    Rel(scheduler, muniAI,   "Creates and manages shift slots")
    Rel(patient,   muniAI,   "TBD")
    Rel(muniAI,    googleId, "Delegates authentication",     "OAuth 2.0 / OIDC")
    Rel(muniAI,    smtp,     "Sends OTP + activation emails","SMTP / STARTTLS")
```

---

## Level 2 — Containers

Internal building blocks of the MuniAI platform.

```mermaid
C4Container
    title MuniAI — Containers

    Person(user, "Any platform user")
    System_Ext(googleId, "Google Identity", "OAuth 2.0 / OIDC")
    System_Ext(smtp,     "SMTP Server",     "Gmail / any SMTP")

    System_Boundary(muniAI, "MuniAI Platform") {

        Container(nginx,    "API Gateway",        "nginx",              "SSL termination (HTTPS 443); routes to upstream pools; load-balances backend replicas")
        Container(webApp,   "Web Application",    "React + Vite",       "Microfrontend shell: Dashboard, User CRUD, Reports, Logs. Public route: /activate/:uuid")
        Container(bff,      "BFF",                "Python · Flask",     "Session facade; Google OAuth; JWT issuance; forwards requests to Backend")
        Container(backend,  "Backend API",        "Python · Flask",     "Domain logic; RBAC; UC implementations; OPERATION_LOG writes. Swagger at /apidocs")
        Container(dispatcher,"OTP Dispatcher",    "Python · pika",      "RabbitMQ consumer; delivers OTP via email + WhatsApp + SMS; ACK/NACK retry")

        ContainerDb(redis,    "Redis",     "Redis 7",       "OTP challenge store (TTL); session cache")
        ContainerDb(rabbit,   "RabbitMQ",  "RabbitMQ 3",    "otp.challenge queue (DLX → otp.challenge.failed DLQ)")
        ContainerDb(postgres, "PostgreSQL","PostgreSQL 16",  "USER, HOSPITAL, DEPARTMENT, SLOT, ESCALA, PERMISSION, USER_HOSPITAL, OPERATION_LOG")
        ContainerDb(mongo,    "MongoDB",   "MongoDB 7",      "OPERATION_LOG (audit, append-only)")

        Container(prometheus,"Prometheus", "prom/prometheus","Scrapes /metrics from all services")
        Container(grafana,   "Grafana",    "grafana/grafana", "Metrics dashboards")
    }

    Rel(user,       nginx,      "HTTPS",          "443")
    Rel(nginx,      webApp,     "HTTP internal",  "30000")
    Rel(nginx,      bff,        "HTTP internal",  "30001")
    Rel(nginx,      backend,    "HTTP internal",  "30002 (N replicas)")
    Rel(bff,        googleId,   "OAuth callback", "OIDC")
    Rel(bff,        backend,    "Internal REST",  "HTTP")
    Rel(backend,    redis,      "OTP store",      "RESP")
    Rel(backend,    rabbit,     "Publish OTP_CHALLENGE", "AMQP")
    Rel(backend,    postgres,   "Domain data",    "SQLAlchemy")
    Rel(backend,    mongo,      "Audit log",      "pymongo")
    Rel(dispatcher, rabbit,     "Consume OTP_CHALLENGE", "AMQP")
    Rel(dispatcher, smtp,       "OTP + confirmation emails","SMTP STARTTLS")
    Rel(prometheus, backend,    "Scrape /metrics")
    Rel(prometheus, bff,        "Scrape /metrics")
    Rel(grafana,    prometheus, "PromQL")
```

---

## Key Design Decisions

| Concern | Decision |
|---|---|
| **Auth** | Google OAuth via BFF; bootstrap SAs in YAML; all other users resolved from DB (`active` status required) |
| **JWT** | `sub` = USER.uuid (or Google sub for bootstrap SA); `role` from DB |
| **OTP delivery** | Async via RabbitMQ — Redis stores OTP immediately so `verify()` is instant; consumer delivers all channels |
| **Retry / DLQ** | Transient failures → NACK requeue; permanent failures (bad credentials, invalid address) → DLQ `otp.challenge.failed` |
| **Activation link** | OTP email includes `APP_URL/activate/:uuid` button; invitee verifies on public page without logging in |
| **Activation email** | Sent by `ApproveUserUseCase` after SA approves; notifies invitee they can now sign in |
| **RBAC** | Internal: PERMISSION table (role → resource → action) + USER_HOSPITAL for hospital-scoped roles |
| **Audit** | OPERATION_LOG written in same DB transaction as the main write; append-only |
