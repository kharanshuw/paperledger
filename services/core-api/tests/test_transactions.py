"""Integration tests for Primary Ledger Transaction Domain, financial precision, and multi-tenant security."""

from datetime import date, timedelta
import uuid
from httpx2 import AsyncClient
import pytest


async def setup_test_context(async_client: AsyncClient) -> dict[str, str]:
    """Helper to register user, fetch primary checking account, and create a test category."""
    email = f"txn_user_{uuid.uuid4().hex[:8]}@example.com"
    auth_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert auth_res.status_code == 201
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch default account
    accts_res = await async_client.get("/api/v1/accounts", headers=headers)
    account_id = accts_res.json()[0]["id"]

    # Create category
    cat_res = await async_client.post(
        "/api/v1/categories",
        json={"name": "Groceries"},
        headers=headers,
    )
    category_id = cat_res.json()["id"]

    return {
        "token": token,
        "account_id": account_id,
        "category_id": category_id,
    }


@pytest.mark.asyncio
async def test_create_debit_transaction_success(async_client: AsyncClient) -> None:
    """Verify recording an expense with exact Decimal string precision."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    payload = {
        "account_id": ctx["account_id"],
        "category_id": ctx["category_id"],
        "amount": "124.50",
        "transaction_type": "DEBIT",
        "transaction_date": str(date.today()),
        "raw_description": "TRADER JOES SOMA SAN FRANCISCO",
        "clean_merchant": "Trader Joe's",
    }

    res = await async_client.post("/api/v1/transactions", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "124.50"
    assert data["transaction_type"] == "DEBIT"
    assert data["clean_merchant"] == "Trader Joe's"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_credit_transaction_success(async_client: AsyncClient) -> None:
    """Verify recording income with exact Decimal string precision."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    payload = {
        "account_id": ctx["account_id"],
        "amount": "3500.00",
        "transaction_type": "CREDIT",
        "transaction_date": str(date.today()),
        "raw_description": "ACH DEPOSIT PAYROLL",
    }

    res = await async_client.post("/api/v1/transactions", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["amount"] == "3500.00"
    assert res.json()["transaction_type"] == "CREDIT"


@pytest.mark.asyncio
async def test_reject_float_monetary_amount(async_client: AsyncClient) -> None:
    """Verify binary floats are strictly rejected with RFC 7807 422 to prevent precision loss."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    # Pass float literal (124.5) instead of string/decimal
    payload = {
        "account_id": ctx["account_id"],
        "amount": 124.5,
        "transaction_type": "DEBIT",
        "transaction_date": str(date.today()),
        "raw_description": "Coffee Shop",
    }

    res = await async_client.post("/api/v1/transactions", json=payload, headers=headers)
    assert res.status_code == 422
    assert res.headers["content-type"] == "application/problem+json"

    problem = res.json()
    assert problem["type"] == "urn:error:validation-error"
    assert any("Float types are forbidden" in p.get("reason", "") for p in problem["invalid_params"])


@pytest.mark.asyncio
async def test_reject_negative_or_zero_amount(async_client: AsyncClient) -> None:
    """Verify non-positive amounts are rejected (direction is strictly handled by DEBIT/CREDIT)."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    # Test negative amount
    res_neg = await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "-50.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(date.today()),
            "raw_description": "Negative expense",
        },
        headers=headers,
    )
    assert res_neg.status_code == 422

    # Test zero amount
    res_zero = await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "0.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(date.today()),
            "raw_description": "Zero expense",
        },
        headers=headers,
    )
    assert res_zero.status_code == 422


@pytest.mark.asyncio
async def test_cross_tenant_isolation_transaction(async_client: AsyncClient) -> None:
    """Verify User A cannot post transactions into User B's accounts or categories."""
    user_a = await setup_test_context(async_client)
    user_b = await setup_test_context(async_client)

    headers_a = {"Authorization": f"Bearer {user_a['token']}"}

    # User A tries to record transaction in User B's account -> 404
    res_bad_acct = await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": user_b["account_id"],
            "amount": "100.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(date.today()),
            "raw_description": "Attempted cross-tenant write",
        },
        headers=headers_a,
    )
    assert res_bad_acct.status_code == 404
    assert res_bad_acct.json()["type"] == "urn:error:account-not-found"

    # User A tries to attach User B's category -> 404
    res_bad_cat = await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": user_a["account_id"],
            "category_id": user_b["category_id"],
            "amount": "100.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(date.today()),
            "raw_description": "Attempted cross-tenant category link",
        },
        headers=headers_a,
    )
    assert res_bad_cat.status_code == 404
    assert res_bad_cat.json()["type"] == "urn:error:category-not-found"


@pytest.mark.asyncio
async def test_filter_and_paginate_transactions(async_client: AsyncClient) -> None:
    """Verify filtering transactions by date range and direction."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}
    today = date.today()

    # Create 3 transactions on different dates
    await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "50.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(today - timedelta(days=5)),
            "raw_description": "Old expense",
        },
        headers=headers,
    )
    await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "1000.00",
            "transaction_type": "CREDIT",
            "transaction_date": str(today - timedelta(days=2)),
            "raw_description": "Salary deposit",
        },
        headers=headers,
    )
    await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "30.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(today),
            "raw_description": "Recent expense",
        },
        headers=headers,
    )

    # 1. Filter by DEBIT direction
    res_debit = await async_client.get(
        "/api/v1/transactions?transaction_type=DEBIT", headers=headers
    )
    assert res_debit.status_code == 200
    assert all(t["transaction_type"] == "DEBIT" for t in res_debit.json()["items"])
    assert res_debit.json()["total"] == 2

    # 2. Filter by date window (past 3 days)
    res_date = await async_client.get(
        f"/api/v1/transactions?start_date={today - timedelta(days=3)}", headers=headers
    )
    assert res_date.status_code == 200
    assert res_date.json()["total"] == 2


@pytest.mark.asyncio
async def test_update_and_delete_transaction(async_client: AsyncClient) -> None:
    """Verify updating fields and deleting transaction."""
    ctx = await setup_test_context(async_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    create_res = await async_client.post(
        "/api/v1/transactions",
        json={
            "account_id": ctx["account_id"],
            "amount": "45.00",
            "transaction_type": "DEBIT",
            "transaction_date": str(date.today()),
            "raw_description": "Initial text",
        },
        headers=headers,
    )
    txn_id = create_res.json()["id"]

    # Update amount and merchant
    patch_res = await async_client.patch(
        f"/api/v1/transactions/{txn_id}",
        json={"amount": "49.99", "clean_merchant": "Updated Store"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "49.99"
    assert patch_res.json()["clean_merchant"] == "Updated Store"

    # Delete
    del_res = await async_client.delete(f"/api/v1/transactions/{txn_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify not found
    get_res = await async_client.get(f"/api/v1/transactions/{txn_id}", headers=headers)
    assert get_res.status_code == 404
