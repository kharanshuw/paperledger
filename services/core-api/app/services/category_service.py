"""Category service managing hierarchical parent/child categories and cycle prevention."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)


class CategoryService:
    """Service handling hierarchical category logic, validation, and tree construction."""

    @staticmethod
    async def list_categories(session: AsyncSession, user_id: uuid.UUID) -> list[CategoryResponse]:
        """Return flat list of all categories owned by the tenant."""
        categories = await CategoryRepository.list_by_user(session, user_id)
        return [CategoryResponse.model_validate(cat) for cat in categories]

    @staticmethod
    async def get_category_tree(session: AsyncSession, user_id: uuid.UUID) -> list[CategoryTreeResponse]:
        """Construct hierarchical category tree with parent groups and nested subcategories."""
        categories = await CategoryRepository.list_by_user(session, user_id)

        # Separate roots from children
        roots: list[CategoryTreeResponse] = []
        children_map: dict[uuid.UUID, list[CategoryResponse]] = {}

        for cat in categories:
            if cat.parent_id is None:
                roots.append(
                    CategoryTreeResponse(
                        id=cat.id,
                        name=cat.name,
                        parent_id=None,
                        subcategories=[],
                    )
                )
            else:
                children_map.setdefault(cat.parent_id, []).append(CategoryResponse.model_validate(cat))

        # Attach direct children to roots
        for root in roots:
            root.subcategories = children_map.get(root.id, [])

        return roots

    @staticmethod
    async def get_category(session: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> CategoryResponse:
        """Fetch single category verifying tenant ownership."""
        category = await CategoryRepository.get_by_id(session, user_id, category_id)
        if not category:
            raise NotFoundError(
                detail=f"Category with ID '{category_id}' was not found.",
                error_type="urn:error:category-not-found",
            )
        return CategoryResponse.model_validate(category)

    @staticmethod 
    async def create_category(
        session: AsyncSession, user_id: uuid.UUID, req: CategoryCreateRequest
    ) -> CategoryResponse:
        """Create category or nested subcategory after validating parent ownership and uniqueness."""
        # 1. Validate parent if specified
        if req.parent_id is not None:
            parent = await CategoryRepository.get_by_id(session, user_id, req.parent_id)
            if not parent:
                raise NotFoundError(
                    detail=f"Parent category with ID '{req.parent_id}' does not exist.",
                    error_type="urn:error:parent-category-not-found",
                )

        # 2. Enforce unique name under same parent
        existing = await CategoryRepository.get_by_name_and_parent(session, user_id, req.name, req.parent_id)
        if existing:
            group_name = "top-level" if req.parent_id is None else f"parent {req.parent_id}"
            raise ConflictError(
                detail=f"A category named '{req.name}' already exists in {group_name}.",
                error_type="urn:error:duplicate-category",
            )

        category = await CategoryRepository.create(
            session=session,
            user_id=user_id,
            name=req.name,
            parent_id=req.parent_id,
        )
        return CategoryResponse.model_validate(category)

    @staticmethod
    async def update_category(
        session: AsyncSession,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        req: CategoryUpdateRequest,
    ) -> CategoryResponse:
        """Update category name or parent, preventing circular loops."""
        category = await CategoryRepository.get_by_id(session, user_id, category_id)
        if not category:
            raise NotFoundError(
                detail=f"Category with ID '{category_id}' was not found.",
                error_type="urn:error:category-not-found",
            )

        new_name = req.name if req.name is not None else category.name
        new_parent_id = req.parent_id if req.parent_id is not None else category.parent_id

        # Cycle prevention: Cannot set self as parent
        if req.parent_id is not None:
            if req.parent_id == category_id:
                raise BadRequestError(
                    detail="A category cannot be its own parent.",
                    error_type="urn:error:circular-hierarchy",
                )

            # Validate parent exists and belongs to user
            parent = await CategoryRepository.get_by_id(session, user_id, req.parent_id)
            if not parent:
                raise NotFoundError(
                    detail=f"Parent category with ID '{req.parent_id}' does not exist.",
                    error_type="urn:error:parent-category-not-found",
                )

            # Cycle prevention: Cannot set descendant as parent
            descendants = await CategoryRepository.get_descendant_ids(session, user_id, category_id)
            if req.parent_id in descendants:
                raise BadRequestError(
                    detail="Cannot set a descendant category as parent (circular hierarchy).",
                    error_type="urn:error:circular-hierarchy",
                )

        # Check name collision if name or parent changed
        if new_name != category.name or new_parent_id != category.parent_id:
            existing = await CategoryRepository.get_by_name_and_parent(session, user_id, new_name, new_parent_id)
            if existing and existing.id != category.id:
                raise ConflictError(
                    detail=f"Another category named '{new_name}' already exists under this parent.",
                    error_type="urn:error:duplicate-category",
                )

        updated = await CategoryRepository.update(
            session=session,
            category=category,
            name=req.name,
            parent_id=req.parent_id,
        )
        return CategoryResponse.model_validate(updated)

    @staticmethod
    async def delete_category(session: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        """Delete category."""
        category = await CategoryRepository.get_by_id(session, user_id, category_id)
        if not category:
            raise NotFoundError(
                detail=f"Category with ID '{category_id}' was not found.",
                error_type="urn:error:category-not-found",
            )
        await CategoryRepository.delete(session, category)
