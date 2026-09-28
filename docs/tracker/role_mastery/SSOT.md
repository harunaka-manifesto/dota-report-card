# Role Mastery — SSOT

**Status:** Backend contract implemented; public release blocked on an owner-approved performance parameter artifact. iOS placement and visual design are separate work.

Role Mastery is accumulated play and positive evidence for each of Carry, Mid, Offlane and Support. It is an **earned level**, never a skill rating, rank, role-level trend or performance verdict. Standard and Turbo contribute XP to the same role level; their metric observations, baselines, trends and PBs remain separate.

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
- If no owner-approved performance parameter artifact exists, mastery remains `CALIBRATION_PENDING`; no provisional awards are made. After approval, retained finalized data may be replayed and backfilled without provider calls. The API shows `BACKFILLING` until the currently entitled finalized matches have awards.

There are no seasons, inactivity penalties, missions, widgets, social comparisons or named cosmetic tiers in this release.
