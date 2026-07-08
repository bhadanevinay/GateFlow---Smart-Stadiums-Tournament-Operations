"""Custom middleware for security headers, request ID propagation, and rate limiting."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import RateLimitExceededError
from app.logging_conf import request_id_var

if TYPE_CHECKING:
    import logging

    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.types import ASGIApp

import logging

logger = logging.getLogger("gateflow")


class GateFlowSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware responsible for security headers, request IDs, and rate limiting."""

    def __init__(self, app: ASGIApp) -> None:
        """Initializes the security middleware.

        Args:
            app: ASGI application instance.

        """
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Processes request, applies rate limit, latency tracking, and security headers.

        Time Complexity: O(1) beyond downstream processing.
        Space Complexity: O(1).

        Args:
            request: The incoming FastAPI request.
            call_next: Callable to trigger the next request handler.

        Returns:
            The FastAPI Response.

        """
        # 1. Establish request ID context
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(req_id)

        start_time = time.time()
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path

        # 2. Apply rate limiting for API endpoints
        if path.startswith("/api/"):
            try:
                # rate_limiter is stored in app state
                rate_limiter = getattr(request.app.state, "rate_limiter", None)
                if rate_limiter is not None:
                    rate_limiter.check_rate_limit(client_ip)
            except RateLimitExceededError as e:
                logger.warning(
                    "Rate limit exceeded for IP %s on path %s", client_ip, path
                )
                response: Response = JSONResponse(
                    content={"detail": str(e)},
                    status_code=429,
                    headers={"Retry-After": "10"},
                )
                request_id_var.reset(token)
                return response

        # 3. Call downstream handlers
        try:
            response = await call_next(request)
        except Exception:  # pragma: no cover
            # Outer boundary exception catch to prevent internal stack leak
            logger.exception("Uncaught exception during request handling.")
            response = JSONResponse(
                content={"detail": "Internal server error"},
                status_code=500,
            )

        # 4. Record request telemetry (Privacy Safe: no question, no credentials)
        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            "Path: %s - Method: %s - Status: %d - Latency: %.2fms",
            path,
            request.method,
            response.status_code,
            latency_ms,
        )

        # 5. Inject response headers
        response.headers["X-Request-ID"] = req_id
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "script-src 'self' 'unsafe-inline';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"

        if request.url.scheme == "https":  # pragma: no cover
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        request_id_var.reset(token)
        return response
