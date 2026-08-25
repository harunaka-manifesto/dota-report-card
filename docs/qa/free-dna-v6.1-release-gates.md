# Free DNA V6.1 release gates

Current status: **blocked pending a future canonical recollection and evidence
run**. This document describes acceptance conditions and commands; it does not
claim that the private corpus exists or that any State B/C gate passes.

Keep `FREE_DNA_V61_ENABLED=false` and all V6.1 shadow/experimental flags false
until every required gate and the separate operator authorization succeeds.

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
- Synthetic interval coverage is 0.93–0.97 and family/branch null discovery is
  at most 0.05.
- Holdout interval/FDR, identity stability, supported-and-believable precision,
  privacy, and all review gates meet their recorded thresholds.
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
