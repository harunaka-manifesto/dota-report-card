# Match Achievements — SSOT

**Status:** Backend implemented on branch `codex/achievements-backend`, not merged or deployed. Native screens, Spline assets and share cards are later phases. This is the contract for the 24-badge Standard-match collection (`match-achievements-v1`, tiers `badge-tiers-v1`). It is separate from Role Mastery medals and from the Home challenge slot ([home §5](../home/SSOT.md)).

## What it is

Each finalized Standard match can earn any number of the 24 badges. Every badge is a factual statement about that match (for example "10 assists, 0 deaths"), with the numbers kept as proof. Losses can earn. Turbo never earns. Nothing is a skill rating or a verdict.

## Locked owner decisions

1. **Catalog.** IDs 1, 2, 4, 6, 8, 10, 11, 13, 14, 15, 17, 18, 20, 22, 23, 25, 30, 37, 41, 42, 44, 45, 49, 50. `id` is the stable machine identifier; `order` (1–24) is the display order.
2. **All qualifying badges are awarded**, including overlapping ones, together at the single READY finalization point. There is no partial Stage-1 award.
3. **Free and Pro** share identical rules and collection access. Visible history, counts and cross-match progress use the entitled-history scope, so a Pro expiry can hide older matches (including pre-link history) and reduce progress without deleting retained evidence. That is intended.
4. **#4 Record on a New Hero** is earned when a strict personal best is set on a hero that never held that metric's record. Each hero can earn #4 once; several qualifying metrics in one match are one award.
5. **#30 Hero Specialist** is the same non-Common single-match feat on the same hero in three distinct Standard matches (the third and later count; roles may differ). #1, #2, #4, #30 and the Common badge #42 are never the repeated feat. Its proof names the feat with the most matches and reports that feat's own count.
6. **Tiers are frozen** (`BADGE_TIERS`), never derived from live data: Common 1 (#42), Rare 9, Epic 10, Legendary 4. Bands: Common ≥20%, Rare 5–<20%, Epic 1–<5%, Legendary <1% of eligible Standard player-matches. Unearned entries hide tier and rarity. Evidence: [threshold review](../architecture/evidence/achievement-threshold-review-2026-09-29.md).
7. **Missing evidence never becomes zero.** An unjudgeable badge is listed as unavailable with a reason (`EVIDENCE_MISSING`, `MATCH_TOO_SHORT`, `INSUFFICIENT_HISTORY`); a real zero is evidence. A match that is not progression-eligible (leaver, abandon, too short, invalid integrity, unassigned role) is `UNAVAILABLE` as a whole.
8. **Later personal bests never erase an earned-at-the-time badge.** Role correction, scope changes, retained-data rebuilds and rule or tier changes recompute current truth from retained evidence **quietly**: no celebration or notification is replayed.
9. **Zero provider calls at runtime.** Every rule reads retained OpenDota summary or parse fields already needed for finalization.

## Rebuild and version rules

- Awards live in the immutable `analyses.result` (`achievements`, `achievement_pb_metrics`); there is no achievement table. Each analysis stores the `rules_digest` it was judged under (thresholds, role gates, constants, repeat list and tiers).
- An analysis whose digest differs from the current one is stale exactly like a methodology-version mismatch: the quiet methodology rebuild replays it in chronological order. Until then Match Detail reports `PENDING`, the collection reports `BACKFILLING`, and history judged under other rules is left out of #4/#30 (they become `INSUFFICIENT_HISTORY` rather than being judged on mixed-version data). A celebration missed in that window is not replayed, so **operators must run `rebuild.enqueue_methodology_rebuilds` at deploy**.
- A match materialized under an older `FEATURE_VERSION` and still in flight is re-projected from its stored snapshot when it finalizes; nothing is fetched.
- Standard role correction replays every later Standard match across roles (#30 spans roles) and recomputes every role's personal-best pointers; Turbo keeps its role-limited closure.

## Notifications

A live READY notification carries `achievement_ids` (each earned badge once, rarest first), `achievement_count` (total awards across a coalesced bundle), `achievement_top_id` (the badge to name; the client localizes the name from the id) and `achievement_more` (count − 1). Historical imports, rebuilds and corrections are silent.

## Known limitations and pre-launch conditions

- Corpus rates come from selected samples; #1/#2/#4/#30 tiers come from a history simulation, and #30's tier depends on history length. Tiers are frozen by owner decision.
- `networth_t`/`deaths_log` exist only in OpenDota parses since about 2026-09-10; older matches make the net-worth badges unavailable.
- Role correction, and Match Detail's correction-availability check, replay the whole later history inside the API request. Measured 73 s at 1,000 matches. Treat this as a pre-launch condition (move it off the request path or bound it) before real long histories exist.

See the [API contract](../api/README.md#match-achievements-match-achievements-v1) and the [implementation ledger](../architecture/IMPLEMENTATION-LEDGER.md).
