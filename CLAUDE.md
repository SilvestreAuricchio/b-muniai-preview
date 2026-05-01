# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**MuniAI** — a medical staffing marketplace for Brazilian hospitals. The platform has two complementary goals: maximize slot coverage for hospitals (ensuring every shift is filled) and give medical professionals the best way to allocate their working time across institutions. Currently in the architectural design phase; no application code exists yet.

## Domain Summary

| Actor | Registered by | Role |
|---|---|---|
| System Administrator | — | Manages hospitals and schedulers |
| Mediciner (Doctor) | Self | Registers credentials; browses and accepts shift slots |
| Scheduler | SysAdmin | Creates and manages shift slots for one or more hospitals |
| Patient User | TBD | Role not yet defined |

Core entities: `User` → (`Scheduler` | `Mediciner`), `Hospital` → `Department` → `Slot` → `Escala`. See `docs/architecture/domain-model.md`.

`User` is the base auth entity for all actors (SA-root, Scheduler, Mediciner). Its `uuid` is embedded in JWT claims and in every write operation's audit record. SA-root has no separate domain entity — the `role` field on `User` is sufficient.

**Authentication vs Authorization split:**
- IdP (Google / OTP / WhatsApp) handles authentication only — who you are.
- JWT carries `sub` (USER.uuid) + `role` (SA-root | Scheduler | Mediciner). No hospital IDs or permissions in the token.
- Authorization is fully internal: coarse via `PERMISSION` table (role → resource → action); hospital scope via `USER_HOSPITAL` table.
- Every protected request: validate JWT → check PERMISSION → check USER_HOSPITAL (scoped roles only) → execute + write OPERATION_LOG atomically.

**OPERATION_LOG convention:** every significant write (CREATE, UPDATE, DELETE on domain entities) must insert one OPERATION_LOG row in the same DB transaction. Never update or delete log rows.

## Architecture Documentation

| File | Contents |
|---|---|
| `docs/index.html` | Local docs viewer — renders `.md` and `.uml` files; links each diagram to Mermaid Live or PlantUML Online. Serve with `python -m http.server` then open `http://localhost:8000/docs/`. Add new files to `docs/manifest.json`. |
| `docs/architecture/c4-diagrams.md` | C4 Level 1 (System Context) and Level 2 (Containers) diagrams |
| `docs/architecture/domain-model.md` | Entity model with field-level notes and open questions |
| `Notes.md` | Running architectural proposal log, organized by date (newest first) |

## Design Conventions (so far)

- REST API with resource-oriented routes: `/hospital`, `/mediciner`, `/scheduler`, `/slot`
- Brazilian identifiers: CPF (individual), CNPJ (company), CRM (medical license)
- Department types: **UTI** (ICU / *Unidade de Terapia Intensiva*), **PA** (Urgent Care / *Pronto Atendimento*), **PS** (Emergency Room / *Pronto Socorro*)
- Slot types: **PM** = Physician On-Call Shift, **PE** = Nursing Duty Shift, **CC** = Operating Room / Surgical Suite, **CM** = Outpatient Consultation
- All technology choices are **TBD** until explicitly decided

## Active Open Questions

See `TBD` markers in `docs/architecture/domain-model.md` for unresolved decisions that will affect implementation.
