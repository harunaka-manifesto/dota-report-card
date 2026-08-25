# Free DNA V6.1 release gates

Current status: **blocked pending calibration, evaluation, and release
authorization**. The replacement corpus is materialized by the offline
selector, but this document does not claim that any State B/C gate passes.

Keep `FREE_DNA_V61_ENABLED=false` and all V6.1 shadow/experimental flags false
until every required gate and the separate operator authorization succeeds.

## Failed release disposition

Release SHA `63b857ce50683cc0a62a1e4c237a964ae4b11e14` is failed and must not
be deployed or reused. Its one-time 339-profile holdout is now revealed and
is diagnostic evidence only: 298 reports evaluated, 41 errors, and
`all_profiles_evaluated=false`. The errors were 33 transfer, 4 involvement,
and 1 consistency insufficient-evidence `ValueError`, plus 3 diagnostic
question `mappingproxy` `TypeError`s. The old checkpoint and its hashes remain
unchanged; no old result is a sealed-release claim or a tuning input.

## Interval methodology

The intended estimand is the metric-specific expected value for a predeclared
population and observation window of comparable future sessions. The failed
holdout did not observe that quantity independently: it compared each report's
point estimate with the bootstrap interval computed from the same history, then
averaged those booleans. Its `0.7838` value is therefore interval
self-containment, not empirical coverage and not evidence that 78.38% of true
population parameters are covered.

Real-data coverage requires a predeclared estimand and independent replicate or
future-session truth: fit on an earlier/disjoint history, form the interval,
and count inclusion of the disjoint target aggregate. Known-truth simulation
is valid for method calibration. The current observational holdout has no
independent truth and cannot support a population-parameter coverage claim;
the same-history value is retained only as a diagnostic named
`interval_self_containment`, never as a release gate. Synthetic known-truth
coverage remains the supported calibration gate.

## Replacement holdout precommit gate

Before any replacement-history network request, the private git-ignored
precommit manifest must pass all of these aggregate checks:

- 1,224 candidates remain after excluding the original 1,130 and all 10
  previously screened reserve candidates.
- Original/screened exclusions have zero overlap, and untouched candidates have
  zero pseudonymous overlap with the current 791/339 population.
- The target is 339 profiles, with canonical eligibility at least 30 usable
  matches.
- The frozen order uses the namespaced account-ID SHA-256 rule and records
  exactly 1,224 summary requests, zero detail requests, zero parse requests,
  retry limit 0, and mandatory raw archiving.

The manifest contains private account IDs, remains mode 0600 under `.local/`,
and must never be committed to Git. “Precommitted” means frozen before network
access, not tracked in the repository.

## Replacement scan resumability gate

The future replacement scan may start only from a clean worktree and a
precommit manifest bound to the exact collection release SHA. Its private scan
manifest must preserve the precommit SHA, candidate-order SHA, salted
pseudonym order, candidate count of 1,224, one frozen 365-day window, provider
limit 10,000, retry limit 0, one summary request per candidate, zero
detail/parse requests, and mandatory raw archiving.

Per-profile state is owner-only and mode 0600 inside mode-0700 directories.
The runner durably records `attempt_started` before a request, writes raw
archives once, atomically writes normalized results, and continues after
terminal failures. Success, failure, and indeterminate are all terminal for
resume purposes; an indeterminate request is never retried automatically and
keeps the release fail-closed. Existing archives are checksum-validated and
renormalized locally without a network request. The aggregate scan artifact
must retain failure/indeterminate counts, `rank_or_mmr_used=false`, and zero
detail/parse accounting. It is not the final 1,130-profile corpus.

The scanner ceiling is 240 new network attempts per minute, or one request
start every 0.25 seconds. The current upstream API_KEY_PER_MIN_LIMIT is
expected to be 300 per minute; the margin is intentional. Pacing uses a
monotonic clock, applies only to new sequential network attempts, and resets
on process restart. Archive/local recovery and terminal resume candidates do
not sleep. retry_limit remains 0, and a 429 is terminal rather than retried.

## Evidence chain

Every stage must consume the same canonical corpus bytes and bind the next
artifact to their actual checksum:

| Stage | Required input/output | Fail-closed condition |
|---|---|---|
| Collection | one summary request per profile; canonical projection; no detail/parse/rank dependency | missing/invalid `leaver_status`, wrong request boundary, or raw identifiers |
| Offline selection | fixed precommit/scan/corpus/split SHAs; first 339 eligible in precommitted order; V2.1 corpus and raw split | any input SHA mismatch, failed scan, shortfall, overlap, wrong window, or nonzero network request |
| Corpus validation | nested profiles with deterministic match/session fields and schema-aware windows | old compact schema, fewer than 30 usable matches, unsupported fields, inconsistent sessions, or a match outside its own profile window |
| Split binding | seed 6000, 791 train, 339 holdout, zero overlap | population or usable-profile mismatch; split not bound to actual corpus SHA |
| Audit | aggregate-only leaver/request/privacy/provenance evidence | audit checksum, corpus checksum, split checksum, or canonical schema mismatch |
| Builders/freeze | training-only artifacts and frozen manifest | holdout rows used for training, missing corpus/split binding, or release authorization in the training manifest |
| Holdout | sealed one-time evaluation over the 339 holdout profiles | holdout membership, corpus, split, artifact, or access-record mismatch |
| Runtime parity | true report assembly path | source SHA/dirty state, corpus, split, artifact, model, report schema, or assertion mismatch |
| Aggregate | identifier-free release evidence | any unbound evidence, failed measured gate, private identifier, path, rank/MMR field, or non-finite value |

## Canonical data contract

Historical canonical evidence remains readable as
`v61-calibration-corpus-2.0.0`; the latest release schema is
`v61-calibration-corpus-2.1.0`. The historical 791 training profiles are
intentionally preserved while the 339 replacement profiles come from the
frozen scan, so the release corpus is mixed-window by design. It retains
`profile_id` as a salted hash, `match_id`, time/duration/outcome/hero/KDA,
`leaver_status`, game mode/lobby type, nullable public context, and runtime-
derived session fields. It never materializes `account_id`. A profile is usable
only with at least 30 included matches. Missing or invalid `leaver_status` is
excluded and audited; it is never defaulted to zero. Session IDs, indexes, and
corruption flags are recomputed with the runtime 90-minute policy. In 2.1.0,
each profile must declare one ordered `collection_window` of exactly 365 days
under `window_policy.mode=per_profile_365_day`; every match and session
inference uses that profile window. A global start/end envelope is not an
analytical window, and no profile receives more than 365 days. The replacement
corpus is materialized only by the selector command below; this gate does not
authorize calibration or evaluation.

The source boundary is `/players/{account_id}/matches`, one physical request,
365 days, limit 10,000, the shared canonical projection, and `retry_limit=0`.
Detail-match and parse endpoints are forbidden. A response at the 10,000-row
ceiling remains auditable as `possibly_truncated`; completeness-dependent
claims must stay suppressed.

## State model

| State | Required evidence | Status before the future run |
|---|---|---|
| A: implementation | code contract, fail-closed validation, synthetic tests, lint/type/docs checks | not asserted here |
| B: calibration-ready | approved canonical corpus, exact split, frozen training artifacts, byte reproducibility, sealed holdout, runtime parity, aggregate gates | blocked |
| C: release-ready | independent statistical/Dota/data-basis/privacy/accessibility reviews, container/checksum verification, operator decision | blocked |

State B does not authorize production. Authorization is a separate owner
decision that must be bound to the aggregate result and release source SHA.

## Measured gates

- At least 1,000 approved profiles and the exact 791/339 player-exclusive split.
- Every usable profile has at least 30 included matches under the canonical
  `leaver_status` boundary.
- Zero detail and parse requests in collection and Free runtime paths.
- Runtime parity assertions are all true except
  `fixture_components_in_production`, which must be false:
  `canonical_one_request`, `full_recomputation`,
  `family_branch_evidence_complete`, and `report_assembly_completed`.
- Runtime parity binds repository commit, dirty-worktree state, canonical
  corpus SHA, split SHA, artifact checksums, model version, and report schema.
- Synthetic known-truth interval coverage is 0.93–0.97 and family/branch null discovery is
  at most 0.05.
- A future holdout may report predictive interval coverage only under a
  precommitted independent time split with enough future sessions; the current
  self-containment diagnostic is not a coverage gate. FDR, identity stability,
  supported-and-believable precision, privacy, and all review gates must meet
  their recorded thresholds.
- Aggregate output contains no profile/account/match/session identifiers,
  private filesystem paths, rank/MMR dimensions, or non-finite values.
- The frozen training manifest and authorization both remain explicit about
  whether traffic is authorized; fixture artifacts never authorize production.

## Replacement materialization command

The collection release is `48de08d851df083b6ab3282cd6231618a90fbbb1`, schema
support is `7908f21c7f812ee72065c378abd97bfaa1270a97`, and the frozen selector
release is `b5ae9257fd82f04f1759e55ef854cdbaf273629f`. From a clean worktree,
run the selector against the immutable private evidence:

```bash
uv run python scripts/select_v61_replacement_holdout.py \
  --precommit-manifest .local/calibration/v61/replacement-candidates-precommitted-2026-08-25.json \
  --replacement-scan .local/calibration/v61/replacement-summary-scan.json \
  --current-corpus .local/calibration/v61/canonical-corpus-final.json \
  --current-split .local/calibration/v61/manifests/split-6000-canonical.json \
  --expected-current-corpus-sha256 273ef68f46746567530a4cb6c6520a5b9b257c8ac35007adb87bedc7ab6ece3e \
  --expected-current-split-sha256 174caebdaf13b45f70423002216007abac00510aeecc1a1df686152c52aec1c5 \
  --collection-release-sha 48de08d851df083b6ab3282cd6231618a90fbbb1 \
  --schema-release-sha 7908f21c7f812ee72065c378abd97bfaa1270a97 \
  --selection-release-sha b5ae9257fd82f04f1759e55ef854cdbaf273629f \
  --output-corpus .local/calibration/v61/replacement-canonical-corpus.json \
  --output-split .local/calibration/v61/manifests/replacement-split-2026-08-25.json \
  --output-selection-evidence .local/calibration/v61/replacement-selection-evidence.json
```

The selector performs zero network requests. It must report 1,224 scanned,
379 eligible, 339 selected, 40 unused eligible reserve, and boundary index
1070 (zero-based). Only after that command succeeds may the existing
`validate-corpus` and `bind-split` commands be run. Calibration builders,
synthetic evaluation, sealed holdout evaluation, and deployment remain outside
this materialization gate.

## Future verification commands

The complete recollection/build/evaluation command sequence is in the
[V6.1 release runbook](../operations/free-dna-v6.1-release.md). After the
implementation is committed, run the required repository checks from a clean
release worktree:

```bash
uv run pytest -q tests/unit/test_v61_canonical_corpus.py \
  tests/unit/test_scan_v61_replacement_holdout.py \
  tests/unit/test_collect_v61_calibration_histories.py \
  tests/unit/test_opendota_client.py \
  tests/unit/test_build_v61_calibration_artifacts.py \
  tests/unit/test_v61_existing_corpus_calibration.py
uv run pytest -q tests/calibration/test_v61_calibration_evaluation.py
make lint
make typecheck
make test
make dna-catalog-check
make docs-check
```

Do not run live collection as part of repository verification. Do not inspect,
copy, or commit `.local/calibration` contents. Before any future recollection,
confirm that the operator has the historical candidate input and salt and that
the existing population can be mapped without exposing profile IDs.
