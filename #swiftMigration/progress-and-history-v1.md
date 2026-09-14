# Progress & History V1 — SSOT

## Status

**Status:** LOCKED — PRODUCT CONTRACT
**Version:** V1
**Scope:** Long-term personal Progress & History semantics for Dota 2
**Last updated:** 2026-09-14

This is the authoritative contract for how progression history is partitioned,
ordered, interpreted, and rebuilt. It is written for backend/data engineers,
mobile/frontend engineers, product designers, analytics/calibration, QA, and
future agents working on adjacent SSOTs.

The product principle is:

> See yourself.

Progress & History describes change in a player's own role-specific metric
history. It does not claim to produce a universal skill score or a causal
judgment about a match.

## Purpose

This SSOT answers:

- Which matches belong to a progression history?
- Which histories may read or affect one another?
- What is the difference between a factual metric observation, a rolling
  baseline, and a trend state?
- When is a trend state eligible and how does it survive sparse activity,
  recovery, role correction, entitlement changes, and methodology migration?
- Which facts and derived states are current canonical truth versus append-only
  historical events?

It makes the long-term progression contract precise without prescribing a
database schema, API shape, queue technology, chart, or screen layout.

## Scope

This document owns:

- the Standard/Turbo and effective-role partitioning of Progress;
- the chronological ordering of role/bucket metric histories;
- the distinction between raw metric observations and derived state;
- the canonical previous-20 rolling baseline as consumed from the metrics
  contract;
- the canonical ten-point trend window and its semantic states;
- missing metric, N/A, insufficient-history, sparse-activity, and entitlement
  behavior;
- deterministic recalculation after role correction, recovery, entitlement
  changes, and methodology migration; and
- the semantic boundary between current canonical Progress and immutable
  lifecycle/celebration records.

This document does not redefine upstream metric formulas, match lifecycle
states, role classification, subscriptions, Personal Records, or visual
design. It references those contracts where their output is required to make
Progress deterministic.

## Dependencies / Upstream Contracts

The following boundaries are normative.

| Dependency | Progress & History consumes or respects | Progress & History does not redefine |
|---|---|---|
| Match Lifecycle V1 | Validated match identity, chronology, progression eligibility, Standard/Turbo classification, chronological finalization, recovery, role-correction triggers, readiness, and append-only celebration/notification behavior. | Discovery, retries, provider checkpoints, lifecycle states, notification timing, or source acquisition. |
| Role Resolution & Correction | Exactly one `effective_role` for every successfully classified match: Carry, Mid, Offlane, or Support. The latest explicit user assertion wins. | Classifier logic, confidence calculation, or role inference. |
| Role Metrics & Personal Baselines V1 | Metric registry, metric versions, raw/comparison values, direction/polarity, match and metric eligibility, N/A/zero semantics, and the previous-20 median baseline with its existing minimum prior-history gate. | Metric formulas, telemetry interpretation, or a second baseline definition. |
| Free vs Pro Boundary SSOT | Which retained history is exposed to the account at the current entitlement. | Entitlement amount, retention policy, paywall behavior, or subscription state. |
| Personal Records SSOT | Current best-known PB/index behavior and presentation of PB state when Progress history is rebuilt. | PB comparison rules, record UX, achievement/challenge behavior, or celebration copy. |
| Match Detail / Latest Match | The pre-match baseline used for a match-level comparison and the distinction between a historical snapshot and current rebuilt Progress. | Match-detail layout, latest-match narrative, or a new comparison formula. |
| Reports / Recaps | Optional presentation windows and filtered views over Progress data. | Canonical Progress math. A report window cannot redefine the ten-point trend or the twenty-observation baseline. |
| Analytics / Calibration | Versioned trend evaluator and per-metric meaningful-movement calibration. | Product states, history partitioning, or a composite score. |

If an adjacent contract conflicts with the locked rules in this document, the
conflict must be recorded and resolved explicitly. An implementation must not
silently choose a third behavior.

## Core Product Invariants

1. **There are eight independent progression tracks.** The tracks are
   Standard Carry, Standard Mid, Standard Offlane, Standard Support, Turbo
   Carry, Turbo Mid, Turbo Offlane, and Turbo Support.
2. **Every progression observation has exactly one bucket and one effective
   role.** Position 4 and Position 5 both use Support.
3. **Buckets are isolated.** Standard and Turbo never share observations,
   baselines, trend windows, ordering dependencies, or derived state.
4. **Roles are isolated.** Carry, Mid, Offlane, and Support never share a
   canonical progression series, even when two roles use the same metric
   formula.
5. **The history is chronological.** Discovery order, notification order,
   worker completion order, and calendar period are not progression order.
6. **Raw observations remain distinguishable from interpretation.** A raw
   metric value is factual evidence for a match; a baseline and trend state are
   derived context and may be rebuilt.
7. **The baseline is previous-only.** A match never contributes to its own
   match-level baseline.
8. **The canonical baseline is the established previous-20 median.** It uses
   the latest eligible measured observations with the same bucket, role, and
   metric identity, subject to the existing minimum prior-history gate in the
   metrics SSOT.
9. **The canonical trend is match-based.** It requires a complete ten-point
   eligible trend window for the same bucket, role, and metric. Calendar
   periods never define canonical trend math.
10. **Trend polarity is metric-specific.** A numerically higher value is not
    automatically semantically improving; lower-is-better metrics are mapped
    accordingly.
11. **Missing values are not zero.** N/A metric points do not enter baseline or
    trend counts.
12. **Inactivity has no analytical force.** A calendar gap does not reset,
    decay, weaken, or expire a history, baseline, or trend.
13. **Progress has no independent retention cutoff.** It consumes the history
    exposed by the current entitlement/retention contract.
14. **One current methodology applies across canonical history.** A
    methodology change is migrated retroactively across retained compatible
    history; old and new math are not mixed in one canonical timeline.
15. **No canonical composite judgment exists.** V1 has metric-level states,
    not an all-role curve, role score, player score, grade, percentage,
    rating, or overall improvement verdict.
16. **Rebuilds are deterministic and idempotent.** Replaying the same ordered
    source history with the same canonical methodology produces the same
    current state and no duplicate observations or events.
17. **Canonical rebuilds do not rewrite append-only delivered events.** A PB or
    celebration already delivered remains an auditable event even if current
    derived Progress later changes.

## Canonical Terminology

### Progression bucket

The mode partition used by Progress:

- `STANDARD`: the supported Standard modes defined by the metrics/lifecycle
  contracts, currently Ranked All Pick and Unranked All Pick;
- `TURBO`: Turbo.

The bucket is part of every progression identity. A general Match History may
display both buckets together, but a Progress calculation may not.

Standard and Turbo use the same V1 role and metric logic. The bucket changes
the history namespace and ordering dependency, not the metric meaning; shared
logic is never permission to share observations or derived state.

### Effective role

The single role supplied by Role Resolution for a classified match:

- `Carry`
- `Mid`
- `Offlane`
- `Support`

An explicit user assertion overrides classifier output. Detected role and
confidence remain metadata; they are not an additional progression role.

### Progression track

The pair:

```text
(progression_bucket, effective_role)
```

For example, `(STANDARD, Carry)` is a different track from `(TURBO, Carry)`
and from `(STANDARD, Support)`.

### Metric history

The chronological sequence of metric points for one progression track and one
current metric definition. A metric history is not an all-role sequence and is
not a replacement for the raw source record.

The full logical identity is:

```text
(progression_bucket, effective_role, metric_id, current_metric_version)
```

Only the current canonical metric version participates in the active
Progress history. Previous versions may remain in audit/provenance records but
must not run beside the current version as a second canonical era.

### Raw metric observation

The factual per-match metric result derived from validated source telemetry and
the current metric definition. It includes the match identity, chronology,
track, metric identity/version, raw value where applicable, canonical
`comparison_value` where applicable, and measured/N/A status with its reason.

A raw metric observation is not a trend label. A metric-level N/A result is a
concluded observation state for a valid match, not a fabricated numeric value.

### Measured observation

A raw metric observation with a valid current metric value, including a
legitimate numeric zero. It can be admitted to baseline, trend, and other
downstream calculations when the containing match is progression-eligible.

### Eligible observation

A measured observation from a progression-eligible match whose bucket, role,
metric identity, chronology, integrity, and current methodology are valid.
N/A points, progression-ineligible matches, unsupported modes, unresolved
roles, and unavailable source matches are not eligible observations.

### Baseline-ready observation

An eligible measured observation for which the already-established minimum
prior-history gate is satisfied and a valid pre-match rolling baseline exists.
The minimum count itself belongs to Role Metrics & Personal Baselines V1; the
current contract there is the established gate before comparison/PB use.

### Rolling baseline

The canonical recent-normal reference available before a specific measured
observation. It is the median of the latest 20 previous eligible measured
observations for the same progression bucket, effective role, and metric
identity, after the upstream minimum prior-history gate. It is contextual
reference, not a score and not a replacement for raw observations.

### Match comparison baseline

The rolling baseline snapshot that existed immediately before one specific
match. Match Detail uses this pre-match value when comparing that match. The
current baseline after later matches is not substituted into an old match's
historical comparison.

### Trend point

One baseline-ready observation paired with the pre-match rolling baseline that
existed at that point. It preserves the ordered relationship between the
metric observation and the recent-normal reference used to interpret it.

This definition makes the baseline gate explicit: a metric can have measured
history and still have no trend points until the existing minimum prior-history
requirement is met. An N/A point never becomes a trend point.

### Trend window

The ten most recent eligible trend points for one metric history, ordered by
chronology. It is complete only when ten such points exist under the current
canonical methodology and current history entitlement.

### Trend state

The semantic result for a complete trend window. V1 states are exactly:

- `Improving`
- `Stable`
- `Declining`
- `Insufficient History`

`Insufficient History` is used when a complete ten-point eligible trend window
does not exist. It is not a claim of decline.

### History entitlement

The current account-level rule that determines which retained progression
history is exposed for calculation and presentation. Progress does not choose
the amount. A change in entitlement changes the available input set; it does
not create a new analytical epoch.

### Canonical methodology

The one versioned set of rules used to derive current Progress state, including
the applicable metric definitions and comparison values, eligibility/missingness
semantics, baseline definition, trend horizon/evaluator, metric polarity, and
calibration binding.

### Recalculation / rebuild

A deterministic replay of retained eligible source history in chronology order
under one canonical methodology, producing current raw metric projections,
baseline snapshots, trend points/states, and directly dependent current
Progress state. A rebuild may replace derived values; it does not rewrite
immutable source evidence or append-only delivered events.

### Unavailable historical metric point

A historical match that is retained and visible, but for which the current
metric definition cannot produce a trustworthy measured value from the
available source telemetry. It is represented as metric-level N/A with a
reason under the current methodology. An obsolete value from a prior metric
definition is not carried forward as if it were current.

### Current canonical state

The derived Progress truth under the current methodology and currently exposed
history: eligible metric observations, baselines, trend points/states, and
other directly dependent indexes. It is distinct from a previously published
match snapshot and from a delivered celebration event.

### Audit/event record

Immutable provenance or delivery history showing what source, methodology,
correction, PB, or celebration was recorded at a point in time. Audit/event
records explain change; they do not create a second active canonical
progression series.

## Progression Partitioning

### The eight canonical histories

Progress is tracked independently in these eight bucket/role histories:

| Bucket | Carry | Mid | Offlane | Support |
|---|---|---|---|---|
| Standard | Standard Carry | Standard Mid | Standard Offlane | Standard Support |
| Turbo | Turbo Carry | Turbo Mid | Turbo Offlane | Turbo Support |

The role sequence below illustrates the partition:

```text
Standard: Carry → Carry → Support → Carry

Standard Carry history:   match 1, match 2, match 4
Standard Support history: match 3
```

The four matches do not form one four-point Standard progression sequence.
Turbo matches are not inserted into either Standard sequence.

### Isolation requirements

Every observation, baseline, trend point, trend state, and directly dependent
index must include the full progression identity. The following are forbidden:

- a role-agnostic baseline;
- a Standard/Turbo shared queue or history count;
- a Carry baseline read by Support;
- a shared trend line for multiple roles;
- cross-role or cross-bucket normalization presented as canonical Progress; or
- a fallback from a missing role history to another role or bucket.

A UI may offer a general chronological Match History or allow the user to
switch context, but an “All” view must show separated tracks or evidence. It
must not silently calculate a merged progression curve.

### Match eligibility versus metric availability

Match-level progression eligibility and metric-level availability are
different:

- A valid progression-eligible match may have one or more metric-level N/A
  points.
- A measured metric point may enter only its own bucket/role/metric history.
- A metric-level N/A point does not enter baseline or trend counts.
- A match that is progression-ineligible remains visible where lifecycle and
  Match History allow, but contributes no Progress observation.
- A source match that is still lifecycle `UNAVAILABLE` contributes no metric
  observation until trustworthy evidence is recovered and admitted.

Progress consumes the upstream eligibility result. It does not make an
otherwise invalid match eligible merely because one metric is calculable.

## Metric History Model

For each current metric identity, the canonical history is an ordered sequence
of match-linked points:

```text
H(bucket, role, metric) = [p1, p2, p3, ...]
```

Each point retains or references:

- the stable logical source match identity;
- the chronology key;
- the progression bucket;
- the effective role used by Progress;
- the metric ID and current metric version;
- the raw/display value when defined;
- the canonical comparison value when defined;
- measured versus N/A status and N/A reason;
- source/provenance needed to reproduce the point; and
- the methodology binding used for current derived state.

The representation above is conceptual. It does not require a particular
storage model.

### Raw values and comparison values

The metrics SSOT owns whether a metric's baseline/trend input is its raw value
or a normalized `comparison_value`, such as a rate or share. Progress must use
that declared comparison value consistently. It must not apply an ad hoc UI
conversion before calculating a baseline or trend.

Examples of valid distinctions include:

- a raw count displayed while a per-ten-minute rate is compared;
- a raw damage amount displayed while a team-share ratio is compared; and
- a raw duration displayed while a lower-is-better rate is compared.

The raw value and source evidence remain available for factual display and
audit. The comparison value is the canonical analytical input where the metric
contract specifies one.

### Chronological ordering

Within each bucket and role history, order by the upstream chronology key:

```text
(provider_started_at, provider_source_match_id)
```

Rules:

1. `provider_started_at` is the primary order.
2. `provider_source_match_id` is the deterministic tie-breaker.
3. Discovery order, analysis completion order, batch order, and notification
   order never substitute for chronology.
4. Missing or untrustworthy chronology is not guessed. The lifecycle recovery
   or unavailable rules apply.
5. A duplicate observation for one logical source match is deduplicated by
   source identity and does not add a second progression point.

### Insertion and replay

When a valid historical match is admitted after newer matches already exist,
insert it at its chronology position. Derived state from that position onward
is replayed when the lifecycle/immutability boundary permits a canonical
rebuild. The replay uses the same current methodology for every affected point.

Chronological insertion is not optional merely because a match arrived late.
Using arrival order would make the result depend on network/provider timing.

## Rolling Baseline

The rolling baseline answers:

> What is my recent normal for this role, mode, and metric?

For a measured current point `p`:

1. select only earlier eligible measured observations with the same bucket,
   effective role, metric ID, and current metric version;
2. exclude `p` itself;
3. order them by the chronology key;
4. retain the latest 20 previous observations, or fewer when fewer exist; and
5. apply the established minimum prior-history gate and median rule owned by
   Role Metrics & Personal Baselines V1.

This SSOT does not introduce a second statistic, fallback baseline, smoothing
layer, or time weighting. V1 has no EMA, regression trend line, form score,
AI-generated numerical trend, or composite progression index.

### Baseline states

- Before the upstream minimum prior-history gate: no canonical baseline exists
  for the point; the metric remains in baseline-building/insufficient-history
  status according to the metrics contract.
- Once the gate is satisfied: the point has a canonical pre-match rolling
  baseline and can form a trend point.
- Fewer than 20 prior observations does not itself invalidate a baseline once
  the established minimum gate is satisfied. The available previous history is
  used, up to 20.
- A missing or N/A metric point does not count toward the gate or the 20-point
  window.

### Baseline versus raw history

The baseline is contextual interpretation, not a replacement for the factual
sequence. A UI or report may show actual values and their baseline reference,
but it must not discard the raw observation history or present the baseline as
an independent skill score.

### Baseline versus Personal Best

The rolling baseline and Personal Best are different references:

- the baseline uses the latest previous 20 observations;
- Personal Best uses the separately defined eligible history boundary in the
  Personal Records/metrics contract; and
- a point can be above its recent baseline without being a Personal Best.

Progress rebuilds must provide corrected current observations and chronology to
the Personal Records boundary. It does not redefine PB comparison or
celebration behavior here.

## 10-Match Trend Model

The canonical trend answers:

> Is my recent normal meaningfully moving for this metric?

Trend is a sequence of baseline contexts, not a label attached to one hot
match, win streak, or outlier.

### Trend point construction

For each baseline-ready observation, retain a trend point containing:

- the observation's chronology and match identity;
- the current comparison value;
- the pre-match rolling baseline value;
- the metric polarity/direction; and
- the current canonical methodology/calibration binding.

The ordered trend-point sequence is derived separately for every
`(progression_bucket, effective_role, metric_id, current_metric_version)`.

### Trend window construction

The canonical trend window is the most recent **10 eligible trend points** in
that sequence. It is complete only when all ten points are present under the
same current methodology and exposed history entitlement.

Consequences:

- the first few measured observations may build a baseline without producing
  trend points;
- a baseline-ready history with fewer than ten trend points has no canonical
  improving/stable/declining state yet;
- N/A metric points are skipped for trend-point counting, not converted to
  zero;
- an isolated outlier is retained in raw history but cannot by itself define a
  trend state; and
- a calendar gap does not remove an otherwise valid point from the window.

### Semantic evaluation

Once the window is complete, the versioned trend evaluator receives the
ordered ten-point baseline sequence, the metric's declared polarity, and the
bound calibration/methodology version. It returns exactly one of Improving,
Stable, or Declining.

The evaluator must respect semantic direction:

- a higher-is-better metric can improve when its baseline moves upward;
- a lower-is-better metric can improve when its baseline moves downward; and
- a numerical movement has no semantic direction until the metric contract
  supplies its polarity.

The exact per-metric meaningful-movement thresholds and calibration parameters
are intentionally not defined here. They are a versioned analytics/calibration
dependency. An implementation must not invent numbers, use a generic cutoff,
or publish a fifth trend state when the evaluator binding is absent.

### Raw noise and state changes

Raw metric values are recorded immediately when valid. A single unusually high
or low value does not become a product judgment. The canonical trend state is
derived only from a complete ten-point window under the bound evaluator; a
point can influence later rolling baselines without forcing a composite or
instant trend verdict.

## Trend Eligibility & States

### State contract

| State | Meaning | Required behavior |
|---|---|---|
| `Improving` | The complete ten-point window shows calibrated meaningful movement in the metric's favorable direction. | Show only for the metric whose evaluator returned it. |
| `Stable` | The complete ten-point window does not meet the calibrated improving or declining movement requirement. | Do not interpret as no activity, no skill, or no change in every match. |
| `Declining` | The complete ten-point window shows calibrated meaningful movement in the metric's unfavorable direction. | Respect lower-is-better versus higher-is-better polarity. |
| `Insufficient History` | Fewer than ten eligible trend points are available under the current history/methodology. | Do not infer a direction from partial data, streaks, or calendar activity. |

No other canonical trend state may be introduced for V1. A metric point may
still carry N/A or unavailable status; that is point-level data state, not a
fifth trend state.

### Eligibility rules

A trend state is eligible only when all of the following hold:

1. the match belongs to a supported progression bucket;
2. the match has the required effective role;
3. the metric is measured under the current metric definition;
4. the match and metric pass the upstream eligibility/integrity rules;
5. the point has a valid pre-match rolling baseline under the established
   minimum prior-history gate;
6. ten such trend points are available in the current exposed history; and
7. the current versioned evaluator/calibration binding is present.

If any point is N/A, it is omitted from the eligible trend-point count. If
omission leaves fewer than ten points, the state is `Insufficient History`.
Missing calibration binding is an implementation/release blocker, not a reason
to guess a label or add an `Unknown` state.

### Trend state is metric-level only

Each metric has its own state. The following is valid:

```text
CS @10    — Improving
Farming   — Stable
Scaling   — Improving
Survival  — Declining
```

The set of metric states does not imply a role-level state.

## Sparse Activity / Inactivity

Progression is match-based, not calendar-based.

If a player has seven Carry matches, stops for three months, and then plays
three more Carry matches in the same bucket:

- the three later observations follow the seven earlier observations in
  chronology;
- the gap itself contributes no observation and no penalty;
- baseline history is not reset or weakened;
- trend history is not reset or expired; and
- the later observations may complete a ten-point trend window once the
  existing baseline gate and ten eligible trend-point requirement are met.

The product may show recency metadata such as last role activity, time since
last match, or an inactive/stale context. Recency must not be translated into
Improving, Stable, or Declining and must not change the underlying math.

There is no V1 time decay, inactivity penalty, hard trend expiry, season reset,
or new progression epoch caused by a calendar gap.

## History Horizon & Entitlement Boundary

### No Progress-owned cutoff

Progress & History does not define “last 30 matches,” “last 90 days,” “last
season,” or any other independent canonical retention horizon.

The baseline and trend have bounded computational windows, but the underlying
history can extend across all retained/entitled eligible observations. A
presentation filter is not a retention rule and cannot change the canonical
baseline or trend input set unless the entitlement contract explicitly changes
what history is exposed.

### Entitlement input contract

The Free vs Pro Boundary SSOT supplies the current exposed history set. Progress
must:

1. use every eligible observation in that exposed set that belongs to the
   requested bucket, role, and metric;
2. preserve the same chronology and methodology regardless of entitlement;
3. avoid treating hidden or unavailable history as zero;
4. show `Insufficient History` when the exposed set no longer contains enough
   trend points; and
5. recompute current derived state when the exposed set changes, without
   creating a new analytical epoch.

If underlying history is retained but temporarily not entitled, it is outside
the current canonical input set and can become available again when entitlement
is restored. If source telemetry is permanently unavailable under the current
metric definition, the affected metric point is N/A rather than a preserved
old-definition value.

### Entitlement changes

When entitlement is reduced:

- do not delete or fabricate observations merely to keep the UI populated;
- rebuild current baseline/trend state from the newly exposed history;
- allow a previously valid trend to become `Insufficient History`; and
- keep the change separate from analytical decline.

When entitlement is expanded or restored, re-admit the newly exposed retained
history, replay it in chronology under the same canonical methodology, and
restore any state supported by the resulting evidence. This is a data-scope
change, not a performance event.

## Allowed Summaries

V1 may summarize each metric independently and descriptively, for example:

- “CS @10 — Improving.”
- “Farming is Stable; Survival is Declining.”
- “Laning and scaling are moving up while survival has slipped,” when each
  statement is directly traceable to the named metric states and values.

Any summary must remain evidence-bound:

- name the underlying metrics when combining observations in prose;
- preserve metric polarity and N/A/Insufficient History status;
- avoid causal claims that the metric contract does not support; and
- never turn a missing metric into a favorable or unfavorable judgment.

## Prohibited Composite Judgments

V1 must not collapse multiple metrics into any of the following:

- one role trend;
- one overall player progress curve;
- a role score or player score;
- a grade, rating, percentage, medal, or performance number;
- a universal improvement verdict;
- a cross-role normalized rank; or
- a Standard/Turbo-normalized score.

The following are not canonical V1 behavior:

```text
“Your Carry performance is improving.”
“Carry Score: 78.”
“3 of 4 metrics improved, therefore your Carry is trending up.”
```

An AI or content layer may describe metric-level evidence, but it may not
manufacture a composite verdict, hidden weighting, or causal explanation.

## Recalculation & Canonical Methodology

### Migration principle

There is one active canonical methodology for current Progress. A change to
baseline definition, trend horizon, trend evaluator/calibration, metric
calculation, or compatible eligibility interpretation must not leave two active
mathematical eras in one history.

The migration contract is:

1. identify and version the new canonical methodology;
2. preserve immutable raw source evidence and prior audit/provenance;
3. determine the retained source history in scope, then apply the current
   entitlement boundary when materializing an account's current view;
4. recompute compatible metric observations in chronology order;
5. represent unsupported current points as N/A, never as old-method values;
6. rebuild baselines from the current previous-history rule;
7. rebuild trend points and states from the current trend rule/calibration;
8. rebuild directly dependent current Progress state and current indexes;
9. make the new canonical state coherent to consumers at cutover; and
10. retain audit metadata showing the old/new methodology and affected scope.

Consumers must not observe a mixture in which earlier points use the old
baseline/trend/metric method and later points use the new method merely because
the replay was processed in separate workers. An incomplete migration keeps
the previous coherent canonical state or remains unavailable to the affected
consumer; it does not publish a partial mixed timeline.

Migration is not a season reset, inactivity reset, or new progression epoch.

### Derived-method migration

For changes such as:

- previous-20 window size;
- baseline aggregation statistic;
- trend horizon;
- trend estimator;
- meaningful-movement threshold;
- calibration/version binding; or
- directly dependent canonical comparison logic;

replay retained compatible history chronologically using the new method. The
raw source observations remain factual. Baselines, trend points, trend states,
and current comparisons may change because they are derived.

Examples:

- If the baseline window changes from 20 to 30, rebuild every affected
  baseline; do not leave early points on 20 and later points on 30.
- If the trend horizon changes, rebuild eligibility and states for every
  affected metric history; do not show a V1 ten-point state beside a newer
  horizon state in one canonical series.
- If the calibration threshold changes, re-evaluate existing complete windows;
  raw values and source observations do not change, but Improving/Stable/
  Declining may change.

### Metric-definition migration

If a metric formula, input interpretation, denominator, boundary, direction,
normalization, or zero/N/A rule changes materially, the metric version and
canonical methodology binding must change according to the metrics contract.

For each retained historical match:

- if required source telemetry remains available and compatible, recompute the
  observation under the new metric definition;
- if the new definition needs telemetry the match does not contain, represent
  the current metric point as N/A/unavailable under the new definition;
- do not place the obsolete value beside the new-definition value in one
  canonical trend window; and
- rebuild baseline/trend state from the resulting current points.

Historical audit records may retain the prior derived value and methodology for
reproducibility. That audit record is not an active second progression series.

If a Dota patch changes the game but does not change the declared metric
semantics or required telemetry, it does not reset Progress. If the metric
semantics materially change, use the migration contract above rather than
silently mixing eras.

### Missing historical telemetry

Missingness is handled per metric and per match:

- a valid match with missing inputs for one metric receives metric-level N/A;
- N/A points do not count toward the baseline gate, 20-point baseline window,
  or ten-point trend window;
- the absence of one metric does not erase other valid metric points from the
  same match; and
- if missingness leaves too little history, the affected metric becomes
  baseline-building or `Insufficient History`, never an inferred trend.

If the entire source match is unavailable, it remains outside Progress until
the lifecycle recovery contract admits trustworthy evidence. Once recovered,
it is inserted at its actual chronology position and processed under the
current methodology.

### Rebuild scope

The minimum affected scope is the smallest canonical dependency closure:

- a metric-definition or calibration change may affect every retained point
  for that metric across all applicable roles and buckets;
- a role correction affects the old and new role histories in the match's one
  bucket, from the corrected match forward;
- a late recovery affects the recovered match's track and future current state,
  subject to lifecycle snapshot immutability;
- an entitlement change affects the currently exposed account history; and
- an unrelated role or bucket is not rebuilt merely because another track
  changed.

“Rebuild everything” is not a substitute for identifying the affected metric,
track, bucket, and chronology boundary.

### Determinism and idempotency

For a fixed account, source history, effective-role assertions, exposed history
set, and methodology version:

- sorting produces one order;
- the same point identity is admitted at most once;
- each baseline uses the same prior observations;
- each trend window selects the same ten points;
- the same polarity/evaluator returns the same state; and
- running the rebuild twice produces no additional observations, PB events, or
  notifications.

At-least-once processing is allowed internally. It must not create duplicate
canonical points or duplicate delivered events.

### Current state versus immutable events

Recalculation may change current canonical baseline, trend, and PB/index state.
It must not:

- rewrite immutable raw provider/source evidence;
- retract a previously delivered PB/celebration/notification event;
- resend a celebration only because the current history was rebuilt; or
- present a historical delivery event as proof that the current canonical
  Progress state is unchanged.

The Personal Records and lifecycle contracts own how superseded/auditable
events are presented.

## Role Correction Effects

Role correction is an explicit upstream input, not a Progress inference.

When a match changes effective role, for example:

```text
Standard Carry → Standard Support
```

Progress must:

1. keep the match in the same Standard/Turbo bucket;
2. remove its role-scoped derived metric points from the old role history;
3. recompute role-applicable metric points under the current canonical metric
   definitions and source telemetry for current Progress state;
4. insert measured points or legitimate N/A points into the new role history
   at the match's original chronology position;
5. replay affected old-role and new-role baselines, trend points/states, and
   directly dependent current indexes from that position forward;
6. leave unrelated roles, unrelated metrics, and the other bucket unchanged;
7. preserve classifier/confidence metadata without treating it as a second
   role; and
8. keep already delivered PB/celebration/notification events append-only and
   auditable rather than retracting or re-sending them.

If the corrected role lacks telemetry required for one of its metrics, that
metric is N/A under the new role; the old-role value is not copied across to
make the new role look complete.

If the latest assertion is identical to the current effective role, the
correction is a no-op. Repeating a changed assertion is idempotent. A later
assertion supersedes the earlier assertion according to Role Resolution and
causes one deterministic replay from the affected match.

The current canonical methodology applies to the rebuilt current Progress
state. A previously finalized Match Lifecycle snapshot may retain the original
metric-version lineage required for its immutability contract; that snapshot
lineage is audit history, not a second active Progress methodology. No role
correction creates parallel canonical histories.

## Recovered / Late Historical Matches

### Recovery before downstream finalization

When a previously unavailable historical match recovers before dependent
same-bucket progression has finalized:

- validate the source and chronology;
- insert the match at its actual chronology position;
- admit only eligible measured metric points;
- keep metric N/A where telemetry is insufficient;
- replay affected downstream state oldest-to-newest; and
- release later matches only after the corrected chronological dependency is
  resolved.

### Recovery after downstream finalization

Match Lifecycle owns the immutability boundary for already-finalized match
snapshots. If an earlier match recovers after later snapshots or delivered
events exist:

- insert the recovered match into current visible history at its true position;
- do not silently rewrite already-finalized Match Detail comparison snapshots
  solely because of the recovery;
- do not retract or re-send already-delivered PB/celebration/notification
  events;
- allow the recovered trustworthy observation to inform current best-known
  indexes and future comparisons under the lifecycle/records contracts; and
- use the current canonical methodology for any Progress state that is
  explicitly rebuilt.

The fact that an old snapshot remains immutable does not permit appending the
recovered match at the end of the canonical history. Current history ordering
must remain chronological even when historical presentation snapshots preserve
what was previously published.

## N/A and Insufficient-History Behavior

### N/A is not zero

Use numeric zero only when the metric contract establishes that the measured
numerator is genuinely zero with valid inputs and opportunity. Use N/A when a
metric cannot be meaningfully calculated because required telemetry, a
checkpoint, a denominator, identity, or current-definition input is absent or
invalid.

Never convert missing telemetry, a zero denominator, a malformed stream, or a
metric-definition incompatibility into zero.

### Baseline insufficiency

When the established minimum prior-history gate is not satisfied:

- retain the raw measured observation;
- show/store the metric as baseline-building or insufficient-history according
  to the metrics contract;
- omit the baseline comparison for that point; and
- do not count it as a trend point.

The observation still remains part of factual history and may contribute to a
later point's baseline once enough prior measured observations exist.

### Trend insufficiency

When a metric has a baseline but fewer than ten eligible trend points:

- show the available actual values and baseline context where supported;
- show `Insufficient History` for canonical trend;
- do not infer a label from the partial window, hot streak, win streak, or
  calendar activity; and
- continue accumulating points chronologically.

### N/A inside otherwise valid history

If one metric is N/A in the middle of an otherwise valid role history:

- preserve the match and N/A reason in general history;
- preserve other measured metrics from the same match;
- exclude only that metric point from baseline and trend counts; and
- use the next eligible measured point to complete a later window.

N/A does not break the entire role history and does not become a zero-valued
placeholder.

### History becomes sparse after scope/method change

If entitlement reduction, telemetry loss, or metric-definition migration
removes points from the current eligible set, recompute counts from the
remaining current points. A trend may become `Insufficient History`, and a
baseline may return to baseline-building, without being labeled Declining.

## Product/UI Semantic Requirements

This is not a visual design specification. Any product surface consuming
Progress must nevertheless be able to represent the following semantics:

1. **Context:** the selected Standard/Turbo bucket and effective role are
   visible or unambiguous. Switching context changes the selected history; it
   does not merge tracks.
2. **Chronology:** per-metric observations can be read in chronological order.
3. **Actual versus reference:** a raw/display value is distinguishable from
   the rolling baseline and from a match-level pre-match comparison baseline.
4. **Trend state:** each metric can show its own Improving, Stable, Declining,
   or Insufficient History state.
5. **N/A:** a metric point can be shown as N/A with an honest reason or omitted
   from a derived visualization without being rendered as zero.
6. **Sparse activity:** recency can be shown separately from trend state.
7. **Entitlement:** a reduced history set can be represented without implying
   that hidden history was poor performance.
8. **No fabricated fill:** missing story/copy/metric data is omitted or marked
   unavailable according to the upstream contract; it is not invented to keep
   a chart or card populated.
9. **General history:** a combined match list may contain all roles and modes,
   but Progress calculations remain separately scoped.
10. **Filters:** 30D, 90D, All, weekly, monthly, or other controls are
    presentation/report windows unless another versioned contract explicitly
    declares a different computation. They do not redefine V1 baseline/trend
    math.

## Cross-SSOT Ownership

| Concern | Owner | Progress boundary |
|---|---|---|
| Match discovery, source validation, readiness, chronology blocking, retry, and recovery | Match Lifecycle V1 | Consume only admitted lifecycle results and chronology. |
| Standard/Turbo mode classification | Match Lifecycle / metrics contract | Use `STANDARD` or `TURBO`; never infer a third bucket here. |
| Role classification and explicit role assertion | Role Resolution & Correction | Consume exactly one `effective_role`; never reclassify here. |
| Role metric formulas and raw/comparison semantics | Role Metrics & Personal Baselines V1 | Consume the current metric registry/version and its measured/N/A result. |
| Minimum baseline gate and previous-20 median | Role Metrics & Personal Baselines V1 | Use the established gate and median; do not replace it. |
| Trend evaluator thresholds/calibration | Analytics / calibration contract | Consume a versioned evaluator and polarity; do not invent numeric thresholds here. |
| Current PB/index and PB presentation | Personal Records SSOT | Provide rebuilt current observations; preserve delivered event immutability. |
| Free/Pro history amount and access | Free vs Pro Boundary SSOT | Use the exposed history set; do not define entitlement. |
| Match Detail comparison snapshot | Match Detail / Match Lifecycle | Use the baseline that existed before that match; do not substitute a later baseline. |
| Reports, recaps, and calendar windows | Report/recap SSOT | May filter or summarize; may not redefine canonical Progress. |
| Screen layout, chart style, colors, motion, and navigation | Product/UI design contracts | Represent these semantics without changing the math. |

## Edge Cases

| Case | Required behavior |
|---|---|
| User alternates roles frequently | Each match enters only its effective-role history. Alternation creates sparse role histories; it does not create an all-role sequence. |
| User plays mostly Turbo and occasional Standard | Turbo observations use only Turbo history; Standard observations use only Standard history. Neither bucket affects the other or waits on the other. |
| User stops a role for six months and returns | Preserve chronology and prior history. No reset, decay, expiry, or inactivity penalty; show recency separately if desired. |
| Enough matches for a baseline but fewer than 10 trend points | Show the pre-match baseline where available and `Insufficient History` for trend. Do not infer a direction. |
| One metric is N/A inside otherwise valid history | Preserve N/A and its reason; exclude only that metric point from baseline/trend counts; keep other metrics from the match. |
| Historical match is later recovered | Insert by true chronology. Before downstream finalization, replay affected state; after finalization, obey lifecycle snapshot immutability while allowing current admitted state/future comparisons per contract. |
| Retained match is role-corrected | Keep its bucket, move it from old to new role history, replay affected old/new histories from that point, and leave unrelated tracks unchanged. |
| Baseline definition changes globally | Version the methodology and replay all retained compatible history in scope. Do not mix old and new baselines. |
| Trend horizon changes globally | Recompute trend-point eligibility and all states under the new horizon. Do not preserve old-horizon labels beside new ones. |
| Trend calibration threshold changes | Re-evaluate complete windows under the new calibration. Raw observations remain unchanged; states may change. |
| Metric definition changes and all historical telemetry is available | Recompute all compatible historical metric points under the new definition, then rebuild baseline/trend state. |
| Metric definition changes and only some historical telemetry is available | Recompute supported points; mark unsupported historical points N/A under the new definition; never retain obsolete values in the current trend. |
| Free/Pro entitlement reduces available history | Rebuild from the exposed set. State may become baseline-building or `Insufficient History`; this is not Declining and does not delete retained source facts. |
| Previously delivered PB/celebration no longer aligns after rebuild | Keep the delivered event append-only/auditable; update current canonical PB/index through the Personal Records boundary; do not retract or re-send. |
| Same rebuild runs twice | Same source/methodology/entitlement yields the same state with no duplicate observations, PB events, or notifications. |
| One role history changes while unrelated role histories exist | Rebuild only the affected role/metric dependency closure. Unrelated roles remain byte-for-byte semantically unchanged. |
| Standard history changes while Turbo history exists | Rebuild only Standard. Turbo observations, baselines, trend states, queues, and indexes do not change. |
| A metric is numerically lower but lower-is-better | Use the metric's declared polarity; favorable downward movement can be Improving. |
| A single hot match arrives | Record it as raw evidence. It cannot create a trend state before a complete ten-point trend window and calibrated evaluation. |
| Calendar filter shows 30D or 90D | Treat it as presentation/report scope only unless a separate versioned contract says otherwise. Do not recalculate canonical trend from the filtered calendar slice. |
| A role has no measured values under the current metric definition | Show no fabricated observations; the metric remains N/A/unsupported or insufficient according to its upstream registry and available state. |

## Acceptance Criteria / Invariants

The document is implemented correctly only if all of the following hold:

### Partition and ordering

- Standard and Turbo produce separate histories and separate derived state.
- Carry, Mid, Offlane, and Support produce separate histories inside each
  bucket.
- Position 4 and Position 5 both map to Support after upstream role
  resolution.
- `Standard: Carry, Carry, Support, Carry` produces three Standard Carry
  observations and one Standard Support observation, not four mixed points.
- Every history is ordered by `(provider_started_at,
  provider_source_match_id)` and not by arrival or worker completion.
- A recovered historical match is inserted at its true chronology position.

### Baseline and trend

- The current match is excluded from its own baseline.
- A baseline uses at most the latest 20 previous eligible measured observations
  with the same bucket, role, and metric identity.
- The upstream minimum prior-history gate is honored.
- N/A points and progression-ineligible matches do not count toward baseline or
  trend eligibility.
- A trend point has a valid pre-match baseline under the current methodology.
- Fewer than 10 eligible trend points produces `Insufficient History`.
- Exactly 10 eligible trend points permits only the versioned evaluator to
  return Improving, Stable, or Declining.
- Higher/lower metric polarity is honored; numerical direction is not assumed.
- No calendar window, inactivity gap, win/loss streak, or single outlier
  changes canonical eligibility.

### Rebuild and versioning

- A methodology change replays retained compatible history under one current
  method and does not expose mixed math.
- Metric-definition changes recompute supported history and mark unsupported
  historical points N/A rather than retaining incompatible values.
- Role correction changes only the affected same-bucket old/new role closure.
- Standard changes do not alter Turbo, and one role change does not alter
  unrelated roles.
- Re-running a rebuild is idempotent.
- Raw/source facts and audit lineage remain distinguishable from current
  derived state.
- Delivered PB/celebration/notification events remain append-only and are not
  retracted or re-sent by a rebuild.

### Product meaning

- The product can represent actual values, baseline context, N/A, and trend
  state separately.
- The product never displays a composite role/player progression score or
  universal progress curve.
- Missing information is omitted or marked unavailable rather than fabricated.
- Entitlement changes do not masquerade as performance change.

## Explicit Non-Goals

Progress & History V1 does **not** define:

- overall skill;
- an MMR replacement;
- an all-role score or universal player progress curve;
- a composite role performance score;
- cross-role normalization;
- Standard/Turbo normalization;
- win/loss-based progression;
- an AI judgment score;
- a calendar-based canonical trend;
- time decay or an inactivity penalty;
- season resets;
- an arbitrary Progress retention cutoff;
- the Free vs Pro entitlement amount or subscription logic;
- Personal Record UX, achievement, or challenge logic;
- report generation;
- monthly or weekly recap semantics;
- exact trend significance thresholds or calibration numbers;
- exact trend visualization, layout, colors, copy, or motion;
- provider acquisition, database schema, API schema, or queue architecture;
- role classification or role-confidence logic; or
- a new analytical source or metric definition.

## Deferred / Calibration-Owned Decisions

The following are intentionally outside this SSOT and must be supplied by the
owning contract before implementation claims a calibrated trend result:

1. exact per-metric meaningful-movement thresholds;
2. the versioned trend estimator/calibration artifact used on the ten-point
   baseline sequence;
3. calibration evidence and release identity for any evaluator change;
4. the amount and shape of history exposed by Free versus Pro; and
5. exact visual treatment of baseline, N/A, recency, and trend states.

These are not alternate product behaviors. Until a versioned evaluator is
bound, the implementation must not guess a threshold or publish an invented
state. A future evaluator change is a canonical methodology migration and must
be applied retroactively to retained compatible history.

No additional product decision is required to implement the partitioning,
ordering, baseline boundary, ten-point eligibility rule, N/A behavior,
inactivity behavior, entitlement boundary, role-correction consequences, or
methodology migration contract in this document.
