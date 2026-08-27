# Luna Max — STRATZ Provider Migration

## Mission

Replace OpenDota with STRATZ as the upstream data provider for Free DNA, in an
isolated branch/worktree, preserving the analytical meaning of V6.1 as closely
as the two providers permit — and reporting honestly where they do not permit it.

You are implementing a **provider swap**, not an analytical redesign. STRATZ
exposes richer and more reliable fields than OpenDota. You may not use them to
change what a finding means. Every such opportunity belongs to the enrichment
track (`02-opus5-enrichment-research.md`) and must be recorded, not adopted.

Read `AGENTS.md` before you touch anything. This task is classified BACKEND +
ANALYTICAL-ADJACENT. It is not a UI task and not a release task.

---

## Current repository state

Captured by the architect at research time. Re-verify before starting; if these
differ, record the difference and continue from actual state.

| item | value |
|---|---|
| repository | `harunaka-manifesto/dota-report-card` |
| branch at capture | `codex/v61-motion-pacing` |
| HEAD at capture | `2ce777b84bd936a416dfdc7e8cac5d758c04ae57` |
| worktree at capture | clean (`git status --porcelain -uall` empty) |
| frozen analytical source SHA | `7df38e6d234ae9c4ee425490bc40b8cc92685f85` |
| frozen V6.1 artifact digest | `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0` |
| python | 3.11+ required (`datetime.UTC`) |
| package manager | `uv`; frontend `pnpm` |

The owner is actively working on the V6.1 presentation layer on
`codex/v61-motion-pacing`. Treat that branch as read-only source material.

---

## Production firewall

**LEAVE PRODUCTION ALONE.** You may not modify, deploy to, or reconfigure:

- `main`, `codex/v61-motion-pacing`, or any `release/*` or `backup/*` branch;
- production Vercel or Railway;
- production environment variables or secrets;
- production PostgreSQL or Redis;
- production feature flags (`FREE_DNA_V61_ENABLED` and siblings);
- release metadata or `.local/release/**`;
- frozen analytical artifacts under `.local/calibration/**` or
  `infra/runtime-artifacts/free_dna_v61/**`.

No deployment. No "temporary production test." No switching Railway to STRATZ.
Do not assume staging infrastructure exists — inspect first, and if it does not,
stop at `READY_FOR_STAGING_SMOKE`.

---

## Captured base SHA and branch/worktree strategy

```sh
git rev-parse HEAD                      # record this verbatim in your report
git status --porcelain --untracked-files=all
git worktree add ../dota-stratz-migration -b feat/stratz-provider-adapter HEAD
cd ../dota-stratz-migration
```

Work only inside that worktree. Never `git checkout` in the owner's working
copy. Never push to `main`. Do not delete the OpenDota implementation.

Note: `services/api/app/core/release.py::current_source_binding` runs
`git status --porcelain=v1 --untracked-files=all` and sets `dirty_worktree`.
Your new files will make the worktree dirty — that is expected inside your own
worktree and must never leak into a release identity computed elsewhere.

---

## Current OpenDota dependency map

Verified by reading the code, not by assumption. The historical paths given in
older project notes (`services/api/tests/...`, `app/clients/opendota*.py`) **do
not exist**. The real layout is below.

```text
POST /v1/analyses                        services/api/app/api/routes.py
  → AnalysisService.create_analysis      services/api/app/analysis/service.py
  → AnalysisService._run                 service.py:530
      ├─ source.get_player(account_id)                      [OpenDota /players/{id}]
      └─ source.get_summary_history_once(...)               [OpenDota /players/{id}/matches]
  → normalize_canonical_summary_history  app/ingestion/summary_history_contract.py
      └─ normalize_summary_rows          app/ingestion/summary_normalize.py
  → filter_history_window                app/ingestion/summary_normalize.py
  → infer_sessions                       app/dna/sessions.py
  → assemble_free_dna_report_v61         app/reports/dna_assembly_v61.py
  → validate_free_dna_report             app/api/report_schemas.py
  → repository.save_report_with_protected_cohorts   app/storage/repository.py
```

| stage | module | consumes | produces | provider-specific? |
|---|---|---|---|---|
| transport | `app/opendota/client.py` (`OpenDotaClient`) | HTTP | `list[dict]` raw rows | **yes** — REST, OpenDota query params, `Retry-After`, `OpenDotaRateLimited`/`OpenDotaUnavailable` |
| source protocol | `app/analysis/source.py` (`AnalysisSource`) | — | 4 async methods | **shape is OpenDota's** — `get_matches`, `get_summary_history_once(days, project, provider_limit)` |
| fixture source | `app/analysis/source.py` (`FixtureOpenDotaSource`, `MappingSource`) | JSON on disk | same | yes |
| projection + audit | `app/ingestion/summary_history_contract.py` | raw OpenDota rows | `CanonicalSummaryHistory` | **yes** — 20 named OpenDota fields, `provider_version="opendota-summary-2.0.0"`, `request_count == 1` |
| normalization | `app/ingestion/summary_normalize.py` | projected rows | `NormalizedSummaryMatch` | **mostly** — consumes `player_slot`, `radiant_win`, integer `game_mode`/`lobby_type`/`leaver_status`/`lane_role` |
| analysis | `app/player_analysis_v6/**`, `app/player_analysis_v61/**`, `app/behavior/**` | `NormalizedSummaryMatch` | elements, findings | **no** — provider-neutral |
| report | `app/reports/dna_assembly_v61.py` | matches + `CanonicalSummaryHistory` | report dict | **leaks** — embeds `audit.as_dict()` verbatim |
| persistence | `app/storage/repository.py`, `app/storage/models.py` | payload + metadata | `raw_payloads` row | **soft** — `metadata_json` is free-form JSON; no `provider` column |

### The two provider calls Free DNA V6.1 actually makes

1. `source.get_player(account_id)` — OpenDota `/players/{id}`. Consumed only by
   `_profile_for_report` (service.py:1236) for `personaname`, `avatarfull`,
   `rank_tier`, and by `_identity_fingerprint`. Note `profile_url` is hardcoded
   to `https://www.opendota.com/players/{account_id}`.
2. `source.get_summary_history_once(account_id, days=365, project=SUMMARY_HISTORY_PROJECTION, provider_limit=10_000)`
   — one physical OpenDota request.

Deep Scan (`app/analysis/deep_scan.py`, `source.get_match`) is **out of scope**.
Free DNA has `detail_requests: 0, parse_requests: 0`.

---

## Current analytical input contract

**Case B** — a semi-normalized internal representation that still carries
OpenDota assumptions. Evidence:

- `SUMMARY_HISTORY_PROJECTION` (`summary_history_contract.py`) names 20 OpenDota
  field names verbatim and is used as the literal `project` query parameter.
- `summary_normalize._normalize_row` derives `side` from `player_slot < 128`,
  `won` from `radiant_win` XOR side, and reads integer `game_mode`,
  `lobby_type`, `leaver_status`, `lane_role`, `lane`, `is_roaming`.
- `SUPPORTED_ALL_PICK_MODES = {1, 22}` and `SUPPORTED_LOBBY_TYPES = {0, 7}` are
  Valve integer ids reached through OpenDota.
- Downstream of `NormalizedSummaryMatch`, nothing consumes OpenDota. `grep -rin
  "opendota" services/api/app/player_analysis_v6* services/api/app/behavior
  services/api/app/dna services/api/app/reports` returns exactly one hit: a
  docstring in `app/behavior/__init__.py` stating that the package "does not
  import an OpenDota transport client." No code path below the seam does.

**The smallest safe seam is therefore `NormalizedSummaryMatch`**, and the
adapter boundary belongs between the transport and
`normalize_canonical_summary_history`. Do not push provider knowledge past it.

### The invariant that blocks a drop-in swap

`summary_history_contract.normalize_canonical_summary_history` opens with:

```python
if request_count != 1:
    raise ValueError("Free DNA V6.1 requires exactly one physical history request")
```

`request_manifest()` publishes `"physical_request_count": 1`, and
`dna_assembly_v61.py:1361` embeds `canonical_history.audit.as_dict()` into the
report as `history_contract`. `request_count`, `provider_version`,
`schema_version` and both payload hashes are **published report fields**, and
`tests/unit/test_v61_contract_boundaries.py` and
`tests/unit/test_v61_canonical_corpus.py` assert on them.

STRATZ caps `take` at 100 (see below). A 365-day history is therefore multiple
requests. **Exact V6.1 parity under `summary-history-schema-3.0.0` is
impossible.** This is not a tolerance question; it is a contract-version
question. Phase 2 below tells you what to do about it.

---

## Verified STRATZ API facts

Verified against the live API and live introspection on 2026-08-27. Anything not
listed here is `UNKNOWN — requires owner/STRATZ confirmation`.

| item | value | source |
|---|---|---|
| endpoint | `https://api.stratz.com/graphql` | live |
| GraphiQL | `https://api.stratz.com/graphiql` | live |
| auth | `Authorization: Bearer <token>` | live |
| **User-Agent** | must be exactly `STRATZ_API`; other values get a Cloudflare HTML interstitial with HTTP 403 and the token is never evaluated | observed |
| token source | `https://stratz.com/api` after Steam login | STRATZ KB |
| Default token limits | 20/s, 250/min, 2 000/hour, 10 000/day | STRATZ KB issue #15 |
| Individual token | 20/s, 250/min, 4 000/hour, 20 000/day | STRATZ KB issue #15 |
| Multi-token | per-user: 20/s, 20/min, 50/hour, 100/day | STRATZ KB issue #15 |
| **`take` ceiling** | **100**. `take: 250` returns `null` for that field plus a GraphQL error: `"You have surpassed the maximum take value of :  100"` | observed |
| pagination | `request.take` / `request.skip`; also `after` / `before` (`Long`) and `orderBy` (`FindMatchPlayerOrderBy`) | introspection |
| default ordering | `startDateTime` descending | observed |
| partial responses | HTTP 200 with **both** `data` (some fields populated, offending fields `null`) **and** `errors` | observed |
| rate-limit headers | none observed on the responses captured | observed |
| storage / caching terms | `UNKNOWN — requires owner/STRATZ confirmation` | — |
| attribution requirement | `UNKNOWN — requires owner/STRATZ confirmation` | — |
| commercial-use terms | `UNKNOWN — requires owner/STRATZ confirmation` | — |
| schema deprecation policy | `UNKNOWN — requires owner/STRATZ confirmation` | — |

The four `UNKNOWN` rows are **blocking for production**, not for local work. Do
not resolve them by guessing. Surface them in your final report.

### Observed request cost

A specimen account returned 100 matches spanning 61.1 days (1.64 matches/day),
extrapolating to ~597 matches per 365-day window ≈ **6 physical requests**. A
heavy player at 5 matches/day reaches ~1 825 matches ≈ **19 requests**. Budget
for a worst case near the `MAX_PAGES` ceiling you choose and make it explicit.

---

## Verified GraphQL operations relevant to parity

Field names below are from live introspection. Do not substitute remembered
names. Rank/MMR surfaces (`actualRank`, `averageRank`, `bracket`, `averageImp`,
`behaviorScore`, `seasonRank`) are **deliberately absent** — the V6.1 audit
asserts `rank_or_mmr_used: False` and `FORBIDDEN_ANALYTICAL_FIELDS` bans them.
Do not add them to the parity document for any reason.

```graphql
query V61History($id: Long!, $start: Long!, $end: Long!, $take: Int!, $skip: Int!) {
  player(steamAccountId: $id) {
    steamAccountId
    matchCount
    steamAccount { id name avatar isAnonymous isStratzPublic }
    matches(request: {
      startDateTime: $start
      endDateTime: $end
      take: $take
      skip: $skip
    }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      endDateTime
      lobbyType
      gameMode
      gameVersionId
      clusterId
      regionId
      leagueId
      isStats
      parsedDateTime
      players(steamAccountId: $id) {
        steamAccountId
        playerSlot
        isRadiant
        isVictory
        heroId
        variant
        kills
        deaths
        assists
        leaverStatus
        partyId
        isRandom
        lane
        position
        role
        roleBasic
      }
    }
  }
}
```

`PlayerMatchesRequestType` input fields (introspected, complete): `matchIds`,
`leagueId`, `leagueIds`, `seriesId`, `teamId`, `teamIdSteamAccount`, `isParsed`,
`startDateTime`, `endDateTime`, `gameModeIds`, `lobbyTypeIds`, `gameVersionIds`,
`regionIds`, `rankIds`, `bracketIds`, `isStats`, `heroIds`, `laneIds`,
`roleIds`, `positionIds`, `awardIds`, `isParty`, `hasAward`,
`withFriendSteamAccountIds`, `withEnemySteamAccountIds`, `withFriendHeroIds`,
`withEnemyHeroIds`, `isVictory`, `isRadiant`, `minGameVersionId`,
`maxGameVersionId`, `minImp`, `maxImp`, `playerList`, `take`, `skip`, `after`,
`before`, `orderBy`.

**Do not filter server-side by `gameModeIds` / `lobbyTypeIds`.** V6.1 owns
eligibility in `summary_normalize._eligibility` and records every exclusion in
the ledger. Filtering upstream would silently empty the exclusion ledger and
change `processed_matches`, which is a published report field.

### Enum ordinals are Valve's integer ids

Verified by introspection and corroborated by `gameModeIds`/`lobbyTypeIds`
being `[Byte]`:

- `GameModeEnumType` index 1 = `ALL_PICK`, 22 = `ALL_PICK_RANKED`, 23 = `TURBO` —
  matching `SUPPORTED_ALL_PICK_MODES = {1, 22}`.
- `LobbyTypeEnum` index 0 = `UNRANKED`, 7 = `RANKED` — matching
  `SUPPORTED_LOBBY_TYPES = {0, 7}`.
- `LeaverStatusEnum` index 0..8 = `NONE`, `DISCONNECTED`,
  `DISCONNECTED_TOO_LONG`, `ABANDONED`, `AFK`, `NEVER_CONNECTED`,
  `NEVER_CONNECTED_TOO_LONG`, `FAILED_TO_READY_UP`, `DECLINED_READY_UP`.
- `MatchLaneType`: `ROAMING`, `SAFE_LANE`, `MID_LANE`, `OFF_LANE`, `JUNGLE`, `UNKNOWN`.
- `MatchPlayerPositionType`: `POSITION_1`..`POSITION_5`, `UNKNOWN`, `FILTERED`, `ALL`.
- `MatchPlayerRoleType`: `CORE`, `LIGHT_SUPPORT`, `HARD_SUPPORT`, `UNKNOWN`.
- `LaneOutcomeEnums`: `TIE`, `RADIANT_VICTORY`, `RADIANT_STOMP`, `DIRE_VICTORY`, `DIRE_STOMP`.

Encode these as an explicit checked-in mapping table with a version string. Do
not compute them from enum ordering at runtime — STRATZ may append values.

---

## Field-level OpenDota → canonical → STRATZ map

Every field in `SUMMARY_HISTORY_PROJECTION`, in projection order. "Consumers"
names the code that reads the canonical field.

| # | analytical requirement | OpenDota field | canonical field | consumers | STRATZ path | equivalence | unit / enum difference | nullability risk | migration action |
|---|---|---|---|---|---|---|---|---|---|
| 1 | match identity | `match_id` | `match_id` | dedupe, ledger, sessions | `matches[].id` | `EXACT` | `Long` vs int | none | cast to int |
| 2 | side | `player_slot` | `side` | `_normalize_row`, `derive_player_won` | `players[].playerSlot`, `players[].isRadiant` | `NORMALIZABLE` | STRATZ gives the boolean directly | none observed | prefer `isRadiant`; keep `playerSlot` for the ledger |
| 3 | match result | `radiant_win` | `won` | outcome, resilience, transfer, post-loss | `matches[].didRadiantWin`, `players[].isVictory` | `NORMALIZABLE` | `isVictory` is already player-relative | none observed | set `radiant_win` from `didRadiantWin` **and** cross-check against `isVictory`; disagreement is a hard error, not a fixup |
| 4 | duration | `duration` | `duration_seconds` | involvement, exposure, eligibility (`>= 300`) | `matches[].durationSeconds` | `EXACT` | seconds both | none | direct |
| 5 | game mode | `game_mode` | `game_mode` | `SUPPORTED_ALL_PICK_MODES` | `matches[].gameMode` | `NORMALIZABLE` | enum string vs Valve int | none | table-map; `ALL_PICK`→1, `ALL_PICK_RANKED`→22 |
| 6 | lobby type | `lobby_type` | `lobby_type` | `SUPPORTED_LOBBY_TYPES` | `matches[].lobbyType` | `NORMALIZABLE` | enum string vs Valve int | none | table-map; `UNRANKED`→0, `RANKED`→7 |
| 7 | hero | `hero_id` | `hero_id` | breadth, toolkit, taxonomy | `players[].heroId` | `EXACT` | same Valve namespace | none observed | direct |
| 8 | chronology | `start_time` | `started_at` | sessions, windows, drift, post-loss | `matches[].startDateTime` | `EXACT` | Unix seconds both | none observed | direct |
| 9 | parse provenance | `version` | `source_version` | audit only | — | **`NOT_AVAILABLE`** | `parsedDateTime` is a timestamp, not a parser revision | always null | set null; record in audit; **do not substitute `parsedDateTime`** |
| 10 | kills | `kills` | `kills` | involvement, finishing, orientation | `players[].kills` | `EXACT` | — | none observed | direct |
| 11 | deaths | `deaths` | `deaths` | death exposure | `players[].deaths` | `EXACT` | — | none observed | direct |
| 12 | assists | `assists` | `assists` | involvement, finishing | `players[].assists` | `EXACT` | — | none observed | direct |
| 13 | abandon state | `leaver_status` | `leaver_status` | eligibility (`abandoned`, `invalid_leaver_status`) | `players[].leaverStatus` | **`SEMANTICALLY_DIFFERENT`** | STRATZ defines 9 values; `_VALID_LEAVER_STATUSES = range(6)` | values 6/7/8 unrepresentable | see risk R2 |
| 14 | party context | `party_size` | `party_size` | optional coverage only | `players[].partyId` | **`NOT_AVAILABLE`** | id, not a size | already <80% on OpenDota | set null; document; do not fetch 10 players for parity |
| 15 | hero facet | `hero_variant` | `hero_variant` | optional coverage only | `players[].variant` | `UNKNOWN` | facet index origin unverified | `0` throughout the specimen | map through, mark `UNKNOWN`, exclude from claims until verified |
| 16 | league exclusion | `leagueid` | (`pro_or_league`) | eligibility | `matches[].leagueId` | `EXACT` | — | null for pubs | direct |
| 17 | region | `cluster` | `region` | ledger only | `matches[].clusterId` / `regionId` | `NORMALIZABLE` | STRATZ separates cluster and region | none observed | map `clusterId`→`cluster` |
| 18 | lane placement | `lane` | `lane` | role hint only | `players[].lane` | `NORMALIZABLE` | enum vs int | 93% in specimen | table-map |
| 19 | role context | `lane_role` | `lane_role` → `role_hint` | role eligibility, role-adjusted normalization | `players[].lane` **or** `players[].position` | **`SEMANTICALLY_DIFFERENT`** | see risk R3 | 93% / 91% | see risk R3 |
| 20 | roaming | `is_roaming` | `is_roaming` | role hint (0.72 confidence) | `players[].lane == "ROAMING"` | `NORMALIZABLE` | derived, not a field | none in specimen | derive |

Fields present on STRATZ but **excluded from the parity projection**:
`isStats`, `gameVersionId`, `parsedDateTime`, `regionId`, `role`, `roleBasic`,
`position`, `isRandom`, `imp`, `award`, `networth`, and everything under
`stats`/`playbackData`. Carry `parsedDateTime`, `gameVersionId` and `isStats`
into the **audit** (they are provenance) and nothing else. Everything else is
enrichment-track material.

---

## Semantic-equivalence risks

These are the findings that must not be quietly smoothed over. Each is measured
against the checked-in specimen at `.local/stratz-probe/specimen/`.

### R1 — the one-request invariant (BLOCKING for parity)

STRATZ caps `take` at 100. `normalize_canonical_summary_history` raises unless
`request_count == 1`, and `request_count` is published inside the report's
`history_contract`. There is no way to satisfy both.

**Required action:** introduce `summary-history-schema-4.0.0` /
`summary-projection-4.0.0` / `<provider>-summary-1.0.0` as a *new, additive*
contract version. Do not mutate the 3.0.0 constants. Specifically:

- keep `normalize_canonical_summary_history` byte-identical for OpenDota;
- add a sibling entry point accepting `request_count >= 1` plus a page ledger;
- redefine completeness: today it is `raw_count >= provider_limit →
  possibly_truncated`. Under pagination, truncation means "the page ceiling was
  reached before a short page appeared." A year of ~600 rows would read
  `complete` under the old rule while actually being capped. Getting this wrong
  silently re-enables `pool_shape` findings that
  `dna_assembly_v61.py:1258` is supposed to suppress;
- deterministic page ordering: pages arrive `startDateTime` descending; sort and
  dedupe by `match_id` before hashing so `normalized_payload_sha256` is stable
  regardless of page boundaries.

### R2 — `leaverStatus` has three values V6.1 cannot express

`_VALID_LEAVER_STATUSES = frozenset(range(6))`. STRATZ ordinals 6
(`NEVER_CONNECTED_TOO_LONG`), 7 (`FAILED_TO_READY_UP`), 8 (`DECLINED_READY_UP`)
fall outside it, so a naive ordinal map marks those rows
`invalid_leaver_status` and drops them from **every** dimension.

Neither of the two obvious fixes is neutral: widening the valid set changes
eligibility, and folding 6/7/8 into `abandoned` changes the abandon population.

**Required action:** map ordinals 0–5 directly. For 6/7/8, emit an explicit new
canonical value and a new exclusion reason `provider_leaver_status_unmapped`,
count it in the audit, and **report the count**. Do not choose a semantic on the
owner's behalf. In the specimen only `NONE` and `DISCONNECTED` appear, so the
expected blast radius is small — prove that on the real corpus.

### R3 — role: three candidate sources, none of them parity

`summary_normalize.ROLE_HINTS` maps `lane_role` 1–5 to
carry/mid/offlane/jungle/roamer and the module's own comment says OpenDota's
`lane_role` "is a lane/context enum, not a position-1..5 enum." STRATZ offers
three different things:

| source | specimen coverage | maps to `lane_role`? |
|---|---|---|
| `players[].lane` | 93 / 100 | yes, one-to-one with the lane enum |
| `players[].position` | 91 / 100 | only lossily — `POSITION_4`/`POSITION_5` have no lane-enum equivalent |
| `players[].roleBasic` | **100 / 100** | **never use** |

Measured on the specimen with the repository's own normalizer:

- role-eligible under `lane`: **49**; under `position`: **47**;
- the two disagree on **16 of 91** rows (17.6%) where both exist;
- 12 of those 16 are `OFF_LANE` + `POSITION_4` — soft supports that the
  lane-shaped mapping labels `offlane`, which `ROLE_HINTS` treats as a **core**
  role. Parity-shaped mapping actively mislabels ~13% of matches.

**`roleBasic` is a fabrication trap.** On all nine unparsed specimen matches
`lane`, `position` and `role` are `null` while `roleBasic` still reads `"CORE"`.
It is a default, not an observation. Feeding it into a normalizer whose contract
is "a missing field never silently becomes a behavioural zero" would be the
worst defect available in this migration.

**Required action for parity:** use `players[].lane` only, mapped
`SAFE_LANE`→1, `MID_LANE`→2, `OFF_LANE`→3, `JUNGLE`→4, `ROAMING`→5, with
`is_roaming = (lane == "ROAMING")`. Drop `position`, `role` and `roleBasic` at
the adapter boundary. Record in your report that `position` exists and that
adopting it is a Project B decision.

### R4 — coverage improvement is itself an analytical change

OpenDota's own specimen (`research/free-dna-v6.1-cheap-history-ceiling.md`)
reports `lane`/`lane_role` at roughly 2.5% coverage. STRATZ delivers 93%. Same
formula, ~37× the eligible population for every role-gated element and for
`role_adjusted_provisional` normalization. Elements will move even though no
code changed.

**Required action:** this is expected, must be measured, and must **not** be
suppressed. Report per-dimension eligible counts before and after. Do not tune
thresholds to make the numbers match.

### R5 — cache-key collision would relabel history as STRATZ-derived

`canonical_summary_history_cache_key()` returns
`/players/{id}/matches/v61-canonical` — provider-neutral in name, OpenDota in
fact. `raw_payloads` is keyed `(endpoint, source_id, payload_hash)` with no
`provider` column. A STRATZ adapter reusing that key would serve OpenDota rows
to a STRATZ run and permanently blur provenance.

**Required action:** namespace the key by provider, e.g.
`/stratz/players/{id}/matches/v61-canonical`. Never rewrite existing rows.

### R6 — partial GraphQL responses

Q2 returned HTTP 200 carrying both populated `data` fields and two `errors`
entries, with the offending aliases `null`. A client that treats any `errors` as
failure discards good pages; one that ignores `errors` reads `null` as "no
matches" and silently truncates a year.

**Required action:** on any response where `errors` is non-empty, fail the page
loudly with the error messages attached. Never treat `data.player.matches ==
null` as an empty page.

### R7 — `profile_url` is hardcoded to opendota.com

`service.py:1264` emits `https://www.opendota.com/players/{account_id}` into
every report. Under STRATZ this is a false provenance claim.

**Required action:** make it provider-derived. Changing it alters a published
report field — flag it, do not change persisted reports.

### R8 — the audit is a published report field

`dna_assembly_v61.py:1361` embeds `canonical_history.audit.as_dict()` as
`history_contract`, and `raw_payload_hash` / `history_hash` derive from it.
Changing `provider_version` changes report content by construction. Byte-identical
reports across providers are **not achievable and must not be a success
criterion.** Your parity target is identical *analytical* output: same eligible
set, same feature vectors, same qualified findings.

---

## Target provider architecture

The repository already has a usable seam (`AnalysisSource`), but its method
signatures are OpenDota-shaped. Widen it minimally; do not build a universal
provider framework.

```text
StratzGraphQLClient  ──┐
OpenDotaClient       ──┤→ HistoryProvider (protocol)
                       │     .fetch_profile(account_id) -> CanonicalProfile
                       │     .fetch_summary_history(account_id, window) -> ProviderHistory
                       ↓
              ProviderHistory { rows: list[CanonicalProjectionRow],
                                ledger: RequestLedger,
                                provenance: ProviderProvenance }
                       ↓
   normalize_canonical_summary_history_v4(...)   # additive; 3.0.0 untouched
                       ↓
              NormalizedSummaryMatch  ← unchanged seam
                       ↓
       existing V6.1 analysis and report assembly  ← unchanged
```

Rules:

- Provider-specific enums, null handling, units, GraphQL structure, pagination
  and API errors are normalized **at the provider boundary**. Nothing below it
  learns the provider's name.
- No `if provider == "stratz":` anywhere in `app/player_analysis_v6*`,
  `app/behavior`, `app/reports`, or `app/dna`.
- `OpenDotaClient` keeps working unchanged and remains the rollback path.
- `AnalysisSource` stays in place for Deep Scan; do not refactor Deep Scan.

---

## Phase 0 — workspace safety

1. `git rev-parse HEAD`; record verbatim.
2. `git status --porcelain -uall`; record.
3. Create the worktree and branch as above.
4. Confirm `.env` is untouched and `OPENDOTA_*` values are unchanged.
5. Confirm no `STRATZ_*` value is written to any tracked file.

Stop and report if the worktree is dirty in a way you did not create.

## Phase 1 — characterize the existing contract

Before writing provider code, capture the current behaviour as executable truth.

1. Run the existing suite and record the baseline: `uv run pytest -q`.
2. Write a characterization test that pins the current OpenDota path end to end
   from `tests/fixtures/opendota/matches_193875165.json` through
   `normalize_canonical_summary_history` to
   `NormalizationResult.as_dict()` — eligible ids, exclusion reasons,
   `normalized_payload_sha256`. This is your regression anchor.
3. Record `request_manifest()` output verbatim into a fixture.

Do not modify any existing test to make this easier.

## Phase 2 — canonical provider seam

1. Add `app/providers/` with `HistoryProvider`, `ProviderHistory`,
   `RequestLedger`, `ProviderProvenance`.
2. Add `summary-history-schema-4.0.0` alongside 3.0.0 in
   `app/ingestion/summary_history_contract.py`. **Additive only.** The 3.0.0
   constants, `normalize_canonical_summary_history`, and `request_manifest()`
   keep their exact current behaviour, including the `request_count != 1` raise.
3. Define the 4.0.0 completeness rule explicitly (see R1) and unit-test the
   page-ceiling case.
4. Wrap `OpenDotaClient` as `OpenDotaHistoryProvider` emitting a single-page
   ledger, and prove Phase 1's characterization test still passes through it.

## Phase 3 — STRATZ GraphQL client

New module `app/stratz/client.py`. Requirements:

- named operations, one document per operation, checked in as constants;
- variables, never string interpolation of the account id;
- minimal field selection — exactly the parity document above;
- `Authorization: Bearer`, `User-Agent: STRATZ_API` (exact), `Accept-Encoding: gzip`;
- timeout from settings, default 45s;
- retry with backoff on 429/5xx only, honouring `Retry-After`; never retry 4xx;
- **`errors` non-empty ⇒ raise**, with messages attached (R6);
- typed response validation; unknown fields ignored, missing required fields fatal;
- pagination: `take=100`, `skip += 100`, stop on a short page, hard ceiling
  `STRATZ_MAX_HISTORY_PAGES` (default 25 → 2 500 matches);
- request counting into `RequestLedger`;
- distinct exception types mirroring `app/core/errors.py` conventions
  (`StratzRateLimited`, `StratzUnavailable`, `StratzPartialResponse`);
- **never** log the token, and never log a full player payload.

Detect the Cloudflare interstitial explicitly: HTTP 403 with an HTML body is a
User-Agent/edge problem, not an auth problem, and must say so in the error.

## Phase 4 — normalization

New module `app/stratz/normalize.py`. Maps a STRATZ page into
`CanonicalProjectionRow` using the checked-in enum tables. Deterministic:
same input bytes ⇒ same output, including ordering. Implements R2 and R3
exactly as specified. Drops `position`, `role`, `roleBasic`, and every
rank/MMR surface.

The specimen and its analyzer at `.local/stratz-probe/` are your reference
implementation — the checked-in TSV, `tsv_to_stratz.py`, and
`stratz_to_canonical.py` reproduce the numbers quoted in R3.

## Phase 5 — raw cache and provenance

- Provider-namespaced cache key (R5).
- Store provenance in the existing `raw_payloads.metadata_json`; **no database
  migration is required** — `metadata_json` is `JSON`/`JSONB` free-form.
- Record: `provider`, `provider_version`, `operation_name`, `document_sha256`,
  `request_count`, `page_count`, `fetched_at`, `normalizer_version`,
  `raw_payload_sha256`, `completeness`, `parsed_coverage`.
- Never rewrite or relabel an existing row. Existing OpenDota payloads stay
  OpenDota-derived forever.

If you conclude a schema migration is genuinely needed, **stop** and report it
separately: local/staging work, production prerequisites, forward compatibility,
rollback, owner approval.

## Phase 6 — configuration and secrets

Follow the existing style in `app/core/config.py` (`Settings.from_env`, an
`APP_ENV=production` validation block, `SUPPORTED_OPENDOTA_SOURCES`).

Introduce:

```
DATA_PROVIDER=opendota|stratz      # default opendota
STRATZ_API_TOKEN=                  # backend only, never committed, never logged
STRATZ_BASE_URL=https://api.stratz.com/graphql
STRATZ_TIMEOUT_SECONDS=45
STRATZ_MAX_RETRIES=3
STRATZ_MAX_HISTORY_PAGES=25
STRATZ_SOURCE=fixture|live         # mirrors OPENDOTA_SOURCE semantics
```

Add them to `.env.example` with empty secret values. Extend
`validate_runtime_configuration` so `APP_ENV=production` with
`DATA_PROVIDER=stratz` requires a token and `STRATZ_SOURCE=live`. Add the token
to the `configure_logging` redaction tuple in `main.py` alongside
`opendota_api_key` and `steam_api_key`. **Do not touch the real `.env`.**

## Phase 7 — adapter tests

Recorded/synthetic fixtures under `tests/fixtures/stratz/`. No live calls.
Cover: nulls; unparsed matches (`parsedDateTime: null` with null lane/position/
role but non-null `roleBasic`); pagination including a short final page and the
ceiling; duplicate `match_id` across pages; out-of-order pages; every enum
value including `leaverStatus` 6/7/8; timestamp handling; partial `data` +
`errors`; HTTP 403 with HTML body; 429 with and without `Retry-After`; 5xx;
timeout; malformed JSON; anonymous/private players (`isAnonymous`,
`isStratzPublic`); Turbo and other excluded modes.

Add a guard that fails any test making an unexpected outbound request —
including to OpenDota — during STRATZ tests.

## Phase 8 — canonical parity tests

For equivalent fixture data, assert `OpenDota fixture → canonical` and
`STRATZ fixture → canonical` agree field by field across all 20 projection
fields, and emit an explicit diff on failure. Fields 9 (`version`) and 14
(`party_size`) are expected `NOT_AVAILABLE` — assert that they are null and that
the audit records why, rather than excluding them from the comparison.

No tolerances. If a field cannot match, it is a finding, not a rounding error.

## Phase 9 — V6.1 analytical regression

Reuse stored development/fixture corpora. **Do not make fresh OpenDota calls to
build a baseline. Do not touch the sealed holdout under
`.local/calibration/v61/release-recovery-7df38e6/sealed-holdout/`.**

Compare, for the same account and window:

- eligible match set (ids, not just counts);
- exclusion-reason histogram;
- chronological ordering and session assignment;
- element point estimates and intervals;
- candidate findings, q-values, qualification decisions;
- published findings and supporting evidence;
- serialized report, excluding the audit fields R8 says must differ.

Deterministic in, deterministic out. Any drift is reported with the field that
caused it.

## Phase 10 — optional bounded staging smoke

Only if **all** hold: a STRATZ credential exists; the owner has authorized it in
writing; a safe non-production scope exists; Phases 7–9 pass.

Bounded: one account, one window, STRATZ only, recorded. Capture operation
names, request count, page count, match counts, normalized counts, missing-field
counts, and any API errors. Never log the token.

If credentials or authorization are absent, stop and report
`READY_FOR_STAGING_SMOKE`. Do not improvise.

---

## Observability

Emit through `app/core/metrics.record_metric`, mirroring the existing
`opendota.*` names: `stratz.request.attempt`, `stratz.response`,
`stratz.graphql.error`, `stratz.partial_response`, `stratz.throttled`,
`stratz.retry`, `stratz.cache.hit`, `stratz.pages_fetched`,
`stratz.matches_returned`, `stratz.matches_normalized`,
`stratz.rows_missing_required`, `stratz.rows_missing_optional`,
`stratz.leaver_status_unmapped`.

Log context: provider, operation name, request count, latency, page index,
normalizer version. Never the token, never a full payload.

## Failure modes

| failure | expected behaviour |
|---|---|
| 403 + HTML body | raise with "Cloudflare edge challenge — check `User-Agent: STRATZ_API`", not "auth failed" |
| 401/403 + JSON | token rejected; surface, do not retry |
| `errors` non-empty | raise `StratzPartialResponse` with messages; never partial-accept |
| `take` rejected | clamp to 100 and record; do not silently retry forever |
| page ceiling hit | mark completeness truncated; suppress completeness-dependent claims |
| duplicate `match_id` across pages | dedupe deterministically, record in `duplicate_conflicts` |
| private/anonymous player | surface as `ProfileUnavailable`, matching current behaviour |
| account has <30 eligible | `InsufficientMatchHistory`, unchanged |

## Rollback

`DATA_PROVIDER=opendota` restores the previous path completely. Keep
`OpenDotaClient`, `FixtureOpenDotaSource`, `tests/fixtures/opendota/**` and
`summary-history-schema-3.0.0` intact and passing. Removing OpenDota is a later
cleanup requiring separate authorization. Prove rollback by running the full
suite with `DATA_PROVIDER=opendota` at the end.

## Explicit non-goals

- No change to any V6.1 formula, threshold, q-value boundary, multiplicity rule,
  eligibility rule, sample unit, finding identifier, or copy.
- No adoption of `position`, `role`, `imp`, `award`, `networth`, `isStats`,
  lane outcomes, or any `stats`/`playbackData` field.
- No rank or MMR field anywhere in the canonical model.
- No Deep Scan changes. No UI changes. No frontend changes.
- No deployment, no production configuration, no database migration.
- No deletion of OpenDota code.
- No modification of frozen calibration artifacts or the sealed holdout.

## Files expected to change

New:
`services/api/app/providers/__init__.py`, `.../models.py`, `.../protocol.py`;
`services/api/app/stratz/__init__.py`, `.../client.py`, `.../normalize.py`,
`.../enums.py`, `.../errors.py`;
`tests/fixtures/stratz/**`;
`tests/unit/test_stratz_client.py`, `test_stratz_normalize.py`,
`test_provider_parity.py`, `test_v61_provider_regression.py`.

Modified (additively):
`services/api/app/ingestion/summary_history_contract.py` (4.0.0 alongside 3.0.0);
`services/api/app/core/config.py`; `services/api/app/main.py` (provider
selection + token redaction); `services/api/app/analysis/service.py` (provider
indirection only); `.env.example`; `docs/architecture/data-provenance.md`.

Must not change: `app/player_analysis_v6/**`, `app/player_analysis_v61/**`,
`app/behavior/**`, `app/dna/**`, `app/reports/**` (except R7 if authorized),
`app/opendota/**`, `.local/**`, `infra/runtime-artifacts/**`.

## Tests and commands

```sh
uv run pytest -q                       # full suite
uv run pytest -q tests/unit            # unit
uv run pytest -q tests/contract        # contract
uv run pytest -q tests/integration     # integration
make lint                              # ruff + next lint
make typecheck                         # mypy + tsc
```

Live smoke is opt-in and OpenDota-specific today (`tests/live/test_live_smoke.py`,
`pytest.mark.live`, gated on `RUN_LIVE_SMOKE=1`). Mirror that pattern for STRATZ;
do not weaken the gate.

## Blocked conditions

Stop and report rather than improvising if:

- the owner has not decided the R2 `leaverStatus` 6/7/8 semantic;
- the owner has not approved a new history-contract version (R1);
- STRATZ storage/caching/attribution/commercial terms are still `UNKNOWN` and
  the task moves toward persisting STRATZ payloads beyond local fixtures;
- no STRATZ credential exists and the task requires live data;
- a database migration appears necessary;
- parity fails on a field you cannot normalize without changing semantics;
- any instruction here conflicts with `AGENTS.md`.

## Definition of Done

- [ ] production untouched
- [ ] `main` untouched by the worker
- [ ] owner UI branch preserved and unmodified
- [ ] isolated branch/worktree used
- [ ] base SHA recorded
- [ ] OpenDota dependency map confirmed against actual code
- [ ] canonical analytical input contract documented
- [ ] STRATZ schema and operations verified, not remembered
- [ ] STRATZ secrets backend-only
- [ ] no secret committed or logged
- [ ] GraphQL partial errors handled per R6
- [ ] pagination deterministic and page-ceiling aware
- [ ] normalization deterministic
- [ ] provider provenance explicit in `metadata_json`
- [ ] historical OpenDota provenance unchanged and un-relabelled
- [ ] normal tests make no live provider calls
- [ ] unexpected OpenDota requests fail during STRATZ tests
- [ ] OpenDota remains the rollback path and still passes
- [ ] canonical parity tests exist and emit diffs
- [ ] V6.1 analytical regression tests exist
- [ ] V6.1 formulas unchanged
- [ ] V6.1 thresholds unchanged
- [ ] frozen artifacts unchanged
- [ ] frozen analytical source identity unchanged
- [ ] sealed holdout not used for tuning
- [ ] R1–R8 each explicitly addressed or explicitly reported as blocked
- [ ] semantic mismatches reported, not hidden under tolerances
- [ ] bounded staging smoke only if authorized
- [ ] no production deployment
- [ ] rollback documented and exercised
- [ ] final report distinguishes PASS / PARTIAL / BLOCKED

## Final worker report format

```markdown
## Status
PASS | PARTIAL | BLOCKED

## Base SHA and branch
## What changed
## R1–R8 disposition
One line each: resolved / normalized / blocked, with evidence.

## Parity evidence
Canonical field diff, eligible-set diff, finding-level diff.

## Coverage deltas
Per-dimension eligible counts, OpenDota vs STRATZ.

## Request cost
Pages, requests, and matches for the accounts exercised.

## Blocked items and owner decisions required
## Rollback verification
## Production safety
Explicitly: production code / deployment / configuration / database /
provider — changed or not.
```
