from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.core.exceptions import (
    AppException,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    ValidationError,
    PaymentError,
    BadRequestError,
)
from app.domains.auth.router import router as auth_router
from app.domains.account.router import router as account_router
from app.domains.products.router import router as products_router
from app.domains.categories.router import router as categories_router
from app.domains.cart.router import router as cart_router
from app.domains.checkout.router import router as checkout_router

configure_logging()

logger = get_logger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Boots Shopping App",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    application.add_middleware(RequestIDMiddleware)

    # Exception handlers
    @application.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @application.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @application.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @application.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @application.exception_handler(PaymentError)
    async def payment_error_handler(request: Request, exc: PaymentError) -> JSONResponse:
        return JSONResponse(status_code=402, content={"detail": str(exc)})

    @application.exception_handler(BadRequestError)
    async def bad_request_handler(request: Request, exc: BadRequestError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # Health check endpoint — must be at root, unprefixed
    @application.get("/health", tags=["health"])
    async def health_check() -> dict:
        return {"status": "ok"}

    # Register domain routers (each router owns its own prefix)
    application.include_router(auth_router)
    application.include_router(account_router)
    application.include_router(products_router)
    application.include_router(categories_router)
    application.include_router(cart_router)
    application.include_router(checkout_router)

    logger.info("Application startup complete")

    return application


app: FastAPI = create_app()