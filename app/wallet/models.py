"""Wallet model for user account representation.

Wallets represent user accounts with a cached balance. The cached balance
is denormalized from the ledger entries (source of truth) for performance.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Wallet(Base):
    """User wallet account.
    
    Wallets hold a cached balance for query efficiency. The source of truth
    for balances is the ledger_entries table (double-entry bookkeeping).
    The cached balance should be periodically reconciled against the ledger.
    """
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Name of the wallet owner
    owner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Cached balance (derived from ledger entries). Should be kept in sync
    # via application logic. Reconciliation job verifies correctness.
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False, default=Decimal("0.00")
    )
    # ISO 4217 currency code (e.g., 'INR', 'USD', 'EUR')
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    # Timestamp when wallet was created
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Wallet id={self.id} owner={self.owner_name} balance={self.balance}>"
