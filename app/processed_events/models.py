import enum
from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy import Enum as SAEnum
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
