"""Transaction service coordinating double-entry invariants and cross-tenant validation."""

from datetime import date
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories.account_repo import AccountRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.transaction import (
    PaginatedTransactionsResponse,
    TransactionCreateRequest,
    TransactionResponse,
    TransactionUpdateRequest,
)
from shared.constants import TransactionType


class TransactionService:
    """Service handling transaction ledger business rules and validation."""

    @staticmethod
    async def create_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        req: TransactionCreateRequest,
    ) -> TransactionResponse:
        """Record a manual transaction after validating account and category tenant ownership."""
        # 1. Enforce account ownership
        account = await AccountRepository.get_by_id(session, user_id, req.account_id)
        if not account:
            raise NotFoundError(
                detail=f"Account with ID '{req.account_id}' does not exist.",
                error_type="urn:error:account-not-found",
            )

        # 2. Enforce category ownership if provided
        if req.category_id is not None:
            category = await CategoryRepository.get_by_id(session, user_id, req.category_id)
            if not category:
                raise NotFoundError(
                    detail=f"Category with ID '{req.category_id}' does not exist.",
                    error_type="urn:error:category-not-found",
                )

        # 3. Create transaction record
        transaction = await TransactionRepository.create(
            session=session,
            user_id=user_id,
            account_id=req.account_id,
            category_id=req.category_id,
            amount=req.amount,
            transaction_type=req.transaction_type,
            transaction_date=req.transaction_date,
            raw_description=req.raw_description,
            clean_merchant=req.clean_merchant,
            is_reviewed=True,
        )
        return TransactionResponse.model_validate(transaction)

    @staticmethod
    async def list_transactions(
        session: AsyncSession,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_type: TransactionType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedTransactionsResponse:
        """Fetch filtered transactions verifying any requested account or category filters belong to the user."""
        if account_id is not None:
            account = await AccountRepository.get_by_id(session, user_id, account_id)
            if not account:
                raise NotFoundError(
                    detail=f"Account with ID '{account_id}' does not exist.",
                    error_type="urn:error:account-not-found",
                )

        if category_id is not None:
            category = await CategoryRepository.get_by_id(session, user_id, category_id)
            if not category:
                raise NotFoundError(
                    detail=f"Category with ID '{category_id}' does not exist.",
                    error_type="urn:error:category-not-found",
                )

        items, total = await TransactionRepository.list_by_user(
            session=session,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return PaginatedTransactionsResponse(
            items=[TransactionResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_transaction(
        session: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> TransactionResponse:
        """Fetch single transaction verifying tenant ownership."""
        transaction = await TransactionRepository.get_by_id(session, user_id, transaction_id)
        if not transaction:
            raise NotFoundError(
                detail=f"Transaction with ID '{transaction_id}' was not found.",
                error_type="urn:error:transaction-not-found",
            )
        return TransactionResponse.model_validate(transaction)

    @staticmethod
    async def update_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        req: TransactionUpdateRequest,
    ) -> TransactionResponse:
        """Update an existing transaction record."""
        transaction = await TransactionRepository.get_by_id(session, user_id, transaction_id)
        if not transaction:
            raise NotFoundError(
                detail=f"Transaction with ID '{transaction_id}' was not found.",
                error_type="urn:error:transaction-not-found",
            )

        if req.category_id is not None:
            category = await CategoryRepository.get_by_id(session, user_id, req.category_id)
            if not category:
                raise NotFoundError(
                    detail=f"Category with ID '{req.category_id}' does not exist.",
                    error_type="urn:error:category-not-found",
                )

        updated = await TransactionRepository.update(
            session=session,
            transaction=transaction,
            category_id=req.category_id,
            amount=req.amount,
            transaction_type=req.transaction_type,
            transaction_date=req.transaction_date,
            raw_description=req.raw_description,
            clean_merchant=req.clean_merchant,
        )
        return TransactionResponse.model_validate(updated)

    @staticmethod
    async def delete_transaction(
        session: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> None:
        """Delete transaction from the ledger."""
        transaction = await TransactionRepository.get_by_id(session, user_id, transaction_id)
        if not transaction:
            raise NotFoundError(
                detail=f"Transaction with ID '{transaction_id}' was not found.",
                error_type="urn:error:transaction-not-found",
            )
        await TransactionRepository.delete(session, transaction)
