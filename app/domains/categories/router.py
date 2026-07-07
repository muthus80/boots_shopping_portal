from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.domains.categories.schemas import CategoryList, CategoryRead
from app.domains.categories.service import CategoryService

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=CategoryList)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> CategoryList:
    service = CategoryService(db)
    return await service.list_categories()


@router.get("/{slug}", response_model=CategoryRead)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> CategoryRead:
    service = CategoryService(db)
    category = await service.get_category_by_slug(slug)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with slug '{slug}' not found.",
        )
    return category
