from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, optional_current_user, get_db
from app.domains.products.schemas import ProductList, ProductRead, ReviewCreate, ReviewRead
from app.domains.products.service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.get("", response_model=ProductList)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: UUID | None = Query(None),
    search: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort_by: str | None = Query(None, pattern="^(price_asc|price_desc|name_asc|name_desc|newest)$"),
    service: ProductService = Depends(get_product_service),
) -> ProductList:
    return await service.list_products(
        page=page,
        page_size=page_size,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    product = await service.get_product(product_id=product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


@router.get("/{product_id}/reviews", response_model=List[ReviewRead])
async def list_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
) -> List[ReviewRead]:
    product = await service.get_product(product_id=product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return await service.list_reviews(
        product_id=product_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{product_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    product_id: UUID,
    payload: ReviewCreate,
    current_user=Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
) -> ReviewRead:
    product = await service.get_product(product_id=product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    review = await service.create_review(
        product_id=product_id,
        user_id=current_user.id,
        payload=payload,
    )
    return review
