"""StagedTransaction model for holding unconfirmed parsed statement lines."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    Date,
    Enum as SQLEnum, 
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.constants import StagedStatus, TransactionType
from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.category import Category
    from shared.models.statement import Statement
    from shared.models.transaction import Transaction


class StagedTransaction(Base, UUIDMixin, TimestampMixin):
    """Parsed statement line staging buffer.

    Lines never enter live transactions directly; they wait here for user
    review, deduplication reconciliation, and category validation.
    """

    __tablename__ = "staged_transactions"
    __table_args__ = (
        Index("ix_staged_transactions_statement_status", "statement_id", "status"),
    )

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    suggested_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Financial precision: NUMERIC(12, 2), zero binary floats
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, name="transaction_type", native_enum=True),
        nullable=False,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    clean_merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Deduplication link to existing confirmed ledger transaction
    potential_duplicate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    duplicate_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # e.g. 0.85

    status: Mapped[StagedStatus] = mapped_column(
        SQLEnum(StagedStatus, name="staged_status", native_enum=True),
        default=StagedStatus.PENDING_REVIEW,
        index=True,
        nullable=False,
    )

    # Relationships
    statement: Mapped["Statement"] = relationship(
        "Statement", back_populates="staged_transactions"
    )
    suggested_category: Mapped["Category | None"] = relationship(
        "Category", back_populates="staged_transactions"
    )
    potential_duplicate: Mapped["Transaction | None"] = relationship(
        "Transaction", back_populates="matched_staged_transactions"
    )
