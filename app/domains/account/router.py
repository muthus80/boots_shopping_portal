from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_member
from app.domains.account.schemas import (
    OrderRead,
    PasswordChange,
    UserRead,
    UserUpdate,
)
from app.domains.account.service import AccountService

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/profile", response_model=UserRead)
async def get_profile(
    current_user=Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/profile", response_model=UserRead)
async def update_profile(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(require_member),
) -> UserRead:
    service = AccountService(db)
    updated = await service.update_profile(current_user.id, payload)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserRead.model_validate(updated)


@router.post("/profile/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: PasswordChange,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(require_member),
) -> dict:
    service = AccountService(db)
    await service.change_password(current_user.id, payload)
    return {"message": "Password changed successfully."}


@router.get("/orders", response_model=List[OrderRead])
async def get_order_history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(require_member),
) -> List[OrderRead]:
    service = AccountService(db)
    orders = await service.get_order_history(current_user.id)
    return [OrderRead.model_validate(order) for order in orders]


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(require_member),
) -> OrderRead:
    service = AccountService(db)
    order = await service.get_order(current_user.id, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return OrderRead.model_validate(order)