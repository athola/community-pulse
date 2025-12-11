"""FastAPI application factory."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from community_pulse.api.routes import health, pulse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Community Pulse API",
        description="Detect emerging trends in online communities",
        version="0.1.0",
    )

    # CORS configuration: read from CORS_ORIGINS environment variable (comma-separated)
    # Defaults to localhost development ports if not set
    # Only use ["*"] if CORS_ORIGINS is explicitly set to "*"
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env == "*":
        allowed_origins = ["*"]
        allow_credentials = False  # Disable credentials for wildcard
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
