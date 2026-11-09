"""User model for multi-tenant authentication and identity isolation."""

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.account import Account
    from shared.models.category import Category
    from shared.models.statement import Statement
    from shared.models.transaction import Transaction


class User(Base, UUIDMixin, TimestampMixin):
    """Multi-tenant User entity. Every core domain query must scope by user_id."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    statements: Mapped[list["Statement"]] = relationship(
        "Statement", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
