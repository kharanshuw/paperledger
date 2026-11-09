"""Transaction model representing the primary confirmed double-entry ledger."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
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

from shared.constants import TransactionType
from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.account import Account
    from shared.models.category import Category
    from shared.models.staged_transaction import StagedTransaction
    from shared.models.statement import Statement
    from shared.models.user import User


class Transaction(Base, UUIDMixin, TimestampMixin):
    """Primary confirmed ledger entry. Source of truth for accounts and analytics."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_account_date", "account_id", "transaction_date"),
        Index("ix_transactions_account_amount_date", "account_id", "amount", "transaction_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    statement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="SET NULL"),
        index=True,
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
    clean_merchant: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    category: Mapped["Category | None"] = relationship("Category", back_populates="transactions")
    statement: Mapped["Statement | None"] = relationship("Statement", back_populates="transactions")
    matched_staged_transactions: Mapped[list["StagedTransaction"]] = relationship(
        "StagedTransaction", back_populates="potential_duplicate"
    )
