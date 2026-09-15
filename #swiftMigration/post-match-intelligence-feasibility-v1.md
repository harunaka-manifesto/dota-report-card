# Post-Match Intelligence Feasibility & Architecture

Status: FEASIBILITY STUDY AND PROPOSED DESIGN — non-normative
Date: 2026-09-14
Repository base: `main` at `5d23eed`
Provider calls made for this study: STRATZ 0, OpenDota 0
Corpus read: Pass-2 `DISCOVERY` and Pass-1 new-lineage history `DISCOVERY` only
`CANDIDATE_TEST`, `CALIBRATION_RESERVED`, `SEALED_VALIDATION`: not read
Identifiers in this document: none (aggregate statistics only)

> **Correction, 2026-09-14 (same day):** a bounded 10-call STRATZ probe showed
> that full parsed `stats` for **all ten players** (camp stacks, wards, dewards,
> farm source, per-minute economy, death/kill events with killer, position, and
> time dead) are available in 8-match batches without a complexity error. The
> statements below that other players are opaque, that enemy stacking/vision is
> impossible, that time dead and positions are unavailable, and that ten-player
> stats exceeded the complexity ceiling are **superseded** by
> [Ten-Player Match Intelligence V1](ten-player-match-intelligence-v1.md). They
> are corrected inline where marked.

This document does not change any locked rule. Where it touches metric
definitions, baselines, Personal Bests, eligibility, or lifecycle, the
[Role Metrics & Personal Baselines V1](role-metrics-and-baselines-v1.md) and
[Match Lifecycle V1](match-lifecycle-v1.md) SSOTs remain authoritative. Anything
here that would alter those contracts is labelled as a proposal requiring an
owner decision.

---

## 1. Executive verdict

**Yes — this can become a meaningful core feature, but only as a narrow,
personal-history observation engine. It cannot become a "why did I lose"
engine with the data we have, and it should not try.**

The "wait, I didn't realise that happened" moment is achievable when the claim
is *"this was unusual for you"* or *"this is when the game turned"*. It is not
achievable honestly when the claim is *"this is why"*.

Seven measured facts decide the verdict:

1. **The personal data is rich enough.** For the tracked player we hold per-minute
   net worth, last hits, damage, healing, camp stacks, level-up timestamps,
   death/kill/assist timestamps, ward placements, dewards, runes, item
   purchases, ability/talent timings, and lane-versus-jungle farm source, with
   93.6% of Pass-2 rows passing a progression-like eligibility gate and 96.7%
   carrying a 10:00 checkpoint.
2. **Other players are opaque in the current corpus — but not at the provider.**
   *(Corrected.)* Existing queries collect only final scoreboard scalars for the
   other nine players. STRATZ serves their full parsed `stats` (stacks, wards,
   dewards, farm source, per-minute economy, death/kill detail) in 8-match
   batches; see [Ten-Player Match Intelligence V1](ten-player-match-intelligence-v1.md).
   Enemy stacking and vision become facts after collection and validation;
   *"…and fed their cores"* remains a hypothesis at best.
3. **The team timeline is solid.** The oriented team net-worth lead curve
   (89.8% of eligible matches reach 20:00 with it), per-minute team kills, and
   tower deaths with timestamps and verified ownership semantics make *"when
   the game turned"* a defensible fact.
4. **Per-match "unusual" flags are mostly noise unless gated hard.** With a
   naive |robust z| ≥ 2 rule against the player's previous 20 games, **32.6% of
   role matches** raise at least one role-metric flag. That is roughly what
   chance produces across 2–5 metrics. Selection must be conservative or the
   product will narrate noise every game.
5. **Fatigue and in-session improvement are not detectable.** Across 8,843
   parsed sessions of four or more matches, no measured laning or death metric
   moved by more than about 0.05 player-SD by game index. A five-match
   session's mean has a standard error of about 0.45 SD. Session "fatigue",
   "tilt", "improving throughout the night", and "deteriorating" stories must
   be rejected.
6. **Positives inside losses occur at a chance-like rate.** 21.7% of losses
   contain a favourable extreme in a role metric, versus 23.2% of all
   matches. Those positives are real facts but not evidence of hidden good
   play. The negative-session experience is supportable only with modest,
   factual copy.
7. **Freshness is a product constraint.** In Pass-1 history, only 54.1% of
   Standard and 49.4% of Turbo matches were parsed within 15 minutes of ending;
   8.0% of Standard and **27.6% of Turbo matches were never parsed** by
   collection time. A post-session recap will frequently be partial when the
   player opens the app immediately.

**Differentiation:** real. Personal records on role-appropriate metrics, "this
was your best laning game in 20", *when* the game swung and what fell during
it, and multi-match same-direction patterns are things a player does not get
from the scoreboard or DotaPlus and would not reliably notice while playing.

**Hardest part:** not engineering. It is *restraint*: detecting real signals
among chance fluctuations, suppressing hero-driven artefacts (hero explains
~50% of a player's game-to-game variation in Support Healing), and shipping a "quiet game" state instead of inventing a
story.

**Realistic expectation:** a genuinely noteworthy item for roughly a third of
single matches and for most sessions of four or more matches. In the Pass-2
corpus, 69.6% of one-match sessions had no role-metric PB or extreme at all;
by seven or more matches that fell to 6.5%. The design must treat "nothing
notable" as a normal, respectable outcome.

---

## 2. What data we actually have

### 2.1 Corpora and code actually inspected

| Source | What it is | Scale | Status |
|---|---|---|---|
| `.local/corpora/stratz/v7-pass2-2026-09-04/canonical` | `GetDeepMatchBatch` v3.4.0: tracked-player full parsed detail + ten-player scalar scoreboard + match timeline | 278 accounts, 104,982 parsed matches, ≤500 most recent parsed per account | Intact, reproducible from raw (`docs/evidence/v7-pass2-integrity-verification-2026-09-08.md`) |
| `.local/corpora/stratz/v7-pass1-history-new-lineage-2026-09-07/canonical/history` | `GetPlayerHistoryPage`: one row per match, 365-day window | 600 accounts; 552 with product-mode rows; 362,443 clean Standard/Turbo rows in window | Intact; the *original* Pass-1 corpus was lost (`v7-corpus-loss-incident-2026-09-07.md`) |
| `.local/stratz-probe/enrichment/A1b.json` | Live introspection of core types | 7 types | Historical specimen |
| `services/api/app/stratz/queries.py` | Versioned GraphQL operations | `GetDeepMatchBatch` 3.4.0 (lines 606–783) | On `main` |
| `services/api/app/player_analysis_v7/research/pass2_tables.py` | The only place Pass-2 provider semantics are decided | Rules 1–6 in module docstring | On `main` |
| `services/api/app/player_analysis_v7/research/pass2_features.py` | Year-level Pass-2 dimensions, lane mapping, observer-ward type verification | 8 dimensions | On `main` |
| `codex/backend-role-metric-contracts` @ `d691008` | Candidate progression calculators and `GetRoleMetricMatchBatch` v1.0.0 | 5 calculators | **Not on `main`** |

Every coverage and distribution number in this document was computed
read-only for this study from the two canonical corpora above (method in
Appendix A). Numbers describe an active, public, parsed-heavy research cohort,
not all Dota players.

### 2.2 Field inventory by category

Legend: **V** = collected, semantics verified from corpus; **C** = collected,
semantics unverified or only partially verified; **N** = exists in STRATZ
schema, not collected; **F** = forbidden by policy.

#### Match-level raw

| Field | Status | Notes |
|---|---|---|
| `didRadiantWin`, `durationSeconds`, `startDateTime`, `endDateTime` | V | 100% |
| `gameMode`, `lobbyType` | V | Standard = `ALL_PICK*` with `RANKED`/`UNRANKED`; Turbo = `TURBO` |
| `gameVersionId` | V | 100%; three patches in corpus |
| `regionId` | C | populated in deep query, null in history projection |
| `numHumanPlayers`, `isStats`, `statsDateTime` | C | data-quality gates; `isStats=false` observed on parsed matches, meaning unknown |
| `firstBloodTime` | C | can be negative (pre-horn) |
| `towerStatus*`, `barracksStatus*` | C | final bitmasks only |
| `pickBans {isPick, isRadiant, heroId, bannedHeroId, order, playerIndex, ...}` | C | collected; order semantics not validated; unused |
| `analysisOutcome`, `winRates`, `predictedWinRates`, `averageRank`, `rank`, `bracket`, `averageImp` | F | proprietary model outputs / rank |

#### Timeline / event data (match level)

| Field | Status | Notes |
|---|---|---|
| `radiantNetworthLeads[]` | V | cumulative Radiant-minus-Dire level; Dire orientation flip required; final sign predicts winner in 96.6% |
| `radiantExperienceLeads[]` | C | collected; not analysed |
| `radiantKills[]` / `direKills[]` | V (as interval kill counts) | kills during minute *i*; **not** scoreboard-credited kills; must not be a participation denominator |
| `towerDeaths {time, isRadiant, npcId, attacker}` | V for `time`, `isRadiant` | `isRadiant` = tower *owner* (97.4% consistency test); `attacker` unverified |
| `playbackData.roshanEvents` | N / unreliable | returned empty on a 60-minute specimen; not collected |
| `laneReport` | N | third-level nested shape unresolved; excluded for complexity |
| `*LaneOutcome` (top/mid/bottom) | C | provider classification (`TIE`, `*_VICTORY`, `*_STOMP`); team/lane-level; how STRATZ computes it is not documented |

#### Tracked player (`self`)

| Field | Status | Notes |
|---|---|---|
| K/D/A, `numLastHits`, `numDenies`, `goldPerMinute`, `experiencePerMinute`, `networth`, `level`, `gold`, `goldSpent`, `heroDamage`, `towerDamage`, `heroHealing` | V | scalars |
| `position`, `role`, `lane` | V | three distinct concepts; 3.3% of eligible parsed rows lack position; essentially all unparsed rows lack all three |
| `leaverStatus` | C | `NONE`, `DISCONNECTED` observed; full enum unmapped (SSOT: integrity fails closed) |
| `partyId` | C | non-null ⇒ queued in party (verified); null ≠ proven solo |
| `invisibleSeconds` | C | semantics unknown; do not use |
| `variant` | C | facet id; unused |
| final `item0..5`, backpack, neutral | V | final inventory only |
| `abilities {abilityId, level, time, isTalent}` | C | real timings; unused |
| `imp`, `award`, `behavior`, `intentionalFeeding`, `roleBasic` | F | |

#### Tracked-player trajectories (`stats.*PerMinute`)

| Field | Semantics | Status |
|---|---|---|
| `networthPerMinute` | cumulative level; one element longer than the other arrays; can decrease on death | V |
| `lastHitsPerMinute`, `deniesPerMinute`, `towerDamagePerMinute`, `healPerMinute` | per-minute increments | V (last hits re-verified on Pass-2; others verified on specimens) |
| `heroDamagePerMinute` | per-minute increment, tail may be unbucketed | C |
| `goldPerMinute` | running average | C |
| `experiencePerMinute` | XP gained in that minute | C |
| `heroDamageReceivedPerMinute` | cumulative level | C |
| `campStack` | cumulative, non-decreasing (100% monotone in eligible Pass-2 rows) | V (candidate-branch validation) |
| `tripsFountainPerMinute` | per-minute counter | C, unused |
| `level` | **level-up timestamps in seconds, one entry per level**, not a minute grid | V |
| `actionsPerMinute` | quarantined hidden-skill proxy | F (quarantine) |

**Array alignment is not settled for exact checkpoints.** Standard per-minute
arrays are `ceil(duration/60) − 1` long in 98.4% of rows and one longer in
1.6%; `networthPerMinute` is one longer still. `pass2_tables.trajectory()` clips
defensively but explicitly does not establish a universal offset. Every
"@10:00" or "@20:00" number below uses a documented index approximation, and
the SSOT already requires a validated time-aligned adapter before any
checkpoint metric ships.

#### Tracked-player events

| Field | Status | Notes |
|---|---|---|
| `killEvents {time}` | V | count matches scoreboard in 95% |
| `deathEvents {time}` | V for timing | count matches scoreboard in 96.2%; **no killer, no location, no respawn time** |
| `assistEvents {time}` | V for timing only | count disagrees with scoreboard in ~48% of rows |
| `itemPurchases {time, itemId}` | V | item vocabulary exists (575 items) |
| `itemUsed {itemId, count}` | C | counts only, **no timestamps** |
| `matchPlayerBuffEvent {time, itemId, abilityId, stackCount}` | C | partial item-use timing; unused |
| `wards {time, type, positionX, positionY}` | V for `type` (0 = observer, 1 = sentry, verified against purchases) | position grid origin/scale unverified |
| `wardDestruction {time, isWard, gold, experience}` | C | count usable; `isWard` subtype unresolved |
| `runes {time, rune}` | C | enum partially known |
| `farmDistributionReport` creep/neutral location gold | V for lane-vs-jungle mix | ancient-camp and bounty gold were traded away for complexity budget; `buyBackGold` scalar has no timing |

#### Team and opponent data

| Available | Not available |
|---|---|
| For all ten players: `playerSlot`, `isRadiant`, `isVictory`, `heroId`, `position`, `role`, `lane`, K/D/A, last hits, denies, GPM, XPM, final net worth, hero damage, tower damage, hero healing | Any per-minute series, any event stream, camp stacks, wards, dewards, farm source, item timings, level timings, deaths timing, positions |

*(Corrected.)* The 6,159,595 complexity rejection quoted in earlier documents
was a full schema introspection query, not a ten-player stats query. The
2026-09-14 probe fetched full ten-player `stats` for 8 matches in one request
(HTTP 200, no complexity error). Only match-level `playbackData` is limited
(one uncached match per request, fresh matches only). See
[Ten-Player Match Intelligence V1](ten-player-match-intelligence-v1.md).

#### Position / map / location

*(Corrected.)* No movement data: `stats.locationReport` has no time field and
playback movement is prohibited (~4.6 MB per match). But `stats.deathEvents`,
`killEvents`, `assistEvents`, and `wards` carry `positionX/Y` for every player
(not collected today); the coordinate grid is unvalidated.

#### Role classifier output

- Provider `position` is present for parsed matches only.
- The SSOT consumes an upstream `effective_role`; **no role-resolution
  implementation exists** on `main` or the candidate branch (the candidate maps
  provider position directly, which the SSOT records as a conflict).
- Measured instability: in-session consecutive matches change role (Support
  4/5 merged) **48.0%** of the time and hero **82.6%** of the time. Only 54.0% of
  sessions with three or more matches contain three or more matches in one
  role.

#### Derived metrics already implemented

| Where | What | Level | Reusable for post-match? |
|---|---|---|---|
| Candidate branch `d691008` | Support Healing, Support Fight Presence, Camps Stacked (final value — conflicts with SSOT @20:00), Mid Early Fight Presence, Offlane Objective Involvement | per match | Yes after SSOT conflicts are fixed |
| `pass2_tables.py` (main) | oriented team lead curve, fight minutes, deaths-alone share, own-team tower kills, lane-vs-jungle gold, ward events, first ward time, product-context gate | per match | Yes — semantics layer is directly reusable |
| `pass2_features.py` / `pass2_observations.py` (main) | vision coverage, spike usage, death clustering, closer-vs-comeback, lane-to-map, fight conversion | per player-year (per-match series exist) | Per-match series reusable; year-level estimands are not post-match insights |
| V7 runtime (`player_analysis_v7/runtime.py`) | 16 population-ranked Findings, one recommendation, archetype | per player-year | **No** — these answer "who are you across a year", require population context projection, and are not per-match |

#### Historical / baseline data

- No persisted per-match observation history exists for V7 or progression.
  `storage/models.py` tables (`matches`, `match_participants`,
  `derived_features`, …) are OpenDota-era; V7 persists reports only.
- `acquisition_policy.PERSISTENCE_REQUIREMENTS` states fetch-once/reuse rules
  but explicitly is not wired.
- Baseline and PB engines exist only as an in-memory candidate (mean instead of
  the locked median; PB restricted to prior-20 instead of all-known history).

#### Collected but unused

`radiantExperienceLeads`, `pickBans`, `abilities` (skill/talent timings),
`runes`, `itemUsed`, `matchPlayerBuffEvent`, `wardDestruction` (only in SSOT
Vision Denial), `towerDeaths.attacker`, `partyId`, `buyBackGold`,
`heroDamageReceivedPerMinute`, `tripsFountainPerMinute`, ten-player healing /
tower damage / net worth scalars beyond share denominators.

### 2.3 Coverage among eligible Pass-2 matches

Eligible = Standard or Turbo, leaver `NONE`, duration ≥ 600 s, ten human
players: **98,216 of 104,982 rows (93.6%)**; Turbo 62,586, Standard 35,630.
Provider-position role proxy: Support 35,252, Mid 21,800, Carry 19,865, Offlane
18,104, missing 3,195.

| Derived value | Non-null |
|---|---:|
| last hits @10 (approx. index) | 96.7% |
| net worth @10 / @20 | 96.7% / 86.8% |
| camps stacked @20 (approx. index) | 86.8% |
| level-6 time | 96.7% |
| fight presence / hero-damage share | 100% |
| tower-damage share (N/A when team tower damage = 0) | 98.2% |
| deaths-in-quiet-minutes share (needs ≥1 death) | 95.2% |
| first observer ward (needs ≥1 observer) | 58.4% |
| lane-vs-jungle share | 96.7% |
| oriented team lead @20 | 89.8% |
| own lane outcome (mapped) | 96.1% |

Baseline readiness on this ≤500-match window, same account + bucket + role:
**91.8%** of matches have ≥5 prior observations, **73.0%** have ≥20. Same
**hero** + role + bucket: only **36.2%** have ≥5 prior.

### 2.4 Parse latency (Pass-1 history, clean Standard/Turbo in window)

| Bucket | Never parsed by collection | Parsed ≤15 min after end | ≤1 h | ≤24 h | Median delay |
|---|---:|---:|---:|---:|---:|
| Standard | 8.0% | 54.1% | 69.1% | 86.4% | 695 s |
| Turbo | **27.6%** | 49.4% | 64.9% | 70.0% | 493 s |

Caveat: `parsed_at` may reflect a later re-parse, which would overstate delay.
The unparsed share is close to final because collection ran at least six days
after the window closed. Only 68.7% of all sessions were fully parsed.

### 2.5 Assumptions in existing documents that the corpus does not support

| Claim (source) | What the corpus shows | Consequence |
|---|---|---|
| Stacks are "invisible work that decides games" (`v7-report-narrative-and-data-requirements-2026-09-04.md` §2) | Support camps @20: median 0, 70.7% zero; win-versus-loss gap 0.00 SD | Stack counts are a legitimate personal record signal, not a match-deciding signal |
| "Match results are far too noisy to see fatigue. Laning numbers are not." (same doc §2.10 K) | Laning and death metrics show no game-index drift within sessions (≤0.05 SD, n=49,550) | Fatigue remains undetectable with in-game metrics too |
| Deaths-alone is "the single most important derived signal" (`pass2_tables.py`) | Reliable at year level (0.893) and nearly independent of result (gap ≈0.0–0.09 SD), but a *minute-granularity proxy*, and per match it rests on a handful of deaths | Keep as observation with careful wording; not "you get picked off" |
| Support Healing as a role-baseline progression metric (SSOT registry) | Hero explains **~50%** of within-player residual variance; Turbo Support median healing is 0 | Healing deltas/PBs mostly reflect hero choice; contract stays, but insight layer must suppress or hero-scope it (owner decision recommended) |
| Mid Lane Net Worth Advantage and Offlane Lane Pressure @10 (SSOT registry) | Opponent `networthPerMinute` is not requested by any existing query; only opponent *final* net worth exists | Both metrics are blocked on new collection plus a complexity probe |
| Mid Early Fight Presence and Offlane Objective Involvement (SSOT) | Required `allPlayers.stats.killEvents` and `towerDamageReport` exist only in the unmerged candidate query; not in any corpus | Cannot be distribution-validated on existing corpus |
| "In production a single user is fetched at full depth… research-coverage artifact, not a product limit" (`v7-backend-capability-manifest.md` §0.4) | 27.6% of Turbo matches never parse | Parsed-dependent capabilities have a real product coverage limit for Turbo-heavy players |
| `docs/progression/role-metrics-and-baselines-v1.md` | Stale pre-bucket copy (identity lacks `progression_bucket`) | The `#swiftMigration/` copy (2026-09-13) is the current SSOT; the stale copy should be marked superseded |
| Candidate Camps Stacked validation concludes "V1 uses the final value" | SSOT locks the @20:00 checkpoint with no final fallback | Existing recorded conflict; confirmed still unresolved |

---

## 3. What the data allows us to know

### 3.1 The evidence ladder

| Rung | Meaning | Evidence requirement | Example we can support |
|---|---|---|---|
| **Fact** | Directly measured in this match | Validated field semantics; N/A never coerced | "Your team led by 4.2k at 18:00 and trailed by 7.9k at 26:00." |
| **Observation** | This match relative to *your own* history | Point-in-time baseline, minimum history, effect floor, chance control | "Your 10-minute CS was higher than in 19 of your last 20 Carry games." |
| **Pattern** | Repeats across several of your matches | Same direction across most matches of a session or window, with a stated chance probability | "In 4 of 4 Support games tonight your first ward was earlier than your usual." |
| **Hypothesis** | Temporal co-occurrence or personal association | Explicit "at the same time" / "in your games where…" framing; ≥15 games per arm for associations | "Your team's lead fell fastest in the same minutes as three of your deaths." |
| **Causal claim** | X caused Y | Identification strategy we do not have | **Not supported anywhere in this product** |

### 3.2 The product's example questions, graded

| Question | Highest defensible rung | Safe reformulation |
|---|---|---|
| What meaningfully helped this match? | Observation | "What went better than your usual" |
| What held the player/team back? | Observation (player) / Fact (team timeline) | "What was below your usual" / "when the lead changed" |
| What was unusual or surprising? | Observation | Rank within own recent history |
| What changed versus normal behaviour? | Observation / Pattern | Per-metric, per role |
| A moment that likely shaped the match? | Fact + Hypothesis | "The game swung between A and B"; never "shaped by" |
| Loss but strong personal performance? | Observation on named dimensions only | No composite "strong performance" |
| Win hiding a weakness? | Observation on named dimensions only | "Below your usual: X" |
| Beat a normal tendency or baseline? | Observation / Fact (PB) | Per SSOT |
| Something that normally requires a replay? | Fact | Swing timing, quiet-minute deaths, ward uptime, farm source, stack count, level-6 time. **Not** positions, fights, rotations, decisions |
| Something that should shape the next challenge? | Pattern (multi-session) | Never from one match |

### 3.3 "Why did I lose?" — what is defensible

**A. Safe observation**

| Statement | Data |
|---|---|
| "Your team went from +3.1k at 14:00 to −6.8k at 24:00 and lost four towers in that stretch." | lead curve, tower deaths |
| "You won your lane by STRATZ's lane result; the game was decided after 20:00." | lane outcome (label is provider-computed) + lead curve |
| "Four of your six deaths came in quiet minutes — neither team got 2+ kills." | death times, per-minute team kills |
| "Your 10-minute CS was your best in 20 Carry games." | trajectory + personal history |
| "The opposing team's heroes did 1.6× your team's hero healing." | ten-player scalars (team-aggregate only; never single out a teammate) |
| "The enemy took their first tower at 7:40; yours came at 19:10." | tower deaths |

**B. Reasonable hypothesis** (must be framed as co-occurrence or personal association)

| Statement | Why only a hypothesis |
|---|---|
| "The lead dropped fastest in the same minutes as three of your deaths." | Minute co-occurrence; direction of influence unknown |
| "Across your last 60 Carry games, you won more often when your 10-minute CS was above your usual." | Personal association; confounded by lane matchup, draft, teammates |
| "Your team's losses tonight all turned after 25:00." | Pattern of game state, not of cause |

**C. Too causal / misleading — never ship**

| Unsafe | Safer alternative |
|---|---|
| "You lost because your support didn't stack." | None today (no enemy/ally stack series). With new collection: "Opposing supports stacked 7 camps by 20:00; your team's supports stacked 1." |
| "You threw the game at 25 minutes." | "Your team led by 8k at 23:00 and trailed at 31:00." |
| "Your early deaths cost you the game." | "You died 4 times before 10:00 — more than in 18 of your last 20 Offlane games." |
| "You played well; your team lost it." | "Your lane numbers were among your best. The team lead fell after 20:00." |
| "Your team lost map control after Roshan." | Not expressible |
| "Your carry was the problem." | Never compare named teammates |
| "Unlucky loss." | Not expressible |

**D. Impossible with current data**

- *(Corrected: enemy/allied stacking, warding, dewarding, farm source, item and
  level timing, who killed whom, where deaths happened, and time dead are
  collectable — see the ten-player document; they are D only for the current
  corpus.)*
- map control, positioning, rotations, movement;
- Roshan and Aegis timing (playback Roshan events came back empty again; a
  fresh-only gold-reason lead exists);
- stuns/disables/control (no attributable duration field);
- teamfight composition, initiation, smokes, decision quality, communication;
- the emotional state of the player (tilt, frustration, fatigue).

---

## 4. Candidate post-match insight catalog

Scoring columns: **Interest** to a normal player, **Noticeability** (how likely
they already noticed — lower is better), **Trust** after the adversarial pass.
"Win-gap" is the median within-player difference between wins and losses in
player-SD units (higher = more outcome-linked). "Hero η²" is the share of
within-player, within-role variance explained by hero. All numbers are from
the Pass-2 corpus (Appendix A).

### P0 — extremely strong

#### P0-1 Role-metric Personal Best

| Field | Specification |
|---|---|
| Example | "Best 10-minute CS in any Carry game we have from you: 71." |
| Raw fields | Per SSOT registry metric inputs |
| Derived | SSOT `comparison_value`; strict direction-aware inequality |
| Reference | Same `progression_bucket + effective_role + metric_id + metric_version`, all known history (SSOT) |
| Minimum sample | SSOT: ≥5 prior. **Presentation proposal:** PBs with fewer than 20 prior observations are shown as "early record" and scored lower (PB rate is 11.1% at 5–9 prior, 5.6% at 10–19, 2.4% at 20–49, 0.8% at 50+) |
| Confidence | Deterministic fact relative to recorded history |
| Level | Match (and session roll-up) |
| Type | Fact |
| Interest | High |
| Noticeability | Low — nobody tracks their best CS@10 as Offlane in Turbo |
| Misleading risk | Early-history inflation; history truncated by import depth ("best we have seen", not "lifetime"); hero-driven metrics (Healing); low-count metrics (Camps 1→2); patch changes |
| Frequency | 8.5% of role matches with ≥10 prior have ≥1 PB; sessions with ≥1 PB: 9.9% (1 match), 20.8% (2–3), 35.7% (4–6), 49.7% (7+) |

#### P0-2 Early-window performance versus your recent usual

Metrics: Carry CS @10, Offlane net worth @10, Mid level-6 time, deaths before
10:00 (all roles), Support first observer ward time.

| Field | Specification |
|---|---|
| Example | "Your CS at 10:00 (58) beat 19 of your last 20 Carry games." |
| Raw fields | `lastHitsPerMinute`, `networthPerMinute`, `stats.level`, `deathEvents`, `wards` |
| Derived | Checkpoint values via validated time-aligned adapter; rank among previous 20 eligible observations |
| Reference | Same bucket + effective role, previous 20 (SSOT window) |
| Minimum sample | ≥10 prior for "unusual" wording (proposal; SSOT delta still allowed from 5) |
| Confidence | Rank-extreme rule (top or bottom 1 of 21 ≈ 4.8% chance per metric per side) plus minimum meaningful difference (§10) |
| Level | Match |
| Type | Observation |
| Interest | High |
| Noticeability | Low–medium (players feel "good lane" but not relative to their own history) |
| Misleading risk | Hero confounding (CS@10 hero η² 0.18); lane matchup unobserved; Turbo clock (bucket isolation handles it) |
| Why P0 | Upstream of the result: win-gap only 0.23–0.38 SD versus 0.63–0.72 for net worth @20 |

#### P0-3 The swing window

| Field | Specification |
|---|---|
| Example | "The game turned between 18:00 and 26:00: your team went from +4.2k to −7.9k and lost 4 towers." |
| Raw fields | `radiantNetworthLeads`, `towerDeaths`, `radiantKills`/`direKills`, `durationSeconds` |
| Derived | Oriented lead; the largest adverse (or favourable) change within an 8-minute window; tower losses/gains and kill totals inside that window |
| Reference | This match's game state; optional own-history rank ("largest collapse in 30 Standard games") |
| Minimum sample | None for the fact; ≥20 prior for a record framing |
| Confidence | Deterministic; show only above a bucket-specific swing floor |
| Level | Match |
| Type | Fact |
| Interest | High |
| Noticeability | Medium — players feel a swing but misjudge its timing and size |
| Misleading risk | Team-level, not personal; net worth lead is not "map control"; Turbo scale (a 10→20 min adverse swing ≥6k occurs in 36.5% of Turbo matches versus ≥4k in 21.6% of Standard) |
| Copy rule | Never "throw", "collapse because", or any attribution |

#### P0-4 Same-direction pattern within a session

| Field | Specification |
|---|---|
| Example | "In all 4 Support games tonight your first ward went down earlier than your usual." |
| Raw fields | As per metric |
| Derived | Per match: direction versus the baseline **frozen at session start**; count matches in the same direction |
| Reference | Previous 20 same bucket + role, as of the session's first match |
| Minimum sample | ≥3 matches of that role in the session; ≥10 prior |
| Confidence | All matches same direction for n=3–4 (chance 12.5% / 6.25%); ≥5 of 6 or ≥n−1 for n≥6 with session median outside the prior-20 interquartile range |
| Level | Session |
| Type | Pattern |
| Interest | High |
| Noticeability | Low |
| Misleading risk | Role fragmentation (only 54% of 3+ sessions have 3 games in one role); regression to the mean after an unusual earlier week; multiple metrics tested |
| Frequency | Same metric favourable-extreme in ≥2 matches of a session: 3.7% (2–3), 12.9% (4–6), 31.1% (7+); unfavourable: 1.0%, 4.0%, 13.7% |

#### P0-5 Focus check (challenge evaluation)

| Field | Specification |
|---|---|
| Example | "Focus — first ward before 1:00: done in 3 of 4 Support games." |
| Raw fields | Challenge metric inputs |
| Derived | Per attempted match: met / not met / N/A; "not attempted" when role not played |
| Reference | Challenge definition, itself anchored on the player's baseline at creation |
| Minimum sample | ≥1 attempted match |
| Type | Fact |
| Interest | High (it was asked for) |
| Noticeability | Medium |
| Misleading risk | Role not played → must not read as failure; metric N/A (unparsed) → "couldn't measure" |

### P1 — strong

#### P1-1 Deaths in quiet minutes

| Field | Specification |
|---|---|
| Example | "4 of your 6 deaths came in quiet minutes — neither team got 2+ kills." |
| Raw | `deathEvents`, `radiantKills`, `direKills` |
| Derived | `pass2_tables.deaths_alone_share`: a death is "quiet" when neither team scored ≥2 kills in that minute (the player's own death is itself one enemy kill) |
| Reference | Previous 20 same bucket + role |
| Minimum | ≥4 deaths this match; ≥10 prior |
| Type | Fact (count) / Observation (vs usual) |
| Interest / Noticeability | Medium-high / Low |
| Evidence | Win-gap ≈0.00–0.09 SD; hero η² ≤0.008 — measures the player, not the result |
| Risk | Minute-granularity proxy; a minute with one kill per side still counts as quiet. Copy must describe exactly what was measured ("quiet minute"), never "alone" or "you got picked off" |

#### P1-2 Lane result versus game result

| Field | Specification |
|---|---|
| Example | "You won your lane — the game was lost after 20:00." |
| Raw | `*LaneOutcome`, own `lane`, `isRadiant`, lead curve |
| Derived | `pass2_features._map_own_lane_to_map_lane`, `_won_own_lane` |
| Reference | This match; own-history lane-win share as context |
| Minimum | None |
| Type | Fact (provider label) |
| Interest / Noticeability | Medium / Medium |
| Evidence | Won own lane 39.4% (ties folded in); match win rate 62.2% when lane won versus 44.5% otherwise |
| Risk | Lane outcome is a STRATZ classification with undocumented method; team-lane-level, not the player alone; jungle/roaming players excluded. Year-level `lane_to_map` collapsed to τ=0 — do not generalise into "your lane wins don't matter" |

#### P1-3 Comeback or lost lead as a personal record

| Field | Specification |
|---|---|
| Example | "Your team came back from 11.4k down — the biggest deficit you've won from in 60 Standard games." |
| Raw | Lead curve, result |
| Derived | Minimum (wins) / maximum (losses) oriented lead; rank within own history |
| Reference | Same bucket, all known |
| Minimum | ≥20 prior bucket matches for record framing |
| Type | Fact |
| Interest / Noticeability | High / Medium (players remember comebacks but not the size or rank) |
| Evidence | Standard ≥10k comeback wins 5.6%, lost-from-≥10k-ahead 5.6%; Turbo 11.0% / 10.8% |
| Risk | Team outcome; "lost lead" framing can blame — prefer the neutral fact for losses and reserve record framing for comebacks |

#### P1-4 Observer uptime (Support)

| Field | Specification |
|---|---|
| Example | "One of your observers was up for 74% of the game — your highest in 20 Support games." |
| Raw | `wards {time, type}` |
| Derived | Union of 6-minute observer lifetimes / duration (upper bound: dewarded wards are not shortened) |
| Reference | Previous 20 Support |
| Minimum | ≥10 prior |
| Type | Observation |
| Interest / Noticeability | Medium-high / Low |
| Evidence | Support median uptime 0.52; year-level reliability 0.985; win-gap small |
| Risk | Overstates uptime when wards are killed; says nothing about useful vision. Copy: "placed-ward time", not "vision" or "map awareness" |

#### P1-5 Farm source mix (cores)

| Field | Specification |
|---|---|
| Example | "62% of your creep gold came from the jungle — about double your usual as Mid." |
| Raw | `farmDistributionReport` creep/neutral gold |
| Derived | neutral / (lane + neutral) |
| Reference | Previous 20 same role |
| Minimum | ≥10 prior |
| Type | Observation (neutral — no good/bad direction) |
| Interest / Noticeability | Medium / Low |
| Risk | Excludes ancient and bounty gold; hero η² 0.11–0.14 (jungle-friendly heroes). Never framed as better/worse |

#### P1-6 Damage and tower share versus usual (Carry, Mid)

| Field | Specification |
|---|---|
| Example | "You did 41% of your team's tower damage — more than in any of your last 20 Carry games." |
| Raw | Ten-player `heroDamage`, `towerDamage` |
| Derived | SSOT share metrics |
| Reference | Previous 20 same role; hero shown as context |
| Minimum | ≥10 prior |
| Type | Observation |
| Interest / Noticeability | Medium / Medium |
| Risk | Share depends on teammates; hero η² 0.10–0.18; Mid tower share is *higher in losses* (win-gap −0.24), so a high value is not a "good game" signal |

#### P1-7 Camps stacked by 20:00 (Support)

| Field | Specification |
|---|---|
| Example | "You stacked 4 camps by 20:00. Most of your Support games have 0 or 1." |
| Raw | `campStack` |
| Derived | SSOT @20:00 cumulative checkpoint (requires validated adapter) |
| Reference | Previous 20 Support; all-known for PB |
| Minimum | Absolute floor ≥3 stacks for any highlight (proposal) |
| Type | Fact / Observation |
| Interest / Noticeability | Medium / Low |
| Evidence | Median 0, 70.7% zero, p90 = 2; win-gap 0.00 |
| Risk | PB from 0→1 is trivial; stacking is an action, not proof the stack was used |

#### P1-8 Hero-scoped comparison (when ready)

| Field | Specification |
|---|---|
| Example | "Fastest level 6 in any of your 14 Mid Storm Spirit games." |
| Reference | Same bucket + role + hero, previous observations |
| Minimum | ≥10 prior hero+role (only 36.2% of matches have even ≥5) |
| Type | Observation |
| Why | The only honest frame for hero-dominated metrics (Healing η² 0.50) |
| Risk | Sparse; must not replace the SSOT role baseline, only add context |

### P2 — experimental

| ID | Insight | Why experimental |
|---|---|---|
| P2-1 | Item spike to first fight ("Your Blink landed at 21:40; your next kill or assist came 40 s later") | Heavy-tailed gap; year-level estimand already changed between census median and ranking mean; item tiering needed |
| P2-2 | Death clustering ("three times you died again within 90 s") | Outcome-leaky (win-gap 0.53–0.60 SD); the 90 s gap includes respawn time, so it is mechanically rarer late-game |
| P2-3 | Bought-but-barely-used items (`itemUsed` counts) | No timestamps; whether passive items register is unverified |
| P2-4 | Skill/talent build deviation on a hero | `abilities` semantics unverified; value unclear |
| P2-5 | Rune pickups versus usual | Rune enum partially known; low interest |
| P2-6 | Party context for the session | `partyId` null ≠ solo; strongly confounded; only as neutral context |

### Reject

| Candidate | Reason |
|---|---|
| Enemy/allied stacking *accelerated* their cores | The causal link stays rejected. *(Corrected: the stack and farm-source facts are collectable — see ten-player document.)* |
| Map control / vision war | No movement; what anyone saw is unobservable. *(Corrected: ward placement/removal per team and death positions are collectable.)* |
| Time dead | *(Corrected: `deathEvents.timeDead` exists; moves to "blocked on collection + validation".)* |
| Control / stuns | No attributable duration (SSOT UNSUPPORTED) (D) |
| Roshan / Aegis stories | Not collected; playback Roshan events unreliable (D) |
| Fatigue / deterioration across session | Measured null; unpowered (§5) |
| Improvement across session | Same measurement |
| Tilt, frustration, resilience | Psychological inference; not observable |
| Composite "performance score", "deserved to win", "unlucky loss" | Judgement disguised as measurement; AGENTS.md forbids fabricated analytical meaning |
| Teammate blame ("your carry had the lowest net worth") | Data exists; product harm and unobserved context |
| Rank/MMR movement as explanation | Fenced display-only by owner decision |
| `analysisOutcome`, `winRates`, IMP, awards | Forbidden proprietary outputs |
| APM | Quarantined hidden-skill proxy |
| `invisibleSeconds` stories | Semantics unknown |
| Fight conversion per match | τ=0.0087, reliability 0.257, modal-sign share 1.000 (restates the result) |
| Post-loss requeue speed / hero switch as session insight | Year-level reliability 0.38–0.46; tilt connotation |
| Mid lane net-worth advantage and Offlane lane pressure @10 | **Blocked** (not rejected): opponent trajectory not collected |
| Mid early fight presence, Offlane objective involvement | **Blocked**: fields only in unmerged candidate query |

---

## 5. Session-level story catalog

### 5.1 What a session looks like (Pass-1 history, 552 accounts)

| Session length | Share of sessions | Share of matches |
|---|---:|---:|
| 1 | 26.7% | 7.5% |
| 2–3 | 37.8% | 25.7% |
| 4–6 | 22.7% | 30.3% |
| 7–9 | 7.5% | 16.5% |
| 10+ | 5.3% | 19.9% |

Session = gap > 3 h between one match's end and the next start (existing
`SESSION_GAP_SECONDS`; the tournament swept 2–6 h with per-player agreement
ρ ≥ 0.973). Median in-session gap 8 minutes. Median account: 172 sessions per
year. 6.5% of sessions mix Standard and Turbo. 68.7% of sessions are fully
parsed. Role changes between consecutive matches 48.0% of the time.

**Implication:** a quarter of sessions are a single match, and two-thirds of
sessions are three matches or fewer. The match-level catalog carries most of
the product; session stories are the reward for longer sessions.

### 5.2 Retained session stories

| ID | Story | Example | Gate | Type |
|---|---|---|---|---|
| S1 | Records collected | "2 personal bests tonight: CS at 10:00 (Carry) and observer uptime (Support)." | ≥1 PB in session | Fact |
| S2 | Consistent direction | "All 4 Support games: first ward earlier than your usual." | P0-4 gate | Pattern |
| S3 | Standout match | "Game 3 had your best early game as Offlane in a month." | One match holds ≥2 favourable extremes or a PB + extreme | Observation |
| S4 | Result versus early game | "0–4 tonight, but your 10-minute numbers were at or above your usual in 3 of 4." | Winless or all-win session; ≥3 matches in role; P0-4-style gate on *early-window* metrics only | Pattern (never "you played well") |
| S5 | Focus result | "Focus met in 3 of 4 attempted games." | Active challenge | Fact |
| S6 | Where games turned | "3 of your 4 losses turned after 25:00." | ≥3 losses with lead data | Pattern of game state |
| S7 | Quiet session | "Five games, nothing far from your usual." | Nothing above gates | Honest default |

Context line, not a story: "5 games · 3 roles · 5 heroes · 2 still processing."

### 5.3 Rejected session stories

| Story | Evidence against |
|---|---|
| Fatigue / deterioration | Mean player-SD by game index within ±0.05 for CS@10, net worth @10, deaths before 10, deaths per 10 min, fight presence, deaths-in-quiet-minutes, first ward (8,843 sessions ≥4 games, 49,550 role observations). Second half versus first half ≤0.03 SD. A per-session test needs an effect of ~1 SD to be visible in 5 games. |
| Progressive improvement | Same measurement |
| Recovery / resilience after losses | Outcome sequence plus psychology; year-level post-loss families are the weakest in V7 |
| Unlucky-looking loss | No luck estimand |
| New emerging tendency | Needs ≥20 versus ≥20 observations; belongs to a weekly "trend" surface, not a session |
| Losing streak despite good underlying performance | Requires a composite judgement; replaced by S4 with named dimensions |
| One anomalous match | Kept only as S3 with named metrics, not "anomalous game" |

### 5.4 Availability in the Pass-2 corpus (parsed, single-bucket sessions)

| Session length | n | ≥1 PB | ≥1 favourable extreme | No role-metric signal at all |
|---|---:|---:|---:|---:|
| 1 | 12,760 | 9.9% | 18.4% | 69.6% |
| 2–3 | 13,438 | 20.8% | 38.0% | 43.0% |
| 4–6 | 6,032 | 35.7% | 58.8% | 20.7% |
| 7+ | 2,348 | 49.7% | 78.5% | 6.5% |

"Favourable extreme" here used |robust z| ≥ 2 against prior 20, which is looser
than the proposed rank rule; production rates will be lower.

### 5.5 Ranking stories

Selection is a two-stage process: hard gates, then a score.

**Hard gates** (any failure removes the candidate):

1. required data present and semantics validated;
2. minimum history met for the claim's wording;
3. effect above the metric's minimum meaningful difference;
4. chance control met (rank extreme, pattern probability);
5. hero-dominated metric not compared at role level;
6. copy template exists for the claim type.

**Score** (all factors in [0, 1], multiplied):

```text
score = magnitude × rarity × confidence × relevance × salience × (1 − redundancy) × novelty
```

| Factor | Operational definition |
|---|---|
| magnitude | effect ÷ (effect + metric MMD × 3), so it saturates |
| rarity | 1 − empirical frequency of this story type for this player over the last 30 recaps |
| confidence | 1.0 for facts; for observations `min(1, prior_n / 20)`; for patterns 1 − chance probability |
| relevance | 1.0 if metric belongs to effective role or the active focus; 0.6 otherwise |
| salience | fixed per type: PB 1.0, swing 0.9, focus 0.9, pattern 0.85, early-window 0.8, other 0.6 |
| redundancy | 1.0 if another selected card shares a redundancy group; else 0 |
| novelty | 0.5 if the same type + metric was shown in either of the last two recaps and is not a new record |

Weights are product choices to be tuned with user research, **not fitted to win
rate**. Actionability is deliberately excluded from match/session ranking; it
belongs to challenge selection (§8).

Redundancy groups: *economy* (CS@10, CS 10–20, NW@10, NW@20, jungle share),
*deaths* (deaths before 10, quiet-minute deaths, clustering), *vision*
(first ward, wards per 10, uptime, dewards), *fight share* (fight presence,
damage share, tower share), *team state* (swing, comeback, lane vs game),
*records* (PB), *focus*.

Selection: up to 3 cards; at most 1 per group; at most 1 unfavourable
observation per recap (consistent with the V7 experience principle of one
criticism scene); win/loss is a context label, never a sort key.

---

## 6. Losing-session and negative-session opportunities

### 6.1 How often it happens

From Pass-1 history: winless sessions are 10.6% of three-match sessions, 4.9%
of four, 2.5% of five, 1.2% of six, and 0.2% of seven or more. A true 0–5 night
is rare but emotionally loud.

### 6.2 What is supportable

| Situation | Supportable? | Evidence |
|---|---|---|
| PB during a loss | **Yes, fact** | 7.4% of losses contain an SSOT role-metric PB |
| Challenge progress during losses | **Yes, fact** | Focus metrics are evaluated per attempted match regardless of result |
| One strong match inside a losing session | **Yes, observation on named metrics** | S3 |
| Early-game numbers held up while results fell | **Yes, pattern with S4 gate** | Early-window metrics have lower outcome linkage (win-gap 0.23–0.38 SD) |
| "Losing despite individually strong metrics" | **Only per named metric**, never as a verdict | See 6.3 |
| Unusual resilience / recovery | **No** | Psychology; not observable |
| Improvement in a tracked dimension while results declined | **Only as a multi-session trend**, ≥20 vs ≥20 | Not a single-session claim |

### 6.3 The adversarial truth about positives in losses

- Favourable extremes appear in **21.7% of losses** and **23.2% of all
  matches**. A loss is almost as likely as any match to contain one.
- Winless three-match sessions contained a PB or favourable extreme in 51.2%
  of cases; winless 4–6-match sessions in 61.9%. With a ~23% per-match rate for
  favourable extremes alone, chance predicts at least ~54% for three matches
  and ~65% for four.

So the positives are **true and personal, but not evidence that the player
secretly played well**. They are exactly as likely as in any other session.
Copy must therefore state the fact and stop:

- Good: "0–5 tonight. Your CS at 10:00 was at or above your usual in 4 of 5."
- Bad: "Tough night, but you actually played great."
- Bad: "Your team let you down."

### 6.4 The quiet negative session

When nothing clears the gates, say so plainly and move forward:

> "0–4 tonight. Nothing far from your usual in these games. Your focus carries
> over to next session."

The V7 experience plan already names this principle: *omission must read as
editing*, and *ordinary is a valid year*. The same applies to a night.

---

## 7. Personal-baseline methodology

### 7.1 What is locked (SSOT, unchanged)

- Identity: `progression_bucket + effective_role + metric_id + metric_version`.
- Recent baseline: median of the latest 20 previous eligible measured
  observations; ≥5 required.
- PB: all known eligible history for the identity, strict inequality, on
  `comparison_value`.
- Buckets Standard / Turbo fully isolated; duration ≥600 s; integrity fails
  closed; N/A never zero.
- Role correction rebuilds affected same-bucket history; delivered
  celebrations are immutable.
- Patch change does not reset history.

### 7.2 What the insight layer adds (proposal, non-normative)

| Need | Proposal | Why |
|---|---|---|
| "Unusual" wording | Rank within previous 20 (top/bottom 1 of 21) **and** above minimum meaningful difference; ≥10 prior | Controls chance at ~5% per metric-side; median-20 alone has no notion of spread |
| "Record" emphasis | PB truth per SSOT from 5 prior; presentation score scaled by `min(1, prior_n/20)` | PB rate at 5–9 prior is 14× the rate at 50+ |
| Session baseline | Freeze each identity's baseline at the session's first match | Prevents session games contaminating each other's reference |
| Trend (weekly, not per match) | Median of latest 20 versus previous 20, both ≥20, above MMD, permutation test | Emerging tendencies need volume |
| Hero | Not a default split (SSOT). Hero shown as context; hero-scoped comparisons only when ≥10 hero+role prior; hero-dominated metrics (Healing) suppressed at role level for insights | Healing η² 0.50; CS@10 0.18; Mid tower share 0.18 |
| Game mode | Bucket isolation is sufficient; do not pool | Only 51.6% of accounts have ≥20 matches in both buckets, so many users effectively live in one bucket |
| Lifetime versus recent | PB = all known; unusual = recent 20; trend = 20 versus 20 | Each answers a different question |
| Duration | Rate or checkpoint metrics only; N/A before checkpoint | Within-player correlation with duration ≤ |0.18| for all measured metrics |

### 7.3 Hindsight contamination

The current architecture is point-in-time by construction, provided three
rules are kept:

1. **Every comparison uses previous-only observations** ordered by the SSOT
   chronology key.
2. **Onboarding backfill replays chronologically**, producing historical
   snapshots as-of each match; it emits no celebrations (SSOT imported-history
   rule).
3. **Finalized snapshots are immutable** (Lifecycle SSOT); a later role
   correction or late recovery changes current truth without rewriting what
   the user was told.

Two residual contaminations must be disclosed in copy or design:

- "Best" means "best we have from you". Backfill depth is ~500 parsed matches;
  older matches do not exist in our history. Copy: *"best in the 180 Carry
  games we have"*, never *"best ever"*.
- Late-recovered matches can make an old record stale; the current record
  index updates but the old card is not rewritten (already locked).

### 7.4 User-corrected roles

Insight candidates must be computed from `effective_role`, never raw provider
position. A role correction invalidates unpublished insight candidates for the
affected match and the chronologically later matches in that bucket and role;
already-shown recaps remain in the ledger, optionally marked superseded.

---

## 8. Challenge-generation opportunities

### 8.1 Loop

```text
OBSERVATION (match)
  → PATTERN (≥2 sessions or ≥20-vs-20 trend, same role)
  → FOCUS CANDIDATE (safe metric, player's own gap)
  → ONE ACTIVE FOCUS (role-gated, process-based, own-baseline threshold)
  → EVALUATION (per attempted match: met / not met / couldn't measure / not attempted)
  → RETIRE, KEEP, OR SWAP (after ≥5 attempts)
```

### 8.2 Signal classification

| Signal | Class | Guardrail / reason |
|---|---|---|
| First observer ward time (Support) | **Safe** | Low outcome linkage; hard to game harmfully; guardrail: deaths before 10 |
| Observer uptime (Support) | **Safe** | Encourages replacement, not spam; guardrail: none needed beyond wards per 10 not exploding |
| Deaths in quiet minutes | **Safe** | Near-zero outcome linkage; guardrail: fight presence not collapsing |
| Level-6 time (Mid) | **Context-sensitive** | Could encourage stealing lane XP from allies; guardrail: team lane outcome |
| CS @10 (Carry) | **Context-sensitive** | Tunnel vision risk the product already flagged; guardrail: deaths before 10 and hero context |
| Deaths before 10:00 | **Context-sensitive** | Can reward passivity; guardrail: CS/NW @10 not falling |
| Camps stacked @20 | **Context-sensitive** | Can pull supports off lanes; guardrail: fight presence |
| Jungle share | **Context-sensitive** | No good direction; only as "take lane creeps when present" for players with extreme values |
| Net worth @10/@20 | **Dangerous / gameable** | Rewards greed and farm-over-team play |
| Fight presence | **Dangerous / gameable** | Rewards kill/assist chasing |
| Hero damage share | **Dangerous / gameable** | Rewards pointless damage |
| Tower damage share | **Dangerous / gameable** | Rewards split-pushing regardless of state |
| Healing | **Dangerous / gameable** | Rewards hero choice, not play |
| Any PB target | **Dangerous** | Records are celebrations, not quotas |
| Death clustering | **Not suitable (now)** | Outcome-contaminated (modal-sign 0.989) |
| Win rate, lane outcome, comeback, lead | **Not suitable** | Outcomes, not controllable behaviours |
| KDA, APM | **Not suitable** | Skill proxies / gameable |

### 8.3 Challenge design rules

1. One active focus at a time.
2. Evaluated only in matches of the target role and bucket; other matches read
   "not attempted", never failure.
3. Threshold anchored on the player's own baseline at focus creation (e.g.
   "earlier than your usual first ward" or a fixed process target such as
   "before 1:00"), not population norms.
4. Always paired with a guardrail metric; if the guardrail degrades beyond its
   MMD across ≥5 attempts, the recap says so neutrally and suggests swapping.
5. No streaks, no daily-completion pressure (V7 experience principle 6).
6. N/A (unparsed, too short) = "couldn't measure", not "missed".
7. The initial focus may be seeded from the existing year-level V7
   recommendation (7 eligible dimensions, 265 of 276 research players receive
   one), but note its winner `last_hits_at_ten` sits at modal-sign share
   0.9466, four thousandths below the contamination cut.

---

## 9. Insight ranking and selection architecture

### 9.1 Candidate object

```text
InsightCandidate
  candidate_id              deterministic hash(match/session, type, metric, version)
  scope                     MATCH | SESSION
  type                      PB | EARLY_WINDOW | SWING | PATTERN | FOCUS | QUIET_DEATHS | ...
  evidence_rung             FACT | OBSERVATION | PATTERN | HYPOTHESIS
  identity                  bucket, effective_role, metric_id, metric_version, hero_id?
  values                    current, baseline_median, prior_n, rank_in_window, record_value?
  effect                    signed delta, direction_delta, mmd, magnitude_ratio
  chance                    probability under the declared rule
  evidence_refs             match ids (internal), field provenance, detector_version
  redundancy_group
  copy_template_id
  slots                     typed values allowed in copy
  gates_passed / gates_failed
```

### 9.2 Flow

```text
detectors (deterministic, versioned)
  → hard gates (§5.5)
  → scoring (§5.5)
  → redundancy + novelty filters
  → selection (≤3 cards; ≤1 unfavourable; focus card always eligible)
  → template rendering (deterministic)
  → optional language polish (validated slots only)
```

### 9.3 What the LLM may and may not do

| May | Must never |
|---|---|
| Rephrase a selected, validated card within its template's meaning | Choose which insights to show |
| Vary tone within the tone-of-voice guideline | Compute, round differently, or introduce numbers |
| Join two selected cards into one sentence | Add a causal word ("because", "cost you", "led to") |
| Localise | Read raw payloads, trajectories, or other players' data |
| | Introduce judgement (good/bad game, deserved, unlucky, tilt) |
| | Fill a missing card when detectors produced nothing |

Every LLM output is post-validated: all numbers must equal slot values; a
forbidden-lexicon check runs; any failure falls back to the template. **V1
should ship with templates only.**

---

## 10. Statistical methodology (plain-language)

### 10.1 "Your usual"

Your usual is the **middle value of your last 20 games** in the same role and
mode. The middle value (median) ignores one freak game in a way an average
does not.

### 10.2 "Unusual for you"

We say a number was unusual only when two things are both true:

1. **It is at the edge of your last 20 games** — higher than all 20, or lower
   than all 20 (or top/bottom 2 for longer histories). By pure chance this
   happens about 1 time in 21 per metric per side.
2. **The difference is big enough to matter** — larger than a *minimum
   meaningful difference* for that metric.

Why not "2 standard deviations"? Because it fired far too often: tried on the
corpus, 32.6% of matches had at least one flag, and heavy-tailed metrics (first
ward time, level-6 time, item timing) flagged 15–28% of the time on their own.

### 10.3 Minimum meaningful difference (MMD)

Each metric gets one MMD per bucket, set once from the corpus as **half of the
median within-player standard deviation**, then rounded to a readable unit and
frozen with the detector version. Example scale (to be computed, not assumed):
CS@10 in last hits, net worth in hundreds of gold, times in 15-second steps,
shares in 5-point steps.

### 10.4 How many things will look unusual by chance

If a role has 4 metrics and each has ~5% chance of an edge-of-window value on
the favourable side, the chance that **at least one** is favourable-unusual in
a match is about 1 − 0.95⁴ ≈ 19%. That is why at most one card per group is
shown, why the MMD exists, and why "nothing notable" is common.

### 10.5 Patterns across a session

"All of tonight's games went the same way" is only interesting if it is
unlikely by chance. With a 50/50 coin against your own median:

| Matches in role | Rule | Chance |
|---:|---|---:|
| 3 | 3 of 3 | 12.5% |
| 4 | 4 of 4 | 6.3% |
| 5 | 5 of 5 | 3.1% |
| 6 | ≥5 of 6 + session median outside your usual middle half | <5% |
| 8 | ≥7 of 8 | 3.5% |

For three games the pattern also needs the session median beyond the prior
interquartile range.

### 10.6 Why we do not claim fatigue or improvement within a session

Measured across 8,843 sessions of four or more games, the average change by
game number was under 0.05 of a player's normal spread. To see a change inside
one five-game session we would need a change of about one full spread. The
signal is not there, so the story is not offered.

### 10.7 Trends over weeks

"Something changed" compares your **latest 20** with the **previous 20** in the
same role and mode, requires the medians to differ by more than the MMD, and
uses a simple permutation test (shuffle the 40 values many times; how often is
the difference this big?). Checked weekly, not after every game.

### 10.8 Recency weighting

Not needed. The 20-game window already makes "your usual" recent. Exponential
weighting would add tuning parameters without improving reliability at this
sample size.

### 10.9 Outcome leakage

Some metrics move with winning and losing and therefore restate the result.
Measured median win-versus-loss gap in player-SD units:

| Metric | Gap | Use |
|---|---:|---|
| deaths per 10 min | 0.99–1.12 | fact only; never "hidden strength/weakness" |
| net worth @20 | 0.63–0.72 | same |
| death clustering | 0.53–0.60 | same |
| CS @10 / NW @10 / tower share (Carry) | 0.28–0.38 | usable with care |
| level-6 time / hero damage share | 0.23–0.25 | usable |
| observer wards per 10 / uptime | 0.07–0.15 | good |
| deaths in quiet minutes | 0.00–0.09 | good |
| camps @20 / Support fight presence | ≈0.00 | good |

### 10.10 Hero confounding

Share of within-player, within-role variance explained by hero:

| Metric | η² |
|---|---:|
| Support healing per 10 | **0.50** |
| Carry CS 10–20 | 0.22 |
| Mid tower share | 0.18 |
| Carry CS @10 | 0.18 |
| jungle share | 0.11–0.14 |
| Carry hero/tower share | 0.10–0.11 |
| NW @10/@20 | 0.06–0.09 |
| deaths in quiet minutes | ≤0.01 |

Anything above ~0.15 needs hero context on the card; above ~0.3 needs a
hero-scoped comparison or suppression.

### 10.11 What we deliberately do not use

Population percentiles, significance against the population, Bayesian
shrinkage toward a population mean, composite scores, or strength bands. The
V7 cut-point dry run already showed per-player intervals are wider than any
band width.

---

## 11. Proposed technical pipeline

```text
STRATZ
  │  GetPlayerHistoryPage (discovery; cheap)        — exists, v1
  │  GetDeepMatchBatch (≤8 matches/request)          — exists, v3.4.0
  │  GetRoleMetricMatchBatch (SSOT extras)           — candidate branch only
  ▼
Immutable raw payload store (per match, per operation digest)   — NOT BUILT
  ▼
Provider-native normalization (stratz/deep.py)                  — exists
  ▼
Canonical match record + validated semantics adapter
  (pass2_tables rules; time-aligned checkpoint adapter)         — partial: checkpoint adapter NOT BUILT
  ▼
Eligibility + effective_role (Lifecycle + Role Metrics SSOT)    — role resolution NOT BUILT
  ▼
Deterministic metric calculators (SSOT registry, versioned)     — 5/20 on candidate branch
  + insight-only derived values (swing window, quiet deaths,
    uptime, farm mix, lane vs game)                              — helpers exist in research modules
  ▼
Observation history store (bucket+role+metric+version)          — NOT BUILT
  ▼
Baseline + PB engine (median-20, all-known PB, rank-in-window)  — candidate in-memory only, conflicts
  ▼
Match detectors → InsightCandidates                              — NOT BUILT
  ▼
Session aggregator (3 h gap, frozen session baselines)           — session helper exists (tables.iter_sessions)
  ▼
Session detectors → InsightCandidates                            — NOT BUILT
  ▼
Gates → scoring → redundancy/novelty → selection                 — NOT BUILT
  ▼
Template renderer (+ optional validated LLM polish)             — NOT BUILT
  ▼
Recap snapshot (immutable, versioned, provenance)               — NOT BUILT
  ▼
Mobile API payload (cards, context line, processing state)      — NOT BUILT
```

Every layer carries a version: operation digest, adapter version, metric
versions, detector version, selection-policy version, template version.

---

## 12. Incremental update strategy

### 12.1 When one new match arrives

1. **Discovery** finds the match (history page; already durable-cursor
   specified).
2. **Provider wait** until parsed; the Lifecycle SSOT handles bounded waiting.
   Unparsed-forever matches become UNAVAILABLE or NONE for parsed-dependent
   outputs.
3. **Acquire** one deep batch (≤8 matches per request).
4. **Compute** SSOT metrics and insight values — milliseconds.
5. **Wait for predecessor** in the same bucket (SSOT chronological ordering).
6. **Append** observations to each identity history; update the rolling
   20-value window (constant work) and the PB index (constant work).
7. **Run match detectors** against the as-of-before-this-match state.
8. **Update the open session** for the account: add the match; recompute
   session detectors over the session's matches only (≤ tens of matches).
9. **Finalize** the match snapshot; the session recap stays *provisional* until
   the session closes (3 h without a new match) or the user views it.
10. **Notify** once per coalesced ready set (Lifecycle SSOT).

Nothing else is recomputed. Per match: one or zero provider requests, a few
milliseconds of compute, a few hundred bytes of new observation rows.

### 12.2 Provisional versus final session recaps

A player often opens the app minutes after their last game, while matches are
still parsing (≈half parse within 15 minutes). The recap therefore has two
states:

- **Provisional:** shows cards from READY matches plus "2 games still
  processing". Cards already shown are never retracted by later matches.
- **Final:** after the session closes and all matches are READY, UNAVAILABLE,
  or NONE. Session-level stories (patterns) can only upgrade the recap, never
  contradict shown cards.

### 12.3 When full recomputation is preferable

| Trigger | Scope |
|---|---|
| New metric version | Rebuild that metric's histories for all accounts offline; old snapshots unchanged |
| New detector or MMD version | Recompute future candidates only; optionally backfill *current* trend state |
| Role correction | SSOT-scoped rebuild: same bucket, old and new role, later matches |
| Late recovery | No rebuild of later snapshots (SSOT); current indexes update |
| Adapter/semantics bug fix | Controlled offline rebuild with a new adapter version and an audit record |
| Onboarding backfill | Chronological replay of ~500 matches; no celebrations |

---

## 13. Data and engineering gaps

| Gap | Needed for | Kind | Cost |
|---|---|---|---|
| Time-aligned checkpoint adapter with acceptance tests | CS@10, NW@10/20, Camps@20, every early-window card | Validation + code | Cheap |
| Resolve candidate conflicts: median, @20 camps, 600 s gate, effective_role input, all-known PB | Everything progression-based | Code | Cheap |
| Remaining 15 SSOT calculators | P0-1, P0-2 | Code | Cheap–medium |
| Effective-role resolution + confirmation UX contract | All role-scoped insights; unparsed matches | Design + code | Medium |
| Raw/canonical per-match persistence and observation history store | Everything | Build | Medium |
| Baseline/PB engine with persistence and rebuild | P0-1, P0-2, P0-4 | Build | Medium |
| Detector library, gates, scorer, selector, templates | All cards | Build | Medium |
| Session aggregator with frozen baselines and provisional/final states | Session stories | Build | Medium |
| MMD computation per metric per bucket | Gates | Offline analysis on existing corpus | Cheap |
| Opponent `networthPerMinute` (two players) | Mid/Offlane lane metrics | **New collection + complexity probe** | Medium; complexity unknown |
| `allPlayers.stats.killEvents`, `towerDamageReport` | Mid early fight presence, Offlane objective involvement | New collection (query exists on candidate branch) | Low–medium; fits batch 8 per probe |
| Ten-player `campStack` | Any opposing/allied stacking fact | New collection + probe | Unknown complexity |
| Leaver/integrity enum mapping | Eligibility | Validation | Cheap |
| Lane-outcome method understanding | P1-2 trust | Research | Cheap |
| Validation of insight-copy comprehension | Trust | User research | Medium |
| Stale `docs/progression/` SSOT copy | Contract hygiene | Docs | Trivial |

Cannot be derived from the existing payload under any design: positions, time
dead, stun/control, Roshan timing, other players' timelines, decision quality.

---

## 14. Cost and performance considerations

| Item | Measurement / estimate |
|---|---|
| Provider limits | 8/s, 150/min, 1,500/h, 15,000/day (clock-aligned headers) |
| Deep batch | 8 matches per request; ~14.4 KB response per match |
| Onboarding backfill | ~45 requests per account (measured in Pass-2); ≈333 first-time users/day on one key |
| Ongoing per active player | ~1 history call per app open + ~1 deep call per 8 new matches → typically 2–3 requests per play day |
| Raw storage | ~14 KB/match uncompressed ⇒ ~7 MB for a 500-match backfill; ~10–15 MB per heavy player-year before compression |
| Compute | Per-match metrics and detectors: milliseconds; session recompute: tens of matches; weekly trends: 40 values per identity |
| Expensive additions | *(Corrected: full ten-player `stats` is feasible — ~110 KB/match with rich events, 8 matches per request.)* Match playback is one match per request and fresh-only; the movement stream (~4.6 MB/match) stays prohibited |
| Cheap additions | Narrow ten-player fields shown to fit (kill events); SSOT query extras |
| LLM | Optional; ≤1 KB of validated slots per recap; no raw payloads; template fallback keeps cost at zero |
| Offline work | MMD table, detector validation on corpus, periodic trend backfills |

---

## 15. Failure modes and misleading interpretations (adversarial pass)

For each family: how the conclusion could be wrong, what the corpus says, and
the resulting disposition.

| Family | Attack | Evidence | Disposition |
|---|---|---|---|
| Personal Best | Early-history inflation | PB rate 11.1% at 5–9 prior vs 0.8% at 50+ | Keep; presentation scaled by history |
| Personal Best | Hero confounding | Healing η² 0.50 | Suppress Healing PB cards at role level; keep SSOT record |
| Personal Best | Low-count ties | Camps median 0 | Absolute floor for highlight |
| Personal Best | History truncation | ~500-match backfill | "best we have" copy |
| Personal Best | Patch changes | No reset by SSOT | Annotate records set in the first week of a large patch (proposal) |
| Early window | Role confounding | Role changes 48% between session games | Strict effective-role identity |
| Early window | Lane matchup / draft | Unobserved | Observation wording only |
| Early window | Checkpoint misalignment | Array offset unresolved | Block until adapter validated |
| Early window | Win/loss leakage | 0.23–0.38 SD | Acceptable; never used as a verdict |
| Swing window | Stomp bias | One-sided games (never trailed/led by >1k, max margin ≥10k): 25.0% of Standard matches are one-sided wins, 22.2% one-sided losses | No swing card when the lead never changed sides meaningfully; use a one-sided fact instead |
| Swing window | Turbo scale | Swings far larger in Turbo | Bucket-specific floors |
| Swing window | Implied blame | Team-level | Neutral copy, no personal attribution |
| Session pattern | Small n | 3-game patterns ~12.5% chance | Require all-same plus IQR condition |
| Session pattern | Multiple metrics tested | ~4 metrics per role | ≤1 pattern card per session |
| Session pattern | Regression to mean | Baseline may be depressed by a bad week | Freeze session baseline; median-20 dampens |
| Quiet-minute deaths | Proxy definition | Minute granularity; ≥2-kill threshold | Copy describes exactly what was measured |
| Quiet-minute deaths | Few deaths | Values like 1/2 | ≥4 deaths per match |
| Lane vs game | Provider label opacity | Undocumented method | P1 not P0; label named as STRATZ lane result |
| Comeback record | Survivorship: only parsed matches | 27.6% of Turbo unparsed | "of the games we could analyse" |
| Uptime | Upper-bound estimate | Dewards not applied | "placed-ward time" |
| Farm mix | Missing ancient/bounty gold | Traded away in query | Neutral framing only |
| Damage/tower share | Teammate dependence; Mid tower share higher in losses | Win-gap −0.24 | No "good game" framing |
| Positives in losses | Chance-level rate | 21.7% vs 23.2% | Modest factual copy |
| Session fatigue | Everything | Null effect | **Removed** |
| Any claim | Rank/MMR leakage | Rank fenced; no rank field in analysis | Keep fence |
| Any claim | Turbo vs Standard pooling | Isolated buckets | Keep isolation |
| Any claim | Unparsed matches | Sessions 68.7% fully parsed | Provisional states; never infer missing matches |
| Any claim | User-corrected roles | Rebuild rules | Invalidate unpublished candidates |
| Any challenge | Gaming / distortion | See §8.2 | Only Safe or guarded Context-sensitive signals |

Downgrades applied in this pass: death clustering P1→P2; Support healing
removed from role-level insight cards; lane-vs-game held at P1; fatigue,
improvement, resilience, and unlucky-loss stories removed.

---

## 16. Recommended V1

The smallest set that should already feel magical. Match and session.

**Match cards (choose ≤3):**

1. **Personal Best** on SSOT role metrics that are implemented and not
   hero-dominated (P0-1).
2. **Early-window versus your usual** for the effective role, rank-extreme +
   MMD gated (P0-2).
3. **Swing window** with towers lost/taken inside it (P0-3).
4. **Quiet game** state when nothing clears gates.

**Session recap (sessions ≥2 matches):**

5. **Records collected** (S1).
6. **Same-direction pattern** on early-window metrics only (P0-4 / S4).
7. **Focus check** (P0-5 / S5), with one Safe focus metric per role:
   Support first observer time, Carry CS@10 with deaths-before-10 guardrail,
   Mid level-6 time with lane-result guardrail, Offlane deaths-in-quiet-minutes.

**Data prerequisites for V1 (no new STRATZ collection):**

- validated time-aligned checkpoint adapter;
- SSOT calculators for CS@10, CS 10–20, NW@10/@20, level-6 time, wards per 10,
  dewards per 10, Camps@20, fight presence, damage/tower share;
- persistence of observations, baseline/PB engine, session aggregator;
- MMD table computed offline from the existing Pass-2 corpus.

**Explicitly not in V1:** LLM narration, hero-scoped comparisons, trends over
weeks, lane-vs-game card, comeback record, farm mix, uptime, and anything
requiring new collection.

---

## 17. Example outputs

Values are hypothetical but inside observed corpus ranges. Each card ≤2 short
lines.

### Strong win — Carry, Standard

> **Record** · Best CS at 10:00 in the 143 Carry games we have: **74**.
>
> **Early game** · You reached 10:00 with 4.1k net worth — higher than all of
> your last 20 Carry games.
>
> **The swing** · Your team went from −1.2k to +9.6k between 16:00 and 24:00,
> taking 5 towers.

### Ugly win — Support, Turbo

> **Came back** · Your team was 9.8k behind at 14:00 and won.
>
> **Below your usual** · Your first observer went down at 4:10. Your usual is
> 0:40.

### Close loss — Mid, Standard

> **Early game** · Level 6 at 5:02 — your fastest in 20 Mid games.
>
> **The swing** · Even at 30:00. Your team fell 7.4k behind between 31:00 and
> 38:00 and lost two barracks in that stretch.

### Stomp loss — Offlane, Standard

> **One-sided** · Your team trailed from 6:00 onward and never led.
>
> **Deaths** · 5 of your 7 deaths came in quiet minutes — neither team got 2+
> kills.

### 0–5 session with genuine positives — Carry, Standard

> **Tonight** · 0–5 · Carry in 4 of 5.
>
> **Held up** · Your CS at 10:00 was at or above your usual in all 4 Carry
> games.
>
> **Record** · Game 2: best CS from 10:00 to 20:00 in 90 Carry games.

### One-match session — Support, Turbo

> **Record** · 5 camps stacked by 20:00 — the most in any Support game we have
> from you.

### 8-match session — mixed roles, Turbo

> **Tonight** · 5–3 · Support ×5, Offlane ×3 · 1 still processing.
>
> **Pattern** · In all 5 Support games your first observer went down earlier
> than your usual.
>
> **Records** · 2 personal bests: observer wards per 10 min (Support), net
> worth at 10:00 (Offlane).

### Challenge success

> **Focus met** · First observer before 1:00 in 4 of 4 Support games.
> Earliest: 0:12.

### Challenge failure

> **Focus** · First observer before 1:00 in 1 of 3 Support games. Two games as
> Mid didn't count.

### No meaningful insight detected

> **Tonight** · 2–1 · Mid ×3.
>
> Nothing far from your usual in these games. Your focus carries over.

---

## 18. Final recommendation

**Is this technically feasible?** Yes, for personal observations, records,
game-state facts, and conservative session patterns. Every V1 input is already
collected by `GetDeepMatchBatch` v3.4.0 and has verified or verifiable
semantics. The missing work is engineering (checkpoint adapter, calculators,
persistence, baselines, detectors, selection), not data acquisition.

**Is it differentiated enough to be a core hook?** Yes, if the product keeps
its promise of fewer, truer cards. "Best 10-minute CS in 143 Carry games" and
"the game turned between 18:00 and 26:00" are genuinely not visible from the
scoreboard. It stops being differentiated the moment it becomes a stat wall or
starts explaining losses it cannot explain.

**What is the hardest part?** Chance and confounding. A third of matches will
look "unusual" under naive rules; hero choice drives some role metrics; a
quarter of Turbo matches never parse; and sessions fragment across roles.
The product must be comfortable saying "nothing notable" often.

**What to prototype first?**

1. Offline, on the existing Pass-2 corpus: the checkpoint adapter, the MMD
   table, and the three V1 match detectors with gates. Measure per-match and
   per-session card rates, and read 50 randomly sampled recaps by hand for
   "would a player care?" before any UI.
2. Then the persistence + baseline/PB engine per the SSOT batches C–F.
3. Then provisional/final session recap states against real parse latency.

**What not to build yet?**

- LLM narrative generation;
- causal or "why you lost" explanations;
- fatigue, tilt, resilience, improvement-within-session stories;
- composite performance scores or "you played well" verdicts;
- teammate comparisons;
- enemy-behaviour stories (stacking, vision) before the ten-player validation
  corpus runs — then only as facts and opponent-history observations (see
  [Ten-Player Match Intelligence V1](ten-player-match-intelligence-v1.md));
- trend detection before users have 40 role-scoped games;
- new STRATZ collection for V1.

---

## Appendix A — Evidence method

All figures were computed on 2026-09-14 by read-only scratch scripts (not
committed) over:

- `.local/corpora/stratz/v7-pass2-2026-09-04/canonical/v7p_*.json` —
  `split == DISCOVERY` only; semantics via imported
  `pass2_tables.team_lead_curve`, `deaths_alone_share`, `own_team_tower_kills`,
  `lane_vs_jungle_gold`, and `pass2_features` lane mapping and first-real-item
  helpers.
- `.local/corpora/stratz/v7-pass1-history-new-lineage-2026-09-07/canonical/history/v7p_*.json`
  — `split == DISCOVERY`, `in_window`, leaver `NONE`, Standard/Turbo only.

Definitions used:

- **Eligible match:** Standard (All Pick ranked/unranked lobby) or Turbo;
  leaver `NONE`; duration ≥600 s; `numHumanPlayers == 10`.
- **Role proxy:** provider position (Positions 4/5 merged). This is *not* the
  SSOT `effective_role`; it is the only proxy the corpus contains.
- **Checkpoint approximations:** CS@10 = sum of first 10 `lastHitsPerMinute`
  entries; NW@k = `networthPerMinute[k]`; Camps@20 ≈ `campStack[19]` for
  matches ≥1,200 s. These are approximations pending the validated adapter.
- **PB rate:** strict running best within the ≤500-match window, after ≥5
  prior observations in the same account + bucket + role.
- **Unusual (exploratory):** |x − median(prior 20)| / (1.4826 × MAD) ≥ 2, ≥10
  prior. This rule is *not* recommended; it was used to measure how often naive
  flags fire.
- **Win-gap:** per player with ≥5 wins and ≥5 losses, (mean win − mean loss) /
  player SD, signed so positive = favourable in wins; median across players.
- **Hero η²:** between-hero sum of squares over total sum of squares of
  within-player-role residuals, heroes with ≥10 observations.
- **Session:** gap >3 h between end and next start; Pass-2 session analyses use
  parsed eligible matches within one bucket.
- **Fatigue test:** per player-role z-score (player mean/SD over ≥20 matches),
  averaged by game index within sessions of ≥4 matches.
- **Parse latency:** `parsed_at − ended_at` over Pass-1 history rows.

Limitations: research cohort is active and public; Pass-2 is ≤500 most recent
parsed matches per account (PB histories truncated); the role proxy is not the
product role; checkpoint indices are approximate; parse latency may be
overstated by re-parses.

## Appendix B — Conflicts and hygiene issues found

1. `docs/progression/role-metrics-and-baselines-v1.md` is an older SSOT copy
   without `progression_bucket` in the identity; `#swiftMigration/` holds the
   current version.
2. Candidate branch `d691008`: mean baseline, final-value Camps Stacked,
   300 s duration gate, provider-position role mapping, prior-20 PB scope —
   all already recorded in the SSOT as conflicts; still unresolved.
3. SSOT Mid and Offlane lane net-worth-advantage metrics depend on opponent
   trajectories no existing query requests.
4. Support Healing is ~50% hero-determined at role level; the locked metric is
   valid but its deltas and PBs will mostly reflect hero choice. Owner decision
   recommended on whether to keep it as a role metric, hero-scope it, or
   version it.
5. `pass2_tables.deaths_alone_share` treats a minute as quiet unless either
   team scored ≥2 kills in it, so a death plus one other kill is still "alone".
   The docstring's "no team kill activity" description is looser than the code;
   user-facing copy must match the code or the helper must be versioned.
6. `v7-backend-capability-manifest.md` §0.4 describes parsed coverage limits as
   research-only; Turbo parse availability (72.4%) makes it a product limit.
