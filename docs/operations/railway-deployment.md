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

    package:           22206d20b84bf9ee73b93c64177443e1bb585ccdb818c188ac40d9acfcb358f9
    authorization:     3adb977f85c6896ef3228004bb4a60641ce51668688a9b57fa652136fd8ecfb9
    analytical source: f85e88a277ffb365e76dd6eeac6f5009c7bd0165

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
| Start command | celery -A app.workers.tasks.celery_app worker --loglevel=INFO --concurrency=4 |
| Healthcheck path | None |
| Public networking | None; do not generate a public domain |
| Restart policy | ALWAYS |

Use the same committed release source and Dockerfile for both services. The
worker's embedded package path is the same
/app/runtime-artifacts/free_dna_v61/6.1.0.

The image creates a system `app` user after build-time verification and runs
API and worker processes as that non-root user. The embedded package is made
non-writable before the user switch; application and migration inputs remain
readable.

## Shared API and worker variables

Set these values identically on API and worker unless marked API-only. Use
Railway sealed variables for secrets. The reference forms below assume the
services are named Postgres and Redis, as in the project description.

    APP_ENV=production
    LOG_LEVEL=INFO
    OPENDOTA_SOURCE=live
    OPENDOTA_BASE_URL=https://api.opendota.com/api
    OPENDOTA_API_KEY=<sealed OpenDota credential>
    STEAM_API_KEY=<sealed Steam credential or empty>
    STEAM_RESOLVER_BASE_URL=https://api.steampowered.com
    DATABASE_URL=${{Postgres.DATABASE_URL}}
    REDIS_URL=${{Redis.REDIS_URL}}
    STORAGE_BACKEND=database
    ANALYSIS_EXECUTION_BACKEND=celery
    ANALYSIS_MAX_CONCURRENCY=4
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
    FREE_DNA_V61_ANALYTICAL_SOURCE_SHA=f85e88a277ffb365e76dd6eeac6f5009c7bd0165

    RELEASE_COMMIT_SHA=<final committed Railway candidate SHA>
    RELEASE_WORKTREE_DIRTY=false
    REPORT_RETENTION_DAYS=30
    REPORT_INTERACTION_RETENTION_DAYS=90

RAILWAY_DOCKERFILE_PATH is not required when the Dockerfile path is set in the
service Build settings. Railway's injected PORT must not be copied into the
worker variables.

## Database, Redis, and rollout order

The PostgreSQL and Redis service references are:

    DATABASE_URL=${{Postgres.DATABASE_URL}}
    REDIS_URL=${{Redis.REDIS_URL}}

Apply the API pre-deploy migration, confirm the worker is running the same
release identity, and only then allow the API healthcheck to pass. Keep all
V6/V6.1 flags off. Do not attach a volume to either application service.

The migration chain preserves all historical revision IDs. The new
`0001_version_table_width` step widens `alembic_version.version_num` from the
Alembic default `VARCHAR(32)` to `VARCHAR(64)` before
`0002_persist_analysis_job_details`, so a clean bootstrap and a retry from a
partially completed `0001_initial` state both proceed automatically. The
current Alembic environment wraps the run in one PostgreSQL transaction, so a
failed pre-deploy normally rolls back the whole bootstrap; the bridge also
handles a database where `0001_initial` was already committed.

`ANALYSIS_MAX_CONCURRENCY=4` bounds in-process analysis work. It is separate
from Celery's process concurrency; the worker start command explicitly pins
Celery concurrency to 4.

## Release identity

RELEASE_COMMIT_SHA is the truthful SHA of the committed code/image source; it
is not the analytical SHA. FREE_DNA_V61_ANALYTICAL_SOURCE_SHA remains
f85e88a277ffb365e76dd6eeac6f5009c7bd0165.

## Validation commands

    .venv/bin/python scripts/verify_v61_runtime_package.py infra/runtime-artifacts/free_dna_v61/6.1.0
    .venv/bin/pytest -q tests/unit/test_railway_runtime_package.py

The full container build is required before deployment. It could not be run
in the current workspace because Docker/Podman is not installed.
