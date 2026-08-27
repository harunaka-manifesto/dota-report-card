# Existing-finding reassessment

Every current public Element, finding family and semantic outcome, reassessed
against verified STRATZ evidence. Classifications are the brief's A–G.

Verified from code at `services/api/app/player_analysis_v6/` and
`player_analysis_v61/` on 2026-08-27, not from docs.

---

## 0. Three findings that change everything below

### 0.1 The role problem is a vocabulary gap, not a proxy-accuracy problem

The brief frames `role_hint` as "the weakest link in V6.1" and cites a 17.6%
lane-vs-position disagreement. The truth is worse and differently shaped.

`ROLE_HINTS` (`ingestion/summary_normalize.py:27`) is:

```python
{1: "carry", 2: "mid", 3: "offlane", 4: "jungle", 5: "roamer"}
```

**The vocabulary has one coarse support-adjacent token and no way to reach it
from STRATZ.** `roamer` exists (`ROLE_HINTS[5]`, and in
`SUPPORTED_LANE_CONTEXTS` = `{carry, mid, offlane, roamer, safe_lane, mid_lane,
off_lane, unknown}`), and the module's own comment concedes the endpoint
"cannot reliably split hard vs soft support without detail evidence". So the
accurate claim is narrower than "no support concept exists" — but it lands in
the same place operationally, for two reasons. First, `roamer` is reachable only
via OpenDota's `is_roaming` flag, and **STRATZ `MatchLaneType` has no roaming
value at all** (`SAFE_LANE`, `MID_LANE`, `OFF_LANE`, `JUNGLE`), so under a
lane-shaped STRATZ mapping the token is unreachable. Second, `roamer` cannot
distinguish `POSITION_4` from `POSITION_5`, which is the distinction supports
care about.

Measured on the specimen (`analyze.py` §6), for the 91 parsed rows where both
`lane` and `position` exist:

- 25 rows have STRATZ `role` ∈ {`HARD_SUPPORT`, `LIGHT_SUPPORT`}
- **25 of those 25** map, under the lane-shaped vocabulary, onto a word
  `ROLE_HINTS` treats as a core role
- breakdown: 12× `SAFE_LANE`+`HARD_SUPPORT` → "carry", 13× `OFF_LANE`+`LIGHT_SUPPORT` → "offlane"

Within the V6.1-**eligible** matches, **20 of 49 (41%) are supports** — or 20 of
45 (44%) under the stricter reading of the still-BLOCKED `LeaverStatusEnum`
mapping. Every one of them is currently representable only as a core.

**Why this has not already broken production:** OpenDota `lane_role` coverage is
~2.5%, so `_role_hint()` returns `(None, None)` on almost every row, the `role`
eligibility flag fails on `missing_role_hint`, and `lane_context` is `None` —
so matches fall through the baseline hierarchy to the `overall` cell. The
misclassification is **latent**, not active.

**The trap this creates for the sibling migration document:** mapping STRATZ
`lane` onto `ROLE_HINTS` at 93% coverage *activates* a broken vocabulary at
scale. A provider swap that preserves V6.1's meaning must either keep lane dark
or adopt `position`/`role` — and adopting `position`/`role` is a new lineage,
not parity. **`01-luna-max-provider-migration.md` must not do this.** This is
the one cross-document warning in this research.

### 0.2 The 128-feature catalog is a shape, not a design

The brief says: *"a large amount of design work already exists here, and several
of your candidates will already have a slot."* Read from source, that is not
accurate, and building on it would waste effort.

`supporting_signals.py::_catalog()` **generates** the 128 entries:

```python
for prefix, (name, classification, fields, consumers) in _GROUPS.items():
    for index in range(1, 17):
        code = f"{prefix}{index:02d}"
```

Eight groups × sixteen indices. Within a group every entry is **identical** —
same `source_fields`, same `OpportunityContract`, same `estimator_version`,
same consumers. `A01` and `A16` are indistinguishable. The only individuated
entries are the eight in `_REJECTED`.

The catalog satisfies a validator (`len(keys) == 128`) and declares a taxonomy.
It does not contain 128 designed signals, and there is no slot for
"buys a defensive item earlier after a bad lane" waiting to be filled. Candidate
generation below therefore designs from the data, and maps onto the *group
classifications* rather than pretending to fill numbered slots.

The eight `_REJECTED` entries **are** load-bearing. Parsed data touches four of
them, but overturns the stated *reason* for only two (`X13`, `M12`):

| code | stated reason | STRATZ effect |
|---|---|---|
| `X13` | "actual role cannot be inferred from sparse summary lane fields" | **Overturned.** `position` at 91%, `role` at 93%. The reason no longer holds. |
| `X14` | "positioning is unavailable in summary history" | Available via `playerUpdatePositionEvents` — but `positioning` is in `FORBIDDEN_FREE_TERMS`. Availability ≠ publishability. |
| `X15` | "aggression or intent is not observable" | Still not observable. Banned. Unchanged. |
| `X16` | "death quality is not observable" | Still not observable. Banned. Unchanged. |
| `M09` | "rank/MMR conditioning is forbidden" | Unchanged, permanently. |
| `M10` | "local time cannot be inferred from UTC and cluster" | `regionId`/`clusterId` present, but inference is still inference. Unchanged. |
| `M11` | "patch causality is not identifiable" | Causality still not identifiable. But `gameVersionId` at 100% makes patch *stratification* possible for the first time. Different thing; do not conflate. |
| `M12` | "final inventory is not item-build identity" | **Reason overturned.** `itemPurchases {time itemId}` gives real build order and timing. But `item timing` is in `FORBIDDEN_FREE_TERMS`. |

Two rejections (`X13`, `M12`) had their stated *reasons* invalidated by parsed
data while their *language guards* remain. That gap is an owner decision, not an
engineering one — see §4.

### 0.3 Six of the 25 public branches cannot fire on the fixture path

Independent of STRATZ, and **narrower than it first looks — read the
qualification below before acting on it.** In
`player_analysis_v61/family_statistics.py::v61_branch_p_values`, these branch
p-values are hard-coded to `1.0`:

`localized_function_bottleneck`, `adjustment_without_recovery`,
`same_expression_different_results`, `different_expression_same_results`,
`selection_only_drift`, `bounded_stopping_response`.

**Qualification.** `dna_assembly_v61.py:1233-1241` selects
`production_branch_p if production_calibration else v61_branch_p_values(...)`.
The production path, `v61_production_family_branch_p_values`, computes **every**
`public_candidate` branch from bootstrap samples via `_production_p`, with no
hard-coded `1.0`. So the six branches are dead **on the fixture/synthetic path
only** — which is the path in use while V6.1 runs behind disabled flags with
`fixture_synthetic_only` reporting. They are not permanently dead.

Additionally, in `player_analysis_v6/pipeline.py::_signal_inputs` (lines 230,
245, 254, 263) the transfer/post-loss/drift component loops read
`thresholds.get(f"..._delta")` — raw dict access, bypassing `threshold_for()`'s
alias table — and append `1.0` when absent. None of those `*_delta` keys exist
in `DEFAULT_THRESHOLDS`. Without an injected calibrated threshold artifact,
`post_loss_response` and `session_drift` are unpublishable.

Neither of these is a STRATZ finding and neither is this document's job to fix.
The consequence that matters here: **before T1-B's backtest can mean anything,
confirm which path production actually runs.** If it runs the fixture path,
`post_loss_response` cannot fire and the upgrade has nothing to improve.
Flagged for the owner as a prerequisite, not asserted as a permanent defect.

---

## 1. Public Elements

| Element | existing proxy | STRATZ opportunity | verdict | version impact | reason |
|---|---|---|---|---|---|
| `breadth` | Shannon effective hero count over `hero_id` | none direct; `heroIds` filter is acquisition-only | **KEEP unchanged** (G for new work) | `elements` `compatible` | The measure is already direct. Its *input population* changes (`01-field-inventory.md` §3) but the formula is correct and role-neutral. Nothing STRATZ offers improves counting heroes. |
| `toolkit` | editorial taxonomy over hero ids, `min_coverage=0.80` | `position` + `role` give **observed** functional context per match | **B. REPLACE_PROXY** (partial) | `elements` `changed`, new `toolkit` normalization version | Today `toolkit` asks "what jobs do these heroes usually do". With `position`/`role` it can ask "what jobs did this player actually perform". A Crystal Maiden played POSITION_1 is currently counted as a support job. This changes what the number means → new lineage. |
| `involvement` | context-adjusted `(kills+assists)/minute` | `radiantKills`/`direKills` give a real **denominator**; `position`/`role` give role-fair baselines | **B. REPLACE_PROXY** | `elements` + `context_baseline` `changed` | A rate with no denominator is confounded by team tempo and duration. Kill-participation share (`03-candidate-catalog.md` §5, T2-A) measures the same concept with a denominator. Verified computable: 43 participation instants / 68 team kills = 63.2% on A2. |
| `finishing` | `kills / (kills + assists)` | same events, plus team-kill denominator | **A. ENHANCE_EXISTING** | `elements` `compatible` | The formula is already a share and already denominator-bearing. STRATZ adds role-fair baselines, not a better measure. **Note:** `finishing` appears in **no** finding family's `required` tuple. Nor does `consistency`. The `required` tuples are `("breadth","toolkit")`, `("transfer","breadth_or_toolkit")`, `("response","familiarity_or_tempo")`, `("involvement","death_exposure")`, `()`. **Two** public Elements are measured and never tested. Independent gap. |
| `death_exposure` | context-adjusted `deaths / 10min` | `deathEvents{time}`, `radiantNetworthLeads` for game-state context, `position`/`role` baselines | **A. ENHANCE_EXISTING**, not replace | `context_baseline` `changed` | Deaths per ten minutes is a defensible direct count. What parsed data adds is **when** and **in what game state** — and that is a new sub-finding (`03-candidate-catalog.md` §5, T2-B), not a better version of this Element. Do not fold game state into the Element; it would smuggle a causal story into a scalar. |
| `transfer` | multi-signal agreement between familiar and stretch hero contexts, outcome/activity/survival | `position`/`role` distinguish **hero stretch** from **role stretch** — currently conflated | **C. NEW_SUBFINDING** under `transfer`, Element itself KEEP | `findings` `changed`, `elements` `unchanged` | The Element's construction is sound. But "new hero, same role" and "same hero, new role" are different transfers and V6.1 cannot tell them apart. With a 41% support share on the specimen, role variety is high — though only 2 of 18 heroes are played in both a core and a support role, so *same-hero* role-stretch may be rarer than it looks (see `03-candidate-catalog.md` §4b). Split the family, not the Element. |
| `consistency` | robust session-to-session agreement over outcome/activity/survival | role mix per session is now observable and is a **confounder** the current analysis cannot see | **E. BACKSTAGE_EVIDENCE_ONLY** | `elements` `compatible`, new robustness check | A player who alternates POSITION_1 and POSITION_5 will look "inconsistent" for a reason that is not variability of expression. Role-mix should become a robustness check and a limitation, not a new public number. This makes the existing finding *more honest*, which is worth more than a new one. |

## 2. Finding families

| family | existing computation | STRATZ opportunity | verdict | version impact | reason |
|---|---|---|---|---|---|
| `pool_shape` | `breadth` + `toolkit` zones | `position`/`role` add a **role-shape** dimension orthogonal to hero-shape | **C. NEW_SUBFINDING** | `findings` `changed` | "Wide hero pool, one role" and "narrow hero pool, three roles" are different players and currently identical. This is the highest-resonance structural addition parsed data enables. |
| `transfer` | Element `transfer` + `breadth_or_toolkit` | role-stretch vs hero-stretch split (§1) | **C. NEW_SUBFINDING** | `findings` `changed` | As above. |
| `post_loss_response` | matched-control comparison over adjacent same-session loss→next pairs; `min_transitions=30` | `position`/`role` improve control matching; `radiantNetworthLeads` distinguishes *how* the previous game was lost | **A. ENHANCE_EXISTING** | `findings` `changed` (control definition) | The 4-level context backoff currently matches on `patch+lane_context+hero_function`, where `lane_context` is almost always `None` and `patch` almost always absent — so it degrades to L3 "anything". With patch at 100% and role at 93%, **L0 matching becomes real for the first time.** This is a large power gain with no new hypothesis. Best value-per-risk in the whole reassessment. |
| `combat_expression` | `involvement` + `death_exposure` zones | participation denominator; game-state conditioning | **B. REPLACE_PROXY** (via `involvement`) | `findings` `changed` | Follows `involvement`. |
| `session_drift` | late-half minus early-half over completed sessions; `min_sessions=12` | nothing STRATZ-specific improves within-session sequencing | **G. REJECT for now** | `unchanged` | Parsed data adds within-*match* time structure. `session_drift` is about *between*-match structure inside a session. These are orthogonal. Adding parsed detail here multiplies hypotheses without adding independent opportunities. **And the family cannot currently fire at all (§0.3).** Fix that first. |

## 3. Semantic outcomes

All 28. `PC` = `public_candidate`, `SO` = `shadow_only`. "Dead" marks the six
hard-wired to `p = 1.0` (§0.3).

### pool_shape (6)

| outcome | | verdict | reason |
|---|---|---|---|
| `hidden_center` | PC | **A. ENHANCE** | Role-shape sharpens "the center you didn't know you had". Same claim, better evidence. |
| `names_wide_jobs_narrow` | PC | **B. REPLACE_PROXY** | "Jobs" is currently the editorial taxonomy. With observed `role`, this becomes a measurement rather than an inference. Changes what the finding means → new lineage. |
| `names_narrow_jobs_wide` | PC | **B. REPLACE_PROXY** | As above. |
| `names_changed_jobs_held` | PC | **B. REPLACE_PROXY** | As above; the job-JSD ROPE (0.06) is calibrated against taxonomy jobs and would need re-deriving against observed roles. |
| `hero_lifecycle` | SO | **KEEP shadow** | Parsed data does not address the reason it is shadow-only (needs 120+ matches, 45+ sessions, 90+ days). |
| `identity_eras` | SO | **KEEP shadow** | As above. |

### transfer (6)

| outcome | | verdict | reason |
|---|---|---|---|
| `clean_transfer` | PC | **C. NEW_SUBFINDING** (split) | Should split into hero-transfer and role-transfer. Carries a `recommendation_key` (`verify_transfer`), so splitting also splits the verification contract. |
| `results_stop_first` | PC | **A. ENHANCE** | Role-fair baselines reduce the chance this is a role artifact. |
| `expression_stops_first` | PC | **A. ENHANCE** | As above. |
| `involvement_boundary` | PC | **B. REPLACE_PROXY** | Inherits `involvement`'s denominator problem directly. |
| `exposure_boundary` | PC | **A. ENHANCE** | Inherits `death_exposure`, which stays a direct count. |
| `localized_function_bottleneck` | PC, **Dead** | **E. BACKSTAGE** | "Function" is the editorial taxonomy again. Cannot be assessed until it can fire. |

### post_loss_response (5)

| outcome | | verdict | reason |
|---|---|---|---|
| `one_loss_runback` | PC | **A. ENHANCE** | Better control matching (§2). Same claim, more power. |
| `two_loss_switch` | PC | **A. ENHANCE** | As above. The V6.1 state vocabulary (`relationships.py:61, 82`) is `win`, `one_loss`, `two_plus_losses`, `win_streak` — all four exist. V6.0's `post_loss.py` implements only a binary "previous match lost", so the streak states live in V6.1's relationship layer, not in the V6.0 transition builder. |
| `result_shaped_pool` | PC | **C. NEW_SUBFINDING** | With `role`, "changed pool" can distinguish *changed hero* from *changed role after a loss* — a much more Dota-native claim. |
| `result_invariant_response` | PC | **A. ENHANCE** | An equivalence claim; better controls tighten the ROPE test (`rope=0.08`). |
| `adjustment_without_recovery` | PC, **Dead** | **E. BACKSTAGE** | Cannot be assessed until it can fire. |

### combat_expression (5)

| outcome | | verdict | reason |
|---|---|---|---|
| `involvement_holds_exposure_moves` | PC | **B. REPLACE_PROXY** | Inherits `involvement`. |
| `exposure_holds_involvement_moves` | PC | **B. REPLACE_PROXY** | As above. |
| `same_expression_different_results` | PC, **Dead** | **E. BACKSTAGE** | Cannot fire. |
| `different_expression_same_results` | PC, **Dead** | **E. BACKSTAGE** | Cannot fire. |
| `localized_variance` | PC | **E. BACKSTAGE** | Role-mix is an unmodelled variance source (§1 `consistency`). Parsed data should feed a confounder control here, not a new claim. |

### session_drift (6)

| outcome | | verdict | reason |
|---|---|---|---|
| `opening_game_signature` | PC | **G. REJECT for now** | Orthogonal to parsed data; family cannot fire. |
| `gradual_session_drift` | PC | **G. REJECT for now** | As above. |
| `predeclared_breakpoint` | PC | **G. REJECT for now** | As above. Note: per-minute curves make spurious breakpoints *easier* to find, which is a reason for caution, not enthusiasm. |
| `selection_only_drift` | PC, **Dead** | **E. BACKSTAGE** | Cannot fire. |
| `bounded_stopping_response` | PC, **Dead** | **E. BACKSTAGE** | Cannot fire. |
| `behavioral_loop` | SO | **KEEP shadow** | Unchanged. |

**Tally — Elements (7):** 2 KEEP-unchanged (`breadth`, `transfer`),
2 REPLACE_PROXY (`toolkit`, `involvement`), 2 ENHANCE (`finishing`,
`death_exposure`), 1 BACKSTAGE (`consistency`).

**Tally — semantic outcomes (28, sums to 28):** 7 ENHANCE · 6 REPLACE_PROXY ·
2 NEW_SUBFINDING · 7 BACKSTAGE_EVIDENCE_ONLY · 3 REJECT-for-now · 3 KEEP-shadow.

**Nothing is retired.** No current finding is made redundant by parsed data.
That is worth stating plainly: STRATZ does not obsolete V6.1's analysis, it
re-bases it.

---

## 4. Language guards that parsed data collides with

`FORBIDDEN_FREE_TERMS` bans, among others: `positioning`, `item timing`,
`objective conversion`, `fight entry`, `death quality`, `aggression`, `skill`,
`because`, `causes`, and every explicit position label (`position 1`..`pos5`).

Parsed data makes several of these **measurable**. It does not make them
**publishable**, and this research does not propose lifting any guard. Three
collisions are worth surfacing as owner decisions, stated separately from any
candidate:

1. **Explicit position labels.** `position` gives `POSITION_1`..`POSITION_5` at
   91%. The guard bans saying "position 1". Every role-aware finding below is
   written in role words (`safe lane`, `hard support`) rather than numbers, and
   works fine that way. **Recommendation: keep the guard.** It costs nothing.

2. **`item timing`.** `itemPurchases {time itemId}` is exact, and item-timing
   behaviour is among the most Dota-native things in the payload. The guard
   currently blocks the *phrase*, which the substring checker will catch in any
   natural copy. **Recommendation: this is the one guard worth an explicit owner
   decision.** It was written when timing was unobservable; it is now
   observable and directly measured. The underlying concern — implying a causal
   "you bought X late therefore you lost" — is better handled by the existing
   causality bans (`because`, `causes`, `causal`) than by banning the noun.

3. **`positioning`.** Available only via playback, which §Field-inventory §4
   prices out of the product (and that price is a floor — only 7 of 25 playback
   fields were fetched). **Recommendation: keep the guard.** The decision
   is moot at product tier and the guard costs nothing.

No guard is lifted by anything recommended in this research.
