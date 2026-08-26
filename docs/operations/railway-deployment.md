# Railway deployment contract

This is the deployment contract for the Railway API and worker services. It
does not deploy, enable V6.1, rerun holdout, recalibrate, or change analytical
behavior.

## Chosen artifact strategy

Use **A: bake the validated package into the API image**. The exact package is
checked into the versioned path below, copied into the image, verified during
the image build, and made non-writable:

    infra/runtime-artifacts/free_dna_v61/6.1.0
    /app/runtime-artifacts/free_dna_v61/6.1.0

The API and worker build the same infra/docker/api.Dockerfile, so both image
copies are derived from the same package. The Docker build fails unless the
package file set, all manifest-linked artifact bytes, authorization bytes, and
analytical source match the approved values:

    package:           8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0
    authorization:     9ddde890c25a47fcabf7a5e51f22ba3a3007f79dd5e5f9c52845a2bfe4e69b2a
    analytical source: 7df38e6d234ae9c4ee425490bc40b8cc92685f85

The package was inspected before committing it. It contains aggregate
calibration values, hashes, counts, and release metadata; it contains no
credentials, tokens, raw account/player identifiers, or raw match data. The
authorization file contains only release-gate metadata, checksums, and source
identity. It is therefore suitable for this public repository; the runtime
flags remain explicitly off.

## Option evaluation

| Option | Decision | Reason |
|---|---|---|
| A. Bake into image | **Chosen** | Immutable with the image, reproducible from GitHub, no runtime network dependency, and the API/worker use the same build path. |
| B. Release asset fetch | Rejected | Adds URL/asset availability and startup/build-fetch failure modes when the validated package can be safely versioned with this public source. |
| C. Railway volume | Rejected | Volumes are mutable, service-scoped, not mounted during build/pre-deploy, and would require separate API/worker population. |
| D. Prebuilt private image | Deferred | Strong isolation for restricted artifacts, but adds a registry and an external image-publish workflow that this inspected package does not require. |

## Railway API service

Configure the existing API service from the repository root.

| Setting | Exact value |
|---|---|
| Source | GitHub repository harunaka-manifesto/dota-report-card |
| Root directory | / |
| Dockerfile | infra/docker/api.Dockerfile |
| Build command | Leave unset; use the Dockerfile build |
| Pre-deploy command | alembic upgrade head |
| Start command | Leave unset; use the Dockerfile CMD |
| Effective start command | /bin/sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' |
| Healthcheck path | /health/ready |
| Public networking | Generate a public domain; do not set a fixed PORT (Railway injects it) |
| Restart policy | ALWAYS |

The API must be deployed after the worker is available because the production
lifespan requires worker reachability and exact release parity before serving.

## Railway worker service

Configure the existing worker service from the same repository, branch, root,
and Dockerfile.

| Setting | Exact value |
|---|---|
| Source | GitHub repository harunaka-manifesto/dota-report-card |
| Root directory | / |
| Dockerfile | infra/docker/api.Dockerfile |
| Build command | Leave unset; use the Dockerfile build |
| Pre-deploy command | Leave unset |
| Start command | celery -A app.workers.tasks.celery_app worker --loglevel=INFO |
| Healthcheck path | None |
| Public networking | None; do not generate a public domain |
| Restart policy | ALWAYS |

Use the same committed release source and Dockerfile for both services. The
worker's embedded package path is the same
/app/runtime-artifacts/free_dna_v61/6.1.0.

## Shared API and worker variables

Set these values identically on API and worker unless marked API-only. Use
Railway sealed variables for secrets. The reference forms below assume the
services are named PostgreSQL and Redis, as in the project description.

    APP_ENV=production
    LOG_LEVEL=INFO
    OPENDOTA_SOURCE=live
    OPENDOTA_BASE_URL=https://api.opendota.com/api
    OPENDOTA_API_KEY=<sealed OpenDota credential>
    STEAM_API_KEY=<sealed Steam credential or empty>
    STEAM_RESOLVER_BASE_URL=https://api.steampowered.com
    DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
    REDIS_URL=${{Redis.REDIS_URL}}
    STORAGE_BACKEND=database
    ANALYSIS_EXECUTION_BACKEND=celery
    CORS_ORIGINS=https://dota-report-card.vercel.app

    FREE_DNA_V6_ENABLED=false
    FREE_DNA_V61_ENABLED=false
    FREE_DNA_V61_SHADOW_ENABLED=false
    FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED=false
    FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED=false

    FREE_DNA_V61_ARTIFACT_DIR=/app/runtime-artifacts/free_dna_v61/6.1.0
    FREE_DNA_V61_BASELINE_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/context-baseline-3.0.0.json
    FREE_DNA_V61_THRESHOLD_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/metric-thresholds-6.1.0.json
    FREE_DNA_V61_RELEASE_AUTHORIZATION=/app/runtime-artifacts/free_dna_v61/6.1.0/production-beta-authorization-6.1.0.json
    FREE_DNA_V61_SUMMARY_PRIOR_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/summary-priors-6.1.0.json
    FREE_DNA_V61_DISTANCE_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/portfolio-distance-calibration-1.0.0.json
    FREE_DNA_V61_SESSION_RELIABILITY_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/session-reliability-calibration-1.0.0.json
    FREE_DNA_V61_SEMANTIC_ARTIFACT=/app/runtime-artifacts/free_dna_v61/6.1.0/semantic-outcome-calibration-1.0.0.json
    FREE_DNA_V61_BUILD_MANIFEST=/app/runtime-artifacts/free_dna_v61/6.1.0/build-manifest-6.1.0.json
    FREE_DNA_V61_MODEL_VERSION=free-dna-model-6.1.0
    FREE_DNA_V61_ANALYTICAL_SOURCE_SHA=7df38e6d234ae9c4ee425490bc40b8cc92685f85

    RELEASE_COMMIT_SHA=<final committed Railway candidate SHA>
    RELEASE_WORKTREE_DIRTY=false
    REPORT_RETENTION_DAYS=30
    REPORT_INTERACTION_RETENTION_DAYS=90

RAILWAY_DOCKERFILE_PATH is not required when the Dockerfile path is set in the
service Build settings. Railway's injected PORT must not be copied into the
worker variables.

## Database, Redis, and rollout order

The PostgreSQL and Redis service references are:

    DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
    REDIS_URL=${{Redis.REDIS_URL}}

Apply the API pre-deploy migration, confirm the worker is running the same
release identity, and only then allow the API healthcheck to pass. Keep all
V6/V6.1 flags off. Do not attach a volume to either application service.

## Release identity

RELEASE_COMMIT_SHA is the truthful SHA of the committed code/image source; it
is not the analytical SHA. FREE_DNA_V61_ANALYTICAL_SOURCE_SHA remains
7df38e6d234ae9c4ee425490bc40b8cc92685f85.

## Validation commands

    .venv/bin/python scripts/verify_v61_runtime_package.py infra/runtime-artifacts/free_dna_v61/6.1.0
    .venv/bin/pytest -q tests/unit/test_railway_runtime_package.py

The full container build is required before deployment. It could not be run
in the current workspace because Docker/Podman is not installed.
