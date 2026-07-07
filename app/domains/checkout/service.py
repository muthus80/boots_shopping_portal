from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    NotFoundError,
    PaymentError,
    ValidationError,
)
from app.domains.cart.models import Cart, CartItem
from app.domains.checkout.models import Order, OrderItem
from app.domains.checkout.schemas import (
    ConfirmOrderRequest,
    OrderItemRead,
    OrderRead,
    PaymentIntentRequest,
    PaymentIntentResponse,
)


class CheckoutService:
    def __init__(self, db: AsyncSession, stripe_client=None) -> None:
        self.db = db
        self._stripe = stripe_client or stripe
        self._stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_payment_intent(
        self,
        user,
        request: PaymentIntentRequest,
    ) -> PaymentIntentResponse:
        user_id = user.id
        cart = await self._get_cart_with_items(user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        total_amount = self._calculate_total(cart)
        if total_amount <= Decimal("0"):
            raise ValidationError("Cart total must be greater than zero.")

        amount_in_cents = int(total_amount * 100)

        try:
            intent = self._stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency="gbp",
                metadata={
                    "user_id": str(user_id),
                    "cart_id": str(cart.id),
                },
                automatic_payment_methods={"enabled": True},
            )
        except Exception as exc:
            raise PaymentError(f"Failed to create payment intent: {str(exc)}")

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            amount=total_amount,
            currency="gbp",
        )

    async def confirm_order(
        self,
        user,
        request: ConfirmOrderRequest,
    ) -> OrderRead:
        user_id = user.id
        cart = await self._get_cart_with_items(user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        try:
            intent = self._stripe.PaymentIntent.retrieve(request.payment_intent_id)
        except Exception as exc:
            raise PaymentError(f"Failed to retrieve payment intent: {str(exc)}")

        if intent.status != "succeeded":
            raise PaymentError(
                f"Payment has not been completed. Current status: {intent.status}"
            )

        total_amount = self._calculate_total(cart)

        order = Order(
            id=uuid.uuid4(),
            user_id=user_id,
            status="confirmed",
            total_amount=total_amount,
            shipping_address=request.shipping_address,
            currency=intent.currency,
        )
        self.db.add(order)
        await self.db.flush()

        order_items: list[OrderItem] = []
        for cart_item in cart.items:
            item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                subtotal=cart_item.unit_price * cart_item.quantity,
            )
            self.db.add(item)
            order_items.append(item)

        for cart_item in list(cart.items):
            await self.db.delete(cart_item)

        await self.db.commit()
        await self.db.refresh(order)

        order.items = order_items
        return self._map_order_to_read(order)

    async def get_order(self, user, order_id: str) -> Optional[OrderRead]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.user_id == user.id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return None
        return self._map_order_to_read(order)

    async def list_orders(self, user) -> list[OrderRead]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        return [self._map_order_to_read(order) for order in orders]

    async def _get_cart_with_items(self, user_id: uuid.UUID) -> Optional[Cart]:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _calculate_total(self, cart: Cart) -> Decimal:
        total = Decimal("0")
        for item in cart.items:
            total += Decimal(str(item.unit_price)) * item.quantity
        return total

    def _map_order_to_read(self, order: Order) -> OrderRead:
        items = [
            OrderItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=getattr(item, "product_name", ""),
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=getattr(item, "subtotal", item.unit_price * item.quantity),
            )
            for item in (order.items or [])
        ]
        return OrderRead(
            id=order.id,
            user_id=order.user_id,
            status=str(order.status),
            total_amount=order.total_amount or Decimal("0"),
            shipping_address=getattr(order, "shipping_address", "") or "",
            items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
