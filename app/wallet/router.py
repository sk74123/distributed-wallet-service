"""
Wallet router.

HTTP layer only — no business logic lives here.
Each endpoint:
  1. Parses the request (Pydantic handles validation)
  2. Gets a DB session from the get_db dependency
  3. Calls the service layer
  4. Returns the response DTO

Exceptions raised by the service are caught by the global handlers
registered in main.py — this router never handles them directly.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.wallet.schemas import CreateWalletRequest, FundWalletRequest, WalletResponse
from app.wallet.service import (
    create_wallet_service,
    fund_wallet_service,
    get_wallet_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=WalletResponse, status_code=201)
async def create_wallet(
    request: CreateWalletRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new wallet.

    Returns 201 with the created wallet on success.
    """
    return await create_wallet_service(session, request)


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Get wallet by ID.

    Returns 404 if the wallet does not exist.
    """
    return await get_wallet_service(session, wallet_id)


@router.post("/{wallet_id}/fund", response_model=WalletResponse)
async def fund_wallet(
    wallet_id: int,
    request: FundWalletRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Add funds to a wallet.

    Test helper endpoint — simulates loading money into a wallet.
    Returns 404 if wallet does not exist.
    Returns 422 if amount is invalid (handled by Pydantic).
    """
    return await fund_wallet_service(session, wallet_id, request)
