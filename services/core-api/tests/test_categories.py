"""Integration tests for Hierarchical Category Domain and cycle prevention."""

import uuid
from httpx2 import AsyncClient
import pytest


async def get_authenticated_user(async_client: AsyncClient) -> str:
    """Helper to register a unique user and return access token."""
    email = f"cat_user_{uuid.uuid4().hex[:8]}@example.com"
    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_nest_categories(async_client: AsyncClient) -> None:
    """Verify creating top-level category and nested subcategories."""
    token = await get_authenticated_user(async_client)

    # 1. Create parent category
    parent_res = await async_client.post(
        "/api/v1/categories",
        json={"name": "Food & Dining", "parent_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert parent_res.status_code == 201
    parent_id = parent_res.json()["id"]
    assert parent_res.json()["parent_id"] is None

    # 2. Create subcategory
    sub_res = await async_client.post(
        "/api/v1/categories",
        json={"name": "Groceries", "parent_id": parent_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sub_res.status_code == 201
    assert sub_res.json()["parent_id"] == parent_id

    # 3. Retrieve category tree
    tree_res = await async_client.get(
        "/api/v1/categories/tree",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tree_res.status_code == 200
    tree = tree_res.json()
    food_cat = next((c for c in tree if c["id"] == parent_id), None)
    assert food_cat is not None
    assert len(food_cat["subcategories"]) == 1
    assert food_cat["subcategories"][0]["name"] == "Groceries"


@pytest.mark.asyncio
async def test_duplicate_category_under_same_parent(async_client: AsyncClient) -> None:
    """Verify duplicate category names under the same parent fail with 409 RFC 7807."""
    token = await get_authenticated_user(async_client)

    parent_res = await async_client.post(
        "/api/v1/categories",
        json={"name": "Utilities", "parent_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    parent_id = parent_res.json()["id"]

    # First subcategory
    r1 = await async_client.post(
        "/api/v1/categories",
        json={"name": "Electricity", "parent_id": parent_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201

    # Duplicate subcategory under same parent
    r2 = await async_client.post(
        "/api/v1/categories",
        json={"name": "Electricity", "parent_id": parent_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409
    assert r2.headers["content-type"] == "application/problem+json"
    assert r2.json()["type"] == "urn:error:duplicate-category"


@pytest.mark.asyncio
async def test_parent_not_found(async_client: AsyncClient) -> None:
    """Verify specifying non-existent parent_id fails with 404 RFC 7807."""
    token = await get_authenticated_user(async_client)
    fake_parent_id = str(uuid.uuid4())

    res = await async_client.post(
        "/api/v1/categories",
        json={"name": "Orphan Subcategory", "parent_id": fake_parent_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["type"] == "urn:error:parent-category-not-found"


@pytest.mark.asyncio
async def test_prevent_circular_hierarchy(async_client: AsyncClient) -> None:
    """Verify cycle prevention: category cannot be its own parent or descendant's child."""
    token = await get_authenticated_user(async_client)

    # 1. Create Parent A
    res_a = await async_client.post(
        "/api/v1/categories",
        json={"name": "Parent Category A"},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_a = res_a.json()["id"]

    # 2. Try to set Parent A as its own parent -> 400 Circular Hierarchy
    self_loop = await async_client.patch(
        f"/api/v1/categories/{id_a}",
        json={"parent_id": id_a},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert self_loop.status_code == 400
    assert self_loop.json()["type"] == "urn:error:circular-hierarchy"

    # 3. Create Child B under Parent A
    res_b = await async_client.post(
        "/api/v1/categories",
        json={"name": "Child Category B", "parent_id": id_a},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_b = res_b.json()["id"]

    # 4. Try to set Parent A's parent to Child B -> 400 Circular Hierarchy
    cycle_res = await async_client.patch(
        f"/api/v1/categories/{id_a}",
        json={"parent_id": id_b},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cycle_res.status_code == 400
    assert cycle_res.json()["type"] == "urn:error:circular-hierarchy"


@pytest.mark.asyncio
async def test_tenant_isolation_categories(async_client: AsyncClient) -> None:
    """Verify User A's categories cannot be accessed, nested into, or deleted by User B."""
    token_a = await get_authenticated_user(async_client)
    token_b = await get_authenticated_user(async_client)

    # User A creates a category
    res_a = await async_client.post(
        "/api/v1/categories",
        json={"name": "User A Private Category"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    id_a = res_a.json()["id"]

    # User B cannot view User A's category -> 404
    get_res = await async_client.get(
        f"/api/v1/categories/{id_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_res.status_code == 404

    # User B cannot use User A's category as parent -> 404
    nest_res = await async_client.post(
        "/api/v1/categories",
        json={"name": "User B Attempt", "parent_id": id_a},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert nest_res.status_code == 404
