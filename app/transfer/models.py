"""Transfer models for wallet-to-wallet fund transfers.

Transfers follow a state machine pattern with idempotent processing
via the outbox pattern and idempotency key tracking.
"""
import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, String, Integer, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TransferStatus(str, enum.Enum):
    """Transfer lifecycle states.
    
    State machine transitions:
    PENDING -> PUBLISHED -> PROCESSING -> COMPLETED
                                      -> FAILED -> DEAD_LETTERED
    
    PENDING: Transfer created, awaiting outbox publication
    PUBLISHED: Outbox entry sent to Kafka
    PROCESSING: Consumer is processing the transfer
    COMPLETED: Transfer successfully applied to ledger
    FAILED: Transfer failed (retryable error)
    DEAD_LETTERED: Transfer abandoned (max retries exceeded)
    """
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTERED = "DEAD_LETTERED"


class Transfer(Base):
    """Transfer record representing a wallet-to-wallet fund movement.
    
    Transfers are processed asynchronously via the outbox pattern:
    1. Transfer created atomically with outbox entry in DB
    2. Outbox publisher polls and publishes to Kafka
    3. Consumer reads from Kafka, applies debits/credits with locks
    4. Failed transfers are retried or sent to DLQ
    
    The transfer status and retry_count enable resilience patterns like
    stuck transfer detection and recovery.
    """
    __tablename__ = "transfers"

    # UUID (string) identifying this specific transfer
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # ID of wallet sending funds
    sender_wallet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # ID of wallet receiving funds
    receiver_wallet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Amount of funds to transfer (always positive)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False
    )
    # Current state in the transfer lifecycle (see TransferStatus)
    status: Mapped[TransferStatus] = mapped_column(
        SAEnum(TransferStatus), nullable=False, default=TransferStatus.PENDING
    )
    # Number of times this transfer has been retried by the consumer
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Human-readable reason for failure (if status is FAILED or DEAD_LETTERED)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamp when transfer was created
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    # Timestamp of last state change (updated on every status transition)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Transfer id={self.id} status={self.status} amount={self.amount}>"
