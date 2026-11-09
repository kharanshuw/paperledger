"""Core API configuration using Pydantic Settings.

Reads configuration from environment variables with sensible defaults for local development.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and runtime environment parameters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = Field(default="development", description="Runtime environment (development, test, production)")
    PROJECT_NAME: str = Field(default="PaperLedger Core API")
    API_V1_PREFIX: str = Field(default="/api/v1")
    DEBUG: bool = Field(default=False)

    # Database & Cache
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/expense_tracker",
        description="Async PostgreSQL connection string",
    )
    SQL_ECHO: bool = Field(default=False)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and task queue",
    )

    # Authentication & Security
    SECRET_KEY: str = Field(
        default="super-secret-core-api-key-change-in-production-min-32-chars-long",
        description="Cryptographic secret key for signing JWTs",
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24,  # 24 hours
        description="JWT access token lifetime in minutes",
    )

    # File Storage (PDF Statement Ingestion)
    UPLOAD_STORAGE_DIR: Path = Field(
        default=Path("/tmp/expense_tracker/uploads"),
        description="Filesystem directory for streamed PDF bank statements",
    )
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=25 * 1024 * 1024,  # 25 MiB
        description="Maximum allowed PDF upload file size in bytes",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

    def init_storage_dirs(self) -> None:
        """Ensure upload storage directories exist with proper permissions."""
        self.UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Singleton cached settings instance."""
    settings = Settings()
    settings.init_storage_dirs()
    return settings
