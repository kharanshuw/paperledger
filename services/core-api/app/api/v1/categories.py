"""Category API endpoints for hierarchical expense categories."""

import uuid
from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from app.services.category_service import CategoryService

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryResponse],
    summary="List all categories",
    description="Returns flat list of all categories and subcategories owned by the user.",
)
async def list_categories(
    current_user: CurrentUserDep,
    db: SessionDep,
) -> list[CategoryResponse]:
    """List tenant categories."""
    return await CategoryService.list_categories(db, current_user.id)


@router.get(
    "/tree",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryTreeResponse],
    summary="Get hierarchical category tree",
    description="Returns root categories with nested direct subcategories for UI rendering.",
)
async def get_category_tree(
    current_user: CurrentUserDep,
    db: SessionDep,
) -> list[CategoryTreeResponse]:
    """Retrieve category tree."""
    return await CategoryService.get_category_tree(db, current_user.id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryResponse,
    summary="Create category",
    description="Creates a top-level category (parent_id is null) or a nested subcategory.",
)
async def create_category(
    req: CategoryCreateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> CategoryResponse:
    """Create a new category."""
    return await CategoryService.create_category(db, current_user.id, req)


@router.get(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Get category by ID",
    description="Fetches a specific category by UUID, validating tenant ownership.",
)
async def get_category(
    category_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> CategoryResponse:
    """Get single category."""
    return await CategoryService.get_category(db, current_user.id, category_id)


@router.patch(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Update category",
    description="Updates category name or moves it under a new parent.",
)
async def update_category(
    category_id: uuid.UUID,
    req: CategoryUpdateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> CategoryResponse:
    """Update category."""
    return await CategoryService.update_category(db, current_user.id, category_id, req)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete category",
    description="Deletes category. Subcategories are dissociated (parent_id set to null).",
)
async def delete_category(
    category_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> Response:
    """Delete category."""
    await CategoryService.delete_category(db, current_user.id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
