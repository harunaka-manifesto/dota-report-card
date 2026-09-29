# Hero Pool — SSOT

The heroes a player used most in each role. It sits on the role screen beside the Role Mastery
level and the activity heatmap. The backend contract is `hero-pool-v1`; iOS design is pending.

Cross-product rules come from [`app_foundation/SSOT.md`](../app_foundation/SSOT.md). This
document only projects them onto the hero pool.

## 1. Owner decisions (2026-09-29)

| Question | Decision |
|---|---|
| Roles | `CARRY`, `MID`, `OFFLANE`, `SUPPORT`, each with its own list. There is no `ALL` series. |
| Windows | Trailing **7, 30 and 365 local days** ending today, inclusive (today 2026-09-29 → `LAST_7_DAYS` starts 2026-09-23). The client sends an IANA `time_zone` on each request; none is stored. |
| Counted matches | The same set as the [activity heatmap](../activity/SSOT.md): `READY` only, Standard and Turbo combined, grouped by the match's effective role. |
| Value | **Match count** per hero. It is not win rate, XP or a performance signal. |
| List | The **top 10** heroes per role and window. Fewer heroes gives a shorter list, with no minimum. |
| Order | Matches descending, then most recent play descending, then `hero_id` ascending. |
| Totals | `total_matches` per role and window counts every hero, before the top-10 cut. |
| Shape | Every role and window is always present, even when empty (`total_matches: 0`, `heroes: []`). |
| Entitlement | The existing entitled-history scope only (ADR 0004). There is no hero-pool-specific gate. |
| Drill-in | None. Profile is unchanged, and `favourite_hero_id` is independent of this feature. |

## 2. Guardrails

- **Presentation only.** Nothing here feeds baselines, trends, PBs, mastery, claims or any
  progression state (foundation §11.3).
- **Counts, not verdicts.** No "best hero", no win rate, no ranking language beyond the ordering
  above.
- **Coverage is stated.** A bootstrap-only pre-link span inside the 365-day window is returned as
  `partial_ranges` with reason `BOOTSTRAP_SAMPLE`, using the heatmap's rule. The client should mark
  it as partial, never as "played little".
- **Provider-free.** A render reads persisted data only (foundation §13.2).
- **Retroactive truth.** Role corrections, late finalization and scope changes move counts
  silently on the next read. The body ETag changes with them.

## 3. Data

Computed on read from `tracker_account_matches` joined to `tracker_match_players` on
`match_id` and `player_slot` for the hero, in one grouped query over the 365-day range. Ranking
and the top-10 cut happen in the application. There is no materialized table.

## 4. API

`GET /mobile/v1/hero-pool?time_zone=<IANA>`. See the [API](../api/README.md#hero-pool-hero-pool-v1).

## 5. Open items

- The role list page shows the first N ≤ 5 heroes. This is client-only and undecided.
