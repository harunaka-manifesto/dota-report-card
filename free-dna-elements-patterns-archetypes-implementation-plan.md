# Free DNA Behavioral Model Revamp — Technical Implementation Plan

**Target agent:** GPT Luna  
**Repository:** `harunaka-manifesto/dota-report-card`  
**Target branch baseline:** `main`, inspected 2026-08-17  
**Primary scope:** Free DNA  
**Architecture goal:** replace the current “eight scored dimensions + one global archetype + separately-computed findings” model with a coherent, versioned behavioral ontology:

```text
OpenDota summary history
  → normalized observations
  → private low-level features
  → ELEMENTS (atomic, interpretable tendencies)
  → PATTERNS (multi-element relationships / contradictions)
  → CONTEXT ARCHETYPES (one result per archetype group)
  → FINDINGS / STORY (editorial selection and copy)
  → immutable public report
```

The implementation must preserve the current Free DNA unit-economics boundary: **one bounded player-history read; zero individual match-detail reads; zero replay parse requests**. Deep analysis is not being implemented in this project, but the semantic model, result contracts, registries, provenance model, and documentation must be designed so richer paid evidence can plug into the same hierarchy later without replacing the Free system.

---

## 0. Executive instruction to Luna

Do not treat this as a cosmetic rename of `dimensions` to `elements`.

This is a logic and architecture migration. The end state must have one canonical inference path in which:

1. raw OpenDota observations never directly produce public personality claims;
2. private features are reusable numerical facts, not public interpretations;
3. each Element answers one narrow behavioral question;
4. each Pattern combines at least two Elements or independently-supported semantic signals;
5. each Archetype is contextual and belongs to a named archetype group;
6. Findings are editorial stories selected from upstream Elements/Patterns/Archetypes and **must not re-implement their own competing analytics**;
7. Free and paid/deep capabilities are explicit in machine-readable definitions;
8. every semantic artifact has evidence, coverage, confidence, limitations, and a version;
9. public copy describes observed behavior, not psychology or hidden intent;
10. owner-facing documentation is generated or validated from the same registries as production logic so documentation cannot silently drift from code.

Implement this comprehensively across backend contracts, report assembly, API schemas, API client types, the active Free renderer, tests, README, new `ARCHITECTURE.md`, and the new owner model catalog.

Do not redesign the entire visual language or product navigation in this work. Make the frontend compatible with and able to render the new model, but keep the focus on semantic/data architecture.

---

# 1. Current-state diagnosis

The repo already contains many strong pieces. Preserve the statistically careful work; reorganize its semantics.

## 1.1 Current Free DNA pipeline

`services/api/app/dna/pipeline.py` currently does roughly:

```text
summary matches
→ session inference
→ DnaFeatureSet
→ eight DimensionResult scores
→ one global archetype
→ hero identity
```

The eight dimensions are:

- breadth
- role
- adaptability
- activity
- orientation
- resilience
- endurance
- rhythm

Several of these are already good atomic behavioral measurements, but the names sometimes imply more than the actual measurement:

| Current name | What it actually measures |
|---|---|
| `breadth` | hero-pool distribution/concentration |
| `role` | credible lane/role-hint breadth/anchoring |
| `adaptability` | familiar vs off-pool performance transfer |
| `activity` | kills + assists per minute, optionally role-adjusted |
| `orientation` | kill share within kills + assists, optionally role-adjusted |
| `resilience` | next-match performance after losses vs wins within sessions |
| `endurance` | within-session performance slope |
| `rhythm` | session length/duration shape |

The underlying implementations contain valuable protections that should be retained: sample gates, coverage checks, role adjustment, shrinkage, robust statistics, chronological evaluation splits, session sensitivity checks, and explicit confounders.

## 1.2 Current duplicate semantic paths

There are currently multiple systems that can independently create behavioral meaning:

- `services/api/app/dna/dimensions/*`
- `services/api/app/dna/archetypes/*`
- `services/api/app/patterns/*`
- `services/api/app/findings/*`
- hero identity / taxonomy logic

The current `app/patterns/detector.py` derives summary observations directly from summary features. The newer `app/findings/*` system then creates additional cross-signal stories from dimensions, DNA features, summary patterns, session signals, and hero signals.

This produces a conceptual problem: the product has no single source of truth for whether something is an atomic trait, a composite relationship, an archetype, or just editorial wording.

The migration must eliminate that ambiguity.

## 1.3 Current public contract

New reports currently emit `free-dna-report-2.0.0`. The public report exposes:

- `dimensions`
- one `archetype`
- `heroes`
- `findings`
- story/page data
- share payloads

The TypeScript API client and frontend explicitly distinguish v1 and v2 reports. This is useful: **do not mutate v2 semantics in place**. Introduce a v3 contract.

## 1.4 Current Free data boundary

The summary normalizer already models the fields Free is allowed to use, including:

- hero ID / hero variant
- start time and duration
- side / outcome
- game and lobby type
- K / D / A
- party size
- lane / lane-role / roaming hints
- patch / version
- skill bracket
- region
- leaver status

It correctly treats `lane_role` as a lane/context hint rather than fabricating exact position 1–5 certainty. Preserve this principle everywhere.

---

# 2. Target semantic model

## 2.1 Definitions

### Observation

A normalized source fact.

Examples:

- hero 86 was picked
- match lasted 2,714 seconds
- player had 5 kills, 8 deaths, 19 assists
- match started at timestamp X
- credible lane-role hint was `offlane`

Observations never contain interpretive language.

### Feature

A private reusable calculation derived from observations.

Examples:

- normalized hero entropy
- top-5 hero share
- `(kills + assists) / minute`
- session index
- role entropy
- familiar hero set
- per-match performance proxy

Features are engineering/data-science primitives. They do not need to be understandable or exposed to users.

### Element

A narrow, user-interpretable behavioral measurement answering one question.

Examples:

- Hero Pool Breadth
- Toolkit Breadth
- Combat Involvement
- Finisher Orientation
- Death Exposure
- Off-Pool Performance
- Late-Session Performance

An Element may use multiple raw features internally, but it must resolve to **one behavioral concept**.

### Dimension

A taxonomy/grouping bucket. A Dimension is **not automatically a scored personality axis**.

Examples:

- Hero Identity
- Role Identity
- Combat Expression
- Economy
- Map & Objectives
- Risk & Survival
- Adaptability
- Consistency & Form
- Session Response
- Progression

Do not calculate an arbitrary aggregate “Hero Identity = 78” unless a future validated product need explicitly defines one. Dimensions exist primarily to organize Elements and Patterns.

### Pattern

A composite relationship or contradiction that requires at least two Elements or two independently-supported semantic signals.

Examples:

- Broad Pool, Narrow Toolkit
- Activity Travels Better Than Results
- High Involvement, Controlled Exposure
- Losses Change Picks More Than Pace
- Long Session Tax

Patterns are the primary “I did not know that” analytical layer.

### Context Archetype

A contextual summary within one archetype group. A player receives zero or one result per group, depending on evidence quality.

Examples:

- Hero Identity → Craftsman
- Combat Expression → Enabler
- Session Style → Grinder

There is no longer one global archetype pretending to summarize the whole player.

### Finding / Story

An editorially-ranked narrative generated from already-computed Elements, Patterns, and Archetypes.

A Finding decides **what to tell the user**, not **what is statistically true**.

Example:

- Pattern truth: `activity_travels_better_than_results`
- Editorial headline: “Your mechanics travel. Your results don’t—yet.”

The Finding layer may select, suppress, sequence, and phrase upstream truth. It must not recalculate the truth independently.

---

# 3. Non-negotiable architecture invariants

1. **Free stays summary-only.** No code path reachable from Free Element/Pattern/Archetype evaluation may perform match-detail reads or request parsing.
2. **No runtime LLM writes analytical claims.** Production claims remain deterministic and catalog/template driven.
3. **No hidden psychology.** The model may describe observable response after a loss; it may not claim tilt, anger, confidence, trust, selfishness, leadership, anxiety, etc.
4. **No causal language from observational data.** Prefer “is associated with”, “changes”, “shows up”, “in these matches”, “when X happens” rather than “X causes Y”.
5. **No fake percentiles.** A 0–1 normalized Element score is not a population percentile unless it is explicitly backed by a versioned cohort distribution.
6. **Missing is not neutral.** Unavailable data produces unavailable Elements; it must not silently become score 0.5.
7. **Confidence is separate from score.** A strong measured tendency with weak evidence is still low-confidence.
8. **Patterns do not bypass Elements.** Composite inference must reference upstream semantic results, not rebuild duplicate raw formulas.
9. **Archetypes do not bypass Elements/Patterns.** Archetypes classify semantic results, not normalized matches directly.
10. **Findings do not bypass Patterns/Elements/Archetypes.** Findings are editorial composition only.
11. **Private provenance remains private.** Source match IDs may live in internal results but must be stripped at the public report boundary unless a separately-approved product feature explicitly exposes them.
12. **Every registry is versioned.** Any threshold, formula, prototype, label, source requirement, or public semantic change must participate in the analysis fingerprint.
13. **Old immutable reports remain readable.** v1/v2 validators and renderers remain supported through the migration.

---

# 4. Target package architecture

Create a tier-agnostic behavioral semantic package rather than burying the new model inside Free-specific `dna/dimensions` code.

Recommended structure:

```text
services/api/app/
  behavior/
    __init__.py
    models.py
    tiers.py
    dimensions.py
    evidence.py
    comparisons.py
    catalog.py

    elements/
      __init__.py
      models.py
      registry.py
      service.py
      free_summary/
        __init__.py
        hero_identity.py
        role_identity.py
        combat_expression.py
        risk_survival.py
        adaptability.py
        consistency_form.py
        session_response.py

    patterns/
      __init__.py
      models.py
      registry.py
      service.py
      free_summary.py

    archetypes/
      __init__.py
      models.py
      registry.py
      classifier.py
      free_v1.json          # optional if prototypes remain data-driven

  dna/
    pipeline.py             # Free orchestration adapter into behavior package
    features/               # retain current private summary feature extraction initially
    sessions.py
    ...

  findings/
    ...                     # refactor to consume behavior results, not recompute analytics
```

Do **not** force a risky rewrite of all low-level summary feature extraction at the same time. `DnaFeatureSet`, session inference, hero taxonomy, and carefully-tested scoring helpers may be reused as private inputs. The critical change is the semantic ownership boundary.

After v3 is stable, duplicate legacy summary-feature code may be consolidated separately.

---

# 5. Capability and product-tier model

Create explicit enums / literals.

```python
EvidenceTier = Literal[
    "summary_history",
    "match_detail",
    "parsed_replay",
]

ProductTier = Literal[
    "free",
    "paid",
]

ModelStatus = Literal[
    "active",
    "planned",
    "legacy",
]
```

If useful, represent capabilities more granularly:

```python
DataCapability = Literal[
    "summary.hero",
    "summary.outcome",
    "summary.kda",
    "summary.time",
    "summary.role_hint",
    "summary.party",
    "hero.taxonomy",
    "detail.economy",
    "detail.items",
    "parsed.teamfights",
    "parsed.objectives",
    "parsed.vision",
    "parsed.position",
    "parsed.timelines",
]
```

Every Element/Pattern/Archetype definition must state minimum evidence tier and required capabilities.

For this implementation, active production definitions are Free only. Planned paid definitions may be represented in the owner catalog and optional metadata catalog, but must not be returned as fake unavailable Free results unless there is a clear product requirement.

---

# 6. Shared result contracts

Create immutable typed domain models.

## 6.1 Evidence receipt

```python
@dataclass(frozen=True, slots=True)
class BehaviorEvidence:
    key: str
    value: float | int | str | bool | None
    unit: str
    denominator: int
    coverage: float
    confidence_score: float
    comparison: str | None = None
    source_match_ids: tuple[int, ...] = ()   # private only
```

Public serialization must remove `source_match_ids` unless intentionally allowed by a different API contract.

## 6.2 Element definition

```python
@dataclass(frozen=True, slots=True)
class ElementDefinition:
    key: str
    label: str
    dimension_key: str
    description: str
    user_question: str
    why_it_exists: str
    product_tier: ProductTier
    minimum_evidence_tier: EvidenceTier
    required_capabilities: tuple[str, ...]
    scorer_key: str
    minimum_sample: int
    minimum_coverage: float
    axis_left: str | None
    axis_right: str | None
    normalization_basis: str
    confounders: tuple[str, ...]
    copy_guardrails: tuple[str, ...]
    version: str
```

## 6.3 Element result

```python
@dataclass(frozen=True, slots=True)
class ElementResult:
    key: str
    dimension_key: str
    status: Literal["available", "limited", "unavailable"]
    score: float | None              # normalized 0..1 descriptive axis
    centered_score: float | None     # -1..1 convenience transform
    confidence: Literal["low", "moderate", "high", "unavailable"]
    confidence_score: float
    sample_size: int
    effective_sample_size: float
    coverage: float
    stability: float
    quality: float
    raw_metrics: dict[str, float | int | str | bool | None]
    evidence: tuple[BehaviorEvidence, ...]
    confounders: tuple[str, ...]
    missing_reasons: tuple[str, ...]
    methodology_version: str
```

`raw_metrics` is important. Patterns should be able to use named upstream metrics such as `delta`, `share`, or `mad` without reopening the raw match corpus.

## 6.4 Pattern definition / result

A Pattern definition must list its semantic dependencies.

```python
@dataclass(frozen=True, slots=True)
class PatternDefinition:
    key: str
    label: str
    description: str
    kind: Literal["identity", "contradiction", "edge", "leak", "trajectory", "style"]
    dimension_keys: tuple[str, ...]
    required_elements: tuple[str, ...]
    optional_elements: tuple[str, ...]
    minimum_element_confidence: float
    evaluator_key: str
    product_tier: ProductTier
    minimum_evidence_tier: EvidenceTier
    why_it_matters: str
    copy_guardrails: tuple[str, ...]
    version: str
```

```python
@dataclass(frozen=True, slots=True)
class PatternResult:
    key: str
    status: Literal["qualified", "suppressed", "unavailable"]
    direction: str | None
    strength: float
    confidence: str
    confidence_score: float
    element_keys: tuple[str, ...]
    evidence: tuple[BehaviorEvidence, ...]
    effect_metrics: dict[str, float | int | str | bool | None]
    confounders: tuple[str, ...]
    suppression_reasons: tuple[str, ...]
    methodology_version: str
```

Rules:

- every qualified Pattern must reference at least two distinct Elements unless an explicitly-reviewed future pattern uses one Element plus a separately-derived external semantic signal such as hero taxonomy;
- prefer at least two distinct evidence families for high-confidence patterns;
- suppress rather than soften unsupported patterns.

## 6.5 Context archetype contracts

```python
@dataclass(frozen=True, slots=True)
class ArchetypeGroupDefinition:
    key: str
    label: str
    description: str
    product_tier: ProductTier
    required_elements: tuple[str, ...]
    optional_elements: tuple[str, ...]
    optional_patterns: tuple[str, ...]
    minimum_reliable_elements: int
    minimum_confidence_score: float
    prototypes: tuple[ArchetypePrototype, ...]
    version: str
```

```python
@dataclass(frozen=True, slots=True)
class ContextArchetypeResult:
    group_key: str
    key: str
    label: str
    fit: float
    confidence: str
    runner_up: dict | None
    descriptors: tuple[dict, ...]
    contributing_elements: tuple[dict, ...]
    contributing_patterns: tuple[str, ...]
    explanation_evidence: tuple[str, ...]
    classifier_version: str
```

If evidence is insufficient or winner/runner-up margin is too small, return a neutral group-specific fallback such as `unclassified` / `developing`, not a forced archetype.

---

# 7. Dimension taxonomy

Create a canonical dimension registry. Dimensions are organizational domains.

| Key | Label | Free status | Deep status |
|---|---|---|---|
| `hero_identity` | Hero Identity | active | enrich later |
| `role_identity` | Role Identity | active | enrich later |
| `combat_expression` | Combat Expression | active, summary-limited | major paid enrichment |
| `economy` | Economy | none in Free | planned paid |
| `map_objectives` | Map & Objectives | none in Free | planned paid |
| `risk_survival` | Risk & Survival | limited Free | major paid enrichment |
| `adaptability` | Adaptability | active | enrich later |
| `consistency_form` | Consistency & Form | active | enrich later |
| `session_response` | Session Response | active | enrich later |
| `progression` | Progression | basic future/free extension | paid/free enrichment later |

Do not expose empty paid dimensions as if the Free report failed to calculate them. The owner catalog may show them as planned.

---

# 8. Free DNA Element catalog to implement

Implement the following **23 Free Elements** as v1 of the new model. Where current logic already exists, migrate/refactor it rather than rewriting it gratuitously.

All thresholds below are initial production gates. Keep them declarative/versioned and testable so they can be recalibrated later.

## 8.1 Hero Identity

### E01 `hero_pool_breadth` — Hero Pool Breadth

**Question:** How distributed is the player’s hero usage rather than concentrated on a small pool?  
**Source:** summary `hero_id`.  
**Reuse:** current `breadth` logic.  
**Initial method:** retain the current combination of top-5 share, normalized hero entropy, and effective hero count.  
**Minimum:** 30 eligible hero rows.  
**Axis:** `Specialized` → `Broad`.  
**Why:** broad versus specialist hero identity is foundational and highly stable in cheap history.

### E02 `hero_pool_stability` — Hero Pool Stability

**Question:** Does the player keep returning to a similar hero distribution over time?  
**Source:** `hero_id`, `start_time`.  
**Method:** compare recent and prior hero distributions using a bounded distribution similarity metric such as normalized Jensen-Shannon similarity; include sensitivity across 50/100/full windows when possible.  
**Minimum:** 60 dated matches with at least 25–30 per comparison window.  
**Axis:** `Changing` → `Stable`.  
**Do not:** label low stability as “inconsistent” or “indecisive”.

### E03 `hero_exploration_rate` — Hero Exploration

**Question:** How often does the player intentionally/observably leave the previously-established pool?  
**Source:** `hero_id`, chronology.  
**Method:** establish familiar heroes on historical/training rows only; measure off-pool share in later evaluation rows. Never define familiarity using future outcomes.  
**Minimum:** 60 history rows and at least 20 evaluation rows.  
**Axis:** `Familiar picks` → `Exploratory picks`.

### E04 `toolkit_breadth` — Toolkit Breadth

**Question:** Are the player’s heroes strategically/mechanically diverse, or are many picks variations of the same toolkit?  
**Source:** summary `hero_id` + versioned hero taxonomy.  
**Method:** match-weighted entropy/effective count across taxonomy toolkit/trait families. Avoid counting every trait as independent if the taxonomy is multi-label; define a stable toolkit aggregation rule.  
**Minimum:** 30 eligible matches; taxonomy coverage >= 0.80.  
**Axis:** `Narrow toolkit` → `Diverse toolkit`.  
**Why:** enables “many heroes, same toolkit” insights that raw hero count misses.

### E05 `signature_dependence` — Signature Dependence

**Question:** How much better does performance hold on established signature/comfort heroes than elsewhere?  
**Source:** hero identity + per-match performance proxy + role hints.  
**Method:** familiar/signature vs remainder comparison; role-stratify when cells are sufficient; apply shrinkage.  
**Minimum:** target 15+ familiar/signature and 15+ comparison matches; unavailable if cells are too small.  
**Axis:** `Little dependence` → `High dependence`.  
**Do not:** describe high dependence as a flaw by default.

### E06 `post_loss_familiarity_shift` — Post-Loss Familiarity Shift

**Question:** Does hero selection become more familiar after a loss?  
**Source:** sessions, outcomes, familiar hero set.  
**Method:** compare `P(next hero is familiar | previous game loss)` vs the corresponding post-win rate within valid session transitions; preserve session-gap sensitivity.  
**Minimum:** 15 post-loss and 15 post-win valid transitions, 10+ independent sessions.  
**Axis:** `Explores after losses` → `Returns to familiarity after losses`.  
**Language:** selection response only. Never call this “fear”, “trust”, or “tilt”.

## 8.2 Role Identity

### E07 `role_breadth` — Role Breadth

**Question:** How concentrated are credible role/lane-context hints?  
**Source:** `lane_role`, `lane`, `is_roaming` through existing role-confidence normalizer.  
**Reuse:** current `role` dimension logic.  
**Minimum:** 30 credible rows and coverage >= 0.40.  
**Axis:** `Role-anchored` → `Role-flexible`.  
**Caveat:** these are summary role hints, not exact Dota positions.

### E08 `role_switch_rate` — Role Switching

**Question:** How often does the credible role context change between adjacent games?  
**Source:** dated role-eligible rows, preferably within sessions for the primary measure.  
**Method:** share of valid consecutive role pairs whose role hint changes; report within-session and all-history metrics separately in `raw_metrics`.  
**Minimum:** 20 valid role transitions.  
**Axis:** `Usually same role context` → `Frequently switches role context`.

## 8.3 Combat Expression

### E09 `combat_involvement` — Combat Involvement

**Question:** How frequently is the player involved in kills relative to time played?  
**Source:** K + A + duration; role hints for adjustment.  
**Reuse:** current `activity` logic.  
**Method:** `(kills + assists) / minutes`, robust center, role-adjust where credible; provisional baseline must cap confidence as current code does.  
**Minimum:** 30 eligible K/A-duration rows.  
**Axis:** `Lower involvement` → `Higher involvement`.

### E10 `finisher_orientation` — Finisher Orientation

**Question:** When involved in kills, how often is the player the killer versus the assister?  
**Source:** K + A, role hints.  
**Reuse:** current `orientation` logic.  
**Method:** aggregate `kills / (kills + assists)` with role-adjusted expectation and shrinkage.  
**Minimum:** 30 matches and at least 100 total involvement events.  
**Axis:** `Assist-oriented` → `Kill-oriented`.  
**Do not:** call this selfishness, leadership, playmaking, or initiation.

## 8.4 Risk & Survival

### E11 `death_exposure` — Death Exposure

**Question:** How frequently does the player die relative to time played and role context?  
**Source:** deaths, duration, role hints.  
**Method:** deaths per 10 minutes; robust role-adjusted residual where role sample allows, otherwise self-relative/overall normalization. Any provisional role baseline must cap confidence.  
**Minimum:** 30 eligible rows.  
**Axis:** `Lower exposure` → `Higher exposure`.  
**Do not:** automatically equate deaths with recklessness; some roles/heroes structurally die more.

## 8.5 Adaptability

### E12 `off_pool_performance` — Off-Pool Performance

**Question:** How well does performance transfer away from the player’s established hero pool?  
**Source:** hero familiarity, outcome, performance proxy, role hints.  
**Reuse:** the statistically careful portions of current `adaptability`.  
**Method:** chronological training/evaluation split; compare familiar versus off-pool performance; role-stratify when possible; shrink small cells.  
**Minimum:** target 20 familiar + 20 off-pool evaluation observations; retain current safe fallback if justified.  
**Axis:** `Drops off-pool` → `Travels off-pool`.

### E13 `off_pool_activity_stability` — Off-Pool Activity Stability

**Question:** Does combat involvement remain similar when the player leaves familiar heroes?  
**Source:** familiar/off-pool split + K/A/min.  
**Method:** robust standardized delta between familiar and off-pool involvement. Convert absolute delta into a “travels well” stability score while preserving signed delta in `raw_metrics`.  
**Minimum:** 12+ usable rows in both groups.  
**Axis:** `Activity changes off-pool` → `Activity travels off-pool`.

### E14 `off_role_performance` — Off-Role Performance

**Question:** How well does performance transfer outside established credible role contexts?  
**Source:** credible role hints + performance proxy + chronology.  
**Method:** define familiar roles without looking at future outcomes, then evaluate familiar-role vs off-role performance; stratify by hero familiarity where enough support exists.  
**Minimum:** 12+ usable rows per group and role coverage >= 0.50.  
**Axis:** `Drops off-role` → `Travels off-role`.  
**Caveat:** summary role hints limit ceiling; confidence should generally remain moderate until richer evidence exists.

## 8.6 Consistency & Form

### E15 `performance_volatility` — Performance Volatility

**Question:** How variable is the player’s observable match-to-match performance proxy?  
**Source:** existing per-match performance proxy.  
**Method:** robust MAD/IQR-based dispersion; optionally residualize by credible role before dispersion; avoid standard deviation sensitivity to extreme matches.  
**Minimum:** 30 usable matches.  
**Axis:** `Steadier` → `More variable`.  
**Do not:** call volatility “inconsistency” unless copy clearly says observed results/performance.

### E16 `recent_form_shift` — Recent Form Shift

**Question:** Is recent observable performance materially different from the preceding window?  
**Source:** chronology + performance proxy.  
**Method:** compare approximately recent 20 vs prior 40, with robust mean/median and shrinkage. Preserve direction.  
**Minimum:** at least 15 recent and 30 prior usable matches.  
**Axis:** `Recent decline` → `Recent improvement`; neutral center when no material change.

### E17 `recent_activity_shift` — Recent Activity Shift

**Question:** Has combat involvement changed recently even if results changed?  
**Source:** chronology + role-adjusted K/A/min.  
**Method:** recent vs prior robust delta, role-adjust when possible.  
**Minimum:** 15 recent and 30 prior eligible activity rows.  
**Axis:** `Recently less involved` → `Recently more involved`.

### E18 `long_game_performance_shift` — Long-Game Performance Shift

**Question:** Does observable performance differ materially in long games?  
**Source:** duration + outcome/performance proxy.  
**Method:** compare a long-game group (initially >=45m) to a shorter reference group (initially <=35m), excluding middle if useful to improve contrast; preserve both rates and robust performance delta.  
**Minimum:** 10+ usable matches per group; prefer 15+.  
**Axis:** `Falls in long games` → `Improves in long games`.  
**Caveat:** game duration is endogenous to both teams and game state.

## 8.7 Session Response

### E19 `session_length_tendency` — Session Length Tendency

**Question:** Does the player usually play short bursts or long sessions?  
**Source:** start times + inferred sessions.  
**Reuse:** the descriptive, outcome-free parts of current `rhythm`.  
**Method:** median matches/session, p75, share 5+ sessions, median elapsed session duration; retain 60/90/120-minute session-gap sensitivity.  
**Minimum:** 10 sessions and 25 dated matches.  
**Axis:** `Short bursts` → `Long sessions`.

### E20 `late_session_performance` — Late-Session Performance

**Question:** Does observable performance rise or fall as a session gets longer?  
**Source:** session position + performance proxy.  
**Reuse:** current `endurance` slope logic.  
**Minimum:** 12 independent multi-game sessions; enough game-one and game-three-plus observations.  
**Axis:** `Declines later` → `Improves later`.  
**Caveat:** stopping behavior and role/hero mix can confound this.

### E21 `post_loss_performance_response` — Post-Loss Performance Response

**Question:** How does next-match observable performance differ after a loss versus after a win?  
**Source:** valid within-session transitions.  
**Reuse:** current `resilience` measurement, renamed semantically.  
**Minimum:** 15 post-win + 15 post-loss transitions and 10+ independent sessions.  
**Axis:** `Lower after losses` → `Higher after losses`.  
**Never:** name the underlying metric “mental resilience” or “tilt resistance”.

### E22 `post_loss_activity_shift` — Post-Loss Activity Shift

**Question:** Does combat involvement change after a loss?  
**Source:** valid within-session transitions + K/A/min.  
**Method:** compare next-game role-adjusted activity after losses vs wins; robust delta and session sensitivity.  
**Minimum:** 15 valid transitions in each comparison group.  
**Axis:** `Slower after losses` → `More active after losses`.

### E23 `post_loss_death_shift` — Post-Loss Death Exposure Shift

**Question:** Does death exposure change after a loss?  
**Source:** valid session transitions + deaths/minute, role hints.  
**Method:** compare next-game death exposure after loss vs after win; role-adjust where viable.  
**Minimum:** 15 valid transitions per group.  
**Axis:** `Lower exposure after losses` → `Higher exposure after losses`.  
**Why:** enables safe “pace vs exposure” distinctions without claiming emotion.

---

# 9. Element scoring conventions

## 9.1 Score meaning

`score` is a bounded **descriptive axis coordinate**, not a grade.

- `0.0` = strong left-side tendency
- `0.5` = neutral/near expected
- `1.0` = strong right-side tendency

Do not label 1.0 as good or 0.0 as bad unless the specific Element is explicitly directional and product-approved.

## 9.2 Normalization basis

Each Element definition must declare one of:

- `bounded_absolute`
- `self_relative`
- `role_adjusted_provisional`
- `cohort_calibrated`
- `window_comparison`
- `conditional_comparison`

This must appear in the owner catalog.

## 9.3 Confidence

Reuse the best existing confidence machinery where possible. Confidence should combine:

- sample sufficiency
- effective sample size
- field coverage
- stability/sensitivity
- role/taxonomy quality where applicable
- confounder penalties

Do not let a large sample overcome structurally poor data quality.

## 9.4 Provisional baselines

Current role baselines are provisional. Preserve the current behavior of capping confidence for claims dependent on those cells until a versioned cohort-calibrated baseline exists.

---

# 10. Free DNA Pattern catalog to implement

Implement a finite v1 Pattern registry. Do **not** create a generic combinatorial “test every pair of Elements” engine in production. A finite reviewed registry controls multiple-comparison risk, product quality, copy quality, and explainability.

Every Pattern below needs explicit thresholds, gates, confidence rules, and deterministic tie-breaking in the registry/evaluator.

## P01 `broad_pool_narrow_toolkit` — Broad Pool, Narrow Toolkit

**Requires:** `hero_pool_breadth`, `toolkit_breadth`.  
**Meaning:** player uses many heroes but they cluster into a smaller strategic/mechanical toolkit.  
**Initial qualification:** breadth clearly above neutral; toolkit breadth clearly below neutral; both moderate+ confidence; taxonomy coverage >=0.80.  
**Likely finding:** “You have a big hero pool and a surprisingly small playstyle pool.”

## P02 `broad_pool_narrow_safety_zone` — Broad Pool, Narrow Safety Zone

**Requires:** `hero_pool_breadth`, `off_pool_performance`.  
**Optional:** `post_loss_familiarity_shift`, `signature_dependence`.  
**Meaning:** the player selects broadly but results/performance are meaningfully safer inside an established subset.  
**Do not:** imply fear or lack of confidence.

## P03 `specialist_transferable_style` — Specialist, Transferable Style

**Requires:** `hero_pool_breadth`, `off_pool_activity_stability`.  
**Optional:** `off_pool_performance`.  
**Meaning:** narrow hero selection, but observable combat activity changes little when leaving the pool.  
**Value:** distinguishes preference from inability.

## P04 `role_anchor_hero_explorer` — Role Anchor, Hero Explorer

**Requires:** `role_breadth`, `hero_pool_breadth`.  
**Meaning:** many hero choices inside a relatively stable role context.  
**Value:** answers whether identity is more role-shaped than hero-shaped.

## P05 `hero_anchor_role_flex` — Hero Anchor, Role Flex

**Requires:** `hero_pool_breadth`, `role_breadth`.  
**Meaning:** relatively narrow hero identity but wider role-context use.  
**Only qualify:** when role coverage is strong enough that this is not a lane-role artifact.

## P06 `signature_strength_with_tax` — Signature Strength With a Tax

**Requires:** `signature_dependence`, `off_pool_performance`.  
**Optional:** `hero_exploration_rate`.  
**Meaning:** signature heroes are a real strength, but leaving them carries a measurable cost.  
**Editorial rule:** frame the signature strength first, then the constraint.

## P07 `activity_travels_better_than_results` — Activity Travels Better Than Results

**Requires:** `off_pool_activity_stability`, `off_pool_performance`.  
**Meaning:** combat involvement remains similar off-pool while results/performance fall.  
**Interpretation:** suggests the missing mechanism is not simply “you stop participating”; Deep Scan can later investigate lane, item timing, fight arrival, etc.  
**This pattern should emit a future Deep diagnostic hook.**

## P08 `high_involvement_controlled_exposure` — High Involvement, Controlled Exposure

**Requires:** `combat_involvement`, `death_exposure`.  
**Meaning:** player is frequently involved without correspondingly high death exposure.  
**Safe editorial idea:** “You show up a lot without paying for it as often.”  
**Do not:** call it aggression unless wording is explicitly defined as observable combat activity.

## P09 `high_involvement_high_exposure` — High Involvement, High Exposure

**Requires:** `combat_involvement`, `death_exposure`.  
**Optional:** `post_loss_death_shift`.  
**Meaning:** high participation comes with high death exposure.  
**Actionability:** later Deep can investigate timing/location/death cost.

## P10 `selective_finisher` — Selective Finisher

**Requires:** `combat_involvement`, `finisher_orientation`, `death_exposure`.  
**Meaning:** lower/moderate event volume but high kill share and controlled exposure.  
**Do not:** equate with kill stealing; this is only an event-distribution description.

## P11 `losses_change_picks_more_than_pace` — Losses Change Picks More Than Pace

**Requires:** `post_loss_familiarity_shift`, `post_loss_activity_shift`.  
**Optional:** `post_loss_performance_response`.  
**Meaning:** hero selection moves toward familiarity after losses while combat activity stays broadly similar.  
**Replace legacy “losses change trust more than pace” language.** “Trust” is not observable.

## P12 `losses_change_pace_more_than_picks` — Losses Change Pace More Than Picks

**Requires:** `post_loss_familiarity_shift`, `post_loss_activity_shift`.  
**Optional:** `post_loss_death_shift`.  
**Meaning:** activity changes materially after losses while familiarity changes little.

## P13 `long_session_tax` — Long Session Tax

**Requires:** `session_length_tendency`, `late_session_performance`.  
**Optional:** `post_loss_performance_response`.  
**Meaning:** player commonly reaches long sessions and performance declines later.  
**Actionability:** preserve the existing experiment concept around game-four opt-in / stopping rule.

## P14 `marathon_stability` — Marathon Stability

**Requires:** `session_length_tendency`, `late_session_performance`.  
**Meaning:** long sessions with stable or improving late-session performance.  
**Value:** strength counterpart to `long_session_tax`.

## P15 `form_identity_divergence` — Form Changed, Style Didn’t

**Requires:** `recent_form_shift`, `hero_pool_stability`, `recent_activity_shift`.  
**Meaning:** results/performance changed recently while hero identity and involvement remain relatively stable.  
**Value:** supports “your form changed more than your style” instead of incorrectly diagnosing a playstyle breakdown.

---

# 11. Pattern qualification and ranking

Pattern qualification is analytical. Finding ranking is editorial. Keep them separate.

## 11.1 Pattern qualification

A Pattern should only become `qualified` if:

- all required Elements are available/limited according to the definition;
- each required Element clears the minimum confidence threshold;
- Element source populations are compatible;
- required signed effects meet a meaningful magnitude threshold;
- the relationship survives applicable window/session sensitivity checks;
- no contradiction rule invalidates it;
- minimum sample/coverage requirements are met.

## 11.2 Pattern strength

Pattern `strength` should reflect effect magnitude, not editorial importance.

## 11.3 Pattern confidence

Weight the weakest required Element heavily. A suggested initial form:

```text
0.60 * weakest_required_confidence
+ 0.25 * mean_required_confidence
+ 0.15 * relationship_stability
```

Clamp and version this formula.

## 11.4 Pattern priority

Do not put surprise/shareability in analytical qualification. Those belong to the Finding/story ranking layer.

---

# 12. Free context archetype groups

Replace the single global archetype with **three Free archetype groups**. Additional paid groups are planned later.

Each group classifier may continue using weighted prototype distance, but classification is local to the group and must include confidence/margin/fallback gates.

## 12.1 Group A — `hero_identity`

**Label:** Hero Identity  
**Primary inputs:**

- hero_pool_breadth
- hero_pool_stability
- hero_exploration_rate
- toolkit_breadth
- signature_dependence
- off_pool_performance

### A1 Specialist

Typical shape:

- low breadth
- high pool stability
- low exploration
- higher signature dependence

Meaning: repeated depth in a small pool.

### A2 Craftsman

Typical shape:

- low-to-medium hero breadth
- low toolkit breadth relative to hero breadth
- high stability
- moderate/high signature dependence

Meaning: several heroes, but a repeated toolkit/mechanism.

### A3 Explorer

Typical shape:

- high breadth
- high exploration
- lower pool stability
- off-pool results may be mixed

Meaning: novelty is a meaningful part of selection behavior.

### A4 Adapter

Typical shape:

- medium/high breadth
- medium/high toolkit breadth
- off-pool performance travels relatively well
- exploration is purposeful rather than purely volatile

Meaning: selection range is supported by performance transfer.

### A5 Free Agent

Typical shape:

- high breadth
- low signature dependence
- lower persistent hero identity
- optional support from higher role breadth

Meaning: no small hero subset dominates the observable identity.

## 12.2 Group B — `combat_expression`

**Label:** Combat Expression  
**Free limitation:** summary-level K/D/A and duration cannot identify initiation, teamfight positioning, control contribution, or objective conversion. Archetype names must stay within those limits.

**Primary inputs:**

- combat_involvement
- finisher_orientation
- death_exposure

### B1 Skirmisher

High involvement, neutral-to-kill-oriented finishing, moderate exposure.

### B2 Enabler

High involvement, assist-oriented event distribution, controlled/moderate exposure.

### B3 Selective Finisher

Moderate/lower involvement, high finisher orientation, lower exposure.

### B4 Connector

Moderate involvement, assist-oriented, lower exposure.

### B5 Balanced

No strong extreme across the three summary-visible combat Elements.

Do not use “Initiator”, “Shotcaller”, “Leader”, “Carry Mindset”, or similar names in Free because the summary evidence does not establish those concepts.

## 12.3 Group C — `session_style`

**Label:** Session Style  
**Primary inputs:**

- session_length_tendency
- late_session_performance
- post_loss_performance_response
- post_loss_activity_shift
- post_loss_familiarity_shift
- optional post_loss_death_shift

### C1 Sprinter

Shorter sessions; limited exposure to game-4+ behavior.

### C2 Grinder

Longer sessions with relatively stable late-session performance.

### C3 Second Wind

Medium/long sessions with improved later-session performance.

### C4 Front-Loaded

Often reaches longer sessions but performance declines later.

### C5 Reset Player

Meaningful post-loss response that improves or stabilizes the next game, optionally accompanied by a selection reset toward familiarity.

### C6 Even-Keel

No strong session-position or post-loss shift; behavior is relatively stable across the observed session context.

## 12.4 Classification gates

Suggested defaults:

- Hero Identity: minimum 3 reliable Elements across at least 2 evidence subfamilies.
- Combat Expression: all 3 core Elements preferred; minimum 2 with confidence cap.
- Session Style: minimum 2 reliable session Elements; 3+ required for high confidence.
- Winner/runner-up fit margin <0.04 → low confidence or fallback.
- Do not force a high-confidence archetype when inputs are clustered around neutral.
- Archetype output must name exactly which Elements/Patterns contributed.

---

# 13. Findings/story refactor

The existing finding system has good ranking/conflict/story-selection infrastructure. Reuse those editorial mechanisms, but change its inputs.

## 13.1 New rule

**Findings no longer compute analytical signals.**

Delete or deprecate any v3 path in which a Finding rule re-derives hero breadth, off-pool deltas, recent form, session decline, etc. Those truths belong upstream.

## 13.2 New Finding context

Create something similar to:

```python
@dataclass(frozen=True)
class BehaviorStoryContext:
    elements: Mapping[str, ElementResult]
    patterns: Mapping[str, PatternResult]
    archetypes: Mapping[str, ContextArchetypeResult]
    hero_identity: HeroIdentityResult
    quality: BehaviorQualitySummary
```

Finding definitions should reference:

- `source_pattern_keys`
- optional `supporting_element_keys`
- optional `archetype_group_keys`
- editorial priors: surprise, specificity, consequence, actionability, shareability
- experiment key
- copy template keys

## 13.3 Migration map for existing findings

Use this as an initial mapping, then update copy/tests accordingly:

| Existing finding | v3 semantic source |
|---|---|
| `broad_pool_narrow_safety_zone` | P02 |
| `many_heroes_same_toolkit` | P01 |
| `activity_travels_better_than_results` | P07 |
| `losses_change_trust_more_than_pace` | rename/rebuild from P11 |
| `long_session_tax` | P13 |
| `long_game_edge` / `long_game_leak` | strong E18 + optional supporting Elements; can remain Element-backed findings until a true composite exists |
| `form_identity_divergence` | P15 |
| `strength_with_tax` | P06 or another qualified strength+cost pattern |
| `signature_hero_mechanism` | E05 + hero taxonomy / P06 as appropriate |
| `role_vs_hero_identity` | P04/P05 |
| `volatile_results_stable_style` | P15 or retire if semantically redundant |
| `hidden_strength_fallback` | strongest high-confidence Element/Archetype fallback; no new analytics |

## 13.4 Copy rule

Pattern labels should be relatively neutral. Findings may be entertaining, but copy lint must reject:

- causal certainty
- diagnosis
- psychological intent
- guaranteed coaching outcomes
- unsupported role semantics
- fake population comparisons

---

# 14. Deep-analysis scalability seam

Do not implement the paid metrics now, but make the model capable of accepting them without another conceptual rewrite.

## 14.1 Deep inputs

The future paid path may use selected `/matches/{match_id}` responses and existing parsed replay collections when available. Parsing remains separately budgeted and must not be implicitly triggered by the semantic engine.

The semantic package must therefore be independent of OpenDota transport calls. It receives typed evidence contexts; orchestration decides what data is affordable and available.

## 14.2 Planned paid Elements to document

Mark these **planned / paid**, not active.

### Laning

- `lane_efficiency`
- `cs_pressure`
- `deny_pressure`
- `early_kill_pressure`
- `lane_recovery`

Sources: gold/XP/LH timelines, denies, kill/death timing, lane fields/positions when parsed.

### Economy

- `farm_intensity`
- `farm_efficiency`
- `gold_conversion`
- `recovery_farming`
- `item_timing_reliability`
- `itemization_flexibility`
- `resource_sacrifice`

Sources: GPM/XPM/net worth, gold timelines, purchase log, item timings, ward/support spend, damage/objective outputs.

### Advanced Combat

- `teamfight_participation`
- `damage_contribution`
- `control_contribution`
- `fight_survival`
- `pickoff_orientation`
- `buyback_aggression`

Sources: teamfights, damage relationships, stuns/control, kill/death logs, buyback logs.

### Map & Objectives

- `tower_pressure`
- `objective_conversion`
- `roshan_orientation`
- `vision_contribution`
- `ward_efficiency`
- `rotation_frequency`
- `map_spread`

Sources: tower damage, objectives, Roshan events, ward logs, lane/map positions, movement/position timelines where available.

### Risk & Survival enrichment

- `early_death_exposure`
- `death_cost`
- `positioning_exposure`
- `advantage_protection`

Sources: death timestamps, gold/XP advantage curves, position data, fight context.

## 14.3 Planned paid Patterns to document

Examples:

- `lane_winner_map_loser`
- `high_activity_low_conversion`
- `farm_without_pressure`
- `mechanics_travel_timing_doesnt`
- `recovery_specialist`
- `resource_sacrifice_enabler`
- `ahead_but_unprotected`
- `late_fight_arrival`
- `item_timing_variance_off_pool`
- `vision_without_conversion`

These are not promises that current data coverage will always support them. They are model targets whose required evidence capabilities are documented explicitly.

## 14.4 Planned paid archetype groups

Document, but do not implement classification yet:

### Economy

- Accelerator
- Investor
- Converter
- Sacrificer
- Recovery Farmer

### Map & Objectives

- Hunter
- Pusher
- Rotator
- Controller
- Objective Player

### Advanced Combat

Can later replace/enrich Free combat archetypes once teamfight/position/control evidence exists.

## 14.5 Diagnostic hook from Free → Deep

Add an optional private field to qualified Pattern results:

```python
diagnostic_questions: tuple[str, ...]
required_deep_elements: tuple[str, ...]
```

Example:

```text
P07 activity_travels_better_than_results
→ diagnostic questions:
   - does laning performance stay stable off-pool?
   - do item timings become more variable?
   - does teamfight arrival shift?
→ future deep elements:
   lane_efficiency
   item_timing_reliability
   teamfight_participation / arrival proxy
```

Do not expose unsupported answers. This metadata only prepares intelligent paid match selection and explanation later.

---

# 15. New Free pipeline execution order

Refactor `services/api/app/dna/pipeline.py` toward:

```text
1. Normalize summary history
2. Apply eligibility
3. Infer sessions
4. Extract private summary features
5. Resolve hero taxonomy / hero identity facts
6. Build SummaryBehaviorContext
7. Score all Free Elements
8. Evaluate finite Free Pattern registry
9. Classify each Free context archetype group
10. Build BehaviorStoryContext
11. Generate/rank/conflict-check Findings
12. Select story
13. Assemble immutable free-dna-report-3.0.0
```

A recommended top-level result:

```python
@dataclass(frozen=True, slots=True)
class BehaviorAnalysisResult:
    elements: tuple[ElementResult, ...]
    patterns: tuple[PatternResult, ...]
    archetypes: tuple[ContextArchetypeResult, ...]
    dimensions: tuple[DimensionSummary, ...]
    quality: BehaviorQualitySummary
    versions: BehaviorVersionMap
```

Then Free DNA can contain:

```python
@dataclass(frozen=True, slots=True)
class DnaAnalysisResult:
    matches: ...
    sessions: ...
    features: ...                 # private
    heroes: HeroIdentityResult
    behavior: BehaviorAnalysisResult
    history_tier: str
```

Do not keep new v3 `dimensions` and the legacy eight `DimensionResult`s as two competing public truths. Legacy dimensions may remain calculated only while needed for v1/v2 compatibility tests or migration comparison.

---

# 16. Report schema v3

Create `free-dna-report-3.0.0`.

Do not change the meaning of the v2 schema.

## 16.1 v3 top-level shape

Recommended public shape:

```json
{
  "schema_version": "free-dna-report-3.0.0",
  "report_variant": "free_dna_report",
  "identity": {},
  "metadata": {},
  "versions": {},
  "quality": {},
  "dimensions": [],
  "elements": [],
  "patterns": [],
  "archetypes": [],
  "heroes": {},
  "findings": [],
  "story": {},
  "pages": [],
  "shares": {},
  "deep_dive": {},
  "methodology": {},
  "cost": {}
}
```

## 16.2 Public Dimension summary

Dimensions are group summaries, not trait scores.

```json
{
  "key": "hero_identity",
  "label": "Hero Identity",
  "element_keys": ["hero_pool_breadth", "hero_pool_stability"],
  "qualified_pattern_keys": ["broad_pool_narrow_toolkit"],
  "available_elements": 5,
  "total_free_elements": 6,
  "confidence": "high"
}
```

## 16.3 Public Element shape

Expose enough to explain the result without leaking private match IDs.

```json
{
  "key": "combat_involvement",
  "dimension_key": "combat_expression",
  "label": "Combat Involvement",
  "status": "available",
  "score": 0.74,
  "centered_score": 0.48,
  "axis": {"left": "Lower involvement", "right": "Higher involvement"},
  "confidence": "moderate",
  "confidence_score": 0.68,
  "sample_size": 183,
  "effective_sample_size": 170.2,
  "coverage": 0.91,
  "receipts": [],
  "confounders": [],
  "methodology_version": "element.combat_involvement-1.0.0"
}
```

## 16.4 Public Pattern shape

Only expose qualified/published product Patterns, not every suppressed candidate.

```json
{
  "key": "activity_travels_better_than_results",
  "label": "Activity Travels Better Than Results",
  "kind": "contradiction",
  "strength": 0.72,
  "confidence": "moderate",
  "element_keys": ["off_pool_activity_stability", "off_pool_performance"],
  "receipts": [],
  "confounders": []
}
```

## 16.5 Public Archetype shape

```json
{
  "group_key": "hero_identity",
  "group_label": "Hero Identity",
  "key": "craftsman",
  "label": "Craftsman",
  "fit": 0.81,
  "runner_up": {"key": "specialist", "fit": 0.69},
  "confidence": "high",
  "descriptors": [],
  "contributing_element_keys": [],
  "contributing_pattern_keys": [],
  "classifier_version": "hero-identity-archetypes-1.0.0"
}
```

## 16.6 Version map

v3 should include at least:

- eligibility
- sessions
- features
- hero taxonomy
- hero identity
- behavior model
- element registry
- pattern registry
- archetype registry
- finding registry
- finding ranking
- story
- copy
- report schema
- share renderer
- analysis fingerprint

Any semantic-registry version change must invalidate completed-report reuse when appropriate.

---

# 17. Frontend migration

Create a v3 renderer instead of overloading `report-story-v2.tsx` with incompatible types.

Recommended:

```text
apps/web/app/report/[reportId]/dna/report-story-v3.tsx
```

Update report routing to support:

- v1 → existing renderer
- v2 → existing renderer
- v3 → new renderer

Keep current vertical story/scroll behavior. This task is not a visual redesign.

## 17.1 v3 story behavior

The frontend should be able to render:

- selected Findings as primary story pages;
- contextual archetype identity card showing 2–3 groups rather than one global label;
- an optional “DNA X-ray” / details view organized by Dimensions and Elements;
- qualified Pattern evidence disclosure;
- existing hero identity/recommendation content where still valid;
- Deep Scan handoff;
- share cards using v3 archetype-group identities and selected findings.

## 17.2 Do not expose analytics logic in React

Frontend only formats API output. No thresholding, classification, pattern qualification, or score calculations in TypeScript components.

---

# 18. API client migration

Update `packages/api-client/src/index.ts` or generated equivalent.

Create v3-specific types rather than weakening the union with `any`.

Suggested types:

- `BehaviorDimension`
- `BehaviorElement`
- `BehaviorPattern`
- `ContextArchetype`
- `FreeDnaReportV3`
- `ReportVersionsV3`
- `StoryPageV3`

Preserve `FreeDnaReportV1` and `FreeDnaReportV2`.

If the client is intended to be generated from OpenAPI, make the source schema authoritative and regenerate rather than manually drifting types.

---

# 19. Backward compatibility strategy

## 19.1 Never rewrite stored reports

Existing v1/v2 immutable snapshots remain valid under their original schema.

## 19.2 Dual-path implementation period

During development, allow an internal compare mode:

```text
legacy v2 semantic output
vs
new v3 behavior output
```

This mode is for QA only and should not double OpenDota requests. Both models must consume the same already-fetched normalized summary corpus.

Use it to catch:

- sign reversals
- missing coverage
- unexpected population changes
- archetype instability
- broken hero/session logic

## 19.3 Cutover

After acceptance tests pass:

- new Free analyses emit v3;
- v1/v2 report readers/renderers remain;
- no new product logic imports legacy dimensions/archetypes;
- legacy code is clearly marked and scheduled for later cleanup.

Do not delete legacy v1/v2 code in the same risky commit unless test coverage proves it is unused for historical snapshot validation.

---

# 20. Statistical and data-science requirements

## 20.1 Chronological leakage prevention

Any concept involving “familiar”, “established”, “signature”, or baseline identity must be defined using past/training data before evaluating later rows when performance is involved.

Preserve the anti-leak logic already present in current adaptability work.

## 20.2 Robust estimators

Prefer:

- medians
- MAD
- IQR
- bounded transforms
- shrinkage toward neutral
- stratification where supported

Avoid unstable ratios and raw means when a few extreme games can dominate.

## 20.3 Session sensitivity

Preserve/reuse comparison across 60/90/120-minute session-gap policies for session-dependent Elements and Patterns.

A session conclusion should lose confidence if direction changes materially across reasonable session definitions.

## 20.4 Role confounding

When a metric varies heavily by role and credible role support exists:

- adjust or stratify by role;
- expose the adjustment status in evidence;
- cap confidence when only provisional role baselines exist.

When role coverage is weak, do not manufacture role-adjusted certainty.

## 20.5 Hero/patch confounding

Where material, include caveats for:

- hero availability
- patch changes
- hero learning windows
- role mix changes
- party context
- matchmaking / opponent composition

Do not attempt causal correction that the available summary data cannot support.

## 20.6 Multiple comparisons

Do not build an unrestricted relationship miner in the user-facing path.

The v1 Pattern registry is a finite hypothesis set. If an exploratory offline miner is later introduced, its discoveries must be reviewed and promoted into the versioned registry before public use.

## 20.7 No accidental outcome dominance

Many Elements should describe behavior independently of wins when possible. Do not let the performance proxy dominate every archetype and Pattern.

The user’s “identity” should not collapse into “wins a lot” versus “loses a lot”.

---

# 21. Owner documentation deliverable — required

Create:

```text
docs/dna-model-catalog.md
```

This is the owner-friendly source of truth explaining what the system can say and why.

## 21.1 Required sections

1. **Plain-English model overview**
   - Observation → Feature → Element → Pattern → Archetype → Finding
   - what each layer is for
   - examples

2. **Free vs Paid data boundary**
   - summary history
   - match detail
   - parsed replay
   - what costs/request types each tier requires

3. **Dimension map**
   - all master Dimensions
   - which are represented in Free
   - which need paid/deep data

4. **Free Element catalog**
   For every E01–E23 include:
   - key
   - display name
   - Dimension
   - Free/Paid
   - active/planned
   - user question
   - exact source data family
   - plain-English calculation
   - minimum sample/coverage
   - score axis meaning
   - confidence limitations
   - why it exists / user value
   - which Patterns consume it
   - methodology version

5. **Free Pattern catalog**
   For every P01–P15 include:
   - key/name
   - required Elements
   - optional Elements
   - qualification explanation
   - what it means
   - what it does not mean
   - likely Finding/story use
   - Deep diagnostic questions, if any

6. **Free Archetype groups**
   - group definition
   - prototypes
   - inputs
   - fallback behavior
   - examples of why two players with the same Hero Identity archetype can have different Combat/Session archetypes

7. **Planned Paid Elements / Patterns / Archetypes**
   - clearly labeled as planned, not implemented
   - source endpoint/capability
   - why Free cannot support them reliably

8. **Worked trace examples**
   At least three:
   - many heroes → narrow toolkit → Craftsman-type identity → finding
   - activity stable off-pool + results drop → Pattern → future Deep diagnostic hook
   - long sessions + late decline → Long Session Tax → experiment

9. **Claims we intentionally do not make**
   - tilt
   - anger
   - confidence
   - selfishness
   - leadership
   - trust
   - psychological diagnoses
   - guaranteed coaching outcomes

10. **Version history**

## 21.2 Generate the catalog from code where possible

Create:

```text
scripts/generate_dna_model_catalog.py
```

The script should read registry metadata and produce stable generated sections of `docs/dna-model-catalog.md`.

If a fully-generated document is too restrictive, use markers:

```md
<!-- BEGIN GENERATED: DIMENSIONS -->
...
<!-- END GENERATED: DIMENSIONS -->
```

Do the same for Elements, Patterns, and Archetypes.

Add Make targets:

```text
make dna-catalog
make dna-catalog-check
```

`dna-catalog-check` should fail CI when registry definitions and committed owner documentation diverge.

This documentation requirement is part of the feature, not an optional cleanup task.

---

# 22. README update — required

Update root `README.md` so it reflects the v3 architecture rather than the current eight-dimension model.

README should remain concise and operational. It should contain:

1. **What Dota Report Card is**
   - evidence-backed behavioral player analysis
   - Free summary scan + selective deeper future analysis

2. **Core model**

```text
observations → features → elements → patterns → contextual archetypes → findings
```

3. **Free data-cost invariant**
   - one bounded history read
   - no detail reads
   - no replay parse requests

4. **Deep scalability**
   - selected detail/parsed evidence can populate richer Elements later
   - no brute-force parsing of every history match

5. **Repository architecture summary**
   - ingestion
   - private features
   - behavior semantic engine
   - findings/story
   - report assembly
   - web renderer

6. **Versioned immutable report behavior**
   - v1/v2 historical support
   - v3 active contract

7. **Local start / deployment / verification commands**
   - preserve existing useful operational content

8. **Documentation links**
   - `ARCHITECTURE.md`
   - `docs/dna-model-catalog.md`
   - `docs/opendota-data-inventory.md`
   - `docs/system-behavior-baseline.md`

Remove stale language implying the eight legacy dimensions are the primary public semantic model.

---

# 23. ARCHITECTURE.md — required new canonical document

There is no current root `ARCHITECTURE.md`. Create it.

This should be the canonical technical design reference, not a second README.

Required sections:

## 23.1 System goals and constraints

- insight quality
- evidence integrity
- unit economics
- deterministic claims
- immutable reports
- privacy boundary
- Free/Deep separation

## 23.2 System context diagram

Show:

```text
Browser
  ↓
Next.js
  ↓
FastAPI analysis orchestration
  ↓
OpenDota adapter
  ↓
Raw/normalized evidence
  ↓
Behavior semantic engine
  ↓
Finding/story selection
  ↓
Immutable report snapshot
```

## 23.3 Semantic architecture

Explain Observation / Feature / Element / Pattern / Archetype / Finding and which package owns each.

## 23.4 Free request/data flow

Detailed sequence from analysis request through report creation.

## 23.5 Deep extension flow

Explain how Free Patterns can create diagnostic questions and how a future selector can hydrate only explanatory matches.

## 23.6 Package ownership map

Explicit table of paths and responsibilities.

## 23.7 Contracts and versioning

- internal result models
- public report schemas
- registry versions
- analysis fingerprint
- v1/v2/v3 compatibility

## 23.8 Data provenance and privacy

- raw payload storage
- normalized rows
- private match IDs
- public receipt sanitization
- noindex reports
- API-key boundary

## 23.9 Confidence / suppression model

Explain how unavailable/limited/qualified works.

## 23.10 Cost architecture

Explain Free request ceiling and future Deep budgets.

## 23.11 Testing strategy

Unit / property / contract / integration / E2E / catalog drift checks.

## 23.12 Extension playbook

“How to add a new Element”, “How to add a new Pattern”, “How to add an Archetype”, “How to promote a paid/deep capability”.

## 23.13 Explicit anti-patterns

- analytics in React
- findings recomputing truth
- raw API calls inside behavior scorers
- forced archetypes
- missing=neutral
- causal/psychological claims
- unversioned thresholds

---

# 24. Other docs to update for consistency

Even though the owner explicitly requires README and ARCHITECTURE, do not leave contradictory documentation behind.

Update at least:

- `docs/free-dna-finding-system.md`
  - either rewrite for v3 or mark as historical v2 and link to new architecture/catalog;
- `docs/opendota-data-inventory.md`
  - align terminology with summary/detail/parsed evidence tiers and current request policy;
- `docs/system-behavior-baseline.md`
  - update expected public behavior to v3;
- `docs/evidence-contract.md`
  - add Element/Pattern/Archetype provenance expectations;
- `docs/dota_report_card_free_dna_ux_blueprint.md`
  - only the data-contract terminology necessary to prevent obsolete “eight primary dimensions + one archetype” assumptions; do not perform a full UX rewrite unless required by tests.

Do not silently delete historical design docs that are still useful; mark superseded sections clearly.

---

# 25. File-by-file implementation map

## Create

```text
services/api/app/behavior/__init__.py
services/api/app/behavior/models.py
services/api/app/behavior/tiers.py
services/api/app/behavior/dimensions.py
services/api/app/behavior/evidence.py
services/api/app/behavior/comparisons.py
services/api/app/behavior/catalog.py

services/api/app/behavior/elements/__init__.py
services/api/app/behavior/elements/models.py
services/api/app/behavior/elements/registry.py
services/api/app/behavior/elements/service.py
services/api/app/behavior/elements/free_summary/*.py

services/api/app/behavior/patterns/__init__.py
services/api/app/behavior/patterns/models.py
services/api/app/behavior/patterns/registry.py
services/api/app/behavior/patterns/service.py
services/api/app/behavior/patterns/free_summary.py

services/api/app/behavior/archetypes/__init__.py
services/api/app/behavior/archetypes/models.py
services/api/app/behavior/archetypes/registry.py
services/api/app/behavior/archetypes/classifier.py
services/api/app/behavior/archetypes/free_v1.json   # optional

scripts/generate_dna_model_catalog.py
docs/dna-model-catalog.md
ARCHITECTURE.md

apps/web/app/report/[reportId]/dna/report-story-v3.tsx
```

## Update

```text
services/api/app/dna/pipeline.py
services/api/app/findings/models.py
services/api/app/findings/context.py
services/api/app/findings/registry.py
services/api/app/findings/evaluator.py
services/api/app/findings/conflicts.py
services/api/app/findings/copy.py
services/api/app/reports/dna_assembly.py
services/api/app/api/report_schemas.py
services/api/app/content/*
packages/api-client/src/index.ts   # or generated source
apps/web/app/report/[reportId]/page.tsx
apps/web/app/report/[reportId]/dna/* as needed
README.md
Makefile
relevant CI workflow files
relevant docs listed above
```

## Legacy / freeze

Initially retain:

```text
services/api/app/dna/dimensions/*
services/api/app/dna/archetypes/*
services/api/app/patterns/*
```

but make sure **new v3 runtime code does not depend on them as semantic truth** except through intentionally-wrapped reusable statistical helpers during migration.

Add comments/docs that identify them as legacy v1/v2 paths if they must stay.

Do not leave two active “pattern” registries that both publish v3 semantics.

---

# 26. Testing plan

Add dedicated behavior tests instead of hiding all coverage inside report tests.

Recommended files:

```text
tests/unit/test_behavior_element_registry.py
tests/unit/test_behavior_elements_hero.py
tests/unit/test_behavior_elements_role.py
tests/unit/test_behavior_elements_combat.py
tests/unit/test_behavior_elements_adaptability.py
tests/unit/test_behavior_elements_form.py
tests/unit/test_behavior_elements_sessions.py
tests/unit/test_behavior_patterns.py
tests/unit/test_behavior_archetypes.py
tests/unit/test_behavior_findings_bridge.py
tests/unit/test_dna_catalog_generation.py

tests/contract/test_free_dna_v3_contract.py
tests/integration/test_free_dna_v3_pipeline.py
```

Also update existing regression tests rather than discarding them.

## 26.1 Element unit tests

For every Element test:

- high-left synthetic case
- neutral synthetic case where meaningful
- high-right synthetic case
- insufficient sample
- missing field coverage
- input-order invariance
- deterministic output
- boundary thresholds
- confidence cap when baseline is provisional

## 26.2 Property/invariant tests

Add tests for:

- score always in [0,1] when available
- centered score always in [-1,1]
- confidence in [0,1]
- unavailable score is `None`
- no negative denominator
- no future leakage in familiar/off-pool definitions
- duplicating identical matches should not create impossible score direction flips
- shuffling source input should not change chronological results
- session-sensitive result confidence falls when direction is unstable

If Hypothesis/property-based testing is already acceptable in dependencies, use it. Otherwise implement deterministic parametrized cases.

## 26.3 Pattern tests

For each Pattern:

- qualifies on intended combination
- fails when one required Element missing
- fails below confidence threshold
- fails below effect threshold
- suppresses contradictory combination
- uses only declared dependencies
- never qualifies from one Element alone unless explicitly permitted

## 26.4 Archetype tests

For each prototype group:

- canonical prototype input wins expected archetype
- runner-up returned correctly
- close margin reduces confidence/falls back
- missing Elements do not become neutral values
- group classifications are independent
- same Hero Identity can coexist with multiple Combat/Session results

## 26.5 Finding bridge tests

Assert that v3 Finding evaluation does not recalculate upstream metrics.

A useful architectural test: monkeypatch/raw context should not be accessible from Finding evaluator except through `BehaviorStoryContext`.

## 26.6 Cost boundary tests

Free v3 integration must assert:

- one bounded history retrieval behavior remains
- detail request count = 0
- parse request count = 0
- no hidden deep hydration from Element/Pattern/Archetype services

## 26.7 Public privacy contract tests

Assert v3 public report contains no:

- account ID
- raw match IDs
- raw normalized rows
- OpenDota API key
- internal source references
- suppressed Pattern internals

unless already explicitly allowed by an approved separate contract.

## 26.8 Backward compatibility

Keep tests that validate/read v1/v2 snapshots.

Frontend E2E should verify v1/v2/v3 routing.

## 26.9 Documentation drift test

`make dna-catalog-check` must fail if registry metadata changed without regenerating `docs/dna-model-catalog.md`.

---

# 27. Acceptance criteria for content quality

Create or extend copy lint tests with forbidden/flagged concepts.

At minimum flag public analytic copy that uses these without explicitly approved context:

```text
tilt
tilting
angry
anger
fear
anxious
anxiety
insecure
confidence
trust teammates
selfish
selfless
leader
leadership
shotcaller
mental strength
mental resilience
emotionally
because you
causes you
will make you
will improve your rank
```

Some words such as “confidence” are valid for statistical confidence in UI metadata; lint must distinguish analytical-copy context from model-quality labels.

Prefer public Element names that state the observation precisely.

---

# 28. Observability and debugging

Add structured internal logging at layer boundaries, not per-match spam.

Useful events:

```text
behavior_elements_completed
behavior_patterns_completed
behavior_archetypes_completed
behavior_findings_completed
behavior_model_partial
behavior_model_version_mismatch
```

Log only safe aggregate metadata:

- counts available/limited/unavailable
- registry versions
- elapsed stage time
- history tier
- failure key

Do not put raw account IDs/match rows in normal application logs if current privacy standards avoid them.

For debugging/tests, preserve private analysis snapshots with source-match provenance according to current persistence policy.

---

# 29. Implementation phases

Luna should implement in this sequence so the system remains testable after each phase.

## Phase 0 — Baseline and safety net

1. Run current test suite and record failures before changes.
2. Read current Free v2 contract, findings system, session logic, hero taxonomy, feature extraction, report assembly, frontend v2 renderer.
3. Add missing golden/snapshot fixtures needed to compare old and new semantic outputs from the same normalized history.
4. Add an ADR or architecture note documenting the semantic migration decision if the repo uses ADRs.

**Exit:** current behavior is reproducible and regression-protected.

## Phase 1 — Core behavior contracts and registries

1. Create `app/behavior` base models.
2. Create dimension registry.
3. Create Element definition/result registry contracts.
4. Create Pattern definition/result contracts.
5. Create Archetype group contracts.
6. Add EvidenceTier/ProductTier metadata.
7. Add registry validation at import/startup/test time:
   - unique keys
   - valid dimensions
   - no missing scorer/evaluator key
   - no dependency cycles
   - all pattern Element dependencies exist
   - all archetype dependencies exist
   - active Free definitions require summary-supported capabilities only

**Exit:** empty engine contracts validate, no product cutover yet.

## Phase 2 — Free Elements

1. Migrate current breadth → `hero_pool_breadth`.
2. Migrate role → `role_breadth`.
3. Migrate activity → `combat_involvement`.
4. Migrate orientation → `finisher_orientation`.
5. Split/refactor adaptability into off-pool Elements.
6. Rename/refactor resilience/endurance/rhythm into precise session Elements.
7. Add the new hero/toolkit/role/death/form/session Elements E01–E23.
8. Centralize robust comparison helpers to reduce copied statistics.
9. Add comprehensive tests.

**Exit:** all Free Elements compute from existing summary corpus with zero new network requests.

## Phase 3 — Free Patterns

1. Create finite registry P01–P15.
2. Implement declarative evaluators.
3. Add confidence/strength/suppression rules.
4. Add diagnostic Deep metadata for explainable Patterns.
5. Stop using legacy `app/patterns/detector.py` in the v3 Free path.
6. Add Pattern tests.

**Exit:** v3 analytical synthesis exists independently of Findings.

## Phase 4 — Context archetypes

1. Implement three groups.
2. Define prototypes/weights/version.
3. Add group-specific evidence gates.
4. Add runner-up and margin behavior.
5. Implement neutral fallback/unclassified result.
6. Migrate descriptor generation to group context.
7. Add tests.

**Exit:** there is no v3 global archetype.

## Phase 5 — Findings/story bridge

1. Create `BehaviorStoryContext`.
2. Refactor Finding definitions to reference Patterns/Elements/Archetypes.
3. Retire v3 analytic recomputation from `findings/signals.py` and evaluator paths.
4. Map existing high-value findings to new sources.
5. Rename unsafe “trust” / psychological wording.
6. Preserve editorial ranking, conflict suppression, experiments, shareability priors.
7. Add architectural tests proving Findings consume upstream truth only.

**Exit:** “truth” and “story” layers are cleanly separated.

## Phase 6 — v3 report/API/client/frontend

1. Add `free-dna-report-3.0.0` Pydantic schema.
2. Update report assembly.
3. Update version fingerprint.
4. Add v3 TypeScript client types.
5. Add `report-story-v3.tsx`.
6. Route v1/v2/v3 correctly.
7. Update shares as needed for multiple archetype groups.
8. Preserve noindex/privacy/cost behavior.
9. Add contract/integration/E2E tests.

**Exit:** new analyses render v3 without breaking historical reports.

## Phase 7 — Owner catalog and canonical architecture docs

1. Implement registry-driven catalog generation.
2. Create `docs/dna-model-catalog.md` with required Free/Paid/source/why fields.
3. Create root `ARCHITECTURE.md`.
4. Rewrite README architecture summary.
5. Update stale supporting docs.
6. Add CI drift check.

**Exit:** owner can understand the system without reading Python and docs match code.

## Phase 8 — Cleanup and hardening

1. Mark legacy dimensions/global archetype/summary-pattern code clearly.
2. Remove v3 imports of old semantic layers.
3. Remove dead compatibility code only if historical report reading does not require it.
4. Run full QA and inspect representative reports.
5. Verify all version strings/fingerprints.

**Exit:** one active v3 semantic truth path.

---

# 30. Full verification commands

At minimum Luna must finish with:

```bash
make lint
make typecheck
make test
make test-contract
make test-integration
make test-e2e
make taxonomy-validate
make dna-catalog-check
```

If API client generation is canonical:

```bash
make api-client
```

Then rerun typecheck and tests after generation.

Do not claim completion while generated files are dirty or documentation drift check fails.

---

# 31. Definition of Done

The project is complete only when all of the following are true.

## Architecture

- [ ] One canonical v3 semantic pipeline exists: Element → Pattern → context Archetype → Finding.
- [ ] No v3 global archetype remains.
- [ ] Dimensions are organizational, not arbitrary aggregate trait scores.
- [ ] Free v3 uses only summary history and hero taxonomy.
- [ ] Future deep evidence tiers are represented in contracts without triggering deep calls.

## Elements

- [ ] E01–E23 are implemented or, if a field-support reality makes one impossible, the deviation is explicitly documented with a safer replacement rather than silently skipped.
- [ ] Every Element has sample/coverage/confidence/missing-state handling.
- [ ] Every Element has owner-readable metadata.
- [ ] No Element score is presented as a percentile without cohort calibration.

## Patterns

- [ ] P01–P15 finite registry exists.
- [ ] Each qualified Pattern uses declared upstream Elements.
- [ ] No unrestricted production pair-mining exists.
- [ ] Pattern confidence/strength are separate from editorial priority.
- [ ] Relevant Patterns expose future diagnostic Deep questions privately.

## Archetypes

- [ ] Hero Identity group implemented.
- [ ] Combat Expression group implemented.
- [ ] Session Style group implemented.
- [ ] Each group has fallback behavior and runner-up margin handling.
- [ ] Public output includes contributing Element/Pattern references.

## Findings/story

- [ ] Findings do not recompute semantic analytics.
- [ ] Existing high-value findings are migrated or intentionally retired with explanation.
- [ ] Unsafe psychological language is removed from semantic keys/copy where applicable.
- [ ] Experiments remain observable and testable rather than guaranteed recommendations.

## Public contract

- [ ] `free-dna-report-3.0.0` validates strictly.
- [ ] v1/v2 remain readable.
- [ ] TypeScript client has exact v3 types.
- [ ] v3 frontend renderer works.
- [ ] Public report leaks no raw IDs/rows/internal provenance.

## Cost

- [ ] Free detail requests = 0.
- [ ] Free parse requests = 0.
- [ ] Element/Pattern/Archetype code contains no OpenDota transport calls.

## Documentation

- [ ] `docs/dna-model-catalog.md` exists and is owner-readable.
- [ ] It clearly states Free vs Paid, source data, calculation, reason, limitations, and dependencies.
- [ ] Root `ARCHITECTURE.md` exists and is canonical.
- [ ] `README.md` represents the new model accurately.
- [ ] Supporting docs are not contradictory.
- [ ] Catalog drift is CI-enforced.

## Quality

- [ ] Unit tests cover every Element family.
- [ ] Pattern qualification tests exist.
- [ ] Archetype prototype/fallback tests exist.
- [ ] Contract/integration/E2E tests pass.
- [ ] Missing-data and limited-history behavior is explicit.
- [ ] Psychological/causal copy lint passes.

---

# 32. Final implementation principles for Luna

When there is tension between a catchy insight and evidence quality, choose evidence quality.

When there is tension between a new abstraction and the repo’s already-tested statistical logic, reuse the tested logic but place it behind the correct semantic boundary.

When a concept cannot be measured from Free summary data, do not simulate it. Put it in the planned paid catalog with the exact richer data capability required.

The target product is not “a dashboard with more metrics.” It is a layered behavioral interpretation system:

```text
ELEMENT
“What single tendency can we measure?”

PATTERN
“What becomes meaningful when several tendencies interact?”

ARCHETYPE
“What recurring style does this combination resemble in this specific context?”

FINDING
“What is the most useful, surprising, evidence-backed way to tell the player?”
```

The implementation is successful when a future engineer can add a new paid Economy Element or Map Pattern without changing the meaning of the hierarchy, and when the owner can open `docs/dna-model-catalog.md` and understand exactly what the product knows, how it knows it, what tier pays for it, and where the claim boundary stops.
