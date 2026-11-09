"""Category repository handling raw database queries for hierarchical categories."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.category import Category


class CategoryRepository:
    """Repository handling database operations for Category records."""

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: uuid.UUID) -> list[Category]:
        """Fetch all categories for a user, sorted alphabetically."""
        query = select(Category).where(Category.user_id == user_id).order_by(Category.name.asc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
        """Fetch a single category ensuring tenant user ownership."""
        query = select(Category).where(Category.id == category_id, Category.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name_and_parent(
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        parent_id: uuid.UUID | None,
    ) -> Category | None:
        """Check if category name already exists under the same parent for this user."""
        parent_filter = Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id
        query = select(Category).where(
            Category.user_id == user_id,
            Category.name == name.strip(),
            parent_filter,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_descendant_ids(
        session: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """Traverse category hierarchy to collect all descendant UUIDs (prevents cycles)."""
        all_categories = await CategoryRepository.list_by_user(session, user_id)
        parent_to_children: dict[uuid.UUID, list[uuid.UUID]] = {}
        for cat in all_categories:
            if cat.parent_id:
                parent_to_children.setdefault(cat.parent_id, []).append(cat.id)

        descendants: set[uuid.UUID] = set()
        queue = list(parent_to_children.get(category_id, []))
        while queue:
            child_id = queue.pop(0)
            if child_id not in descendants:
                descendants.add(child_id)
                queue.extend(parent_to_children.get(child_id, []))

        return descendants

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        parent_id: uuid.UUID | None,
    ) -> Category:
        """Persist a new category entity."""
        category = Category(
            user_id=user_id,
            name=name.strip(),
            parent_id=parent_id,
        )
        session.add(category)
        await session.flush()
        return category

    @staticmethod
    async def update(
        session: AsyncSession,
        category: Category,
        name: str | None = None,
        parent_id: uuid.UUID | None = None,
        clear_parent: bool = False,
    ) -> Category:
        """Apply updates to an existing category."""
        if name is not None:
            category.name = name.strip()
        if clear_parent:
            category.parent_id = None
        elif parent_id is not None:
            category.parent_id = parent_id

        await session.flush()
        return category

    @staticmethod
    async def delete(session: AsyncSession, category: Category) -> None:
        """Delete category entity."""
        await session.delete(category)
        await session.flush()
