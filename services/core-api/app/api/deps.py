"""Dependency injection providers for database sessions and tenant authentication."""

from collections.abc import AsyncGenerator
from typing import Annotated, Any
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.security import decode_access_token
from shared.database import get_session_factory
from shared.models.user import User

settings = get_settings()

# Use auto_error=False to intercept missing headers and emit RFC 7807 Problem Details
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """Yield an isolated asynchronous database session with automatic commit/rollback."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
 

SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: SessionDep,
) -> User:
    """Extract and authenticate the multi-tenant user from the Bearer token.

    Raises:
        AuthenticationError: If token is missing, expired, invalid, or user is inactive.
    """
    if not token:
        raise AuthenticationError(
            detail="Authentication credentials were not provided. Pass 'Authorization: Bearer <token>' header.",
            error_type="urn:error:unauthorized",
        )

    payload = decode_access_token(token)
    user_id_str = payload.get("sub")

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError) as exc:
        raise AuthenticationError(
            detail="Token subject identifier is not a valid UUID.",
            error_type="urn:error:invalid-token",
        ) from exc

    # Query active user
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(
            detail="The user account associated with this token no longer exists.",
            error_type="urn:error:user-not-found",
        )

    if not user.is_active:
        raise AuthenticationError(
            detail="This user account has been deactivated.",
            error_type="urn:error:user-inactive",
        )

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
