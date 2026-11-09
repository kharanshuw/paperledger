"""User repository handling raw database queries for User entities."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User


class UserRepository:
    """Repository handling database operations for User records."""

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a single user by primary key UUID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> User | None:
        """Fetch a single user by unique email address."""
        result = await session.execute(select(User).where(User.email == email.strip().lower()))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, email: str, password_hash: str) -> User:
        """Persist a new user entity."""
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user
