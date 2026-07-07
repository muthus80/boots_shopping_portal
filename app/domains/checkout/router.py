from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_stripe_client, optional_current_user
from app.domains.checkout.schemas import (
    ConfirmOrderRequest,
    ConfirmOrderResponse,
    OrderRead,
    PaymentIntentRequest,
    PaymentIntentResponse,
)
from app.domains.checkout.service import CheckoutService

router = APIRouter(prefix="/api/v1/checkout", tags=["checkout"])


@router.post(
    "/payment-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a Stripe PaymentIntent for the current cart (US-011)",
    description=(
        "Fetches cart total, creates a Stripe PaymentIntent server-side. "
        "Returns client_secret for Stripe Elements. No card data touches application servers. "
        "guest_email is required when not authenticated (ADR-003)."
    ),
)
async def create_payment_intent(
    payload: PaymentIntentRequest,
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> PaymentIntentResponse:
    """POST /api/v1/checkout/payment-intent — guest and authenticated checkout."""
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
    response_model=ConfirmOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm payment, create order, send confirmation email (US-011)",
    description=(
        "Verifies Stripe payment status, creates order record, clears cart, "
        "triggers order confirmation email. Handles both guest and authenticated checkout."
    ),
)
async def confirm_order(
    payload: ConfirmOrderRequest,
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> ConfirmOrderResponse:
    """POST /api/v1/checkout/confirm — creates the order after Stripe payment succeeds."""
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
    summary="List orders for the authenticated user",
)
async def list_orders(
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> list[OrderRead]:
    """GET /api/v1/checkout/orders — list orders for the authenticated user."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    service = CheckoutService(db=db, stripe_client=stripe_client)
    return await service.list_orders(user=current_user)


@router.get(
    "/orders/{order_id}",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
    summary="Get a specific order",
)
async def get_order(
    order_id: str,
    current_user=Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client=Depends(get_stripe_client),
) -> OrderRead:
    """GET /api/v1/checkout/orders/{order_id} — retrieve a single order."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    service = CheckoutService(db=db, stripe_client=stripe_client)
    order = await service.get_order(user=current_user, order_id=order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order
