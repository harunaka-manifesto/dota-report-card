# Free DNA V6.1 release and rollback runbook

V6.1 is disabled by default. Fixture artifacts and synthetic evaluation never
authorize deployment or public traffic.

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

## State A: implementation verification

Run the commands in the [release gates](../qa/free-dna-v6.1-release-gates.md).
Generate the synthetic record with:

```bash
uv run python scripts/evaluate_v61_calibration.py \
  --output .local/calibration/v61/synthetic-evaluation.json
```

Confirm the record reports State A and State D true, States B/C false, and no
missing or failed implementation checks. Synthetic rates validate the harness,
but cannot override a missing State A check. State A permits local and shadow
engineering QA only.

## State B: calibration workflow

Use only a reviewed public/consented corpus. Collection, fixtures, training,
holdout, and runtime must call the same canonical summary-history projection
and normalizer. Freeze a deterministic player-exclusive split before deriving
artifacts; keep the holdout sealed. Private rows, identifiers, manifests,
checkpoints, and reviewer packets stay under owner-only `.local/calibration/`
paths and are never copied into an image.

Network recollection is not part of State A and requires separate
authorization. When authorized, the guarded collector uses exactly the runtime
contract:

```bash
uv run python scripts/collect_v61_calibration_histories.py \
  --candidates .local/calibration/v61/candidates.json \
  --salt .local/calibration/v61/salt.bin \
  --acknowledge-network-collection
```

Derive `context-baseline-3.0.0` and `metric-thresholds-6.1.0` from training data
only. The candidate builder also emits training-only prior, distance, and
semantic manifests:

```bash
uv run python scripts/build_v61_calibration_artifacts.py \
  --input .local/calibration/v61/corpus.json \
  --output-dir .local/calibration/v61/candidate-artifacts \
  --seed 6100 \
  --generated-at 2000-01-01T00:00:00+00:00
```

Rebuild from a clean output directory and require byte-identical hashes.
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
