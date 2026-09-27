# Role Mastery — SSOT

**Status:** Backend contract implemented; public release blocked on an owner-approved performance parameter artifact. iOS placement and visual design are separate work.

Role Mastery is accumulated play and positive evidence for each of Carry, Mid, Offlane and Support. It is an **earned level**, never a skill rating, rank, role-level trend or performance verdict. Standard and Turbo contribute XP to the same role level; their metric observations, baselines, trends and PBs remain separate.

## Earning

- Only finalized, progression-eligible Standard and Turbo matches earn XP. Every such Standard match earns 100 base XP; Turbo earns 50. Win/loss, baseline readiness and replay availability do not change the base.
- Each `ABOVE` metric adds 10 Standard XP, at most two metrics (+20). Each newly set strict Personal Best adds 20 Standard XP, at most two (+40). PBs require five prior comparable matches; ties do not qualify. The Standard award is at most 160 XP. Turbo halves the entire award, including bonuses, so its maximum is 80 XP.
- Missing evidence is not a negative result. It simply earns no bonus for that metric. A later replay can quietly append a missing bonus, within the same caps.
- XP is an award-time record with the qualifying metric IDs, source analysis and rule versions. Entitlement and calibration changes do not rewrite prior awards. A corrected role moves that match's XP; later matches keep their recorded awards.

## Levels and entitlement

- A role is `UNSTARTED` before its first eligible match. The first award shows Level 1. Each transition from current level L to L+1 costs `2,000 + 300 × floor((L − 1) / 5)` XP, through Level 99. Level 5 begins at 8,000 XP and Level 99 at 469,600 XP. XP continues accumulating at Level 99.
- Free shows at most Level 5. It may show progress within Levels 1–4. At Level 5 it shows a saved-progress indicator, without true level, total XP, or deeper progress. Pro shows the earned level and total XP. Pro expiry never removes XP.
- One Steam profile owns its own ledger. A Steam switch starts a separate Role Mastery track.

## Lifecycle and surface contract

- Live awards occur in the finalization transaction. Bootstrap and historical awards are imported in match chronology at coherent completion checkpoints, without retrospective level celebrations. Role corrections and late replay bonuses are quiet.
- Live visible level milestones are in-app events only. Push remains READY-only.
- `/mobile/v1/mastery` supplies the four role levels, entitlement-safe progress and live milestones for Home, Profile and Progress. `/mobile/v1/mastery/{role}/awards` supplies paginated award reasons and links only to currently entitled matches. A Free response must not disclose hidden Pro-history match references.
- If no owner-approved performance parameter artifact exists, mastery remains `CALIBRATION_PENDING`; no provisional awards are made. After approval, retained finalized data may be replayed and backfilled without provider calls. The API shows `BACKFILLING` until the currently entitled finalized matches have awards.

There are no seasons, inactivity penalties, missions, widgets, social comparisons or named cosmetic tiers in this release.
