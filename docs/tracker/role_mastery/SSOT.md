# Role Mastery — SSOT

**Status:** Backend implemented and **on** (owner sign-off 2026-09-28). The approved parameter set `context-2026-09-v1` is registered by migration `0017`, so any database at head serves mastery. iOS placement and visual design are separate work; the iOS app consumes `/mobile/v1/mastery` ([API](../api/README.md)).

Role Mastery is accumulated play and positive evidence for each of Carry, Mid, Offlane and Support. It is an **earned level**, never a skill rating, rank, role-level trend or performance verdict. Standard and Turbo contribute XP to the same role level; their metric observations, baselines, trends and PBs remain separate.

The role screen's activity heatmap sits beside the level. It is a separate, presentation-only match-count calendar and never affects XP ([activity SSOT](../activity/SSOT.md)).

## How it works (plain English)

- **XP per match.** Every counted match gives 100 XP (Turbo: half of everything). On top: +10 XP for each of up to 2 stats where you clearly beat your usual ("Above"), and +20 XP for each of up to 2 new personal bests. Max 160 XP per Standard match.
- **Your usual** is the middle value of your last 20 games in that role and mode, for each of the role's 4 stats.
- **Hero fairness.** For 6 farm stats (Carry last hits @10 and net worth @20; Mid net worth @20 and lane lead vs enemy mid; Offlane net worth @10 and lane lead vs enemy carry) your usual is nudged by how tonight's hero normally farms compared with the heroes you usually play, using millions of public matches. The nudge is capped. Other stats use your usual as is.
- **Example.** Your usual Carry net worth @20 is 9,000 on Juggernaut (population average 8,648). Tonight you play Faceless Void (average 7,520). Target = 9,000 − 1,128 = 7,872; "Above" needs about 8,520. Finishing at 8,300 is "In line" instead of an unfair "Below". The reverse applies to fast farmers: an Anti-Mage player (8,367) on Sven (9,007) gets a target about 640 higher.
- **Lane matchups never change XP.** The Difficult/Typical/Favourable badge is information only.
- **Earned XP never changes by itself.** Hero averages are refreshed after each major patch, but only future matches use the new numbers; every past match keeps the verdict and XP it earned (foundation §10.8). XP changes only when you correct a match's role (the XP moves to the new role) or a late replay adds a bonus that was missing; it is never reduced by a refresh.

## Earning

- Only finalized, progression-eligible Standard and Turbo matches earn XP. Every such Standard match earns 100 base XP; Turbo earns 50. Win/loss, baseline readiness and replay availability do not change the base.
- Bonus evidence comes only from the effective role's four canonical metrics ([foundation §7.2](../app_foundation/SSOT.md)). Retired metrics and other roles' metrics never qualify.
- `ABOVE` is the metric's performance state from [foundation §10](../app_foundation/SSOT.md): the comparison value against the personal baseline plus, for class B/B\* Standard metrics, the hero adjustment only. No lane or opponent term enters it for any role, and the display-only matchup badge never affects XP (owner decision, 2026-09-28).
- Each `ABOVE` metric adds 10 Standard XP, at most two metrics (+20). Each newly set strict Personal Best adds 20 Standard XP, at most two (+40). PBs require five prior comparable matches; ties do not qualify. The Standard award is at most 160 XP. Turbo halves the entire award, including bonuses, so its maximum is 80 XP.
- Missing evidence is not a negative result. An N/A metric, a building baseline or a `BELOW`/`IN_LINE` state simply earns no bonus for that metric; the base is never reduced and no metric count is required. A later replay can quietly append a missing bonus, within the same caps.
- Every role has the same four-metric opportunity and the same fixed caps, so the maximum award is identical for every role. Offlane Objective Involvement is diagnostic-only: it can set a PB but is never `ABOVE`, leaving three `ABOVE` candidates, still above the cap of two.
- XP is an award-time record with the qualifying metric IDs, source analysis and rule versions. Entitlement and calibration changes do not rewrite prior awards. A corrected role moves that match's XP; later matches keep their recorded awards.

## Rule versions and rebuilds

- The current rule is `role-mastery-v2`: v1 with bonus evidence limited to the four canonical metrics per role. Only current-rule rows count toward totals, award history, corrections and late bonuses.
- `role-mastery-v1` rows could cite metrics retired on 2026-09-27. They stay as append-only audit history and never count; there is no mixed v1/v2 timeline. The `tracker-analysis-7` methodology rebuild replays retained evidence and re-awards every finalized match under v2 in match chronology, with reason `METHODOLOGY_REBUILD`. It makes no provider calls and creates no level celebration; a delivered milestone is never re-sent.
- A new award waits while an earlier visible match in the same mode still awaits a methodology rebuild, so it never snapshots transitional history. The API shows `BACKFILLING` until the rebuild's quiet backfill lands.

## Levels and entitlement

- The curve is calibrated on the base award: twenty base-only Standard matches per early level. Bonus caps do not depend on how many metrics a role has, so the four-metric registry changes no threshold.
- A role is `UNSTARTED` before its first eligible match. The first award shows Level 1. Each transition from current level L to L+1 costs `2,000 + 300 × floor((L − 1) / 5)` XP, through Level 99. Level 5 begins at 8,000 XP and Level 99 at 469,600 XP. XP continues accumulating at Level 99.
- Free shows at most Level 5. It may show progress within Levels 1–4. At Level 5 it shows a saved-progress indicator, without true level, total XP, or deeper progress. Pro shows the earned level and total XP. Pro expiry never removes XP.
- One Steam profile owns its own ledger. A Steam switch starts a separate Role Mastery track.

## Lifecycle and surface contract

- Live awards occur in the finalization transaction. Bootstrap and historical awards are imported in match chronology at coherent completion checkpoints, without retrospective level celebrations. Role corrections and late replay bonuses are quiet.
- Live visible level milestones are in-app events only. Push remains READY-only.
- `/mobile/v1/mastery` supplies the four role levels, entitlement-safe progress and live milestones for Home, Profile and Progress. `/mobile/v1/mastery/{role}/awards` supplies paginated award reasons and links only to currently entitled matches. A Free response must not disclose hidden Pro-history match references.
- The performance parameter artifact (schema `tracker-context-parameters-v3`, model `context-adjustment-v3`) holds per-metric spread, `tau`, floor and floor tolerance, and hero levels; it has no lane scale. Its lane-model data serves only the badge, and a lane-model failure never blocks mastery. Artifacts built under schema v2 fail closed.
- If no owner-approved performance parameter artifact exists (for example, a database below migration `0017`), mastery remains `CALIBRATION_PENDING`; no provisional awards are made. When the first approved set appears, matches finalized before it are graded once and backfilled quietly from retained data, with no provider calls and no celebrations. The API shows `BACKFILLING` until the currently entitled finalized matches have awards.
- **Parameter refresh (each major patch).** A new approved set is a new immutable version. It applies only to matches graded after registration; it never re-grades or re-awards past matches. Past awards are append-only snapshots and are never recalculated by a refresh.

There are no seasons, inactivity penalties, missions, widgets, social comparisons or named cosmetic tiers in this release.
