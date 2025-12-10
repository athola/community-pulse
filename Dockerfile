# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "community_pulse.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
