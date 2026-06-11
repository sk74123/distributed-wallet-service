"""
Outbox repository.

The outbox table is an internal infrastructure concern — it has no router
or service layer. It is written to by the transfer service (atomically
with the transfer row) and read by the outbox publisher worker.

Key design: the outbox payload is a JSON string containing everything
the Kafka consumer needs to process the transfer. This decouples the
consumer from needing to query the DB to understand the event.
"""

import json
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.models import OutboxEvent, OutboxStatus

logger = logging.getLogger(__name__)


def _decimal_serializer(obj):
    """
    Custom JSON serializer for Decimal types.
    Converts Decimal to string to preserve precision in the payload.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def create_outbox_event(
    session: AsyncSession,
    transfer_id: str,
    sender_wallet_id: int,
    receiver_wallet_id: int,
    amount: Decimal,
) -> OutboxEvent:
    """
    Insert a PENDING outbox event for the given transfer.

    Must be called within the same transaction as the transfer insert —
    that's what solves the dual-write problem.

    The payload contains all data the consumer needs:
    - transfer_id: for idempotency checks
    - sender/receiver: for debit/credit operations
    - amount: for ledger entries
    """
    payload = json.dumps(
        {
            "transfer_id": transfer_id,
            "sender_wallet_id": sender_wallet_id,
            "receiver_wallet_id": receiver_wallet_id,
            "amount": amount,
        },
        default=_decimal_serializer,
    )

    event = OutboxEvent(
        transfer_id=transfer_id,
        payload=payload,
        status=OutboxStatus.PENDING,
    )
    session.add(event)
    await session.flush()

    logger.info("Created outbox event for transfer_id=%s", transfer_id)
    return event
