"""Account repository handling raw SQLAlchemy queries strictly scoped by user_id."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.constants import AccountType
from shared.models.account import Account


class AccountRepository:
    """Repository handling database operations for financial Account records."""

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: uuid.UUID) -> list[Account]:
        """Fetch all accounts belonging to the tenant, sorted by creation date."""
        query = select(Account).where(Account.user_id == user_id).order_by(Account.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account | None:
        """Fetch a single account ensuring strict multi-tenant ownership."""
        query = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(session: AsyncSession, user_id: uuid.UUID, name: str) -> Account | None:
        """Fetch an account by name for a specific user to prevent duplicate naming."""
        query = select(Account).where(Account.user_id == user_id, Account.name == name.strip())
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        currency: str,
        account_type: AccountType,
    ) -> Account:
        """Persist a new financial account."""
        account = Account(
            user_id=user_id,
            name=name.strip(),
            currency=currency.strip().upper(),
            account_type=account_type,
        )
        session.add(account)
        await session.flush()
        return account

    @staticmethod
    async def update(
        session: AsyncSession,
        account: Account,
        name: str | None = None,
        currency: str | None = None,
        account_type: AccountType | None = None,
    ) -> Account:
        """Apply updates to an existing account model."""
        if name is not None:
            account.name = name.strip()
        if currency is not None:
            account.currency = currency.strip().upper()
        if account_type is not None:
            account.account_type = account_type

        await session.flush()
        return account

    @staticmethod
    async def delete(session: AsyncSession, account: Account) -> None:
        """Delete an account record from the database."""
        await session.delete(account)
        await session.flush()
