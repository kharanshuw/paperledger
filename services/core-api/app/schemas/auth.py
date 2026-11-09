"""Pydantic v2 schemas for authentication, registration, and tokens."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field
  

class UserRegisterRequest(BaseModel):
    """Payload for registering a new user tenant."""

    email: EmailStr = Field(description="Unique email address for user login")
    password: str = Field(min_length=8, max_length=128, description="Plain text password (min 8 chars)")


class UserLoginRequest(BaseModel):
    """Payload for user login authentication."""

    email: EmailStr = Field(description="Registered email address")
    password: str = Field(description="Account password")


class TokenResponse(BaseModel):
    """Response containing signed JWT access token."""

    access_token: str = Field(description="Signed JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token type identifier")
    expires_in: int = Field(description="Token lifetime in seconds")


class UserResponse(BaseModel):
    """Public user tenant representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique tenant user UUID")
    email: EmailStr = Field(description="User email address")
    is_active: bool = Field(description="Whether the user account is active")
    created_at: datetime = Field(description="Account registration timestamp (UTC)")
