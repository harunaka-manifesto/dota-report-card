# Dota Player-Centric Analysis v6 — Implementation Record

## Outcome

`free-dna-report-6.0.0` is implemented as a versioned path beside the immutable v5 report stack. The v6 path is summary-only for Free, uses seven public identity Elements and five finding families, emits a deterministic dynamic identity and nine-beat story, and provides token-protected interaction state plus a diagnostic-question entry into Deep v2.

Production generation remains disabled by default behind `FREE_DNA_V6_ENABLED`. Enabling it requires the calibration and rollout gates in this record; existing v5 reports, schemas, renderers, semantic catalogs, and share cards are not rewritten.

## Current implementation status

Implementation is complete in the working tree, with public release blocked on
the calibration corpus/gates. The checked-in path includes strict baseline and
threshold artifact loaders, deterministic artifact construction, the summary-
only v6 analytical pipeline, real clustered uncertainty and FDR fields, the
server-owned nine-beat payload, token-protected follow-up state, serialized
Deep question specifications, actual parse transport execution, the dedicated
v6 glyph registry, fixture-server interaction routes, and the v6 quality
workflow.

The repository fixtures prove contract behavior and deterministic smoke gates;
they are not production calibration data. A real 1,000-profile player-level
calibration corpus and the external Dota reviewer precision assessment remain
the only release prerequisites outside this repository. Until those gates are
reviewed, `FREE_DNA_V6_ENABLED` must remain false.

## Product contract

- Audience: experienced casual players with at least 30 eligible public matches in the 365-day window.
- 0–29 matches: no report.
- 30–59 matches: limited identity report; no finding-based strength/weakness recommendation.
- 60+ matches: normal report eligibility.
- Stable identity uses equal match weighting. Recency appears only as optional recent-state context.
- Rank and MMR do not affect thresholds, copy, recommendations, or baselines.
- Free may expose literal lane context, never inferred position 1–5 labels.
- Missing or conflicting signals produce `mixed`, `suppressed`, or `unavailable`; they do not collapse to a neutral guess.
- Public claims keep observation, evidence, interpretation, and recommendation separate.
- User responses are stored under `user_reported`; computed truth remains under `observed`.

## Versioned surfaces

| Surface | Version |
|---|---|
| Report | `free-dna-report-6.0.0` |
| Elements | `free-elements-6.0.0` |
| Findings | `free-findings-6.0.0` |
| Multi-signal expression | `summary-expression-multisignal-1.0.0` |
| Statistical intervals | `stats-cluster-bootstrap-1.0.0` |
| Context baseline | `context-baseline-2.0.0` |
| Claim contract | `claim-contract-1.0.0` |
| Story | `free-story-6.0.0` |
| Semantic copy | `free-dna-semantic-copy-6.0.0` |
| Deep diagnostics | `deep-diagnostics-2.0.0` |
| Share renderer | `share-svg-6.0.0` |
| Interaction state | `report-interactions-1.0.0` |

## Free analytical path

The Free path retains one OpenDota summary-history read and performs no match-detail or replay-parse requests:

```text
365-day summary history
→ normalization and eligibility
→ literal lane context and 90-minute sessions
→ non-MMR context-baseline fallback
→ session-clustered estimates and intervals
→ seven Elements
→ five finding families
→ FDR-controlled qualification and ranking (maximum three published)
→ deterministic identity, story, diagnostic questions, and share candidates
```

The seven Elements are:

1. Breadth — Shannon effective hero count.
2. Toolkit — Shannon effective count across match-weighted hero jobs, available only at ≥80% taxonomy coverage.
3. Involvement — context-adjusted `(kills + assists) / minutes`; never described as aggression.
4. Finishing — context-adjusted `kills / (kills + assists)` with zero-event exclusion.
5. Death Exposure — context-adjusted deaths per ten minutes; never used to infer positioning or death value.
6. Transfer — familiar/core versus stretch agreement across outcome, activity, and survival; mixed unless two agree and the third does not confidently oppose.
7. Consistency of Summary Expression — robust session dispersion across outcome, activity, and death exposure; requires 12 usable sessions and two-of-three agreement.

The five finding families are Pool Shape, Transfer, Post-Loss Response, Combat Expression, and Session Drift. Every family requires two meaningfully independent signals. Opposite directions are outcomes within one family. Ranking publishes no more than three findings and favors confidence, identity value, actionability, and cross-family diversity.

## Statistical contract

- Independent sessions, not match rows, are resampled.
- Production estimates use 2,000 seeded bootstrap iterations and 95% intervals.
- Fewer than eight independent sessions cannot produce a high-confidence stable claim.
- High confidence requires ≥90% zone/direction stability and an interval clearing the metric's practical-equivalence region.
- Moderate confidence requires ≥75% stability plus metric-specific sample and coverage gates.
- Thresholds and practical-equivalence margins are versioned per metric; no shared 0.20/0.40/0.60/0.80 bands are used.
- The finite finding set is controlled with Benjamini–Hochberg at `q ≤ 0.05`.
- Baseline fallback is `patch+hero+lane → patch+hero-function+lane → patch+hero → patch+lane → patch → overall`.
- A baseline cell is eligible only at ≥200 matches and ≥50 distinct players.

## Claim and recommendation contract

Every published finding exposes:

```text
CLAIM           literal supported conclusion
EVIDENCE        estimate, interval, sample, sessions, coverage, and comparison
INTERPRETATION  bounded meaning and unresolved alternatives
RECOMMENDATION  context, evidence requirement, and verification rule
```

Free recommendations are limited to hero/toolkit choices and high-confidence summary-observable behavior. Positioning, death quality, item timing, objective conversion, and fight-entry advice require Deep evidence. Deep advice identifies positive, negative, and control evidence and never claims causality.

## Interaction and follow-up contract

The API provides:

- `POST /v1/reports/{report_id}/interaction-sessions`
- `GET /v1/report-interactions/{session_id}`
- `PATCH /v1/report-interactions/{session_id}` with `If-Match`
- `DELETE /v1/report-interactions/{session_id}`
- `POST /v1/report-interactions/{session_id}/follow-up`

An interaction session receives a random 256-bit bearer token once. Only its SHA-256 hash is persisted. State updates are schema-validated and revision-protected, sessions expire after 90 days, and resume links carry credentials in the URL fragment. Explicit deletion is supported. Follow-up reports progress until five eligible context-matching games exist, then compares only the predeclared metric and says what changed in those five games without claiming improvement or changing stable identity.

## Deep v2 contract

`POST /v1/reports/{report_id}/deep-analyses` accepts an offered `diagnostic_question_id` and an optional interaction-session reference. Access is decided by an entitlement interface; pricing and billing are intentionally not implemented.

Deep uses one user-primary hypothesis and at most one secondary hypothesis whose evidence reuse is at least 50%. Candidate acquisition prefers cached parsed data, then cached detail data, then new work. Detail candidates require marginal information gain ≥0.05; new parses require cost-adjusted gain ≥0.10. Hard ceilings are 25 selected matches, 25 detail reads, 25 parses, and 160 relative cost units. Moderate resolution requires positive/negative/control minimums of three each; high resolution requires eight each plus practical effect ≥0.15. Every job persists its parent report, diagnostic choice, entitlement result, selection plan, and explicit stopping reason.

## Story and share contract

The renderer presents nine ordered, skippable beats:

1. Identity self-estimate.
2. Dynamic identity reveal.
3. Hero-pool prediction and Pool Evolution scrub.
4. Combat Expression self-estimate and reveal.
5. Strongest finding comparison.
6. Secondary or conditional finding with layered claim disclosure.
7. Recommendation choice and five-game commitment.
8. Hero Mirror and eligible share-card composer.
9. Deep diagnostic fork.

All controls are visible, keyboard and touch operable, reduced-motion safe, and usable at 200% zoom and narrow viewports. Share choices are limited to eligible identity, strongest-finding/contradiction, and Hero Mirror cards. Eligibility requires high confidence, no blocking confounder, no early-signal wording, no recommendation, and sufficient standalone context. Self-assessments never become evidence.

## Compatibility and rollback

- v5 schemas and snapshots retain their existing strict validation.
- v6 has a dedicated validator and renderer.
- Refreshes generate v6 only when `FREE_DNA_V6_ENABLED` is true.
- Existing reports, evidence, jobs, and share cards are never rewritten.
- Rollback disables new v6 generation; stored v6 snapshots remain readable.
- Existing unrelated worktree changes are preserved.

## Verification gates

Implementation tests cover formulas, missing data, baseline fallback, session rather than row resampling, deterministic seeds, practical effects, mixed multi-signal outcomes, family qualification, exact 7/5/9 contracts, maximum three published findings, and the zero-detail/zero-parse Free boundary. Interaction tests cover token hashing, unauthorized access, revision conflicts, expiry, deletion, resume fragments, and input limits. Deep tests cover primary/secondary selection, evidence reuse, cached preference, information-gain gates, 25/25 ceilings, cost stops, comparison-group sufficiency, and abstention. Web tests cover keyboard, touch, reduced motion, zoom, narrow layouts, resume, follow-up, share selection, and diagnostic routing.

The public flag must remain off until all release prerequisites are satisfied:

- At least 1,000 public/consented calibration profiles stratified by annual eligible volume, pool concentration, lobby mix, and region, never MMR.
- 30% player-level holdout.
- Synthetic 95% interval coverage between 93% and 97%.
- Empirical finding-family FDR ≤5%.
- At least 80% nonblank identity coverage for eligible holdout players.
- At least 80% split-half agreement for high-confidence zones.
- Zero forbidden causal/positioning claims.
- Dota reviewer precision ≥90% on supported-and-believable fixtures.
- Free cost and Deep ceilings pass all fixtures.

Rollout proceeds only after those gates: internal shadow generation, calibration holdout, staff and fixture QA, 5% canary, 25%, then 100%. Operational monitoring excludes identity-shaped analytics fields and tracks coverage, abstention, interval width, story completion, recommendation selection, Deep resolution and parse cost, follow-up completion, and share eligibility.

## Explicit non-goals

- Billing or pricing.
- Archetypes.
- MMR cohorting or MMR-shaped copy.
- LLM-generated public identity copy.
- Account authentication.
- Bayesian partial pooling before it wins a held-out experiment.
- Rewriting historical v5 artifacts.
