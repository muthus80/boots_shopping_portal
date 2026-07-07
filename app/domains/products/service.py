from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import exists, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.products.models import Product, ProductVariant, Review
from app.domains.products.schemas import ProductList, ProductRead, ReviewCreate, ReviewRead
from app.core.exceptions import NotFoundError, ConflictError


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_products(
        self,
        *,
        category_id: Optional[UUID] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        in_stock: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> ProductList:
        filters = []

        if category_id is not None:
            filters.append(Product.category_id == category_id)

        if search:
            term = f"%{search.lower()}%"
            filters.append(
                func.lower(Product.name).like(term)
                | func.lower(Product.description).like(term)
                | func.lower(Product.brand).like(term)
            )

        # Faceted size/color filtering via EXISTS on variants (US-005)
        if size is not None:
            filters.append(
                exists().where(
                    and_(
                        ProductVariant.product_id == Product.id,
                        func.lower(ProductVariant.size) == size.lower(),
                        ProductVariant.is_active.is_(True),
                    )
                )
            )

        if color is not None:
            filters.append(
                exists().where(
                    and_(
                        ProductVariant.product_id == Product.id,
                        func.lower(ProductVariant.color) == color.lower(),
                        ProductVariant.is_active.is_(True),
                    )
                )
            )

        if min_price is not None:
            filters.append(Product.price >= min_price)

        if max_price is not None:
            filters.append(Product.price <= max_price)

        if in_stock is True:
            filters.append(Product.stock_quantity > 0)
        elif in_stock is False:
            filters.append(Product.stock_quantity == 0)

        count_stmt = select(func.count()).select_from(Product)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.reviews),
            )
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        # Map router-facing sort_by values to (column, direction) pairs.
        _SORT_MAP = {
            "price_asc": (Product.base_price, "asc"),
            "price_desc": (Product.base_price, "desc"),
            "name_asc": (Product.name, "asc"),
            "name_desc": (Product.name, "desc"),
            "newest": (Product.created_at, "desc"),
        }
        if sort_by in _SORT_MAP:
            sort_column, sort_order = _SORT_MAP[sort_by]
        elif sort_by and sort_by != "None":
            # Fallback: try direct column attribute lookup, default to created_at desc
            sort_column = getattr(Product, sort_by, Product.created_at)
        else:
            # Default: newest first
            sort_column = Product.created_at
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        products = result.scalars().all()

        total_pages = max(1, (total + page_size - 1) // page_size)

        return ProductList(
            items=[ProductRead.model_validate(p) for p in products],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_product(self, product_id: UUID) -> ProductRead:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.variants),
                selectinload(Product.reviews),
            )
        )
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if product is None:
            raise NotFoundError(f"Product with id '{product_id}' not found.")

        return ProductRead.model_validate(product)

    async def create_review(
        self,
        product_id: UUID,
        user_id: UUID,
        payload: ReviewCreate,
    ) -> ReviewRead:
        product_stmt = select(Product).where(Product.id == product_id)
        product_result = await self.db.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        if product is None:
            raise NotFoundError(f"Product with id '{product_id}' not found.")

        existing_stmt = select(Review).where(
            and_(Review.product_id == product_id, Review.user_id == user_id)
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_review = existing_result.scalar_one_or_none()

        if existing_review is not None:
            raise ConflictError("You have already reviewed this product.")

        review = Review(
            product_id=product_id,
            user_id=user_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        return ReviewRead.model_validate(review)

    async def get_product_reviews(
        self,
        product_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ReviewRead]:
        product_stmt = select(Product).where(Product.id == product_id)
        product_result = await self.db.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        if product is None:
            raise NotFoundError(f"Product with id '{product_id}' not found.")

        offset = (page - 1) * page_size
        stmt = (
            select(Review)
            .where(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reviews = result.scalars().all()

        return [ReviewRead.model_validate(r) for r in reviews]

    # Alias so router code using either name works.
    list_reviews = get_product_reviews