# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Put the venv on PATH so dagster is directly executable
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY twinship_harmonisation/ ./twinship_harmonisation/
COPY dagster_pipeline/ ./dagster_pipeline/
COPY shacl/ ./shacl/
COPY data/ ./data/
COPY argo/ ./argo/

# Expose Dagster gRPC port
EXPOSE 4000

# Default command runs Dagster gRPC server
CMD ["uv", "run", "dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", "-m", "dagster_pipeline"]
