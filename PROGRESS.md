# Distributed Wallet Transfer System — Build Progress

## Status: Phase 1 Complete ✅ | Phase 2 In Progress

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

### Key Decisions Made
- Domain-based project structure with layered architecture (router → service → repository)
- No SQLAlchemy FK constraints — referential integrity at application layer
- Async SQLAlchemy + asyncpg throughout — nothing blocks the event loop
- Outbox pattern chosen over CDC (Debezium) — simpler for demo, noted in DECISIONS.md
- Background jobs as separate Docker services — independently deployable
- KRaft mode Kafka — no Zookeeper needed for local dev

---

## Phase 2 — Wallet Service 🔲

### To Build
- POST /wallets — create wallet
- GET /wallets/{id} — get wallet
- POST /wallets/{id}/fund — add funds (test helper)

### Files to Create
- app/wallet/schemas.py
- app/wallet/repository.py
- app/wallet/service.py
- app/wallet/router.py

---

## Phase 3 — Transfer Creation + Outbox 🔲

- POST /transfers
- GET /transfers/{id}
- Atomic transfer + outbox write in single transaction

---

## Phase 4 — Outbox Publisher 🔲

- Background polling service
- Kafka producer
- Mark outbox rows SENT

---

## Phase 5 — Consumer + Happy Path 🔲

- Kafka consumer
- SELECT FOR UPDATE with ordered locking
- Debit / credit / ledger writes
- Idempotency via processed_events

---

## Phase 6 — Concurrency & Failure Handling 🔲

- Retry logic with exponential backoff
- DLQ on max retries
- Stuck transfer recovery job

---

## Phase 7 — Reconciliation 🔲

- Ledger sum verification
- Wallet balance vs ledger-derived balance check

---

## Phase 8 — DECISIONS.md 🔲

- Document every architectural choice with tradeoffs
- Interview prep artifact

---

## Context for New Conversations

### Tech Stack
Python 3.14, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, aiokafka, Redis, Docker Compose, Kafka KRaft

### Project Path
/home/billa/sahil_projects/prep/python_prep/distributed-wallet-service

### Repo
git remote: origin/master

### Running Services
- Postgres: localhost:5432 (docker)
- Kafka: localhost:9092 (not started yet)
- Redis: localhost:6379 (not started yet)
- API: not started yet

### Branch Strategy
- master — stable
- phase/N-name — feature branches from Phase 2 onwards
