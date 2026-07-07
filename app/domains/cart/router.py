from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import optional_current_user
from app.core.database import get_db
from app.domains.cart.schemas import CartRead
from app.domains.cart.service import CartService

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


@router.get("", response_model=CartRead, status_code=status.HTTP_200_OK)
async def get_cart(
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartRead:
    service = CartService(db)
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    if current_user is not None:
        user_id = current_user.id
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    return cart
