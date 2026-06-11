"""
Entry point for the Distributed Wallet Transfer System API.

Responsibilities:
- Bootstrap the FastAPI application
- Register domain routers
- Register global exception handlers
- Handle application lifespan (startup / shutdown)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import (
    DuplicateTransferError,
    InsufficientBalanceError,
    InvalidTransferError,
    TransferNotFoundError,
    WalletNotFoundError,
)
from app.logging_config import setup_logging

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.

    Startup: initialise logging, log config summary.
    Shutdown: log graceful shutdown message.

    Using lifespan instead of deprecated @app.on_event handlers.
    """
    setup_logging(debug=settings.debug)
    logger.info("Starting Distributed Wallet Service [env=%s]", settings.app_env)
    yield
    logger.info("Shutting down Distributed Wallet Service")


app = FastAPI(
    title="Distributed Wallet Transfer System",
    description=(
        "Demonstrates distributed systems patterns: Outbox, Idempotency, "
        "Saga, DLQ, Reconciliation, and Row-level locking."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handlers
# Each handler maps a domain exception to an appropriate HTTP status code.
# The service layer raises these; the router layer never touches HTTPException.
# ---------------------------------------------------------------------------

@app.exception_handler(WalletNotFoundError)
async def wallet_not_found_handler(request: Request, exc: WalletNotFoundError):
    """404 when a wallet ID does not exist."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TransferNotFoundError)
async def transfer_not_found_handler(request: Request, exc: TransferNotFoundError):
    """404 when a transfer ID does not exist."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InsufficientBalanceError)
async def insufficient_balance_handler(request: Request, exc: InsufficientBalanceError):
    """422 when sender does not have enough balance."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "wallet_id": exc.wallet_id,
            "required": float(exc.required),
            "available": float(exc.available),
        },
    )


@app.exception_handler(InvalidTransferError)
async def invalid_transfer_handler(request: Request, exc: InvalidTransferError):
    """400 for business rule violations (e.g. sender == receiver, amount <= 0)."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(DuplicateTransferError)
async def duplicate_transfer_handler(request: Request, exc: DuplicateTransferError):
    """409 when a transfer with the same ID is submitted more than once."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Domain routers
# Uncommented as each phase is completed.
# ---------------------------------------------------------------------------

from app.wallet.router import router as wallet_router
# from app.transfer.router import router as transfer_router
app.include_router(wallet_router, prefix="/wallets", tags=["Wallets"])
# app.include_router(transfer_router, prefix="/transfers", tags=["Transfers"])


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple liveness probe.
    Returns 200 if the application process is running.
    Does not check DB or Kafka connectivity.
    """
    return {"status": "ok", "env": settings.app_env}
