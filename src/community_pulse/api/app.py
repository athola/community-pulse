"""FastAPI application factory."""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from community_pulse.api.routes import health, pulse

logger = logging.getLogger(__name__)

# Rate limiter shared across the application
limiter = Limiter(key_func=get_remote_address)


def _rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle rate limit exceeded errors with informative response."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Community Pulse API",
        description="Detect emerging trends in online communities",
        version="0.1.0",
    )

    # Configure rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )

    # CORS configuration: read from CORS_ORIGINS environment variable (comma-separated)
    # Defaults to localhost development ports if not set
    # SECURITY: Wildcard CORS is blocked in production environments
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    environment = os.getenv("ENVIRONMENT", "development")

    if cors_origins_env == "*":
        if environment == "production":
            msg = (
                "CORS_ORIGINS='*' is not allowed in production. "
                "Set explicit allowed origins (comma-separated)."
            )
            logger.error(msg)
            raise ValueError(msg)
        # Allow wildcard only in development with credentials disabled
        logger.warning("CORS wildcard enabled - development mode only")
        allowed_origins = ["*"]
        allow_credentials = False
    elif cors_origins_env:
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
        allow_credentials = True
    else:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8081",
            "http://localhost:19006",
        ]
        allow_credentials = True

    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]  # starlette typing issue
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(pulse.router)

    return app


# For uvicorn
app = create_app()
