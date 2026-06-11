"""
Wallet DTOs (Data Transfer Objects).

Schemas are split into Request and Response types:
- Request schemas validate and parse incoming client data
- Response schemas define exactly what the API returns

The service layer always converts ORM models to response DTOs before
returning — the router never sees a raw SQLAlchemy model.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CreateWalletRequest(BaseModel):
    """Request body for POST /wallets."""

    owner_name: str = Field(
        min_length=1,
        max_length=100,
        description="Name of the wallet owner",
    )


class FundWalletRequest(BaseModel):
    """
    Request body for POST /wallets/{id}/fund.

    This endpoint exists only for testing — it simulates loading
    money into a wallet without going through a real payment flow.
    """

    amount: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Amount to add in INR. Must be positive.",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """
        Reject amounts with more than 2 decimal places.
        e.g. 100.123 is invalid, 100.12 is valid.
        """
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class WalletResponse(BaseModel):
    """
    Response schema for all wallet endpoints.

    balance is serialized as a string to avoid float precision issues
    in JSON — the client receives exactly what is stored in the DB.
    """

    id: int
    owner_name: str
    balance: Decimal
    currency: str
    created_at: datetime

    model_config = {
        "from_attributes": True,  # Allows model_validate(orm_object)
    }
