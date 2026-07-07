from __future__ import annotations

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        bound_logger = logger.bind(request_id=request_id)
        bound_logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        request.state.request_id = request_id

        response: Response = await call_next(request)

        response.headers[REQUEST_ID_HEADER] = request_id

        bound_logger.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response