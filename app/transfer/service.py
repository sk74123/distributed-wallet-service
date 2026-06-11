"""
Transfer service.

Phase 3 responsibility: create a transfer + outbox event atomically.

The dual-write problem is solved here — both the transfer row and the
outbox event are written in the same DB transaction (managed by get_db).
If anything fails, both rows are rolled back together.

Balance validation strategy:
- Synthetic check here (Phase 3): fast rejection for obviously insufficient balance
- Exact check in consumer (Phase 5): authoritative check under SELECT FOR UPDATE lock

This two-stage approach gives fast user feedback while guaranteeing
correctness at processing time.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    InvalidTransferError,
    TransferNotFoundError,
    WalletNotFoundError,
    InsufficientBalanceError,
)
from app.outbox.repository import create_outbox_event
from app.transfer.repository import create_transfer, get_transfer_by_id
from app.transfer.schemas import CreateTransferRequest, TransferResponse
from app.wallet.repository import get_wallet_by_id

logger = logging.getLogger(__name__)


async def create_transfer_service(
    session: AsyncSession,
    request: CreateTransferRequest,
) -> TransferResponse:
    """
    Create a transfer and its outbox event atomically.

    Steps:
    1. Validate sender != receiver
    2. Validate both wallets exist
    3. Synthetic balance check (optimistic, not authoritative)
    4. Generate transfer UUID
    5. INSERT transfer row
    6. INSERT outbox event row (same transaction)
    7. Commit — both rows land together or neither does

    The session is committed by get_db after this function returns.
    """

    # --- Business rule: sender and receiver must be different wallets ---
    if request.sender_wallet_id == request.receiver_wallet_id:
        raise InvalidTransferError("Sender and receiver cannot be the same wallet")

    # --- Validate sender wallet exists ---
    sender = await get_wallet_by_id(session, request.sender_wallet_id)
    if sender is None:
        raise WalletNotFoundError(request.sender_wallet_id)

    # --- Validate receiver wallet exists ---
    receiver = await get_wallet_by_id(session, request.receiver_wallet_id)
    if receiver is None:
        raise WalletNotFoundError(request.receiver_wallet_id)

    # --- Synthetic balance check ---
    # This is an optimistic check for fast failure — not a correctness guarantee.
    # The authoritative balance check happens in Phase 5 under SELECT FOR UPDATE.
    # Between now and then, another transfer could debit the sender's balance.
    if sender.balance < request.amount:
        raise InsufficientBalanceError(
            wallet_id=request.sender_wallet_id,
            required=request.amount,
            available=sender.balance,
        )

    # --- Generate transfer ID in application layer ---
    # We generate the UUID here (not in DB) because we need it before the insert
    # to use as the outbox event's transfer_id.
    transfer_id = str(uuid.uuid4())

    # --- Atomic write: transfer + outbox event ---
    # Both inserts happen in the same transaction managed by get_db.
    # If either insert fails, the entire transaction rolls back.
    transfer = await create_transfer(
        session=session,
        transfer_id=transfer_id,
        sender_wallet_id=request.sender_wallet_id,
        receiver_wallet_id=request.receiver_wallet_id,
        amount=request.amount,
    )

    await create_outbox_event(
        session=session,
        transfer_id=transfer_id,
        sender_wallet_id=request.sender_wallet_id,
        receiver_wallet_id=request.receiver_wallet_id,
        amount=request.amount,
    )

    logger.info(
        "Transfer created atomically id=%s sender=%s receiver=%s amount=%s",
        transfer_id,
        request.sender_wallet_id,
        request.receiver_wallet_id,
        request.amount,
    )

    return TransferResponse.model_validate(transfer)


async def get_transfer_service(
    session: AsyncSession,
    transfer_id: str,
) -> TransferResponse:
    """
    Fetch a transfer by ID for status polling.
    Raises TransferNotFoundError if not found.
    """
    transfer = await get_transfer_by_id(session, transfer_id)
    if transfer is None:
        raise TransferNotFoundError(transfer_id)

    return TransferResponse.model_validate(transfer)
