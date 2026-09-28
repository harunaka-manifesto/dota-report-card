# Role Mastery context parameter feasibility — 2026-09-27

**Decision: keep public Role Mastery gated pending parameter approval.** Eight-week population acquisition and opponent coverage succeeded. Retained ten-player data measures all 16 metrics, but its tracked-account sampling frame and the unresolved calibration choices do not yet support an owner-approved context parameter artifact. Missing hero-specific levels use a zero adjustment; they do not block the artifact. This study publishes no parameter set or awards.

## Owner review guide

This is the document to review for the **evidence and calibration direction**. The owner has chosen local data first and the existing `Above` threshold. The [reuse audit below](#retained-corpus-reuse-audit--2026-09-28) gives all 16 measured scales and their sample counts. The [slope check](#slope-check) explains the remaining matchup-adjustment choice.

**Owner direction, 2026-09-28:** use retained local matches for the first candidate and check it against held-aside local matches. Make new provider calls only if that check shows a gap. This chooses the next data source; it does not approve parameter values or public enablement.

**Owner direction, 2026-09-28:** keep the existing V1 `Above` threshold (`tau = 0.35`) for the first candidate. The local history check below puts this near one in three eligible comparisons. This approves the threshold choice, not the other parameters or public enablement.

**Owner direction, 2026-09-28:** keep the earlier Carry/Mid/Offlane matchup multipliers, **0.748 / 0.778 / 0.722**, for the first release. The local estimates remain a validation check; they are not applied at runtime. The history replay found that swapping the multipliers changed 14 of 17,565 checked `Above` results. The gold-unit conversions, floor tolerances and drift limit remain separate choices.

**Owner direction, 2026-09-28:** use the 16 metric spread values measured from the 757 retained ten-player matches for the first-release candidate. The two retained samples differ by at most 11.7% on these measurements. Both were selected through tracked accounts, so this approves a practical V1 source, not a claim that the sample represents every player.

**Owner decision, 2026-09-28 — no lane-opponent adjustment.** The lane/opponent term is removed from every expectation for every role (foundation §10). This retires the gold-conversion question: the three provisional lane scales below (48.63 / 53.08 / 45.31) are **historical evidence only** and have no place in any artifact. Carry Last Hits @10 and Offlane Net Worth @10 move to class B (own-hero term); the two lane net-worth advantage metrics become class B\* (viewer-minus-counterpart hero term in gold, no lane term). The matchup multipliers and opponent effects now feed only the display-only matchup badge, so they no longer change any `Above` result or XP; the "14 of 17,565" comparison below is historical. A lane-model coverage or drift failure withholds only the badge. The parameter schema is now `tracker-context-parameters-v3` with no `lane_scale`; the private v2 draft must be rebuilt without it.

**This is not a final parameter artifact to approve.** The selected threshold, matchup multipliers (badge only) and metric scales still need to be combined with decisions on near-floor tolerance and the badge's maximum slope drift in a versioned artifact. No approval of public mastery is requested from this study alone. Once those choices are documented with validation results, that artifact is the final sign-off item.

## Acquisition and provenance

- The pre-existing private STRATZ corpus had tracked-player histories and deep responses, but no retained `heroStats.stats` or `heroStats.laneOutcome` population aggregate for the required window.
- With owner authorization, the offline collector requested eight full STRATZ weeks, **2026-07-30 through 2026-09-24 UTC** (weeks 2952–2959): 10- and 20-minute `stats` for five positions and opponent `laneOutcome` for 127 heroes in each core position. Requests used the tracker `ControlledTransport` and `ProviderGate` against local PostgreSQL/Redis. The local audit records **160 collection plus 8 exploratory STRATZ calls, all HTTP 200, no recorded failures**. OpenDota calls: **0**. No production service or flag changed.
- The 160 aggregate responses and SHA-256 manifest are retained only at `.local/tracker-context-calibration-2026-09-27/` in the primary checkout. Manifest SHA-256: `d0fdef3c96fb7ca3b23867c9c8bd132cddf35ba75c94079d1f23cda9caf4ff0f`. No player identifiers or raw responses are committed.
- STRATZ accepts a Unix timestamp for the `week` input and returns the week number in each row. The `laneOutcome.position` response reported `POSITION_1` even when a P2/P3 filter materially changed cohort counts. The requested filter was retained as the cohort key; every row's week and own hero ID was checked. Sampled summed pair counts were about twice `stats` match counts at P1/P3 and equal at P2, consistent with 2v2 and 1v1 lanes. The response-position discrepancy needs a provider regression check before publication.

## Population and independent coverage

| Measure | Result |
|---|---:|
| Hero-position checkpoint cells | 635/635 (127 heroes × 5 positions) |
| Hero-position cells meeting the ≥300-match gate | 635/635 |
| Weekly opponent pair rows | 367,587 |
| Eight-week pooled opponent pairs | 47,894 |
| Opponent effects after 3,000/20/500-match gates | 127/127 in each of P1, P2 and P3 |
| Independent recent Standard drafts with valid core lane shape | 4,937 |
| Drafts with all lane opponents covered | Carry 1,657/1,657; Mid 2,060/2,060; Offlane 1,220/1,220 |

The independent drafts came from the private V7 tracked-player replay corpus, not the STRATZ aggregate pool. Observed 100% coverage clears the 97% gate **for this sample**; the sample is concentrated in tracked accounts, so it is not proof of launch-cohort representativeness.

## Slope check

The engineering reference slopes are Carry **0.748**, Mid **0.778**, Offlane **0.722**. A direct regression of raw CS on the opponent score confounds player and hero mix. This diagnostic instead uses each player's 20 prior same-role Standard matches (at least five), subtracts median CS and the own-hero population-level change, then regresses that residual on the current opponent score minus its prior median. It mirrors the runtime window-relative adjustment, but does **not** replace the independent per-opponent partial-effect regression used to lock the reference slopes. The repository has no owner-approved maximum drift bound.

| Role | Recent observations | Estimated slope | Approximate 95% interval | Full retained-year slope (observations) |
|---|---:|---:|---:|---:|
| Carry | 1,627 | 0.813 | 0.629–0.997 | 0.838 (7,141) |
| Mid | 1,977 | 0.768 | 0.640–0.896 | 0.851 (7,923) |
| Offlane | 1,197 | 0.990 | 0.781–1.199 | 0.767 (5,649) |

Intervals use an independent-observation standard error and do not account for repeated accounts; they are not a release gate. Recent Offlane is materially above the frozen reference while full-year Offlane is closer. The owner chose to retain the earlier multipliers; the regression method and acceptable drift still need approval before artifact validation. More aggregate calls cannot settle that choice.

## Metric parameter gap

The builder requires finite `sigma_pop`, `tau`, `floor` and `floor_tolerance` for **all 16 active** tracker metrics (four per role). Running the tracker's normalization, replay and metric functions on 7,435 recent Standard viewer rows yielded usable *provisional* distributions for 12 active metrics. Four lacked a usable scale in that one-viewer corpus:

| Metric | Valid measurements | Main reason |
|---|---:|---|
| `mid.early_fight_presence.v1` | 0/2,048 | Other players' event streams absent |
| `mid.lane_net_worth_advantage_at_10.v1` | 0/2,048 | Opposing player's checkpoint absent |
| `offlane.lane_net_worth_advantage_at_10.v1` | 0/1,277 | Opposing player's checkpoint absent |
| `offlane.objective_involvement.v1` | 0/1,277 | Tower-damage report absent |

The private parsed OpenDota corpus has 960 Standard matches with ten players. Under the tracker's existing evidence translation, tested lane net-worth comparisons still yielded zero valid measurements. The 12 provisional distributions come from a tracked-player cohort, not an approved population sample. STRATZ `stats` supplies useful checkpoint means for active metrics. The acquired aggregate fields cannot establish damage-share and event hero levels. The four retired metrics are excluded from this release assessment.

The owner selected the existing V1 `tau = 0.35` default for the first candidate. Per-metric floor tolerances and representative population scales are still unapproved. Arbitrary positive placeholders for scored metrics would pass shape checks while changing `ABOVE`/`BELOW` states and mastery bonuses. Offlane Objective Involvement is diagnostic-only, but the current artifact contract still requires its parameter entry.

## Ten-player follow-up — 2026-09-28

With renewed owner authorization, one bounded probe and 60 fixed batches used the existing `GetTrackerMatchBatch` operation through `ControlledTransport` and `ProviderGate`. All **61 STRATZ calls returned HTTP 200** and were recorded in the local provider audit; **0 OpenDota calls** were made. The query returned all ten players' replay fields, including minute net worth, kill and assist events, and tower damage reports. The tracker's own translators and `measure` function produced valid values for all 16 active metrics in the seven-match probe, then in the wider sample below. No production acquisition or public flag changed.

The sampling frame was retained V7 deep matches from **2026-07-30 through 2026-09-03**, the five weeks present in that corpus. A fixed hash selected eight Standard matches from each of 60 accounts with at least eight eligible matches. Eight of the 480 requested match IDs appeared under more than one selected account, leaving **472 distinct matches** and **4,720 player-match observations**. The participant observations broaden coverage beyond the tracked viewers, but the match selection still inherits the tracked-account cohort. The local index, collection and assessment scripts, raw responses, assessment and SHA-256 manifest are private at `.local/tracker-context-calibration-2026-09-27/`; canonical manifest digest: `756a26a2f44b4d649a5a464bcf9fa9d46cd6da336abd5ebc3981fde7bfb4f09d`. No player or match identifiers are committed.

| Active metric | Valid / eligible | Pilot standard deviation | Holdout standard deviation |
|---|---:|---:|---:|
| Carry last hits at 10 | 944 / 944 | 12.770 | 14.610 |
| Carry net worth at 20 | 926 / 944 | 1,904.840 | 2,204.060 |
| Carry hero damage share | 944 / 944 | 0.0865 | 0.0877 |
| Carry tower damage share | 930 / 944 | 0.2513 | 0.2659 |
| Mid lane net-worth advantage at 10 | 944 / 944 | 1,242.873 | 1,506.226 |
| Mid early fight presence | 940 / 944 | 0.2141 | 0.2204 |
| Mid net worth at 20 | 926 / 944 | 1,930.223 | 2,119.380 |
| Mid tower damage share | 930 / 944 | 0.2393 | 0.2271 |
| Offlane lane net-worth advantage at 10 | 944 / 944 | 1,132.760 | 1,132.445 |
| Offlane net worth at 10 | 944 / 944 | 693.523 | 707.688 |
| Offlane fight presence | 944 / 944 | 0.1428 | 0.1513 |
| Offlane objective involvement | 911 / 944 | 0.2518 | 0.2692 |
| Support fight presence | 1,884 / 1,888 | 0.1501 | 0.1674 |
| Support observer wards placed | 1,888 / 1,888 | 1.0178 | 1.0563 |
| Support vision denial | 1,888 / 1,888 | 0.9813 | 1.0081 |
| Support camps stacked | 1,852 / 1,888 | 1.5480 | 1.2079 |

The holdout labels 12 of the 60 tracked accounts by an independent hash. Eight matches selected through more than one account were deduplicated before measurement, so this is a cohort check rather than a fully independent population holdout. Failed measurements stayed unavailable: short matches, zero team tower damage or tower deaths, and seven event-credit inconsistencies were not imputed as zero. The standard deviations above are **pilot estimates**, not approved `sigma_pop` values.

Four matching checkpoint fields in the sample exceed the same five-week `heroStats.stats` position-weighted population means: Carry CS@10 **44.36 vs 39.37** (+12.7%), Carry NW@20 **8,797.54 vs 8,307.10** (+5.9%), Mid NW@20 **8,394.43 vs 8,000.60** (+4.9%), and Offlane NW@10 **3,540.26 vs 3,171.02** (+11.6%). STRATZ's aggregate `cs` semantics are not fully documented. These mean differences flag a different cohort mix, but do not establish that its standard deviations are biased. Some account holdout dispersions also differ (Mid lane advantage 1,506 vs overall 1,243; Support stacks 1.208 vs overall 1.548), so the proposed population scales still need a documented sampling and validation decision. No share/event hero-position-metric cell reaches 300 observations in this sample. Under the runtime contract, such missing hero levels contribute **zero hero adjustment**; 300 is a threshold for using an optional adjustment, not for approving the artifact. More calls drawn from the same tracked-account frame would not resolve its representativeness.

The 61 calls close the *missing replay-field* question, but do not close the *parameter approval* question. No arbitrary `tau`, floor tolerance, population scale or slope drift bound was published. The owner-approved artifact gate remains closed.

## Retained-corpus reuse audit — 2026-09-28

The private `.local` corpus is substantial but has different evidence depths. The V7 deep corpus holds about **104,823 distinct matches** over a year; its tracked viewer has replay detail, while other participants generally have summary fields. The derived OpenDota history has **422,161 player rows**, but no ten-player replay. Private STRATZ probe caches include ten-player responses. Replaying recent Standard responses through the production tracker translators and `measure` function, and deduplicating against the 61-call sample, yields **757 distinct ten-player matches**: **1,514 observations per core role** and **3,028 support-position observations**. Every active metric has valid measurements, generally at least 1,450 core or 2,980 support values after evidence checks. These are provisional distributions from a tracked-account selection frame, not approved population scales. Private source files and identifiers remain uncommitted.

**Additional provider calls needed to construct an offline 16-metric candidate: 0.** Existing aggregate responses and retained ten-player matches cover the required fields. A separate, independently sampled population check could improve confidence; its call count depends on the sampling frame and is not a prerequisite imposed by the 300-match hero-level threshold. Additional calls against the same tracked-account frame would add volume without removing that selection concern.

The following are sample standard deviations of **valid comparison values**, deduplicated by match and participant. They are candidates for `sigma_pop`, not approved values. The count is smaller than the eligible count when the production metric correctly returns unavailable. Signed lane-advantage values retain their native gold units; shares and presence are fractions from 0 to 1.

| Metric | Valid observations | Provisional standard deviation |
|---|---:|---:|
| `carry.hero_damage_share.v1` | 1,514 | 0.0851 |
| `carry.last_hits_at_10.v1` | 1,514 | 12.4208 |
| `carry.net_worth_at_20.v1` | 1,492 | 1,854.5177 |
| `carry.tower_damage_share.v1` | 1,492 | 0.2528 |
| `mid.early_fight_presence.v1` | 1,508 | 0.2112 |
| `mid.lane_net_worth_advantage_at_10.v1` | 1,514 | 1,211.0468 |
| `mid.net_worth_at_20.v1` | 1,492 | 1,887.9295 |
| `mid.tower_damage_share.v1` | 1,492 | 0.2370 |
| `offlane.fight_presence.v1` | 1,512 | 0.1424 |
| `offlane.lane_net_worth_advantage_at_10.v1` | 1,514 | 1,119.9972 |
| `offlane.net_worth_at_10.v1` | 1,514 | 681.7232 |
| `offlane.objective_involvement.v1` | 1,452 | 0.2517 |
| `support.camps_stacked.v1` | 2,984 | 1.4943 |
| `support.fight_presence.v1` | 3,020 | 0.1468 |
| `support.observer_wards_placed.v1` | 3,028 | 1.0024 |
| `support.vision_denial.v1` | 3,028 | 0.9749 |

### Local checks before parameter selection

The older probe cache supplies 318 of the 757 distinct matches; the recent fixed sample supplies 439 more after deduplication. Calculating each metric's spread separately in those two caches gives differences of **0.7%–11.7%** across the 16 metrics. This is useful internal consistency evidence, but both caches were reached through tracked accounts and do not prove population representativeness.

A separate replay of 155 tracked accounts' recent histories tested the engineering default for `Above` against their prior same-role values. For the 12 scored metrics measurable from single-viewer history, about **33%–36%** of eligible comparisons were `Above` at the default `tau = 0.35`; a more permissive `0.25` yielded **38%–40%**, and a stricter `0.65` yielded **22%–26%**, by role. This check does not include hero or lane adjustments and cannot calculate three scored metrics needing other players' replay. It estimates the direction and magnitude of the choice; it is not a final bonus-award rate or parameter approval.

The offline slope validator initially compared only the current opponent lineup while runtime uses the change from the player's prior lineup mix. Its candidate input now carries that prior score. A separate unit check found that the resulting lane score is in last-hit units even for three gold-valued metrics. The context parameter schema then required a per-metric lane scale before such a score could adjust gold (superseded 2026-09-28: the lane term and its scale were removed). Direct ten-player checkpoint comparisons suggest provisional scales of **48.63 gold per unit of the last-hit matchup signal** for Mid lane net-worth advantage, **53.08** for Offlane lane net-worth advantage, and **45.31** for Offlane net worth at 10. These are measured associations across matches, **not fixed gold paid for a last hit**. Estimates from the older and newer caches differ by at most 5.3%; they remain candidate values, not approved parameters. The matchup badge retains its original last-hit score.

The match payload already supplies minute-by-minute net worth, and the tracker measures the Mid and Offlane gold metrics directly from it. That same match's realised net worth cannot set its pre-match expectation. STRATZ's retained `heroStats.stats` gives net-worth means by hero and position, while the retained opponent-conditioned `laneOutcome` rows expose `csCount` but no net-worth field. Two further audited STRATZ GraphQL schema reads (HTTP 200, no OpenDota calls) confirmed that `HeroLaneOutcomeType` has no net-worth field and `HeroStatsQuery.stats` has no opponent filter. These two aggregate paths therefore cannot directly supply opponent-conditioned net worth; other schema paths were not fully evaluated. A direct gold-based opponent adjustment would need an appropriate aggregate or enough **earlier** match net-worth examples for each opposing hero. The local tracked-viewer history offers an upper bound of 8,633 Mid and 6,458 Offlane usable lane/draft examples for this purpose; median examples per opposing hero are only 28 and 64 respectively. Even with a lenient 100-example minimum, the direct-match sample covers only 71% of recent Mid drafts and 59% of Offlane drafts, below the existing 97% opponent-coverage gate. The 757 complete ten-player matches are smaller still. This does not prove a direct-gold model impossible; it identifies a data and methodology change that must be settled before replacing the existing last-hit-based opponent model. Superseded 2026-09-28: the owner removed the lane-opponent adjustment instead, so neither a direct-gold opponent model nor an empirical scale is needed.

### Private parameter candidate — 2026-09-28

The reproducible private draft is `.local/tracker-context-calibration-2026-09-27/candidate-context-parameters-v2.json` (file SHA-256 `4e055570b98a351d859cdf1078d7c8a0ad904a5fa81a83379f1778afca43c75f`). Its private builder and source data remain alongside it; no raw identifiers are committed. It contains all 16 metric scales from the 757 ten-player matches, the owner-selected `Above` threshold of `0.35`, 889 checkpoint hero rows, 47,894 pooled opponent pairs, and three metric-specific gold conversions (obsolete since 2026-09-28; a v3 rebuild drops them). The slope check uses 20,713 longitudinal observations; a **separate 4,937-draft sample** checks opponent coverage. The artifact builder reports 100% coverage in that independent draft sample.

The draft applies the retained Carry/Mid/Offlane matchup multipliers **0.748 / 0.778 / 0.722** and records the local measurements **0.838 / 0.851 / 0.767** only as validation evidence. The draft uses an illustrative maximum drift of `0.10`, chosen after seeing the local data; this bound is **not owner-approved** and the builder's pass does not settle that decision. Near-floor tolerances are provisionally 5% of each adjusted metric's measured spread; signed lane-advantage metrics use a floor below the observed minimum. These are review proposals, not approved release values.

Replaying 155 tracked accounts with the earlier draft produced `Above` on **31.6%–35.4%** of eligible comparisons for the 12 scored metrics available in those histories. Comparing that draft's updated matchup multipliers with the earlier values changed the `Above` result in **14 of 17,565** checked comparisons. Three scored metrics need other players' replay and cannot enter this particular history check. The current draft uses the earlier multipliers, remains unregistered, and leaves public mastery at `CALIBRATION_PENDING`.

## Owner decision and next data work

Finalize the remaining parameter choices and versioned artifact: rebuild the private draft under schema v3 (no lane scale), floor tolerance, and — for the display-only badge only — the opponent check method and its maximum permitted drift from the retained matchup multipliers. The local metric scales, `Above` threshold and matchup multipliers are already selected for V1. Use available hero-specific levels only where their 300-match threshold is met; otherwise the runtime applies zero hero adjustment. Once the artifact is approved, register it and backfill mastery from retained data without provider calls. Public enablement and deployment still require an explicit owner request.
