# Free DNA V6.1 existing-corpus calibration record

Status: **Historical State B record; superseded for release by the current
hardening gates; release unauthorized**.

This record describes the owner-directed offline calibration requested for the
existing corpus. No collector was run and no new OpenDota request was made.
The corpus, split, holdout checkpoint, and artifact outputs remain private under
`.local/calibration/`.

## Frozen inputs

| Input | Value |
|---|---|
| Corpus | `.local/calibration/v6-eligible-corpus-windowed.json` |
| Corpus SHA-256 | `1cbce329f903ccad922aeddb93046b6aa2e505004937ebaaec1b854d853e41bd` |
| Split | `.local/calibration/manifests/split-6000.json` |
| Split SHA-256 | `a1433de109368ba06e54ea65ae595a83e8b8376c5832b2dc91cf2b1f37ac85e9` |
| Split | seed 6000; 791 train; 339 holdout; zero overlap |
| Reuse audit | `179b77b3f28996f8cbb5eb898cb484bf5a2458fcd333209bd0311ab3583f47aa` |
| Reuse authorization | owner-directed task reference; no independent approval inferred |
| Analytical adapter | `legacy-v6-compact-to-v61-1.0.0` |

The audit records legacy paginated transport and compact-to-canonical analytical
compatibility. It does not claim that the legacy corpus was collected in one
physical request; unsupported optional branches are suppressed. It also
predates mandatory `leaver_status` evidence and the required runtime-parity
artifact, so it cannot be reused for a current release decision.

## Frozen build

Build timestamp: `2026-08-24T00:00:00+07:00`.

| Artifact | SHA-256 |
|---|---|
| `context-baseline-3.0.0.json` | `d2d64bac3d2cbe0c7dc0acd4cbbce81badf2ee8e8a9eff4f87470c227290f5f9` |
| `metric-thresholds-6.1.0.json` | `cd442b3459ce5d0ae663367523d10968ee8f3d128ba914d368e323661cf8cdd0` |
| `summary-priors-6.1.0.json` | `a34b7b251d68b1798ec93a4405d9a7ff3cfcba2df3d5c055de97130a0f877765` |
| `portfolio-distance-calibration-1.0.0.json` | `6f2f419a95c994049d474837bac30f02c374fd9a7a8f96c8f538ee0d3f28010e` |
| `session-reliability-calibration-1.0.0.json` | `e20416c54602195bbd93c0ecb8a4158a90d227bf776c8bcd94759eeaaa666f2c` |
| `semantic-outcome-calibration-1.0.0.json` | `015d91c17788809ae53126bbf24607d6f338c7c9d93eddc72b5b75c100c51363` |
| `build-manifest-6.1.0.json` | `9087b85f8a97f06e295d000d6eda43545bf544f0080801bf2b03b2f50dedd55a` |

The freeze record declares `holdout_output_inspected=false` at freeze time and
`release_authorized=false`. A fresh rebuild in `.local/calibration/v61-repro/`
matched all nine declared build outputs byte-for-byte. The reproducibility
record reports `byte_identical=true` and the same compatibility-audit checksum.

## Sealed holdout

The holdout evaluator was sealed by an owner-only access record and completed
once against the frozen bundle:

- 339/339 profiles evaluated; 0 errors.
- Exactly 2,000 deterministic session-cluster bootstrap iterations.
- Seven elements and five family roots present for every report.
- Nonblank identity and high-confidence split-half agreement gates passed.
- Family and branch FDR gates passed.
- Zero forbidden copy, free-cost, experimental-public, and rank/MMR leaks.
- Paired V6.0 holdout evidence available for all 339 split members.
- Holdout aggregate: `holdout_passed=true`; aggregate output contains no private identifiers.

## Decision

The aggregate calibration evaluation reports `state_b=true` and
`state_c=false`. The release manifest reports `release_ready=false`,
`release_authorized=false`, and `public_flags_must_remain_off=true`.

State C still requires independent statistical review, Dota-supported and
believable review, copy overclaim review, accessibility and product-comprehension
review, data-basis/privacy approval, container/checksum verification, and an
explicit operator authorization. Do not promote, deploy, or enable State C from
this record.
