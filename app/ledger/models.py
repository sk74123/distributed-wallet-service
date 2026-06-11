"""
Ledger domain model.

Double-entry bookkeeping table. Every transfer produces exactly two entries —
one DEBIT from the sender and one CREDIT to the receiver.

This is the source of truth for balances. wallet.balance is a cached value
derived from summing ledger entries. The reconciliation job verifies this.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transfers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(
        SAEnum(EntryType), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ledger_entries_transfer_id", "transfer_id"),
        Index("ix_ledger_entries_wallet_id", "wallet_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<LedgerEntry id={self.id} wallet={self.wallet_id} "
            f"type={self.entry_type} amount={self.amount}>"
        )
