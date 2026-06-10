"""Ledger entry models for double-entry bookkeeping.

The ledger is the source of truth for wallet balances. Every transfer
produces exactly 2 entries: a DEBIT from sender and a CREDIT to receiver.
This ensures balance verification and audit trails.
"""
import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, String, Integer, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EntryType(str, enum.Enum):
    """Ledger entry type enumeration.
    
    DEBIT: Money leaving a wallet (sender in a transfer)
    CREDIT: Money entering a wallet (receiver in a transfer)
    """
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(Base):
    """Ledger entry record for double-entry bookkeeping.
    
    Represents a single debit or credit against a wallet in the context
    of a transfer. The ledger is immutable and serves as the source of truth
    for all wallet balance changes.
    """
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # UUID of the transfer that caused this ledger entry
    transfer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # ID of the wallet affected by this entry
    wallet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Amount of money (always positive; entry_type determines direction)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False
    )
    # Type of entry: DEBIT (money out) or CREDIT (money in)
    entry_type: Mapped[EntryType] = mapped_column(
        SAEnum(EntryType), nullable=False
    )
    # Timestamp when entry was recorded (immutable)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<LedgerEntry id={self.id} wallet={self.wallet_id} type={self.entry_type} amount={self.amount}>"
