"""Account model representing user financial accounts (Checking, Savings, Credit Card)."""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum as SQLEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.constants import AccountType
from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin 

if TYPE_CHECKING:
    from shared.models.statement import Statement
    from shared.models.transaction import Transaction
    from shared.models.user import User


class Account(Base, UUIDMixin, TimestampMixin):
    """Financial account owned by a user."""

    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)  # ISO 4217
    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType, name="account_type", native_enum=True),
        default=AccountType.CHECKING,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    statements: Mapped[list["Statement"]] = relationship(
        "Statement", back_populates="account", cascade="all, delete-orphan"
    )
