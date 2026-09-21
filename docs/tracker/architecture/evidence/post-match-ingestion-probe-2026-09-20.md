# Post-match ingestion architecture — evidence-based recommendation (V1)

Date: 2026-09-20. All TESTED claims come from live probes run today.
Probe workspaces (local, not committed):
`/private/tmp/claude-501/.../scratchpad/probe` (OpenDota) and `.../scratchpad/stratz` (STRATZ, 99 calls, ledger.jsonl).

Evidence tags: **TESTED** = measured today by direct API call. **VERIFIED** = read today from
the vendor's own page/spec. **INFERRED** = derived from measurements. **UNKNOWN** = needs a
question to the vendor.

---

## 1. Executive recommendation

**Build OpenDota-first for everything fresh, STRATZ-first for everything historical, and never
let either be the detection mechanism for the other.**

Concretely:

| Layer | Source | Cost | Latency |
|---|---|---|---|
| New-match detection + instant card | OpenDota `GET /players/{id}/recentMatches` | 1 call, 8.6 KB | match visible **T+3 min** |
| Full ten-player summary | OpenDota `GET /matches/{id}` | 1 call, 17 KB | same instant, no parse needed |
| Deep post-match analysis | OpenDota `POST /request/{id}` then `GET /matches/{id}` | 2 calls, 200 KB | **T+6.5 min, 10/10 success** |
| Population baselines | STRATZ `heroStats.stats` / `laneOutcome` | ~5 calls/week, not per match | n/a |
| Historical backfill (deep) | STRATZ `player.matches` aliased pages | **300 deep matches per call** | seconds |
| Rank/bracket, `imp`, `position`/`role` labels | STRATZ | folded into the backfill call | n/a |

Reasons, all measured today:

1. **OpenDota's forced parse is faster and far more reliable than waiting for STRATZ.** 10/10 freshly
   ended public matches were fully parsed on OpenDota at **6.2–7.1 min** after match end when we
   requested the parse ourselves. STRATZ's `statsDateTime` (its real replay-stats gate) landed at
   +11 min in one case, **+61 min** in another, and was **still null 45 min after match end** in a third.
2. **STRATZ does not see most fresh matches at all for many minutes.** 1/20 freshly ended public
   matches existed in STRATZ at T+5–11 min; 0/20 of the freshest cohort at T+12 min.
3. **OpenDota already returns, with zero parsing, everything the instant card needs** — including
   server-computed percentile `benchmarks`, full item slots, `ability_upgrades_arr`, `picks_bans`,
   tower/barracks status and `first_blood_time` — for all ten players, 3 minutes after the match ends.
4. **OpenDota is effectively free at our scale**: $0.0001/call, unlimited daily, 3,000 calls/min.
5. **STRATZ's real strength is history, not freshness**: one STRATZ call returns 300 fully
   detailed matches (3 aliased pages × `take: 100`), with 87–100% replay-stat coverage going back
   years — whereas OpenDota can only *newly* parse matches whose Valve replay still exists
   (works at 60 days, fails at 180/365/730 days, TESTED).

The current code's assumption — "every match requires STRATZ", STRATZ deep batches capped at 8
match IDs — is wrong on both counts and is the main thing to change.

---

## 2. Ideal post-match lifecycle

```
T+0:00   match ends
T+0:00   iOS app can show "match in progress / finishing" from local state only
T+2:54   OpenDota scanner has the match           (TESTED: min 2.4 min across 100 public matches)
T+3:24   /players/{id}/recentMatches returns it   (TESTED median od_basic 3.4 min, n=12)
         -> PUSH + card renders: hero, win/loss, KDA, GPM, XPM, LH, duration, lane_role,
            party_size, average_rank. ZERO extra API calls.
T+3:30   GET /matches/{id} (1 call) -> all 10 players' summary + benchmarks + items +
            ability build + draft + tower/barracks state
         -> Tier-1 analysis renders: role read, KDA/GPM/XPM/LH vs personal baseline,
            vs hero-population benchmark, item build, draft context, PB/record checks
T+3:30   POST /request/{id}  (1 call; counts as 10 against rate limit, 1 for billing)
         (before ~T+6 the Valve replay does not exist yet; the job silently no-ops — retry)
T+7:00   GET /matches/{id} -> version != null, full replay parse
         (TESTED over two independent cohorts: 21 of 22 fresh matches parsed between
          6.2 and 7.8 min after match end, median 7.1; once the replay exists the parse
          itself completes in ~23-25 s. In the same window STRATZ had ingested only
          3 of those 12 matches at all, and none had replay stats.)
         -> Tier-2 analysis renders: laning, net worth / XP / LH / DN timelines, item
            timings, ward log, stacks, objectives, tower timings, teamfights, kill and
            death logs, runes, damage breakdowns, positional heatmap
T+7:00   push "Your full breakdown is ready" (only if the user has left the app)
```

Backfill runs on a separate queue that never competes with this path (§10).

---

## 3. STRATZ findings

### 3.1 Rate limits — the published table is wrong for our token

**VERIFIED** (stratz.com/api, read 2026-09-20):

| | Default | Individual | Multi-Token |
|---|---|---|---|
| Calls/second | 20 | 20 | 20 per user |
| Calls/minute | 250 | 250 | 20 per user |
| Calls/hour | 2,000 | 4,000 | 50 per user |
| Calls/day | 10,000 | 20,000 | 100 per user |
| Required monthly referrals | – | 1,000 | 5,000 |
| Approval | none | application | application |

**TESTED** — what our token actually enforces, straight off the response headers:

```
x-ratelimit-limit-second: 8      x-ratelimit-limit-minute: 150
x-ratelimit-limit-hour: 1500     x-ratelimit-limit-day: 15000
```

So the live limits are **lower per second/minute and per hour** than every published tier, and the
daily limit (15,000) matches none of them. **Do not plan against the published table.** Plan against
headers, and read `x-ratelimit-remaining-*` on every response.

Also **TESTED**: the token is bound to one client IP; a rotating CGNAT address or two concurrent
jobs sharing the token produce `403 ... different IP Addresses`. Server-side use must come from a
stable egress IP, single-flighted.

### 3.2 Complexity — the decisive finding

Complexity cap is **310,000** per request (error text, TESTED).

**Complexity is computed from the shape of the selection set, not from `take`.** Proof:

* `CORE` shape, 5 player-aliases × `take: 20` → complexity **401,410**
* `CORE` shape, 4 player-aliases × `take: 100` → complexity **321,128**
* Both = **80,282 per player-alias**, identical regardless of `take`.

That single fact changes the economics of everything below.

### 3.3 Batching — measured

Three field profiles were used (exact documents in the probe workspace):

* `TINY` — match scalars + all 10 players' summary + items.
* `CORE` — `TINY` + per-player `stats` (`networthPerMinute`, `lastHitsPerMinute`, `campStack`,
  `itemPurchases`, `killEvents`, `deathEvents`) + `towerDeaths` + `radiantNetworth/ExperienceLeads`.
* `HEAVY` — `CORE` + `wards`, `heroDamageReport`, `farmDistributionReport`, `itemUsed`, `runes`.

| Route | Profile | Max per request | Bytes | Latency | Complexity/unit |
|---|---|---|---|---|---|
| Aliased `match(id:)` | TINY | **633** (200 TESTED ok; 700 → 342,300) | 4.1 KB/match | 1.5 s @200 | 489/match |
| Aliased `match(id:)` | CORE | **77** (77 ok, 78 → 313,170) | 25 KB/match | 1.4 s @60 | 4,015/match |
| Aliased `match(id:)` | HEAVY | **37** (30 ok, 40 → 331,560) | 35 KB/match | 1.0 s @30 | 8,289/match |
| `player.matches(take:100)` | CORE | **3 players × 100 = 300 matches** | 2.26 MB/player | 2.9 s | 80,282/player-alias |
| `player.matches(take:100)` | TINY | **≥30 players × 100 = 2,900 matches** | 11.7 MB | 3.0 s | ~9,780/player-alias |
| `player.matches(take:100)` | HEAVY | 1 player × 100 | 3.2 MB | 1.6 s | ~165,000/player-alias |
| `player.matches` aliased pages (`skip`) | CORE | **3 pages × 100 = 300 matches, 1 call** | 7.0 MB | 3.2 s | 80,282/page-alias |
| `player.matches` aliased pages | id-only | **30 pages × 100 = 3,000 matches, 1 call** | 206 KB | 0.9 s | — |
| **Our production `GetDeepMatchBatch`** | as-shipped | **1 player × 100 matches** | 1.09 MB | 1.2 s | 302,982/player-alias |

Hard constraints found:

* `take` is capped at **100** (`"You have surpassed the maximum take value of : 100"`).
* `player.matches` default `take` is **10** when omitted — our production query omits it, so
  `GetDeepMatchBatch` currently returns at most 10 matches no matter how many IDs you pass. **This is a live bug.**
* Root `matches(ids: [...])` now returns `"User is not an admin."` — **unavailable**, not merely expensive.
  (This corrects the older note that it cost ~770k complexity.)
* `PlayerMatchesRequestType` supports `matchIds`, `startDateTime`, `endDateTime`, `isParsed`,
  `skip`, `take`, `orderBy`, plus hero/lane/position/bracket filters — everything an incremental
  sync needs.

**Minimum STRATZ calls for our post-match field set** (answering the question as asked):

| Need | Calls |
|---|---|
| A. 1 new match, deep | 1 |
| B. 5 matches, deep | 1 |
| C. 10 matches, deep | 1 |
| D. 50-match backfill, deep | 1 |
| E. 100-match backfill, deep | 1 |
| F. 500-match backfill, deep | 2 |
| 1,000-match backfill, deep | 4 |
| Full lifetime (9,493 matches), deep | 32 |
| Any number of matches, id + parse-state only | ceil(N/3000) |

### 3.4 Parse semantics — `parsedDateTime` is not the parse gate

**TESTED**: `parsedDateTime` marks basic ingestion; **`statsDateTime` / `isStats`** marks
replay-derived stats. A match can carry `parsedDateTime` and still return null `networthPerMinute`.

| Match | end age at probe | parsedDateTime | statsDateTime |
|---|---|---|---|
| 9007479102 | 45.0 min | +8.0 min | **null** |
| 9007287639 | 5.4 h | +61.2 min | +61.6 min |
| 8999078604 | 5.5 d | +10.9 min | +11.0 min |

Any STRATZ-dependent feature must gate on `statsDateTime`, not `parsedDateTime`.

Historical coverage is good, though: 3 accounts × 300 most-recent matches → `statsDateTime`
present on **87% / 100% / 97%** (1 call each).

### 3.5 Multi-Token — what is actually known

**VERIFIED**: Multi-Tokens exist, require an application, are approved case-by-case, require
**5,000 referral clicks/month** back to stratz.com, and give **20/s, 20/min, 50/hr, 100/day per user**.
The stated purpose is "desktop applications downloaded to many different users' computers".

**UNKNOWN — every operational question you asked is undocumented.** Nothing public states:
whether the end user needs a STRATZ/Steam login; who mints the per-user token; whether there is an
HTTP endpoint for issuance or only the logged-in "My Tokens" page; whether tokens bind to Steam IDs;
whether a global application ceiling exists on top of the per-user one; whether server-side
generation and server-side use (rather than from the user's own machine) is permitted; whether an
iOS consumer app qualifies at all given the "desktop application" framing; and whether the
one-IP binding we measured applies per sub-token (if it does, server-side use of user tokens is
effectively impossible from a multi-IP backend). Questions to send STRATZ are listed in §13.

**INFERRED**: given that our design needs roughly **0–2 STRATZ calls per user per day**
(backfill once at onboarding, then nothing per match), 100/user/day is enormous headroom — but
the 5,000 referral/month obligation, the approval risk and the unanswered issuance questions make
Multi-Token an *optimization to pursue later*, not a foundation to build on now. A single
Individual Token comfortably covers a six-figure DAU product under the architecture in §9.

---

## 4. OpenDota findings

**VERIFIED** (opendota.com/api-keys, read 2026-09-20):

| | Free | Premium |
|---|---|---|
| Price | free | **$0.01 per 100 calls = $0.0001/call** |
| Daily ceiling | 3,000/day | **unlimited** |
| Rate limit | 60/min | **3,000/min** |
| Key | not required | required, needs a card on file |
| Billing exclusions | – | 404 / 429 / 500 responses are not billed |

**TESTED** header confirmation: unauthenticated → `x-rate-limit-remaining-minute: 59`,
`x-rate-limit-remaining-day: 2999`. With our key → `x-rate-limit-remaining-minute: 2999`, **no day header at all**.

**VERIFIED** from OpenDota's own OpenAPI spec (bundled at `api.json` in this repo):
`POST /request/{match_id}` — *"This call counts as 10 calls for rate limit (but not billing) purposes."*
So a parse request bills $0.0001 and consumes 10 of the 3,000/min budget → 300 parse requests/min ceiling.

### Latency, measured today

| Event | Measurement |
|---|---|
| Match appears in `/publicMatches` | min **2.4 min** after match end (n=100) |
| Match appears in `/players/{id}/recentMatches` | min **2.9**, median **3.4**, max **4.0** min (n=12) |
| Auto-parse rate for the general population | **0 / 40** fresh public matches — OpenDota does **not** auto-parse |
| Parse when *we* request it, fresh match | run 1: **10/10** at **6.2–7.1 min**; run 2: **11/12** at **6.4–7.8 min** (median 7.1) after match end |
| Parse latency once the replay exists | **23–25 s** (two matches, aged 14 min and 37 min) |
| Parse of a 60-day-old match | success, < 40 s |
| Parse of 180 / 365 / 730-day-old matches | **all fail** — Valve replay gone |

The 6.5-minute floor is **Valve replay availability**, not OpenDota's queue: requests issued at
T+3 min produced `has_gcdata: true` but no parse; re-requests after T+6 parsed in ~25 s.
OpenDota's own `parseDelay` health metric read 3–7 the whole time, i.e. no queue backlog.

### Endpoint behaviour worth knowing

* `/players/{id}/matches` defaults to `significant=1`, which **silently drops Turbo** (game_mode 23).
  With `significant=0` the same account returned **9,493 matches in one 2.5 MB / 1.7 s call**,
  including a match that had ended 5 minutes earlier. With the default it returned 4,107 and was
  missing 14 of the player's last 20 matches. Always pass `significant=0`.
* `/players/{id}/matches` accepts arbitrary `project=` columns — 20 projected columns over the full
  9,493-match lifetime is still **one call**.
* `version` (parse state) is returned by `recentMatches` and by `matches`, so parse state for an
  entire history costs **zero extra calls**.
* `benchmarks` (percentile of GPM/XPM/KPM/DPM/APM/LH per hero) come back on unparsed matches.
* Anonymous-on-STRATZ accounts still resolve fine on OpenDota (3/3 tested returned 20 recent matches).

---

## 5. Data capability matrix

"OD basic" = `GET /matches/{id}` with `version: null`, i.e. available at T+3 min with no parse.
All four columns below were checked against real payloads today.

| Capability | OD basic (T+3m) | OD parsed (T+6.5m) | STRATZ (statsDateTime) | Valve |
|---|---|---|---|---|
| Win/loss, duration, side, game mode, lobby | ✅ | ✅ | ✅ | ✅ |
| Hero, hero variant, level, K/D/A | ✅ | ✅ | ✅ | ✅ |
| GPM, XPM, net worth, gold spent | ✅ | ✅ | ✅ | ✅ |
| Last hits, denies | ✅ | ✅ | ✅ | ✅ |
| Hero damage, tower damage, healing | ✅ | ✅ | ✅ | ✅ |
| Final items, backpack, neutral, moonshard, aghs/shard | ✅ | ✅ | ✅ | ✅ |
| Ability/talent build order (`ability_upgrades_arr`) | ✅ | ✅ | ✅ (`abilities`) | ✅ |
| Draft (`picks_bans`) | ✅ | ✅ | ✅ | ✅ |
| Tower/barracks end state, first blood time | ✅ | ✅ | ✅ | ✅ |
| All ten players' summary | ✅ | ✅ | ✅ | ✅ |
| **Percentile benchmark vs hero population** | ✅ (`benchmarks`) | ✅ | via `heroStats` (extra calls) | ❌ |
| Rank tier / bracket | ⚠️ `average_rank` only | ✅ `rank_tier` | ✅ `rank`, `bracket` | ❌ |
| Party composition | ⚠️ `party_size` in history | ✅ `party_id`, `party_size` | ✅ `partyId` | ⚠️ |
| Gold / XP / LH / DN / net worth per minute | ❌ | ✅ `gold_t` `xp_t` `lh_t` `dn_t` `networth_t` | ✅ `networthPerMinute` etc. | ❌ |
| Team gold & XP advantage curve | ❌ | ✅ `radiant_gold_adv`, `radiant_xp_adv` | ✅ `radiantNetworthLeads` | ❌ |
| Lane assignment + lane efficiency | ⚠️ `lane_role` hint | ✅ `lane`, `lane_pos`, `lane_efficiency_pct`, `lane_kills` | ✅ `lane`, `position`, `role` | ❌ |
| Item purchase timings | ❌ | ✅ `purchase_log`, `first_purchase_time` | ✅ `itemPurchases` | ❌ |
| Item *usage* counts / consumables | ❌ | ✅ `item_uses`, `item_usage`, `purchase_tpscroll/ward_*` | ✅ `itemUsed` | ❌ |
| Ward placement + expiry log | ❌ | ✅ `obs_log`, `sen_log`, `obs_left_log`, `obs_placed` | ✅ `wards`, `wardDestruction` | ❌ |
| Camp stacking | ❌ | ✅ `camps_stacked`, `camps_stacked_t` | ✅ `campStack` | ❌ |
| Objectives (tower/rax/Roshan/Aegis) with timestamps | ❌ | ✅ `objectives` | ⚠️ `towerDeaths` only (+`chatEvents`) | ❌ |
| Teamfights (participation, damage, gold swing) | ❌ | ✅ `teamfights`, `teamfight_participation` | ❌ (must reconstruct) | ❌ |
| Kill / death / assist logs with targets | ❌ | ✅ `kills_log`, `deaths_log`, `killed`, `killed_by` | ✅ `killEvents`, `deathEvents`, `assistEvents` | ❌ |
| Damage breakdown by inflictor and target | ❌ | ✅ `damage_inflictor`, `damage_targets`, `damage_taken` | ✅ `heroDamageReport` | ❌ |
| Runes, rune pickups | ❌ | ✅ `runes`, `runes_log`, `rune_pickups` | ✅ `runes` | ❌ |
| Stuns, hero hits, max hero hit, multi-kills, streaks | ❌ | ✅ | ⚠️ partial | ❌ |
| Positional heatmap | ❌ | ✅ `lane_pos`, `position_est` | ❌ `locationReport` is unusable (no `time`, fixed length) | ❌ |
| Buyback log, connection log, pauses | ❌ | ✅ | ⚠️ `buyBackGold` dead | ❌ |
| Neutral item history, permanent buffs | ❌ | ✅ | ⚠️ `inventoryReport` returns empty | ❌ |
| Chat / pings / word counts | ❌ | ✅ | ✅ `chatEvents`, `allTalks`, `chatWheels` | ❌ |
| Replay URL / salt | ❌ | ✅ | ✅ `replaySalt` | ✅ |
| `imp` (STRATZ impact score), `award` | ❌ | ❌ | ✅ | ❌ |
| Population baselines by hero × position × week | ❌ | ⚠️ only via per-hero `benchmarks` | ✅ `heroStats.stats`, `heroStats.laneOutcome` | ❌ |
| Deep data for matches older than ~3 months | ❌ (replay gone) | ❌ (replay gone) | ✅ already parsed, 87–100% | ❌ |

Cross-source agreement check on one match (9007479102): duration, winner, and every player's
K/D/A and final net worth matched **exactly** between OpenDota and STRATZ. No reconciliation
problem at the summary level.

---

## 6. Minimum STRATZ dependency

**Category A — no STRATZ needed (OpenDota basic or parsed covers it).**
Everything in the matrix above that has a ✅ in either OpenDota column. That is the overwhelming
majority of a post-match report: result, KDA, farm, items and timings, laning, net worth/XP curves,
wards, stacks, objectives, teamfights, kill/death logs, damage breakdowns, runes, heatmaps,
personal baselines, PBs, and hero-population percentiles (`benchmarks` is free and unparsed).

**Category B — either source works.** Ten-player context, draft, party, kill/death timelines,
item purchase timings, ward logs, camp stacks. Use whichever is already cached; prefer OpenDota
for fresh matches and STRATZ for history.

**Category C — genuinely requires STRATZ.**
1. `imp` and `award` — STRATZ's proprietary impact scores. No equivalent anywhere.
2. `position` / `role` (POSITION_1..5) as a first-class label. OpenDota gives `lane_role` +
   `is_roaming`, which is a hint; STRATZ's is better and is what the existing V7 models were fit on.
3. `rank` / `bracket` per match, reliably.
4. `heroStats.stats` and `heroStats.laneOutcome` — the population baseline corpus (already
   validated in `CONTEXT-ADJUSTED-PERFORMANCE-V1.md`). ~5 calls per patch/week, **not per match**.
5. **Deep data for matches older than the Valve replay window** (~60–180 days). This is the big one
   for Pro-tier history features: OpenDota simply cannot produce it, STRATZ already has it.

**Sophisticated-sounding features that do NOT need STRATZ:** lane win/loss, lane efficiency,
"you were X gold behind at 10 minutes", item timing vs your own median, smoke→kill conversion,
stack counts, ward uptime, objective participation, teamfight impact, death-cost analysis,
farm-pattern change, hero-population percentile ranking. All of these are derivable from
OpenDota parsed fields tested today.

**Consequence: STRATZ usage per fresh match should be zero.** STRATZ is a per-user onboarding cost
(1–32 calls once) plus a per-week global cost (~5 calls), not a per-match cost.

---

## 7. API-call experiments (what was actually run)

### 7.1 OpenDota

| # | Call | Params | Key | Status | Latency | Bytes | Result |
|---|---|---|---|---|---|---|---|
| 1 | `GET /health` | – | no | 200 | – | 2.9 KB | `remaining-minute: 59`, `remaining-day: 2999` |
| 2 | `GET /health` | – | yes | 200 | 0.66 s | 2.9 KB | `remaining-minute: 2999`, no day header |
| 3 | `GET /publicMatches` | – | yes | 200 | 0.39 s | 25 KB | 100 matches; freshest ended **2.4 min** ago |
| 4 | `GET /matches/{id}` ×40 | fresh matches | yes | 200 | – | 17–19 KB | **0/40 parsed**, 4/40 had gcdata |
| 5 | `GET /matches/{id}` | parsed match | yes | 200 | 0.76 s | 216 KB | `version: 22`; full field delta recorded |
| 6 | `POST /request/{id}` ×4 | fresh (T+4m) | yes/no | 200 | 0.3–0.5 s | – | jobs accepted, **no parse after 9 min** |
| 7 | `POST /request/{id}` ×2 | aged 14 m, 37 m | yes | 200 | – | – | **parsed in 23 s and 24 s** |
| 8 | parse-age sweep, 10 fresh matches | request+poll every 45 s | yes | 200 | 3.7 min wall | – | **10/10 parsed at 6.2–7.1 min after match end** |
| 9 | `POST /request/{id}` | 60 d old | yes | 200 | – | – | parsed < 40 s |
| 10 | `POST /request/{id}` ×3 | 180 d / 365 d / 730 d | yes | 200 | – | – | **all failed to parse** |
| 11 | `GET /players/{id}/recentMatches` | – | yes | 200 | 0.63 s | 8.6 KB | 20 matches, incl. one ended **4.9 min** ago; carries `version` |
| 12 | `GET /players/{id}/matches` | default | yes | 200 | 1.37 s | 1.10 MB | 4,107 rows, **missing 14 of last 20** (Turbo dropped) |
| 13 | `GET /players/{id}/matches` | `significant=0` | yes | 200 | 1.71 s | 2.52 MB | **9,493 rows, fully current, one call** |
| 14 | `GET /players/{id}/matches` | 20 × `project=` | yes | 200 | 1.41 s | 1.67 MB | 4,107 rows with GPM/XPM/LH/DN/level/lane_role |
| 15 | `GET /players/{id}/recentMatches` ×3 | anonymous accounts | yes | 200 | – | – | 20/20/20 rows — anonymity is not a blocker |
| 16 | head-to-head, 12 fresh matches | OD vs STRATZ, polled 7 min | yes | 200 | – | – | OD visible: min **2.9** / med **3.4** / max **4.0** min. OD parsed: **11/12** at min **6.4** / med **7.1** / max **7.8** min. STRATZ: only **3/12** existed at all by T+7 min |

### 7.2 STRATZ (99 calls, ledger at `scratchpad/stratz/ledger.jsonl`)

| # | Test | Result |
|---|---|---|
| 1 | header dump | `8/s, 150/min, 1500/hr, 15000/day` — **contradicts the published table** |
| 2 | 20 fresh public matches, aliased `match(id:)` | **1/20 present**; the one present: parsed +5.9 min |
| 3 | longitudinal, 20 freshest matches, 4 rounds over 12 min | **0/20 present throughout** |
| 4 | aliased `match(id:)` TINY at n = 1/5/10/16/20/25/30/40/60/100/150/200 | all 200; 700 → complexity 342,300 → **cap ≈ 633** |
| 5 | aliased `match(id:)` CORE at n = 1…60, then 77 / 78 | 77 ok; 78 → 313,170 → **cap 77** |
| 6 | aliased `match(id:)` HEAVY at n = 1/10/20/30/40 | 30 ok; 40 → 331,560 → **cap ≈ 37** |
| 7 | `player.matches` CORE `take` = 5/20/50/100/200 | 100 ok (2.26 MB, 1.53 s); 200 → `max take 100` |
| 8 | `player.matches` CORE, 1–4 player aliases × `take: 100` | 3 ok (300 matches, 8.07 MB, 2.9 s); 4 → 321,128 |
| 9 | `player.matches` TINY, 10/20/25/30 aliases × `take: 100` | **30 aliases = 2,900 matches, 11.7 MB, 3.0 s** |
| 10 | same `take` 20 vs 100, complexity | **identical (80,282/alias)** → `take` is free |
| 11 | `player.matches(request:{matchIds:[100 ids], take:100})` CORE | 89/100 returned, 1.98 MB, 1.45 s |
| 12 | `matches(ids: [...])` root field | `"User is not an admin."` — **unavailable** |
| 13 | production `GetDeepMatchBatch`, 8/20/50/100 IDs | returned **10** every time — missing `take` |
| 14 | production `GetDeepMatchBatch` + `take: 100` | **89 matches, 1.09 MB, 1.2 s**; 2 aliases → 605,964 |
| 15 | aliased `skip` pagination, CORE, 3 vs 5 pages | 3 pages = **300 matches, 7.0 MB, 3.2 s**; 5 → 401,406 |
| 16 | aliased `skip` pagination, id-only, 30 pages | **3,000 matches, 206 KB, 0.93 s** |
| 17 | `parsedDateTime` vs `statsDateTime` on 3 matches | see §3.4 — they diverge by up to 45+ min |
| 18 | `statsDateTime` coverage, 3 accounts × 300 matches | **87% / 100% / 97%**, one call each |
| 19 | cross-source agreement vs OpenDota on one match | KDA, net worth, duration, winner — **exact match** |

**Answer to "1 vs 5 vs 10+ match batching":** with the right query shape it is never 10 calls for
10 matches. It is **one call for up to 100 matches per player**, **one call for up to 300 matches**
using aliased pages, and **one call for 2,900 matches** at summary depth.

---

## 8. Scale simulation

Assumptions: 1 detection call per app-open session (users open the app ~1.4× per match session, so
detection amortizes to ~0.4 calls/match); 1 parse request + 1 parsed fetch per match; the instant
card comes free out of the detection payload; `GET /matches/{id}` basic is skipped because
`recentMatches` already carries the card fields and the parsed fetch supersedes it.

**Per unique match, OpenDota calls ≈ 2.4.** Dedup means a match shared by *k* of our users still
costs 2.4 calls total.

| DAU | matches/user/day | raw matches | unique after dedup* | OD calls/day | OD $/day | OD $/month | STRATZ calls/day |
|---|---|---|---|---|---|---|---|
| 100 | 2 | 200 | 200 | 480 | $0.05 | $1.4 | ~5 + onboarding |
| 1,000 | 4 | 4,000 | 3,996 | 9,590 | $0.96 | $29 | ~5 + onboarding |
| 5,000 | 4 | 20,000 | 19,900 | 47,760 | $4.78 | $143 | ~5 |
| 10,000 | 4 | 40,000 | 39,600 | 95,040 | $9.50 | $285 | ~5 |
| 10,000 | 6 | 60,000 | 59,400 | 142,560 | $14.26 | $428 | ~5 |
| 50,000 | 4 | 200,000 | 195,000 | 468,000 | $46.80 | $1,404 | ~5 |
| 100,000 | 4 | 400,000 | 380,000 | 912,000 | $91.20 | $2,736 | ~5 |
| 100,000 | 6 | 600,000 | 555,000 | 1,332,000 | $133.20 | $3,996 | ~5 |
| 100,000 | 10 (heavy cohort) | 1,000,000 | 900,000 | 2,160,000 | $216 | $6,480 | ~5 |

\* dedup factor = 1 − (our share of the concurrent player pool) × 9/10, applied crudely. At 100k DAU
against Dota's ~1M daily players, roughly 5% of matches contain ≥2 of our users.

**Rate-limit headroom.** 100k DAU × 6 matches = 1.33 M calls/day = **925 calls/min average**.
Premium allows 3,000/min. Parse requests cost 10 against that budget: 555k parse requests/day =
385/min → 3,850 rate-limit units/min, which **exceeds** 3,000/min. Mitigation: parse requests must be
spread by a scheduler (they are already naturally spread by the T+6 min delay) and the system needs
a token-bucket in front of the parse queue. At 50k DAU there is no issue at all.

### Architecture comparison

| | A. STRATZ-only | B. OpenDota-only | C. OD instant + STRATZ deep | D. **OD + selective STRATZ** (recommended) | E. STRATZ Multi-Token |
|---|---|---|---|---|---|
| Fresh deep analysis at | 11–60+ min, unreliable | **6.5 min, 10/10** | 11–60+ min | **6.5 min** | 11–60+ min |
| Calls/day @100k DAU ×4 | ~4,000 STRATZ (batched) | 912k OD | 912k OD + 4,000 STRATZ | **912k OD + ~5 STRATZ** | same, spread over user tokens |
| Fits limits? | yes on volume, **no on latency** | yes | yes | **yes** | yes |
| Cost/month @100k DAU | $0 | $2,736 | $2,736 | **$2,736** | $2,736 |
| Deep history > 3 months | ✅ | ❌ | ✅ | **✅ (STRATZ for backfill only)** | ✅ |
| Vendor risk | single point of failure | single point of failure | two vendors | **two vendors, either can degrade gracefully** | + approval + referral obligation |
| Blocking unknowns | – | – | – | – | **many (§3.5)** |

D wins. Note that A is *cheap* but loses on the one thing the product is built around.

---

## 9. Recommended backend architecture

### 9.1 `match_id` is the unit of work, not `(user, match)`

```
                     ┌──────────────────────────────┐
  iOS app open ─────▶│  POST /sync/{dota_account}   │
                     └───────────┬──────────────────┘
                                 │  (debounced: max 1 per account per 60 s)
                                 ▼
                    OpenDota /players/{id}/recentMatches      ← 1 call
                                 │
                        new match_ids not in DB?
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
     upsert matches(match_id)          upsert match_players rows
     state = 'summary'                 (from the recentMatches payload)
                 │
                 ▼
     enqueue parse_job(match_id)  ── idempotent on match_id, unique index
                 │
                 ▼
     scheduler: run_at = max(now, match_end + 6 min)
                 │
                 ▼
     POST /request/{match_id}  ──▶ wait 30 s ──▶ GET /matches/{match_id}
                 │                                        │
          version == null?                          version != null
                 │                                        │
      retry with backoff 2m/5m/10m/20m            store parsed payload
      (max 6 attempts, then state='unparseable')  state = 'parsed'
                                                          │
                                                          ▼
                                            compute analysis for EVERY
                                            tracked account in that match
                                                          │
                                                          ▼
                                          push notification to those users
```

Because the job key is `match_id`, five of our users in the same match produce **one** parse request
and **one** parsed fetch. The friend-timeline case in §10 falls out of the same property.

### 9.2 Sync state machine

`matches.state ∈ {discovered, summary, parse_requested, parsed, unparseable, archived}`

| Transition | Trigger | Guard |
|---|---|---|
| → `summary` | seen in any `recentMatches` | – |
| `summary` → `parse_requested` | scheduler at `end_time + 6 min` | match_end within replay window |
| `parse_requested` → `parsed` | `version != null` | – |
| `parse_requested` → `parse_requested` | retry | `attempts < 6` |
| `parse_requested` → `unparseable` | attempts exhausted, or match older than 90 d | – |
| `unparseable` → `parsed` | STRATZ backfill job finds `statsDateTime` | Pro tier only |

`sync_state` per dota account holds `last_seen_match_id`, `last_sync_at`, `backfill_cursor`,
`backfill_complete`, and `consecutive_failures`. Detection is pull-only; **there are no webhooks
from either vendor** — neither OpenDota nor STRATZ offers one (VERIFIED by absence from both API
surfaces).

### 9.3 Polling policy

* **On app foreground**: always, debounced to 1 call / account / 60 s. This is the P0 path.
* **Background, "hot" users** (played in the last 3 h): poll `recentMatches` every 5 min for 45 min
  after the last seen match, then stop. This is what lets the push notification fire while the app
  is closed.
* **Background, cold users**: no polling at all. Their next app-open picks everything up.
* Never poll `/matches/{id}` to discover matches. Never spend a STRATZ call on detection.

### 9.4 Queues

Three priority classes on one worker pool, strict priority:

| Class | Contents | Concurrency budget |
|---|---|---|
| P0 | detection sync for a user with the app open | unbounded (it is 1 cheap call) |
| P1 | parse request + parsed fetch for matches < 2 h old | 70% of workers |
| P2 | re-parse retries, matches 2 h – 7 d old | 20% |
| P3 | historical backfill (OpenDota and STRATZ) | 10%, and hard-paused whenever P1 depth > N |

### 9.5 Caching

* Postgres is the cache. Redis only for the 60-second per-account sync debounce and the
  rate-limit token buckets.
* Serve the app from the DB always; the API is never on the read path of a screen.
* `analysis_results` keyed by `(match_id, dota_account_id, analysis_version)`.

---

## 10. Social / friend timelines

The `match_id`-keyed design already solves this. A friend timeline is a **read against
`match_players` joined to `matches`**, with zero API calls, provided the followed player is a
*tracked account*.

Rules:

1. A `dota_account` is tracked if any user owns it **or** at least one user follows it.
2. Tracking is a property of the account, not of the follower count. 100 followers of Player X
   produce exactly the same ingestion cost as 1 follower.
3. Followed-but-unowned accounts get the cheap tier: `recentMatches` detection on app-open of any
   follower (debounced globally per account, not per follower), and P2 parse priority rather than P1.
4. Follower fan-out is a DB fan-out on read. Never a fetch fan-out.

Cost model: ingestion scales with **distinct tracked accounts**, not with the follow graph.

---

## 11. Database strategy

### Tables

| Table | Notes |
|---|---|
| `users` | app identity |
| `dota_accounts` | `account_id` (Steam32) PK, `is_owned`, `is_tracked`, `personaname`, `profile_visibility` |
| `user_dota_accounts` | ownership, verified via Steam OpenID |
| `follows` | `(user_id, account_id)` — read-side only |
| `matches` | `match_id` PK, `start_time`, `duration`, `end_time` generated, `game_mode`, `lobby_type`, `patch`, `region`, `radiant_win`, `state`, `parse_version`, `parsed_at`, `source_flags` |
| `match_players` | `(match_id, player_slot)` PK; the normalized summary columns (hero, K/D/A, GPM, XPM, LH, DN, net worth, items, level, lane_role, party_size, `account_id` nullable) |
| `match_raw_opendota` | `match_id` PK, `payload jsonb`, `fetched_at`, `version` — **compressed, TOASTed** |
| `match_raw_stratz` | `match_id` PK, `payload jsonb`, `fetched_at`, `stats_date_time` |
| `parsed_match_features` | `(match_id, player_slot)`; the extracted, versioned feature vector our analysis consumes (timelines downsampled to per-minute arrays, item timings, ward counts, lane metrics) + `feature_version` |
| `player_match_metrics` | `(account_id, match_id)`; per-player derived metrics + baselines at time of computation |
| `analysis_results` | `(match_id, account_id, analysis_version)` PK; the rendered insight payload + `inputs_digest` |
| `sync_state` | per `account_id`; cursors, failure counters |
| `ingest_jobs` | queue table with `unique(match_id, job_type)` for idempotency |
| `api_call_log` | vendor, endpoint, status, latency, billed — for cost attribution and post-mortems |

### What to normalize vs. keep raw

* **Normalize** everything the app renders directly and everything you filter/aggregate on
  (`match_players`, `player_match_metrics`).
* **Keep raw** the full OpenDota parsed payload. It is ~200 KB uncompressed, roughly **35–50 KB
  after Postgres jsonb + TOAST compression**. At 100k DAU × 4 matches/day × 380k unique matches, that
  is ~15 GB/day raw. **Do not keep it in Postgres past 30 days.**
* **Recommended tiering:** raw payload in Postgres for 7 days (fast re-derivation while algorithms
  are churning) → object storage (S3/Supabase Storage, gzip) for 12 months → delete. Keep
  `parsed_match_features` in Postgres forever; it is 1–2 KB per player-match and is the actual
  reproducibility unit.
* STRATZ raw only for matches we pulled from STRATZ (backfill), same policy.

### Reproducibility

Three independent version columns, all recorded on every result:

* `feature_version` — how raw payload → `parsed_match_features`.
* `analysis_version` — how features → insight.
* `baseline_version` — which population parameters (STRATZ `heroStats` snapshot date) were used.

`analysis_results.inputs_digest` = hash of (feature_version, analysis_version, baseline_version,
feature row hashes). Recompute is a backfill job over `parsed_match_features`, never over the API.
**Historical calculations stay reproducible as long as `parsed_match_features` survives, which is why
that table — not the raw JSON — is the thing you must never lose.**

---

## 12. Fresh-match vs backfill strategy

Hard rules:

1. **Backfill never issues a parse request.** Backfill is summary-only on OpenDota
   (1 call for the whole lifetime with `significant=0`) plus STRATZ for deep history.
2. Onboarding, free tier: **1 OpenDota call** (full lifetime summary, 9,493 rows in the example
   account) + **1 STRATZ call** (300 deep matches). That is the entire free-tier import.
3. Onboarding, Pro tier: add STRATZ pages, 300 deep matches per call:

| Backfill depth | OpenDota calls | STRATZ calls | Wall time |
|---|---|---|---|
| 20 matches, deep | 20 (only if < 60 d old) | **1** | ~1 s |
| 50 | 50 | **1** | ~2 s |
| 100 | 100 | **1** | ~1.5 s |
| 300 | 300 | **1** | ~3 s |
| 500 | 500 | **2** | ~6 s |
| 1,000 | 1,000 | **4** | ~13 s |
| Full lifetime (~9,500) | not possible (replays gone) | **32** | ~2 min |

4. Backfill runs in P3 and is **hard-paused** whenever the P1 queue depth exceeds a threshold or
   whenever the OpenDota minute-budget is above 70% utilized.
5. STRATZ daily budget (15,000 measured) is split: 90% backfill, 10% reserved. At 1 call per free
   onboarding that is 13,500 new users/day; at 32 calls per full Pro import, ~420 full imports/day.
   If that binds, apply for an Individual Token or stage Pro imports over hours — **it never blocks a
   fresh match, because fresh matches do not touch STRATZ.**

---

## 13. Failure and degradation behaviour

| Failure | Behaviour |
|---|---|
| **STRATZ quota exhausted** | No effect on fresh matches. Backfill pauses and resumes next window. Pro import shows "importing your history — this can take a few hours". Population baselines are cached for the whole patch, so no per-request dependency. |
| **STRATZ down** | Same as above. The only user-visible loss is `imp`/`award`/`position` labels on *new* matches — fall back to OpenDota `lane_role` + `is_roaming` and mark the role read as "estimated". |
| **OpenDota parse delayed / queue backed up** | Card still renders at T+3 min from `recentMatches`. Tier-2 section shows a progress state with an honest ETA. Retry ladder 2/5/10/20/40 min. After 6 attempts mark `unparseable` and, for Pro users, hand the match to the STRATZ backfill queue (STRATZ will usually have `statsDateTime` within the hour). |
| **Match never parses** (replay missing, abandoned, custom lobby) | State `unparseable`. The Tier-1 report is complete and self-sufficient — this is exactly why Tier 1 must never depend on parsed fields. Show "replay unavailable for this match" once, not a spinner. |
| **OpenDota down entirely** | This is the real single point of failure. Mitigation: a STRATZ fallback detection path (`player.matches(request:{startDateTime, take:100})`, 1 call, ~4 min ingest lag) behind a circuit breaker. Accept degraded deep-analysis latency while it is on. Because both sources agree exactly on summary values (TESTED), the switch is invisible to users. |
| **Sources disagree** | They did not, on any summary field, in the cross-check. Policy anyway: OpenDota parsed is authoritative for anything replay-derived on fresh matches; STRATZ is authoritative for `imp`, `award`, `position`, `rank`; for matches present in both, keep both raw payloads and record which source produced each stored feature (`parsed_match_features.source`). |
| **Steam profile not public** | Both vendors depend on Dota's "Expose Public Match Data". Detect at onboarding (empty `recentMatches` + non-zero `matchCount` in the Steam profile) and show the in-client instructions. Not an API problem. |
| **STRATZ 403 "different IP"** | Server-side STRATZ jobs must run single-flighted from a fixed egress IP (NAT gateway / static egress). This is already a known failure mode in our probe history. |

---

## 14. Product implications — what you can safely promise

Based on measured numbers, not aspiration:

* ✅ **"Your match shows up about as fast as you can get to the main menu."** Median 3.4 min,
  worst observed 4.0 min (n=12). Safe copy: *"Your match appears within a few minutes of the
  post-game screen."* Do **not** say "instantly".
* ✅ **"Your report is ready before you queue again."** Full parsed analysis at 6.2–7.8 min across
  22 matches in two cohorts (21/22 succeeded on the first pass). Safe copy: *"Full breakdown usually
  ready in under 10 minutes."* Do **not** promise 30 s —
  Valve does not publish the replay that fast, and no vendor can beat that floor.
* ✅ **Two-stage UI is a feature, not an apology.** Ship the Tier-1 card the moment it exists, with a
  visible, honest "deep breakdown unlocking in ~5 min" affordance, and a push when it lands.
* ⚠️ Avoid any promise about matches older than ~2 months getting *new* deep analysis on the free
  tier. That is a Pro/STRATZ capability.
* ❌ Never promise real-time / in-game or immediately-at-scoreboard analysis. The floor is Valve's
  replay publication (~6 min), full stop.

The emotional-moment concern is satisfied: at T+3 min the user gets result, hero, KDA, farm, items,
draft, role and **percentile-vs-population benchmarks** — a genuinely substantive report — and the
deep layer lands well inside the same sitting.

---

## 15. Remaining unknowns

**Ask STRATZ (Discord / API application form):**
1. Our token reports `8/s, 150/min, 1500/hr, 15000/day` while the public table lists
   `20/250/2000/10000` for Default and `20/250/4000/20000` for Individual. Which is authoritative,
   and what tier is this token on?
2. Multi-Token: who mints the per-user tokens — is there an HTTP endpoint, or only the logged-in
   "My Tokens" page? Is it documented anywhere?
3. Does a Multi-Token sub-token require the end user to have a STRATZ account or to log in with Steam?
4. Are sub-tokens bound to a Steam ID? Can one be minted for a Steam ID that has never visited STRATZ?
5. Is there a global ceiling across all sub-tokens of one Multi-Token, or only the per-user 100/day?
6. Does a native **iOS** app qualify for a Multi-Token, given the docs frame it as "desktop
   applications downloaded to many different users' computers"?
7. Can sub-tokens be generated and used **server-side** on the user's behalf, or must the call
   originate from the user's own device?
8. Does the one-IP binding we observe on our token apply per sub-token? (If yes, server-side use
   from a multi-IP backend is impossible and Multi-Token is off the table for us.)
9. Is the 5,000/month referral requirement measured as clicks, unique visitors, or sessions?
   What happens on a short month?
10. What is the expected/SLA'd distribution of `endDateTime → statsDateTime`? We measured +11 min,
    +61 min, and still-null-at-45-min. Is there a way to prioritise a match?
11. Is `matches(ids:)` admin-only permanently, or can it be enabled for an Individual Token?
12. Is `take: 100` the hard ceiling for `player.matches`, and is the complexity-independent-of-`take`
    behaviour intentional and stable? (Our whole backfill plan rests on it.)

**Ask OpenDota (Discord):**
13. Does Premium still include a free monthly call allowance (historically 50,000/month)? The
    pricing page no longer mentions one.
14. Is there any anti-abuse ceiling on `POST /request` beyond the 10×-rate-limit accounting? We
    issued ~30 in an hour with no pushback, but we would be issuing ~500k/day at 100k DAU.
15. Is the ~6-minute floor for replay availability stable, or region-dependent?
16. Is there any bulk match endpoint, or any plan for one / for webhooks?
17. What is the retention of `has_archive` matches, and can archived matches be re-served without
    a re-parse?

**Still to test ourselves:**
18. Valve `IDOTA2Match_570/GetMatchHistory` — no Steam Web API key in the environment, so untested.
    Worth 30 minutes: if Valve exposes the match ID at T+0–60 s, detection could beat OpenDota's
    3-minute floor by two minutes at zero marginal cost (100k calls/day, free). It would **not**
    change the analysis timeline, which is replay-bound.
19. Exact replay-availability boundary between 60 and 180 days.
20. Dedup rate in production — the 5% figure at 100k DAU is a crude estimate.

---

## 16. Final architecture

```
┌─────────────┐   foreground open / push ack
│   iOS app   │────────────────────────────────┐
└──────┬──────┘                                │
       │ reads (always DB, never vendor)       ▼
       │                            ┌────────────────────┐
       │                            │  Sync API (P0)     │
       │                            │  debounce 60 s     │
       │                            └─────────┬──────────┘
       │                                      │ 1 call
       │                                      ▼
       │                     OpenDota /players/{id}/recentMatches
       │                                      │
       │                          new match_ids (diff vs DB)
       │                                      ▼
       │                        ┌──────────────────────────┐
       │                        │ matches / match_players  │  ← instant card data
       │                        │ state = summary          │
       │                        └────────────┬─────────────┘
       │                                     │ enqueue unique(match_id)
       │                                     ▼
       │                   ┌───────────────────────────────────┐
       │                   │  Job queue (Postgres + worker)    │
       │                   │  P1 fresh parse  P2 retry  P3 backfill │
       │                   └───────┬───────────────────┬───────┘
       │                           │                   │
       │            run_at = end+6m│                   │ (paused under P1 load)
       │                           ▼                   ▼
       │        OpenDota POST /request/{id}    ┌──────────────────────┐
       │        then GET /matches/{id}         │ STRATZ backfill      │
       │                           │           │ player.matches       │
       │                           │           │ 300 deep / call      │
       │                           ▼           └──────────┬───────────┘
       │              ┌──────────────────────┐            │
       │              │ match_raw_opendota   │◀───────────┤ match_raw_stratz
       │              │ (7 d PG → 12 mo S3)  │            │
       │              └──────────┬───────────┘            │
       │                         ▼                        │
       │              ┌──────────────────────┐            │
       │              │ parsed_match_features│◀───────────┘
       │              │ feature_version      │   (keep forever)
       │              └──────────┬───────────┘
       │                         ▼
       │              ┌──────────────────────┐      ┌─────────────────────┐
       │              │ deterministic engine │◀─────│ STRATZ heroStats    │
       │              │ analysis_version     │      │ baselines, ~5 calls │
       │              └──────────┬───────────┘      │ per patch/week      │
       │                         ▼                  └─────────────────────┘
       │              ┌──────────────────────┐
       └──────────────│ analysis_results     │──▶ push "breakdown ready"
                      │ (match_id, account)  │
                      └──────────────────────┘
```

**One sentence:** detect and render from OpenDota `recentMatches`, force the OpenDota parse at
T+6 min and render the deep layer from it, key every job on `match_id` so shared matches and friend
timelines cost nothing extra, and spend STRATZ only on population baselines and on history that
Valve's replay window has already destroyed.
