from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.account.models import User, RefreshToken
from app.domains.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import (
    UnauthorizedError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.config import settings


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest) -> RegisterResponse:
        # Validate password complexity (min 8 chars)
        if len(payload.password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        result = await self.db.execute(select(User).where(User.email == payload.email))
        existing = result.scalars().first()
        if existing:
            raise ConflictError("A user with this email already exists.")

        hashed = hash_password(payload.password)
        user = User(
            email=payload.email,
            hashed_password=hashed,
            full_name=getattr(payload, "full_name", None),
            is_active=True,
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.flush()

        access_token = create_access_token(str(user.id))
        refresh_token_str, jti, expires_at = create_refresh_token(str(user.id))

        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            jti=jti,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(user)

        return RegisterResponse(
            user_id=str(user.id),
            email=user.email,
            message="Registration successful. Please check your email for confirmation.",
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == payload.email))
        user: Optional[User] = result.scalars().first()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError("Account is inactive.")

        access_token = create_access_token(str(user.id))
        refresh_token_str, jti, expires_at = create_refresh_token(str(user.id))

        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            jti=jti,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
        )

    async def logout(self, refresh_token_str: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        )
        token_record: Optional[RefreshToken] = result.scalars().first()

        if token_record and not token_record.is_revoked:
            token_record.is_revoked = True
            await self.db.commit()

    async def refresh_tokens(self, refresh_token_str: str) -> Optional[TokenResponse]:
        decoded = decode_token(refresh_token_str)
        if decoded is None:
            return None

        if decoded.get("type") != "refresh":
            return None

        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        )
        token_record: Optional[RefreshToken] = result.scalars().first()

        if not token_record:
            return None

        if token_record.is_revoked:
            return None

        now = datetime.now(timezone.utc)
        expires_at = token_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return None

        user_id = decoded.get("sub")
        if not user_id:
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError):
            return None

        result = await self.db.execute(select(User).where(User.id == user_uuid))
        user: Optional[User] = result.scalars().first()

        if not user:
            return None

        if not user.is_active:
            return None

        # Revoke old token (rotation)
        token_record.is_revoked = True

        new_access_token = create_access_token(str(user.id))
        new_refresh_token_str, new_jti, new_expires_at = create_refresh_token(str(user.id))

        new_refresh_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            jti=new_jti,
            expires_at=new_expires_at,
            is_revoked=False,
        )
        self.db.add(new_refresh_token)
        await self.db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            token_type="bearer",
        )
