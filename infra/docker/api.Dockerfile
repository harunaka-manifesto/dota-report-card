FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY services ./services
COPY migrations ./migrations
COPY scripts/verify_v61_runtime_package.py ./scripts/verify_v61_runtime_package.py
COPY infra/runtime-artifacts/free_dna_v61/6.1.0/ ./runtime-artifacts/free_dna_v61/6.1.0/
COPY alembic.ini ./
RUN pip install --no-cache-dir .
RUN python scripts/verify_v61_runtime_package.py /app/runtime-artifacts/free_dna_v61/6.1.0
RUN chmod -R a-w /app/runtime-artifacts/free_dna_v61/6.1.0
RUN addgroup --system app && adduser --system --ingroup app --no-create-home app

ENV PYTHONPATH=/app/services/api \
    FREE_DNA_V61_ARTIFACT_DIR=/app/runtime-artifacts/free_dna_v61/6.1.0 \
    FREE_DNA_V61_BASELINE_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/context-baseline-3.0.0.json \
    FREE_DNA_V61_THRESHOLD_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/metric-thresholds-6.1.0.json \
    FREE_DNA_V61_RELEASE_AUTHORIZATION=/app/runtime-artifacts/free_dna_v61/6.1.0/production-beta-authorization-6.1.0.json \
    FREE_DNA_V61_SUMMARY_PRIOR_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/summary-priors-6.1.0.json \
    FREE_DNA_V61_DISTANCE_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/portfolio-distance-calibration-1.0.0.json \
    FREE_DNA_V61_SESSION_RELIABILITY_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/session-reliability-calibration-1.0.0.json \
    FREE_DNA_V61_SEMANTIC_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/semantic-outcome-calibration-1.0.0.json \
    FREE_DNA_V61_BUILD_MANIFEST=/app/runtime-artifacts/free_dna_v61/6.1.0/build-manifest-6.1.0.json \
    FREE_DNA_V61_MODEL_VERSION=free-dna-model-6.1.0 \
    FREE_DNA_V61_ANALYTICAL_SOURCE_SHA=7df38e6d234ae9c4ee425490bc40b8cc92685f85
USER app
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
