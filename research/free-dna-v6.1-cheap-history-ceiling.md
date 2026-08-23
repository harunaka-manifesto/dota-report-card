# Free DNA V6.1: the analytical ceiling of one cheap history call

**Status:** research specification; no production code  
**Window:** previous 365 days  
**Evidence boundary:** one OpenDota `players/{account_id}/matches` response, saved verbatim, plus the repository's static hero-job taxonomy  
**Design question:** can Free DNA discover substantially more truths while keeping exactly seven public Elements?

## Executive answer

Yes. V6 has the right public ontology and the current seven Elements should remain seven. The underused asset is not another raw statistic; it is the ordering of the matches. V6 already treats sessions and a post-loss contrast as more than rows, but it leaves most of the history's portfolio shape, state transitions, repetition, stopping behavior, hero lifecycles, conditional consistency, and identity evolution unused.

The recommended V6.1 change is therefore a **larger hidden analytical graph**, not a larger public scorecard:

1. keep the seven Elements and five family keys;
2. repair measurement weaknesses in Toolkit, Finishing, Transfer, and Consistency;
3. add portfolio, lifecycle, transition, sequence, stopping, and era features underneath them;
4. expand `pool_shape`, `post_loss_response`, and `session_drift` into richer semantic outcomes without creating more top-level families;
5. qualify outcomes hierarchically, with session-clustered uncertainty, negative controls, minimum opportunity counts, effect-size gates, and abstention;
6. synthesize a stable primary identity plus an optional conditional or longitudinal “twist.”

The strongest one-call experiences are not “your KDA is X.” They are statements such as “your hero names changed, but the jobs did not,” “one loss barely changes your choice; two losses do,” “your sessions break at Game 4 rather than fading,” and “your results travel farther from your core than your summary expression.” Each is observable and testable without pretending to know intent, emotion, positioning, or causality.

The specimen proves the headroom and the limits. One request returned 900 chronologically useful rows and 36 fields, of which 842 pass the current V6 match gate. It supports 366 session clusters, 63 eligible heroes, portfolio/lifecycle/sequence analysis, and session-block inference. But lane and patch-like fields are only about 2.5% complete and party size about 36%, so the product cannot honestly make lane-normalized, patch-specific, or solo-versus-party claims from this response. The model must treat coverage as evidence, never as a field merely existing in the schema.

---

# Part 1 — V6 audit

## 1.1 What V6 is trying to accomplish

V6 replaces V5's 18 public Elements and 11 named Patterns with a smaller, evidence-controlled narrative system:

```text
365-day summary history
→ normalization and context adjustment
→ 7 public Elements
→ supporting state/evolution/condition signals
→ 5 independently tested Finding families
→ at most 3 published Findings
→ dynamic identity and 9-beat story
```

Its best decision is separating **measurement**, **identity**, **finding family**, and **semantic outcome**. “Post-Loss Response” can be one family while supporting “runs it back,” “returns to core after two,” or “changes behavior without a result difference.” That prevents the V5 failure mode in which every useful conditional became an ontology item.

Other strong decisions are:

- Shannon effective counts for Breadth and Toolkit, which preserve distribution shape better than unique counts.
- Context-adjusted activity and death exposure rather than raw KDA-derived labels.
- Transfer requiring agreement across outcome, activity, and survival instead of equating unfamiliar-hero win rate with adaptability.
- Consistency defined as repeatability of summary expression, not personality.
- Session-cluster bootstrap, 95% intervals, minimum independent sessions, finite-family testing, Benjamini–Hochberg FDR, effect-size gates, and explicit abstention.
- A maximum of three Findings with family diversity, keeping insight density high.
- Claim → evidence → interpretation → recommendation, with copy contracts that forbid aggression, positioning, death quality, motive, skill, or causal claims.
- Dynamic identity composed from evidence rather than rigid global archetypes.

The statistical direction is sound. Effective diversity is grounded in the “numbers equivalents” interpretation of entropy ([Jost, 2006](https://nsojournals.onlinelibrary.wiley.com/doi/abs/10.1111/j.2006.0030-1299.14714.x)); BH controls false discovery rate across the declared family ([Benjamini and Hochberg, 1995](https://rss.onlinelibrary.wiley.com/doi/pdf/10.1111/j.2517-6161.1995.tb02031.x)); and session-cluster resampling respects repeated observations from the same play period ([Ren et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7148287/)).

## 1.2 V5 → V6 compression

| V5 public concept | V6 disposition | Assessment |
|---|---|---|
| Breadth, Toolkit, Involvement, Finishing, Deaths, Transfer | retained or clarified | Correct: these are legible identity axes. |
| Stability, Exploration | hidden under pool evolution | Correct, but the hidden model is currently too shallow. |
| Familiarity, Role, Presence | evidence/context rather than identity | Correct; they become useful conditional descriptors. |
| Volatility | folded into Consistency | Correct publicly; internally outcome and expression variance must stay separable. |
| Form, Pace, Duration, Drift | state/session support | Correct; these are conditional or time-bound. |
| Tempo, Recovery | post-loss evidence | Correct; neither deserves a universal score. |
| 11 fixed Patterns | 5 tested families with semantic variants | Major improvement in multiplicity control and narrative flexibility. |

V6 intentionally hides ten useful concepts without deleting them. The compression only becomes harmful where implementation treats “hidden” as “not modeled.” Pool evolution cannot be just Stability plus Exploration; Consistency cannot be one undifferentiated dispersion number; and Post-Loss cannot be one matched contrast.

The same audit across V5's 11 Pattern registry entries shows that V6 preserves the useful questions while removing fixed ontology weight:

| V5 Pattern | V6 home | What should survive in V6.1 |
|---|---|---|
| P01 Same Playbook | Pool Shape | stable functional thread, now expressed without a rigid type |
| P02 Comfort Edge | Pool Shape / Transfer | supported core and adjacent development candidates |
| P03 Partial Transfer | Transfer | component-level failure; expand into result/expression subtypes |
| P04 Versatile Core | Pool Shape | Breadth×Toolkit contradiction and redundancy |
| P05 Proven Flexibility | Transfer | clean equivalence across supported distance |
| P06 Bounceback | Post-Loss Response | multi-signal recovery, with sequence/context enrichment |
| P07 Performance Slide | Session Drift / recent state | only when time/session scope is explicit |
| P08 Controlled Presence | Combat Expression | high Involvement with lower Death Exposure, safe wording retained |
| P09 Presence Tax | Combat Expression | high Involvement with higher Exposure, no claim that deaths are valuable |
| P10 Session Fade | Session Drift | monotone or breakpoint-specific decline |
| P11 Session Rise | Session Drift | inverse outcome with the same selection-bias caveat |

None needs to return as a sixth family or an eighteenth Element. Several should survive as semantic outcomes or negative contrasts under the five families.

## 1.3 Current end-to-end map

| Raw field(s) | Current feature | V6 signal/Element | Family/outcome | Action/story beat |
|---|---|---|---|---|
| `hero_id` | hero counts, hero entropy | Breadth; portfolio core/tail | Pool Shape | identity anchor, pool evidence |
| `hero_id` + taxonomy | job-label distribution | Toolkit | Pool Shape | common thread, contradiction |
| `kills`,`assists`,`duration` | `(K+A)/minutes` | adjusted Involvement | Combat Expression, Transfer, Consistency | expression claim |
| `kills`,`assists` | per-match `K/(K+A)` | adjusted Finishing | Combat Expression | modifier/evidence |
| `deaths`,`duration` | deaths/10 | adjusted Death Exposure | Combat Expression, Transfer, Consistency | survival-safe claim |
| side + `radiant_win` | win indicator | outcome component | Transfer, post-loss, Consistency | evidence, never “skill” |
| `hero_id` + 60% core split | core/stretch comparison | Transfer | Transfer semantic direction | Five-game stretch experiment |
| `start_time` | 90-minute sessions | session dispersion/drift | Consistency, Session Drift | session curve |
| previous outcome + next row | matched post-loss contrast | familiarity/tempo/recovery | Post-Loss Response | recovery experiment |
| recent timestamps | recent form/activity | support | identity evidence | recent beat |
| strongest family + second distinct family + anchor | identity sentence | dynamic identity | — | headline + story |

## 1.4 Implementation gaps found before proposing V6.1

1. **The runtime and calibration do not request the same data.** The calibration collector explicitly projects context fields; the runtime `AnalysisService._get_summary_history` does not. The current OpenDota client also paginates in blocks of 200, so it is not a one-physical-request implementation. V6.1 must declare one canonical projection and prove runtime/calibration parity.
2. **Context is mostly theoretical for this payload.** `lane`, `lane_role`, `is_roaming`, and `version` are present in only 22/900 rows. Patch and region are not returned as useful dimensions. The fallback baseline is well designed, but calibration cannot make unavailable context appear at inference time.
3. **Toolkit is not match weighted in the current portfolio summary.** It counts each established hero's taxonomy labels, so a 200-game hero and an 8-game hero can contribute equally. Multi-job taxonomy uncertainty also is not propagated.
4. **The portfolio timeline can form an accidental fourth sliver.** Integer chunking by `len // 3` and clamped labels can produce two “Later” chunks.
5. **Transfer distance is binary.** The smallest heroes covering 60% define “core”; everything else is equally far away. A near-adjacent stretch hero and an unrelated experimental hero should not have the same distance.
6. **Post-loss controls are greedy and reusable.** The first comparable control can be reused, and one-loss behavior is not separated from loss streaks or personally strong/weak summary expression.
7. **Session Drift has an overly broad opportunity denominator.** Requiring qualifying long sessions to be at least half of all sessions can suppress a player with many one-game sessions even when there are enough independent long sessions.
8. **Consistency overweights tiny sessions.** A one-match session contributes an outcome of exactly 0 or 1 with the same session-level status as a longer session; this can inflate apparent outcome dispersion.
9. **Finishing averages unstable per-match ratios.** A one-event match and a twenty-event match can receive equal weight after zero-event exclusion.
10. **Identity composition has no compatibility/stability model.** “strongest + another family + anchor” cannot yet distinguish a stable identity foundation from a recent state, surface a contradiction as a twist, or avoid semantically awkward combinations.

## 1.5 What remains unexplored

The missing analytical objects are not more public labels. They are: continuous portfolio distance; redundancy and single-point functions; hero auditions and retention; distributions that move at different speeds; repeated-pick curves; result- and expression-conditioned transitions; streak thresholds; session stopping with censoring; non-linear session breakpoints; within-context variance decomposition; recurrent motifs; robust identity eras; and compatibility-aware identity synthesis.

---

# Part 2 — Cheap payload anatomy

## 2.1 The one and only API request

OpenDota's current route declares `/players/:account_id/matches` as the full player match history endpoint ([route spec](https://github.com/odota/core/blob/master/svc/api/spec.ts)). Its request builder applies `date` in days and defaults to significant modes ([request parameters](https://github.com/odota/core/blob/master/svc/api/requests/playerParams.ts)); when `limit` is absent, the player-history builder uses the complete filtered length ([history builder](https://github.com/odota/core/blob/master/svc/util/buildPlayer.ts)). Fields are constrained to the live player-history projection allow-list ([player fields](https://github.com/odota/core/blob/master/svc/api/playerFields.ts)).

Exactly one physical request was made:

```http
GET https://api.opendota.com/api/players/349485267/matches
  ?date=365
  &significant=1
  &project=match_id
  &project=player_slot
  … 35 additional repeated project parameters …
```

`limit` and `offset` were intentionally omitted. The precise ordered projection is in [`request-manifest.json`](opendota-free-v6.1-specimen/request-manifest.json). The response is preserved at [`raw-history.json`](opendota-free-v6.1-specimen/raw-history.json), 507,006 bytes, 900 rows, SHA-256 `7f08e56bac7844850a9123203cfb6cdcc2366440a6bbc9a4042e92b608c84458`. No other OpenDota endpoint or second history request was called.

The chosen public specimen was selected from already-local calibration metadata for high history/session/hero coverage. Results below describe **Specimen A**, not population prevalence. They are a feasibility probe, not calibration evidence.

## 2.2 Request and eligibility facts

| Fact | Observed |
|---|---:|
| Raw rows | 900 |
| Time range | 2025-08-24 to 2026-08-22 UTC |
| Returned fields | 36 |
| Requested but absent | `leagueid` |
| V6-eligible rows | 842 |
| Excluded modes | 22 mode-2 + 30 mode-4 rows, plus any other gate failures |
| Eligible lane/context coverage | 21/842 (~2.49%) |
| Eligible party-size coverage | 305/842 (~36.2%) |
| Independent 90-minute session clusters | 366 |
| Eligible heroes | 63 |

Eligibility here uses the current V6 intent: public All Pick/ranked All Pick (`game_mode` 1 or 22), public/ranked lobby (`lobby_type` 0 or 7), duration at least five minutes, and no material abandon (`leaver_status < 2`). The raw body is immutable; all exclusions happen locally.

## 2.3 Field-by-field inventory

Coverage is non-null count over 900. “Use” distinguishes production V6 today from V6.1 opportunity. Every scalar requires type/range validation; rate fields require duration/context normalization; categories require allow-lists and missingness gates.

| Field | Meaning and type | Coverage | Temporal / categorical / interaction value | V6 use and V6.1 derivations |
|---|---|---:|---|---|
| `match_id` | unique 64-bit match identifier; integer | 900 (100%) | dedupe key; ordering tie-breaker; evidence link | V6 validates/dedupes. Keep; never treat magnitude as time. |
| `player_slot` | side/slot code; integer | 900 | combines with `radiant_win` for personal outcome; possible side check | V6 uses outcome. Do not infer role from slot. |
| `radiant_win` | Radiant won; boolean | 900 | outcome, streaks, transitions, stopping, adoption | V6 uses. Derive personal win, prior/next result, streak state. |
| `hero_id` | selected hero identifier; integer | 900 | portfolio, taxonomy, lifecycle, repetition, eras | Heavily used. Add distance, lifecycle, transition, distribution-change features. |
| `hero_variant` | facet/variant identifier; integer | 900 | possible within-hero context if semantics/version are maintained | Ignored. Research-only until facet metadata and patch stability are versioned; never compare raw IDs across incompatible periods. |
| `start_time` | Unix match start seconds; integer | 900 | chronology, sessions, gaps, recency, rolling windows, eras, local-hour approximation | V6 uses sessions/recent. Add streaks, motifs, stopping/censoring, lifecycle, change points. Time zone is unknown; avoid “night player” claims. |
| `duration` | match length seconds; integer | 900 | per-minute rates, duration strata, session length, censoring | V6 uses. Add nonlinear duration residuals and opportunity weighting. |
| `game_mode` | OpenDota mode code; integer category | 900 | eligibility and separately calibrated strata | V6 gate. Never pool Turbo/other modes into All Pick baselines. |
| `lobby_type` | lobby category code; integer | 900 | ranked/public eligibility/context | V6 gate. Avoid rank/skill interpretation. |
| `version` | replay/parser version-like history field; integer nullable | 22 (2.44%) | weak chronology/context hint | Effectively unusable here; reject patch-specific claims. It is not a reliable patch identifier. |
| `cluster` | server cluster code; integer category | 900 | potential region/latency proxy only with maintained mapping | Returned but not used. Do not infer geography or latency; at most a nuisance stratum after privacy and coverage review. |
| `kills` | player kills; non-negative integer | 900 | activity, finishing, expression, transition conditioning | V6 uses. Add stabilized event shares and strong/weak-expression strata. |
| `deaths` | player deaths; non-negative integer | 900 | exposure rate, variance, transitions | V6 uses. Add duration-residual curve and within-context variability; no death quality. |
| `assists` | player assists; non-negative integer | 900 | activity and finishing denominator | V6 uses. Add event-weighted/shrunk finishing. Team kills are absent, so kill-participation cannot be computed. |
| `level` | end-of-match hero level; integer | 900 | duration/economy-dependent summary | Ignored. Supporting-only after strong duration/function adjustment; too outcome- and role-confounded for identity. |
| `last_hits` | end-of-match last hits; integer | 900 | farm-expression context | Ignored. Candidate supporting context, never inferred position. Normalize nonlinearly by duration and function. |
| `denies` | end-of-match denies; integer | 900 | lane/economy residue | Ignored. Low-value conditional support; duration and role heavily confound it. |
| `gold_per_min` | end-of-match GPM; numeric | 900 | economy expression and strong/weak personal-summary condition | Ignored publicly. Supporting/negative-control feature after function/outcome adjustment; do not equate with efficiency or skill. |
| `xp_per_min` | end-of-match XPM; numeric | 900 | economy/level expression | Same as GPM; useful jointly as a summary-expression condition, not public identity. |
| `hero_damage` | total hero damage; integer | 900 | possible combat-output context | Ignored. Per-minute/function/outcome-adjusted support only; illusion/DoT/hero mechanics confound. |
| `tower_damage` | total tower damage; integer | 900 | objective-output context | Ignored. Sparse/zero-inflated, hero- and result-confounded; finding evidence only after calibration. |
| `hero_healing` | total hero healing; integer | 900 | healing-capable function expression | Ignored. Zero-inflated and hero-specific; conditional taxonomy evidence only. |
| `leaver_status` | abandon/disconnect code; integer category | 900 | eligibility | V6 gate. Never turn it into a behavioral Finding. |
| `party_size` | party member count; integer nullable | 311 (34.56%) | solo/party nuisance context | Coverage too low and likely non-random. Use only for sensitivity analysis; no public solo/stack comparison. |
| `lane` | inferred lane code; integer nullable | 22 (2.44%) | intended lane baseline/context | V6 normalizer can carry it, but unusable on this specimen. Missingness gate must force fallback. |
| `lane_role` | inferred lane-role code; integer nullable | 22 (2.44%) | intended lane/function context | Same: no public lane-conditioned Finding at this coverage. |
| `is_roaming` | inferred roaming flag; boolean nullable | 22 (2.44%) | intended role context | Same; inference is itself noisy. Never label identity from it. |
| `skill` | OpenDota skill bracket; nullable | 0 | none | Reject. V6 explicitly forbids rank/MMR-conditioned calibration. |
| `average_rank` | average match rank encoding; integer | 900 | tempting context but rank/MMR-derived | Reject despite completeness. The V6 evidence contract forbids rank/MMR dimensions, avoiding identity/skill leakage. |
| `item_0`…`item_5` | final main-inventory item IDs; integers | 900 each | build fingerprints, but state is end-of-match and patches alter semantics | Ignored. Research-only unless a versioned item catalog, purchase timing caveat, and strong support gates exist. Not enough to claim build decisions or causality. |
| `item_neutral` | final neutral-item ID; integer | 900 | weak version/context clue | Reject for V6.1 identity; availability, tier, time, and random allocation confound it. |

## 2.4 What the call does not contain

There are no team kills, team net worth, position traces, ward events, purchase times, ability builds, objectives by time, draft order, bans, lane opponents, team composition, parsed fights, reliable patch identifier, reliable lane context, exact queue time, user time zone, or reason for stopping. Therefore:

- Involvement is **not kill participation**; it remains `(K+A)/minute` relative to comparable histories.
- Death Exposure cannot describe bad/good/avoidable deaths or positioning.
- A session boundary is an operational 90-minute gap, not proof the player chose to stop.
- Consecutive rows express observed transitions, not conscious rules or tilt.
- A history change point is a distributional chapter, not proof a patch or decision caused it.
- Items cannot reconstruct builds from final slots.

## 2.5 The real ceiling

The payload has 36 columns, but the useful object is a time-indexed multivariate history:

```text
fields × chronology × portfolio membership × taxonomy
       × session position × prior state × repetition
       × conditional contrasts × uncertainty
```

That multiplication produces the analytical headroom. It also multiplies false-discovery risk, which is why candidate generation may be large while public output stays small.

---

# Part 3 — Derived-feature universe

The catalog below has **128 plausible features: 16 in each of eight classes**. “P” means suitable for the seven public Elements; “S” supporting; “C” conditional; “L” longitudinal; “F” finding-only; “R” research/reject until calibrated. Definitions are deliberately mechanical so they can be registered, versioned, and tested.

## 3.1 Atomic (A01–A16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| A01 | eligible matches | count after immutable match gate | meta confidence |
| A02 | active days | distinct UTC dates with eligible match | S activity |
| A03 | session count | 90-minute-gap clusters | meta / Consistency |
| A04 | unique heroes | distinct `hero_id` | evidence, not Breadth alone |
| A05 | hero Shannon entropy | `-Σp_h ln p_h` | P Breadth input |
| A06 | effective hero count | `exp(H_hero)` | P Breadth |
| A07 | hero Simpson effective count | `1/Σp_h²` | S shape/check |
| A08 | top-1 hero share | max hero count / matches | S concentration |
| A09 | top-3 hero share | top-three count / matches | S core |
| A10 | top-5 hero share | top-five count / matches | S core |
| A11 | `(K+A)/minute` | match activity opportunity rate | P Involvement input |
| A12 | finishing share | `K/(K+A)` where events exist | P Finishing input |
| A13 | deaths/10 | `10D/minutes` | P Death Exposure input |
| A14 | personal outcome | side-resolved win indicator | Transfer/Consistency support |
| A15 | match duration | minutes, with nonlinear bins/spline | nuisance/session support |
| A16 | inter-match gap | next start minus prior end | sessions, requeue proxy, censoring |

## 3.2 Contextual (X01–X16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| X01 | activity residual | A11 minus hierarchical context expectation | P Involvement |
| X02 | exposure residual | A13 minus hierarchical context expectation | P Death Exposure |
| X03 | finishing residual | stabilized A12 minus hero/function expectation | P Finishing |
| X04 | nonlinear duration residual | rate residual from duration spline/bin | S all expression |
| X05 | hero-conditioned outcome | shrunk result delta for a hero | S portfolio/Transfer |
| X06 | function-conditioned activity | residual within taxonomy job mixture | C Combat |
| X07 | function-conditioned exposure | residual within job mixture | C Combat |
| X08 | mode/lobby sensitivity | estimate with/without each allowed stratum | meta robustness |
| X09 | side sensitivity | Radiant/Dire residual check | meta negative control |
| X10 | party-known sensitivity | estimate on known party subset vs all | R due missingness |
| X11 | farm-expression residual | duration/function/outcome adjusted LH/min | R/S expression condition |
| X12 | economy-expression residual | joint GPM/XPM standardized residual | R/S condition |
| X13 | hero-damage residual | duration/function/outcome adjusted | R/S condition |
| X14 | tower-output residual | zero-inflated adjusted tower damage | R finding evidence |
| X15 | healing-opportunity residual | among healing-capable heroes only | R finding evidence |
| X16 | lane-observed coverage | non-null lane rows / eligible rows | meta gate; no imputation |

## 3.3 Longitudinal (L01–L16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| L01 | rolling hero JSD | Jensen–Shannon divergence between adjacent windows | L Pool |
| L02 | rolling job JSD | taxonomy-mixture divergence between windows | L Pool |
| L03 | hero turnover | entering + exiting supported heroes per window | L Pool |
| L04 | core retention | prior core mass retained next window | L Pool |
| L05 | new-core emergence | heroes crossing supported core threshold | L Pool |
| L06 | old-core decay | prior core share slope/shrunk drop | L Pool |
| L07 | Breadth slope | robust trend in effective hero count | L support |
| L08 | Toolkit slope | robust trend in effective job count | L support |
| L09 | concentration slope | trend in top-3/HHI | L support |
| L10 | activity drift | robust trend in X01 | L Combat/session |
| L11 | exposure drift | robust trend in X02 | L Combat/session |
| L12 | finishing drift | robust trend in X03 | L Combat |
| L13 | transfer drift | early/middle/recent transfer frontier | L Transfer |
| L14 | expression-variance drift | recent vs historical repeatability | L Consistency |
| L15 | distribution change points | penalized/session-block splits with minimum eras | F Pool eras |
| L16 | name-minus-job migration | hero JSD minus job JSD across eras | F identity migration |

## 3.4 Transitional (T01–T16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| T01 | hero repeat after win | `P(H_t=H_{t-1}|W_{t-1})` | C Result Response |
| T02 | hero repeat after one loss | same after exactly one prior loss | C Result Response |
| T03 | hero switch after 2+ losses | switch probability by loss-run length | C rules |
| T04 | job repeat after win | fractional taxonomy-overlap continuation | C Result Response |
| T05 | job repeat after loss | same after loss state | C Result Response |
| T06 | core return after loss | next pick moves from stretch to core | C Result Response |
| T07 | portfolio-distance movement | next continuous distance minus previous | C Result Response |
| T08 | activity change after result | matched next-game X01 delta | C Result Response |
| T09 | exposure change after result | matched next-game X02 delta | C Result Response |
| T10 | finishing change after result | matched next-game X03 delta | C Result Response |
| T11 | recovery outcome | next-game result vs matched non-loss control | C Result Response |
| T12 | continue-after-result | next match starts inside session gap | F stopping |
| T13 | stop-after-result | session ends, excluding right-censored edge | F stopping |
| T14 | adoption after first win | second/third game hazards after debut win | C lifecycle |
| T15 | abandonment after first loss | no supported return within horizon | C lifecycle |
| T16 | switch after weak expression | next choice conditional on predeclared summary residual | C rules |

## 3.5 Sequential (Q01–Q16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| Q01 | result run length | signed consecutive win/loss count | state/rules |
| Q02 | hero run length | consecutive identical hero count | repetition |
| Q03 | function-overlap run | consecutive high taxonomy-overlap count | repetition |
| Q04 | repeat-position curve | X01/X02/outcome at hero run positions 1…5+ | F repetition |
| Q05 | two-loss threshold contrast | switch after 2 losses minus after 1 | F unwritten rule |
| Q06 | win-streak expansion | portfolio distance/diversity by win-run | F rule |
| Q07 | loss-streak contraction | core mass/diversity by loss-run | F rule |
| Q08 | recovery-stop motif | `LL → core → W → session end` support | F loop |
| Q09 | experiment-recovery loop | `W → stretch → L → core → W` support | F loop |
| Q10 | audition-drop motif | `new → loss → no return` support | F lifecycle |
| Q11 | audition-adopt motif | `new → repeat → repeat → retained` support | F lifecycle |
| Q12 | repeat-until-loss motif | same hero through wins then switch after loss | F loop |
| Q13 | session-core-return motif | late-position pick moves toward core | F Session |
| Q14 | first-game shock | Game 1 expression/outcome vs Games 2–3 | F Session |
| Q15 | nonlinear session breakpoint | best supported position split, predeclared minimum | F Session |
| Q16 | motif lift | motif frequency / product of player transition baselines | meta qualification |

## 3.6 Portfolio (P01–P16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| P01 | job Shannon entropy | entropy of **match-weighted fractional** job mass | P Toolkit |
| P02 | effective job count | `exp(H_job)` | P Toolkit |
| P03 | job Simpson count | concentration-sensitive companion | S Toolkit |
| P04 | job redundancy | effective heroes supporting each job above sample floor | S Toolkit |
| P05 | unique-job coverage | supported taxonomy jobs with meaningful mass | S Toolkit |
| P06 | single-point job mass | job mass supplied by only one established hero | S Toolkit risk |
| P07 | hero functional overlap | pairwise taxonomy-vector similarity | S distance |
| P08 | portfolio fragmentation | hero clusters separated in taxonomy space | S Pool/Transfer |
| P09 | stable core size | heroes whose core status survives bootstrap/windows | S Breadth |
| P10 | reliable stretch size | noncore heroes within transfer frontier | S Transfer |
| P11 | experimental tail size | low-sample recent heroes outside frontier | S Pool |
| P12 | abandoned pool size | formerly supported, absent beyond horizon | L Pool |
| P13 | returning hero count | dormant hero reappearing with supported run | L Pool |
| P14 | emerging hero count | recent share/retention crossing threshold | L Pool |
| P15 | continuous core distance | blend of familiarity percentile and taxonomy distance | P Transfer input |
| P16 | transfer frontier | farthest distance with outcome/activity/exposure equivalence | P Transfer |

## 3.7 Conditional (C01–C16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| C01 | core vs stretch outcome | shrunk/clustered delta | Transfer |
| C02 | core vs stretch activity | clustered X01 delta | Transfer/Combat |
| C03 | core vs stretch exposure | clustered X02 delta | Transfer/Combat |
| C04 | core vs stretch variance | variance-component delta | Consistency |
| C05 | hero vs function variance share | hierarchical decomposition | Consistency/Combat |
| C06 | early vs late session expression | position contrast | Session |
| C07 | Game 4+ pool distance | late vs early continuous distance | Session |
| C08 | win vs loss expression | descriptive residual contrast | Combat support |
| C09 | post-win exploration | next-pick distance after win vs control | Result Response |
| C10 | post-loss contraction | next-pick distance after loss vs control | Result Response |
| C11 | strong-loss response | next choice after loss with high personal expression | Result Response |
| C12 | weak-loss response | same after low expression | Result Response |
| C13 | function-specific transfer | frontier/equivalence within supported job | Transfer |
| C14 | hero-conditioned finishing | shrunk X03 by hero | Combat |
| C15 | session-conditioned consistency | repeatability by session position/length | Consistency/Session |
| C16 | recent vs historical identity | same estimator in independent eras/windows | dynamic identity twist |

## 3.8 Meta (M01–M16)

| ID | Feature | Definition | Destination |
|---|---|---|---|
| M01 | raw field coverage | non-null eligible fraction | gate |
| M02 | eligible-match coverage | eligible/raw rows | gate |
| M03 | independent opportunities | sessions/transitions/lifecycles, not rows | gate |
| M04 | effective sample size | weight-aware or cluster-aware information count | shrinkage |
| M05 | cluster-bootstrap interval | resample sessions, recompute full estimator | confidence |
| M06 | posterior/equivalence probability | probability effect inside/outside practical band | confidence |
| M07 | standardized effect | interpretable delta relative to robust scale | ranking |
| M08 | temporal stability | same sign/magnitude across disjoint windows | identity eligibility |
| M09 | leave-one-hero-out stability | conclusion survives dominant hero removal | confound check |
| M10 | leave-one-era-out stability | conclusion not one short chapter | confound check |
| M11 | taxonomy sensitivity | result across plausible job allocations | confidence |
| M12 | session-gap sensitivity | result at 60/90/120-minute definitions | confidence |
| M13 | boundary censoring rate | opportunities lost at history/session edge | stopping gate |
| M14 | family-level p/q | predeclared omnibus test + hierarchical FDR | multiplicity |
| M15 | evidence diversity | number of independent signal groups supporting claim | ranking |
| M16 | copy entitlement | machine-readable supported/forbidden claim set | publication gate |

## 3.9 What not to do with 128 features

Do not put 128 z-scores into one learned “identity” model, fish across every slice, or publish whichever sentence has the lowest p-value. Most features are nuisance controls, gates, variants, or explanations. The graph should produce a small number of pre-registered family hypotheses; semantic variants are selected only after the family qualifies, and their wording remains bounded by the exact evidence groups that contributed.

---

# Part 4 — Seven Element forensic review

## 4.1 Breadth

| Field | Answer |
|---|---|
| Current V6 definition | Shannon effective hero count over eligible 365-day matches: `exp(-Σp_h ln p_h)`. |
| Main strength | Interpretable “equivalent equally played heroes”; much harder to game with one-off picks than unique count. |
| Main weakness | One number cannot distinguish a smooth medium pool from a sharp core plus a very long audition tail. Two equal entropies can have different top-1 dependence, core size, redundancy, and stability. |
| Hidden information currently discarded | Simpson count, HHI/Gini, top-1/3/5 shares, bootstrap-stable core, long-tail depth, emerging/dormant heroes, and distribution shape over time. |
| Better estimator? | Keep Shannon as the public center. Add Simpson effective count and stable-core/tail decomposition as hidden shape evidence. Show credible/cluster-bootstrap uncertainty only when instability matters; do not blend shape into an opaque composite. |
| Better contextual normalization? | No population role normalization: Breadth is what the player chose. Separately gate modes and report taxonomy/context sensitivity. Use time weighting only for a “recent Breadth” support signal, never silently in the annual identity. |
| Supporting signals to add | Top shares, stable-core size, reliable stretch, experimental tail, core retention, emerging/returning/abandoned heroes, rolling hero JSD. |
| Finding opportunities unlocked | “17 meaningful heroes, six carry half the games”; “wide annual pool, compact recent core”; “many auditions, few adoptions”; “core replaced.” |
| Keep public? | **Yes.** Breadth is fundamental, legible, and distinct from Toolkit and Transfer. |
| Recommended V6.1 definition | Unchanged public estimator and label. Require ≥30 eligible hero rows; confidence combines sample, coverage, session independence, and window stability. Store a versioned portfolio-shape object beside it. |

Specimen A shows why the companion shape matters: 63 unique heroes becomes 25.67 effective heroes, 15.51 Simpson-effective heroes, and only six heroes carry 50% of games. “63 heroes” is theater; “a broad tail around a real six-hero center” is understanding.

## 4.2 Toolkit

| Field | Answer |
|---|---|
| Current V6 definition | Shannon effective count across taxonomy job labels, using established heroes and a taxonomy coverage gate. |
| Main strength | Separates hero-name diversity from the kinds of jobs those heroes supply; enables high-value contradictions. |
| Main weakness | Current portfolio implementation counts job labels per established hero rather than match-weighted fractional job mass. A rarely played seven-job hero can outweigh a frequently played four-job hero; correlated tags and taxonomy uncertainty inflate breadth. |
| Hidden information currently discarded | Job concentration, redundancy, single-provider jobs, pairwise hero overlap, portfolio fragmentation, taxonomy confidence, and name-change versus job-change. |
| Better estimator? | For each match, distribute mass fractionally across that hero's supported jobs; aggregate match mass, then take Shannon effective count. Maintain a primary-job sensitivity estimate and shrink/discount low-confidence taxonomy assignments. Do not count “jobs per hero” as usage. |
| Better contextual normalization? | No population normalization by default. Normalize the taxonomy itself: version it, define tag dependence, propagate missing/ambiguous hero weights, and require ≥80% weighted coverage. |
| Supporting signals to add | Simpson jobs, unique supported jobs, redundancy per job, single-point mass, functional overlap matrix, job clusters, rolling job JSD. |
| Finding opportunities unlocked | “You experiment with names, not playstyles”; “compact hero pool covers many jobs”; “your toolkit looks wide but one hero supplies all save”; “names stable, jobs migrated.” |
| Keep public? | **Yes.** It answers a different, valuable question from Breadth. |
| Recommended V6.1 definition | Match-weighted fractional taxonomy entropy with versioned confidence weights; public value remains `exp(H_job)`. Evidence names the top job masses and redundancy, not an unhelpful entropy number. |

On Specimen A, fractional match weighting yields 12.65 effective jobs; a primary-job-only sensitivity yields 8.65. That gap is useful uncertainty, not a reason to pick the prettier number. The player changed hero distributions far more than job distributions across thirds (hero JSD 0.215/0.159 versus job JSD 0.010/0.014), a promising “names changed, underlying toolkit held” pattern.

## 4.3 Involvement

| Field | Answer |
|---|---|
| Current V6 definition | Context-adjusted `(kills + assists) / minutes`. |
| Main strength | Uses available opportunity time and makes a narrow, observable claim about scoreboard event presence. It explicitly avoids “aggression.” |
| Main weakness | Team kills are absent, so it is not kill participation. Rate/duration relationships can be nonlinear; hero/function and win/loss context can dominate. A global mean hides stable versus conditional involvement. |
| Hidden information currently discarded | Within-hero stability, function variance, core/stretch delta, session position, post-result change, recent drift, and covariance with death exposure. |
| Better estimator? | Retain per-match rate but estimate hierarchical residuals with a duration spline, hero/function mixture, allowed mode/lobby, and calibrated fallback. Aggregate with robust or partially pooled estimators rather than a raw mean. |
| Better contextual normalization? | Use runtime-available contexts only. Hero + fractional function + duration are viable; lane/patch must fall back when coverage fails. Include a context-cell coverage/borrowed-baseline flag in evidence. |
| Supporting signals to add | Residual dispersion, hero/function variance decomposition, core/stretch equivalence, session curve, result-conditioned movement, recent stability. |
| Finding opportunities unlocked | “Results change off-pool; involvement does not”; “presence stable across heroes, exposure is not”; “function explains more of the change than session position.” |
| Keep public? | **Yes**, with the current narrow name. |
| Recommended V6.1 definition | Robust annual center of cross-fitted hierarchical activity residuals; calibrate to percentile/zoned output. Publish only “involvement”/“activity,” never participation, aggression, or teamfight skill. |

Team-kill context cannot be reconstructed from this endpoint. Calling A11 “kill participation” would be a data-contract violation.

## 4.4 Finishing

| Field | Answer |
|---|---|
| Current V6 definition | Context-adjusted per-match `kills / (kills + assists)`, excluding zero-event matches. |
| Main strength | A compact, comprehensible modifier separating credited kills from assists without turning it into a performance grade. |
| Main weakness | Per-match averaging gives low-event games disproportionate influence. Zero-event exclusion is selected missingness, and the ratio is strongly hero/function/result conditioned. “Finishing” may sound intentional or evaluative if copy is careless. |
| Hidden information currently discarded | Event denominator, low-event uncertainty, between-hero variation, recent drift, core/stretch difference, and whether the aggregate is a few kill-heavy games. |
| Better estimator? | Use an empirical-Bayes beta-binomial or equivalent stabilized event share. Preserve match/session clustering for uncertainty. Report an event-weighted sensitivity estimate and exclude/flag insufficient total `K+A`, not only insufficient matches. |
| Better contextual normalization? | Hero/function and duration/outcome strata with partial pooling. No lane normalization at 2.5% coverage. Compare estimates within support, not across impossible taxonomy cells. |
| Supporting signals to add | Event opportunities, shrunk hero finishing, conditional spread, core/stretch delta, temporal stability. |
| Finding opportunities unlocked | “Finishing changes off-pool while involvement holds”; “same result, different event mix”; “one function accounts for the finishing shift.” |
| Keep public? | **Yes, but subordinate.** It is useful as a modifier and in relationships, rarely as the headline Finding. |
| Recommended V6.1 definition | Posterior/stabilized share of credited kills among own kill+assist events, context-adjusted and opportunity-gated. Copy: “more kill-weighted” / “more assist-weighted,” never “secures kills better.” |

## 4.5 Death Exposure

| Field | Answer |
|---|---|
| Current V6 definition | Context-adjusted deaths per ten minutes. |
| Main strength | Observable, duration-aware, and rigorously separated from death quality, positioning, or “feeding.” |
| Main weakness | Death rate is nonlinear across very short/long games and strongly depends on hero/function and match state. Mean exposure hides whether the player's signature is actually stability. |
| Hidden information currently discarded | Robust dispersion, hero/function contributions, core/stretch equivalence, late-session drift, post-result movement, and covariance with Involvement. |
| Better estimator? | Fit a count/rate model with log-duration exposure or a calibrated duration spline, robust random effects, and overdispersion. Retain the understandable deaths/10 evidence unit. |
| Better contextual normalization? | Hierarchical hero/function + duration + allowed mode/lobby; outcome may be a descriptive conditional lens but should not be “adjusted away” in every product statement. Missing lane/patch triggers fallback. |
| Supporting signals to add | Exposure variance, high-involvement joint state, core/stretch/session/result contrasts, temporal drift. |
| Finding opportunities unlocked | “High involvement with low exposure”; “activity transfers, exposure changes”; “late picks get safer while results stay flat.” |
| Keep public? | **Yes.** It is distinct, legible, and one of Free's safest combat-expression axes. |
| Recommended V6.1 definition | Context-adjusted overdispersed death rate, summarized as percentile/zone and deaths/10 evidence, with a separate stability object. |

## 4.6 Transfer

| Field | Answer |
|---|---|
| Current V6 definition | Compare core versus stretch outcome, adjusted activity, and adjusted survival; publish a direction when at least two of three agree. Core is the smallest heroes covering 60% of matches. |
| Main strength | Treats transfer as multivariate equivalence/change rather than unfamiliar-hero win rate. The two-of-three rule and abstention are materially better than V5. |
| Main weakness | The binary 60% boundary is discontinuous and semantically crude. Directional agreement can hide “results travel, expression does not.” It uses differences where equivalence is often the real question and lacks partial pooling across sparse stretch bands. |
| Hidden information currently discarded | Familiarity gradient, taxonomy distance, reliable stretch versus experimental edge, function-specific frontiers, expression/result subtypes, asymmetry, and recent improvement. |
| Better estimator? | Define continuous distance `d` from core using familiarity rank/share, stable-core membership, and taxonomy-vector distance. Fit partially pooled outcome/activity/exposure curves over `d`; define the **transfer frontier** as the farthest supported band where all required signals remain within predeclared practical-equivalence bounds. |
| Better contextual normalization? | Compare within function where support allows; shrink hero estimates; cross-fit the core definition so the same outcomes do not select and evaluate heroes. Separate historical identity from recent frontier. |
| Supporting signals to add | Outcome transfer, expression transfer, frontier width, function-specific frontier, distance asymmetry, temporal frontier, leave-one-core-hero-out stability. |
| Finding opportunities unlocked | clean transfer; result-only failure; expression-only shift; conditional failure; one-function bottleneck; improving frontier; “results travel farther than style.” |
| Keep public? | **Yes.** It is conceptually rich enough to remain a synthesized public Element. |
| Recommended V6.1 definition | A calibrated synthesis of equivalence curves for outcome, activity, and exposure over continuous portfolio distance. Public zone reflects how far reliable summary expression carries; Findings expose which component creates the boundary. |

The unadjusted specimen illustrates why subtypes matter: core minus noncore is +7.96 percentage points for outcome (session-bootstrap 95% interval +1.22 to +14.49) and +0.058 `(K+A)/min` (+0.030 to +0.084), while death exposure is effectively unchanged (-0.017 deaths/10; -0.157 to +0.118). That is not one generic “poor transfer” sentence. It is “results and involvement fall outside this binary core; exposure appears to hold,” pending population context adjustment.

## 4.7 Consistency

| Field | Answer |
|---|---|
| Current V6 definition | Robust session dispersion across outcome, adjusted activity, and adjusted death exposure; requires signal agreement and at least 12 sessions. |
| Main strength | Respects session clustering and defines consistency as repeatable summary expression rather than temperament. |
| Main weakness | Outcome and expression need not be one latent phenomenon. Equal session weighting lets one-match sessions inject Bernoulli extremes; a global synthesis cannot tell the player where variability lives. |
| Hidden information currently discarded | Outcome-versus-expression components, within/between-session variance, hero/function/session-position contributions, core/stretch and recent conditional consistency. |
| Better estimator? | Hierarchical variance decomposition at match and session levels. Estimate a shrunk outcome-repeatability component and an expression-repeatability component separately; synthesize publicly only with calibrated rules. Weight information, not simply session count. |
| Better contextual normalization? | Decompose after the same cross-fitted hero/function/duration residualization used by Involvement/Exposure. Report context-specific inconsistency only with enough independent sessions and heroes. |
| Supporting signals to add | Outcome repeatability, expression repeatability, variance-source shares, conditional variance ratios, recent stability, leave-one-hero-out robustness. |
| Finding opportunities unlocked | “Not inconsistent overall—experiments explain the variance”; “results vary, expression holds”; “one secondary function creates most unpredictability.” |
| Keep public? | **Yes**, provided its internal components remain visible to the finding engine. |
| Recommended V6.1 definition | Calibrated synthesis of shrunk outcome and expression repeatability across sessions; allow “mixed/unclear.” Findings always identify the source rather than merely repeating the score. |

## 4.8 Verdict on the public ontology

Keep all seven, add none. Breadth and Toolkit describe portfolio extent and function; Involvement, Finishing, and Death Exposure describe summary expression; Transfer describes how that expression generalizes; Consistency describes repeatability. Lifecycle, eras, stopping, streak response, repetition, and exploration quality are relationships or states—not universal identity axes.

---

# Part 5 — Supporting signal catalog

The classification is architectural, not a quality rating. A signal can be excellent precisely because it is **not** public.

| # | Candidate signal | Class | Why |
|---:|---|---|---|
| 1 | Shannon effective heroes | PUBLIC ELEMENT | Breadth's stable, legible center. |
| 2 | Match-weighted effective jobs | PUBLIC ELEMENT | Toolkit's corrected center. |
| 3 | Adjusted activity residual | PUBLIC ELEMENT | Involvement input; narrow observable meaning. |
| 4 | Stabilized credited-kill share | PUBLIC ELEMENT | Finishing input; opportunity-gated. |
| 5 | Adjusted death rate | PUBLIC ELEMENT | Death Exposure input. |
| 6 | Continuous multivariate transfer frontier | PUBLIC ELEMENT | Transfer synthesis. |
| 7 | Shrunk outcome/expression repeatability | PUBLIC ELEMENT | Consistency synthesis. |
| 8 | Simpson effective heroes | SUPPORTING SIGNAL | Detects dominant head hidden by Shannon. |
| 9 | Top-1/top-3 dependence | SUPPORTING SIGNAL | Explains portfolio shape, not separate identity. |
| 10 | Stable core size | SUPPORTING SIGNAL | Bootstrap/window robustness under Breadth. |
| 11 | Reliable stretch size | SUPPORTING SIGNAL | Explains Transfer boundary. |
| 12 | Experimental-tail mass | SUPPORTING SIGNAL | Separates breadth from auditions. |
| 13 | Job redundancy | SUPPORTING SIGNAL | Distinguishes toolkit coverage from resilience. |
| 14 | Single-point function mass | SUPPORTING SIGNAL | One hero supplies a capability; useful evidence. |
| 15 | Hero functional overlap | SUPPORTING SIGNAL | Powers distance and name/style contradictions. |
| 16 | Activity stability | SUPPORTING SIGNAL | Explains Involvement and Consistency. |
| 17 | Exposure stability | SUPPORTING SIGNAL | Often more revealing than mean. |
| 18 | Outcome repeatability component | SUPPORTING SIGNAL | Must remain separate internally. |
| 19 | Expression repeatability component | SUPPORTING SIGNAL | Same. |
| 20 | Core-versus-stretch activity | CONDITIONAL SIGNAL | Only meaningful with supported groups. |
| 21 | Core-versus-stretch exposure | CONDITIONAL SIGNAL | Same. |
| 22 | Function-specific transfer | CONDITIONAL SIGNAL | Needs independent support within function. |
| 23 | Hero-conditioned finishing | CONDITIONAL SIGNAL | High context dependence and event gate. |
| 24 | Strong-loss versus weak-loss response | CONDITIONAL SIGNAL | Requires predeclared expression strata. |
| 25 | Game-position expression | CONDITIONAL SIGNAL | Requires enough long sessions/opportunities. |
| 26 | Solo-versus-party sensitivity | REJECT (current payload) | 36% non-random coverage cannot support a claim. |
| 27 | Lane-conditioned expression | REJECT (current payload) | 2.5% coverage; fallback only. |
| 28 | Recent Breadth/Toolkit | LONGITUDINAL SIGNAL | A time-bound state, not annual identity. |
| 29 | Hero distribution JSD | LONGITUDINAL SIGNAL | Detects name evolution. |
| 30 | Job distribution JSD | LONGITUDINAL SIGNAL | Detects toolkit evolution. |
| 31 | Core retention/replacement | LONGITUDINAL SIGNAL | Defines portfolio chapters. |
| 32 | Transfer-frontier trend | LONGITUDINAL SIGNAL | Supports recent improvement/decline. |
| 33 | Expression-variance trend | LONGITUDINAL SIGNAL | Recent consistency twist. |
| 34 | Hero audition retention | FINDING-ONLY FEATURE | Lifecycle opportunity; left-bound caveat. |
| 35 | First-win/first-loss return hazard | FINDING-ONLY FEATURE | Qualifies lifecycle outcome. |
| 36 | Rediscovery after dormancy | LONGITUDINAL SIGNAL | Hero lifecycle/evolution evidence. |
| 37 | Same-hero repeat probability | FINDING-ONLY FEATURE | Useful in result/session transitions, not identity. |
| 38 | Repeat-position curve | FINDING-ONLY FEATURE | Requires rare run opportunities. |
| 39 | Two-loss switch threshold | FINDING-ONLY FEATURE | A semantic rule only if contrast qualifies. |
| 40 | Win-streak exploration gradient | FINDING-ONLY FEATURE | Sequence-specific. |
| 41 | Loss-streak pool gradient | FINDING-ONLY FEATURE | Sequence-specific. |
| 42 | Stop after win/loss/recovery | FINDING-ONLY FEATURE | Operational boundary and censoring caveats. |
| 43 | Recurrent motif lift | FINDING-ONLY FEATURE | Useful only after baseline and session-stability checks. |
| 44 | Identity-era change point | LONGITUDINAL SIGNAL | Chapter evidence; not a permanent score. |
| 45 | Hero-change minus job-change | LONGITUDINAL SIGNAL | High-value identity migration relation. |
| 46 | GPM/XPM expression residual | SUPPORTING SIGNAL (research) | Adds context/conditioning, not “efficiency.” |
| 47 | Damage/healing/tower residuals | FINDING-ONLY FEATURE (research) | Highly function/mechanics dependent; require calibration. |
| 48 | Final-item fingerprint | REJECT for V6.1 | No purchase timing, patch-safe semantics, or build intent. |
| 49 | `average_rank`/`skill` | REJECT | Violates V6 rank/MMR-free evidence contract. |
| 50 | `cluster` as region/latency | REJECT | Server cluster does not prove geography or latency. |
| 51 | UTC time-of-day identity | REJECT | Player time zone is absent. |
| 52 | `hero_variant` identity | RESEARCH ONLY | Needs versioned facet semantics and adequate stability. |

The catalog's result is deliberate: exactly seven PUBLIC entries. There are far more conditional and finding-only features than identity scores because that is where personalized truth lives.

---

# Part 6 — Finding-family review

| V6 family | Coherence | Missing relationships / pressure | V6.1 decision |
|---|---|---|---|
| **Pool Shape** | Strong: portfolio composition and common thread belong together. | Stable core/tail, redundancy, exploration quality, lifecycle, name-versus-job migration, and eras are underdeveloped. | Keep key/name. Expand internal hypotheses to **shape**, **lifecycle**, and **evolution** branches. “Eras” is a cross-time presentation of this family, not a sixth family. |
| **Transfer** | Strong and genuinely multivariate. | Binary core, no equivalence/frontier, no function-conditioned or recent subtypes, no result/expression contradiction. | Keep. Replace binary-only qualification with continuous-distance model while retaining a simple core/stretch view for UI. |
| **Post-Loss Response** | Coherent but name is narrower than the opportunity. | Wins, streak length, strong/weak personal summary, repetition, function switching, pool distance, continuation/stopping. | Keep stable family key for V6.1; editorial label may render **Result Response** when evidence compares both sides. Add win/loss/streak branches. Do not create a separate Win family. |
| **Combat Expression** | Strong safety boundary around activity, exposure, finishing. | Conditional stability, covariance, hero/function/core/session localization, same-expression/different-result contradictions. | Keep. Add relationship outcomes; keep farm/damage/economy features research-only support. |
| **Session Drift** | Coherent if it describes within-session change. | Nonlinear breakpoints, Game 1 effect, selection change, repetition, conditional consistency, and stopping. | Keep. Expand from early/late to curve, breakpoint, choice-shift, and bounded stopping outcomes. |

### Is a new family necessary?

Not yet. “Behavioral Rules” and “Eras” are compelling product treatments but poor new testing families: their evidence is generated by Pool, Result Response, or Session hypotheses and would duplicate those tests. Treat `rule` and `era` as **semantic forms / interaction templates**, not independent families. Revisit only if held-out calibration shows a large, nonredundant set of cross-family motifs that cannot be assigned without distorting family error control.

### Family-level testing

Use a predeclared omnibus or global-null test for each of the five keys, then test semantic branches only inside qualified families using hierarchical FDR. Tree-structured testing better matches this architecture than pretending 60 sentences are 60 independent hypotheses ([Yekutieli, 2008](https://www.math.tau.ac.il/~yekutiel/papers/JASA%20FDR%20trees.pdf)). Within a family, rank by effect, stability, evidence diversity, and editorial value—not the smallest p-value. Publish at most one outcome per family and at most three total.

---

# Part 7 — 65-Finding library

## 7.1 Common analytical contracts

Each candidate below has all 20 requested attributes. Abbreviations keep the library auditable:

- **Raw E:** `kills,deaths,assists,duration`; **Raw H:** `hero_id,start_time`; **Raw O:** `player_slot,radiant_win`; all include match eligibility fields and `match_id`.
- **N-portfolio:** within-player annual proportions; no population role normalization. **N-expression:** cross-fitted hierarchical hero × fractional-function × nonlinear-duration residuals with only covered contexts. **N-transition:** matched within-player opportunities, session position/calendar band/core-distance controlled. **N-time:** session-block chronology with minimum segment and no silent recency weighting.
- **G-portfolio:** ≥100 eligible matches, ≥20 sessions, taxonomy coverage ≥80%. **G-life:** ≥20 left-bound-safe first-observed candidates and ≥8 retained events. **G-transfer:** ≥50 matches and ≥20 sessions per compared distance band. **G-transition:** ≥60 opportunities and ≥25 sessions per state. **G-session:** ≥40 observations at each compared position from ≥20 qualifying sessions. **G-era:** ≥120 matches and ≥45 sessions per segment.
- **Confidence:** unless narrowed, recompute the complete estimator in 2,000 session-cluster bootstrap samples; require a 95% interval beyond a practical-effect boundary, temporal/leave-one-dominant-hero stability, the family omnibus, and hierarchical BH `q≤.05`. Equivalence Findings require the interval inside a predeclared ROPE, not merely `p>.05`.
- **OOOH vector:** `(Surprise, Self-recognition, Accuracy, Specificity, Actionability, Shareability, Uniqueness, Analytical depth)`; total uses the requested `20/20/20/10/10/10/5/5%` weights. Scores are candidate ceiling estimates, not specimen results.

### Pool Shape candidates (PS01–PS17)

#### PS01 — Hidden center

- **1 Family:** Pool Shape. **2 Name:** Hidden center. **3 Headline:** “Your pool is wide, but half your year runs through six heroes.” **4 OOOH:** replaces an inflated unique count with recognizable shape; `(7,9,9,8,6,8,7,8) = 8.0`.
- **5 Elements:** Breadth. **6 Support:** effective/unique heroes, top-50% count, stable core, tail mass. **7 Raw:** H. **8 Algorithm:** entropy + cumulative share + bootstrap core stability. **9 Normalization:** N-portfolio. **10 Sample:** G-portfolio. **11 Sessions:** ≥20; each named core hero in ≥8. **12 Confidence:** standard contract; core membership ≥80% bootstrap stability.
- **13 Confounders:** bans, meta, draft demand, left boundary. **14 Supported:** observed concentration. **15 Forbidden:** “can only play six,” preference/motive, skill. **16 Evidence:** unique/effective count + six hero portraits + 50% brace. **17 Value:** honest pool mental model. **18 Recommendation:** identify one adjacent reliable-stretch hero for five games. **19 Interactive:** Core Boundary. **20 Share:** compact “63 → 26 → 6” reveal card.

#### PS02 — Smooth breadth

- **1 Family:** Pool Shape. **2 Name:** Smooth breadth. **3 Headline:** “Your breadth is real—there is no single hero holding the pool up.” **4 OOOH:** validates breadth rather than punishing specialization; `(6,8,9,7,5,7,6,7) = 7.15`.
- **5 Elements:** Breadth. **6 Support:** low top-1/3, Shannon≈Simpson, leave-one-hero-out. **7 Raw:** H. **8 Algorithm:** concentration-shape/equivalence tests. **9 Normalization:** N-portfolio. **10 Sample:** G-portfolio. **11 Sessions:** ≥25. **12 Confidence:** equivalence ROPE; stable across thirds.
- **13 Confounders:** forced role switching, mode mix. **14 Supported:** no dominant observed hero. **15 Forbidden:** equally skilled on all heroes. **16 Evidence:** ranked share bars and effective counts. **17 Value:** credible breadth recognition. **18 Recommendation:** consolidate an explicit three-hero “ready” core without abandoning breadth. **19 Interactive:** concentration curve. **20 Share:** pool silhouette.

#### PS03 — Core without tail

- **1 Family:** Pool Shape. **2 Name:** Deliberate compact pool. **3 Headline:** “This is not a one-trick year; it is a compact, repeatedly used core.” **4 OOOH:** distinguishes specialization from accidental low variety; `(5,8,9,7,7,6,6,7) = 7.05`.
- **5 Elements:** Breadth. **6 Support:** low effective count, ≥3 stable heroes, low one-off mass. **7 Raw:** H. **8 Algorithm:** core/tail decomposition. **9 Normalization:** N-portfolio. **10 Sample:** ≥60 matches. **11 Sessions:** ≥20, core spans ≥3 calendar thirds. **12 Confidence:** standard stability.
- **13 Confounders:** short account/window, hero release/patch. **14 Supported:** compact recurring selection. **15 Forbidden:** inflexibility or narrow skill. **16 Evidence:** core shares and calendar coverage. **17 Value:** makes a low Breadth score nonjudgmental. **18 Recommendation:** add only a function-adjacent stretch option. **19 Interactive:** stable-core ring. **20 Share:** “compact by repetition” badge.

#### PS04 — Redundant toolkit

- **1 Family:** Pool Shape. **2 Name:** Functional redundancy. **3 Headline:** “Several heroes can do your main jobs; your toolkit does not depend on one name.” **4 OOOH:** exposes resilience underneath hero choice; `(7,8,8,8,7,7,8,9) = 7.65`.
- **5 Elements:** Toolkit, Breadth. **6 Support:** job mass, per-job established hero count, taxonomy overlap. **7 Raw:** H + taxonomy. **8 Algorithm:** fractional job contribution network. **9 Normalization:** N-portfolio with taxonomy sensitivity. **10 Sample:** G-portfolio; ≥3 meaningful jobs. **11 Sessions:** each redundant provider ≥6 sessions. **12 Confidence:** bootstrap/taxonomy perturbation.
- **13 Confounders:** multi-tag inflation, hero facets. **14 Supported:** multiple selected heroes provide overlapping taxonomy jobs. **15 Forbidden:** draft interchangeability or equal execution. **16 Evidence:** job→hero mini-network. **17 Value:** actionable pool resilience. **18 Recommendation:** name a backup hero for the least redundant core job. **19 Interactive:** Toolkit map. **20 Share:** “three ways to start fights” card.

#### PS05 — Single-point function

- **1 Family:** Pool Shape. **2 Name:** Single-point capability. **3 Headline:** “One hero supplies almost all of one meaningful job in your pool.” **4 OOOH:** specific vulnerability hidden by a broad Toolkit score; `(8,8,8,9,9,7,8,9) = 8.15`.
- **5 Elements:** Toolkit, Breadth. **6 Support:** job mass, provider count, hero share, taxonomy confidence. **7 Raw:** H + taxonomy. **8 Algorithm:** attributable fractional job mass and leave-one-hero-out Toolkit loss. **9 Normalization:** N-portfolio. **10 Sample:** G-portfolio; job mass ≥10%. **11 Sessions:** provider ≥10; alternatives collectively ≥8. **12 Confidence:** bootstrap loss exceeds practical boundary.
- **13 Confounders:** taxonomy incompleteness, multi-role hero use. **14 Supported:** observed selections expose a single-provider job. **15 Forbidden:** cannot perform job on other heroes. **16 Evidence:** Toolkit before/after removing hero. **17 Value:** clear pool gap. **18 Recommendation:** five games on one adjacent provider. **19 Interactive:** remove-a-hero simulation. **20 Share:** cracked-link reveal.

#### PS06 — Names wide, jobs narrow

- **1 Family:** Pool Shape. **2 Name:** Cosmetic exploration. **3 Headline:** “You experiment with heroes constantly, but most experiments keep you inside the same few jobs.” **4 OOOH:** a sharp contradiction experienced players recognize; `(9,9,8,9,8,9,9,9) = 8.70`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** high hero/low job effective count, high pairwise functional overlap, experimental-tail job mass. **7 Raw:** H + taxonomy. **8 Algorithm:** calibrated Breadth×Toolkit contradiction and tail-vs-core job JSD. **9 Normalization:** N-portfolio. **10 Sample:** G-portfolio; ≥12 tail heroes. **11 Sessions:** ≥30. **12 Confidence:** both axes stable; taxonomy sensitivity.
- **13 Confounders:** broad/overlapping taxonomy tags, hero role variation. **14 Supported:** different selected names map to similar job mixture. **15 Forbidden:** same playstyle inside matches, unwillingness to learn. **16 Evidence:** hero count reveal → effective jobs. **17 Value:** turns exploration into an honest question. **18 Recommendation:** try five games on a taxonomy-distant hero in the same lane context if available. **19 Interactive:** Contradiction Reveal. **20 Share:** “25 heroes, 4 jobs” card.

#### PS07 — Names narrow, jobs wide

- **1 Family:** Pool Shape. **2 Name:** Compact versatility. **3 Headline:** “A small set of heroes gives you a surprisingly wide toolkit.” **4 OOOH:** positive inverse contradiction; `(8,9,8,9,8,8,8,9) = 8.3`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** low hero/high job effective count, per-hero job breadth, redundancy. **7 Raw:** H + taxonomy. **8 Algorithm:** opposite-zone contradiction with leave-one-hero-out check. **9 Normalization:** N-portfolio. **10 Sample:** ≥80 matches; taxonomy ≥80%. **11 Sessions:** ≥25. **12 Confidence:** standard + taxonomy perturbation.
- **13 Confounders:** taxonomy describes capability, not actual match role. **14 Supported:** selected heroes collectively cover many taxonomy jobs. **15 Forbidden:** performs every job each match. **16 Evidence:** hero portraits unfolding into job map. **17 Value:** reframes narrow Breadth without stigma. **18 Recommendation:** reinforce the one thinly represented job. **19 Interactive:** Toolkit fan-out. **20 Share:** compact-versatility badge.

#### PS08 — Portfolio islands

- **1 Family:** Pool Shape. **2 Name:** Portfolio islands. **3 Headline:** “Your pool is not one gradient; it has two separated functional islands.” **4 OOOH:** reveals contextual identities; `(8,8,7,9,7,8,9,9) = 7.90`.
- **5 Elements:** Breadth, Toolkit, Transfer. **6 Support:** taxonomy-vector clusters, hero mass, between-cluster transfer. **7 Raw:** H, O, E + taxonomy. **8 Algorithm:** stable graph clustering then held-out cluster contrast. **9 Normalization:** N-portfolio + N-expression. **10 Sample:** ≥150; ≥40 matches/island. **11 Sessions:** ≥20/island. **12 Confidence:** cluster stability and family test.
- **13 Confounders:** taxonomy resolution, patch/meta, lane unavailable. **14 Supported:** two observed selection/function clusters. **15 Forbidden:** two personalities/roles. **16 Evidence:** two labeled islands with expression summaries. **17 Value:** “two versions of you” foundation. **18 Recommendation:** bridge with one adjacent hero. **19 Interactive:** Two Versions of You. **20 Share:** dual-island card.

#### PS09 — Frequent auditions, low adoption

- **1 Family:** Pool Shape. **2 Name:** Audition-heavy explorer. **3 Headline:** “You try many heroes; very few earn a lasting place.” **4 OOOH:** recognizes process, not just breadth; `(8,9,8,8,8,8,8,9) = 8.2`.
- **5 Elements:** Breadth. **6 Support:** first-observed entries, second/3/5-game hazards, tail share, retention. **7 Raw:** H, O. **8 Algorithm:** left-truncated lifecycle survival with 60-day burn-in and right-censoring. **9 Normalization:** N-time. **10 Sample:** G-life. **11 Sessions:** candidate returns must span independent sessions. **12 Confidence:** interval on retention vs player baseline/cohort calibration.
- **13 Confounders:** pre-window hero history, event modes, bans. **14 Supported:** first-observed-in-window trials rarely recur. **15 Forbidden:** truly new hero, gives up, dislike. **16 Evidence:** audition funnel. **17 Value:** makes exploration quality visible. **18 Recommendation:** precommit next experiment to three games before evaluation. **19 Interactive:** Hero Lifecycle. **20 Share:** audition funnel.

#### PS10 — Game-3 adoption gate

- **1 Family:** Pool Shape. **2 Name:** Game-3 gate. **3 Headline:** “Most trials vanish early; heroes that reach Game 3 usually keep returning.” **4 OOOH:** sounds like a friend's observation; `(9,9,7,9,8,9,9,9) = 8.50`.
- **5 Elements:** Breadth. **6 Support:** conditional return hazards after observed games 1/2/3, retained mass. **7 Raw:** H, O. **8 Algorithm:** landmark survival/hazard model with burn-in and censoring. **9 Normalization:** N-time. **10 Sample:** G-life; ≥10 reach Game 3. **11 Sessions:** games must span ≥2 sessions; retention ≥3 later sessions. **12 Confidence:** hazard jump interval and split-window replication.
- **13 Confounders:** left boundary, hero release, role access. **14 Supported:** observed retention threshold. **15 Forbidden:** conscious decision or learning completed. **16 Evidence:** survival curve with Game 3 highlighted. **17 Value:** clarifies the player's selection rule. **18 Recommendation:** test rejected heroes with a three-game commitment. **19 Interactive:** lifecycle threshold scrubber. **20 Share:** “Game 3 decides” card.

#### PS11 — First result does not decide

- **1 Family:** Pool Shape. **2 Name:** Result-resistant audition. **3 Headline:** “A first win and a first loss are followed by nearly the same return rate.” **4 OOOH:** contradicts easy tilt stories; `(7,8,8,9,6,7,8,8) = 7.60`.
- **5 Elements:** Breadth. **6 Support:** censored return hazards by first observed result, equivalence band. **7 Raw:** H, O. **8 Algorithm:** matched lifecycle equivalence test. **9 Normalization:** N-transition + N-time. **10 Sample:** ≥30 candidates, ≥12 per first-result state. **11 Sessions:** independent next-session returns. **12 Confidence:** equivalence interval; not nonsignificance.
- **13 Confounders:** pre-window familiarity, matchup/draft. **14 Supported:** first observed result does not materially change recurrence. **15 Forbidden:** player ignores results or is emotionally unaffected. **16 Evidence:** two return bars + ROPE. **17 Value:** debunks a tempting narrative. **18 Recommendation:** evaluate trials on three-game expression, not first result. **19 Interactive:** win/loss toggle. **20 Share:** “first result ≠ verdict.”

#### PS12 — Fast adoption

- **1 Family:** Pool Shape. **2 Name:** Fast adopter. **3 Headline:** “When a hero belongs, your history usually shows it within days—not months.” **4 OOOH:** temporal specificity; `(8,9,7,9,8,8,8,9) = 8.15`.
- **5 Elements:** Breadth. **6 Support:** time from first-observed to 3rd/5th game among retained heroes. **7 Raw:** H. **8 Algorithm:** censored adoption-time distribution versus personal trial baseline. **9 Normalization:** active-day exposure, not calendar alone. **10 Sample:** ≥12 adopted heroes. **11 Sessions:** ≥3 sessions/hero. **12 Confidence:** bootstrap median/quantiles stable across windows.
- **13 Confounders:** schedule gaps, pre-window experience, hero availability. **14 Supported:** retained heroes accumulate observed games quickly. **15 Forbidden:** learns quickly or consciously decides. **16 Evidence:** days-to-five dot plot. **17 Value:** improves experiment cadence. **18 Recommendation:** reserve three sessions for a candidate before verdict. **19 Interactive:** lifecycle timeline. **20 Share:** speedometer card.

#### PS13 — Rediscovery habit

- **1 Family:** Pool Shape. **2 Name:** Deep-shelf returns. **3 Headline:** “You regularly bring heroes back after two months away.” **4 OOOH:** recognizes dormant repertoire; `(7,8,8,8,6,8,8,8) = 7.60`.
- **5 Elements:** Breadth. **6 Support:** ≥60-day gaps, pre/post return run, hero recurrence. **7 Raw:** H, O. **8 Algorithm:** dormant-return event detection with active-day exposure. **9 Normalization:** N-time; exclude global inactivity gaps. **10 Sample:** ≥8 rediscoveries over ≥5 heroes. **11 Sessions:** returns in independent sessions. **12 Confidence:** rate above shuffled-chronology expectation.
- **13 Confounders:** patches, Cavern/event goals, long general inactivity. **14 Supported:** observed selected heroes recur after dormancy. **15 Forbidden:** relearning, nostalgia, intent. **16 Evidence:** dormant→return arcs. **17 Value:** finds usable stretch candidates. **18 Recommendation:** choose the returned hero with closest expression to current core for five games. **19 Interactive:** Hero Lifecycle shelf. **20 Share:** comeback reel.

#### PS14 — Core replacement

- **1 Family:** Pool Shape. **2 Name:** Replaced center. **3 Headline:** “Your old core did not merely shrink; a different set took its place.” **4 OOOH:** identity evolution rather than a recent-form blip; `(9,9,8,9,7,9,9,9) = 8.6`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** stable era split, low core retention, new-core emergence, share crossover. **7 Raw:** H + taxonomy. **8 Algorithm:** penalized multinomial change points + session-block validation. **9 Normalization:** N-time. **10 Sample:** G-era. **11 Sessions:** G-era. **12 Confidence:** held-out/penalized split, permutation, boundary robustness.
- **13 Confounders:** patch/meta, role availability, 365-day truncation. **14 Supported:** selected hero distribution has a durable replacement. **15 Forbidden:** “became better/different person,” causal patch claim. **16 Evidence:** before/after core ranks. **17 Value:** strongest annual reflection. **18 Recommendation:** decide which former core hero remains an intentional fallback. **19 Interactive:** Pool Evolution Scrubber. **20 Share:** before/after lineup.

#### PS15 — Names changed, jobs held

- **1 Family:** Pool Shape. **2 Name:** Stable toolkit migration. **3 Headline:** “Your hero names changed. The jobs you repeatedly chose barely did.” **4 OOOH:** precise identity contradiction; `(9,10,8,10,7,10,10,10) = 9.10`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** high hero JSD, job JSD inside equivalence band, stable top jobs. **7 Raw:** H + taxonomy. **8 Algorithm:** paired distribution-change model with taxonomy uncertainty. **9 Normalization:** N-time/N-portfolio. **10 Sample:** G-era. **11 Sessions:** G-era. **12 Confidence:** hero change qualifies; job equivalence qualifies; split stability.
- **13 Confounders:** taxonomy too coarse, actual in-match role unknown, patch. **14 Supported:** chosen names moved more than taxonomy job mixture. **15 Forbidden:** playstyle literally unchanged. **16 Evidence:** hero turnover animation over fixed job bars. **17 Value:** exceptionally recognizable migration story. **18 Recommendation:** select new heroes by the one job not already covered. **19 Interactive:** Identity Eras. **20 Share:** split-panel “names moved / jobs held.”

#### PS16 — Names held, jobs changed

- **1 Family:** Pool Shape. **2 Name:** Functional migration under stable names. **3 Headline:** “Your familiar hero center stayed visible, but the surrounding toolkit changed.” **4 OOOH:** detects change a hero-count page misses; `(9,9,7,9,7,9,10,10) = 8.5`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** hero-distribution equivalence, job JSD change, changed secondary-hero mass. **7 Raw:** H + taxonomy. **8 Algorithm:** paired divergence/attribution model. **9 Normalization:** N-time. **10 Sample:** G-era. **11 Sessions:** G-era. **12 Confidence:** inverse dual qualification and taxonomy sensitivity.
- **13 Confounders:** taxonomy cannot observe within-hero role changes. **14 Supported:** selected hero mixture stable relative to job mixture change caused by surrounding picks. **15 Forbidden:** same heroes performed different in-game jobs unless directly represented. **16 Evidence:** fixed hero center, changing job ring. **17 Value:** subtle evolution. **18 Recommendation:** test whether the new job mix is intentional across five picks. **19 Interactive:** layered scrubber. **20 Share:** “same center, new toolkit.”

#### PS17 — Multiple identity eras

- **1 Family:** Pool Shape. **2 Name:** A year in chapters. **3 Headline:** “Your Dota year contains three statistically distinct selection eras.” **4 OOOH:** turns 900 rows into a memorable history; `(10,9,7,10,6,10,10,10) = 8.80`.
- **5 Elements:** Breadth, Toolkit; optional expression anchors. **6 Support:** ≥2 penalized change points, stable segment distributions, minimum eras. **7 Raw:** H, optional E/O + taxonomy. **8 Algorithm:** PELT/segment-neighborhood candidates, session-block resampling, held-out penalty calibration. **9 Normalization:** N-time. **10 Sample:** ≥360 matches total. **11 Sessions:** ≥45/era. **12 Confidence:** no segmentation unless improvement exceeds penalty and survives 60/90/120-minute session sensitivity.
- **13 Confounders:** patch/meta, long inactivity, one hero spam burst. **14 Supported:** observable identity features differ by chapter. **15 Forbidden:** cause, exact conscious turning point, skill progression. **16 Evidence:** era cards with 2–3 decisive changes. **17 Value:** flagship annual reflection. **18 Recommendation:** choose which era's pool shape to carry forward. **19 Interactive:** Identity Eras swipe/scrub. **20 Share:** three-chapter strip.

### Transfer candidates (TR01–TR12)

#### TR01 — Clean transfer

- **1 Family:** Transfer. **2 Name:** Clean transfer. **3 Headline:** “Your results and summary expression both hold beyond the core.” **4 OOOH:** validates real generalization, not breadth alone; `(7,9,8,8,8,8,7,9) = 8.00`.
- **5 Elements:** Transfer, Involvement, Death Exposure. **6 Support:** outcome/activity/exposure equivalence across distance. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** partially pooled frontier with three equivalence tests. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥20/band. **12 Confidence:** all required ROPEs plus frontier bootstrap.
- **13 Confounders:** hero selection/draft, taxonomy, unobserved lane. **14 Supported:** observed summary measures remain practically similar. **15 Forbidden:** equally skilled on every hero. **16 Evidence:** three aligned core→edge curves. **17 Value:** credible adaptability evidence. **18 Recommendation:** extend one distance band for five controlled-context games. **19 Interactive:** Core Boundary. **20 Share:** “expression travels” card.

#### TR02 — Result transfer failure

- **1 Family:** Transfer. **2 Name:** Results stop first. **3 Headline:** “Outside your core, activity and exposure hold—but results do not.” **4 OOOH:** localizes the drop without blaming execution; `(8,9,8,9,9,8,8,10) = 8.5`.
- **5 Elements:** Transfer, Consistency. **6 Support:** outcome difference outside ROPE; activity/exposure equivalence. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** frontier component decomposition. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥20/band. **12 Confidence:** one difference + two equivalences, FDR/stability.
- **13 Confounders:** draft strength, opponents, lane, hero learning. **14 Supported:** scoreboard expression transfers farther than outcome. **15 Forbidden:** why outcomes differ, luck, decision quality. **16 Evidence:** two flat tracks + result break. **17 Value:** identifies where Deep should look. **18 Recommendation:** five stretch games holding function constant. **19 Interactive:** Two Versions. **20 Share:** “same expression, different scoreboard.”

#### TR03 — Expression stops first

- **1 Family:** Transfer. **2 Name:** Results travel farther than expression. **3 Headline:** “Your results hold outside the core, but the way they appear in the summary changes.” **4 OOOH:** counterintuitive and nuanced; `(9,9,8,9,8,9,9,10) = 8.7`.
- **5 Elements:** Transfer plus changing Involvement and/or Death Exposure. **6 Support:** outcome equivalence; expression break. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** component frontier. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥20/band. **12 Confidence:** equivalence + practical expression difference.
- **13 Confounders:** function mix, game duration/state. **14 Supported:** same observed result rate accompanies different summary expression. **15 Forbidden:** style, strategy, or decisions changed unless parsed. **16 Evidence:** result track continues while expression track bends. **17 Value:** premium “how did it know” contradiction. **18 Recommendation:** five stretch games tracking the changed component. **19 Interactive:** Core Boundary layers. **20 Share:** broken-line card.

#### TR04 — It works differently

- **1 Family:** Transfer. **2 Name:** Different expression, working result. **3 Headline:** “You play the edge of your pool differently in the summary—and it works anyway.” **4 OOOH:** positive contradiction; `(9,9,8,9,7,9,9,9) = 8.6`.
- **5 Elements:** Transfer, Involvement, Death Exposure, optional Finishing. **6 Support:** outcome equivalence plus coherent expression shifts. **7 Raw:** H,O,E. **8 Algorithm:** multivariate equivalence/difference profile. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥25/band. **12 Confidence:** at least two expression signals or one large stable signal.
- **13 Confounders:** taxonomy/role mix. **14 Supported:** result holds while specified summary rates move. **15 Forbidden:** strategic adaptation or superior versatility. **16 Evidence:** “same result / different signature” split. **17 Value:** contextual identity. **18 Recommendation:** retain the edge heroes whose result and exposure remain supported. **19 Interactive:** Two Versions. **20 Share:** mirrored profile card.

#### TR05 — Activity-only boundary

- **1 Family:** Transfer. **2 Name:** Involvement boundary. **3 Headline:** “The first thing that changes away from your core is involvement—not exposure.” **4 OOOH:** names a precise frontier component; `(7,8,8,9,8,7,8,9) = 7.85`.
- **5 Elements:** Transfer, Involvement, Death Exposure. **6 Support:** activity curve breaks; exposure equivalent. **7 Raw:** H,E + taxonomy. **8 Algorithm:** component change/equivalence over distance. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥20/band. **12 Confidence:** standard component contract.
- **13 Confounders:** function/lane, match state. **14 Supported:** adjusted event rate changes first. **15 Forbidden:** less active by choice, teamfight absence. **16 Evidence:** frontier ruler. **17 Value:** targeted experiment. **18 Recommendation:** five adjacent heroes in same function, track `(K+A)/min`. **19 Interactive:** metric selector. **20 Share:** concise frontier card.

#### TR06 — Exposure-only boundary

- **1 Family:** Transfer. **2 Name:** Exposure boundary. **3 Headline:** “Your involvement travels; death exposure is where the stretch pool separates.” **4 OOOH:** highly actionable safe combat relation; `(8,9,8,9,9,8,8,9) = 8.4`.
- **5 Elements:** Transfer, Involvement, Death Exposure. **6 Support:** involvement equivalence, exposure difference, optional result. **7 Raw:** H,E,O + taxonomy. **8 Algorithm:** frontier decomposition. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥20/band. **12 Confidence:** equivalence + difference.
- **13 Confounders:** hero durability/function, outcome state. **14 Supported:** adjusted exposure changes at distance. **15 Forbidden:** bad deaths or positioning. **16 Evidence:** stable involvement line + exposure step. **17 Value:** clear Deep handoff. **18 Recommendation:** five adjacent stretch games; monitor exposure only. **19 Interactive:** Two Versions. **20 Share:** “presence travels / exposure doesn't.”

#### TR07 — Conditional clean transfer

- **1 Family:** Transfer. **2 Name:** One-function transfer. **3 Headline:** “Your stretch pool transfers cleanly inside one job family.” **4 OOOH:** turns a weak global score into a usable boundary; `(7,9,7,9,9,7,8,9) = 8.0`.
- **5 Elements:** Transfer, Toolkit. **6 Support:** function-specific frontiers and interaction. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** partially pooled distance×function model. **9 Normalization:** N-expression. **10 Sample:** ≥60/band inside function. **11 Sessions:** ≥25/function band. **12 Confidence:** interaction plus within-function equivalence, multiplicity controlled.
- **13 Confounders:** taxonomy and sparse cells. **14 Supported:** transfer differs by observed function mixture. **15 Forbidden:** role mastery. **16 Evidence:** small multiples by job. **17 Value:** safe expansion path. **18 Recommendation:** choose stretch heroes in the qualifying job for five games. **19 Interactive:** function filter on Core Boundary. **20 Share:** “your reliable lane out” card.

#### TR08 — One-function bottleneck

- **1 Family:** Transfer. **2 Name:** Narrow bottleneck. **3 Headline:** “Your off-pool drop is narrower than it looks: one job family accounts for most of it.” **4 OOOH:** highly specific and actionable; `(9,9,8,10,9,9,9,10) = 8.9`.
- **5 Elements:** Transfer, Toolkit, Consistency. **6 Support:** function attribution of frontier failure, leave-function-out recovery. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** hierarchical attribution with held-out function interaction. **9 Normalization:** N-expression. **10 Sample:** ≥200; offending function ≥60. **11 Sessions:** ≥25/function. **12 Confidence:** interaction, dominance share, leave-one-hero-out.
- **13 Confounders:** one hero may masquerade as function; lane/draft. **14 Supported:** supported function subset explains observed difference. **15 Forbidden:** root cause inside games. **16 Evidence:** global gap collapses when function is filtered. **17 Value:** turns broad weakness into precise question. **18 Recommendation:** five same-function adjacent heroes or temporarily narrow it. **19 Interactive:** tap-to-remove attribution. **20 Share:** bottleneck reveal.

#### TR09 — Asymmetric frontier

- **1 Family:** Transfer. **2 Name:** Names travel, jobs do not. **3 Headline:** “You can move far across hero names as long as the underlying job stays close.” **4 OOOH:** combines portfolio and transfer distance; `(9,9,7,9,9,9,9,10) = 8.6`.
- **5 Elements:** Breadth, Toolkit, Transfer. **6 Support:** familiarity distance, taxonomy distance, interaction. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** two-dimensional transfer surface. **9 Normalization:** N-expression. **10 Sample:** ≥250 with populated distance quadrants. **11 Sessions:** ≥20/quadrant. **12 Confidence:** stable taxonomy-distance interaction.
- **13 Confounders:** taxonomy coarseness, unavailable actual role. **14 Supported:** expression/outcome holds with name distance conditional on job proximity. **15 Forbidden:** hero mechanics do not matter. **16 Evidence:** 2D frontier map. **17 Value:** best pool-expansion guidance. **18 Recommendation:** expand names one job step at a time. **19 Interactive:** frontier surface. **20 Share:** “far names / near jobs.”

#### TR10 — Frontier improving

- **1 Family:** Transfer. **2 Name:** Expanding frontier. **3 Headline:** “The recent version of your stretch pool carries farther than the early-year version.” **4 OOOH:** recognizes growth without skill claims; `(8,9,7,9,8,8,9,10) = 8.2`.
- **5 Elements:** Transfer, Consistency. **6 Support:** frontier by independent era/window, stable core definition. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** time-varying partially pooled frontier. **9 Normalization:** N-expression + N-time. **10 Sample:** ≥150/window. **11 Sessions:** ≥50/window. **12 Confidence:** interaction and change-point stability.
- **13 Confounders:** patch, hero mix, regression. **14 Supported:** observed transfer estimates improved recently. **15 Forbidden:** learning caused it or permanent improvement. **16 Evidence:** old/new frontier overlay. **17 Value:** longitudinal twist. **18 Recommendation:** repeat five recent stretch picks under similar function. **19 Interactive:** time scrubber. **20 Share:** expanding-ring card.

#### TR11 — Experiments create variance, not weakness

- **1 Family:** Transfer. **2 Name:** Volatile edge. **3 Headline:** “Your experimental edge is not consistently weaker; it is less predictable.” **4 OOOH:** separates average from variance; `(8,9,8,9,8,8,8,10) = 8.4`.
- **5 Elements:** Transfer, Consistency. **6 Support:** outcome/expression means equivalent; variance higher outside frontier. **7 Raw:** H,O,E. **8 Algorithm:** hierarchical mean equivalence + variance ratio. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥25/band. **12 Confidence:** mean ROPE + variance interval.
- **13 Confounders:** sparse heroes, opponent/draft mix. **14 Supported:** observed average holds while dispersion rises. **15 Forbidden:** unreliable person or risky player. **16 Evidence:** equal centers/different bands. **17 Value:** explains “inconsistency” locally. **18 Recommendation:** precommit experiments in five-game blocks. **19 Interactive:** uncertainty bands. **20 Share:** same-center/wider-cloud.

#### TR12 — Off-pool steadier

- **1 Family:** Transfer. **2 Name:** Counterintuitive steadiness. **3 Headline:** “Outside the core, your summary expression is actually more repeatable.” **4 OOOH:** rare inverse; `(9,9,7,9,6,9,9,9) = 8.3`.
- **5 Elements:** Transfer, Consistency. **6 Support:** conditional variance ratio <1 with mean context shown. **7 Raw:** H,O,E. **8 Algorithm:** hierarchical variance decomposition. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥30/band. **12 Confidence:** variance interval, leave-one-hero-out.
- **13 Confounders:** stretch heroes may be one homogeneous function; selection. **14 Supported:** lower observed adjusted dispersion in supported stretch games. **15 Forbidden:** plays better/safer or should abandon core. **16 Evidence:** two distribution clouds. **17 Value:** surprising localization. **18 Recommendation:** identify which stretch context supplies repeatability. **19 Interactive:** Two Versions. **20 Share:** inverse-consistency card.

### Post-Loss / Result Response candidates (RR01–RR14)

#### RR01 — Run it back after one

- **1 Family:** Post-Loss Response. **2 Name:** One-loss runback. **3 Headline:** “After one loss, you are unusually likely to run the same hero back.” **4 OOOH:** a concrete observed habit; `(8,9,8,9,7,9,8,8) = 8.3`.
- **5 Elements:** Breadth; optional Transfer. **6 Support:** same-hero probability after exactly one loss vs matched win/neutral baseline. **7 Raw:** H,O. **8 Algorithm:** opportunity-matched transition contrast. **9 Normalization:** N-transition. **10 Sample:** G-transition. **11 Sessions:** within-session transitions across ≥25 sessions. **12 Confidence:** cluster interval, calendar/core controls.
- **13 Confounders:** hero availability/draft, player may not control pick. **14 Supported:** repeat selection follows one loss more often. **15 Forbidden:** stubbornness, tilt, conscious retry. **16 Evidence:** After X toggle with repeat rates. **17 Value:** immediate recognition. **18 Recommendation:** predeclare one runback maximum for five relevant losses. **19 Interactive:** After X. **20 Share:** two-match strip.

#### RR02 — Unwritten two-loss switch

- **1 Family:** Post-Loss Response. **2 Name:** Two-loss rule. **3 Headline:** “One loss barely changes your choice. The second one does.” **4 OOOH:** friend-level specificity; `(10,10,7,10,8,10,10,10) = 9.20`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** switch probability after one vs 2+ consecutive losses; no comparable win-streak jump. **7 Raw:** H,O + taxonomy. **8 Algorithm:** run-length transition model with threshold versus monotone alternative. **9 Normalization:** N-transition. **10 Sample:** ≥80 one-loss and ≥40 2+ opportunities. **11 Sessions:** ≥30/20. **12 Confidence:** breakpoint effect, negative control, split-window stability.
- **13 Confounders:** draft/bans, sessions ending, few long streaks. **14 Supported:** observed switch probability rises after the second consecutive loss. **15 Forbidden:** conscious rule, emotional tilt, causation. **16 Evidence:** 0/1/2/3-loss step curve. **17 Value:** defining Free insight. **18 Recommendation:** test a predeclared decision rule over five 2+ loss events. **19 Interactive:** After X slider. **20 Share:** animated two-loss switch.

#### RR03 — Two losses → core → stabilization

- **1 Family:** Post-Loss Response. **2 Name:** Core recovery chain. **3 Headline:** “Two losses pull you toward the core—and those next games return closer to your baseline.” **4 OOOH:** context→change→outcome chain; `(10,9,7,10,9,9,10,10) = 9.0`.
- **5 Elements:** Breadth, Transfer, Consistency. **6 Support:** streak→distance drop; core return→outcome/expression stabilization; matched alternative. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** sequential mediation-shaped description without causal estimator. **9 Normalization:** N-transition/N-expression. **10 Sample:** ≥60 2+ loss events, ≥30 core returns. **11 Sessions:** ≥25. **12 Confidence:** both links qualify; full-chain bootstrap and FDR.
- **13 Confounders:** selection, regression to mean, draft/opponents. **14 Supported:** recurring ordered association. **15 Forbidden:** core return caused recovery or fixes tilt. **16 Evidence:** three-node chain with counts/deltas. **17 Value:** high-action insight. **18 Recommendation:** five 2-loss events with a preselected core option; compare descriptively. **19 Interactive:** Behavioral Chain. **20 Share:** animated chain.

#### RR04 — Switch names, keep jobs

- **1 Family:** Post-Loss Response. **2 Name:** Functional runback. **3 Headline:** “After losses, the hero changes more often than the underlying job.” **4 OOOH:** observes adjustment under surface sameness; `(9,9,8,10,7,9,9,10) = 8.8`.
- **5 Elements:** Breadth, Toolkit. **6 Support:** hero switch, fractional job overlap, matched win baseline. **7 Raw:** H,O + taxonomy. **8 Algorithm:** paired hero identity vs taxonomy-vector transition. **9 Normalization:** N-transition. **10 Sample:** G-transition. **11 Sessions:** ≥25. **12 Confidence:** hero/job contrast bootstrap + taxonomy sensitivity.
- **13 Confounders:** taxonomy broadness, actual role unavailable. **14 Supported:** selected names change while mapped jobs overlap. **15 Forbidden:** playstyle did not change. **16 Evidence:** hero swap over fixed job icons. **17 Value:** classic contradiction. **18 Recommendation:** decide whether the next adjustment should change job distance, not only name. **19 Interactive:** After X job overlay. **20 Share:** “switch outside / same underneath.”

#### RR05 — Change without result movement

- **1 Family:** Post-Loss Response. **2 Name:** Adjustment without recovery difference. **3 Headline:** “Your post-loss choices change sharply; the next-result rate does not.” **4 OOOH:** punctures a comforting story safely; `(8,9,8,9,8,8,8,9) = 8.4`.
- **5 Elements:** Breadth, Transfer. **6 Support:** large hero/job/distance shift, next-result equivalence vs no-change/matched control. **7 Raw:** H,O + taxonomy. **8 Algorithm:** matched transition groups with outcome ROPE. **9 Normalization:** N-transition. **10 Sample:** ≥50 changed and unchanged responses. **11 Sessions:** ≥25/group. **12 Confidence:** behavior difference + outcome equivalence.
- **13 Confounders:** draft, regression, selection into switch. **14 Supported:** observable adjustment is not accompanied by material next-result difference. **15 Forbidden:** adjustment is useless or caused no benefit. **16 Evidence:** choice delta + equal result bars. **17 Value:** encourages experimentation with rules. **18 Recommendation:** hold one response constant for five losses. **19 Interactive:** response/outcome toggle. **20 Share:** “big switch, flat result.”

#### RR06 — No change, strong recovery

- **1 Family:** Post-Loss Response. **2 Name:** Stable response. **3 Headline:** “Your strongest observed recoveries often come when the next pick stays close to the previous one.” **4 OOOH:** inverse of common switching advice; `(9,9,7,9,9,9,8,9) = 8.5`.
- **5 Elements:** Transfer, Consistency. **6 Support:** low distance movement after loss, matched recovery difference, expression stability. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** matched response-distance curve. **9 Normalization:** N-transition/N-expression. **10 Sample:** ≥50 losses across distance bands. **11 Sessions:** ≥25. **12 Confidence:** dose-response stability and practical effect.
- **13 Confounders:** stronger heroes more likely repeated; selection. **14 Supported:** near-constant responses associate with stronger observed recovery. **15 Forbidden:** staying same causes wins. **16 Evidence:** recovery by adjustment distance. **17 Value:** concrete five-game test. **18 Recommendation:** preselect a repeat/adjacent response for five losses. **19 Interactive:** distance dial. **20 Share:** “less change, better return” with observational badge.

#### RR07 — Wins expand, losses contract

- **1 Family:** Post-Loss Response. **2 Name:** Result-shaped pool. **3 Headline:** “Winning widens your next pick; losing pulls it inward.” **4 OOOH:** symmetric, visual, recognizable; `(9,9,8,9,8,10,9,10) = 8.9`.
- **5 Elements:** Breadth, Transfer. **6 Support:** continuous next-pick distance/diversity after win vs loss, matched within session. **7 Raw:** H,O + taxonomy. **8 Algorithm:** bidirectional transition model. **9 Normalization:** N-transition. **10 Sample:** G-transition both states. **11 Sessions:** ≥30/state. **12 Confidence:** opposite signed changes, calendar/core controls.
- **13 Confounders:** draft order, bans, streak/session position. **14 Supported:** observed selection expands/contracts conditionally. **15 Forbidden:** confidence, fear, tilt. **16 Evidence:** pool ring breathes under Win/Loss toggle. **17 Value:** flagship self-recognition. **18 Recommendation:** compare one deliberate post-win core pick and one post-loss adjacent pick across five opportunities. **19 Interactive:** After X. **20 Share:** animated breathing pool.

#### RR08 — Wins unlock experiments

- **1 Family:** Post-Loss Response. **2 Name:** Win-funded audition. **3 Headline:** “New auditions appear disproportionately after wins.” **4 OOOH:** discovers when exploration happens; `(8,9,8,9,7,9,8,9) = 8.4`.
- **5 Elements:** Breadth. **6 Support:** first-observed/experimental picks after result vs opportunity baseline. **7 Raw:** H,O. **8 Algorithm:** matched transition hazard. **9 Normalization:** N-transition/N-time. **10 Sample:** ≥30 experiments, ≥80 prior-result opportunities. **11 Sessions:** ≥25. **12 Confidence:** interval and win/loss/neutral contrast.
- **13 Confounders:** patch release, event goals, first-observed not new. **14 Supported:** first-observed-in-window picks follow wins more often. **15 Forbidden:** winning creates confidence. **16 Evidence:** experiment-origin strip. **17 Value:** improves trial planning. **18 Recommendation:** schedule experiments independently of the previous result for five trials. **19 Interactive:** lifecycle origin filter. **20 Share:** “where experiments begin.”

#### RR09 — Losses trigger experiments

- **1 Family:** Post-Loss Response. **2 Name:** Loss-triggered expansion. **3 Headline:** “After longer loss runs, you move farther from the core—not closer.” **4 OOOH:** surprising counterexample to comfort narratives; `(9,9,7,9,7,9,9,9) = 8.4`.
- **5 Elements:** Breadth, Transfer. **6 Support:** distance/experimental probability rises with loss-run length. **7 Raw:** H,O + taxonomy. **8 Algorithm:** run-length transition gradient. **9 Normalization:** N-transition. **10 Sample:** ≥50 2+ loss opportunities. **11 Sessions:** ≥20. **12 Confidence:** monotone or threshold change, matched session position.
- **13 Confounders:** draft/bans, late-session pool, sparse streaks. **14 Supported:** observed picks move outward after loss runs. **15 Forbidden:** desperation, tilt, random picking. **16 Evidence:** loss-count→distance curve. **17 Value:** player-specific inverse rule. **18 Recommendation:** predeclare whether Game after two losses is core or experiment for five events. **19 Interactive:** After X slider. **20 Share:** outward-arrow card.

Specimen A is directionally compatible with RR09, not RR03: after exactly one loss the next pick is core in 63.0% of 192 opportunities and experimental in 7.3%; after 2+ losses those are 45.2% and 16.4% over 73 opportunities. The Wilson intervals are wide and these are not fully matched/FDR-controlled, so this is a **research lead**, not a publishable specimen claim.

#### RR10 — Same response after wins and losses

- **1 Family:** Post-Loss Response. **2 Name:** Result-invariant selection. **3 Headline:** “Your next hero choice barely reacts to the previous result.” **4 OOOH:** a legitimate null can be personally meaningful; `(6,8,9,8,5,7,7,8) = 7.35`.
- **5 Elements:** Breadth, Consistency. **6 Support:** hero repeat, job overlap, core distance all inside equivalence bands. **7 Raw:** H,O + taxonomy. **8 Algorithm:** multivariate transition equivalence. **9 Normalization:** N-transition. **10 Sample:** G-transition. **11 Sessions:** ≥30/state. **12 Confidence:** all predeclared behavioral ROPEs.
- **13 Confounders:** draft constraints can force invariance. **14 Supported:** measured selection responses are materially similar. **15 Forbidden:** emotionally unaffected. **16 Evidence:** overlapping After Win/Loss profiles. **17 Value:** prevents forced response stories. **18 Recommendation:** none unless player wants a deliberate rule. **19 Interactive:** toggle showing overlap. **20 Share:** low priority/null card.

#### RR11 — Streaks matter, single results do not

- **1 Family:** Post-Loss Response. **2 Name:** Streak threshold. **3 Headline:** “One result does not change you much. Runs of results do.” **4 OOOH:** summarizes a stable conditional rule; `(9,9,8,9,8,9,9,10) = 8.7`.
- **5 Elements:** Breadth, Toolkit, optional expression. **6 Support:** 0/1-result equivalence; 2+ behavior difference; win/loss symmetry or specified side. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** threshold/segmented transition model. **9 Normalization:** N-transition. **10 Sample:** ≥50 2+ opportunities/side. **11 Sessions:** ≥25. **12 Confidence:** threshold outperforms linear/one-result models out of sample.
- **13 Confounders:** session position and stopping. **14 Supported:** observed transition changes at streak state. **15 Forbidden:** emotion/momentum. **16 Evidence:** staircase with confidence bands. **17 Value:** memorable behavioral rule. **18 Recommendation:** log five threshold events with a predeclared response. **19 Interactive:** streak slider. **20 Share:** “streaks, not singles.”

#### RR12 — Personally strong loss response

- **1 Family:** Post-Loss Response. **2 Name:** Strong-loss runback. **3 Headline:** “When the result is a loss but your summary expression is strong, you respond differently.” **4 OOOH:** separates team result from personal scoreboard expression; `(8,9,7,9,8,8,8,10) = 8.2`.
- **5 Elements:** Involvement, Death Exposure, Finishing. **6 Support:** predeclared multivariate expression stratum and next-pick transition. **7 Raw:** H,O,E. **8 Algorithm:** cross-fitted expression residual → matched transition interaction. **9 Normalization:** N-expression/N-transition. **10 Sample:** ≥60 losses, ≥25 per stratum. **11 Sessions:** ≥20. **12 Confidence:** interaction; no same-row threshold leakage.
- **13 Confounders:** summary expression is incomplete; outcome/game state. **14 Supported:** observable response differs after specified scoreboard profiles. **15 Forbidden:** “you played well,” blame teammates, deserved win. **16 Evidence:** loss type→next choice. **17 Value:** richer than loss alone. **18 Recommendation:** use one observable postgame rule for five strong-expression losses. **19 Interactive:** loss-profile toggle. **20 Share:** limited/private by default.

#### RR13 — Recovery changes expression, not results

- **1 Family:** Post-Loss Response. **2 Name:** Expression reset. **3 Headline:** “After losses, your involvement/exposure returns toward baseline even when next-result odds do not move.” **4 OOOH:** reveals recovery as expression rather than win rate; `(8,8,8,9,7,7,8,10) = 8.0`.
- **5 Elements:** Involvement, Death Exposure, Transfer. **6 Support:** expression movement toward baseline; outcome equivalence. **7 Raw:** H,O,E. **8 Algorithm:** matched multivariate next-game contrast. **9 Normalization:** N-expression/N-transition. **10 Sample:** G-transition. **11 Sessions:** ≥25. **12 Confidence:** expression difference + result ROPE.
- **13 Confounders:** regression to mean, hero/function switch. **14 Supported:** summary rates normalize without observed result difference. **15 Forbidden:** recovered mentally. **16 Evidence:** baseline distance before/after. **17 Value:** safer recovery language. **18 Recommendation:** keep the response that stabilizes desired expression for five losses. **19 Interactive:** baseline-return animation. **20 Share:** summary reset card.

#### RR14 — Recovery without adjustment

- **1 Family:** Post-Loss Response. **2 Name:** No-switch recovery. **3 Headline:** “Your recoveries are strongest when the observable pick/function response barely changes.” **4 OOOH:** causal-looking chain handled honestly; `(9,9,7,9,9,9,9,10) = 8.7`.
- **5 Elements:** Transfer, Consistency. **6 Support:** low adjustment distance, next result/expression difference, matched controls. **7 Raw:** H,O,E + taxonomy. **8 Algorithm:** response-distance model with doubly robust sensitivity, still observational. **9 Normalization:** N-transition/N-expression. **10 Sample:** ≥100 loss transitions. **11 Sessions:** ≥35. **12 Confidence:** stable across propensity/matching choices and windows.
- **13 Confounders:** core hero strength and selection remain unmeasured. **14 Supported:** repeated association. **15 Forbidden:** no-switching causes recovery. **16 Evidence:** chain plus alternatives panel. **17 Value:** elite recommendation scaffold. **18 Recommendation:** five losses with preselected no-switch response; verify expression/result descriptively. **19 Interactive:** chain explorer. **20 Share:** chain with “observed, not causal” footer.

### Combat Expression candidates (CE01–CE10)

#### CE01 — Involvement holds, exposure moves

- **1 Family:** Combat Expression. **2 Name:** Stable presence, changing exposure. **3 Headline:** “Your involvement stays remarkably stable across contexts; death exposure does not.” **4 OOOH:** identifies the precise changing axis; `(8,9,8,9,8,8,8,10) = 8.4`.
- **5 Elements:** Involvement, Death Exposure, Consistency. **6 Support:** activity equivalence plus exposure heterogeneity by hero/function/core. **7 Raw:** H,E + taxonomy. **8 Algorithm:** hierarchical mean/variance decomposition. **9 Normalization:** N-expression. **10 Sample:** ≥150, ≥3 supported contexts. **11 Sessions:** ≥20/context collectively. **12 Confidence:** activity ROPE + exposure interaction.
- **13 Confounders:** function/game state/lane. **14 Supported:** adjusted rates have different conditional stability. **15 Forbidden:** positioning or death quality. **16 Evidence:** two aligned context plots. **17 Value:** “not inconsistent overall” specificity. **18 Recommendation:** five games in the high-exposure context, track exposure. **19 Interactive:** context selector. **20 Share:** stable-line/bending-line card.

#### CE02 — Exposure holds, involvement moves

- **1 Family:** Combat Expression. **2 Name:** Stable exposure, changing involvement. **3 Headline:** “Your death exposure barely changes; involvement is the context-sensitive part.” **4 OOOH:** inverse localization; `(7,8,8,9,8,7,8,9) = 7.85`.
- **5 Elements:** Involvement, Death Exposure, Consistency. **6 Support:** exposure equivalence, activity heterogeneity. **7 Raw:** H,E + taxonomy. **8 Algorithm:** same decomposition. **9 Normalization:** N-expression. **10 Sample:** ≥150. **11 Sessions:** ≥20/context. **12 Confidence:** component contract.
- **13 Confounders:** hero/function/event opportunity. **14 Supported:** specified adjusted rates differ in sensitivity. **15 Forbidden:** passivity/aggression. **16 Evidence:** exposure band + activity spread. **17 Value:** focused diagnosis. **18 Recommendation:** control function over five games and monitor activity residual. **19 Interactive:** Two Metrics. **20 Share:** modest.

#### CE03 — High involvement, low exposure

- **1 Family:** Combat Expression. **2 Name:** Economical summary presence. **3 Headline:** “High involvement and low death exposure repeatedly coexist in your history.” **4 OOOH:** positive relationship without claiming death value; `(7,9,8,8,7,8,7,8) = 7.85`.
- **5 Elements:** Involvement, Death Exposure. **6 Support:** joint calibrated zones, session stability, context residuals. **7 Raw:** E,H. **8 Algorithm:** bivariate zone/evidence-diversity test. **9 Normalization:** N-expression. **10 Sample:** ≥100. **11 Sessions:** ≥25. **12 Confidence:** both marginal zones and joint stability.
- **13 Confounders:** function, wins, low-event matches. **14 Supported:** two summary rates coexist. **15 Forbidden:** discipline, positioning, valuable deaths, impact. **16 Evidence:** joint quadrant + examples. **17 Value:** legible identity anchor. **18 Recommendation:** preserve this expression while testing one stretch hero. **19 Interactive:** expression plane. **20 Share:** quadrant card.

#### CE04 — High involvement, high exposure

- **1 Family:** Combat Expression. **2 Name:** High-event exposure. **3 Headline:** “Your most involved contexts also carry your highest death exposure.” **4 OOOH:** honest tradeoff without value judgment; `(6,9,8,8,8,7,6,8) = 7.60`.
- **5 Elements:** Involvement, Death Exposure. **6 Support:** positive within-player residual association localized by context. **7 Raw:** E,H + taxonomy. **8 Algorithm:** cluster-robust bivariate relation. **9 Normalization:** N-expression. **10 Sample:** ≥120. **11 Sessions:** ≥25. **12 Confidence:** stable association and context check.
- **13 Confounders:** losses, hero function, match pace. **14 Supported:** rates rise together observationally. **15 Forbidden:** deaths enable involvement or are worthwhile. **16 Evidence:** context-linked scatter bands. **17 Value:** clear five-game target. **18 Recommendation:** keep function constant and test a predeclared exposure ceiling. **19 Interactive:** expression plane. **20 Share:** private by default.

#### CE05 — Function explains expression

- **1 Family:** Combat Expression. **2 Name:** Function-shaped expression. **3 Headline:** “Your summary expression changes more with hero function than with hero name.” **4 OOOH:** identifies the level that matters; `(8,8,7,9,8,8,9,10) = 8.1`.
- **5 Elements:** Toolkit, Involvement, Death Exposure, Finishing. **6 Support:** variance attributed to function vs hero residual. **7 Raw:** H,E + taxonomy. **8 Algorithm:** crossed hierarchical variance decomposition. **9 Normalization:** N-expression. **10 Sample:** ≥250, ≥4 supported functions. **11 Sessions:** ≥20/function. **12 Confidence:** variance-share interval + taxonomy sensitivity.
- **13 Confounders:** actual role unknown, nested hero/function collinearity. **14 Supported:** mapped function groups explain more observed variation. **15 Forbidden:** function causes behavior. **16 Evidence:** variance attribution bars. **17 Value:** organizes pool learning. **18 Recommendation:** compare heroes within one function for five games. **19 Interactive:** hero/function toggle. **20 Share:** “job > name” card.

#### CE06 — One hero creates the exposure story

- **1 Family:** Combat Expression. **2 Name:** Localized exposure. **3 Headline:** “Your global death-exposure label is mostly one heavily played hero context.” **4 OOOH:** rescues user from an overgeneralized score; `(8,9,8,10,9,7,9,9) = 8.5`.
- **5 Elements:** Death Exposure, Consistency. **6 Support:** hero attribution, leave-one-hero-out Element zone shift. **7 Raw:** H,E. **8 Algorithm:** influence diagnostics on hierarchical estimator. **9 Normalization:** N-expression. **10 Sample:** dominant hero ≥30; rest ≥100. **11 Sessions:** ≥15 hero and ≥25 rest. **12 Confidence:** influence stable across windows.
- **13 Confounders:** hero is proxy for function/lane. **14 Supported:** one context contributes most adjusted estimate/variance. **15 Forbidden:** hero causes bad deaths. **16 Evidence:** score before/after with explicit counterfactual limitation. **17 Value:** prevents generic advice. **18 Recommendation:** inspect five games on that hero context. **19 Interactive:** remove-context lens. **20 Share:** low; diagnostic.

#### CE07 — Finishing is conditional

- **1 Family:** Combat Expression. **2 Name:** Conditional finishing. **3 Headline:** “Your finishing mix is not global; one function accounts for the shift.” **4 OOOH:** makes a secondary Element precise; `(7,8,8,9,7,7,8,9) = 7.75`.
- **5 Elements:** Finishing, Toolkit. **6 Support:** stabilized event share by function/hero and global equivalence elsewhere. **7 Raw:** H,E + taxonomy. **8 Algorithm:** beta-binomial hierarchical interaction. **9 Normalization:** N-expression. **10 Sample:** ≥300 K+A events/function and ≥20 matches. **11 Sessions:** ≥15/function. **12 Confidence:** posterior/practical interaction and leave-one-hero-out.
- **13 Confounders:** hero design, outcome state, low events. **14 Supported:** credited-kill share differs in specified context. **15 Forbidden:** kill securing, greed, execution quality. **16 Evidence:** event-weighted shares + denominators. **17 Value:** avoids global caricature. **18 Recommendation:** no generic behavior advice; use as Transfer evidence. **19 Interactive:** function filter. **20 Share:** secondary card.

#### CE08 — Same expression, different results

- **1 Family:** Combat Expression. **2 Name:** Result/expression contradiction. **3 Headline:** “Your results move across contexts; your summary combat expression barely does.” **4 OOOH:** excellent Deep handoff; `(9,9,8,9,9,9,9,10) = 8.9`.
- **5 Elements:** Involvement, Death Exposure, Consistency, Transfer. **6 Support:** outcome difference; activity/exposure equivalence. **7 Raw:** H,O,E. **8 Algorithm:** multivariate conditional contrast. **9 Normalization:** N-expression. **10 Sample:** ≥80/context. **11 Sessions:** ≥25/context. **12 Confidence:** outcome practical difference + expression ROPEs.
- **13 Confounders:** team/draft/opponents; summary misses decisions. **14 Supported:** recorded result differs without measured expression shift. **15 Forbidden:** bad luck or teammates caused it. **16 Evidence:** result bars above identical expression fingerprints. **17 Value:** tells Deep exactly where to inspect. **18 Recommendation:** five controlled-context games; verify same expression before seeking parsed explanation. **19 Interactive:** reveal contradiction. **20 Share:** premium split card.

#### CE09 — Different expression, same results

- **1 Family:** Combat Expression. **2 Name:** Multiple working modes. **3 Headline:** “Two contexts produce similar results through different summary expression.” **4 OOOH:** turns conditionality into strength; `(9,9,8,9,7,9,9,10) = 8.7`.
- **5 Elements:** Involvement, Death Exposure, Finishing, Consistency. **6 Support:** result equivalence plus coherent expression differences. **7 Raw:** H,O,E. **8 Algorithm:** conditional multivariate profile. **9 Normalization:** N-expression. **10 Sample:** ≥80/context. **11 Sessions:** ≥25/context. **12 Confidence:** result ROPE + expression differences.
- **13 Confounders:** function and game state. **14 Supported:** summary signatures differ while result rate is equivalent. **15 Forbidden:** two strategies or causal routes. **16 Evidence:** two fingerprints, one result band. **17 Value:** “Two Versions” story. **18 Recommendation:** choose context based on draft/pool needs, then verify over five games. **19 Interactive:** Two Versions. **20 Share:** dual-profile card.

#### CE10 — Experiments explain inconsistency

- **1 Family:** Combat Expression. **2 Name:** Localized inconsistency. **3 Headline:** “You are not inconsistent everywhere; most summary variance lives in experiments.” **4 OOOH:** specific, compassionate, actionable; `(9,10,8,10,9,9,9,10) = 9.1`.
- **5 Elements:** Consistency, Transfer, Breadth. **6 Support:** core repeatability, edge variance ratio, variance attribution. **7 Raw:** H,O,E. **8 Algorithm:** hierarchical mean/variance decomposition by distance. **9 Normalization:** N-expression. **10 Sample:** G-transfer. **11 Sessions:** ≥30/band. **12 Confidence:** stable variance attribution and core equivalence.
- **13 Confounders:** experiments have sparse heterogeneous heroes. **14 Supported:** observed variability is concentrated by portfolio tier. **15 Forbidden:** experimental decisions are bad or player is inconsistent. **16 Evidence:** total variance partition. **17 Value:** replaces global label with leverage point. **18 Recommendation:** run experiments in fixed five-game blocks. **19 Interactive:** variance decomposition. **20 Share:** “not everywhere—here.”

### Session Drift candidates (SD01–SD12)

#### SD01 — Game 1 effect

- **1 Family:** Session Drift. **2 Name:** Opening-game signature. **3 Headline:** “Game 1 is the outlier; the rest of your session settles into a different range.” **4 OOOH:** detects warm-up/opener shape without naming cause; `(8,9,7,9,8,8,8,9) = 8.2`.
- **5 Elements:** Involvement, Death Exposure, Consistency. **6 Support:** position-1 expression/result versus 2–3 and matched session length. **7 Raw:** H,O,E. **8 Algorithm:** within-session position model. **9 Normalization:** N-expression plus session/calendar fixed effects. **10 Sample:** G-session. **11 Sessions:** ≥40 qualifying. **12 Confidence:** cluster interval and session-length sensitivity.
- **13 Confounders:** selection into longer sessions, gap definition. **14 Supported:** first observed session game differs. **15 Forbidden:** needs warm-up or queue mindset. **16 Evidence:** G1→G2→G3 curve. **17 Value:** easy experiment. **18 Recommendation:** use a consistent opener for five sessions. **19 Interactive:** Session Curve. **20 Share:** opener card.

#### SD02 — Gradual fade

- **1 Family:** Session Drift. **2 Name:** Smooth session drift. **3 Headline:** “Your summary expression moves gradually as sessions lengthen.” **4 OOOH:** familiar but less unique; `(5,8,8,7,8,6,5,8) = 6.95`.
- **5 Elements:** Involvement/Death Exposure/Consistency. **6 Support:** monotone position slope, no better breakpoint. **7 Raw:** H,O,E. **8 Algorithm:** within-session spline/ordinal trend. **9 Normalization:** N-expression. **10 Sample:** G-session through G5+. **11 Sessions:** ≥30 with 4+. **12 Confidence:** monotone effect stable at session gaps 60/90/120.
- **13 Confounders:** long-session selection, time of day unknown. **14 Supported:** observed position trend. **15 Forbidden:** fatigue, tilt, causal duration. **16 Evidence:** smooth curve. **17 Value:** session planning. **18 Recommendation:** compare capped versus usual sessions descriptively. **19 Interactive:** Session Curve. **20 Share:** secondary.

#### SD03 — Game-4 breakpoint

- **1 Family:** Session Drift. **2 Name:** Hard breakpoint. **3 Headline:** “Your sessions do not fade gradually. Game 4 is the breakpoint.” **4 OOOH:** extraordinary specificity; `(10,10,7,10,9,10,10,10) = 9.3`.
- **5 Elements:** Consistency plus changed expression/outcome component. **6 Support:** best predeclared/penalized position split, effect at 4+, no linear alternative. **7 Raw:** H,O,E. **8 Algorithm:** cluster-validated segmented position model. **9 Normalization:** N-expression. **10 Sample:** ≥80 G4+ observations. **11 Sessions:** ≥40 with 4+. **12 Confidence:** split selected in train, verified in held-out sessions; gap sensitivity.
- **13 Confounders:** players reaching Game 4 differ; clock time/party unavailable. **14 Supported:** an observed conditional break after session position. **15 Forbidden:** fatigue/tilt causes it. **16 Evidence:** curve with hard hinge and counts. **17 Value:** flagship experiment. **18 Recommendation:** stop at Game 3 for five eligible sessions; compare summary metrics. **19 Interactive:** breakpoint slider. **20 Share:** animated snap at G4.

#### SD04 — Late-session rise

- **1 Family:** Session Drift. **2 Name:** Late-session lift. **3 Headline:** “Your later session games move upward on the measured expression/result component.” **4 OOOH:** positive inverse, but selection risk; `(7,8,7,8,6,7,7,8) = 7.25`.
- **5 Elements:** specified Involvement/Exposure/Consistency. **6 Support:** late vs early effect and long-session matched analysis. **7 Raw:** H,O,E. **8 Algorithm:** within-session model with session-length stratification. **9 Normalization:** N-expression. **10 Sample:** G-session. **11 Sessions:** ≥30 long. **12 Confidence:** cluster effect; inverse-probability sensitivity.
- **13 Confounders:** only certain days/contexts become long. **14 Supported:** later observed positions differ. **15 Forbidden:** warms up, endurance skill. **16 Evidence:** position curve. **17 Value:** counters generic “stop early.” **18 Recommendation:** no cap; verify which component rises over five long sessions. **19 Interactive:** Session Curve. **20 Share:** rise card.

#### SD05 — Stable results, safer selection late

- **1 Family:** Session Drift. **2 Name:** Late pool contraction. **3 Headline:** “Your results stay stable, but hero choices move closer to the core late in sessions.” **4 OOOH:** sees behavior beneath stable outcome; `(9,9,8,10,8,9,9,10) = 8.9`.
- **5 Elements:** Breadth, Transfer, Consistency. **6 Support:** outcome equivalence, distance/core shift by position. **7 Raw:** H,O + taxonomy. **8 Algorithm:** within-session selection curve + result ROPE. **9 Normalization:** N-transition. **10 Sample:** G-session. **11 Sessions:** ≥30 long. **12 Confidence:** choice difference + result equivalence.
- **13 Confounders:** draft/bans, hero repetition. **14 Supported:** selections narrow while result stays similar. **15 Forbidden:** safer mental state or fatigue. **16 Evidence:** stable result line over contracting pool ring. **17 Value:** great conditional identity. **18 Recommendation:** decide whether the late core return is desirable over five long sessions. **19 Interactive:** Session Curve + pool ring. **20 Share:** “same results, smaller pool.”

#### SD06 — Late experiments

- **1 Family:** Session Drift. **2 Name:** Late-session expansion. **3 Headline:** “The longer a session runs, the farther your picks move from the core.” **4 OOOH:** identifiable selection rule; `(8,9,8,9,8,8,8,9) = 8.4`.
- **5 Elements:** Breadth, Transfer. **6 Support:** distance/experimental probability by position. **7 Raw:** H + taxonomy. **8 Algorithm:** within-session ordinal distance model. **9 Normalization:** N-transition. **10 Sample:** G-session. **11 Sessions:** ≥30 long. **12 Confidence:** monotone/breakpoint effect and long-session controls.
- **13 Confounders:** party/draft/time unknown. **14 Supported:** observed later picks are farther from core. **15 Forbidden:** boredom or tilt. **16 Evidence:** expanding pool by G1…G5+. **17 Value:** experiment timing insight. **18 Recommendation:** move experiments to a preselected session position for five sessions. **19 Interactive:** pool animation. **20 Share:** expansion strip.

#### SD07 — Repeat benefit peaks at Game 2

- **1 Family:** Session Drift. **2 Name:** Second-game peak. **3 Headline:** “Your second consecutive game on a hero is the strongest measured point; later repeats flatten.” **4 OOOH:** coach-like specificity; `(9,9,6,10,8,9,9,10) = 8.4`.
- **5 Elements:** Involvement, Death Exposure, Transfer. **6 Support:** repeat-position curve and nonrepeat matched baseline. **7 Raw:** H,O,E. **8 Algorithm:** run-position hierarchical curve. **9 Normalization:** N-expression/N-transition. **10 Sample:** ≥50 position-2, ≥30 position-3, ≥15 position-4+. **11 Sessions:** ≥25 runs. **12 Confidence:** peak vs plateau contrasts; hero mix controlled.
- **13 Confounders:** very rare long runs, selected heroes, draft. **14 Supported:** observed summary curve peaks at repeat 2. **15 Forbidden:** familiarity causes benefit or spamming is optimal. **16 Evidence:** repeat curve with opportunity counts. **17 Value:** precise spam experiment. **18 Recommendation:** two-game blocks for five hero runs. **19 Interactive:** Repeat Curve. **20 Share:** “Game 2 peak.”

#### SD08 — Three-game benefit, then flat

- **1 Family:** Session Drift. **2 Name:** Repeat frontier. **3 Headline:** “Repeating helps through three observed picks; beyond that the summary no longer moves.” **4 OOOH:** useful but difficult to support; `(8,9,6,9,8,8,8,9) = 7.95`.
- **5 Elements:** specified expression/Transfer. **6 Support:** monotone positions 1–3 and equivalence 3–5+. **7 Raw:** H,O,E. **8 Algorithm:** repeat-position segmented curve. **9 Normalization:** N-expression. **10 Sample:** ≥30 at each position through 5+. **11 Sessions:** ≥25 long runs. **12 Confidence:** difference then ROPE.
- **13 Confounders:** massive selection and sparse tail. **14 Supported:** measured curve shape. **15 Forbidden:** learning/diminishing returns causality. **16 Evidence:** curve + rarity warning. **17 Value:** spam cadence. **18 Recommendation:** use three-game blocks over five runs. **19 Interactive:** repeat slider. **20 Share:** curve card.

Specimen A cannot support SD07/SD08: 789 hero runs contribute a first position, only 49 reach position 2, three reach position 3, and one reaches 4+. This is exactly why opportunity gates belong in the candidate definition.

#### SD09 — Wins end sessions

- **1 Family:** Session Drift. **2 Name:** Win-stop pattern. **3 Headline:** “Wins end your observed sessions more often than losses do.” **4 OOOH:** highly recognizable stopping rule; `(9,9,8,9,7,10,9,9) = 8.70`.
- **5 Elements:** Consistency; optional result response. **6 Support:** bounded stop probability after win/loss, streak/session-position controls. **7 Raw:** H,O. **8 Algorithm:** discrete-time stopping hazard with censored boundaries. **9 Normalization:** N-transition. **10 Sample:** ≥100 completed opportunities/state. **11 Sessions:** ≥80 completed; boundary sessions excluded. **12 Confidence:** cluster/Wilson interval plus matched hazard.
- **13 Confounders:** 90-minute gap is operational; real-life schedule, time zone, queue time absent. **14 Supported:** no eligible match begins within boundary after wins more often. **15 Forbidden:** consciously stops satisfied. **16 Evidence:** stop rates + session-gap definition. **17 Value:** friend-level habit. **18 Recommendation:** observe five intended session endings; verify boundary. **19 Interactive:** session end markers. **20 Share:** stop-sign card.

Specimen A supplies a strong descriptive lead for SD09: among boundary-safe opportunities, observed stopping is 50.9% after wins (218/428; Wilson 95% 46.2–55.6) and 35.6% after losses (146/410; 31.1–40.4). Production still needs matched session-position/calendar controls before publication.

#### SD10 — Stop after getting one back

- **1 Family:** Session Drift. **2 Name:** Recovery stop. **3 Headline:** “You usually continue through losses and stop after the first recovery win.” **4 OOOH:** an animated, exact loop; `(10,10,7,10,8,10,10,10) = 9.20`.
- **5 Elements:** Consistency, Transfer. **6 Support:** continue after loss-run, stop after recovery win, motif lift vs transition baseline. **7 Raw:** H,O. **8 Algorithm:** censored sequence hazard/motif model. **9 Normalization:** N-transition. **10 Sample:** ≥50 loss→recovery events. **11 Sessions:** ≥30. **12 Confidence:** both links and motif lift stable across gap definitions.
- **13 Confounders:** clock/schedule; recovery win definition. **14 Supported:** operational session pattern recurs. **15 Forbidden:** emotional need to recover or satisfaction. **16 Evidence:** `L→continue→W→stop` with counts. **17 Value:** flagship loop. **18 Recommendation:** set a session cap independent of results for five sessions. **19 Interactive:** Behavioral Loop. **20 Share:** animated sequence.

#### SD11 — First loss ends the session

- **1 Family:** Session Drift. **2 Name:** Loss-stop boundary. **3 Headline:** “A first session loss is your strongest observed stopping signal.” **4 OOOH:** specific but schedule-confounded; `(8,9,7,9,7,8,8,8) = 8.0`.
- **5 Elements:** Consistency. **6 Support:** stop hazard after first loss vs matched first win/other positions. **7 Raw:** H,O. **8 Algorithm:** censored stopping model. **9 Normalization:** N-transition. **10 Sample:** ≥100 first-game outcomes. **11 Sessions:** ≥100 completed. **12 Confidence:** position interaction and gap sensitivity.
- **13 Confounders:** one-game planned sessions. **14 Supported:** observed boundary association. **15 Forbidden:** loss caused quitting. **16 Evidence:** Game1 result→stop bars. **17 Value:** calendar habit. **18 Recommendation:** predeclare session length for five starts. **19 Interactive:** boundary map. **20 Share:** moderate.

#### SD12 — Choices drift, expression does not

- **1 Family:** Session Drift. **2 Name:** Selection-only drift. **3 Headline:** “Your hero choices change across the session; measured combat expression stays stable.” **4 OOOH:** finds adaptation without a performance story; `(9,9,8,9,7,9,9,10) = 8.7`.
- **5 Elements:** Breadth, Toolkit, Involvement, Death Exposure. **6 Support:** hero/job/distance shift plus expression equivalence. **7 Raw:** H,E + taxonomy. **8 Algorithm:** joint within-session selection and expression model. **9 Normalization:** N-expression/N-transition. **10 Sample:** G-session. **11 Sessions:** ≥30 long. **12 Confidence:** selection difference + multivariate expression ROPE.
- **13 Confounders:** draft and unavailable lane context. **14 Supported:** observable selection changes without measured rate change. **15 Forbidden:** adapts successfully or strategy unchanged. **16 Evidence:** changing hero ribbon over fixed expression fingerprint. **17 Value:** premium conditional identity. **18 Recommendation:** no correction; verify whether the selected shift is intentional across five sessions. **19 Interactive:** Session Curve layered. **20 Share:** “choices moved / expression held.”

## 7.2 Ranking sanity check

The library contains **65 semantic candidates**: 17 Pool Shape, 12 Transfer, 14 Result Response, 10 Combat Expression, and 12 Session Drift. The OOOH range is intentionally broad (about 7.1–9.3), and high OOOH never bypasses evidence qualification. A 9.3 candidate with 12 opportunities abstains; a 7.5 candidate with overwhelming stable evidence may publish if it is the most truthful result.

---

# Part 8 — Top 20 “How did it know that?” Findings

These are product treatments for a Finding **after** qualification. Each preserves V6's Claim → Evidence → Interpretation → Recommendation contract, adds an alternative explanation, and gives the five-game experiment a verification metric.

## 8.1 PS15 — Names changed, jobs held

- **Claim:** Your hero names changed substantially; the taxonomy job mixture barely moved.
- **Evidence:** era hero JSD; job JSD/equivalence; 2–3 hero share crossovers. **Interpretation:** the roster evolved around a durable selection thread. **Alternatives:** taxonomy may be too coarse; patches/draft access can rotate names.
- **Recommendation:** choose the next experiment for a job currently underrepresented, not another substitute for the dominant jobs. **Verify after five:** job-distance added and whether annual/recent Toolkit moves. **Interaction/share:** eras scrubber and fixed-job/rotating-hero card. **Deep question:** do those new names actually perform the same jobs in parsed fights and item/skill choices?

## 8.2 PS17 — A year in chapters

- **Claim:** The history supports two or three durable selection chapters rather than one stationary year.
- **Evidence:** penalized change points; minimum matches/sessions per era; the largest hero/job/expression changes. **Interpretation:** the annual score is an average of observable versions. **Alternatives:** patch/meta or schedule shifts may explain the boundary.
- **Recommendation:** explicitly select which era's core is the current foundation. **Verify after five:** recent picks' distance to each era profile. **Interaction/share:** swipeable Identity Eras; three-panel chapter strip. **Deep question:** what draft, lane, and in-game choices distinguish the chapters?

## 8.3 PS10 — Game-3 adoption gate

- **Claim:** First-observed heroes often disappear early; those reaching Game 3 have a much higher later-return rate.
- **Evidence:** candidate funnel; conditional retention after 1/2/3; independent-session returns. **Interpretation:** the history contains a repeatable audition threshold. **Alternatives:** pre-window familiarity and hero availability can shape it.
- **Recommendation:** give the next eligible experiment three games before evaluation. **Verify after five:** expression stability and return decision, not only wins. **Interaction/share:** hero lifecycle funnel; “Game 3 decides” card. **Deep question:** what inside the first three games predicts retention?

## 8.4 PS06 — Names wide, jobs narrow

- **Claim:** Many selected heroes map back to a compact set of taxonomy jobs.
- **Evidence:** effective heroes; effective jobs; tail-to-core job JSD/functional overlap. **Interpretation:** exploration changes surface choices more than the strategic capability mix visible to Free.
- **Alternatives:** taxonomy does not observe actual match role; broad tags may compress genuine differences. **Recommendation:** test a taxonomy-distant hero while holding known context constant. **Verify after five:** job-distance and expression, not success alone. **Interaction/share:** contradiction reveal. **Deep question:** do parsed actions make those heroes more different than the taxonomy suggests?

## 8.5 TR03 — Results travel farther than expression

- **Claim:** Outcome remains within the equivalence band farther from core than involvement/exposure does.
- **Evidence:** result frontier; first expression component to break; opportunity/session counts. **Interpretation:** unfamiliar selections can keep producing similar results through a different summary signature. **Alternatives:** function, draft, and opponents differ.
- **Recommendation:** play five stretch games at the boundary in one function. **Verify after five:** the breaking expression metric and result, reported separately. **Interaction/share:** layered Core Boundary. **Deep question:** which decisions inside the game produce the expression shift?

## 8.6 TR08 — One-function bottleneck

- **Claim:** One supported function accounts for most of the off-core difference.
- **Evidence:** global transfer gap; function attribution; gap after excluding that function. **Interpretation:** the transfer problem is localized rather than global. **Alternatives:** one hero, lane, or draft pattern may be masquerading as function.
- **Recommendation:** play five function-matched adjacent heroes or temporarily narrow that branch. **Verify after five:** outcome/activity/exposure relative to core-function baseline. **Interaction/share:** tap-to-remove bottleneck. **Deep question:** what deaths, farming paths, fights, or objective choices differ there?

## 8.7 TR09 — Names travel, jobs do not

- **Claim:** Hero-name distance is tolerated when taxonomy-job distance remains small.
- **Evidence:** two-dimensional distance surface; near-job/far-name equivalence; far-job break. **Interpretation:** the reliable frontier follows jobs more than names. **Alternatives:** taxonomy and actual role may disagree.
- **Recommendation:** expand one name step at a time inside a supported job, then cross one job boundary deliberately. **Verify after five:** frontier component closest to its boundary. **Interaction/share:** 2D frontier map. **Deep question:** which inside-game responsibilities stop transferring across the job boundary?

## 8.8 TR11 — Experiments create variance, not weakness

- **Claim:** Experimental-edge means remain close to core while their distributions are wider.
- **Evidence:** outcome/expression equivalence; variance ratio; variance contribution. **Interpretation:** the edge is less predictable, not uniformly worse. **Alternatives:** it pools heterogeneous sparse heroes.
- **Recommendation:** test experiments in fixed five-game blocks. **Verify after five:** dispersion and center separately. **Interaction/share:** same-center/different-band view. **Deep question:** which within-match event types create the wider spread?

## 8.9 RR02 — Unwritten two-loss switch

- **Claim:** Selection is stable after one loss and changes sharply after the second consecutive loss.
- **Evidence:** switch rates at 0/1/2/3; breakpoint effect; comparable win-streak negative control. **Interpretation:** the observed history behaves as if it has a threshold. **Alternatives:** bans, draft, session position, and sparse streaks.
- **Recommendation:** predeclare the response after two losses for five qualifying events. **Verify after five:** switch distance, next expression, next result—separately. **Interaction/share:** After X step animation. **Deep question:** what inside games differs before and after that threshold?

## 8.10 RR03 — Two losses → core → stabilization

- **Claim:** Two-loss states precede inward pool movement, which precedes expression/outcome closer to baseline.
- **Evidence:** both conditional links and complete-chain support/lift. **Interpretation:** a recurring observable recovery route. **Alternatives:** regression to mean and stronger core selection; no causal conclusion.
- **Recommendation:** use a preselected core option for five two-loss events. **Verify after five:** distance, expression-baseline distance, result. **Interaction/share:** animated three-node chain with counts. **Deep question:** what actual decisions stabilize on the core pick?

## 8.11 RR04 — Switch names, keep jobs

- **Claim:** Post-loss hero switches retain much more taxonomy overlap than the changed names imply.
- **Evidence:** hero-switch rate; any-job overlap; matched post-win comparison. **Interpretation:** the adjustment often stays inside a familiar capability family. **Alternatives:** taxonomy is broad and cannot observe match role.
- **Recommendation:** on five losses, record whether the desired adjustment is a name or a job change. **Verify after five:** taxonomy distance and expression movement. **Interaction/share:** hero swap over fixed job icons. **Deep question:** does the parsed play pattern really remain similar?

## 8.12 RR07 — Wins expand, losses contract

- **Claim:** Next-pick distance moves outward after wins and inward after losses.
- **Evidence:** matched distance deltas; experimental/core probabilities; session-position controls. **Interpretation:** results organize when the player explores versus returns inward. **Alternatives:** draft availability and streak position.
- **Recommendation:** decouple one experiment and one core return from prior result over five opportunities. **Verify after five:** choice distance and expression. **Interaction/share:** breathing pool toggle. **Deep question:** how do draft and actual role choices differ in the expanded state?

## 8.13 RR11 — Streaks, not singles

- **Claim:** One-result states are equivalent; 2+ result runs cross a behavioral threshold.
- **Evidence:** state profile at 0/1/2+; threshold model; held-out stability. **Interpretation:** repeated results, not isolated ones, organize the observable response. **Alternatives:** session length/stopping and fewer long-run opportunities.
- **Recommendation:** predefine the threshold response for five runs. **Verify after five:** selection/function/expression deltas. **Interaction/share:** streak slider and threshold card. **Deep question:** do parsed choices change at the same threshold?

## 8.14 RR14 — Recovery without adjustment

- **Claim:** Near-zero observable pick/function change is associated with the strongest recovery profile.
- **Evidence:** response-distance curve; matched outcome/expression; robustness alternatives. **Interpretation:** the player's history does not require a visible selection change for recovery. **Alternatives:** stronger heroes are more likely to be retained; selection is unmeasured.
- **Recommendation:** five loss responses with a preselected same/adjacent choice. **Verify after five:** summary expression before result. **Interaction/share:** observational chain with alternatives drawer. **Deep question:** what does remain constant inside those games?

## 8.15 CE08 — Same expression, different results

- **Claim:** Result rates differ by context while adjusted involvement and exposure remain equivalent.
- **Evidence:** result effect; two expression ROPEs; context/session support. **Interpretation:** the summary endpoint locates a result gap it cannot explain. **Alternatives:** teams, opponents, draft, objectives, and decisions are absent.
- **Recommendation:** repeat five context-matched games and confirm the contradiction. **Verify after five:** result and expression separately. **Interaction/share:** result reveal over identical fingerprints. **Deep question:** exactly which parsed decisions/events distinguish the contexts?

## 8.16 CE10 — Not inconsistent everywhere

- **Claim:** Most observed expression variance is concentrated in the experimental edge.
- **Evidence:** core/edge variance; attribution share; stable core center. **Interpretation:** global Consistency hides a localized source. **Alternatives:** sparse edge heroes are heterogeneous by construction.
- **Recommendation:** evaluate one experiment as a five-game block. **Verify after five:** edge variance and mean. **Interaction/share:** variance decomposition. **Deep question:** which repeatable inside-game events create experiment variance?

## 8.17 SD03 — Game-4 breakpoint

- **Claim:** A segmented session model identifies Game 4 as the first stable break; a gradual trend fits worse.
- **Evidence:** G1–G5+ curve; held-out breakpoint; counts/sessions. **Interpretation:** later-session change is abrupt in this history. **Alternatives:** only certain days/parties/drafts reach Game 4.
- **Recommendation:** stop at Game 3 for five otherwise-eligible sessions. **Verify after five:** the component that broke, with no causal verdict. **Interaction/share:** curve snapping at G4. **Deep question:** what changes inside Games 4+?

## 8.18 SD09 — Wins end sessions more often

- **Claim:** The operational stop hazard is higher after wins than losses.
- **Evidence:** bounded rates/intervals; matched session position; 60/90/120-minute sensitivity. **Interpretation:** results are associated with where observed sessions end. **Alternatives:** planned session length, clock time, and real-life schedule are absent.
- **Recommendation:** mark five intended endings to validate the 90-minute proxy. **Verify after five:** intended versus inferred end and prior result. **Interaction/share:** session ribbon with win stop markers. **Deep question:** none initially; first validate the boundary.

## 8.19 SD10 — Stop after getting one back

- **Claim:** The recurring bounded motif is loss continuation followed by a recovery win and session end.
- **Evidence:** link hazards; motif support/lift; stability across sessions/gap definitions. **Interpretation:** an operational “get one back, then end” loop appears in history. **Alternatives:** clock/schedule and chance sequence overlap.
- **Recommendation:** set a result-independent cap for five sessions. **Verify after five:** intended endpoints and session expression. **Interaction/share:** animated loop. **Deep question:** if long sessions remain, what inside later games changes?

## 8.20 SD12 — Choices drift, expression holds

- **Claim:** Hero/job selection moves across session position while adjusted activity/exposure stay equivalent.
- **Evidence:** distance or distribution change; expression ROPEs; long-session controls. **Interpretation:** selection evolves without a detectable summary-expression shift. **Alternatives:** draft and actual lane context are missing.
- **Recommendation:** make the late selection rule explicit for five sessions. **Verify after five:** selection distance and expression. **Interaction/share:** moving hero ribbon over fixed fingerprint. **Deep question:** do parsed responsibilities stay as stable as the summary rates?

---

# Part 9 — Top 10 flagship Free experiences

| Rank | Experience | Why it defines the ceiling | Minimum truthful fallback |
|---:|---|---|---|
| 1 | **Identity Eras: a year in chapters** (PS17) | Makes chronology the product; deeply personal and shareable. | “No stable chapter boundary detected” and show a stable-year summary. |
| 2 | **Names changed, jobs held** (PS15) | A precise contradiction no normal hero-count page shows. | Show hero/job divergence descriptively without a headline. |
| 3 | **The Game-4 breakpoint** (SD03) | Coach-like specificity plus a clean five-session experiment. | Show the session curve and abstain on a breakpoint. |
| 4 | **Your most common Dota loop** (SD10 or a qualified motif) | Turns rows into an animated recurring history. | Say no loop dominates; never publish a three-occurrence curiosity. |
| 5 | **The two-loss rule / inverse rule** (RR02 or RR09) | Observed threshold behavior is instantly recognizable. | Show state counts only; the specimen demonstrates the inverse may occur. |
| 6 | **Results travel farther than expression** (TR03) | Sophisticated yet intuitive Transfer decomposition. | Publish a binary core/stretch component contrast. |
| 7 | **One-function transfer bottleneck** (TR08) | Converts a generic weakness into an exact learning target. | State that no supported function dominates the gap. |
| 8 | **Wins expand; losses contract** (RR07) | Symmetric interactive reveal, excellent stack-share object. | Render Win/Loss profiles only when both states clear gates. |
| 9 | **Not inconsistent everywhere** (CE10) | Replaces a vague trait label with the source of variance. | Keep only the public Consistency Element. |
| 10 | **Choices drift; expression holds** (SD12) | Shows conditional identity without a dashboard or causal claim. | Show either selection or expression curve, not the contradiction. |

Implementation complexity does not determine this ranking. These define the experience ceiling; the rollout priority later is stricter.

---

# Part 10 — Behavioral loops and rules

## 10.1 Representation

Encode every eligible match as a small, observable state, for example:

```text
result: W | L
portfolio: C(core) | R(reliable stretch) | E(experimental edge)
repeat: same hero | job overlap | switch
session: G1 | G2 | G3 | G4 | G5+
expression: adjusted low | typical | high  (cross-fitted, predeclared)
```

Mine length-2 to length-5 motifs **inside sessions** first. For each candidate store support, distinct sessions, player transition-baseline probability, lift, bootstrap interval, first/second-half stability, and opportunities. Generate candidates on a discovery split; qualify only the frozen motifs on a holdout split. This avoids reporting the most colorful path found among thousands.

## 10.2 Rule candidates and publication gates

| Observable rule | Test | Gate beyond common contract | Safe wording |
|---|---|---|---|
| one loss → repeat hero | repeat contrast vs matched win/neutral | ≥60 one-loss opportunities | “After one loss, you repeat more often.” |
| 2+ losses → switch | segmented switch probability | ≥40 2+ opportunities and threshold replication | “The second loss is where observed selection changes.” |
| 2+ losses → core | distance/core transition | ≥30 inward movements | “Loss runs precede inward movement.” |
| 2+ losses → experiment | inverse distance transition | same | “Loss runs precede outward movement.” |
| wins → exploration | next-pick distance/adoption hazard | ≥30 experiments | “Experiments appear more often after wins.” |
| result streak → behavior threshold | threshold vs linear/flat model | ≥50 opportunities beyond threshold | “Runs, not single results, separate the profiles.” |
| Game 4+ → core/edge | session-position distance model | ≥40 long sessions | “Later positions move toward/away from core.” |
| strong-expression loss → repeat/switch | cross-fitted interaction | ≥25 per expression stratum | “The response differs after this summary profile.” |
| first result → stop | censored stopping hazard | ≥100 completed sessions | “Observed sessions end more often after X.” |
| loss run → recovery win → stop | motif lift and link hazards | ≥30 complete motifs, ≥20 sessions | “This sequence recurs above your transition baseline.” |

## 10.3 Loop qualification

A publishable “YOUR MOST COMMON DOTA LOOP” must satisfy all of:

1. at least 30 non-overlapping occurrences in at least 20 sessions;
2. lower 95% cluster-bootstrap bound for lift >1.25 versus the player's own first-order transition baseline;
3. no one hero supplies >40% of occurrences unless the headline names that hero context;
4. same directional lift in both chronological halves;
5. survives a stricter 60/90/120-minute session-boundary sensitivity;
6. family qualifies under hierarchical FDR;
7. no shorter submotif explains all of the lift;
8. copy describes recurrence, never intent or causality.

## 10.4 Specimen result: sequencing is viable; no flagship loop yet

Specimen A provides 476 within-session transitions. The most frequent three-state motif, `win-core → win-core → win-core`, appears only 11 times; the next appears nine times. Those counts fail the flagship gate. The honest output is **no dominant multi-match loop detected**, even though transition/state analysis is viable.

The useful real lead is stopping: 364 completed boundary-safe sessions show a substantially higher raw stop rate after wins than losses. The other lead is an inverse two-loss pattern described under RR09. Neither should be promoted until the full matched, family-controlled model qualifies it.

---

# Part 11 — Player eras and evolution

## 11.1 Is change-point identity viable?

Yes—as a selectively published Pool Shape outcome, not a segmentation forced onto every player. Hero selection is multinomial, taxonomy jobs are fractional-compositional, and expression features are continuous. A production detector should combine compatible objectives rather than apply one mean-shift test to all of them.

PELT provides an efficient penalized framework with exact optimization under its conditions ([Killick, Fearnhead, and Eckley, 2012](https://arxiv.org/abs/1101.1438)); multinomial sequence methods provide a closer reference for categorical distributions ([De and Mukhopadhyay, 2013](https://www.sciencedirect.com/science/article/pii/S0047259X13000353)). Neither is permission to accept an in-sample maximum split.

## 11.2 Recommended era detector

1. **Session blocks:** order eligible matches, cluster at 90 minutes, and never split inside a session.
2. **Features:** hero composition, fractional job composition, Breadth/Toolkit, and optional adjusted expression centers/variances. Do not use result as the primary era boundary; it is too noisy and evaluative.
3. **Cost:** multinomial/compositional likelihood for hero/job features plus robust Gaussian/Student cost for expression; standardize each family and cap dominance.
4. **Penalty:** calibrate on stationary simulated and held-out real histories to control false era rate. Use PELT or segment neighborhood; maximum three eras in Free.
5. **Minimum era:** 120 eligible matches, 45 independent sessions, and 45 observed days; no chapter shorter than 10% of the usable span.
6. **Discovery/verification:** propose boundaries on one session subset and verify adjacent-segment divergence/effect on the other, or use nested bootstrap selection correction.
7. **Robustness:** boundary within ±14 days across bootstrap; same substantive change at 60/90/120-minute sessions; leave-one-hero-out; taxonomy perturbation.
8. **Patch sensitivity:** because the one-call payload lacks reliable patch coverage, disclose that meta/patch may explain a boundary. Never write “patch X changed you.” A future static calendar may be used only as an explanatory overlay, not proof.
9. **Null outcome:** “stable year” is a valid positive finding. Do not create chapters to fill a carousel.

## 11.3 Era semantics

After a boundary qualifies, attribute what moved:

| Hero distribution | Job distribution | Expression | Safe semantic outcome |
|---|---|---|---|
| changes | equivalent | stable | names changed, underlying job mixture held |
| equivalent | changes | stable | surrounding toolkit migrated; avoid claiming within-hero role change |
| changes | changes | stable | portfolio identity moved; summary expression held |
| changes | equivalent | changes | new names accompanied an expression shift, not necessarily caused it |
| stable | stable | changes | same pool, different observed expression chapter |
| stable | stable | stable | no era; abstain |

## 11.4 Specimen feasibility result

The local exploratory detector searched session boundaries with at least 120 matches per side and compared the maximum split with 500 session-block randomizations:

- hero distribution: split at **2026-02-01**, after match 335/session 143; raw JSD `0.1922`, balance-weighted score `0.1842`, exploratory randomization `p=0.001996`;
- job distribution: split at **2026-04-18**, after match 523/session 238; raw JSD `0.01466`, score `0.01380`, exploratory `p=0.003992`;
- adjacent chronological thirds: hero JSD `0.2146` then `0.1590`, versus job JSD only `0.0097` then `0.0142`;
- effective heroes by third: `20.11 → 23.94 → 20.11`; effective jobs: `12.84 → 12.42 → 12.20`.

This supports feasibility and a strong **relative** observation: hero names moved much more than mapped job mixture. It does **not** yet license “you became a different player on February 1” because the boundary was chosen in-sample, the payload lacks patch context, and taxonomy does not observe actual role. The intriguing six-to-eleven-week lag between the hero and job candidate splits should be a registered hypothesis, not retrospective copy.

The reproducible local outputs are in [`analysis-summary.json`](opendota-free-v6.1-specimen/analysis-summary.json); [`analyze_specimen.py`](opendota-free-v6.1-specimen/analyze_specimen.py) performs no network I/O.

---

# Part 12 — Recommended V6.1 analytical model

## 12.1 Architecture

```text
ONE SAVED SUMMARY-HISTORY PAYLOAD
│
├─ immutable validation, eligibility, coverage, dedupe
├─ chronology + 90-minute sessions + censored boundaries
└─ static, versioned hero taxonomy
        ↓
ATOMIC FEATURES
rates · outcomes · hero/job mass · opportunities
        ↓
CONTEXT MODELS
cross-fitted hero/function/duration residuals
coverage-aware fallback; no rank/MMR
        ↓
HIDDEN FEATURE GRAPH
portfolio shape · continuous distance · lifecycle
transitions · streaks · repetition · stopping
variance decomposition · rolling distributions · eras
        ↓
7 PUBLIC ELEMENTS (unchanged count)
Breadth · Toolkit · Involvement · Finishing
Death Exposure · Transfer · Consistency
        ↓
CONDITIONAL + LONGITUDINAL RELATIONSHIPS
equivalence/difference · threshold · breakpoint
contradiction · chain · motif · change point
        ↓
5 FAMILY OMNIBUS TESTS (unchanged keys)
Pool Shape · Transfer · Post-Loss Response
Combat Expression · Session Drift
        ↓
HIERARCHICAL FDR + EFFECT + STABILITY + COPY ENTITLEMENT
        ↓
0–3 SEMANTIC FINDINGS
claim · evidence · interpretation · alternatives
recommendation · five-game verification
        ↓
DYNAMIC IDENTITY
stable primary line + optional twist + hero/pool anchor
        ↓
INTERACTIVE STORY + DEEP DIAGNOSTIC HANDOFF
```

## 12.2 Element estimator changes

| Element | V6.1 change |
|---|---|
| Breadth | Keep estimator; add a versioned shape object and uncertainty/stability, not a composite. |
| Toolkit | Replace established-hero label counting with match-weighted fractional job entropy; propagate taxonomy sensitivity. |
| Involvement | Cross-fitted hierarchical residual with nonlinear duration and covered hero/function context. Do not rename it participation. |
| Finishing | Stabilized beta-binomial/event-weighted share with event-opportunity gate; keep as modifier. |
| Death Exposure | Overdispersed count/rate model with duration exposure and robust context residual. |
| Transfer | Continuous familiarity×function-distance curves and practical-equivalence frontier; preserve component subtypes. |
| Consistency | Internally separate shrunk outcome and expression repeatability; decompose variance sources before synthesizing publicly. |

## 12.3 Finding registry changes

Retain the five family keys and add structured semantic outcome records:

```text
FindingCandidate
  family_key
  hypothesis_branch          # shape, lifecycle, frontier, transition, etc.
  semantic_outcome_key       # names_changed_jobs_held, two_loss_switch, ...
  evidence_groups[]          # independent required groups
  opportunity_contract       # rows, transitions, sessions, heroes, eras
  estimator_version
  normalization_version
  practical_effect_boundary
  confidence_interval
  p_value / q_value / equivalence_status
  robustness_checks[]
  supported_claim_tokens[]
  forbidden_claim_tokens[]
  confounder_tokens[]
  recommendation_key
  verification_metric_keys[]
  interaction_key
  share_key
```

Candidate generation can be broad; the registry and testing tree must be finite for each release. New copy variants that change the claim require a new semantic outcome key, not an untested string template.

## 12.4 Qualification and selection

1. Calculate availability/opportunity gates before effects.
2. Use cross-fitting wherever the same data defines a core/context/threshold and evaluates its contrast.
3. Test five family-level global hypotheses; apply BH across the five.
4. Only inside qualified families, test frozen branches/outcomes with hierarchical FDR.
5. Require practical effect or practical equivalence, session independence, temporal stability, and robustness checks.
6. Rank qualified outcomes on evidence strength × OOOH × evidence diversity; p-values never act as editorial scores.
7. Conflict rules: at most one outcome/family; no mutually exclusive claims; a chain suppresses its weaker component claims; a specific localized Finding suppresses the generic Element restatement.
8. Publish 0–3. The empty state still shows Elements and honest evidence.

## 12.5 Dynamic identity composition

Dynamic identity should use three typed slots:

```text
PRIMARY — stable annual identity evidence
TWIST   — one compatible contradiction, condition, or longitudinal change
ANCHOR  — supported hero/pool/function evidence
```

- **Primary eligibility:** annual Element or family outcome stable across at least two chronological thirds; not a post-result or late-session state by itself.
- **Twist eligibility:** qualified Finding from a different family or a longitudinal branch; may contradict the primary in a clearly scoped context.
- **Anchor eligibility:** established/stable hero or top job with adequate taxonomy coverage; no recommendation masquerading as identity.
- **Compatibility:** registry matrix for semantic redundancy, contradiction, temporal tense, and copy grammar. Prefer a meaningful twist over a second generic compliment.
- **Stability language:** “This year…” for annual evidence; “Recently…” for recent state; “In longer sessions…” for conditional evidence. Never flatten them into one timeless label.

Example:

> **The Function-First Explorer**  
> Many hero names, a remarkably stable catch-and-sustain thread.  
> **The twist:** your recent reliable frontier is wider than it was early this year.

This remains dynamic evidence composition, not a return to Archetypes.

## 12.6 Five-game commitment model

Every actionable Finding should emit:

```text
eligibility event      what counts as one of the five
controlled context    what to hold approximately constant
primary metric        the one expected to be informative
guardrail metric      a second metric that prevents tunnel vision
baseline              the Finding's original supported comparison
follow-up wording     “Here is what changed,” never “this fixed you”
```

Five games are a product experiment, not adequate proof of causality. Use shrinkage, show uncertainty, and allow “too early to tell.”

---

# Part 13 — Interactive report opportunities

| Interaction | Best Findings | Core behavior | Guardrail |
|---|---|---|---|
| **Pool Evolution Scrubber** | PS14–PS17, TR10 | scrub time; hero shares, jobs, core boundary, expression update together | display era confidence bands and minimum segment; no fake continuous precision |
| **Identity Eras** | PS17, PS15/16 | swipe between 2–3 chapters, each with only decisive changes | “possible patch/meta context” alternatives drawer |
| **Core Boundary** | TR01–TR10 | move from core→reliable stretch→experimental edge; show three component curves | disabled/hatched unsupported distance bands |
| **After X** | RR01–RR13 | toggle Win / 1 Loss / 2+ Losses / Win streak; pool and response update | always show opportunity/session counts; withhold thin states |
| **Session Curve** | SD01–SD06, SD12 | G1→G5+ selection/result/expression layers | selection into long sessions warning; no fatigue label |
| **Behavioral Loop** | SD10/qualified motifs | animate sequence with support and baseline lift | never animate a loop below occurrence/session gate |
| **Two Versions of You** | TR02–TR04, CE08–CE10 | core vs stretch or context A/B fingerprints | precise scope labels; no personality modes |
| **Contradiction Reveal** | PS06/07/15/16, CE08/09 | first show intuitive surface, then underlying opposite/constant | both halves must independently qualify |
| **Hero Lifecycle** | PS09–PS13 | NEW/observed trial→tested→retained→dormant→returned | say “first observed in window,” not Discover, unless lifetime history exists |
| **Variance Decomposition** | CE06/10, TR11/12 | tap sources to see contribution to Consistency | no causal or blame language |
| **Five-Game Commitment** | actionable top findings | eligibility counter, context reminder, primary+guardrail metric | follow-up is descriptive and can abstain |

The report should remain a story, not a dashboard. Each interaction exists to reveal one relationship: change over time, distance from core, conditional response, or source of variance.

---

# Part 14 — Deep diagnostic opportunities

Free identifies **where the history changes**. Parsed Deep asks what actually happens there.

| Free Finding | What Free genuinely knows | High-value parsed-data question |
|---|---|---|
| names changed, jobs held | selected hero taxonomy mixture stayed close | Do item/skill builds, map regions, fight entry, and objective participation also show the same jobs? |
| identity era boundary | selection/expression distribution changed around a period | Which patches, lane assignments, allies, drafts, and in-game actions distinguish the eras? |
| one-function transfer bottleneck | summary transfer gap localizes to a mapped job family | Are deaths, farm timing, spell usage, fight entry, lane outcomes, or objective sequences different there? |
| results travel, expression changes | outcome equivalent; activity/exposure does not | Which decisions allow similar results under a different expression profile? |
| expression travels, results do not | summary rates equivalent; outcomes differ | Are draft quality, lane matchups, objectives, item timings, or fight conversion different? |
| off-core exposure rises | adjusted death rate changes by distance | Where, when, and in what game states do those deaths occur; what precedes them? |
| one hero creates global exposure | influence localizes to hero context | Are deaths clustered before items, around objectives, during saves/initiations, or after lost fights? |
| one/two-loss selection rule | choice transition changes after result state | Does warding, farming, lane choice, build, or fight behavior also change, and at what point? |
| behavior changes without recovery | selection/expression response shifts; next result equivalent | Is the adjustment solving one inside-game problem while introducing another? |
| recoveries with no visible change | pick/function stays near; summary recovery stronger | Which within-game behaviors stay constant or normalize despite the same hero/function? |
| Game-4 breakpoint | a summary/result component breaks by session position | Do reaction proxies, deaths by phase, farming routes, spell use, objectives, or decision timing change? |
| choices narrow late, results stable | pool distance falls; result equivalent | Are late-session drafts more familiar, or does actual execution differ despite stable results? |
| stop after recovery win | bounded sequence recurs | First validate actual intended stopping; then inspect whether long loss-run games have distinct in-game patterns. |
| experiments explain variance | edge variance exceeds core | Which experimental heroes/events contribute, and is variance lane-, build-, phase-, or fight-specific? |
| same expression, different results | Free metrics are equivalent across result contexts | What unmeasured objectives, net-worth conversion, draft, lane, or team-fight features explain the gap? |

Deep should receive the Finding's exact match/session IDs, context definition, comparison groups, estimator version, and unanswered alternatives. That turns Free into a diagnostic router instead of a teaser.

---

# Part 15 — What I would actually change

## 15.1 Discovery comparison against V6

| Discovery | Already V6? | Partially V6? | New | Value |
|---|:---:|:---:|:---:|---|
| seven-element public ontology | ✓ |  |  | high; keep simple |
| effective hero/job diversity | ✓ | Toolkit weighting needs repair |  | high |
| cluster bootstrap, FDR, abstention | ✓ | hierarchical branches needed |  | foundational |
| portfolio head/core/tail/redundancy |  | ✓ |  | high explanatory depth |
| continuous core distance/frontier |  | binary core/stretch | ✓ | flagship Transfer improvement |
| result-vs-expression Transfer subtypes |  | component signals exist | ✓ | very high |
| lifecycle retention/adoption/rediscovery |  | exploration exists | ✓ | high, boundary-sensitive |
| name-versus-job migration |  | pool evolution exists | ✓ | flagship |
| robust identity eras |  | coarse timeline exists | ✓ | flagship/research-heavy |
| win response and streak thresholds |  | post-loss only | ✓ | high |
| hero/job repetition curves |  |  | ✓ | medium; often sparse |
| sequence motifs/behavioral loops |  |  | ✓ | high ceiling, strict gates |
| session breakpoint |  | early/late drift | ✓ | high |
| session stopping with censoring |  | session end implied | ✓ | high but boundary-sensitive |
| conditional variance localization |  | global Consistency | ✓ | very high |
| primary identity + scoped twist |  | dynamic identity exists | ✓ | high UX gain |
| five-game verification metric | recommendation skeleton | ✓ |  | high |
| rank/MMR, local time, item-build identity | forbidden/ignored |  |  | reject |

## 15.2 Keep exactly as V6

- Exactly seven public Elements and five stable family keys.
- 365-day Free boundary and one cheap source payload.
- Maximum three published Findings with family diversity.
- Cluster-aware uncertainty, 95% intervals, practical effects, FDR, and abstention.
- Claim → Evidence → Interpretation → Recommendation and machine-reviewable safe copy.
- No aggression, personality, intent, positioning, death quality, skill/MMR, or causal claims.
- Free locates the pattern; Deep explains inside-game mechanisms.

## 15.3 Improve before implementation

**P0 — data contract and parity**

1. Make one canonical projection shared by runtime, corpus collection, fixtures, and documentation. Assert runtime/calibration field parity and coverage behavior.
2. Decide whether production economics require one unpaginated physical request; current client pagination violates that constraint. Save/normalize once and analyze locally.
3. Treat lane/version/party as coverage-gated optional inputs. At this specimen's coverage, force fallback and prohibit their public use.
4. Preserve the raw payload hash, request manifest, provider/schema version, and eligibility audit in reproducibility metadata.

**P0 — estimator correctness**

5. Fix Toolkit to match-weighted fractional job mass with taxonomy sensitivity.
6. Stabilize Finishing by events and partial pooling; add a total-event opportunity gate.
7. Replace binary-only Transfer with continuous distance while keeping a simple UI boundary; cross-fit core/distance definitions.
8. Split outcome and expression repeatability inside Consistency; use hierarchical information weighting instead of equal tiny-session weight.
9. Revisit Session Drift's qualifying-session denominator; gate on direct position opportunities and independent long sessions, not the fraction of every one-game session.
10. Replace greedy reusable post-loss controls with explicit matched/weighted opportunities, no uncontrolled reuse, and streak-state separation.

## 15.4 Add to V6

**P1 — high-value hidden graph**

1. Portfolio-shape object: Shannon/Simpson, top shares, stable core, reliable stretch, experimental tail, redundancy, single-point jobs.
2. Conditional variance decomposition and result/expression Transfer subtypes.
3. Bidirectional result response: wins, exactly one loss, 2+ streaks, selection distance, function overlap, continuation/stopping.
4. Nonlinear session curve/breakpoint candidates and selection-only drift.
5. Semantic outcome registry with opportunity contracts, copy entitlement, alternatives, five-game verification, and interaction/share keys.
6. Dynamic identity `PRIMARY + TWIST + ANCHOR` compatibility/stability model.
7. Deep handoff contract containing exact qualifying cohorts and unanswered diagnostic questions.

**P2 — high-ceiling expansions after P1 calibration**

8. Left-truncation-aware hero lifecycle outcomes.
9. Robust name-versus-job migration and at most three identity eras.
10. Frozen sequence/rule candidate library with discovery/holdout motif qualification.

## 15.5 Research experimentally

- Calibrate continuous portfolio distance and practical-equivalence bands on the existing deidentified corpus; compare binary V6 against frontier V6.1 on held-out stability and user recognition.
- Estimate false era and boundary-location rates on stationary simulations and held-out histories before any era copy ships.
- Validate hero taxonomy tags/weights with Dota experts, track version/facet uncertainty, and measure whether job contradictions survive plausible mappings.
- Test whether GPM/XPM, damage, healing, LH, and tower residuals add incremental Finding reliability after hero/function/outcome context. They should remain hidden even if useful.
- Validate 60/90/120-minute session gaps against consenting users' intended sessions. Stopping Findings should wait for acceptable proxy accuracy.
- Run blinded expert/user evaluations: recognition, overclaim perception, usefulness, and whether alternatives are understood. Compare against V6, not raw analytics pages.
- Pre-register candidate families/branches and evaluate realized false-discovery/abstention rates, not only engagement.

## 15.6 Reject

- New public Elements for Exploration, Eras, Repetition, Stopping, Resilience, Pace, Farm, Damage, or “Aggression.” They are conditional, longitudinal, or confounded.
- A sixth `Behavioral Rules` or `Eras` family before nonredundancy evidence; use semantic forms under existing families.
- Team kill participation from one player's K+A; local-time identities from UTC plus server cluster; patch stories from `version`; lane Findings at ~2.5% coverage.
- Rank/MMR/`average_rank` conditioning, even though the specimen returns it completely.
- Final-item “build style” inference without purchase timing/versioned semantics.
- Generic causal recommendations (“stop after Game 3 and you will win more”) or psychological labels (“tilts after two losses”).
- Any system that must publish a Finding. Truthful abstention is a feature.

## 15.7 Rollout order and stop conditions

| Priority | Work | Ship gate | Stop/reject condition |
|---|---|---|---|
| P0 | request/runtime/calibration parity; estimator repairs | deterministic fixtures, corpus parity, no coverage leakage | cannot reproduce same normalized history from same payload |
| P1 | portfolio shape, Transfer subtypes, conditional variance, richer result/session states | held-out stability + controlled false discovery + safe copy audit | semantic candidates mostly restate Elements |
| P1 UX | Core Boundary, After X, Two Versions, five-game verification | comprehension and no-causal-misread tests | dashboard burden exceeds recognition gain |
| P2 | lifecycle and eras | simulated false-era target, boundary robustness, left/right censor gates | false chapters or “new hero” mislabeling remain common |
| P2 | loops/rules | discovery/holdout lift, ≥30 occurrences/20 sessions | most players yield only low-support motifs |
| P3 research | extra scoreboard residuals/facets/items | incremental reliability and copy safety | adds metrics but not distinct user truths |

## 15.8 Final challenge answered

This proposal does not primarily invent more meters. Its core outputs are relationships:

- the same Breadth can hide different heads and tails;
- hero names and job mixtures can move at different speeds;
- outcome, involvement, and exposure can stop transferring at different distances;
- one loss and two losses can lead to different next choices;
- selection can move while expression holds;
- variance can be local rather than global;
- an annual average can contain several durable chapters;
- a session ending can complete a recurring sequence.

Consequently, two players with nearly identical seven-Element scores can receive dramatically different Findings because one has a stable redundant core and result-invariant choices, while the other has two functional islands, a streak threshold, an exposure-only frontier, and a Game-4 selection break.

That is the right ceiling for Free DNA: one cheap request that feels implausibly observant because it treats every match as one step in a history—while being unusually explicit about what the history cannot know.
