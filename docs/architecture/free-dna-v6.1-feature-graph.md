# Free DNA V6.1 feature graph

Status: implemented behind disabled flags; fixture/synthetic validation only  
Public release: not authorized  
Compatibility: V5.2 and V6.0 remain immutable, validator-routed generations

Free DNA V6.1 is an additive summary-only analysis generation. It keeps the
seven public Elements and five top-level finding families from V6.0, but moves
the richer research surface into a typed private graph and publishes only
qualified semantic outcomes with bounded evidence.

## Product boundary

```text
one physical 365-day summary-history request
-> canonical projection, normalization, coverage, and hashes
-> private 128-signal typed graph
-> seven public Element estimates
-> five-family omnibus tests and inner branch correction
-> at most three qualified semantic outcomes
-> PRIMARY / TWIST / ANCHOR identity slots
-> nine-beat immutable story, interactions, share, and optional Deep handoff
```

V6.1 does not request match details, replay parsing, or parse status. It does
not use rank or MMR in inputs, artifacts, thresholds, copy, or cohorting. The
browser renders the server snapshot and never recomputes estimates, tests,
identity, copy, or recommendations.

## Canonical summary history

The sole transport owner is
`services/api/app/ingestion/summary_history_contract.py`.

| Contract | Value |
|---|---|
| Schema | `summary-history-schema-3.0.0` |
| Provider | `opendota-summary-2.0.0` |
| Projection | `summary-projection-3.0.0` |
| Normalization | `summary-normalization-2.0.0` |
| Window | previous 365 days |
| Physical requests | exactly one |
| Provider transport ceiling | 10,000 rows; reaching it means `possibly_truncated` |

The exact projection is `match_id`, `player_slot`, `radiant_win`, `duration`,
`game_mode`, `lobby_type`, `hero_id`, `start_time`, `version`, `kills`,
`deaths`, `assists`, `leaver_status`, `party_size`, `hero_variant`, `leagueid`,
`cluster`, `lane`, `lane_role`, and `is_roaming`.

Optional public context needs at least 80% field coverage. Missing fields stay
missing. Every run records raw and normalized SHA-256 hashes, row counts, date
bounds, per-field coverage, completeness, projection/normalization/provider
versions, request count, and `rank_or_mmr_used=false`.

## Seven public Elements

The ordered V6.1 Element registry remains exactly:

1. Breadth
2. Toolkit
3. Involvement
4. Finishing
5. Death Exposure
6. Transfer
7. Consistency

Breadth and Toolkit use effective-count and concentration measures. Pool shape
also records top-1/top-3 shares, HHI, a stable core, match-weighted fractional
job mass, three exact chronological thirds, Jensen-Shannon movement, and
cross-fitted continuous distance bands.

Finishing uses an event-weighted beta-binomial estimate over kill and assist
opportunities and applies match, session, and event gates. Transfer freezes a
full-history core/stretch split and cross-fits per-session component frontiers.
Consistency uses information-weighted session dispersion with shrinkage.
V6.1 expression and statistical implementations are versioned separately from
V6.0 and cannot be selected by a V6.0 report.

## Private supporting-signal graph

`supporting-signals-1.0.0` classifies exactly 128 research features: A01-A16,
X01-X16, L01-L16, T01-T16, Q01-Q16, P01-P16, C01-C16, and M01-M16. Each entry
owns source fields, an opportunity denominator, minimum matches/sessions/events,
coverage, estimator and normalization versions, allowed consumers, public
exposure, dependencies, and—where applicable—a rejection reason.

The classifications are `PUBLIC_ELEMENT_SUPPORT`, `SUPPORTING`, `CONDITIONAL`,
`LONGITUDINAL`, `FINDING_ONLY`, `RESEARCH_ONLY`, and `REJECTED`. Research-only
and rejected signals are never public. The registry rejects duplicate keys,
unknown consumers, unknown dependencies, and dependency cycles.

Eight signals are explicitly rejected:

- X13 actual role from sparse lane hints
- X14 positioning
- X15 aggression or intent
- X16 death quality
- M09 rank/MMR conditioning
- M10 local time inferred from UTC and cluster
- M11 patch causality
- M12 final inventory treated as item-build identity

## Five finding families and semantic outcomes

The public roots remain Pool Shape, Transfer, Post-Loss Response, Combat
Expression, and Session Drift. `semantic-outcomes-1.1.0` freezes 29 outcome
definitions. Twenty-six are public candidates; `hero_lifecycle`,
`identity_eras`, and `behavioral_loop` are shadow-only experiments.

Each outcome owns its family and hypothesis branch, at least two evidence
groups for public candidates, opportunity denominator and gates, practical
effect or equivalence rule, robustness checks, bounded claim tokens, forbidden
tokens, alternatives, optional recommendation, two-metric verification
contract, interaction kind, share entitlement, and rollout status.

Inference is hierarchical. First, one omnibus p-value per family is corrected
across the five roots with Benjamini-Hochberg. Only a surviving family may test
its branches, which receive a second correction within that family. Missing,
neutral, or insufficient evidence abstains. Ranking occurs after correction and
publishes at most three outcomes.

The current family-statistics implementation is a deterministic fixture and
synthetic approximation. It is not a release-grade calibration result and is
reported as `fixture_synthetic_only` in the snapshot.

## Transitions, sessions, and opportunity denominators

Post-result transitions are same-session and chronological. The states are
win, one loss, two-or-more consecutive losses, and win streak. A row cannot be
reused as both a treatment transition and a control, and controls cannot cross
session boundaries.

Session Drift uses completed sessions and direct G1, G2, G3, G4, and G5+
opportunity curves. Denominators are completed qualifying sessions, not raw
match counts. Duration remains context, never a fatigue claim.

## Identity and story

Identity has three typed slots: `PRIMARY`, `TWIST`, and `ANCHOR`. Slot selection
is deterministic and can remain empty when evidence is insufficient. It does
not synthesize a personality, grade, or global player type.

The story remains nine beats and gains finite interaction kinds:
`contradiction_reveal`, `core_boundary`, `two_versions`, `after_x`,
`variance_decomposition`, and `session_curve`. Every relationship surface has
a table or disclosure alternative. Server copy is deterministic and registered
for all 29 outcomes; missing copy is a validation error.

Claims separate observation, bounded interpretation, unresolved alternatives,
recommendation, verification, and limits. Recommendations lock one primary and
one guardrail metric for the first five qualifying post-cutoff matches. Deep
receives only an opaque protected-cohort reference; public output contains no
cohort members or source identifiers.

## Version matrix

| Surface | V6.1 version | Compatibility decision |
|---|---|---|
| report | `free-dna-report-6.1.0` | changed; V6.0 remains immutable |
| model | `free-dna-model-6.1.0` | changed; new selector only |
| elements | `free-elements-6.1.0` | changed; same seven ordered keys |
| findings | `free-findings-6.1.0` | changed; same five roots |
| supporting signals | `supporting-signals-1.0.0` | new private graph |
| semantic outcomes | `semantic-outcomes-1.1.0` | additive no-transfer outcome; prior reports remain readable |
| expression | `summary-expression-multisignal-2.0.0` | changed |
| statistics | `stats-cluster-bootstrap-2.1.0` | changed; ordered family/branch bootstrap statistics |
| context baseline | `context-baseline-3.0.0` | changed artifact schema |
| thresholds | `metric-thresholds-6.1.0` | changed exact-key manifest |
| claims | `claim-contract-2.0.0` | changed alternatives/verification |
| story | `free-story-6.1.0` | changed payload, same nine beats |
| story payload | `free-story-payload-1.0.0` | new additive descriptive module payload |
| story rules | `free-story-rules-1.0.0` | new frozen aggregation and omission rules |
| story copy | `free-story-copy-1.0.0` | new deterministic story copy variants |
| game mode map | `opendota-mode-map-e7705ee` | new pinned AP/CM mode and lobby tuples |
| hero taxonomy | `hero-taxonomy-2026-08-16` | new frozen public hero taxonomy |
| hero metadata | `hero-knowledge-semantic-freeze-full-roster-v1` | new frozen public hero roster |
| archetype contract | `free-archetype-interface-1.0.0` | new not-ready archetype interface |
| copy | `free-dna-semantic-copy-6.1.1` | additive no-transfer copy; prior reports remain readable |
| recommendations | `free-dna-recommendations-6.1.0` | changed verification contract |
| Deep diagnostics | `deep-diagnostics-2.1.0` | changed protected cohort refs |
| share renderer | `share-svg-6.1.0` | changed semantic cards |
| interactions | `report-interactions-1.1.0` | additive kinds; old sessions readable |
| summary history | `summary-history-schema-3.0.0` | new physical-request contract |

The compatibility fingerprint includes this entire matrix plus baseline and
threshold checksums and the canonical input hashes.

## Flags and rollout states

All flags default to false:

- `FREE_DNA_V61_ENABLED` selects V6.1 generation and requires validated V6.1
  baseline and threshold artifacts.
- `FREE_DNA_V61_SHADOW_ENABLED` permits internal shadow evaluation only.
- `FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED` permits shadow lifecycle/era
  evaluation; it does not make those outcomes public.
- `FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED` permits shadow loop evaluation; it
  does not make loop motifs public.

State A means every planned runtime, model, API, web, calibration-builder,
test, documentation, migration, and rollback item exists and passes fixture or
synthetic verification. State B additionally requires a real,
consented/public calibration corpus and frozen player-exclusive holdout. State
C additionally requires measured interval/FDR, stability, copy, expert,
privacy, container, checksum, and operator gates. Only State C can authorize
public enablement. Current repository evidence is **State A only**: the fixed
implementation manifest and fixture/synthetic checks pass. Automated
interaction coverage includes keyboard, reduced motion, narrow mobile, 200%
text zoom, resume, follow-up, and identity-safe analytics. Deterministic
training-only builders emit validated baseline, threshold, prior, distance,
semantic, and non-authorizing build-manifest artifacts. Experimental
lifecycle, session-block era candidates, split
discovery/verification motifs, and stationary false-positive simulations are
implemented but remain non-public and require separate calibrated evidence.
The protected Deep cohort path keeps exact groups in private repository
storage and resolves them only after entitlement. The separate State D
Markdown handoff is ready.
