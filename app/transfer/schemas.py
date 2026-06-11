"""
Transfer DTOs (Data Transfer Objects).

CreateTransferRequest — validated at API boundary before hitting service layer.
TransferResponse — returned for both POST /transfers and GET /transfers/{id}.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.transfer.models import TransferStatus


class CreateTransferRequest(BaseModel):
    """
    Request body for POST /transfers.

    Field-level validation handled here:
    - amount must be positive
    - amount max 2 decimal places
    - sender and receiver cannot be the same (business rule, validated in service)
    """

    sender_wallet_id: int = Field(gt=0, description="Wallet ID of the sender")
    receiver_wallet_id: int = Field(gt=0, description="Wallet ID of the receiver")
    amount: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Transfer amount in INR. Must be positive.",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Reject amounts with more than 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class TransferResponse(BaseModel):
    """
    Response schema for all transfer endpoints.

    Returned immediately after creation (status=PENDING) and
    for status polling (GET /transfers/{id}).
    """

    id: str
    sender_wallet_id: int
    receiver_wallet_id: int
    amount: Decimal
    status: TransferStatus
    retry_count: int
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Allows model_validate(orm_object)
    }
