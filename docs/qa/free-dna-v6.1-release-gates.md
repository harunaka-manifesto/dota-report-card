# Free DNA V6.1 release gates

Current status: **blocked pending a future canonical recollection and evidence
run**. This document describes acceptance conditions and commands; it does not
claim that the private corpus exists or that any State B/C gate passes.

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

## Evidence chain

Every stage must consume the same canonical corpus bytes and bind the next
artifact to their actual checksum:

| Stage | Required input/output | Fail-closed condition |
|---|---|---|
| Collection | one summary request per profile; canonical projection; no detail/parse/rank dependency | missing/invalid `leaver_status`, wrong request boundary, or raw identifiers |
| Corpus validation | nested profiles with deterministic match/session fields | old compact schema, fewer than 30 usable matches, unsupported fields, or inconsistent sessions |
| Split binding | seed 6000, 791 train, 339 holdout, zero overlap | population or usable-profile mismatch; split not bound to actual corpus SHA |
| Audit | aggregate-only leaver/request/privacy/provenance evidence | audit checksum, corpus checksum, split checksum, or canonical schema mismatch |
| Builders/freeze | training-only artifacts and frozen manifest | holdout rows used for training, missing corpus/split binding, or release authorization in the training manifest |
| Holdout | sealed one-time evaluation over the 339 holdout profiles | holdout membership, corpus, split, artifact, or access-record mismatch |
| Runtime parity | true report assembly path | source SHA/dirty state, corpus, split, artifact, model, report schema, or assertion mismatch |
| Aggregate | identifier-free release evidence | any unbound evidence, failed measured gate, private identifier, path, rank/MMR field, or non-finite value |

## Canonical data contract

The private corpus schema is `v61-calibration-corpus-2.0.0`. It retains
`profile_id` as a salted hash, `match_id`, time/duration/outcome/hero/KDA,
`leaver_status`, game mode/lobby type, nullable public context, and runtime-
derived session fields. It never materializes `account_id`. A profile is usable
only with at least 30 included matches. Missing or invalid `leaver_status` is
excluded and audited; it is never defaulted to zero. Session IDs, indexes, and
corruption flags are recomputed with the runtime 90-minute policy.

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

## Future verification commands

The complete recollection/build/evaluation command sequence is in the
[V6.1 release runbook](../operations/free-dna-v6.1-release.md). After the
implementation is committed, run the required repository checks from a clean
release worktree:

```bash
uv run pytest -q tests/unit/test_v61_canonical_corpus.py \
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
