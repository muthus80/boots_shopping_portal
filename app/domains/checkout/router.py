from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_stripe_client
from app.domains.checkout.schemas import (
    ConfirmOrderRequest,
    OrderRead,
    PaymentIntentRequest,
    PaymentIntentResponse,
)
from app.domains.checkout.service import CheckoutService

router = APIRouter(prefix="/api/v1/checkout", tags=["checkout"])


@router.post(
    "/payment-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_intent(
    payload: PaymentIntentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> PaymentIntentResponse:
    service = CheckoutService(db=db, stripe_client=stripe_client)
    try:
        return await service.create_payment_intent(
            user=current_user,
            request=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/confirm",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_order(
    payload: ConfirmOrderRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> OrderRead:
    service = CheckoutService(db=db, stripe_client=stripe_client)
    try:
        return await service.confirm_order(
            user=current_user,
            request=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/orders",
    response_model=list[OrderRead],
    status_code=status.HTTP_200_OK,
)
async def list_orders(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> list[OrderRead]:
    service = CheckoutService(db=db, stripe_client=stripe_client)
    return await service.list_orders(user=current_user)


@router.get(
    "/orders/{order_id}",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
)
async def get_order(
    order_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> OrderRead:
    service = CheckoutService(db=db, stripe_client=stripe_client)
    order = await service.get_order(user=current_user, order_id=order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order