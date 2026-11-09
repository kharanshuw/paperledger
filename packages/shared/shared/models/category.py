"""Category model supporting hierarchical parent/child expense categories."""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.staged_transaction import StagedTransaction
    from shared.models.transaction import Transaction
    from shared.models.user import User


class Category(Base, UUIDMixin, TimestampMixin):
    """Hierarchical category entity scoped by tenant user_id."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "parent_id", name="uq_user_category_name_parent"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="subcategories"
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )
    staged_transactions: Mapped[list["StagedTransaction"]] = relationship(
        "StagedTransaction", back_populates="suggested_category"
    )
