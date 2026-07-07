from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.account.schemas import (
    OrderHistoryResponse,
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
    """Return the authenticated user's profile."""
    return UserRead.model_validate(current_user)


@router.put("/profile", response_model=UserRead)
async def update_profile(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Update the authenticated user's profile."""
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the authenticated user's password."""
    service = AccountService(db)
    await service.change_password(current_user.id, payload)
    return {"message": "Password changed successfully."}


@router.get(
    "/orders",
    response_model=OrderHistoryResponse,
    summary="Get authenticated user order history",
    description=(
        "Returns a paginated list of past orders for the authenticated user. "
        "Returns empty list with message when no orders have been placed (US-003)."
    ),
)
async def get_order_history(
    page: int = Query(default=1, ge=1, description="Page number (default 1)"),
    per_page: int = Query(default=10, ge=1, le=100, description="Items per page (default 10)"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderHistoryResponse:
    """Return paginated order history for the authenticated user.

    - Requires: ``member`` role (authenticated user)
    - Returns: 200 with orders list, total count, and optional empty-state message
    - Returns: 401 when no valid JWT is provided
    """
    service = AccountService(db)
    return await service.get_order_history(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    """Return a single order by ID for the authenticated user."""
    service = AccountService(db)
    order = await service.get_order(current_user.id, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return OrderRead.model_validate(order)