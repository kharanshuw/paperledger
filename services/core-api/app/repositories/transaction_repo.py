"""Transaction repository handling database queries for the primary confirmed ledger."""

from datetime import date
from decimal import Decimal
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.constants import TransactionType
from shared.models.transaction import Transaction


class TransactionRepository:
    """Repository handling database operations for Transaction ledger records."""

    @staticmethod
    async def list_by_user(
        session: AsyncSession,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_type: TransactionType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Fetch paginated transactions matching optional filters, strictly scoped to user_id."""
        conditions = [Transaction.user_id == user_id]

        if account_id is not None:
            conditions.append(Transaction.account_id == account_id)
        if category_id is not None:
            conditions.append(Transaction.category_id == category_id)
        if transaction_type is not None:
            conditions.append(Transaction.transaction_type == transaction_type)
        if start_date is not None:
            conditions.append(Transaction.transaction_date >= start_date)
        if end_date is not None:
            conditions.append(Transaction.transaction_date <= end_date)

        # 1. Total count query
        count_query = select(func.count(Transaction.id)).where(*conditions)
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # 2. Paginated items query
        items_query = (
            select(Transaction)
            .where(*conditions)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_result = await session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    @staticmethod
    async def get_by_id(
        session: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> Transaction | None:
        """Fetch a single transaction verifying tenant user ownership."""
        query = select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        transaction_type: TransactionType,
        transaction_date: date,
        raw_description: str,
        category_id: uuid.UUID | None = None,
        clean_merchant: str | None = None,
        is_reviewed: bool = True,
        statement_id: uuid.UUID | None = None,
    ) -> Transaction:
        """Persist a new transaction in the confirmed ledger."""
        transaction = Transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            statement_id=statement_id,
            amount=amount,
            transaction_type=transaction_type,
            transaction_date=transaction_date,
            raw_description=raw_description.strip(),
            clean_merchant=clean_merchant.strip() if clean_merchant else None,
            is_reviewed=is_reviewed,
        )
        session.add(transaction)
        await session.flush()
        return transaction

    @staticmethod
    async def update(
        session: AsyncSession,
        transaction: Transaction,
        category_id: uuid.UUID | None = None,
        amount: Decimal | None = None,
        transaction_type: TransactionType | None = None,
        transaction_date: date | None = None,
        raw_description: str | None = None,
        clean_merchant: str | None = None,
        clear_category: bool = False,
    ) -> Transaction:
        """Apply updates to an existing transaction record."""
        if clear_category:
            transaction.category_id = None
        elif category_id is not None:
            transaction.category_id = category_id

        if amount is not None:
            transaction.amount = amount
        if transaction_type is not None:
            transaction.transaction_type = transaction_type
        if transaction_date is not None:
            transaction.transaction_date = transaction_date
        if raw_description is not None:
            transaction.raw_description = raw_description.strip()
        if clean_merchant is not None:
            transaction.clean_merchant = clean_merchant.strip()

        await session.flush()
        return transaction

    @staticmethod
    async def delete(session: AsyncSession, transaction: Transaction) -> None:
        """Delete transaction from the ledger."""
        await session.delete(transaction)
        await session.flush()
