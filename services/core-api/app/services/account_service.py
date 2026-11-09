"""Account service orchestrating business rules and multi-tenant security for financial accounts."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.repositories.account_repo import AccountRepository
from app.schemas.account import AccountCreateRequest, AccountResponse, AccountUpdateRequest


class AccountService:
    """Service handling account business logic and validation."""

    @staticmethod
    async def list_accounts(session: AsyncSession, user_id: uuid.UUID) -> list[AccountResponse]:
        """Retrieve all accounts owned by the authenticated tenant."""
        accounts = await AccountRepository.list_by_user(session, user_id)
        return [AccountResponse.model_validate(acct) for acct in accounts]

    @staticmethod
    async def get_account(session: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> AccountResponse:
        """Retrieve a specific account by ID, verifying tenant ownership."""
        account = await AccountRepository.get_by_id(session, user_id, account_id)
        if not account:
            raise NotFoundError(
                detail=f"Account with ID '{account_id}' was not found.",
                error_type="urn:error:account-not-found",
            )
        return AccountResponse.model_validate(account)

    @staticmethod
    async def create_account(
        session: AsyncSession, user_id: uuid.UUID, req: AccountCreateRequest
    ) -> AccountResponse:
        """Create a new account after validating uniqueness of the account name."""
        existing = await AccountRepository.get_by_name(session, user_id, req.name)
        if existing:
            raise ConflictError(
                detail=f"An account named '{req.name}' already exists in your workspace.",
                error_type="urn:error:duplicate-account",
            )

        account = await AccountRepository.create(
            session=session,
            user_id=user_id,
            name=req.name,
            currency=req.currency,
            account_type=req.account_type,
        )
        return AccountResponse.model_validate(account)

    @staticmethod
    async def update_account(
        session: AsyncSession,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        req: AccountUpdateRequest,
    ) -> AccountResponse:
        """Update an existing account with conflict detection."""
        account = await AccountRepository.get_by_id(session, user_id, account_id)
        if not account:
            raise NotFoundError(
                detail=f"Account with ID '{account_id}' was not found.",
                error_type="urn:error:account-not-found",
            )

        # Check for name collision if updating name
        if req.name is not None and req.name.strip() != account.name:
            existing = await AccountRepository.get_by_name(session, user_id, req.name)
            if existing and existing.id != account.id:
                raise ConflictError(
                    detail=f"Another account named '{req.name}' already exists.",
                    error_type="urn:error:duplicate-account",
                )

        updated_account = await AccountRepository.update(
            session=session,
            account=account,
            name=req.name,
            currency=req.currency,
            account_type=req.account_type,
        )
        return AccountResponse.model_validate(updated_account)

    @staticmethod
    async def delete_account(
        session: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> None:
        """Delete an account owned by the tenant."""
        account = await AccountRepository.get_by_id(session, user_id, account_id)
        if not account:
            raise NotFoundError(
                detail=f"Account with ID '{account_id}' was not found.",
                error_type="urn:error:account-not-found",
            )

        await AccountRepository.delete(session, account)
