"""Pydantic request and response schemas for Core API."""

from app.schemas.account import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from app.schemas.transaction import (
    PaginatedTransactionsResponse,
    TransactionCreateRequest,
    TransactionResponse,
    TransactionUpdateRequest,
)

__all__ = [
    "AccountCreateRequest",
    "AccountResponse",
    "AccountUpdateRequest",
    "CategoryCreateRequest",
    "CategoryResponse",
    "CategoryTreeResponse",
    "CategoryUpdateRequest",
    "PaginatedTransactionsResponse",
    "TokenResponse",
    "TransactionCreateRequest",
    "TransactionResponse",
    "TransactionUpdateRequest",
    "UserLoginRequest",
    "UserRegisterRequest",
    "UserResponse",
]
