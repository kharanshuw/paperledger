"""Pytest fixtures for Core API integration tests."""

from collections.abc import AsyncGenerator
from typing import Any
import pytest
from httpx2 import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, Any]:
    """Provide an async test client configured with the FastAPI ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
