"""
Outbox domain model.

Solves the dual-write problem — instead of writing to DB and publishing
to Kafka in two separate operations (which can fail independently), we write
the transfer row and outbox row in a single DB transaction.

A separate outbox publisher process polls PENDING rows and publishes to Kafka,
then marks them SENT. If the publisher crashes after publishing but before
marking SENT, the message gets republished — downstream idempotency handles it.
"""

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"


class OutboxEvent(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transfers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One outbox event per transfer, enforced at DB level
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        SAEnum(OutboxStatus), nullable=False, default=OutboxStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<OutboxEvent id={self.id} "
            f"transfer_id={self.transfer_id} status={self.status}>"
        )
