# Vision Insight Enrichment Research — OUR_VISION_CLEARED

**Date:** 2026-09-16
**Scope:** Can the Tier A "Our Vision Cleared" candidate become worth a post-match card slot? Research only. No SSOT, UI, production code, or final copy.
**Inputs:** `post-match-intelligence-deep-research-v2.md`, `post-match-deterministic-candidate-validation-v1.md`, cached STRATZ payloads in `.local/stratz-probe/deep-research-2026-09-14/raw/`, and new analysis scripts in `vision-insight-research-code/`.

**Data used**

| Set | Size | Use |
|---|---|---|
| Historical corpus | 886 eligible matches; 18 feeding-guard matches excluded → 868 matches, 1,736 team perspectives (938 Standard, 798 Turbo) | Frequencies, base rates, examples |
| Playback truth set | 18 matches that have cached playback `wardEvents` and historical stats (9 Standard, 9 Turbo): 36 team perspectives, 630 observers placed, 182 cleared by the enemy | Exact ward lifecycles; validation of every historical method |
| New STRATZ calls | **2** (both playback probes on matches from 2026-09-14; both returned `playbackData: null`). Probe ledger now at 412 calls. The token was read from the environment and never printed. | Availability check |

Rendered sentences in this document are diagnostic renderings, not product copy.

---

## 1. Executive recommendation

**Is OUR_VISION_CLEARED worth keeping as Tier A?**
Only in an enriched form. The current rule fires for 10.1% (Standard) / 9.3% (Turbo) of team perspectives: "the enemy destroyed an unusually high share and rate of our observers". It answers "how many", which the owner correctly called "so what?".

**Is the raw deward count enough?** No.
- **The count mostly measures match length and support activity.** A 73-minute game produces "15 of 31 destroyed" without anything unusual happening.
- **It is loss-skewed:** 13.2% of losses vs 7.0% of wins in Standard.
- **It tells the player nothing about where or how fast.**

**Best enriched form.** Keep a single card, **VISION_CLEARED (enriched)**. It fires only when at least one concrete pattern exists.

1. **QUICK_CLEARS** — "your observers barely lasted".
   - Rule: at least 4 (Standard) / 3 (Turbo) of our observers were destroyed within 90 seconds of being placed, and they are at least 25% of all observers we placed.
   - Example: "8 of your 26 observers were destroyed within 90 seconds of being placed (5 within a minute)."
2. **VISION_SWEEP** — "one area was cleared in one go".
   - Rule: at least 3 of our observers in the same map region were destroyed within 5 minutes.
   - Evidence line: the enemy sentries placed there in that window.
   - Example: "Between 9:50 and 12:50 three of your observers in your half of the map were destroyed after 36–90 seconds; the enemy placed 4 sentries there in that window."

Either pattern fires for 14.2% (Standard) / 13.8% (Turbo) of team perspectives. That is about half of the current count-only fires (48% / 66%) plus 9% / 8% new perspectives.

**What historical stats support — a new finding.**
- **The old limitation looked hard.** Historical stats do not say which ward died, and the earlier "most recent alive ward" guess was right only 26% of the time.
- **Enemy sentry placements solve it.** They are historical, cover all ten players, and include exact coordinates. On the playback truth set, **95% of cleared observers had an enemy sentry placed within 640 units (10 cells) while they were alive, or up to 7 minutes before they were placed**, versus 3% of observers that expired naturally.
- **Reconstruction.** Match each deward to the alive observer that had an enemy sentry placed within 640 units in the preceding 90 seconds. This identifies **76% of dewards with 92% precision**, and **the region is correct 99% of the time** when a ward is identified. On the full corpus, 81% of dewards get identified.
- **Consequence:** ward lifetime, region and sweep facts become computable for old matches, with no playback.
- **Caveat:** the method was tuned on the same 18 matches it was scored on. It must be re-checked on fresh playback matches once playback returns.

**What playback adds.**
- Exact lifecycles for 100% of cleared wards instead of about 80%.
- The destroying player for each individual ward.
- Removes the 8% error rate of the reconstruction.

This is useful as an accuracy upgrade, but the card does not depend on it. Playback returned null for every match on 2026-09-15 and 2026-09-16.

**What we should definitely NOT claim.**
- Any visibility percentage ("you saw X% of the map", "reduced your vision to X%").
- "They could see you" / "you had no vision".
- That a deward caused deaths, lost fights, lost towers or net-worth swings.
- That a ward was badly placed.
- That a presence gap was caused by the enemy, when it was mostly caused by wards expiring.

---

## 2. STRATZ capability map

"Hist." means available for old matches; "Batch" means it can be fetched in multi-match batches.

| Field (schema path) | Example payload | Hist. | Batch | All 10 players | Std / Turbo | Playback needed | Semantic confidence | Validation evidence |
|---|---|---|---|---|---|---|---|---|
| `match.players.stats.wards {time, type, positionX, positionY}` | `{time: 526, type: 0, positionX: 114, positionY: 126}` | ✅ | ✅ (7 matches / request) | ✅ | ✅ / ✅ | — | **High.** `type 0` = Observer, `1` = Sentry. Coordinates are in 64-unit cells, range 62–194. | Per player, counts equal playback spawns 70/70 (earlier). Per team (this study): stats count equals playback observer spawns in 21/36; otherwise stats is 1–3 higher, never lower. |
| `match.players.stats.wardDestruction {time, isWard, gold, experience}` | `{time: 526, isWard: true, gold: 270, experience: null}` | ✅ | ✅ | ✅ (credited to the destroyer) | ✅ / ✅ | — | **High for time, destroyer and type. No link to which ward.** | `isWard` = Observer 112/114 (earlier). Per-team cleared count equals playback in 25/34; the rest are off by 1. **`gold` is not the ward's age:** a 5-second-old ward paid 122 gold, a 358-second-old one 293 (n=131). `experience` is null for Observers. |
| Sentry placements (same `wards` field, `type 1`) | `{time: 1041, type: 1, positionX: 98, positionY: 140}` | ✅ | ✅ | ✅ | ✅ / ✅ | — | **High** as placements | **New: the key to identifying cleared wards** (Section 3, candidate 3; Section 7) |
| `match.playbackData.wardEvents {indexId, time, positionX, positionY, fromPlayer, wardType, action, playerDestroyed}` | `{indexId: 925, time: -52, positionX: 114, positionY: 126, fromPlayer: 0, wardType: "OBSERVER", action: "SPAWN", playerDestroyed: null}` | ❌ (≤90 days, and currently null) | ❌ (1 match / request) | ✅ | ✅ / ✅ | **Yes** | **High:** exact spawn/despawn and destroyer | Natural Observer life 360 s. Cleared Observers: median life 98.5 s, 37% ≤ 60 s, 56% ≤ 120 s (n=182). |
| `match.towerDeaths {time, npcId, isRadiant}` | `{time: 1714, npcId: 23, isRadiant: false}` | ✅ | ✅ | — | ✅ / ✅ | — | **High** (`isRadiant` = owner) | Earlier phase |
| `players.stats.deathEvents {time, positionX, positionY, timeDead, …}` | `{time: 619, positionX: 104, positionY: 138, timeDead: 30}` | ✅ | ✅ | ✅ | ✅ / ✅ | — | **High** for time and position | Assist↔death reconciliation 99.2% (earlier) |
| `players.stats.deathEvents.isWardWalkThrough` | `true` | ✅ | ✅ | ✅ | ✅ / ✅ | — | **Low / undocumented** | Only 77% corroborated earlier. Not used. |
| `players.stats.killEvents.isSmoke` | `false` | ✅ | ✅ | ✅ | ✅ / ✅ | — | **Medium:** conservative | Precision 89%, recall 41% (earlier) |
| `players.stats.itemUsed` (Smoke of Deceit count) | `{itemId: 188, count: 6}` | ✅ | ✅ | ✅ | ✅ / ✅ | — | **High** as a count; **no times** | Counts equal playback (earlier) |
| `players.playbackData.itemUsedEvents` (Smoke times) | `{time: 1320, itemId: 188}` | ❌ | ❌ | ✅ | ✅ | **Yes** | **High** | Earlier phase |
| `players.stats.actionReport.scanUsed` | `2` | ✅ | 4 per request (reports op) | ✅ | ✅ | — | **Medium:** count only, **no time or position** | Chat-event scan comparison only partial (earlier) |
| `match.chatEvents` | ward-kill types 105/106 | ✅ | 4 per request | — | ✅ | — | **Unusable for wards** | STRATZ does not store ward-kill chat types (earlier) |
| `players.stats.locationReport` | `{positionX, positionY}` | ✅ | ✅ | ✅ | ✅ | — | **Unusable** | Rejected earlier. No new evidence to overturn. |
| `players.playbackData.csEvents.mapLocation` | `"DIRE_MID_LANE"` | ❌ | ❌ | ✅ | ✅ | **Yes** | **High** as STRATZ labels | **Used offline once** to build a fixed region grid from 23,521 labelled last hits (Section 3 notes). The runtime classifier needs no playback. |
| `MapLocationEnums` | RADIANT/DIRE BASE, SAFE/MID/OFF LANE, RIVER, ROSHAN, ROAMING, FOUNTAIN | — | — | — | — | — | Coarse; jungle is only "ROAMING" | Schema introspection |
| `players.playbackData.playerUpdatePositionEvents` | (not fetched) | ❌ | ❌ | ✅ | ? | **Yes** | **Unknown** | Present in the schema, untested because playback is null. Hero positions still would **not** give fog-of-war state. |
| `players.stats.farmDistributionReport` / runes / courier | — | ✅ | ✅ | ✅ | ✅ | — | Not relevant to vision | — |

**Map geometry (heuristic, validated coarsely).**
- **Distance:** 1 cell = 64 world units.
- **Radiant base** is bottom-left (label centroid 86, 85); **Dire base** is top-right (161, 159).
- **River:** RIVER and ROSHAN labels fit the diagonal x + y ≈ 252 cells. River band = |x + y − 252| ≤ 10.
- **Regions per team:** OWN_BASE, OWN_HALF, RIVER, ENEMY_HALF, ENEMY_BASE. Base cells use STRATZ base labels; the rest use the river diagonal.
- **Roshan pit:** one pit is labelled near (104, 141); the second pit is assumed at the mirrored position (152, 115). This is **not validated for the current patch**.
- **Observer mechanics:** Observer Ward ground vision is a 1600-unit radius (25 cells), and the ward lasts 6 minutes ([dotacoach 7.41e](https://dotacoach.gg/en/items/observer-ward); [Liquipedia](https://liquipedia.net/dota2/Observer_Ward) could not be fetched). Ground vision is blocked by trees and cliffs. Wiki text says the bounty grows with ward age ([Fandom](https://dota2.fandom.com/wiki/Observer_Ward)), but the STRATZ `gold` field does not reflect that.

---

## 3. Enrichment option menu

Frequencies are the share of team perspectives (Standard / Turbo), feeding-guard matches excluded, unless noted. Every rendering is a real payload.

### 1. VISION_CLEARED_COUNT (the current candidate) — REJECT as headline

| Aspect | Detail |
|---|---|
| Question | How many of our observers did they destroy? |
| Calculation | Placed ≥ 8, share destroyed ≥ p75, destroyed per 10 min ≥ p90 |
| Fields | `wards`, `wardDestruction` |
| Frequency | 10.1% / 9.3%. Wins 7.0% vs losses 13.2% (Standard). |
| Thresholds (p50 / p75 / p90) | Destroyed per team: Standard 5 / 7 / 9, Turbo 3 / 4 / 5. Share destroyed (placed ≥ 8): Standard 29% / 37% / 46%, Turbo 27% / 40% / 50%. |
| Reliability | High for counts; ±1 in about a quarter of teams |
| Usefulness / "so what?" | Low. The owner's reaction is typical: long games and active supports inflate the count. |
| Rendering | "Enemy destroyed 15 of your 31 observers" (Standard win, 73 min). The dewarder was their support (Nyx, 9 of 15). |
| Supported claim | Counts |
| Forbidden claim | "They controlled the map" |

**Verdict: REJECT as headline; keep as the context number inside the enriched card.**

### 2. QUICK_CLEARS (survival collapse) — KEEP

| Aspect | Detail |
|---|---|
| Question | Did our wards actually get to do anything, or were they found almost immediately? |
| Calculation | Our observers destroyed ≤ 90 s after placement. Needs identified dewards (historical reconstruction) or playback. |
| Fields | `wards` (ours and enemy sentries), `wardDestruction`; playback optional |
| Threshold | ≥ 4 (Standard) / ≥ 3 (Turbo) quick clears **and** ≥ 25% of placed observers |
| Frequency | 4.2% / 8.9%. With only "≥ 3 quick" it is 26.1% / 12.7% — too common. |
| Reliability | Counts are a **lower bound** (unidentified dewards are not counted). On 36 truth perspectives the estimate never overshoots by more than 1. |
| Player value | High. The warding player sees wards disappear but not how fast, and nobody else on the team sees it at all. "They were sweeping behind you" is a genuinely hidden fact. |
| "So what?" risk | Medium-low |
| Outcome skew | Mild: 3.4% of wins vs 4.9% of losses (Standard) |
| Duration bias | Fires more in the longer half of games (Standard 19.8% short vs 32.5% long at ≥ 3). The 25% share floor controls this. |
| Rendering | "8 of your 26 observers were destroyed within 90 seconds of being placed (5 within a minute); their Shadow Shaman destroyed 7 of 13." (Standard win, 59 min, match 8463940029) |
| Supported claim | Survival times |
| Forbidden claims | "They could see where you warded"; "your wards were placed in obvious spots" |

**Verdict: KEEP (headline component).**

### 3. VISION_SWEEP (region + burst + sentry evidence) — KEEP

| Aspect | Detail |
|---|---|
| Question | Did the enemy methodically clear one part of the map? |
| Calculation | Identified dewards grouped by region of the destroyed ward; ≥ 3 in one region within 300 s. Evidence line: enemy sentries placed in that region in [window start − 90 s, window end]. |
| Fields | `wards` (both teams, including sentries), `wardDestruction`, region grid |
| Frequency | 11.3% / 7.9% (≥ 4 in 5 min: 1.4% / 0.6%). Regions: Standard own half 57, their half 37, river 12. |
| Reliability | Region correct 99% of identified dewards; identity precision 92% |
| Player value | High. It turns a number into a place and a time the player can remember. |
| "So what?" risk | Low-medium |
| Guards needed | 15% (Standard) / 29% (Turbo) of sweeps end in the final 5 minutes (end-game high-ground pushes). 17% / 27% start while already ≥ 10k behind (restates a stomp). **Exclude both.** |
| Outcome skew | 8.5% of wins vs 14.1% of losses (Standard) |
| Rendering | "Between 9:50 and 12:50 three of your observers in your half of the map were destroyed after 90, 36 and 65 seconds; the enemy placed 4 sentries there in that window." (Turbo loss, 22 min, match 8983370743, lead −5.0k at 9:50) |
| Supported claim | Place, time, lifetimes, sentries placed |
| Forbidden claim | "They blinded your jungle so they could farm/gank there" |

**Verdict: KEEP (headline component).**

### 4. AGGRESSIVE_VISION_DENIED — ENRICHMENT ONLY

| Aspect | Detail |
|---|---|
| Question | Were our wards on their side of the map cleared? |
| Calculation | Our observers placed in ENEMY_HALF / ENEMY_BASE; share identified as destroyed |
| Threshold | ≥ 4 placed and ≥ 60% destroyed |
| Frequency | 3.4% / 3.4% |
| Truth set | Destroyed rate: enemy half 33% (71/217), river 29%, own half 24%, enemy base 50% (8/16; median life 113 s), own base 0/15. Share of lives ≤ 90 s: aggressive 17% vs own half 12%. |
| Reliability | Good |
| Player value | Medium. Mostly confirms what players expect ("deep wards die"). |
| "So what?" risk | Medium, and it reads as blame |
| Rendering | "5 of your 7 observers placed on their side of the map were destroyed." |
| Forbidden claim | "Your aggressive wards were a mistake" |

**Verdict: ENRICHMENT ONLY** (one clause inside VISION_SWEEP when the swept region is their half).

### 5. OBSERVER_MINUTES_REMOVED — SUPPORTING

| Aspect | Detail |
|---|---|
| Question | How much observer time did their dewarding take away? |
| Calculation | Σ over destroyed observers of (natural end − destruction time). Natural end = min(placement + 360 s, match end). |
| Truth set | Median 14.6 min removed (p90 37.4), which is 17% of our nominal observer time |
| Historical estimate | Identity-based, or bounded by alive-candidate ranges (truth inside [low, high] ±30 s for 32/34 perspectives; median interval width 12 min; midpoint error median 1.9 min) |
| Player value | Medium. More meaningful than a count ("they wiped out about 15 minutes of your ward time"), but abstract. |
| "So what?" risk | Medium |
| Supported claim | "Observer time", clearly labelled as ward time, not vision |
| Forbidden claim | Converting it into a map-visibility percentage |

**Verdict: SUPPORTING SLOT** (one number, rounded; playback or identified wards only).

### 6. VISION_UPTIME_GAP (our uptime vs theirs) — REJECT

| Aspect | Detail |
|---|---|
| Calculation | Actual observer-seconds ÷ nominal observer-seconds, ours vs theirs |
| Evidence | Uptime ratio p10 / p50 / p90 = 0.70 / 0.79 / 0.93. Correlation with plain "share destroyed" is −0.83, so it adds almost nothing. Our-minus-their gap p10 / p90 = −0.12 / +0.12. |
| "So what?" risk | High ("your wards were up 72% of the time") |

**Verdict: REJECT.**

### 7. VISION_COVERAGE_PERCENT — REJECT (see Section 4)

### 8. WARD_PRESENCE_GAP — REJECT for this card

| Aspect | Detail |
|---|---|
| Calculation | Stretches after 10:00 with zero own observers alive. Historically certain when no observer could still be alive (count bounds). |
| Truth set | 9 of 36 perspectives have a gap of ≥ 3 minutes. Of 14 gaps, **10 began with a natural expiry**, 3 with an enemy deward, 1 other. |
| Frequency | Certain gaps ≥ 4 minutes: 11% / 11% |
| Problem | It is mostly a "you stopped warding" fact, not an enemy action. That is blame risk, and the wrong family. |
| Example | Standard match 8965006124 (Radiant): no observer standing 20:30–25:30, although the team placed 30 and lost 12; the gap followed a natural expiry. |

**Verdict: REJECT** here. It could be reconsidered in a separate own-team-warding family.

### 9. DEWARD_BURST (time only, no location) — ENRICHMENT ONLY (fallback)

| Aspect | Detail |
|---|---|
| Calculation | Historical exact times: ≥ 3 enemy dewards within 120 s |
| Frequency | Standard 10.2% (≥ 4 within 180 s: 2.2%); Turbo 5.0% (1.4%) |
| Player value | Lower than VISION_SWEEP because it has no place |
| Use | Only when identity is unresolved |

**Verdict: ENRICHMENT ONLY** (fallback line).

### 10. ROSHAN_AREA_CLEARED — REJECT

| Aspect | Detail |
|---|---|
| Evidence | Truth set: 19 of 54 observers near the pit areas were cleared (35%, similar to the river overall) |
| Frequency | ≥ 3 cleared: 0.7% / 0.1% |
| Problem | Pit location is not validated for the current patch (Roshan changes pits) |

**Verdict: REJECT** (too rare, unsafe geometry).

### 11. CLEAR_THEN_DEATHS_NEARBY — REJECT as a card; at most a guarded sequence line

| Aspect | Detail |
|---|---|
| Calculation | Allied deaths within 25 cells (1600 units) of the cleared ward in the next 120 s |
| Base rates | See Section 5: after-clear 44% vs same-spot control 30%; with no nearby death in the previous 2 min, 41% vs 27%; two or more deaths 21% vs 12%. **About two-thirds of "after" stories would happen anyway.** |
| Fight context | 42–50% of clears already had an allied death nearby in the **preceding** 2 minutes: the deward is often the aftermath of a fight |

**Verdict: REJECT for V1** (false-story risk too high).

### 12. CLEAR_THEN_OBJECTIVE / NET-WORTH SWING — REJECT

| Aspect | Detail |
|---|---|
| Structures lost | After any deward (3 min): 45.9% vs 42.5% control. After 3-in-2-minute bursts: 49.2% vs 43.4% (n=130) — no reliable lift. |
| Net worth | Lead change −885 after dewards vs −84 control. This is **confounded**: dewards follow enemy map pressure, so the association is not evidence of effect. |

**Verdict: REJECT.**

### 13. ENEMY_DEWARD_SPECIALIST — ENRICHMENT ONLY

| Aspect | Detail |
|---|---|
| Question | Who did the dewarding? |
| Calculation | Historical exact: `wardDestruction` credited per enemy hero |
| Threshold | ≥ 5 and ≥ 60% of our destroyed observers |
| Frequency | Standard 13.9%, Turbo 3.5%. Specialists (≥ 4) are mostly Position 5 (163) and Position 4 (126) in Standard. |
| Player value | Low-medium alone ("their support dewarded" is expected). Better when extreme and surprising: "Their Hoodwink destroyed 11 of the 12" (match 8971203099); a core dewarder (Storm Spirit 6 of 8, match 8773670384). |

**Verdict: ENRICHMENT ONLY** (a name inside the card).

### 14. ENEMY_SENTRY_INVESTMENT — PROMISING (belongs to Hidden Enemy Activity, not this card)

| Aspect | Detail |
|---|---|
| Question | How hard did they hunt our vision? |
| Calculation | Enemy sentries placed in our half (historical, exact) |
| Distribution | Standard p50 / p90 = 7 / 18 in our half (28 / 43 total); Turbo 4 / 11 (17 / 26) |
| Player value | Medium. Sentries are invisible to the player, and 95% of clears had one nearby. |
| Use | Evidence clause inside VISION_SWEEP. Could be tested later as its own hidden-activity candidate. |

**Verdict: PROMISING / supporting evidence.**

### 15. CLEAR_WITH_ENEMY_SMOKE — REJECT

| Aspect | Detail |
|---|---|
| Evidence | Playback only: an enemy smoke in [−60 s, +300 s] around 59% of clears. That base rate is too high, and there is no historical timing. |

**Verdict: REJECT.**

### 16. Historical ward identity from deward gold — REJECT

| Aspect | Detail |
|---|---|
| Evidence | STRATZ `gold` does not track ward age (residual range 6–493 gold against age ÷ 15) |

**Verdict: REJECT** (method disproved).

---

## 4. Vision coverage feasibility

**Question:** "They destroyed 10 wards before minute 20, reducing your map visibility to X%."

### A. Literal actual visibility — not feasible

| Aspect | Assessment |
|---|---|
| Requires | Fog-of-war state per team per tick. Ground vision is blocked by trees (which are cut and regrow), cliffs and high ground. It also depends on hero and creep vision, day/night radii, Smoke/invisibility, sentries/true sight, and reveal spells. |
| Available | None of this is in historical stats or the playback fields we have. `playerUpdatePositionEvents` exists in the schema but would give hero positions only, not vision. |
| Likely error | Unbounded; any number would be invented |
| Recommendation | **Never claim.** |

### B. Geometric Observer coverage estimate — prototyped, not recommended for copy

| Aspect | Assessment |
|---|---|
| Method | Union of 25-cell circles (1600 units) of our alive observers over the playable 64–192 square (4-cell sampling grid), averaged per minute from 10:00. Exact lifetimes from playback. |
| Results (36 truth perspectives) | Our nominal coverage median **18.0%** of the square (p10 14.5%, p90 21.5%). **Dewarding removed a median of 2.9 percentage points.** Our ÷ their coverage p10 / p50 / p90 = 0.74 / 0.99 / 1.26. Correlation with share destroyed −0.28. |
| Missing | Terrain occlusion (tree lines and cliffs can hide most of a circle), day/night radius, overlap with hero vision, the fact that wards are placed to watch paths rather than area |
| Likely error | Large and one-directional: the circles overstate what a ward sees |
| Would it mislead? | Yes, twice. "18%" looks like "we saw 18% of the map". "Dewards reduced visibility from 21% to 18%" looks both precise and unimpressive. |
| Recommendation | **REJECT** for player-facing use. It could remain an internal ranking feature if ever needed. |

### C. Observer uptime — feasible, low value

| Aspect | Assessment |
|---|---|
| Method | Actual ÷ nominal observer-seconds (exact with playback; bounded or estimated historically) |
| Error | Playback: none. Historical interval median width 12 min; midpoint error median 1.9 min on a truth median of 13.6 min. With identity reconstruction, about 80% of the removed time is exact. |
| Value | Low (correlation −0.83 with share destroyed) |
| Recommendation | Use only as **"observer-minutes removed"** (candidate 5), never as percent visibility |

### D. Strategic-region presence — feasible for placement and fate, not for vision

| Aspect | Assessment |
|---|---|
| Method | Region grid (Section 2). Placement region is exact historically; cleared-ward region is 99% correct when identified. |
| Supportable | "3 of your observers in the river were destroyed between 21:00 and 24:00". "You kept an Observer standing in their half for N of the M minutes after 10:00" is computable with playback, or bounded historically. |
| Missing | Region semantics are coarse. The jungle is only "half of the map". Roshan geometry is unvalidated. |
| Error | Low for regions; the region presence-time share is only as good as uptime (C) |
| Recommendation | **Use for place-and-time facts (VISION_SWEEP)**. Do not present "presence in 3 of 8 strategic regions": the strategic regions are our own invention and not validated. |

### E. Other safer proxies

| Proxy | Status |
|---|---|
| "Observers destroyed within 90 s of placement" | Strongest; exact with playback, a lower bound historically |
| "Enemy sentries placed near your observers" | Historical, exact |
| "Minutes of observer time removed" | Supporting |

**Answer to the owner.** A literal "you saw X% of the map" is not defensible: we do not know fog-of-war state, and ward circles ignore trees and cliffs. The honest, stronger replacement is:
- how quickly the wards were found;
- where the enemy cleared them;
- optionally, how many observer-minutes were removed.

---

## 5. Consequence / sequence analysis

**Design.**
- **Events:** our observers destroyed by the enemy. Exact on the playback set (n=176 at a 120 s window). Identified historically on the corpus (n=5,296).
- **Outcome:** allied deaths within 25 cells (1600 units) of the ward, or anywhere; own towers/barracks lost; net-worth lead change.
- **Controls:** the same ward location at the same match's other times (±4, ±7, ±10 min); natural-expiry wards; random matched times for time-only tests.

| Test | After clear | Control | Lift | Read |
|---|---:|---:|---:|---|
| Allied death near the ward, next 2 min (playback exact) | 33% | 25% (same spot) | 1.35× | Weak |
| Same, next 5 min | 57% | 50% | 1.14× | Weak |
| Allied death near the ward in the **previous** 2 min (playback) | 42% | — | — | Clears cluster **after** fights |
| Allied death near, next 2 min (historical identified, n=5,296) | 44% | 30% | 1.49× | Modest |
| Same, no nearby allied death in the previous 2 min (n=2,629) | 41% | 27% | 1.51× | 66% of these stories would happen anyway |
| Two or more nearby allied deaths, no prior death | 21% | 12% | 1.74× | Still majority baseline |
| Allied death anywhere, next 3 min (every deward, n=6,001) | 91.7% | 91.7% | 1.00× | Dota is busy |
| Own tower/barracks lost, next 3 min | 45.9% | 42.5% | 1.08× | None |
| After a 3-in-2-min burst: structure lost, next 3 min (n=130) | 49.2% | 43.4% | 1.13× | Noisy |
| Net-worth lead change, next 3 min | −885 | −84 | — | Confounded (enemy pressure precedes clears) |
| Enemy smoke within [−60 s, +300 s] (playback) | 59% | — | — | High base rate |
| Enemy deaths near the cleared ward, next 2 min (playback) | 38% | — | — | Fights go both ways |

**Conclusion.** "X happened after dewarding" is mostly what Dota does anyway. The strongest variant (two or more nearby allied deaths, no prior fight) is still baseline in about 57% of cases. A sequence sentence would be true but would invite a causal reading that the data does not support.

**V1 recommendation: no consequence line.** If the owner wants one later, allow only a neutral time-and-place line ("two of your heroes died in that area in the next two minutes"), only when no nearby fight happened in the previous two minutes, and never as the headline.

---

## 6. Real-match examples

### Excellent

1. **Turbo loss, 22 min — match 8983370743 (Dire).**
   > 4 of your 10 observers were destroyed within 90 seconds (2 within a minute). Between 9:50 and 12:50 three observers in your half were destroyed after 90, 36 and 65 seconds; the enemy placed 4 sentries there. Their Venomancer destroyed 4 of 5.

   Why excellent: early (lead only −5k), specific, hidden from teammates, and the sentry evidence explains how without claiming cause.
2. **Standard win, 59 min — match 8463940029 (Radiant).**
   > 8 of your 26 observers were destroyed within 90 seconds (5 within a minute); their Shadow Shaman destroyed 7 of 13.

   Why excellent: happens in a win, so it is not a loss excuse, and it is a pattern the warder only half-noticed.
3. **Standard win, 71 min — match 8971203099 (Dire).**
   > Their Hoodwink destroyed 11 of your 12 cleared observers; 6 died within a minute of being placed; four in their half fell between 27:18 and 29:52.

   Why excellent: an extreme concentration plus a place and a time.
4. **Standard loss, 55 min — match 8829989290 (Dire).**
   > 8 of your 25 observers were destroyed within 90 seconds (7 within a minute); their Bane destroyed 10 of 12.

   Why excellent: quick clears and a specialist. Its sweep (50:22–51:29) must be dropped by the final-minutes guard; the quick-clear line alone is good.
5. **Standard win, 50 min — match 8967682035 (Dire).**
   > Between 19:18 and 23:20 three observers in their half were destroyed after 46, 101 and 115 seconds; 4 of your 15 lasted under 90 seconds.

   Why excellent: happened while trailing 3.8k in a game they later won, so it is not a result restatement.

### Boring

1. **Turbo loss, 23 min — match 8977537646.** "Enemy destroyed 5 of your 10 observers (50%)." No quick clears, no sweep, and the game was lost by 44k. Count only; restates the stomp.
2. **Standard loss, 27 min — match 8900728743.** "6 of 11 destroyed". The cleared wards lived a median of 128 s and nothing clustered. Nothing to learn.
3. **Standard win, 73 min — match 8991555270.** "15 of 31 destroyed". A long game inflates the count; the dewarder was their support (Nyx, 9 of 15) doing its normal job.
4. **Turbo loss, 31 min — match 8772511984.** A "sweep" of three own-half observers at 22:02–25:12. They had already lived 277, 322 and 111 seconds, so little was lost, and the team was already 19k behind. Technically a sweep, practically nothing.
5. **Standard loss, 46 min — match 8974982183.** "Their Rubick destroyed 5 of your 10." A support dewarding is expected; the name adds no surprise.

### Misleading / dangerous

1. **Turbo loss, 24 min — match 8969440024.** Sweep of three own-half wards at 15:17–19:07 while already **27k behind**. The sentence would read as an explanation for a game that was decided. → Deficit guard.
2. **Standard loss, 55 min — match 8829989290.** Three wards destroyed at 50:22–51:29 during the final push (the match ended 55:xx). This is the end-game high-ground clear, not a hidden pattern. → Final-5-minutes guard. Turbo sweeps end in the final 5 minutes 29% of the time.
3. **Standard, match 8965006124 (Radiant).** A ward placed 17:00 was destroyed 19:17 in our half. Axe, Lina and Shadow Shaman had **already died nearby at 17:19–17:49**, and more deaths followed at 19:29–20:55. "After your wards were cleared, three heroes died there" would hide that the deward was part of a fight already being lost.
4. **Coverage framing on any match:** "Your observers covered 18% of the map". The median nominal circle area ignores trees and cliffs, and the implied "enemy removed 3% of your vision" is false precision.
5. **Presence gap — match 8984234793 (Radiant).** No observer standing 34:20–40:40. The gap began with a **natural expiry** (only 4 of 26 wards were cleared). Presenting it under "vision cleared" would blame the enemy for the team not re-warding.
6. **Identity error (the ~8% case) — match 8965006124.** The deward at 51:44 was attributed to the ward placed at 49:28 at (84, 116); the truth was the ward placed at 49:18 at (104, 102). The region was still right (their half). Lifetime-precise sentences must tolerate this: round lifetimes, and prefer counts over single-ward claims.

---

## 7. Historical vs recent architecture

### A. CORE historical only — recommended baseline

- **Inputs:** `stats.wards` (both teams, both types), `stats.wardDestruction`, `stats.deathEvents`, `towerDeaths`, `networthPerMinute` (for guards).
- **Process:** reconstruct cleared-ward identity with the sentry rule (enemy sentry ≤ 10 cells, placed ≤ 90 s before the deward, unique best candidate; single alive candidate as fallback).
- **Output:** QUICK_CLEARS (lower-bound counts), VISION_SWEEP, specialist name, sentry evidence, deward bursts as fallback.
- **Coverage:** about 81% of dewards identified; batchable (7 matches per request); works for old matches.
- **Wording:** stays count-based ("at least N"), so the ~8% identity error never produces a false specific claim.

### B. CORE + REPORTS

Adds nothing material for vision. `actionReport.scanUsed` is a count without time or place, and chat events lack ward kills.

### C. Recent PLAYBACK enrichment — optional upgrade

- **Adds:** exact lifecycles (100% identity), per-ward destroyer, exact observer-minutes removed, and a precise "lasted N seconds" for single wards.
- **Operational status:** one match per request; ≤ 90 days old; **returned null on 2026-09-15 and 2026-09-16**, even for two-day-old matches.
- **Use:** only as a silent accuracy upgrade. The card must render the same template from A when playback is absent.

**Degradation:**
1. Playback present → exact values.
2. Playback absent → reconstruction.
3. Too few identified clears (< 3 identified, or unresolved share > 50%) → only a count plus the time-only burst fallback, which is **not** enough to show the card.
4. Nothing → no card.

---

## 8. Final shortlist

### KEEP AS HEADLINE

**VISION_CLEARED (enriched) = QUICK_CLEARS or VISION_SWEEP.** One card; count and share appear only as context.

**Inputs (historical):**
- our observer placements (time, x, y);
- enemy sentry placements (time, x, y);
- enemy `wardDestruction` with `isWard = true` (time, destroyer hero);
- our net-worth lead per minute;
- match duration;
- region grid.

**Identity step:** for each deward at time t:
- **Candidates:** our observers with placement ≤ t < min(placement + 360 s, match end), not already assigned.
- **Pick** the candidate whose nearest enemy sentry placed in [t − 90 s, t] is within 10 cells and at least 3 cells closer than the next candidate's.
- **Fallback:** if exactly one candidate is alive, pick it.
- **Otherwise:** unresolved.

**Smallest V1 rules:**

- **QUICK_CLEARS**
  - identified clears with life ≤ 90 s ≥ 4 (Standard) / ≥ 3 (Turbo);
  - they are ≥ 25% of our placed observers;
  - counted only before (match end − 5 min).
  - Frequency: about 4% Standard / 9% Turbo.
- **VISION_SWEEP**
  - ≥ 3 identified clears whose wards are in the same region, within 300 s;
  - window ends before (match end − 5 min);
  - our net-worth lead at window start > −10,000;
  - evidence clause shown only if the enemy placed ≥ 1 sentry in that region in [start − 90 s, end].
  - Frequency before guards: 11.3% Standard / 7.9% Turbo; after guards an estimated ~8% / ~4–5% (not separately measured).
- **Card slots:**
  - placed / destroyed counts;
  - quick-clear count, and the count within 60 s;
  - sweep region and time window;
  - lifetimes of the swept wards, rounded;
  - enemy sentries placed there;
  - optional top dewarder, if ≥ 60% and ≥ 5;
  - reconstruction confidence (identified share).

### KEEP AS ENRICHMENT ONLY

- **ENEMY_DEWARD_SPECIALIST** — a name inside the card.
- **AGGRESSIVE_VISION_DENIED** — a clause when the swept region is their half.
- **OBSERVER_MINUTES_REMOVED** — one rounded number, playback or identified only.
- **DEWARD_BURST** — time-only fallback clause.
- **ENEMY_SENTRY_INVESTMENT** — evidence clause; separate hidden-activity test later.

### REJECT

- **VISION_CLEARED_COUNT** as a standalone headline.
- **Literal or geometric visibility percentage** ("reduced your map visibility to X%").
- **VISION_UPTIME_GAP**.
- **WARD_PRESENCE_GAP** as an enemy-caused fact.
- **CLEAR_THEN_DEATHS_NEARBY** (V1).
- **CLEAR_THEN_OBJECTIVE / net-worth swing.**
- **CLEAR_WITH_ENEMY_SMOKE.**
- **ROSHAN_AREA_CLEARED.**
- **Gold-bounty ward identity.**
- **Any "bad ward" judgement.**

**Required follow-up validation:** re-score the sentry-based identity on a fresh playback sample (≥ 30 matches) when playback returns. It was tuned and scored on the same 18 matches.

---

## 9. Questions requiring owner decision

1. **Replace or rename?** Should the enriched card replace today's count-based "Our Vision Cleared", given that about half of today's fires would no longer show a card?
2. **Show a card built from reconstructed (≈92%-precise) ward identities, or require playback-exact data?** Requiring playback would make the card almost never appear while playback is unavailable.
3. **Name the enemy dewarder?** It is exact historically and sometimes striking ("their Hoodwink destroyed 11 of 12"), but it is usually "their support did its job".
4. **Loss skew.** Both headline patterns fire more in losses (Standard sweep 14.1% vs 8.5%). Accept, or apply the future negative-insight balancing rule?
5. **Consequence lines.** Keep them out entirely (the evidence recommendation), or allow the strictly neutral, fight-free "two of your heroes died in that area in the next two minutes" as an optional line at about 1.5× lift?
