"""
Wallet repository.

All database queries for the wallet domain live here.
The service layer never writes raw SQL or uses the ORM directly.

Repository contract:
- Returns None when a record is not found (never raises)
- Never contains business logic
- Always receives a session from the caller (no session management here)
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.wallet.models import Wallet

logger = logging.getLogger(__name__)


async def create_wallet(session: AsyncSession, owner_name: str) -> Wallet:
    """
    Insert a new wallet with zero balance.
    Returns the persisted Wallet ORM object.
    """
    wallet = Wallet(owner_name=owner_name)
    session.add(wallet)
    await session.flush()  # flush to get the DB-generated ID without committing

    logger.info("Created wallet id=%s owner=%s", wallet.id, wallet.owner_name)
    return wallet


async def get_wallet_by_id(
    session: AsyncSession, wallet_id: int
) -> Wallet | None:
    """
    Fetch a wallet by primary key.
    Returns None if not found — caller decides how to handle it.
    """
    result = await session.execute(
        select(Wallet).where(Wallet.id == wallet_id)
    )
    return result.scalar_one_or_none()


async def update_wallet_balance(
    session: AsyncSession, wallet_id: int, new_balance: Decimal
) -> Wallet | None:
    """
    Update a wallet's cached balance.
    Returns the updated Wallet, or None if not found.

    Note: this updates the cached balance only. The ledger_entries table
    is the source of truth — this value is derived from it.
    """
    wallet = await get_wallet_by_id(session, wallet_id)
    if wallet is None:
        return None

    wallet.balance = new_balance
    await session.flush()

    logger.info("Updated wallet id=%s new_balance=%s", wallet_id, new_balance)
    return wallet
