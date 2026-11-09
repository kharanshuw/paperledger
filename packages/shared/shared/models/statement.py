"""Statement model for tracking uploaded PDF bank/credit card statements."""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.constants import StatementStatus
from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.account import Account
    from shared.models.staged_transaction import StagedTransaction
    from shared.models.transaction import Transaction
    from shared.models.user import User


class Statement(Base, UUIDMixin, TimestampMixin):
    """Uploaded bank or credit card statement batch."""

    __tablename__ = "statements"
    __table_args__ = (
        Index("ix_statements_user_file_hash", "user_id", "file_hash"),
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
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 digest of binary content
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[StatementStatus] = mapped_column(
        SQLEnum(StatementStatus, name="statement_status", native_enum=True),
        default=StatementStatus.QUEUED,
        index=True,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="statements")
    account: Mapped["Account"] = relationship("Account", back_populates="statements")
    staged_transactions: Mapped[list["StagedTransaction"]] = relationship(
        "StagedTransaction", back_populates="statement", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="statement"
    )
