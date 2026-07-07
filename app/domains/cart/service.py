from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.cart.models import Cart, CartItem
from app.domains.cart.schemas import AddCartItem, UpdateCartItem
from app.domains.products.models import ProductVariant
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError


class CartService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_cart(
        self,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self._find_cart(user_id=user_id, session_id=session_id)
        if cart is None:
            cart = Cart(user_id=user_id, session_id=session_id)
            self.db.add(cart)
            await self.db.flush()
            await self.db.refresh(cart)
        return cart

    async def get_cart(
        self,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self._find_cart(user_id=user_id, session_id=session_id)
        if cart is None:
            raise NotFoundError("Cart not found")
        return cart

    async def get_cart_by_id(self, cart_id: UUID) -> Cart:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.variant))
            .where(Cart.id == cart_id)
        )
        cart = result.scalar_one_or_none()
        if cart is None:
            raise NotFoundError("Cart not found")
        return cart

    async def add_item(
        self,
        cart_id: UUID,
        payload: AddCartItem,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self.get_cart_by_id(cart_id)
        await self._assert_cart_access(cart, user_id=user_id, session_id=session_id)

        if payload.variant_id is not None:
            variant = await self._get_variant(payload.variant_id)
            if variant.stock_quantity < payload.quantity:
                raise BadRequestError(
                    f"Insufficient stock. Available: {variant.stock_quantity}"
                )
            existing_item = await self._find_cart_item(cart_id, payload.variant_id)
            if existing_item is not None:
                new_qty = existing_item.quantity + payload.quantity
                if variant.stock_quantity < new_qty:
                    raise BadRequestError(
                        f"Insufficient stock. Available: {variant.stock_quantity}"
                    )
                existing_item.quantity = new_qty
            else:
                unit_price = float(
                    (variant.price_modifier or 0)
                    + (await self._get_product_price(payload.product_id))
                )
                item = CartItem(
                    cart_id=cart_id,
                    product_id=payload.product_id,
                    variant_id=payload.variant_id,
                    quantity=payload.quantity,
                    unit_price=unit_price,
                )
                self.db.add(item)
        else:
            # No variant — add product directly
            unit_price = await self._get_product_price(payload.product_id)
            existing_item = await self._find_cart_item_by_product(cart_id, payload.product_id)
            if existing_item is not None:
                existing_item.quantity += payload.quantity
            else:
                item = CartItem(
                    cart_id=cart_id,
                    product_id=payload.product_id,
                    quantity=payload.quantity,
                    unit_price=unit_price,
                )
                self.db.add(item)

        await self.db.flush()
        # Expire all cached ORM objects so get_cart_by_id re-fetches the
        # items collection from the database (avoids stale identity-map).
        self.db.expire_all()
        return await self.get_cart_by_id(cart_id)

    async def add_item_to_cart(
        self,
        payload: AddCartItem,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        """Get-or-create the user's/guest's cart, then add the item to it (US-009)."""
        cart = await self.get_or_create_cart(user_id=user_id, session_id=session_id)
        return await self.add_item(
            cart_id=cart.id,
            payload=payload,
            user_id=user_id,
            session_id=session_id,
        )

    async def update_item(
        self,
        cart_id: UUID,
        item_id: UUID,
        payload: UpdateCartItem,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self.get_cart_by_id(cart_id)
        await self._assert_cart_access(cart, user_id=user_id, session_id=session_id)

        item = await self._get_cart_item(item_id, cart_id)
        variant = await self._get_variant(item.variant_id)

        if payload.quantity <= 0:
            await self.db.delete(item)
        else:
            if variant.stock_quantity < payload.quantity:
                raise BadRequestError(
                    f"Insufficient stock. Available: {variant.stock_quantity}"
                )
            item.quantity = payload.quantity

        await self.db.flush()
        return await self.get_cart_by_id(cart_id)

    async def remove_item(
        self,
        cart_id: UUID,
        item_id: UUID,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self.get_cart_by_id(cart_id)
        await self._assert_cart_access(cart, user_id=user_id, session_id=session_id)

        item = await self._get_cart_item(item_id, cart_id)
        await self.db.delete(item)
        await self.db.flush()
        return await self.get_cart_by_id(cart_id)

    async def clear_cart(
        self,
        cart_id: UUID,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        cart = await self.get_cart_by_id(cart_id)
        await self._assert_cart_access(cart, user_id=user_id, session_id=session_id)

        await self.db.execute(
            delete(CartItem).where(CartItem.cart_id == cart_id)
        )
        await self.db.flush()
        return await self.get_cart_by_id(cart_id)

    async def merge_guest_cart_into_user_cart(
        self,
        user_id: UUID,
        session_id: str,
    ) -> Cart:
        guest_cart = await self._find_cart(session_id=session_id)
        if guest_cart is None:
            return await self.get_or_create_cart(user_id=user_id)

        user_cart = await self._find_cart(user_id=user_id)
        if user_cart is None:
            guest_cart.user_id = user_id
            guest_cart.session_id = None
            await self.db.flush()
            return await self.get_cart_by_id(guest_cart.id)

        guest_items_result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == guest_cart.id)
        )
        guest_items = guest_items_result.scalars().all()

        for guest_item in guest_items:
            variant = await self._get_variant(guest_item.variant_id)
            existing = await self._find_cart_item(user_cart.id, guest_item.variant_id)
            if existing is not None:
                new_qty = existing.quantity + guest_item.quantity
                capped_qty = min(new_qty, variant.stock_quantity)
                existing.quantity = capped_qty
            else:
                merged_item = CartItem(
                    cart_id=user_cart.id,
                    variant_id=guest_item.variant_id,
                    quantity=min(guest_item.quantity, variant.stock_quantity),
                    unit_price=guest_item.unit_price,
                )
                self.db.add(merged_item)

        await self.db.execute(
            delete(CartItem).where(CartItem.cart_id == guest_cart.id)
        )
        await self.db.delete(guest_cart)
        await self.db.flush()
        return await self.get_cart_by_id(user_cart.id)

    async def _find_cart(
        self,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Cart]:
        if user_id is not None:
            result = await self.db.execute(
                select(Cart)
                .options(selectinload(Cart.items).selectinload(CartItem.variant))
                .where(Cart.user_id == user_id)
            )
            return result.scalar_one_or_none()
        if session_id is not None:
            result = await self.db.execute(
                select(Cart)
                .options(selectinload(Cart.items).selectinload(CartItem.variant))
                .where(Cart.session_id == session_id)
            )
            return result.scalar_one_or_none()
        return None

    async def _get_product_price(self, product_id: UUID) -> float:
        from app.domains.products.models import Product
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundError("Product not found")
        return float(product.base_price)

    async def _find_cart_item_by_product(
        self, cart_id: UUID, product_id: UUID
    ) -> Optional[CartItem]:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id,
                CartItem.variant_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _find_cart_item(
        self, cart_id: UUID, variant_id: UUID
    ) -> Optional[CartItem]:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.variant_id == variant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_cart_item(self, item_id: UUID, cart_id: UUID) -> CartItem:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.id == item_id,
                CartItem.cart_id == cart_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("Cart item not found")
        return item

    async def _get_variant(self, variant_id: UUID) -> ProductVariant:
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant is None:
            raise NotFoundError("Product variant not found")
        return variant

    async def _assert_cart_access(
        self,
        cart: Cart,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> None:
        if user_id is not None and cart.user_id == user_id:
            return
        if session_id is not None and cart.session_id == session_id:
            return
        if user_id is None and session_id is None:
            return
        raise ForbiddenError("Access to this cart is not allowed")