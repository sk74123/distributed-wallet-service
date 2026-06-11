"""
ProcessedEvent domain model.

Provides database-enforced idempotency for the Kafka consumer.

Flow:
1. Consumer receives a Kafka message (transfer_id as event_id)
2. Attempts to INSERT event_id with status PROCESSING
3. If insert fails (unique violation) — already processed, skip
4. If insert succeeds — proceed with transfer processing
5. On successful completion — UPDATE status to COMPLETED

This handles the at-least-once delivery guarantee of Kafka.
Even if the same message arrives 10 times, only one will get past step 2.

Note: No FK to transfers here intentionally — processed_events is an
infrastructure concern, not a business concern. It should remain
decoupled from the transfer domain.
"""

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedEventStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[ProcessedEventStatus] = mapped_column(
        SAEnum(ProcessedEventStatus), nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ProcessedEvent event_id={self.event_id} status={self.status}>"
