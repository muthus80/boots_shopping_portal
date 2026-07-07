from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import optional_current_user
from app.core.database import get_db
from app.domains.cart.schemas import AddCartItem, CartRead
from app.domains.cart.service import CartService

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


@router.get("", response_model=CartRead, status_code=status.HTTP_200_OK)
async def get_cart(
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartRead:
    """Retrieve the current user's or guest's cart. Creates an empty cart if none exists."""
    service = CartService(db)
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    if current_user is not None:
        user_id = current_user.id
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    return cart


@router.post(
    "/items",
    response_model=CartRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to cart (US-009)",
    description=(
        "Add a product variant to the current user's or guest's cart. "
        "If no cart exists one is created automatically. "
        "For authenticated users the cart is tied to their account; "
        "for guests it is tied to the X-Session-ID header value."
    ),
)
async def add_cart_item(
    payload: AddCartItem,
    request: Request,
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartRead:
    """Add a product (optionally specifying a variant) to the cart (US-009).

    - Authenticated users: cart is identified by user_id.
    - Guest users: cart is identified by the ``X-Session-ID`` request header.
    """
    service = CartService(db)
    user_id: Optional[UUID] = current_user.id if current_user is not None else None
    session_id: Optional[str] = (
        request.headers.get("X-Session-ID") if user_id is None else None
    )
    cart = await service.add_item_to_cart(
        payload=payload,
        user_id=user_id,
        session_id=session_id,
    )
    return cart
