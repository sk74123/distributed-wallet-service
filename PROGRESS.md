# Distributed Wallet Transfer System — Build Progress

## Status: Phase 2 Complete ✅ | Phase 3 In Progress

---

## Phase 1 — Project Foundation ✅

### Completed
- uv project setup with pyproject.toml
- FastAPI app skeleton with lifespan, exception handlers, health endpoint
- Async SQLAlchemy engine and session factory (asyncpg driver)
- Pydantic-settings config management with .env
- Structured logging setup
- ORM models: wallets, transfers, ledger_entries, outbox, processed_events
- Alembic async migration setup
- Dockerfile (multi-stage) and docker-compose (Postgres, Kafka KRaft, Redis)
- .env.example for onboarding
- Initial migration: create_initial_tables
- FK constraints and indexes migration: add_fk_constraints_and_indexes

### Key Decisions Made
- Domain-based project structure with layered architecture (router → service → repository)
- FK constraints added — monolith with single DB, DB-level integrity is correct
- Indexes on all FK columns — FKs do not auto-create indexes in Postgres
- Async SQLAlchemy + asyncpg throughout — nothing blocks the event loop
- Outbox pattern chosen over CDC (Debezium) — simpler for demo, noted in DECISIONS.md
- Background jobs as separate Docker services — independently deployable
- KRaft mode Kafka — no Zookeeper needed for local dev

---

## Phase 2 — Wallet Service ✅

### Completed
- POST /wallets — create wallet
- GET /wallets/{id} — get wallet
- POST /wallets/{id}/fund — add funds (test helper)
- Full layered stack: schemas.py, repository.py, service.py, router.py

### Key Decisions Made
- Repository returns None on not found — never raises, service decides
- Service never returns ORM objects — always converts to WalletResponse DTO
- Router is purely HTTP — no business logic, no exception handling
- Decimal serialized as string in JSON — avoids float precision issues in transit
- Two layers of validation:
  - Field rules (amount > 0, max 2 decimal places) → Pydantic schema
  - Business rules (wallet must exist) → service layer
- field_validator for decimal precision removed — Pydantic's decimal_places=2
  in Field() already handles it

---

## Phase 3 — Transfer Creation + Outbox 🔲

### To Build
- POST /transfers — create transfer + outbox event atomically
- GET /transfers/{id} — get transfer status

### Files to Create
- app/transfer/schemas.py
- app/transfer/repository.py
- app/outbox/repository.py
- app/transfer/service.py
- app/transfer/router.py

### Key Concepts
- Transfer row and outbox row written in single DB transaction
- Dual-write problem solved here
- UUID generated in application before DB insert
- Outbox payload is JSON-serialized transfer data

---

## Phase 4 — Outbox Publisher 🔲

- Background polling service
- Kafka producer
- Mark outbox rows SENT after successful publish

---

## Phase 5 — Consumer + Happy Path 🔲

- Kafka consumer
- SELECT FOR UPDATE with ordered locking (min/max wallet_id)
- Debit / credit / ledger writes
- Idempotency via processed_events

---

## Phase 6 — Concurrency & Failure Handling 🔲

- Retry logic with exponential backoff
- DLQ after max retries
- Stuck transfer recovery job

---

## Phase 7 — Reconciliation 🔲

- Ledger sum verification: sum(debits) == sum(credits)
- Wallet balance vs ledger-derived balance check

---

## Phase 8 — DECISIONS.md 🔲

- Document every architectural choice with tradeoffs
- Interview prep artifact

---

## Context for New Conversations

### Tech Stack
Python 3.14, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, aiokafka,
Redis, Docker Compose, Kafka KRaft

### Project Path
/home/billa/sahil_projects/prep/python_prep/distributed-wallet-service

### Running Services (local dev)
- Postgres: localhost:5432 (docker) ✅
- Kafka: localhost:9092 (not started yet)
- Redis: localhost:6379 (not started yet)
- API: run manually with uvicorn (not dockerized yet)

### How to Run Locally
```bash
docker compose up postgres -d
DATABASE_URL=postgresql+asyncpg://wallet_user:wallet_pass@localhost:5432/wallet_db \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### How to Run Migrations
```bash
DATABASE_URL=postgresql+asyncpg://wallet_user:wallet_pass@localhost:5432/wallet_db \
  alembic upgrade head
```

### Branch Strategy
- master — stable, merged after each phase
- phase/N-name — feature branches, one per phase
- Current branch: phase/3-transfer-outbox (after merge and checkout)

### Migrations Applied
1. 6028a2abbcc0 — create_initial_tables
2. 248e40c26b84 — add_fk_constraints_and_indexes
