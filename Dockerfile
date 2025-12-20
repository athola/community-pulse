# Dockerfile - Multi-stage production build for Community Pulse
# Usage: docker build -t community-pulse .
#        docker run -p 8000:8000 community-pulse

# =============================================================================
# Stage 1: Build stage - install dependencies with uv
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev --no-editable

# Copy source code
COPY src/ ./src/

# =============================================================================
# Stage 2: Runtime stage - minimal production image
# =============================================================================
FROM python:3.12-slim AS runtime

# Security: Run as non-root user
RUN groupadd --gid 1000 pulse && \
    useradd --uid 1000 --gid pulse --shell /bin/bash --create-home pulse

WORKDIR /app

# Copy uv and virtual environment from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER pulse

# Expose API port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "community_pulse.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
