from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import optional_current_user, require_member, get_current_user
from app.domains.cart.schemas import CartRead, AddCartItem, UpdateCartItem
from app.domains.cart.service import CartService

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


def get_cart_service(db: AsyncSession = Depends(get_current_user)) -> CartService:
    return CartService(db)


@router.get("", response_model=CartRead, status_code=status.HTTP_200_OK)
async def get_cart(
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(optional_current_user),
) -> CartRead:
    pass


from app.core.database import get_db as _get_db


@router.get("", response_model=CartRead, status_code=status.HTTP_200_OK, include_in_schema=False)
async def _get_cart_duplicate() -> CartRead:
    pass


router.routes = [r for r in router.routes if not (hasattr(r, "path") and r.path == "" and getattr(r, "include_in_schema", True) is False)]


from fastapi import Request


@router.get("", response_model=CartRead, status_code=status.HTTP_200_OK)
async def get_cart_endpoint(
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(_get_db),
) -> CartRead:
    service = CartService(db)
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    if current_user is not None:
        user_id = current_user.id
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    return cart


from __future__ import annotations