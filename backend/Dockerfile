# Build from the repository root: docker build -f backend/Dockerfile .
ARG BASE_IMAGE=python:3.13-slim-bookworm
FROM ${BASE_IMAGE} AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements-models.txt backend/requirements-runtime.lock /app/backend/
RUN pip install --no-cache-dir -c backend/requirements-runtime.lock -r backend/requirements.txt -r backend/requirements-models.txt
COPY backend/app /app/backend/app
COPY backend/run.py backend/gunicorn_config.py /app/backend/
COPY clean_product /app/clean_product
COPY configs/product.yaml configs/active_baseline_descriptor.yaml configs/tw_modular_registry.yaml configs/tw_product_artifact_registry.yaml configs/tw_replay_window_policy.yaml /app/configs/
# Market data and frozen assets are mounted read-only at their configured paths.
# Live Qlib scoring additionally needs the audited Taiwan Qlib wheel; see backend/README.md.
WORKDIR /app/backend
EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn_config.py", "run:app"]

# Optional target: a named context containing ONLY the audited wheel and manifest.
FROM base AS frozen-models
ARG QLIB_WHEEL_SHA256
RUN --mount=type=bind,from=qlib-wheel,source=.,target=/wheels \
    python -c "import hashlib, pathlib, sys; p=list(pathlib.Path('/wheels').glob('*.whl')); assert len(p)==1 and len(sys.argv[1])==64 and hashlib.sha256(p[0].read_bytes()).hexdigest()==sys.argv[1]" "${QLIB_WHEEL_SHA256}" \
    && pip install --no-cache-dir -c /app/backend/requirements-runtime.lock /wheels/*.whl \
    && pip check \
    && python -c "from qlib.constant import REG_TW; assert REG_TW == 'tw'"

# Default image does not claim to support live Qlib inference.
FROM base AS runtime
