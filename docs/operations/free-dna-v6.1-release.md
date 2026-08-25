# Free DNA V6.1 release and rollback runbook

V6.1 remains disabled. This runbook documents the future operator workflow; it
does not assert that a private canonical corpus, split, artifact bundle,
holdout, or release gate currently exists or passes.

Keep these values on the API and worker until the complete workflow has passed:

```text
FREE_DNA_V61_ENABLED=false
FREE_DNA_V61_SHADOW_ENABLED=false
FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED=false
FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED=false
```

The public enable flag is mutually exclusive with `FREE_DNA_V6_ENABLED`.
Production also requires `APP_ENV=production`, database-backed storage,
Celery/Redis execution, `RELEASE_COMMIT_SHA=<release commit>`, and
`RELEASE_WORKTREE_DIRTY=false`. The API and worker must receive the same
values. `OPENDOTA_SOURCE=fixture` is rejected in production.

## Canonical contract

The only authorized V6.1 calibration path is:

```text
candidate input → canonical collector → corpus validator/audit → split binding
→ training-only builders → freeze → synthetic/holdout/runtime parity → aggregate
→ separate production-beta authorization → bundle packaging
```

The canonical collector and runtime use `/players/{account_id}/matches` with
one physical request per profile, a 365-day window, provider limit 10,000,
the shared canonical projection, and `retry_limit=0`. No detail-match or parse
request is permitted. Rank/MMR is not an analytical dimension. Missing or
invalid `leaver_status` is excluded and never converted to zero; included rows
must have `leaver_status` 0 or 1. Session fields are derived with the runtime
90-minute session policy. The private materialized corpus may retain salted
profile hashes, match IDs, source fields, and session fields, but never
`account_id`. Aggregate evidence must remain identifier-free.

The historical 791 training profiles remain readable as
`v61-calibration-corpus-2.0.0`. The latest canonical schema is
`v61-calibration-corpus-2.1.0`, which is required for the eventual replacement
release corpus. That mixed-window corpus is expected because the historical
training profiles and the 339 replacement holdout profiles are collected at
different times. Each profile carries its own `collection_window` with exactly
365 days; no profile receives more than 365 days, and no top-level start/end
envelope is used as an analytical window. The 2.1.0 `window_policy` is
`per_profile_365_day`, and session/completed-session inference uses each
profile's declared window. The replacement corpus has not been built here.

## Consumed holdout and replacement protocol

The prior 339-profile holdout was consumed by the failed release and is not
re-run, recollected, or reused as sealed evidence. The local candidate inventory
contains 2,364 candidates: 1,130 belong to the original population and ten
reserve candidates were previously screened (including the two selected in that
screen). Excluding those leaves exactly 1,224 untouched reserve candidates.

Before any network call, commit an owner-only replacement manifest containing
that exclusion rule, the fixed ordering key
`sha256("v61-new-holdout-reserve-scan-2026-08-25:" + account_id)` with the
numeric account ID as the tie-breaker, the `>=30` usable-match rule, and the
first-339-eligible selection rule. Selection may use only request completeness,
canonical normalization, and the predeclared usable-match threshold; it must
not use V6.1 outcomes, findings, rank, or MMR. Scan every candidate once so
replacement availability is deterministic: the exact new OpenDota call count is
**1,224 summary calls**. Do not begin a sealed evaluation unless at least 339
eligible candidates remain; never fill the shortfall from the revealed holdout.

Build a fresh 791/339 corpus, split, audit, and training artifact directory
from the unaffected training population plus the first 339 eligible reserve
profiles. Bind every artifact to the new corpus and split checksums. The
revealed 339 remain validation diagnostics only.

## Private raw response archive

For a future scan, pass `--raw-archive-dir` to the dedicated replacement
scanner. It writes one owner-only, mode-600 JSON object per pseudonymous
profile and refuses to replace an existing object. The archive stores the
requested summary projection, endpoint template, request parameters, capture
timestamp, provider/projection/normalization versions, raw count,
provider-limit completeness state, and a SHA-256 of the stored response. It
removes identifier fields before writing and does not store an account-ID
lookup; the candidate input and salt stay owner-only for collection. Rank/MMR
and detail/parse requests remain forbidden.

The stored response can be hash-checked and re-normalized with
`normalize_archived_summary_history`; the same canonical normalization and
session policy are then applied without another network request. A response at
the 10,000-row ceiling remains `possibly_truncated` and cannot support
completeness-dependent claims.

## Paths and candidate input

The commands below are a template for an owner-only shell. They require the
precommitted replacement candidate and split manifests from the protocol above;
do not substitute the consumed 1,130-profile input. Do not print private files
or their contents.

```bash
set -euo pipefail

export CAL=.local/calibration/v61
export CANDIDATES="$CAL/replacement-candidates-precommitted-2026-08-25.json"
export SCAN_STATE="$CAL/replacement-scan-state"
export RAW_ARCHIVE="$CAL/raw-summary-archive"
export RAW_SCAN="$CAL/replacement-summary-scan.json"
export CORPUS="$CAL/replacement-canonical-corpus.json"
export AUDIT="$CAL/corpus-compatibility-2.0.0.json"
export ARTIFACTS="$CAL/staged"
export EVAL="$CAL/evaluation"
export STAMP=2000-01-01T00:00:00+00:00

mkdir -p "$CAL/manifests" "$ARTIFACTS" "$EVAL"
test -s .local/calibration/v6-public-match-candidates.json
test -s "$CAL/candidates.json"
test -s "$CAL/replacement-candidates-batch-01.json"
test -s .local/calibration/v61/manifests/split-6000-canonical.json
test -s .local/calibration/v6-corpus-salt.bin
```

If any source file or the salt is missing, stop. Do not recreate the original
1,130-profile candidate artifact. After this implementation is committed and
the worktree is clean, prepare the private manifest before any OpenDota request:

```bash
test -z "$(git status --porcelain)"
uv run python scripts/prepare_v61_replacement_holdout.py \
  --historical-candidates .local/calibration/v6-public-match-candidates.json \
  --original-population .local/calibration/v61/candidates.json \
  --screened-reserve .local/calibration/v61/replacement-candidates-batch-01.json \
  --salt .local/calibration/v6-corpus-salt.bin \
  --current-split .local/calibration/v61/manifests/split-6000-canonical.json \
  --expected-current-split-sha256 174caebdaf13b45f70423002216007abac00510aeecc1a1df686152c52aec1c5 \
  --release-sha "$(git rev-parse HEAD)" \
  --output "$CANDIDATES"

# Re-run the exact command above to verify the same private bytes without rewriting;
# its aggregate status must be "verified-existing".
test -s "$CANDIDATES"
```

“Precommitted” means this private, git-ignored account-ID manifest is frozen
before any replacement history request; it does not mean the manifest is
committed to Git. The manifest records 1,224 planned summary requests, zero
detail/parse requests, retry limit 0, and mandatory raw archiving.

## Resumable scan, deterministic selection, and validation

The following is a future, owner-authorized command. It is not a claim that
the replacement scan has run. The scanner freezes the 365-day boundary in its
private immutable manifest, fsyncs an `attempt_started` marker before each
request, records failures without retrying, and resumes from per-profile state.
Completed archives are hash-checked and normalized locally. A marker without an
archive becomes indeterminate and is never retried automatically; any such
result remains fail-closed.

The scanner-owned ceiling is 240 network attempts per minute, with a minimum
request-start interval of 0.25 seconds. The current upstream
API_KEY_PER_MIN_LIMIT is expected to be 300 per minute, so this safety margin
is intentional. Pacing applies only to new network attempts; archive reuse,
local normalization, and terminal resume states do not sleep. The collection
retry limit remains 0, including for a 429 response.

```bash
test -z "$(git status --porcelain)"
uv run python scripts/scan_v61_replacement_holdout.py \
  --precommit-manifest "$CANDIDATES" \
  --salt .local/calibration/v6-corpus-salt.bin \
  --raw-archive-dir "$RAW_ARCHIVE" \
  --state-dir "$SCAN_STATE" \
  --output "$RAW_SCAN" \
  --release-sha "$(git rev-parse HEAD)" \
  --acknowledge-network-collection
```

The raw 1,224-profile scan is not itself the release corpus. A later owner-only
selection step must take the first 339 eligible profiles in the frozen
precommitted order, merge them with the unaffected 791 training profiles, and
write the concrete replacement corpus and split. That deterministic selection
and the resulting 791/339 corpus are future steps and are intentionally not
implemented here. Only after they have written `$CORPUS` and the
precommitted split may the validation/build commands below run; do not use the
revealed old holdout to fill any shortfall.

After that future selection step, set the concrete split paths and validate the
actual replacement corpus. The split is not known before collection:

```bash
export RAW_SPLIT="$CAL/manifests/replacement-split-2026-08-25.json"
export SPLIT="$CAL/manifests/replacement-split-canonical-2026-08-25.json"

test -s "$CORPUS"
test -s "$RAW_SPLIT"

uv run python scripts/build_v61_calibration_artifacts.py validate-corpus \
  --input "$CORPUS" \
  --output "$CAL/corpus-diagnostics.json"

uv run python scripts/build_v61_calibration_artifacts.py bind-split \
  --input "$CORPUS" \
  --split-manifest "$RAW_SPLIT" \
  --output "$SPLIT"
```

The split binding fails if the population is not exactly 1,130 usable profiles
or if the 791/339 split no longer covers it; it does not print profile IDs:

```bash
uv run python scripts/build_v61_calibration_artifacts.py audit-reuse \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --output "$AUDIT" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>"
```

The audit computes the corpus SHA from the actual file. No new corpus checksum
is hardcoded in code or documentation.

## Training artifacts and reproducibility

Build all artifacts from the canonical corpus and the bound split. The
compatibility audit is required at every stage, and the holdout is never an
input to training estimators:

```bash
uv run python scripts/build_v61_calibration_artifacts.py baseline \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --compatibility-audit "$AUDIT" \
  --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>" \
  --output "$ARTIFACTS/context-baseline-3.0.0.json"

uv run python scripts/build_v61_calibration_artifacts.py calibrate-support \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --compatibility-audit "$AUDIT" \
  --baseline-input "$ARTIFACTS/context-baseline-3.0.0.json" \
  --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>" \
  --output-dir "$ARTIFACTS"

uv run python scripts/build_v61_calibration_artifacts.py thresholds \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --compatibility-audit "$AUDIT" \
  --baseline-input "$ARTIFACTS/context-baseline-3.0.0.json" \
  --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>" \
  --checkpoint-dir "$CAL/checkpoints/thresholds-6.1.0" \
  --workers 1 \
  --output "$ARTIFACTS/metric-thresholds-6.1.0.json"

uv run python scripts/build_v61_calibration_artifacts.py freeze \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --compatibility-audit "$AUDIT" \
  --artifact-dir "$ARTIFACTS" \
  --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>"
```

Rebuild into a fresh directory with the same source bytes, split, audit,
timestamp, and seed. Then require byte identity:

```bash
export REBUILD="$CAL/repro"
mkdir -p "$REBUILD"

uv run python scripts/build_v61_calibration_artifacts.py baseline \
  --input "$CORPUS" --split-manifest "$SPLIT" --compatibility-audit "$AUDIT" \
  --generated-at "$STAMP" --reuse-authorization-reference "approved-v61-replacement:<ticket>" \
  --output "$REBUILD/context-baseline-3.0.0.json"
uv run python scripts/build_v61_calibration_artifacts.py calibrate-support \
  --input "$CORPUS" --split-manifest "$SPLIT" --compatibility-audit "$AUDIT" \
  --baseline-input "$REBUILD/context-baseline-3.0.0.json" --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>" --output-dir "$REBUILD"
uv run python scripts/build_v61_calibration_artifacts.py thresholds \
  --input "$CORPUS" --split-manifest "$SPLIT" --compatibility-audit "$AUDIT" \
  --baseline-input "$REBUILD/context-baseline-3.0.0.json" --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>" \
  --checkpoint-dir "$CAL/checkpoints/thresholds-6.1.0-repro" --workers 1 \
  --output "$REBUILD/metric-thresholds-6.1.0.json"
uv run python scripts/build_v61_calibration_artifacts.py freeze \
  --input "$CORPUS" --split-manifest "$SPLIT" --compatibility-audit "$AUDIT" \
  --artifact-dir "$REBUILD" --generated-at "$STAMP" \
  --reuse-authorization-reference "approved-v61-replacement:<ticket>"
uv run python scripts/build_v61_calibration_artifacts.py verify-reproducibility \
  --first-dir "$ARTIFACTS" \
  --second-dir "$REBUILD" \
  --output "$EVAL/reproducibility-6.1.0.json"
```

## Evaluation and release authorization

Generate the offline synthetic evidence, run the sealed holdout once, execute
the real runtime assembly path, and aggregate every bound artifact:

```bash
uv run python scripts/evaluate_v61_calibration.py synthetic \
  --artifact-dir "$ARTIFACTS" \
  --output "$EVAL/synthetic-6.1.0.json"

uv run python scripts/evaluate_v61_calibration.py holdout \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --compatibility-audit "$AUDIT" \
  --artifact-dir "$ARTIFACTS" \
  --output-dir "$EVAL"

uv run python scripts/evaluate_v61_calibration.py runtime-parity \
  --input "$CORPUS" \
  --split-manifest "$SPLIT" \
  --artifact-dir "$ARTIFACTS" \
  --output "$EVAL/runtime-parity-6.1.0.json"

uv run python scripts/evaluate_v61_calibration.py aggregate \
  --compatibility-audit "$AUDIT" \
  --artifact-dir "$ARTIFACTS" \
  --synthetic "$EVAL/synthetic-6.1.0.json" \
  --holdout "$EVAL/holdout-evaluation-6.1.0.json" \
  --reproducibility "$EVAL/reproducibility-6.1.0.json" \
  --runtime-parity "$EVAL/runtime-parity-6.1.0.json" \
  --output-dir "$EVAL"
```

The aggregate must bind the actual corpus SHA, bound split SHA, all artifact
checksums, model/report versions, release commit, and clean-worktree state.
State B evidence is not a production authorization.

Only after State B aggregate evidence and the required independent reviews are
complete may an owner create a separate beta authorization and package the
bundle:

```bash
uv run python scripts/evaluate_v61_calibration.py authorize-production-beta \
  --evaluation "$EVAL/calibration-evaluation-6.1.0.json" \
  --release-manifest "$EVAL/release-manifest-6.1.0.json" \
  --output "$EVAL/production-beta-authorization-6.1.0.json" \
  --operator-reference "owner-beta-approval:<ticket>"

uv run python scripts/package_v61_production_bundle.py \
  --artifact-dir "$ARTIFACTS" \
  --authorization "$EVAL/production-beta-authorization-6.1.0.json" \
  --output-dir .local/release/v61/6.1.0
```

Keep the package read-only and use the same package for API and worker. The
service must reject missing or mismatched checksums, source SHA, authorization,
or release identity. Do not enable traffic from a failed or incomplete step.

## Startup, readiness, and rollback

Migrations run before either production process starts:

```bash
docker compose -f infra/compose.yaml run --rm migrate
docker compose -f infra/compose.yaml up -d
curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
```

Readiness must report the database revision, Redis and worker reachability,
complete artifact bundle, matching release identity, and explicit production
authorization. Roll back by setting `FREE_DNA_V61_ENABLED=false` on both API
and worker. Preserve artifacts and snapshots, and verify that new reports use
the approved older generation and that Free makes no detail or parse request.

See the [V6.1 release gates](../qa/free-dna-v6.1-release-gates.md) for the
acceptance checklist and final verification commands.
