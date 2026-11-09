"""Pydantic v2 schemas for ledger transactions, filtering, and pagination."""

from datetime import date, datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field

from shared.constants import TransactionType
from shared.schemas.financial import Money, PositiveMoney


class TransactionCreateRequest(BaseModel):
    """Payload for recording a manual ledger transaction."""

    account_id: uuid.UUID = Field(description="Account UUID where transaction took place")
    category_id: uuid.UUID | None = Field(default=None, description="Optional category UUID")
    amount: PositiveMoney = Field(description="Transaction monetary amount (strictly positive Decimal, 2 decimal places)")
    transaction_type: TransactionType = Field(description="Double-entry direction: DEBIT (expense) or CREDIT (income)")
    transaction_date: date = Field(description="Date transaction occurred (ISO 8601: YYYY-MM-DD)")
    raw_description: str = Field(min_length=1, max_length=500, description="Raw transaction narration or note")
    clean_merchant: str | None = Field(default=None, max_length=255, description="Normalized merchant name")


class TransactionUpdateRequest(BaseModel):
    """Payload for modifying an existing transaction."""

    category_id: uuid.UUID | None = Field(default=None, description="Updated category UUID")
    amount: PositiveMoney | None = Field(default=None, description="Updated monetary amount")
    transaction_type: TransactionType | None = Field(default=None, description="Updated direction")
    transaction_date: date | None = Field(default=None, description="Updated date")
    raw_description: str | None = Field(default=None, min_length=1, max_length=500, description="Updated narration")
    clean_merchant: str | None = Field(default=None, max_length=255, description="Updated merchant name")


class TransactionResponse(BaseModel):
    """Public representation of a confirmed ledger transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique transaction UUID")
    account_id: uuid.UUID = Field(description="Account UUID")
    category_id: uuid.UUID | None = Field(description="Category UUID or None")
    statement_id: uuid.UUID | None = Field(description="Statement batch UUID if imported from statement")
    amount: Money = Field(description="Quantized 2-decimal monetary amount")
    transaction_type: TransactionType = Field(description="DEBIT or CREDIT")
    transaction_date: date = Field(description="Date transaction occurred")
    raw_description: str = Field(description="Narration")
    clean_merchant: str | None = Field(description="Normalized merchant")
    is_reviewed: bool = Field(description="Whether the transaction has been reviewed")
    created_at: datetime = Field(description="Created timestamp in UTC")


class PaginatedTransactionsResponse(BaseModel):
    """Paginated collection of transactions."""

    items: list[TransactionResponse] = Field(description="List of transactions in current page")
    total: int = Field(description="Total number of matching transactions")
    limit: int = Field(description="Page limit")
    offset: int = Field(description="Page offset")
