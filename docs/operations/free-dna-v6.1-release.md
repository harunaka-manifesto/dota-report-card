# Free DNA V6.1 release and rollback runbook

V6.1 is disabled by default. Fixture artifacts and synthetic evaluation never
authorize deployment or public traffic.

The current repository is not production-ready for V6.1: the checked-in
calibration evidence predates the mandatory `leaver_status` boundary and the
runtime-parity artifact contract. Regenerate the frozen evidence and release
authorization from a clean release commit before enabling traffic.

## Flags

Set the same values on API and worker:

```text
FREE_DNA_V61_ENABLED=false
FREE_DNA_V61_SHADOW_ENABLED=false
FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED=false
FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED=false
```

The public enable flag is mutually exclusive with `FREE_DNA_V6_ENABLED`.
Enabling V6.1 without both validated artifacts is a startup/runtime error. The
baseline must be `context-baseline-3.0.0`; thresholds must be
`metric-thresholds-6.1.0`. Fixture files under `tests/fixtures/v6` must never be
mounted into a production image.

Production also requires `APP_ENV=production`, database-backed storage,
Celery/Redis execution, `RELEASE_COMMIT_SHA=<release commit>`, and
`RELEASE_WORKTREE_DIRTY=false`. The API and worker must receive the same values.

## Migration and readiness

Migrations run before either production process starts. With Compose:

```bash
docker compose -f infra/compose.yaml run --rm migrate
docker compose -f infra/compose.yaml up -d
curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
```

`/health/live` only proves the process is alive. `/health/ready` must report
the database at Alembic revision `0005_v6_interactions_deep`, Redis and the
worker reachable, the complete V6.1 artifact bundle loaded, and production
authorization ready. A failed readiness check must keep the deployment out of
service.

## Canonical history and runtime parity

Free V6.1 uses one physical summary-history request, the shared canonical
projection/normalizer, and the versioned cache key
`/players/{account_id}/matches/v61-canonical`. Retries are disabled for this
request (`retry_limit=0`). Missing or invalid `leaver_status` is ineligible;
there is no default-to-zero production path. The provider ceiling is 10,000:
fewer than 10,000 rows can be complete, while reaching 10,000 is
`possibly_truncated` and suppresses completeness-dependent claims.

Before aggregate evaluation, run a real runtime parity artifact against a
complete canonical corpus and the frozen split:

```bash
uv run python scripts/evaluate_v61_calibration.py runtime-parity \
  --input .local/calibration/v61/canonical-corpus.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --artifact-dir .local/calibration/v61 \
  --output .local/calibration/v61/evaluation/runtime-parity-6.1.0.json
```

Then pass that file explicitly to `aggregate` with `--runtime-parity`. The
aggregate command fails closed when the artifact is absent or is not bound to
the current commit, clean-worktree state, corpus checksum, split checksum,
artifact checksums, report versions, and all required assertions. The legacy
compact corpus is not a substitute; do not insert missing fields by hand.

## Production beta authorization

The frozen training bundle is deliberately not self-authorizing. For the
owner-directed production beta, generate a separate authorization after the
automated State B aggregate passes:

```bash
uv run python scripts/evaluate_v61_calibration.py authorize-production-beta \
  --output .local/calibration/v61/evaluation/production-beta-authorization-6.1.0.json \
  --operator-reference "user-task:Free DNA V6.1 production beta"

uv run python scripts/package_v61_production_bundle.py \
  --artifact-dir .local/calibration/v61 \
  --authorization .local/calibration/v61/evaluation/production-beta-authorization-6.1.0.json \
  --output-dir .local/release/v61/6.1.0
```

The authorization records that the owner assumed the review approvals were
complete; it does not invent reviewer names or alter the frozen training
manifest. Mount the packaged directory read-only into both API and worker. In
`infra/compose.yaml`, set `FREE_DNA_V61_ARTIFACT_HOST_DIR` to that directory,
set `FREE_DNA_V61_ENABLED=true`, and keep all shadow/experimental flags false.
The service refuses to start if either service is missing the bundle,
authorization, matching checksums, or the release source binding.

The interaction-session bearer token is only for session access. It cannot
authorize Deep. Deep requires a separate, short-lived capability bound to the
report, account, diagnostic question, grant, and expiry; missing, malformed,
expired, revoked, replay-detected, mismatched, timed-out, or unavailable
entitlement decisions fail closed.

This is a production beta rollout. It is reversible by setting
`FREE_DNA_V61_ENABLED=false` on both API and worker; it does not require
re-running the sealed holdout.

## State A: implementation verification

Run the commands in the [release gates](../qa/free-dna-v6.1-release-gates.md).
Generate the synthetic record with:

```bash
uv run python scripts/evaluate_v61_calibration.py synthetic \
  --artifact-dir .local/calibration/v61 \
  --output .local/calibration/v61/evaluation/synthetic-6.1.0.json
```

Synthetic rates validate the harness, but cannot substitute for State B or
authorize traffic.

## State B: calibration workflow

For the completed existing-corpus run, do not recollect. The exact corpus and
frozen split are recorded in the [calibration record](../qa/free-dna-v6.1-existing-corpus-calibration-record.md).
Training, holdout, and runtime use the compact-to-canonical analytical adapter;
the holdout was evaluated once against the frozen bytes. Private rows,
identifiers, manifests, checkpoints, and reviewer packets stay under owner-only
`.local/calibration/` paths and are never copied into an image.

Network recollection is not part of this calibration and requires separate
authorization. Do not run the collector for the existing-corpus State B record.
If a future task explicitly authorizes a new collection, the guarded collector
uses exactly the runtime contract:

```bash
uv run python scripts/collect_v61_calibration_histories.py \
  --candidates .local/calibration/v61/candidates.json \
  --salt .local/calibration/v61/salt.bin \
  --acknowledge-network-collection
```

The staged builder derives `context-baseline-3.0.0`,
`metric-thresholds-6.1.0`, and the training-only prior, distance, reliability,
and semantic artifacts from the 791-profile training set:

```bash
uv run python scripts/build_v61_calibration_artifacts.py audit-reuse ...
uv run python scripts/build_v61_calibration_artifacts.py baseline ...
uv run python scripts/build_v61_calibration_artifacts.py calibrate-support ...
uv run python scripts/build_v61_calibration_artifacts.py thresholds ...
uv run python scripts/build_v61_calibration_artifacts.py freeze ...
uv run python scripts/build_v61_calibration_artifacts.py verify-reproducibility ...
```

Run the sealed holdout exactly once after freeze, then run the aggregate
evaluation with the required runtime-parity file. Rebuild from a fresh output
directory and require byte-identical hashes. State B does not authorize
release. Existing State B artifacts from before the canonical `leaver_status`
boundary must be regenerated rather than reused.
Do not promote if a key is missing, duplicated, non-finite, rank/MMR-shaped, or
if the artifact declares a V6.0 version.

## State C: release workflow

Run measured synthetic and sealed-holdout evaluation, independent Dota and
statistical review, privacy/data-basis approval, copy scanning, container
inspection, and checksum verification. The aggregate decision must derive all
gates and remain false when any evidence or approval is missing.

Traffic stages are 5%, 25%, and 100% at the deployment layer. Each stage needs
an explicit operator decision and observation window. Monitor aggregate error,
latency, abstention, interval width, identity availability/stability, baseline
resolution, and request ledgers. Never use player identifiers, identity slots,
Element zones, or outcome directions as monitoring dimensions.

## Rollback

Set `FREE_DNA_V61_ENABLED=false` on API and worker and roll back through the
deployment layer. Do not delete V6.1 artifacts or stored snapshots. Verify:

- new reports select the operator-approved older generation;
- existing V6.1 snapshots still validate and render;
- both services report the disabled flag;
- no detail, parse, or parse-status request occurred in Free;
- artifact checksums and private-data image scans still pass.

Rollback triggers include request-boundary violations, artifact/checksum
mismatch, forbidden copy, public shadow outcomes, report error or latency
regression, unexpected abstention/identity changes, and wider or unresolved
interval/baseline rates.
