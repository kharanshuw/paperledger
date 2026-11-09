"""Authentication endpoints for user registration, login, and profile retrieval."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Register new user tenant",
    description="Registers a new user account, auto-provisions a default checking account, and issues an access token.",
)
async def register(req: UserRegisterRequest, db: SessionDep) -> TokenResponse:
    """Register user and issue JWT access token."""
    return await AuthService.register(db, req)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Authenticate user",
    description="Validates user credentials and issues a JWT access token.",
)
async def login(req: UserLoginRequest, db: SessionDep) -> TokenResponse:
    """Validate credentials and return access token."""
    return await AuthService.login(db, req)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns authenticated user profile information and verifies tenant authorization barrier.",
)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Return currently authenticated user entity."""
    return UserResponse.model_validate(current_user)
