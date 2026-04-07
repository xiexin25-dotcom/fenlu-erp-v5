FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./
COPY packages/shared/pyproject.toml packages/shared/pyproject.toml
COPY packages/product_lifecycle/pyproject.toml packages/product_lifecycle/pyproject.toml
COPY packages/production/pyproject.toml packages/production/pyproject.toml
COPY packages/supply_chain/pyproject.toml packages/supply_chain/pyproject.toml
COPY packages/management_decision/pyproject.toml packages/management_decision/pyproject.toml
COPY apps/api_gateway/pyproject.toml apps/api_gateway/pyproject.toml

RUN uv pip install --system --no-cache .

# Copy application code
COPY packages/ ./packages/
COPY apps/ ./apps/
COPY infra/ ./infra/

# Production image
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages and application
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Non-root user
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "apps.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
