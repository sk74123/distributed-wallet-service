# Distributed Wallet Transfer System — Blueprint

## What We Are Building

A wallet-to-wallet transfer system that demonstrates real-world distributed
systems patterns. The focus is reliability and consistency, not business
features. This is an interview demo project that also serves as a learning
exercise — we slow down at each phase and discuss the why behind every decision.

---

## Problem Statements Being Solved

1. Dual Write Problem — DB commit succeeds, Kafka publish fails
   Solution: Outbox Pattern

2. Double Payment — two concurrent transfers read the same balance
   Solution: SELECT FOR UPDATE with deterministic lock ordering

3. Duplicate Kafka Messages — at-least-once delivery causes reprocessing
   Solution: processed_events table (DB-enforced idempotency)

4. Partial Failures — sender debited, consumer crashes before receiver credited
   Solution: single DB transaction wraps debit + credit + ledger + status update

5. Poison Pill Messages — bad messages fail forever, consumer stuck
   Solution: retry count + DLQ after max retries

6. Ledger Inconsistency — silent data corruption
   Solution: reconciliation job verifies sum(debits) == sum(credits)

7. Stuck Transfers — consumer crashes, transfer stays PROCESSING forever
   Solution: background recovery job requeues stuck transfers

---

## Tech Stack

| Layer          | Technology                        |
|----------------|-----------------------------------|
| Language       | Python 3.14                       |
| Web Framework  | FastAPI                           |
| Validation     | Pydantic v2                       |
| ORM            | SQLAlchemy 2.0 (async)            |
| DB Driver      | asyncpg                           |
| Migrations     | Alembic                           |
| Message Broker | Kafka (KRaft mode, no Zookeeper)  |
| Kafka Client   | aiokafka                          |
| Cache/Rate     | Redis                             |
| Package Mgr    | uv                                |
| Containers     | Docker Compose                    |

---

## Architecture
Client
↓
FastAPI (app/)
↓
PostgreSQL
↓
Outbox Table
↓
Outbox Publisher (workers/outbox_publisher.py)
↓
Kafka Topic: transfers
↓
Transfer Consumer (workers/transfer_consumer.py)
↓
PostgreSQL
↓
DLQ Topic: transfers.dlq
↓
Reconciliation Job (workers/reconciliation_job.py)

---

## Domain Models

### wallets
id | owner_name | balance (Decimal) | currency | created_at
- balance is a cached value, not source of truth
- source of truth is ledger_entries

### transfers
id (UUID) | sender_wallet_id | receiver_wallet_id | amount | status | retry_count | failure_reason | created_at | updated_at

Status state machine:
PENDING → PUBLISHED → PROCESSING → COMPLETED
                                 → FAILED → DEAD_LETTERED

### ledger_entries
id | transfer_id | wallet_id | amount | entry_type (DEBIT/CREDIT) | created_at
- Double-entry bookkeeping
- Every transfer produces exactly 2 entries
- This is the source of truth for balances

### outbox
id | transfer_id | payload (JSON) | status (PENDING/SENT) | created_at
- Written atomically with transfers row
- Solves dual-write problem

### processed_events
event_id | status (PROCESSING/COMPLETED) | processed_at
- DB-enforced idempotency for Kafka consumer
- Insert before processing, update after completion

---

## Project Structure
distributed-wallet-service/
├── app/
│   ├── main.py                  # FastAPI app, routers, exception handlers
│   ├── config.py                # pydantic-settings, lru_cache
│   ├── database.py              # async engine, session factory, Base, get_db
│   ├── logging_config.py        # structured logging
│   ├── exceptions.py            # domain exceptions
│   ├── wallet/
│   │   ├── models.py            # Wallet ORM model
│   │   ├── schemas.py           # Request/Response DTOs
│   │   ├── repository.py        # DB queries
│   │   ├── service.py           # business logic
│   │   └── router.py            # HTTP endpoints
│   ├── transfer/
│   │   ├── models.py            # Transfer ORM model + TransferStatus enum
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── outbox/
│   │   ├── models.py            # OutboxEvent ORM model
│   │   └── repository.py        # internal only, no router
│   ├── ledger/
│   │   ├── models.py            # LedgerEntry ORM model
│   │   └── repository.py        # internal only, no router
│   └── processed_events/
│       ├── models.py            # ProcessedEvent ORM model
│       └── repository.py        # idempotency checks only
├── workers/
│   ├── outbox_publisher.py      # polls outbox, publishes to Kafka
│   ├── transfer_consumer.py     # Kafka consumer, processes transfers
│   ├── recovery_job.py          # requeues stuck transfers
│   └── reconciliation_job.py   # verifies ledger integrity
├── alembic/                     # migrations
├── docker-compose.yml           # Postgres, Kafka, Redis, API
├── Dockerfile                   # multi-stage build
├── pyproject.toml               # uv dependencies
├── .env                         # local config (gitignored)
├── .env.example                 # template (committed)
├── PROGRESS.md                  # build progress and context
├── BLUEPRINT.md                 # this file
└── DECISIONS.md                 # architectural decisions (Phase 8)

---

## Build Phases

### Phase 1 — Project Foundation ✅
Docker Compose, FastAPI skeleton, Postgres + Kafka + Redis, Alembic,
all 5 ORM models, config, logging, exceptions, initial migration.

### Phase 2 — Wallet Service 🔲
POST /wallets, GET /wallets/{id}, POST /wallets/{id}/fund
Pure CRUD, no Kafka. First real business logic.
Files: schemas.py, repository.py, service.py, router.py under app/wallet/

### Phase 3 — Transfer Creation + Outbox 🔲
POST /transfers, GET /transfers/{id}
Transfer row + outbox row written atomically in one transaction.
Dual-write problem solved here.

### Phase 4 — Outbox Publisher 🔲
Background service polls outbox PENDING rows, publishes to Kafka, marks SENT.
First time Kafka is involved.

### Phase 5 — Consumer + Happy Path 🔲
Kafka consumer processes transfer events.
SELECT FOR UPDATE with ordered locking (min/max wallet_id).
Debit sender, credit receiver, write ledger entries, mark COMPLETED.
Idempotency via processed_events.

### Phase 6 — Concurrency & Failure Handling 🔲
Retry logic, DLQ after max retries, deadlock prevention,
stuck transfer recovery job.

### Phase 7 — Reconciliation 🔲
Ledger sum verification: sum(debits) == sum(credits)
Balance verification: wallet.balance == sum(ledger_entries for wallet)

### Phase 8 — DECISIONS.md 🔲
Document every architectural choice with tradeoffs.
Primary interview prep artifact.

---

## Key Architectural Decisions

- No SQLAlchemy FK constraints — referential integrity at application layer
  (supports future service separation)
- Outbox Pattern over CDC/Debezium — simpler, no extra infrastructure
- Polling outbox publisher over event-driven — good enough for demo,
  CDC noted as production preference in DECISIONS.md
- Separate Docker services for workers — independently deployable,
  independently restartable
- KRaft Kafka — no Zookeeper for local dev
- Decimal not float for all monetary values — no precision errors
- UUID generated in application for transfer IDs — needed before DB insert
  for idempotency

---

## Local Development

### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- uv

### Setup
```bash
git clone <repo>
cd distributed-wallet-service
cp .env.example .env
uv sync
source .venv/bin/activate
docker compose up postgres -d
DATABASE_URL=postgresql+asyncpg://wallet_user:wallet_pass@localhost:5432/wallet_db alembic upgrade head
docker compose up -d
```

### Running migrations
```bash
DATABASE_URL=postgresql+asyncpg://wallet_user:wallet_pass@localhost:5432/wallet_db alembic revision --autogenerate -m "description"
DATABASE_URL=postgresql+asyncpg://wallet_user:wallet_pass@localhost:5432/wallet_db alembic upgrade head
```

---

## Project Path
/home/billa/sahil_projects/prep/python_prep/distributed-wallet-service

## Git
Branch strategy: master (stable) + phase/N-name feature branches from Phase 2 onwards
