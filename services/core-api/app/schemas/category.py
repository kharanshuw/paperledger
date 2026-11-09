"""Pydantic v2 schemas for hierarchical expense categories."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CategoryCreateRequest(BaseModel):
    """Payload for creating a new category or subcategory."""

    name: str = Field(min_length=1, max_length=100, description="Category name (e.g. Groceries, Utilities)")
    parent_id: uuid.UUID | None = Field(default=None, description="Optional parent category UUID for nested subcategories")


class CategoryUpdateRequest(BaseModel):
    """Payload for modifying an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Updated category name")
    parent_id: uuid.UUID | None = Field(default=None, description="Updated parent category UUID")


class CategoryResponse(BaseModel):
    """Flat representation of a category."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique category UUID")
    name: str = Field(description="Category name")
    parent_id: uuid.UUID | None = Field(description="Parent category UUID or None if top-level")
    created_at: datetime = Field(description="Creation timestamp in UTC")


class CategoryTreeResponse(BaseModel):
    """Hierarchical category tree with nested subcategories."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique category UUID")
    name: str = Field(description="Category name")
    parent_id: uuid.UUID | None = Field(default=None, description="Parent category UUID")
    subcategories: list[CategoryResponse] = Field(default_factory=list, description="List of direct subcategories")
