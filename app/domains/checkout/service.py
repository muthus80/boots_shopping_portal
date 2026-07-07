from __future__ import annotations

import random
import string
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
    PaymentError,
    ValidationError,
)
from app.domains.cart.models import Cart
from app.domains.checkout.models import Order, OrderItem
from app.domains.checkout.schemas import (
    ConfirmOrderRequest,
    ConfirmOrderResponse,
    OrderItemContractRead,
    OrderItemRead,
    OrderRead,
    PaymentIntentRequest,
    PaymentIntentResponse,
)
from app.domains.products.models import Product, ProductVariant


def _generate_order_number() -> str:
    """Generate a unique order number like ORD-A1B2C3D4."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"ORD-{suffix}"


class CheckoutService:
    def __init__(self, db: AsyncSession, stripe_client=None) -> None:
        self.db = db
        self._stripe = stripe_client or stripe
        self._stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_payment_intent(
        self,
        user,  # Optional[User] — None for guest
        request: PaymentIntentRequest,
    ) -> PaymentIntentResponse:
        """Create a Stripe PaymentIntent server-side for the cart total (ADR-003).

        Works for both authenticated users and guests (US-011).
        guest_email is required when user is None.
        """
        if user is None and not request.guest_email:
            raise BadRequestError("guest_email is required for guest checkout.")

        user_id = user.id if user is not None else None
        cart = await self._get_cart_with_items(user_id=user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        total_amount = self._calculate_total(cart)
        if total_amount <= Decimal("0"):
            raise ValidationError("Cart total must be greater than zero.")

        # Stripe amounts are in the smallest currency unit (pence for GBP)
        amount_in_pence = int(total_amount * 100)

        metadata: dict = {
            "cart_id": str(cart.id),
        }
        if user_id is not None:
            metadata["user_id"] = str(user_id)
        if request.guest_email:
            metadata["guest_email"] = request.guest_email
        if request.shipping_name:
            metadata["shipping_name"] = request.shipping_name

        try:
            intent = self._stripe.PaymentIntent.create(
                amount=amount_in_pence,
                currency="gbp",
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )
        except Exception as exc:
            raise PaymentError(f"Failed to create payment intent: {str(exc)}")

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            amount=amount_in_pence,
            currency="gbp",
        )

    async def confirm_order(
        self,
        user,  # Optional[User] — None for guest
        request: ConfirmOrderRequest,
    ) -> ConfirmOrderResponse:
        """Verify Stripe payment, create order, clear cart, return confirmation.

        Handles both guest and authenticated checkout (US-011).
        """
        user_id = user.id if user is not None else None
        cart = await self._get_cart_with_items(user_id=user_id)
        if not cart or not cart.items:
            raise BadRequestError("Cart is empty or does not exist.")

        # Retrieve and verify payment intent from Stripe (ADR-003)
        try:
            intent = self._stripe.PaymentIntent.retrieve(request.payment_intent_id)
        except Exception as exc:
            raise PaymentError(f"Failed to retrieve payment intent: {str(exc)}", 502)

        if intent.status != "succeeded":
            raise BadRequestError(
                f"Payment has not been completed. Current status: {intent.status}"
            )

        # Extract shipping address and guest_email from metadata (set during PI creation)
        metadata = intent.get("metadata", {}) if hasattr(intent, "get") else {}
        guest_email = metadata.get("guest_email") if user is None else None

        total_amount = self._calculate_total(cart)

        # Extract shipping address — use metadata or fall back to empty dict
        shipping_address: dict = {}
        for key in ("line1", "city", "state", "postal_code", "country"):
            val = metadata.get(f"shipping_{key}")
            if val:
                shipping_address[key] = val

        order_number = _generate_order_number()

        order = Order(
            id=uuid.uuid4(),
            order_number=order_number,
            user_id=user_id,
            guest_email=guest_email,
            status="confirmed",
            payment_status="paid",
            total_amount=total_amount,
            total=total_amount,
            subtotal=total_amount,
            shipping_cost=Decimal("0"),
            tax=Decimal("0"),
            shipping_address=shipping_address,
            stripe_payment_intent_id=request.payment_intent_id,
            currency=getattr(intent, "currency", "gbp"),
        )
        self.db.add(order)
        await self.db.flush()

        order_items: list[OrderItem] = []
        for cart_item in cart.items:
            # Resolve product and variant names for the order item
            product_name = await self._get_product_name(cart_item.product_id)
            color, size = await self._get_variant_attributes(cart_item.variant_id)

            line_total = Decimal(str(cart_item.unit_price)) * cart_item.quantity
            item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                product_id=cart_item.product_id,
                variant_id=cart_item.variant_id,
                product_name=product_name,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                line_total=line_total,
            )
            self.db.add(item)
            order_items.append(item)

        # Clear the cart items (cart stays, just emptied)
        for cart_item in list(cart.items):
            await self.db.delete(cart_item)

        await self.db.commit()
        await self.db.refresh(order)

        # Build the API-contract response
        items_read = [
            OrderItemContractRead(
                product_name=it.product_name,
                color=await self._get_variant_color(it.variant_id),
                size=await self._get_variant_size(it.variant_id),
                quantity=it.quantity,
                unit_price=it.unit_price,
            )
            for it in order_items
        ]

        return ConfirmOrderResponse(
            order_id=str(order.id),
            order_number=order.order_number or order_number,
            shipping_address=order.shipping_address or {},
            total_amount=total_amount,
            items=items_read,
        )

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

    async def _get_cart_with_items(
        self,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Cart]:
        if user_id is None:
            return None
        # Use execution_options populate_existing=True to bypass the identity
        # map cache and always load fresh data (important when the same session
        # is shared between test setup and the service layer).
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    def _calculate_total(self, cart: Cart) -> Decimal:
        total = Decimal("0")
        for item in cart.items:
            total += Decimal(str(item.unit_price)) * item.quantity
        return total

    async def _get_product_name(self, product_id: Optional[uuid.UUID]) -> str:
        if product_id is None:
            return "Unknown product"
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        return product.name if product else "Unknown product"

    async def _get_variant_attributes(
        self, variant_id: Optional[uuid.UUID]
    ) -> tuple[Optional[str], Optional[str]]:
        """Return (color, size) for a variant, or (None, None) if no variant."""
        if variant_id is None:
            return None, None
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant is None:
            return None, None
        return variant.color, variant.size

    async def _get_variant_color(self, variant_id: Optional[uuid.UUID]) -> Optional[str]:
        color, _ = await self._get_variant_attributes(variant_id)
        return color

    async def _get_variant_size(self, variant_id: Optional[uuid.UUID]) -> Optional[str]:
        _, size = await self._get_variant_attributes(variant_id)
        return size

    def _map_order_to_read(self, order: Order) -> OrderRead:
        items = [
            OrderItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=getattr(item, "product_name", "") or "",
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=Decimal(str(item.unit_price)) * item.quantity,
            )
            for item in (order.items or [])
        ]
        return OrderRead(
            id=order.id,
            user_id=order.user_id,
            status=str(order.status),
            total_amount=order.total_amount or Decimal("0"),
            shipping_address=getattr(order, "shipping_address", None),
            items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
