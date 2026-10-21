# Aureon API / Celery image (07 §8.1). Build context = repo root.
# Secrets are never baked in: config comes from env (compose `env_file`), keys from ./secrets:ro.
FROM ghcr.io/astral-sh/uv:0.12.11 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app

# Dependency layer (cached until lockfile changes).
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p apps/api/src/app && touch apps/api/src/app/__init__.py \
    && uv sync --frozen --no-dev --no-install-workspace

COPY --chmod=a+rX apps/api apps/api
COPY --chmod=a+r alembic.ini ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 aureon
USER aureon
