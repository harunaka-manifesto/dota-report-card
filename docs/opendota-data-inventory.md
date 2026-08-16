# OpenDota data inventory

This document defines the two OpenDota payloads used by the report pipeline:

1. **Match summary** — one history request returning up to ~500 rows.
2. **Per-match deep analysis** — one detail request per selected match, capped at 25 for paid users.

The inventory describes fields OpenDota may return, not fields that are guaranteed to be non-null. Availability depends on match type, privacy settings, replay availability, parser coverage, and whether the match is still being processed. Store the raw payload before normalization so new fields can be adopted without another fetch.

## 1. Match summary: `/players/{account_id}/matches`

Example request:

```text
GET https://api.opendota.com/api/players/{account_id}/matches?limit=500
```

The response is an array of compact `PlayerMatch` rows. The row is the player’s view of each match, so `player_slot` identifies the player’s side and `player_team` may be absent on older or unusual rows.

### Fields available per summary row

| Field | Meaning | Typical use |
|---|---|---|
| `match_id` | Match identifier | Join to `/matches/{match_id}` |
| `player_slot` | Player slot; values below 128 are Radiant, values at or above 128 are Dire | Side, win attribution |
| `radiant_win` | Whether Radiant won | Result |
| `duration` | Match duration in seconds | Duration curves, early/late games |
| `game_mode` | Numeric game-mode ID | Ranked/unranked/mode filtering |
| `lobby_type` | Numeric lobby-type ID | Match eligibility filtering |
| `hero_id` | Hero played by the account | Hero pool, hero-role history |
| `start_time` | Unix timestamp when the match started | Recency, trend windows |
| `version` | Game version/parser version identifier when supplied | Patch/version grouping |
| `kills` | Player kills | K/D/A and outcome features |
| `deaths` | Player deaths | K/D/A and collapse-tail features |
| `assists` | Player assists | Participation features |
| `skill` | OpenDota skill bracket code when available | Cohort filtering; treat as a source label, not exact MMR |
| `party_size` | Party size | Solo/party splits |
| `leaver_status` | Valve leaver-status code | Abandonment/eligibility filtering |
| `hero_variant` | Hero facet/variant identifier when supplied | Facet-aware grouping |
| `lane_role` | Lane-role code when supplied | Role hints; not a replay-proven position |
| `lane` | Lane code when supplied | Lane hints |
| `is_roaming` | Whether the player was marked roaming when supplied | Role/style hint |
| `cluster` | Server cluster identifier | Region/server analysis |
| `region` | Region identifier when supplied | Region filtering |
| `patch` | Numeric patch identifier | Patch grouping |
| `isRadiant` | Whether the player was Radiant, in some API/client versions | Side; normalize with `player_slot` |
| `player_team` | Player-team identifier/name when supplied | Team labeling |

### Request controls relevant to the summary pass

The endpoint also supports filters such as `limit`, `offset`, `win`, `patch`, `game_mode`, `lobby_type`, `region`, date window, `lane_role`, `hero_id`, `is_radiant`, party/account filters, `significant`, `having`, `sort`, and `project`. The application should request only the needed projection when the deployment’s OpenDota version supports it, but must tolerate omitted fields.

### What summary data does not provide

The history row does **not** reliably contain all ten players, item timelines, abilities, gold/XP/net-worth timelines, purchases, wards, chat, teamfights, draft timings, objective events, or per-event timestamps. Those belong to the match-detail payload and/or replay parser output.

## 2. Per-match deep analysis: `/matches/{match_id}`

Example request:

```text
GET https://api.opendota.com/api/matches/{match_id}
```

This is a single detailed match payload. The application may call it for at most 25 selected matches for a paid report. This request must not request or trigger replay parsing; an existing parsed payload is the only deep source for this flow.

### Match-level fields

| Field family | Fields / data |
|---|---|
| Identity and timing | `match_id`, `start_time`, `duration`, `patch`, `version`, `game_mode`, `lobby_type`, `cluster`, `region`, `replay_url`, `replay_salt`, `radiant_win`, `positive_votes`, `negative_votes` |
| Teams and score | `radiant_score`, `dire_score`, `radiant_team`, `dire_team`, `radiant_team_id`, `dire_team_id`, team names/IDs when known |
| Buildings | `tower_status_radiant`, `tower_status_dire`, `barracks_status_radiant`, `barracks_status_dire` |
| First blood and economy curves | `first_blood_time`, `radiant_gold_adv`, `radiant_xp_adv` |
| Match metadata | `human_players`, `leagueid`, `league`, `skill`, and parser metadata when present |
| Parse provenance | Parser/version and parse-status indicators exposed by the deployment, plus presence/absence of each parsed collection |

`radiant_team` and `dire_team` are generally objects containing team metadata when a team is known; do not assume they are present for ordinary public matchmaking.

### `players`: up to ten player records

Each player object can include the following groups:

| Group | Data available |
|---|---|
| Identity and side | `account_id`, `player_slot`, `isRadiant`, `personaname`, `name`, `avatar`, `avatarfull`, `hero_id`, `hero_variant`, `team_number` |
| Result and core score | `kills`, `deaths`, `assists`, `last_hits`, `denies`, `gold_per_min`, `xp_per_min`, `level`, `hero_damage`, `hero_healing`, `tower_damage`, `net_worth`, `total_gold`, `total_xp`, `kill_streak`, `multi_kills`, `rampages`, `buyback_count`, `buyback_cost`, `buyback_log` |
| Lane and role | `lane`, `lane_role`, `is_roaming`, `role`, `role_levels`, `gold_t`, `xp_t`, `lh_t`, `dn_t`, `times`, `lane_pos` |
| Combat and control | `kills_log`, `deaths_log`, `assists_log`, `stuns`, `stuns_dealt`, `hero_damage`, `hero_healing`, `damage`, `damage_taken`, `damage_by_hero`, `damage_taken_by_hero`, `deaths_by_hero`, `kill participation` fields when supplied |
| Items and abilities | `item_0`–`item_5`, `backpack_0`–`backpack_2`, `item_neutral`, `item_neutral_time`, `item_usage`, `purchase_log`, `ability_upgrades`, `ability_uses`, `item_uses`, `runes`, `runes_log` |
| Vision and map activity | `obs_placed`, `sen_placed`, `obs_log`, `sen_log`, `obs_left_log`, `sen_left_log`, `wards_purchased`, `wards_placed`, `wards_destroyed`, `camps_stacked`, `roshan_kills` |
| Player outcomes and ratings | `win`, `lose`, `player_rating`, `personaname`, `rank_tier`, `isRadiant` |

Field names have changed slightly across OpenDota/parser versions. In particular, some analytics are arrays or event logs rather than scalar totals. Normalize by semantic field family and preserve unknown keys.

### Parsed event collections

These collections are the main reason to spend a deep request:

| Collection | Data available |
|---|---|
| `objectives` | Tower, barracks, Roshan, shrine/other objective events; event type, time, and player/side attribution where parser can determine it |
| `teamfights` | Fight windows and aggregate fight duration; per-player kills, deaths, assists, damage, damage taken, healing, buybacks, and participation fields when available |
| `chat` | Timestamped chat messages and player slot/account attribution when available |
| `draft_timings` | Pick/ban order, hero ID, team/side, and draft timestamp |
| `picks_bans` | Pick/ban entries, hero IDs, team/side, and whether the entry was a pick or ban |
| `radiant_gold_adv` / `radiant_xp_adv` | Time-indexed team advantage curves |
| `cosmetics` | Cosmetic item/hero metadata when returned |
| `all_word_counts` / `my_word_counts` | Chat-word frequency aggregates when available |

### Deep fields that require special handling

- `chat`, `draft_timings`, `picks_bans`, `objectives`, `teamfights`, and time-series arrays may be `null`, empty, or absent even when the match itself is valid.
- `replay_url` being present does not guarantee that every parsed collection is populated.
- Player account IDs and names can be missing or anonymized. The report must remain usable from slot, hero, and team-side data.
- A match can be public and retrievable while still lacking replay-derived data. Track coverage per field family, not only a single `parsed = true/false` flag.
- Do not treat OpenDota-derived `skill`, `rank_tier`, or role labels as exact competitive ratings or replay-verified positions.

## 3. Product budget and storage contract

| Tier | Request budget | Raw source | Intended output |
|---|---:|---|---|
| Summary | 1 request, up to ~500 rows | `/players/{account_id}/matches` | Broad history, outcomes, hero pool, duration, side, mode, party, patch, and lightweight role hints |
| Deep | Up to 25 requests for paid users | `/matches/{match_id}` | Selected-match context, ten-player comparisons, timelines, items, events, objectives, teamfights, chat, and draft where present |
| Replay parse | 0 automatic requests in this flow | Not called | Never assume missing replay data can be created during report generation |

Recommended persisted layers:

1. Raw payload plus endpoint, source ID, fetch time, hash, and parser/schema version.
2. Normalized match and participant facts with nullable fields.
3. Parsed feature families and per-family coverage.
4. Derived evidence that names the source match IDs and raw payload references.

## Sources

- [OpenDota API documentation](https://docs.opendota.com/)
- [OpenDota core repository](https://github.com/odota/core)
- [Generated OpenDota client match-history documentation](https://github.com/wood-run/opendota-client/blob/master/docs/PlayersApi.md)
