from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.domains.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.domains.auth.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """
    Register a new user account.

    - Validates email uniqueness (409 if duplicate)
    - Validates password complexity (422 if weak)
    - Hashes password with bcrypt
    - Persists user record
    - Returns user_id, email, and confirmation message
    """
    result = await service.register(payload)
    return result


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT tokens",
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate user with email/password and issue JWT access + refresh tokens.

    - 200: tokens issued
    - 401: invalid credentials
    """
    result = await service.login(payload)
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Issue new access token from valid refresh token",
)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Validate refresh token and issue a new access token (with rotation).

    - 200: new access token issued
    - 401: refresh token invalid or expired
    """
    result = await service.refresh_tokens(payload.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token and invalidate session",
)
async def logout(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    current_user=Depends(get_current_user),
) -> dict:
    """
    Revoke refresh token and end the session.

    - 200: logged out successfully
    - 401: not authenticated
    """
    await service.logout(payload.refresh_token)
    return {"message": "Logged out successfully"}
