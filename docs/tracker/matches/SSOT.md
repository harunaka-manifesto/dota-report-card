# Matches — SSOT

The Matches page lists a player's Standard and Turbo matches, newest first, grouped into play
sessions. It has keyword search and filters, and tapping a row opens Match Detail. It replaces the
History surface. The backend contract is `matches-list-v1`.

Cross-product rules come from [`app_foundation/SSOT.md`](../app_foundation/SSOT.md). The
[History SSOT](../history/SSOT.md) still governs row identity, lifecycle and ineligibility wording,
except where §1 below amends it.

## 1. Owner decisions (2026-09-29)

| Question | Decision |
|---|---|
| Listed matches | Standard and Turbo only, every lifecycle state. Unsupported-mode matches are **hidden** here (amends history §2 "never hidden"), because the app never counts them. |
| Row | Hero, effective role, K/D/A, result, mode, start time, duration, lifecycle, progression and its reason, insight-present marker, PB-owner marker. |
| K/D/A | Shown as **plain facts**: three numbers, with no ratio, colouring, comparison or trend. This amends the history §4 allowed list. K/D/A is still never a progression proxy (foundation §16). |
| Performance arrow | **None.** The mock's up/down marker for the four role metrics is dropped. Foundation §11.2/§16 and history §4 stand: no composite and no per-metric state on a row. |
| Play session | Consecutive listed matches where each starts **less than 3 hours after the previous one ended** (start + duration). A gap of exactly 3 hours starts a new session. A match with no duration yet counts as ending when it started. |
| Session scope | Sessions are built from the whole entitled Standard+Turbo history. Hidden unsupported matches never bridge two sessions. Filters and search narrow rows but never change a session's identity, name or header. |
| Session header | Name, local day of the first match, W-L count (unknown results left out), start and end time, and total match count. |
| Placeholder name | `{Weekday} {day part} {focus}`, in the request's time zone. Day parts: 05–12 morning, 12–17 afternoon, 17–22 evening, 22–05 late-night (00–05 keeps its own weekday). Focus: a hero in ≥50% of matches → `{Hero} run`, otherwise a role in ≥50% → `{Role} grind`, otherwise all Turbo → `Turbo session`, otherwise `session`. A single match → `{Hero} game`. A 50% tie goes to the most recently played. Deterministic, with no LLM (ADR 0005). |
| Rename | A player may name a session (1–40 printable characters, whitespace collapsed). Null restores the placeholder. |
| Search | Server-side over the whole history. Terms are whitespace separated and **all** must match a row. A term matches a hero (name word, prefix of two or more letters, or common alias such as `am`, `wr`, `sf`), a role word (`carry`, `mid`, `offlane`, `support`, `pos1`–`pos5`, …), a mode (`turbo`, `standard`), a result (`win`, `loss`, …) or the session's displayed name. Reserved words never also match heroes as prefixes. |
| Filters | Heroes (multi-select, up to 10), one role, one mode (Standard or Turbo), and a local date range (`from`/`to`, inclusive). Client presets (today, 7 days, 30 days) map onto the range. |
| Entitlement | The existing entitled-history scope only (ADR 0004). Free sessions are built from entitled matches. |

## 2. Guardrails

- **Presentation only.** Sessions, names and search feed no baseline, trend, PB, mastery, claim or
  progression state (foundation §11.3).
- **No verdicts on a row.** No per-metric value or state, no matchup context, no composite, no
  KDA ratio. Result and role are never composed into a single judgment (history §10).
- **Provider-free.** A render reads persisted data only (foundation §13.2).
- **Honest empty states.** `has_matches` tells a filtered-empty list from an empty account.
- **Retroactive truth.** Late matches, role corrections and scope changes can move rows between
  sessions on the next read. A late match that bridges two sessions merges them, and the merged
  session keeps its most recently chosen name.

## 3. Data

- Computed on read: one query loads every entitled Standard+Turbo link with its start, duration,
  result, hero and role. Sessions, names, filters and search are applied in the application, and
  K/D/A plus the insight and PB markers are loaded for the page rows only.
- `tracker_play_session_names` (migration `0018`) stores a player-chosen name on the session's
  first match, keyed by `(profile_id, match_id)` and cascading with the link. A session's custom
  name is the most recently updated name among its matches. Renaming or resetting clears the
  other names in that session.
- Hero names come from `hero_references.py` (`hero-catalog-v1`), a checked-in snapshot of the public
  hero table. It is used for search and placeholder names only.

## 4. API

`GET /mobile/v1/matches` and `POST /mobile/v1/matches/sessions/{session_ref}/name`. See the
[API](../api/README.md#matches-matches-list-v1).

## 5. Open items

- A "this patch" time preset needs a current-patch source. It is deferred; presets map to `from`/`to`.
- `/history` stays until iOS moves to `/matches`, then it can be retired.
- If a very long history makes reads slow, materialize session boundaries. Measure first.
