"""Authentication service coordinating registration, login, and tenant account provisioning."""

from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from shared.constants import AccountType
from shared.models.account import Account
from shared.models.user import User


class AuthService:
    """Service handling tenant registration and credential validation."""

    @staticmethod
    async def register(session: AsyncSession, req: UserRegisterRequest) -> TokenResponse:
        """Register a new user tenant and provision baseline account."""
        settings = get_settings()

        # 1. Enforce unique email constraint
        existing = await UserRepository.get_by_email(session, req.email)
        if existing:
            raise ConflictError(
                detail=f"An account with email '{req.email}' already exists.",
                error_type="urn:error:duplicate-email",
            )

        # 2. Hash password with Argon2id
        hashed_pw = hash_password(req.password)

        # 3. Create user
        user = await UserRepository.create(session, req.email, hashed_pw)

        # 4. Provision default primary checking account
        default_account = Account(
            user_id=user.id,
            name="Primary Checking",
            currency="USD",
            account_type=AccountType.CHECKING,
        )
        session.add(default_account)
        await session.flush()

        # 5. Generate JWT access token
        access_token = create_access_token(subject=user.id)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    @staticmethod
    async def login(session: AsyncSession, req: UserLoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue JWT token."""
        settings = get_settings()

        # 1. Find user by email
        user = await UserRepository.get_by_email(session, req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise AuthenticationError(
                detail="Invalid email or password.",
                error_type="urn:error:invalid-credentials",
            )

        # 2. Check active status
        if not user.is_active:
            raise AuthenticationError(
                detail="Your account has been deactivated. Please contact support.",
                error_type="urn:error:user-inactive",
            )

        # 3. Issue access token
        access_token = create_access_token(subject=user.id)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )
