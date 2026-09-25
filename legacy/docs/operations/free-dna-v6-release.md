# Free DNA v6 release and rollback runbook

Free DNA v6 is disabled by default. Candidate artifact generation and local
evaluation do not authorize deployment or public traffic.

## Candidate workflow

Run every command from the repository root. Private inputs, manifests,
checkpoints, reviewer packets, and per-player evidence stay below
`.local/calibration/` with owner-only permissions.

```bash
uv run python scripts/build_v6_calibration_artifacts.py validate \
  --input .local/calibration/v6-eligible-corpus-windowed.json \
  --split-manifest .local/calibration/manifests/split-6000.json

uv run python scripts/build_v6_calibration_artifacts.py baseline \
  --input .local/calibration/v6-eligible-corpus-windowed.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --baseline-output .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --seed 6000 --generated-at 2026-08-23T11:01:52.851682+00:00

uv run python scripts/build_v6_calibration_artifacts.py thresholds \
  --input .local/calibration/v6-eligible-corpus-windowed.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --baseline-input .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --threshold-output .local/calibration/releases/6.0.0/metric-thresholds-6.0.0.json \
  --checkpoint-dir .local/calibration/checkpoints/thresholds-6.0.0 \
  --seed 6000 --workers 5 --generated-at 2026-08-23T00:00:00+07:00
```

Run `scripts/evaluate_v6_calibration.py synthetic`, then `holdout`, then
`aggregate`. The holdout command is resumable and uses exactly 2,000 bootstrap
iterations unless `--smoke` is explicitly selected for non-release CI.
Promotion refuses missing or failed automated gates, missing reviewer approval,
missing data-basis approval, inconsistent checksums, identifiers, non-finite
values, and rank/MMR fields.

The frozen local candidate has passed all automated gates. Its evaluation
status is `external-review-required`; do not copy it to a production artifact
directory until the reviewed evidence is ingested and all external gates pass.
The independent reviewers complete the packet's item judgments, approval
booleans, and reviewer-reference fields. `evaluate_v6_calibration.py
ingest-review` accepts that completed private packet directly and emits only
aggregate counts, precision, and sign-off references for the release evidence.

## Local review page

Run the review survey only on the machine holding the private packet. The
server binds to `127.0.0.1`, opens the browser, and saves drafts/final output
with owner-only permissions:

```bash
uv run python scripts/serve_v6_calibration_review.py \
  --packet .local/calibration/review/reviewer-packet-6.0.0.json \
  --output .local/calibration/review/reviewer-packet-6.0.0-completed.json
```

For each claim, choose `Accurate and useful`, `Supported, but misleading`,
`Unsupported`, or `Unsure`. The page explains each signal in Dota terms and
keeps raw intervals behind an optional details section. Misleading and
unsupported verdicts require a note. Completing the Dota review does not
self-approve the separate statistical or data-basis gates.

After the page reports that the completed packet was finalized, stop the local
server with `Ctrl-C` and pass the completed file to `ingest-review`. The
2026-08-23 Dota-domain decision and the still-separate external gates are
recorded in
[`docs/qa/free-dna-v6-dota-review-record.md`](../qa/free-dna-v6-dota-review-record.md).

## Internal shadow and staff QA

Use the frozen candidate bytes to generate internal reports without returning
v6 to users. Keep `FREE_DNA_V6_ENABLED=false` on public API and worker
instances. Exercise null/no-effect, positive and negative centered effects,
mixed Transfer, stable and variable Consistency, no/real Post-Loss response,
no/rise/fade Session Drift, patch-boundary fallback, missing baselines, sparse
taxonomy, and 30–59-match limited histories.

Record aggregate success, latency, identity availability, abstention, interval
width, baseline fallback/unresolved rate, and the Free request ledger. Never use
player IDs, identity labels, Element zones, or finding directions as monitoring
dimensions.

## Staged rollout

Traffic stages are deployment-layer decisions: 5%, then 25%, then 100%. Do not
invent an application-level identity cohort. If the deployment platform cannot
split traffic, stop and obtain an operator-approved alternative before any
public enablement. Each stage requires a separate operator decision and a
predeclared observation window.

Rollback triggers include report error/latency regression, nonblank identity or
abstention regression, wider intervals, elevated baseline-unresolved rates, any
Free detail/parse request, checksum mismatch, or forbidden public copy.

## Rollback

Set `FREE_DNA_V6_ENABLED=false` for both API and worker and roll the deployment
back through the deployment layer. This stops new v6 generation and restores v5
generation. Do not delete the artifact release or stored v6 snapshots; their
versions must remain readable for audit and support. Confirm after rollback:

- a new Free analysis produces v5;
- an existing v6 snapshot still validates and renders;
- API and worker report the expected disabled flag;
- no private calibration files were copied into the image.

This runbook applies only to V6.0. The additive V6.1 artifact family, flags,
stages, and rollback rules are maintained in the
[V6.1 runbook](free-dna-v6.1-release.md); never mount or relabel a V6.0 artifact
as V6.1.
