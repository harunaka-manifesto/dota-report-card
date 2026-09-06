# V7 runtime capability payload — specification

```text
STATUS: specification for implementation
SCHEMA: v7-capability-payload-1.0.0
```

The contract the V7 runtime returns. **Capability-oriented, not screen-oriented**:
it says what is true about a player, never what to show first. Frontend owns
story, sequence and emphasis.

## 1. The frozen-population problem, and how the runtime solves it

**This is the constraint that shapes the whole runtime.**

Every V7 analytical output is *population-relative*:

- A Finding's `z` is `(δ̂ − μ_d) / τ_d`, where `μ_d` and `τ_d` are fitted across a
  cohort of players. Its `reliability` needs `τ_d` and the dependence inflation
  `D_d`.
- A recommendation's standardized gap divides by `s_d`, the dimension's pooled
  match-to-match spread across the cohort.
- Every archetype axis is cut at population quantiles **within a mode stratum**.

A runtime request has **one** player. It cannot fit a population. Recomputing
population parameters per request would make each player their own population,
which is meaningless — `τ` of one player is zero and every `z` becomes
undefined.

**Therefore the runtime loads frozen population parameters fitted once on
DISCOVERY and shipped as a versioned data artifact.** The artifact is
`services/api/app/player_analysis_v7/data/population-parameters-<version>.json`,
generated from the existing pipeline. It contains, per dimension: `mu`, `tau`,
`dependence_inflation`, and for recommendation dimensions `dimension_scale`;
plus, per mode stratum, the archetype cuts (`tempo_low`, `tempo_high`,
`participation_low`, `deaths_median`, `lighthouse_cut`, `closer_cut`).

Rules:

1. The artifact is **generated, not hand-written**, from the same code paths the
   research evidence came from. A test regenerates and diffs it.
2. Its version is part of provenance. A payload computed against different
   population parameters is not comparable to one computed against these.
3. Changing it is an analysis-version change and invalidates persisted results.
4. It is **never** refitted from live pilot users during the pilot — that would
   silently move everyone's baseline and make two reports incomparable.

## 2. Payload shape

Reuse the existing typed models where they already exist and are approved:
`Finding`, `Recommendation`, `RecommendationObservation`, `ArchetypeSection`,
`RankDisplay` from `report_contract.py`. Do not redefine them.

```text
V7CapabilityPayload
  schema_version : str            # "v7-capability-payload-1.0.0"
  metadata       : ReportMetadata
  player_context : PlayerContext
  findings       : list[Finding]           # 0..5, backend-selected and gated
  recommendation : Recommendation | None
  archetype      : ArchetypeSection | None
  availability   : dict[CapabilityKey, CapabilityAvailability]
  refusals       : list[Refusal]
  provenance     : V7Provenance
```

**`supporting_facts` is deliberately absent in 1.0.0.** The conceptual shape in
the phase brief includes it, but nothing in the backend computes history
statistics, hero contrasts, death profiles or telling-sign minutes today. An
empty bag would invite a design agent to fill it. When a producer exists, it is
an additive schema change.

### ReportMetadata
`generated_at` (ISO-8601 UTC), `window_days`, `window_start`, `window_end`
(epoch seconds), `matches_total`, `matches_analysed`, `matches_with_event_detail`,
`acquisition_depth`.

### PlayerContext
`dominant_mode: "STANDARD" | "TURBO" | None` — the frame every archetype output
is expressed in; `rank_display: RankDisplay | None` — **display-only, fenced**.

### CapabilityAvailability
`status: "available" | "refused"`, `refusal_code: RefusalCode | None`,
`detail: str | None` (factual backend state, **never user-facing copy**).

### Refusal
`capability: CapabilityKey`, `code: RefusalCode`,
`retry_may_change: bool` (would running again later differ),
`more_matches_may_change: bool`, `permanently_unsupported: bool`.

Keeping the machine-readable code separate from copy is the point: frontend
decides presentation, backend states fact.

## 3. Enums

`CapabilityKey`: `findings`, `recommendation`, `archetype`, `dominant_mode`,
`rank_display`.

`RefusalCode`:

| code | meaning | retry? | more matches? | permanent? |
|---|---|---|---|---|
| `profile_private` | account anonymous or private | yes | no | no |
| `insufficient_history` | too few product-context matches | yes | yes | no |
| `insufficient_parsed_support` | too few parsed matches | yes | yes | no |
| `no_dominant_mode_stratum` | neither mode reaches 20 matches | yes | yes | no |
| `insufficient_event_support` | too few matches in the dominant stratum | yes | yes | no |
| `insufficient_sessions` | fewer than 8 sessions of 3+ matches | yes | yes | no |
| `insufficient_wins_or_losses_per_arm` | no eligible dimension has 15 wins and 15 losses | yes | yes | no |
| `no_valid_opportunities` | no dimension has enough support | yes | yes | no |
| `fewer_than_floor_dimensions` | fewer than 3 dimensions qualify | yes | yes | no |
| `acquisition_failed` | provider data could not be obtained | yes | no | no |
| `not_collected` | capability not gathered for this account | yes | no | no |

## 4. Invariants the model must enforce

Validators, not documentation:

1. `len(findings) <= REPORT_SLOTS` (5).
2. `findings` is ordered by `(-score, dimension_key)`.
3. No `dimension_key` may be a withheld dimension:
   `transfer_risk`, `transfer_activity`, `lane_to_map`,
   `lane_recovery_participation`, `side_sensitivity`. **Fail closed** — a
   zero-signal dimension reaching a payload is a defect, not a display choice.
4. Every `CapabilityKey` appears exactly once in `availability`.
5. A capability whose `availability.status` is `refused` must have a
   `refusal_code`, and a matching entry in `refusals`. A capability that is
   `available` must carry no refusal.
6. `recommendation is None` ⟺ `availability["recommendation"].status == "refused"`.
   Same for `archetype`.
7. `findings == []` ⟺ `availability["findings"].status == "refused"`.
8. The D1 gate is respected: beyond the first `FINDING_FLOOR` entries, a Finding
   is present only if `score > SCORE_LINE` **or** it is the only representative
   of its section.
9. Serialised payload contains no `v7p_` and no key matching the forbidden-field
   tokens.
10. No strength band field exists.

## 5. What must not appear

No percentile, rank-derived, or "top X%" field. No `strength_band`. No internal
pseudonym or research identifier. No UI ordering hint beyond the analytical
ranking. No causal language in any backend-supplied string.

## 6. Assembler contract

`app.player_analysis_v7.assembly.assemble_capability_payload(...)` orchestrates
and **computes nothing**. It calls the canonical research implementations for
inference, ranking, selection, the D1 gate, recommendation selection and
archetype assignment, and it loads population parameters from the frozen
artifact.

Any statistical expression appearing in the assembler is a defect. The test for
this is mechanical: the assembler module may not contain arithmetic on
estimates.
