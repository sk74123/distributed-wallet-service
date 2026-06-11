"""
Wallet service.

Contains all business logic for the wallet domain.
Sits between the router (HTTP) and repository (DB).

Responsibilities:
- Validate business rules (e.g. wallet must exist before funding)
- Orchestrate repository calls
- Convert ORM models to response DTOs
- Raise domain exceptions on failure

The service never returns ORM objects — always WalletResponse DTOs.
"""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientBalanceError, WalletNotFoundError
from app.wallet.repository import (
    create_wallet,
    get_wallet_by_id,
    update_wallet_balance,
)
from app.wallet.schemas import CreateWalletRequest, FundWalletRequest, WalletResponse

logger = logging.getLogger(__name__)


async def create_wallet_service(
    session: AsyncSession,
    request: CreateWalletRequest,
) -> WalletResponse:
    """
    Create a new wallet with zero balance.
    owner_name uniqueness is not enforced — multiple wallets per name is allowed.
    """
    wallet = await create_wallet(session, owner_name=request.owner_name)
    logger.info("Wallet created successfully id=%s", wallet.id)
    return WalletResponse.model_validate(wallet)


async def get_wallet_service(
    session: AsyncSession,
    wallet_id: int,
) -> WalletResponse:
    """
    Fetch a wallet by ID.
    Raises WalletNotFoundError if the wallet does not exist.
    """
    wallet = await get_wallet_by_id(session, wallet_id)
    if wallet is None:
        raise WalletNotFoundError(wallet_id)

    return WalletResponse.model_validate(wallet)


async def fund_wallet_service(
    session: AsyncSession,
    wallet_id: int,
    request: FundWalletRequest,
) -> WalletResponse:
    """
    Add funds to a wallet.

    Business rules validated here (not in schema):
    - Wallet must exist

    The amount field-level validation (> 0, max 2 decimal places)
    is handled by Pydantic in FundWalletRequest before reaching here.
    """
    wallet = await get_wallet_by_id(session, wallet_id)
    if wallet is None:
        raise WalletNotFoundError(wallet_id)

    new_balance = wallet.balance + request.amount
    updated_wallet = await update_wallet_balance(session, wallet_id, new_balance)

    logger.info(
        "Funded wallet id=%s amount=%s new_balance=%s",
        wallet_id,
        request.amount,
        new_balance,
    )
    return WalletResponse.model_validate(updated_wallet)
