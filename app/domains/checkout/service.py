from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boots-shopping-app.app.core.config import settings
from boots-shopping-app.app.core.exceptions import (
    BadRequestError,
    NotFoundError,
    PaymentError,
    ValidationError,
)
from boots-shopping-app.app.domains.cart.models import Cart, CartItem
from boots-shopping-app.app.domains.checkout.models import Order, OrderItem
from boots-shopping-app.app.domains.checkout.schemas import (
    ConfirmOrderRequest,
    OrderItemRead,
    OrderRead,
    PaymentIntentRequest,
    PaymentIntentResponse,
)


class CheckoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_payment_intent(
        self,
        user_id: uuid.UUID,
        request: PaymentIntentRequest,
    ) -> PaymentIntentResponse:
        cart = await self._get_cart_with_items(user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        total_amount = self._calculate_total(cart)
        if total_amount <= Decimal("0"):
            raise ValidationError("Cart total must be greater than zero.")

        amount_in_cents = int(total_amount * 100)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=request.currency.lower(),
                metadata={
                    "user_id": str(user_id),
                    "cart_id": str(cart.id),
                },
                automatic_payment_methods={"enabled": True},
            )
        except stripe.error.StripeError as exc:
            raise PaymentError(f"Failed to create payment intent: {exc.user_message or str(exc)}")

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            amount=total_amount,
            currency=request.currency.lower(),
        )

    async def confirm_order(
        self,
        user_id: uuid.UUID,
        request: ConfirmOrderRequest,
    ) -> OrderRead:
        cart = await self._get_cart_with_items(user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        try:
            intent = stripe.PaymentIntent.retrieve(request.payment_intent_id)
        except stripe.error.StripeError as exc:
            raise PaymentError(f"Failed to retrieve payment intent: {exc.user_message or str(exc)}")

        if intent.status != "succeeded":
            raise PaymentError(
                f"Payment has not been completed. Current status: {intent.status}"
            )

        existing_order = await self._get_order_by_payment_intent(request.payment_intent_id)
        if existing_order:
            return self._map_order_to_read(existing_order)

        total_amount = self._calculate_total(cart)

        order = Order(
            id=uuid.uuid4(),
            user_id=user_id,
            payment_intent_id=request.payment_intent_id,
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

    async def get_order(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderRead:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.user_id == user_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError(f"Order {order_id} not found.")
        return self._map_order_to_read(order)

    async def list_orders(self, user_id: uuid.UUID) -> list[OrderRead]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
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

    async def _get_order_by_payment_intent(self, payment_intent_id: str) -> Optional[Order]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.payment_intent_id == payment_intent_id)
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
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in (order.items or [])
        ]
        return OrderRead(
            id=order.id,
            user_id=order.user_id,
            payment_intent_id=order.payment_intent_id,
            status=order.status,
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            currency=order.currency,
            items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )