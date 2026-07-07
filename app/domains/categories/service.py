from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.categories.models import Category
from app.domains.categories.schemas import CategoryList, CategoryRead
from app.core.exceptions import NotFoundError


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_categories(
        self,
        parent_id: Optional[uuid.UUID] = None,
        include_inactive: bool = False,
    ) -> CategoryList:
        stmt = select(Category)

        if not include_inactive:
            stmt = stmt.where(Category.is_active.is_(True))

        if parent_id is not None:
            stmt = stmt.where(Category.parent_id == parent_id)
        else:
            stmt = stmt.where(Category.parent_id.is_(None))

        stmt = stmt.order_by(Category.name)

        result = await self.db.execute(stmt)
        categories: List[Category] = list(result.scalars().all())

        items = [CategoryRead.model_validate(c) for c in categories]
        return CategoryList(items=items, total=len(items))

    async def get_category(self, category_id: uuid.UUID) -> CategoryRead:
        stmt = select(Category).where(Category.id == category_id)
        result = await self.db.execute(stmt)
        category: Optional[Category] = result.scalar_one_or_none()

        if category is None:
            raise NotFoundError(f"Category with id {category_id} not found")

        return CategoryRead.model_validate(category)

    async def get_category_by_slug(self, slug: str) -> CategoryRead:
        stmt = select(Category).where(Category.slug == slug)
        result = await self.db.execute(stmt)
        category: Optional[Category] = result.scalar_one_or_none()

        if category is None:
            raise NotFoundError(f"Category with slug '{slug}' not found")

        return CategoryRead.model_validate(category)

    async def list_all_categories(self, include_inactive: bool = False) -> CategoryList:
        stmt = select(Category)

        if not include_inactive:
            stmt = stmt.where(Category.is_active.is_(True))

        stmt = stmt.order_by(Category.name)

        result = await self.db.execute(stmt)
        categories: List[Category] = list(result.scalars().all())

        items = [CategoryRead.model_validate(c) for c in categories]
        return CategoryList(items=items, total=len(items))
