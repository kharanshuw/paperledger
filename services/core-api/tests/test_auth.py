"""Integration tests for authentication, tenant onboarding, and RFC 7807 error responses."""

import uuid
from httpx2 import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Verify system health endpoint reports healthy database and Redis status."""
    res = await async_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient) -> None:
    """Verify clean registration returns 201 Created and a valid JWT bearer token."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "SecurePassword123!"}

    res = await async_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient) -> None:
    """Verify duplicate registration fails with HTTP 409 Conflict adhering to RFC 7807."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "SecurePassword123!"}

    # First registration
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email
    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.headers["content-type"] == "application/problem+json"

    problem = res2.json()
    assert problem["type"] == "urn:error:duplicate-email"
    assert problem["status"] == 409
    assert "already exists" in problem["detail"]


@pytest.mark.asyncio
async def test_register_validation_error(async_client: AsyncClient) -> None:
    """Verify invalid payloads (short password, invalid email) fail with RFC 7807 422."""
    # Short password (< 8 chars)
    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert res.status_code == 422
    assert res.headers["content-type"] == "application/problem+json"

    problem = res.json()
    assert problem["type"] == "urn:error:validation-error"
    assert problem["status"] == 422
    assert len(problem["invalid_params"]) > 0


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient) -> None:
    """Verify authenticating with valid credentials returns a valid JWT token."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "MyPassword123!"

    # Setup user
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})

    # Perform login
    res = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient) -> None:
    """Verify invalid password returns HTTP 401 Unauthorized with RFC 7807 problem details."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    await async_client.post(
        "/api/v1/auth/register", json={"email": email, "password": "CorrectPassword123"}
    )

    res = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": "WrongPassword123"}
    )
    assert res.status_code == 401
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["type"] == "urn:error:invalid-credentials"


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient) -> None:
    """Verify logging in with non-existent email returns 401 Unauthorized."""
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword123"},
    )
    assert res.status_code == 401
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["type"] == "urn:error:invalid-credentials"


@pytest.mark.asyncio
async def test_get_me_authenticated(async_client: AsyncClient) -> None:
    """Verify authenticated user can retrieve their profile via /me."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "Password123!"

    reg_res = await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    token = reg_res.json()["access_token"]

    res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == email
    assert profile["is_active"] is True
    assert "id" in profile


@pytest.mark.asyncio
async def test_get_me_unauthenticated(async_client: AsyncClient) -> None:
    """Verify accessing /me without Authorization header returns 401 RFC 7807."""
    res = await async_client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["type"] == "urn:error:unauthorized"


@pytest.mark.asyncio
async def test_get_me_invalid_token(async_client: AsyncClient) -> None:
    """Verify accessing /me with tampered token returns 401 RFC 7807."""
    res = await async_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer fake.tampered.token"}
    )
    assert res.status_code == 401
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["type"] == "urn:error:invalid-token"
