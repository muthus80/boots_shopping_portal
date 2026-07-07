from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail if detail is not None else self.__class__.detail
        self.status_code = status_code if status_code is not None else self.__class__.status_code
        self.extra = extra or {}
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code!r}, "
            f"detail={self.detail!r})"
        )


class NotFoundError(AppException):
    """Raised when a requested resource cannot be found."""

    status_code: int = 404
    detail: str = "The requested resource was not found."

    def __init__(
        self,
        detail: str | None = None,
        resource: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if detail is None and resource is not None:
            detail = f"{resource} not found."
        super().__init__(detail=detail, extra=extra)


class UnauthorizedError(AppException):
    """Raised when authentication is required but missing or invalid."""

    status_code: int = 401
    detail: str = "Authentication credentials are missing or invalid."

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=detail, extra=extra)


class ForbiddenError(AppException):
    """Raised when the authenticated user lacks permission for the action."""

    status_code: int = 403
    detail: str = "You do not have permission to perform this action."

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=detail, extra=extra)


class ConflictError(AppException):
    """Raised when a resource conflict occurs (e.g. duplicate entry)."""

    status_code: int = 409
    detail: str = "A conflict occurred with the current state of the resource."

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=detail, extra=extra)


class ValidationError(AppException):
    """Raised when input data fails domain-level validation."""

    status_code: int = 422
    detail: str = "The provided data is invalid."

    def __init__(
        self,
        detail: str | None = None,
        errors: list[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        combined_extra = extra or {}
        if errors is not None:
            combined_extra["errors"] = errors
        super().__init__(detail=detail, extra=combined_extra)


class PaymentError(AppException):
    """Raised when a payment operation fails."""

    status_code: int = 402
    detail: str = "Payment processing failed."

    def __init__(
        self,
        detail: str | None = None,
        payment_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        combined_extra = extra or {}
        if payment_code is not None:
            combined_extra["payment_code"] = payment_code
        super().__init__(detail=detail, extra=combined_extra)


class BadRequestError(AppException):
    """Raised when the request is malformed or contains invalid parameters."""

    status_code: int = 400
    detail: str = "The request is invalid or malformed."

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=detail, extra=extra)