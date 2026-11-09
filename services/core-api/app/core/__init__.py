"""Core module containing application configuration, security, and RFC 7807 error handlers."""

from app.core.config import Settings, get_settings
from app.core.errors import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    ConflictError,
    FileValidationError,
    NotFoundError,
    ProblemDetail,
    setup_exception_handlers,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "BadRequestError",
    "ConflictError",
    "FileValidationError",
    "NotFoundError",
    "ProblemDetail",
    "Settings",
    "create_access_token",
    "decode_access_token",
    "get_settings",
    "hash_password",
    "setup_exception_handlers",
    "verify_password",
]
