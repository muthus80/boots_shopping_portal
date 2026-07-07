from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.domains.account.models import User
from app.domains.account.schemas import (
    OrderHistoryResponse,
    OrderItemRead,
    OrderRead,
    OrderSummaryRead,
    PasswordChange,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.domains.checkout.models import Order, OrderItem


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, payload: UserCreate) -> UserRead:
        existing = await self.db.execute(
            select(User).where(User.email == payload.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("A user with this email already exists.")

        hashed = hash_password(payload.password)
        user = User(
            email=payload.email,
            hashed_password=hashed,
            full_name=payload.full_name,
            is_active=True,
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return UserRead.model_validate(user)

    async def get_user_by_id(self, user_id: UUID) -> UserRead:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")
        return UserRead.model_validate(user)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update_profile(self, user_id: UUID, payload: UserUpdate) -> UserRead:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return UserRead.model_validate(user)

    async def change_password(self, user_id: UUID, payload: PasswordChange) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        if not verify_password(payload.current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect.")

        user.hashed_password = hash_password(payload.new_password)
        await self.db.commit()

    async def get_order_history(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 10,
    ) -> OrderHistoryResponse:
        """Return a paginated list of orders for an authenticated user (US-003).

        Returns an ``OrderHistoryResponse`` with:
        - ``orders``: list of ``OrderSummaryRead`` items for the requested page
        - ``total``: total number of orders across all pages
        - ``message``: human-readable string when the list is empty
        """
        # Total count query (no limit/offset)
        count_result = await self.db.execute(
            select(Order).where(Order.user_id == user_id)
        )
        all_orders = count_result.scalars().all()
        total = len(all_orders)

        # Paginated query
        offset = (page - 1) * per_page
        result = await self.db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        orders = result.scalars().all()

        summaries = [OrderSummaryRead.model_validate(o) for o in orders]

        message: Optional[str] = None
        if total == 0:
            message = "You have not placed any orders yet."

        return OrderHistoryResponse(orders=summaries, total=total, message=message)

    async def deactivate_account(self, user_id: UUID) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        user.is_active = False
        await self.db.commit()