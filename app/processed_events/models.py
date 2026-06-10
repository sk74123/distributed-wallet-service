"""Processed events model for idempotent message handling.

Kafka provides at-least-once delivery guarantees, which means the same
message may be delivered multiple times. The processed_events table
ensures idempotency by tracking event IDs that have already been handled.
"""
import enum
from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ProcessedEventStatus(str, enum.Enum):
    """Status of a processed event.
    
    PROCESSING: Event is currently being processed (prevents concurrent processing)
    COMPLETED: Event processing finished successfully
    """
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class ProcessedEvent(Base):
    """Record of a processed Kafka message for idempotency.
    
    When a transfer message is consumed from Kafka, we create a ProcessedEvent
    record to prevent reprocessing if the message is delivered again.
    The event_id is the Kafka message offset or a unique transfer ID.
    """
    __tablename__ = "processed_events"

    # Unique identifier for the Kafka event (typically transfer UUID or offset)
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Processing status (PROCESSING during handling, COMPLETED when done)
    status: Mapped[ProcessedEventStatus] = mapped_column(
        SAEnum(ProcessedEventStatus), nullable=False
    )
    # Timestamp when event was first processed
    processed_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ProcessedEvent event_id={self.event_id} status={self.status}>"
