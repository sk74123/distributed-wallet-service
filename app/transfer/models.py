"""
Transfer domain model.

Represents a money transfer request and tracks its full lifecycle
through the distributed system via the status state machine.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TransferStatus(str, enum.Enum):
    """
    State machine for a transfer lifecycle.

    PENDING       — created in DB, outbox event written
    PUBLISHED     — outbox publisher sent event to Kafka
    PROCESSING    — consumer started handling the event
    COMPLETED     — transfer successfully finished
    FAILED        — business or processing failure
    DEAD_LETTERED — retry limit exceeded, moved to DLQ
    """
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTERED = "DEAD_LETTERED"


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sender_wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    receiver_wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False
    )
    status: Mapped[TransferStatus] = mapped_column(
        SAEnum(TransferStatus), nullable=False, default=TransferStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # Indexes on FK columns — FKs do not auto-create indexes in Postgres
        Index("ix_transfers_sender_wallet_id", "sender_wallet_id"),
        Index("ix_transfers_receiver_wallet_id", "receiver_wallet_id"),
        Index("ix_transfers_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Transfer id={self.id} status={self.status} amount={self.amount}>"
