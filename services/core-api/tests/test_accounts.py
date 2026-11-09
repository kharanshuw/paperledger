"""Integration tests for Account Domain CRUD and multi-tenant isolation."""

import uuid
from httpx2 import AsyncClient
import pytest


async def get_authenticated_user(async_client: AsyncClient) -> tuple[str, str]:
    """Helper to register a unique user and return (email, token)."""
    email = f"acct_user_{uuid.uuid4().hex[:8]}@example.com"
    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 201
    return email, res.json()["access_token"]


@pytest.mark.asyncio
async def test_list_accounts(async_client: AsyncClient) -> None:
    """Verify listing accounts returns the auto-provisioned Primary Checking account."""
    _, token = await get_authenticated_user(async_client)

    res = await async_client.get(
        "/api/v1/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) >= 1
    assert any(a["name"] == "Primary Checking" for a in accounts)


@pytest.mark.asyncio
async def test_create_account(async_client: AsyncClient) -> None:
    """Verify creating a new account returns 201 Created and persists properties."""
    _, token = await get_authenticated_user(async_client)

    payload = {
        "name": "High Yield Savings",
        "currency": "EUR",
        "account_type": "SAVINGS",
    }
    res = await async_client.post(
        "/api/v1/accounts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "High Yield Savings"
    assert data["currency"] == "EUR"
    assert data["account_type"] == "SAVINGS"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_account_name(async_client: AsyncClient) -> None:
    """Verify creating duplicate account name for the same user fails with 409 RFC 7807."""
    _, token = await get_authenticated_user(async_client)

    payload = {"name": "Travel Card", "currency": "USD", "account_type": "CREDIT_CARD"}
    res1 = await async_client.post("/api/v1/accounts", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/accounts", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 409
    assert res2.headers["content-type"] == "application/problem+json"
    assert res2.json()["type"] == "urn:error:duplicate-account"


@pytest.mark.asyncio
async def test_get_and_update_account(async_client: AsyncClient) -> None:
    """Verify retrieving and updating an existing account."""
    _, token = await get_authenticated_user(async_client)

    create_res = await async_client.post(
        "/api/v1/accounts",
        json={"name": "Investment Portfolio", "currency": "USD", "account_type": "INVESTMENT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_res.json()["id"]

    # 1. Get by ID
    get_res = await async_client.get(
        f"/api/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Investment Portfolio"

    # 2. Update account
    patch_res = await async_client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"name": "Retirement Portfolio (401k)"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Retirement Portfolio (401k)"


@pytest.mark.asyncio
async def test_delete_account(async_client: AsyncClient) -> None:
    """Verify deleting an account returns 204 No Content and removes it."""
    _, token = await get_authenticated_user(async_client)

    create_res = await async_client.post(
        "/api/v1/accounts",
        json={"name": "Temporary Card", "currency": "USD", "account_type": "CREDIT_CARD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_res.json()["id"]

    # Delete
    del_res = await async_client.delete(
        f"/api/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    # Verify not found
    get_res = await async_client.get(
        f"/api/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 404
    assert get_res.json()["type"] == "urn:error:account-not-found"


@pytest.mark.asyncio
async def test_tenant_isolation_accounts(async_client: AsyncClient) -> None:
    """Verify User A cannot view, update, or delete User B's accounts."""
    _, user_a_token = await get_authenticated_user(async_client)
    _, user_b_token = await get_authenticated_user(async_client)

    # User A creates an account
    create_res = await async_client.post(
        "/api/v1/accounts",
        json={"name": "User A Secret Vault", "currency": "USD", "account_type": "SAVINGS"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    acct_a_id = create_res.json()["id"]

    # User B tries to view User A's account -> 404 Not Found
    get_res = await async_client.get(
        f"/api/v1/accounts/{acct_a_id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert get_res.status_code == 404

    # User B tries to update User A's account -> 404 Not Found
    patch_res = await async_client.patch(
        f"/api/v1/accounts/{acct_a_id}",
        json={"name": "Hacked Account"},
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert patch_res.status_code == 404

    # User B tries to delete User A's account -> 404 Not Found
    del_res = await async_client.delete(
        f"/api/v1/accounts/{acct_a_id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert del_res.status_code == 404
