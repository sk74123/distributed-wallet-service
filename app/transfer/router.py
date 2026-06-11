"""
Transfer router.

HTTP layer only. Two endpoints:
- POST /transfers: create a transfer (returns PENDING status immediately)
- GET /transfers/{id}: poll transfer status

The client is expected to poll GET /transfers/{id} to track the transfer
through its lifecycle: PENDING → PUBLISHED → PROCESSING → COMPLETED.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.transfer.schemas import CreateTransferRequest, TransferResponse
from app.transfer.service import create_transfer_service, get_transfer_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(
    request: CreateTransferRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Initiate a wallet-to-wallet transfer.

    Returns 201 with status=PENDING immediately.
    The transfer is processed asynchronously by the Kafka consumer.
    Poll GET /transfers/{id} to track progress.

    Returns 400 if sender == receiver.
    Returns 404 if either wallet does not exist.
    Returns 422 if amount is invalid or sender has insufficient balance.
    """
    return await create_transfer_service(session, request)


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Get transfer status by ID.

    Returns 404 if the transfer does not exist.
    """
    return await get_transfer_service(session, transfer_id)
