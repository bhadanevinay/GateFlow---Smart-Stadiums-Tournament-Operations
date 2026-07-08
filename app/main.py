"""FastAPI application factory, middleware configuration, and lifespan setup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_assist import router as assist_router
from app.api.routes_health import router as health_router
from app.api.routes_transport import router as transport_router
from app.api.routes_venue import router as venue_router
from app.config import settings
from app.exceptions import GateFlowError, RateLimitExceededError, RouteNotFoundError
from app.logging_conf import setup_logging
from app.middleware import GateFlowSecurityMiddleware
from app.services.llm_client import get_llm_client
from app.services.security import RateLimiter

# 1. Initialize logging configuration
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup and shutdown lifecycle events.

    Args:
        app: The FastAPI application instance.

    """
    # Initialize shared clients/services in app state
    app.state.llm_client = get_llm_client(settings)
    app.state.rate_limiter = RateLimiter(settings)
    yield
    # Shutdown / cleanup (none required for in-memory / redis standard connections)


# 2. Create FastAPI instance
app = FastAPI(
    title="GateFlow",
    description="Real-Time Crowd Flow & Transportation Copilot for FIFA World Cup 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# 3. CORS configuration (defaulting to explicit allowed origins from settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-Request-ID", "Content-Type", "Accept"],
)

# 4. Add custom security headers and rate-limiting middleware
app.add_middleware(GateFlowSecurityMiddleware)

# 5. Register API Routers
# (API routers imported at top level to satisfy E402)

app.include_router(health_router, tags=["Health"])
app.include_router(assist_router, prefix="/api", tags=["Assistant"])
app.include_router(transport_router, prefix="/api", tags=["Transportation"])
app.include_router(venue_router, prefix="/api", tags=["Venue"])


# 6. Global Exception Handlers
@app.exception_handler(GateFlowError)
async def gateflow_error_handler(
    _request: Request,
    exc: GateFlowError,
) -> JSONResponse:
    """Handles domain-specific GateFlow errors by returning a 400 Bad Request.

    Args:
        request: FastAPI request.
        exc: Exception instance.

    Returns:
        JSONResponse with a 400 status.

    """
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RouteNotFoundError)
async def route_not_found_handler(
    _request: Request,
    exc: RouteNotFoundError,
) -> JSONResponse:
    """Handles routing path resolution failures with a 404 Not Found.

    Args:
        request: FastAPI request.
        exc: Exception instance.

    Returns:
        JSONResponse with a 404 status.

    """
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(
    _request: Request,
    exc: RateLimitExceededError,
) -> JSONResponse:  # pragma: no cover
    """Handles rate limit breaches with a 429 Too Many Requests response.

    Args:
        request: FastAPI request.
        exc: Exception instance.

    Returns:
        JSONResponse with a 429 status and Retry-After header.

    """
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": "10"},
    )


# 7. Serve Static Frontend files
# (pathlib imported at top level to satisfy E402)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():  # pragma: no cover
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False, response_model=None)
async def read_root() -> FileResponse | JSONResponse:
    """Serves the main single-page application dashboard.

    Returns:
        FileResponse serving index.html if exists, otherwise 404.

    """
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend assets not found."},
    )
