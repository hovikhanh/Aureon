# Aureon API / Celery image (07 §8.1). Build context = repo root.
# Secrets are never baked in: config comes from env (compose `env_file`), keys from ./keys:ro
# (R-DEC-81).
FROM ghcr.io/astral-sh/uv:0.12.11 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app

# Build arg: which uv extra to install. Default `ocr` (R-DEC-146) bakes the real PaddleOCR
# engine for IDP image/scan capture; build with `--build-arg UV_EXTRAS=none` for a lean image.
ARG UV_EXTRAS=ocr

# System libraries PaddleOCR / paddlepaddle need at runtime (OpenMP, OpenGL, glib). Harmless
# when OCR is not installed; kept in a single cached layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer (cached until lockfile changes). `--extra <x>` is passed only when
# UV_EXTRAS is a real extra name (not the sentinel `none`).
COPY --chmod=a+r pyproject.toml uv.lock ./
COPY --chmod=a+r apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p apps/api/src/app && touch apps/api/src/app/__init__.py \
    && EXTRA="$([ \"$UV_EXTRAS\" != none ] && echo --extra $UV_EXTRAS)" \
    && uv sync --frozen --no-dev --no-install-workspace $EXTRA

# Runtime user, created before the model bake so the PaddleOCR cache lands in its HOME.
RUN useradd --create-home --uid 1000 aureon

# Bake the PaddleOCR detection/recognition/angle models into the image (R-DEC-146) so OCR runs
# fully offline at runtime — no download from bcebos.com on the first scanned document.
# This layer depends only on the dependency layer above, NOT on the application source: it sits
# before `COPY apps/api` so a code change reuses the cached models instead of re-downloading
# them (M4-SYNC-AUDIT X-4). It FAILS the build when the `ocr` extra is installed but the models
# are not all on disk — a silently model-less image used to build "green" and only break at the
# first scanned document. `UV_EXTRAS=none` skips the bake on purpose (lean image, OCR stub).
USER aureon
RUN set -eu; \
    if [ "$UV_EXTRAS" = none ]; then echo "UV_EXTRAS=none: OCR models not baked"; exit 0; fi; \
    if ! python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('paddleocr') else 1)"; then \
      echo "UV_EXTRAS=$UV_EXTRAS but paddleocr is not installed" >&2; exit 1; \
    fi; \
    python -c "import warnings; warnings.filterwarnings('ignore'); from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='vi', show_log=False)"; \
    for kind in det rec cls; do \
      for f in inference.pdmodel inference.pdiparams; do \
        hit=$(find "/home/aureon/.paddleocr/whl/$kind" -name "$f" -size +0 2>/dev/null | head -n 1); \
        [ -n "$hit" ] || { echo "OCR model bake incomplete: no $kind/$f" >&2; exit 1; }; \
        echo "baked: $hit"; \
      done; \
    done
USER root

COPY --chmod=a+rX apps/api apps/api
COPY --chmod=a+r alembic.ini ./
RUN EXTRA="$([ \"$UV_EXTRAS\" != none ] && echo --extra $UV_EXTRAS)" \
    && uv sync --frozen --no-dev $EXTRA

RUN mkdir -p /app/var/idp-storage && chown -R aureon:aureon /app/var
USER aureon

EXPOSE 4000
