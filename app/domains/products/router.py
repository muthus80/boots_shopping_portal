from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.domains.products.schemas import ProductList, ProductRead, ReviewCreate, ReviewRead
from app.domains.products.service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.get(
    "",
    response_model=ProductList,
    summary="List products (US-005, US-006)",
    description=(
        "Return a paginated list of active products. "
        "Filter by category, price range, size, color, and keyword search. "
        "Each result card includes primary image, name, brand, and price (US-006)."
    ),
)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[UUID] = Query(None, description="Filter by category UUID (US-006)"),
    search: Optional[str] = Query(None, description="Keyword search across name/description"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter (US-005)"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter (US-005)"),
    size: Optional[str] = Query(None, description="Filter by variant size (US-005)"),
    color: Optional[str] = Query(None, description="Filter by variant color (US-005)"),
    in_stock: Optional[bool] = Query(None, description="Filter to in-stock products only"),
    sort_by: Optional[str] = Query(
        None,
        pattern="^(price_asc|price_desc|name_asc|name_desc|newest)$",
        description="Sort order",
    ),
    service: ProductService = Depends(get_product_service),
) -> ProductList:
    """List products with filtering support (US-005, US-006)."""
    return await service.list_products(
        page=page,
        page_size=page_size,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        size=size,
        color=color,
        in_stock=in_stock,
        sort_by=sort_by,
    )


@router.get(
    "/search",
    response_model=ProductList,
    summary="Search products (US-004)",
    description=(
        "Full-text keyword search across product name, brand, and description. "
        "Returns 'No results' compatible empty list when nothing matches (US-004)."
    ),
)
async def search_products(
    q: str = Query(..., min_length=1, description="Full-text search keyword (US-004)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
) -> ProductList:
    """Full-text search across product name, brand, and description (US-004)."""
    return await service.list_products(
        page=page,
        page_size=page_size,
        search=q,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    # NotFoundError raised by service is caught by the global exception handler
    return await service.get_product(product_id=product_id)


@router.get("/{product_id}/reviews", response_model=List[ReviewRead])
async def list_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
) -> List[ReviewRead]:
    return await service.get_product_reviews(
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
    return await service.create_review(
        product_id=product_id,
        user_id=current_user.id,
        payload=payload,
    )
