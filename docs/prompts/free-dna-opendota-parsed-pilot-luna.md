# Luna Pilot — Free DNA OpenDota Parsed-State QA

This is a **four-call maximum provider-semantics QA**, not a Finding calibration and not production work.

## Hard stop before provider access

Do all offline preflight and then stop. Do not make any provider call unless the owner explicitly approves this exact ceiling in the active task:

```text
I approve up to 4 OpenDota GET requests, Rp8 and $0.0004 pro-rata under the owner-supplied rate, with zero parse submissions, zero retries, and immediate stop on schema/state disagreement.
```

No approval means return `BLOCKED — OWNER APPROVAL REQUIRED` after offline preflight.

## Scope

Allowed after approval:

- two detail GETs for stored matches already represented in the local tuning corpus: one `source_version=22`, one `source_version=null`;
- one additional already-parsed detail GET to verify Tier-2 fields and that no parse submission occurs; and
- one timed repeat only if it is a physical GET and remains inside the four-call ceiling.

Forbidden:

- replay parse submissions or polling;
- STRATZ or Steam;
- old holdout or fresh sealed-validation analytics;
- Finding formulas, thresholds, calibration, or publication decisions;
- production code, report contracts, deployment, or environment changes;
- retries, replacements, or extra calls after any failure.

## Offline preflight

1. Read `AGENTS.md`, production-safety and analytical-invariant manuals.
2. Verify branch/worktree isolation and preserve the owner worktree.
3. Re-run `scripts/free_dna_opendota_parsed_feasibility.py` and require all corpus digests to pass.
4. Read `docs/evidence/free-dna-opendota-parsed-feasibility-2026-08-28.md` and the local `minimal_provider_qa_plan.json`.
5. Select match identifiers privately from the permitted tuning corpus. Never print or commit them.
6. Print the exact request/cost ceiling and stop for approval.

## Approved execution

Use sequential requests, no retry:

1. Fetch one stored `source_version=22` match detail. Require `version=22`, `od_data.has_parsed=true`, and expected parsed fields.
2. Fetch one stored `source_version=null` match detail. Record whether `version` remains null and `od_data.has_parsed=false`; do not submit parsing.
3. If steps 1–2 agree, fetch one additional known parsed detail and record presence/shape of purchases, wards, kill logs, minute series, objectives, teamfights, and advantage timelines.
4. Use the final allowed call only for a predeclared latency repeat. Record elapsed time as one observation; do not infer an SLA.

Stop immediately on disagreement, rate limit, unexpected billing, schema drift, parse-workflow requirement, or any ceiling risk.

## Outputs

Local-only under `.local/diagnostics/free-dna-opendota-parsed-pilot/`:

- `preflight.json`
- `request_ledger.jsonl`
- `parsed_marker_crosscheck.json`
- `detail_shape_check.json`
- `latency_observation.json`
- `aggregate_summary.json`

Tracked evidence may contain aggregate states and field names only. No raw IDs, raw payloads, or user identifiers.

## Required integrity

```text
OPENDOTA CALLS <= 4
PARSE JOBS SUBMITTED = 0
RETRIES = 0
STRATZ CALLS = 0
OLD HOLDOUT EVALUATED = 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED = 0
PRODUCTION ANALYTICAL BEHAVIOR CHANGED = NO
DEPLOYED = NO
```
