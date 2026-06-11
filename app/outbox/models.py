"""
Outbox domain model.

Solves the dual-write problem — instead of writing to DB and publishing
to Kafka in two separate operations (which can fail independently), we write
the transfer row and outbox row in a single DB transaction.

Three-state status machine:
PENDING    — written atomically with transfer, waiting to be claimed
PROCESSING — claimed by a publisher instance, publish in progress
SENT       — successfully published to Kafka

The PROCESSING state enables multiple publisher instances to run safely
(each claims its own rows) and allows a recovery job to detect and reset
rows stuck in PROCESSING due to publisher crashes.
"""

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"  # claimed by a publisher, publish in progress
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
