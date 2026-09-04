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
| `stats.towerDamageReport` | `npcId`, `damage`, `damageCreeps`, `damageFromAbility` | Which tower, not just how much — a tier-1 and a tier-3 are different events for objective conversion. |
| `stats.farmDistributionReport` | `buyBackGold`, `abandonGold` | Buyback spending is a real tempo and desperation signal. **See §3** for what is missing here. |

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
| `stats.locationReport` | Its resolved shape is `{positionX, positionY}` with **no time field**, so positions cannot be joined to a death or any other event. It cannot answer "where you die" even if it returned data — and in the probe it returned none. Excluded on shape evidence, not merely on the failed call. |
| `stats.heroDamageReport` | All eight subfields are objects whose shapes are still unresolved. |
| `stats.inventoryReport` | All subfields unresolved; final inventory is already captured via `item0Id`–`item5Id`. |
| `match.laneReport` | Both subfields unresolved. |
| `match.towerStatus` | Both subfields unresolved; the tower and barracks bitmasks are already captured. |
| `stats.abilityCastReport` | `targets` unresolved, and per-ability cast counts are mechanical-intensity data no defined research question needs. |
| `stats.actionReport` | Eleven attack/cast/move/ping counters. Adding them would widen the hidden-skill-proxy surface for no defined question. |
| `stats.courierKills` | No defined research question depends on it. |
| `pickBans.adjustedWinRate`, `pickBans.baseWinRate` | Proprietary win-rate predictions — a prohibited surface. |
| `player.roleBasic` | On the project's forbidden-token list since pass 1. The runner's own gate caught it during implementation; the rule was respected rather than weakened. |
| `player.abilities.abilityType` | Returns an object type needing a sub-selection. Rather than infer one, it was dropped — `abilityId` already identifies the ability. Found by the live smoke test. |

## 3. Known gaps carried forward

1. **Lane-versus-jungle farm distribution is not obtainable yet.** The
   interesting parts of `farmDistributionReport` — `creepLocation`,
   `neutralLocation`, `ancientLocation`, `creepType`, `buildings`, `bountyGold`
   — are all nested objects whose shapes remain unresolved. Only the two scalar
   fields are collected. Resolving them needs one more introspection call
   against those second-level types, and would make it a v3.1 query.
2. **`itemUsed` has no timestamps**, so spike-usage latency is only partially
   recoverable, through `matchPlayerBuffEvent`.
3. **Positional analysis remains out of scope.** Playback is prohibited and
   `locationReport` cannot support it.

## 4. The production contract

```text
operation           GetDeepMatchBatch v3.0.0
document sha256     d75592bd5363ea77701839444c1d82394bb8d03ea31385d12ee13ce5437db6ab
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
```

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

# full production run, supervised through quota pauses
uv run python scripts/stratz_v7_pass2_supervisor.py --dotenv .env

# resume — identical command; the checkpoint decides what is outstanding
uv run python scripts/stratz_v7_pass2_supervisor.py --dotenv .env
```

Stopping is safe at any point: Ctrl-C leaves the checkpoint and the archive
intact, and the next run refetches nothing.
