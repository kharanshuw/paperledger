"""Pydantic v2 schemas for account creation, updates, and responses."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field

from shared.constants import AccountType


class AccountCreateRequest(BaseModel):
    """Payload for creating a new financial account."""

    name: str = Field(min_length=1, max_length=100, description="Display name of the account (e.g. Chase Checking)")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 3-letter currency code")
    account_type: AccountType = Field(default=AccountType.CHECKING, description="Account categorization")


class AccountUpdateRequest(BaseModel):
    """Payload for modifying an existing account."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Updated display name")
    currency: str | None = Field(default=None, min_length=3, max_length=3, description="Updated ISO 4217 currency")
    account_type: AccountType | None = Field(default=None, description="Updated account categorization")


class AccountResponse(BaseModel):
    """Public representation of a financial account."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique account UUID")
    name: str = Field(description="Display name of the account")
    currency: str = Field(description="ISO 4217 3-letter currency code")
    account_type: AccountType = Field(description="Account categorization")
    created_at: datetime = Field(description="Creation timestamp in UTC")
    updated_at: datetime = Field(description="Last updated timestamp in UTC")
