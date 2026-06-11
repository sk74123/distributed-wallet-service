"""
Outbox repository.

The outbox table is an internal infrastructure concern — it has no router
or service layer. It is written to by the transfer service (atomically
with the transfer row) and read/updated by the outbox publisher worker.

Three-state flow:
  PENDING    — written atomically with transfer row
  PROCESSING — claimed by publisher before Kafka publish
  SENT       — marked after successful Kafka publish

The PROCESSING state ensures multiple publisher instances never process
the same row, and allows a recovery job to detect stuck rows.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
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
    that is what solves the dual-write problem.

    The payload contains all data the consumer needs so it never has
    to query the DB to understand the event.
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


async def claim_pending_events(
    session: AsyncSession,
    batch_size: int = 10,
) -> list[OutboxEvent]:
    """
    Atomically claim a batch of PENDING rows by marking them PROCESSING.

    Uses SELECT FOR UPDATE SKIP LOCKED:
    - FOR UPDATE: locks the selected rows
    - SKIP LOCKED: if a row is already locked by another publisher instance,
      skip it instead of waiting — ensures two publishers never claim the same row

    Returns the claimed rows with their payloads ready for Kafka publish.
    """
    # Select PENDING rows with lock
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxStatus.PENDING)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(result.scalars().all())

    if not events:
        return []

    # Claim by marking PROCESSING
    event_ids = [e.id for e in events]
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id.in_(event_ids))
        .values(status=OutboxStatus.PROCESSING)
    )
    await session.flush()

    logger.info("Claimed %d outbox events for processing", len(events))
    return events


async def mark_event_sent(session: AsyncSession, event_id: int) -> None:
    """
    Mark a single outbox event as SENT after successful Kafka publish.
    Called per-event so a failure on one row does not block others.
    """
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(status=OutboxStatus.SENT)
    )
    await session.flush()
    logger.debug("Marked outbox event id=%d as SENT", event_id)


async def mark_event_pending(session: AsyncSession, event_id: int) -> None:
    """
    Reset a PROCESSING event back to PENDING.

    Used by the recovery job (Phase 6) to rescue rows stuck in PROCESSING
    due to a publisher crash after claiming but before publishing.
    """
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(status=OutboxStatus.PENDING)
    )
    await session.flush()
    logger.info("Reset outbox event id=%d back to PENDING", event_id)


async def get_stuck_processing_events(
    session: AsyncSession,
    stuck_threshold: datetime,
) -> list[OutboxEvent]:
    """
    Find outbox events stuck in PROCESSING older than the threshold.

    An event stuck in PROCESSING means the publisher claimed it but crashed
    before publishing. The recovery job uses this to reset them.

    stuck_threshold: datetime before which PROCESSING rows are considered stuck.
    Example: datetime.now() - timedelta(minutes=10)
    """
    result = await session.execute(
        select(OutboxEvent).where(
            OutboxEvent.status == OutboxStatus.PROCESSING,
            OutboxEvent.created_at < stuck_threshold,
        )
    )
    return list(result.scalars().all())
