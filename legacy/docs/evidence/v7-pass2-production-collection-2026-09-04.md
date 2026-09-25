# V7 Pass-2 production collection — 2026-09-04

Pass 1 collected player history and a shallow parsed projection. Pass 2 deepens
the **existing frozen cohort** with the fields the report narrative needs and
pass 1 does not have. This document records what the sizing probe decided, what
was included and excluded and why, and how the collection is run, stopped,
resumed and verified.

```text
PHASE: V7_PASS2_DEEP_ACQUISITION
STATUS: IMPLEMENTED AND SMOKE-VERIFIED — full run not started
SPLIT: DISCOVERY only
CANDIDATE_TEST TOUCHED: NO
CALIBRATION_RESERVED / SEALED_VALIDATION TOUCHED: NO
PLAYBACK: NOT USED
COHORT: frozen, not regenerated, not topped up
```

## 1. What the probe decided

Probe report:
`.local/corpora/stratz/v7-pass2-probe/20260904T011031Z/report.json`
(4 physical calls).

| measured | result |
|---|---|
| largest workable batch | **8** — succeeded on the first rung, 66,123 bytes, no complexity failure |
| bytes per match | 8,265 |
| type shapes resolved | 16 of 16 |
| item vocabulary | usable — 575 items, 560 with a cost |
| `stats.locationReport` | **not usable** |

Production does not re-probe. The batch size is a constant the runner refuses to
override, because changing it silently would break the ledger's comparability
and re-open a question the probe already answered.

## 2. The sixteen resolved shapes: include or exclude

Every one was a deliberate decision, not a default.

### Included — analytical inputs

| field | fields kept | why |
|---|---|---|
| `match.towerDeaths` | `time`, `isRadiant`, `npcId`, `attacker` | The strongest proposed Finding — *does a won fight become a map* — was going to use tower **damage** as a proxy. These are the real objective timings. |
| `stats.itemUsed` | `itemId`, `count` | *Do you use your spike, or just buy it.* **Limitation:** counts only, no timestamps, so this answers "did you use it" and not "how soon after buying". |
| `stats.wardDestruction` | `time`, `isWard`, `gold`, `experience` | Dewarding. Support Findings otherwise only measure placing vision, never taking it away. |
| `player.abilities` | `abilityId`, `level`, `time`, `isTalent` | Skill build order and talent choices, with real timings. Level progression. |
| `match.pickBans` | `isPick`, `isRadiant`, `heroId`, `bannedHeroId`, `order`, `playerIndex`, `isCaptain`, `wasBannedSuccessfully` | Draft order and position. Nothing else exposes it. |
| `stats.matchPlayerBuffEvent` | `time`, `itemId`, `abilityId`, `stackCount` | Partially recovers item-usage **timing**, which `itemUsed` lacks: a buff-granting item consumption carries a timestamp. |
| `stats.farmDistributionReport` | `buyBackGold`, `abandonGold`, `creepLocation`, `neutralLocation` (each `id`, `count`, `gold`, `xp`) | **Lane versus jungle farm** — the signal the field audit explicitly asked for, and nothing else in the payload exposes it. Buyback spending is a tempo and desperation signal on top. |

### Included — quality and control metadata

`match.numHumanPlayers`, `match.isStats`, `match.statsDateTime` detect bot-filled
and unrecorded games. Their absence silently pollutes every denominator.

### Included — quarantined

`stats.actionsPerMinute` is collected but stored under
`quarantined_trajectories`, never alongside the analytical trajectories. Click
rate is a legitimate behavioural descriptor **and** correlates with skill; it
does not enter a Finding without an explicit hidden-skill-proxy review.

### Excluded, with reasons

| field | reason |
|---|---|
| `match.laneReport` | Its faction objects nest a third unresolved level; lane outcomes plus the own last-hit trajectory already answer the laning question. |
| `stats.heroDamageReport` | Traded for complexity budget — see §2b. |
| `stats.towerDamageReport` | Traded for complexity budget; `towerDamagePerMinute` and `towerDeaths` cover it. |
| `stats.locationReport` | Its resolved shape is `{positionX, positionY}` with **no time field**, so positions cannot be joined to a death or any other event. It cannot answer "where you die" even if it returned data — and in the probe it returned none. Excluded on shape evidence, not merely on the failed call. |
| `stats.inventoryReport` | Resolved as `{itemId, charges, secondaryCharges}` — an inventory snapshot. Final inventory is already captured via `item0Id`–`item5Id`, so it is redundant. |
| `match.towerStatus` | Resolved as tower HP and outpost control snapshots. Redundant against `towerDeaths` timings and the tower/barracks bitmasks. |
| `stats.abilityCastReport` | `targets` unresolved, and per-ability cast counts are mechanical-intensity data no defined research question needs. |
| `stats.actionReport` | Eleven attack/cast/move/ping counters. Adding them would widen the hidden-skill-proxy surface for no defined question. |
| `stats.courierKills` | No defined research question depends on it. |
| `pickBans.adjustedWinRate`, `pickBans.baseWinRate` | Proprietary win-rate predictions — a prohibited surface. |
| `player.roleBasic` | On the project's forbidden-token list since pass 1. The runner's own gate caught it during implementation; the rule was respected rather than weakened. |
| `player.abilities.abilityType` | Returns an object type needing a sub-selection. Rather than infer one, it was dropped — `abilityId` already identifies the ability. Found by the live smoke test. |

## 2b. Complexity is priced on query shape, not batch size

The single most consequential measurement of this phase, and it was not
anticipated.

A second sentinel resolved the eleven remaining second-level types, which made
lane-versus-jungle farm distribution and a full damage/crowd-control report
selectable. Adding both produced:

```text
Query is too complex to execute. Complexity is 379382; maximum allowed is 310000
```

...**at every batch size from 8 down to 1, with the identical number each time**.
STRATZ prices the selection set, not the number of matches. Shrinking the batch
cannot rescue a query that is too complex; only removing fields can. The probe
now stops laddering the moment it sees a complexity failure, rather than proving
the same thing six times.

Measured budget, by removal:

| query | complexity | fits |
|---|---:|---|
| v3.1.0 — 4 farm buckets + damage report | 379,382 | no |
| v3.2.0 — damage report removed | 369,782 | no |
| v3.3.0 — ancient and bounty buckets removed | 335,382 | no |
| **v3.4.0 — per-tower damage report removed** | **under 310,000** | **yes, batch 8** |

So the additions were paid for by trades, each one deliberate:

- **kept** `creepLocation` and `neutralLocation` — the explicit lane-versus-jungle
  requirement;
- **traded away** `ancientLocation` and `bountyGold` — the same question answered
  more coarsely;
- **traded away** `heroDamageReport` — my own addition, weaker justification than
  the audit's explicit request;
- **traded away** `towerDamageReport` — per-tower damage attribution, which
  `towerDamagePerMinute` and `towerDeaths` already cover between them.

Response size rose from 8,265 to 14,407 bytes per match, as expected.

## 3. Known gaps carried forward

1. **`match.laneReport` remains unresolved and is excluded.** Its faction objects
   nest a *third* level (`MatchStatsLaneReportFactionLaneObject`) that would need
   yet another introspection round. The recursion was stopped there: lane
   outcomes and the player's own last-hit trajectory already answer the laning
   question, so a third round would buy redundancy.
2. **Ancient-camp and bounty-rune gold are not separately attributed**, having
   been traded for the complexity budget. Lane and jungle are.
3. **`itemUsed` has no timestamps**, so spike-usage latency is only partially
   recoverable, through `matchPlayerBuffEvent`.
4. **Positional analysis remains out of scope.** Playback is prohibited and
   `locationReport` cannot support it.

## 4. The production contract

```text
operation           GetDeepMatchBatch v3.4.0
document sha256     45f600f0d13fe93d... (stamped in state, ledger and manifest)
batch size          8 (fixed; the runner refuses any other value)
match target        500 most recent parsed matches per account
accounts            300 DISCOVERY, frozen manifest order
```

The query digest is stamped into `state.json`, every ledger row, every
normalized document, and the run manifest. A resume against a corpus collected
with a different document is refused rather than silently mixing two contracts.

### Account and match ordering

Accounts: `DISCOVERY` only, sorted by frozen `source_position`, first 300.
Deterministic and non-adaptive — the list does not depend on how much data an
account turns out to have, because choosing the richest accounts is how a frozen
cohort becomes a convenience sample.

Matches: taken from the **pass-1 corpus**, not from the provider — the matches
pass 1 saw as parsed, ordered most-recent-first with the match id as tie-break,
capped at 500. The runner therefore depends on the pass-1 corpus, never on the
timestamped probe directory.

### Measured plan against the real cohort

```text
accounts planned                 300
accounts with pass-1 history     300
accounts with parsed matches     278   (22 have none and are recorded as such)
total planned matches            104,982
projected requests               13,253
```

Lower than the probe's 18,900 projection because the median account has ~350
parsed matches rather than 500.

## 4b. Rate control believes the provider, not a guess

The first live run paused at exactly 1,000 attempts. That was not the provider
saying stop — its own header at that moment reported **1,129 requests still
remaining that hour**. The ceiling was ours.

Measured provider limits, from live response headers:

```text
x-ratelimit-limit-second   8
x-ratelimit-limit-minute   150
x-ratelimit-limit-hour     1500
x-ratelimit-limit-day      15000
```

Pass 1 ran under hardcoded local ceilings of 5/second, 100/minute, 1,000/hour
and a planned daily cap of 9,000. Those were reasonable when nothing was known
about the key's real limits, but they are strictly below what it allows, and
`_effective_limits` takes the **minimum** of local and observed — so the local
guess won every time. For a 13,253-request collection the two binding caps cost
roughly four extra hours of hourly stalls, plus a potential wait to the next UTC
midnight once the 9,000 daily cap tripped.

`Pass2RateController` subclasses the pass-1 controller and changes two things:

- local window ceilings start at the provider's advertised limits rather than a
  fraction of them;
- there is no hardcoded daily cap. The pause decision reads the live
  `x-ratelimit-remaining-*` counters, which account for windows that reset
  mid-run and for any other session sharing the key.

A reserve is left unused in each window — 1/second, 10/minute, 40/hour,
150/day — because the counter is shared, and stopping short of zero is what
keeps a concurrent session from turning our last request into a 429.

STRATZ sends a reset header only for the per-second window, so an exhausted
minute, hour or day window waits to the next aligned boundary and re-checks.
Waiting slightly too long is cheap; guessing an early reset is a 429.

### The rolling-versus-clock mismatch

The first fix was not enough. The run stalled again at 5,500 attempts with the
provider's header reporting **1,194 requests still remaining that hour**.

The cause: our local backstop counts a *rolling* hour, while STRATZ resets on
the *clock*. A rolling window straddles two provider windows, so it reaches
1,500 while the provider — having reset in the middle — is still offering
hundreds. Observed hourly throughput shows it plainly: 1,354 in the 08:00 hour
and 1,429 in the 09:00 hour, but a rolling window spanning both counts well over
1,500.

The local windows are a backstop for missing headers and only that. Where the
provider reports what is left for a bucket, its number is now the only one
consulted for that bucket; the rolling count is skipped. A bucket the provider
does not report keeps its backstop.

Expected effect: about **9–10 hours** for the full run rather than a day and a
half, with pauses only when the provider itself is genuinely near a limit.

### Running it unattended

The supervisor is an ordinary foreground process and dies with its terminal.
One observed stall was simply that: the pause elapsed and nothing was alive to
resume it. For a multi-hour run, detach it — see §7.

## 5. Safety properties

- **Idempotent.** Every request is keyed by operation plus variables. A repeat
  is served from the immutable archive and issues no call, so rerunning a
  finished account produces no duplicate logical record.
- **Resumable.** Per-account `next_batch` checkpointing; a resume requests only
  outstanding batches.
- **Crash-safe.** State and canonical documents are written atomically; raw
  bodies are write-once. A body archived before its ledger row was appended no
  longer collides on resume — the archive takes the next free suffix, because
  the ledger, not the filename, binds a body to a request.
- **Self-repairing.** A completed account whose canonical document is missing is
  rebuilt from its normalized batches without a network call.
- **Fails closed.** Unrequested match, duplicate match, missing own-player row,
  forbidden provider field, or unexpected shape stops the run rather than
  writing a row that quietly means something else.
- **Bounded retries.** Transient 5xx, 429 and transport errors back off
  exponentially and honour `Retry-After`. Authentication failures, GraphQL
  errors and schema errors are never retried — including HTTP 400 selection-set
  rejections, which are classified as schema drift rather than transient.
- **No silent drops.** Accounts end in `complete`, `no_parsed_opportunities`, or
  `no_pass1_history`; matches the provider omits are listed in
  `missing_match_ids`.
- **No secrets.** Verified against the live smoke corpus: the token appears in
  no artifact, and no authorization header is retained.

## 6. Live smoke result

```text
command   collect --smoke  (3 accounts, 24 matches each, hard ceiling 15 requests)
physical calls   6
accounts         2 complete, 1 no_parsed_opportunities
verifier         complete: true, critical findings: none
matches          48, orphan raw bodies 0, duplicates 0
operation        GetDeepMatchBatch v3.4.0
```

Lane-versus-jungle farm arrives with real data. One sampled match:
3,492 gold from lane creeps against 4,538 from neutrals — a 57% jungle share,
which is exactly the kind of thing a player cannot see about themselves.

The smoke test paid for itself twice: it caught the `abilityType` selection-set
error on its first call, and confirmed every newly added field arrives with real
data — 27 tower deaths, 12 pick/bans, 21 ability levels, death timings, item
usage, ward destruction, and all twelve analytical trajectories, with
`actionsPerMinute` correctly quarantined.

## 7. Commands

```bash
# smoke — tiny, bounded, exercises the real pipeline end to end
uv run python scripts/stratz_v7_pass2_runner.py collect \
    --dotenv .env --smoke \
    --output-dir .local/corpora/stratz/v7-pass2-smoke \
    --acknowledge-network-collection

# verify any pass-2 corpus
uv run python scripts/stratz_v7_pass2_runner.py verify \
    --output-dir .local/corpora/stratz/v7-pass2-2026-09-04

# full production run, supervised through quota pauses.
# Detached, because the supervisor dies with its terminal and the run spans hours.
nohup uv run python scripts/stratz_v7_pass2_supervisor.py --dotenv .env \
    > .local/corpora/stratz/v7-pass2-supervisor.log 2>&1 &

# resume — identical command; the checkpoint decides what is outstanding
nohup uv run python scripts/stratz_v7_pass2_supervisor.py --dotenv .env \
    > .local/corpora/stratz/v7-pass2-supervisor.log 2>&1 &
```

Stopping is safe at any point: Ctrl-C leaves the checkpoint and the archive
intact, and the next run refetches nothing.
