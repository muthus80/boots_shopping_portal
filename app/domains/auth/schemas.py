from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str | None = None


class RegisterResponse(BaseModel):
    """Response schema for POST /api/v1/auth/register (US-001).

    Returns user info plus JWT tokens so the user is automatically
    authenticated after account creation (no separate login required).
    """

    user_id: str
    email: str
    message: str = "Registration successful. Please check your email for confirmation."
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds


class RefreshRequest(BaseModel):
    refresh_token: str
