# Dota DNA v5.2 — Single Source of Truth

Status: canonical for the current Free Dota DNA product  
Effective date: 2026-08-22  
Repository baseline reviewed: `3670c49` (`v5.2 sol+luna`)

Figma source: [Report — Knowledge base, node 179:2](https://www.figma.com/design/D3uhn7WPXFsX1DiCIVklyg/Report?node-id=179-2)

## 1. Purpose and authority

This document is the single product and engineering reference for the current
Free Dota DNA model. It consolidates the reviewed Figma knowledge base, the four
checkpoint/implementation documents supplied for this audit, and the behavior
implemented in this repository.

When artifacts disagree, use this precedence:

1. This SSOT for the current model and the conflict resolutions recorded here.
2. Reviewed Figma Element and Pattern frames under node `179:2` for intended
   product meaning, player-facing structure, and copy boundaries.
3. The canonical Element and Pattern registries for executable identities,
   axes, zones, qualification clauses, and gates.
4. Scorer, baseline, Pattern, action, ranking, and assembly code for executable
   methodology.
5. API schemas and generated clients for wire-format and historical-read
   compatibility.
6. Public content, generated catalogs, architecture notes, and web rendering.
7. Older checkpoints as decision history only.

Figma example heroes and numbers illustrate presentation. They are not runtime
thresholds or facts about a player. Runtime values must come from the immutable
report snapshot and its evidence receipts.

## 2. Current product model

The Free product answers two different kinds of question:

- **Elements** measure one observable behavioral axis.
- **Patterns** qualify a reviewed relationship between Element results.

The canonical pipeline is:

```text
one 365-day public summary-history request
→ normalization and eligibility
→ chronology, sessions, and reusable features
→ 18 Elements
→ 11 reviewed Patterns
→ evidence-bounded Pattern actions
→ semantic outcome and recommendation branches
→ independently evaluated Hero Portfolio
→ deterministic ranking and report story
→ immutable, versioned report snapshot
```

Elements do not claim motive, personality, skill, or causality. Patterns do not
re-mine normalized match rows: qualification consumes upstream Element status,
zone, confidence, coverage, quality, receipts, and confounders. Actions are
downstream evidence consumers and cannot change whether a Pattern qualified.

## 3. Free-data boundary

The Free report uses one previous-365-day summary-history window. There is no
normal 500-match cap and no patch-normalization requirement.

Allowed inputs include public summary fields such as hero, outcome, chronology,
duration, kills, deaths, assists, and available role hints. Free may also use
versioned editorial hero taxonomy, relationship, capability-expression,
matchup, synergy, and situation artifacts.

Free must not:

- request match detail or replay parse data;
- infer replay-only facts such as positioning, spell use, objective execution,
  warding, or exact fight decisions;
- fill unavailable evidence with a neutral score;
- present correlation or a summary difference as cause, intent, psychology, or
  a hidden trait;
- let browser code recompute server-owned scores, rankings, or actions.

A limited history may produce a valid partial report. Unavailable and abstained
states are product results, not errors.

## 4. Canonical Element registry

The active registry is `free-elements-5.2.0` and contains exactly 18 Elements,
in this order:

| ID | Key | Label | Axis | Minimum sample | Minimum coverage |
|---|---|---|---|---:|---:|
| E01 | `hero_pool_breadth` | Breadth | Focused → Wide | 30 | 0.00 |
| E02 | `hero_pool_stability` | Stability | Restless → Steady | 60 | 0.00 |
| E03 | `hero_exploration_rate` | Exploration | Comfort → Experimental | 60 | 0.00 |
| E04 | `toolkit_breadth` | Toolkit | Compact → Diverse | 30 | 0.80 |
| E05 | `post_loss_familiarity_shift` | Familiarity | Branches out → Comfort pick | 30 | 0.00 |
| E06 | `role_breadth` | Role | Anchored → Fluid | 30 | 0.40 |
| E07 | `combat_involvement` | Involvement | Quiet → Everywhere | 30 | 0.00 |
| E08 | `finisher_orientation` | Finishing | Setup → Cleanup | 30 | 0.00 |
| E09 | `death_exposure` | Deaths | Elusive → Frequent | 30 | 0.00 |
| E10 | `off_pool_performance` | Transfer | Falls off → Carries over | 40 | 0.00 |
| E11 | `off_pool_activity_stability` | Presence | Changes shape → Unchanged | 24 | 0.00 |
| E12 | `performance_volatility` | Volatility | Rock solid → Wild | 30 | 0.00 |
| E13 | `recent_form_shift` | Form | Sliding → Surging | 45 | 0.00 |
| E14 | `recent_activity_shift` | Pace | Quieter → Full tilt | 45 | 0.00 |
| E15 | `session_length_tendency` | Duration | Burst → Marathon | 25 | 0.00 |
| E16 | `late_session_performance` | Drift | Drops → Finishes strong | 27 | 0.00 |
| E17 | `post_loss_activity_shift` | Tempo | Pulls back → Accelerates | 30 | 0.00 |
| E18 | `post_loss_performance_response` | Recovery | Drops → Surges | 30 | 0.00 |

E14's endpoint **Full tilt** is an explicit owner-copy decision and is not an
engineering typo to normalize away.

### 4.1 Shared score-to-zone rule

All Elements use one half-open boundary function:

| Score | Zone index |
|---|---:|
| `[0.00, 0.20)` | 1 |
| `[0.20, 0.40)` | 2 |
| `[0.40, 0.60)` | 3 |
| `[0.60, 0.80)` | 4 |
| `[0.80, 1.00]` | 5 |

The implementation authority is `ZONE_BOUNDARIES` plus `bisect_right()` in
`behavior/elements/registry.py`. Exact values `.20`, `.40`, `.60`, and `.80`
belong to the higher zone.

### 4.2 Context-adjusted Elements

Drift and Recovery use the shared `context-baseline-1.0.0` resolver. Its
fallback hierarchy is:

```text
hero + role + function
→ hero + function
→ function
→ role
→ overall
```

The target group is excluded from its own reference baseline. The resolver
requires at least three reference observations, uses the approved weighting,
and records the selected level, exclusion, counts, weights, and version.

Recovery's authority is session-clustered: transition rows may contribute to a
within-session estimate, but independent sessions—not raw transitions—carry
the final statistical authority. Current gates require 30 usable transitions,
three independent sessions, and 50% comparable-context coverage.

## 5. Canonical Pattern registry

The active registry is `free-patterns-5.1.0` and contains exactly 11 Patterns.
The following order, public names, tiers, and qualification clauses are fixed:

| ID | Key | Public title | Tier | Exact qualifying clause |
|---|---|---|---|---|
| P01 | `same_playbook` | Same Playbook | A | Breadth ∈ {Varied, Wide} AND Toolkit ∈ {Compact, Focused} |
| P02 | `comfort_edge` | Comfort Edge | A | Breadth ∈ {Varied, Wide} AND Transfer ∈ {Slips, Falls off} |
| P03 | `partial_transfer` | Partial Transfer | A | Presence ∈ {Holds, Unchanged} AND Transfer ∈ {Slips, Falls off} |
| P04 | `versatile_core` | Versatile Core | A | Breadth ∈ {Focused, Selective} AND Toolkit ∈ {Versatile, Diverse} |
| P05 | `proven_flexibility` | Proven Flexibility | A | Breadth ∈ {Varied, Wide} AND Transfer ∈ {Travels, Carries over} |
| P06 | `bounceback` | Bounceback | B | Recovery ∈ {Recovers, Surges} AND (Familiarity ≠ Unchanged OR Tempo ≠ Same) |
| P07 | `performance_slide` | Performance Slide | B | Recovery ∈ {Drops, Slips} AND (Familiarity ≠ Unchanged OR Tempo ≠ Same) |
| P08 | `controlled_presence` | Controlled Presence | B | Involvement ∈ {Active, Everywhere} AND Deaths ∈ {Elusive, Safe} |
| P09 | `presence_tax` | Presence Tax | B | Involvement ∈ {Active, Everywhere} AND Deaths ∈ {Exposed, Frequent} |
| P10 | `session_fade` | Session Fade | B | Duration ∈ {Long, Marathon} AND Drift ∈ {Drops, Fades} |
| P11 | `session_rise` | Session Rise | B | Duration ∈ {Medium, Long, Marathon} AND Drift ∈ {Warms up, Finishes strong} |

### 5.1 Qualification gates

Every Element in the selected clause must be available, scored, meet its own
registry minimum coverage, and have confidence of at least `0.45`. Failures are
distinguished as unavailable, below coverage, below confidence, zone mismatch,
or blocking confounder.

For P06/P07, only the selected Recovery + Familiarity or Recovery + Tempo clause
supplies authoritative confidence, coverage, quality, receipts, blockers, and
strength. Deterministic clause selection compares minimum confidence, mean
confidence, minimum coverage, component sum, then registry order.

For a qualified, unblocked Pattern:

```text
relationship_strength = mean(reviewed zone components)
strength = relationship_strength × confidence × coverage × qualification_quality
```

Ranking must not multiply confidence or coverage a second time.

### 5.2 Selection and oppositions

Free publishes up to five qualified, story-eligible Patterns. The deterministic
selector considers evidence-weighted strength, confidence, novelty, family
diversity, a close Tier-A preference, and a small same-family redundancy
penalty. If fewer than five clear the gates, publish fewer than five.

The principal mirrored pairs are Same Playbook ↔ Versatile Core, Comfort Edge ↔
Proven Flexibility, Bounceback ↔ Performance Slide, Controlled Presence ↔
Presence Tax, and Session Fade ↔ Session Rise. Opposing members must not both
qualify from the same categorical state.

## 6. Pattern action contracts

Actions are attached only after qualification. Every action exposes a common
`evidence_summary` containing resolution status, sample and effective sample,
coverage, confidence, independent-group count where relevant, evidence keys,
limitations, and provenance versions. Resolution states are `resolved`,
`fallback`, `unresolved`, or `not_applicable` where the typed action permits it.

- **P01 Same Playbook:** up to three `deepen` and three `stretch` hero options;
  every option preserves named functional anchors and may abstain.
- **P02 Comfort Edge:** rank up to five sufficiently sampled heroes with
  confidence-adjusted, recency-weighted player-relative reliability; ranks 1–2
  form the reference core and ranks 3–5 receive supported learning reasons.
- **P03 Partial Transfer:** branch in strict order—direct summary difference,
  capability-expression hypothesis, unresolved. Direct evidence requires the
  named sample, confidence, and coverage gates. It may localize an observed gap
  but never claim replay-level cause.
- **P04 Versatile Core:** map core heroes to reviewed jobs, summarize strong,
  single-point, thin, and missing coverage, and recommend at most one next tool
  plus two alternatives only when a real gap clears the gates.
- **P05 Proven Flexibility:** select the strongest active rolling seven-day
  window or return distributed flexibility; expose roster, jobs, repeat proof,
  and distribution evidence.
- **P06/P07:** use same-session, leave-session-out comparable Recovery evidence
  plus the selected Familiarity or Tempo movement. Do not say resilience, tilt,
  confidence, choking, or intent.
- **P08 Controlled Presence:** localize the cleanest confidence-gated hero,
  function, role, or overall context; do not infer positioning skill,
  discipline, personality, or the value of a death.
- **P09 Presence Tax:** classify the supported concentration as job-shaped,
  hero-specific, cross-context, or unresolved. A localized result may request
  Deep Analysis, but summary history cannot explain what deaths bought or why
  they happened.
- **P10/P11:** expose a session-balanced G1/G2/G3/G4/G5+ curve, the earliest
  persistent breakpoint or gradual/unresolved state, companion signals, and
  explicit limits against fatigue, warm-up, momentum, or stop-time claims.

Concrete examples must be generated from actual sufficient evidence. When no
example clears the applicable sample, coverage, confidence, and reliability
gates, the action must abstain or show its fallback state.

### 6.1 Semantic outcome and copy contract

The active v5.2 meaning layer is finite and separate from presentation prose:

- `pattern-outcomes-5.2.0` registers 32 semantic outcome branches across P01–P11.
- `hero-recommendations-semantic-1.1.0` registers 14 recommendation IDs,
  including the shared `HR_PRACTICE_FALLBACK` and the P01 specialist branch.
- `free-dna-semantic-copy-5.2.0` supplies the active branch copy for every
  outcome and recommendation ID.
- `free-dna-copy-5.4.0` remains the legacy 11-record presentation catalog for
  historical snapshots and compatibility reads.

The API keeps the legacy `outcome_id`, `recommendation_id`, and `deep_dive_id`
alongside `semantic_outcome_id`, `semantic_recommendation_id`, and their
semantic versions. Active pages resolve semantic IDs; historical snapshots
continue to resolve the legacy catalog. Copy is deterministic and server-owned;
the browser never synthesizes a missing branch.

## 7. Hero-intelligence dependencies

Hero-facing actions use versioned editorial artifacts rather than inventing
meaning from hero IDs. The shared layer includes:

- reviewed top-level jobs and capability-expression tags;
- a functional relationship graph for similarity, adjacency, and stretch;
- matchup and teammate-synergy layers where the claim requires them;
- a situation taxonomy for player-facing reasons;
- deterministic, versioned provenance and validation for all 127 heroes in the
  active full-roster semantic freeze. The ten-hero pilot remains a historical
  review input, not the active denominator. Structural taxonomy adaptation is
  retained only as an explicit compatibility fallback when a generated record
  is unavailable or unapproved.

The Hero Portfolio is evaluated independently from Element scores. It may
support action recommendations but must not silently redefine Element or
Pattern qualification.

## 8. Report and Figma presentation contract

The reviewed Figma knowledge base represents all 18 Element cards and all 11
Pattern cards. Element documentation uses identity, a five-zone spectrum,
player-facing zone copy, evidence lens, limits, and a relationship network.
Pattern documentation uses a Tier A/B frame, observable evidence, meaning,
action module, guardrail, transparency, and Element ingredients.

The active comprehension check is the Figma section
[`239:2` — V5.2 Semantic Branch QA](https://www.figma.com/design/D3uhn7WPXFsX1DiCIVklyg/Report?node-id=239-2).
Its nine compact production-copy boards cover recommendation found/no trusted
recommendation, job-shaped/unresolved Presence Tax, stable/gradual Session
Fade, real/no functional outlier, and all four Pool Evolution outcomes. Each
board preserves the shipped hierarchy: conclusion, visual proof, meaning,
action, then optional evidence details.

Canonical Pattern frame mapping:

| Pattern | Figma node |
|---|---|
| P01 Same Playbook | `60:2` |
| P02 Comfort Edge | `60:51` |
| P03 Partial Transfer | `60:100` |
| P04 Versatile Core | `60:201` |
| P05 Proven Flexibility | `60:250` |
| P06 Bounceback | `60:351` |
| P07 Performance Slide | `150:46` |
| P08 Controlled Presence | `60:400` |
| P09 Presence Tax | `60:452` |
| P10 Session Fade | `60:504` |
| P11 Session Rise | `60:553` |

Relevant revised Element frames include E16 Drift `2:348` and E18 Recovery
`150:91`. The report UI must render server-owned action discriminators for all
P01–P11, expose required and modifier ingredients, show evidence and limits,
and remain keyboard and reduced-motion accessible. Visual implementation may
adapt Figma to the existing React/CSS system, but it must preserve this content
hierarchy and must not turn illustrative Figma values into product data.

## 9. Version and compatibility contract

Current versions are:

| Contract | Version |
|---|---|
| Behavior model | `behavior-model-5.2.0` |
| Element registry | `free-elements-5.2.0` |
| Pattern registry | `free-patterns-5.1.0` |
| Pattern actions | `pattern-actions-5.1.0` |
| Context baseline | `context-baseline-1.0.0` |
| Report schema | `free-dna-report-5.2.0` |
| Story | `free-story-5.3.0` |
| Pattern presentation | `pattern-presentation-5.2.0` |
| Model content | `free-dna-model-5.2.0` |
| Legacy copy content | `free-dna-copy-5.4.0` |
| Semantic copy content | `free-dna-semantic-copy-5.2.0` |
| Semantic outcome branches | `pattern-outcomes-5.2.0` (32 IDs) |
| Semantic recommendations | `hero-recommendations-semantic-1.1.0` (14 IDs) |
| Hero knowledge schema | `hero-knowledge-schema-1.0.0` |
| Hero semantics rules | `hero-semantics-5.2.0` |
| Hero knowledge snapshot | `hero-knowledge-semantic-freeze-full-roster-v1` (127 approved records) |
| Hero semantic vocabulary | `hero-semantics-full-roster-v1` |
| Hero knowledge manifest | `services/api/app/heroes/data/hero-knowledge-manifest.json` |
| Historical pilot snapshot | `hero-knowledge-semantic-freeze-pilot-v1` / `hero-semantics-pilot-v1` |
| Semantic outcome fixtures | `tests/fixtures/semantic_freeze/pattern-outcome-cases.json` |

Compatibility sources are explicit: semantic outcome and recommendation IDs
come from `services/api/app/behavior/outcomes.py` and
`services/api/app/heroes/recommendations.py`; active branch copy comes from
`services/api/app/content/free_dna/semantic_en.json`; legacy presentation copy
comes from `services/api/app/content/free_dna/en.json`; and the active full-
roster hero snapshot is selected through the checked-in manifest rather than a
runtime network call. The semantic outcome fixture covers all P01–P11
branches; hero source fixtures remain under `tests/fixtures/hero_knowledge/`.

Current snapshots carry these versions and the compatibility fingerprint.
Historical v4, v5.0, and v5.1 snapshots remain readable with their original
versions and without additive v5.2 semantic fields. Readers must not relabel
historical Pattern keys or reinterpret old evidence under the current
methodology. The full compatibility map, including taxonomy and source
snapshot versions, is maintained in [Hero knowledge](hero-knowledge.md).

## 10. Retired and reserved identities

The following are not active current-model Patterns:

| Historical identity | Current treatment |
|---|---|
| `stable_style` | retired; no replacement alias |
| `selective_closer` | retired; no replacement alias |
| `loss_response` | retired; replaced conceptually by the Recovery model, not aliased |
| `heavy_exposure` | retired name; historical compatibility maps to `presence_tax` only where required |
| `session_hold` | retired and reserved |
| `assist_presence` | retired and reserved |

Retired identities must not collide with active registry keys or return through
ranking, copy, generated catalogs, fixtures, or current API payloads.

## 11. Historical checkpoint reconciliation

The checkpoint documents are historical inputs, not simultaneous authorities or
active implementation plans:

- `dota-dna-pattern-actions-checkpoint-p01-p03.md` locks the early P01–P03
  action model but predates later Pattern and Recovery work.
- `dota-dna-pattern-actions-checkpoint-p01-p09-presence-revamp.md` supersedes
  the early checkpoint for P04–P09, removes Stable Style and Selective Closer,
  replaces Loss Response with Bounceback/Performance Slide, and replaces Heavy
  Exposure with Presence Tax.
- `dota-dna-final-consolidated-implementation-plan.md` adds the final 18
  Elements, P10/P11, data, baseline, qualification, selection, versioning, and
  compatibility contracts.
- `free-dna-v5-figma-code-alignment-implementation-plan.md` is the final audit
  specification for bringing runtime behavior to the reviewed Figma model.

Where an early checkpoint conflicts with a later locked revision, the later
revision recorded in this SSOT wins. Historical names remain reserved only for
safe snapshot compatibility.

## 12. Repository alignment result

At baseline `3670c49` (`v5.2 sol+luna`), the repository aligns with this SSOT:

- registries enforce exactly 18 Elements and 11 Patterns;
- shared half-open zone boundaries are centralized;
- all reviewed qualification clauses and Element gates are implemented;
- P06/P07 selected-clause authority and deterministic tie-breaking are present;
- shared leave-group-out context baselines and session-clustered Recovery are
  implemented;
- all 11 typed actions expose the common evidence envelope;
- P03 branch gates, presence actions, and session-curve actions are present;
- current and historical schema versions are both accepted as intended;
- React renders every active action discriminator and does not recompute it;
- retired keys are reserved and absent from the active registry.
- semantic outcomes, recommendations, hero-knowledge provenance, and branch
  copy are carried as additive versioned fields.

Focused verification on 2026-08-22 passed 97 tests covering registry,
qualification, action, context-baseline, Recovery, copy, and report contracts.
The checked-in alignment report records the broader quality run: 167 unit tests
passed with two skips, plus lint, typecheck, contract, integration, end-to-end,
taxonomy, catalog, docs, and client-generation checks.

No current code deviation requiring a remediation plan was found in this audit.

## 13. Change discipline

Any change to an active Element, Pattern, zone label, qualification clause,
baseline hierarchy, action evidence contract, or public interpretation must:

1. update the reviewed Figma knowledge base and this SSOT;
2. change the relevant registry or methodology version;
3. preserve historical snapshot reads;
4. update API/client contracts if serialized fields change;
5. add exact-boundary, truth-table, abstention, and regression tests;
6. regenerate catalogs and fingerprints;
7. pass unit, contract, integration, web, taxonomy, docs, and client checks.

Do not create a second current-model definition in prose, UI code, fixtures, or
generated documentation. Derive those artifacts from the registries and typed
report contract wherever practical.
