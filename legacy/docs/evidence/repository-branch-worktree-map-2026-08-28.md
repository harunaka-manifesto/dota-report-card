# Repository Branch / Worktree Map

Inventory was performed on 2026-08-28 before the pilot commit. Remote refs
were inspected with `git ls-remote --heads origin`; no remote branch named
`staging` or `codex/v61-case-notes` exists.

## Long-lived branches

| branch | head at inventory | upstream | merged into main? | merged into staging? | action |
| --- | --- | --- | --- | --- | --- |
| main | `6d088f7` | `origin/main` | YES | NO | KEEP |
| staging | `c4df42d` | none | NO | YES | KEEP; renamed from `codex/v61-case-notes` |

`staging` preserves the former Case Notes commit and the untracked owner files
in its active worktree. The rename changed only the branch ref/name.

## Active temporary branches

| branch | purpose | head | based on / merge target | main? | staging? | active worktree? | action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| codex/research-v61-findings-statistical-recovery-20260827 | V6.1 findings recovery specification | `55d4f2f` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| codex/v61-suppression-autopsy | suppression audit | `945ce62` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| codex/v61-worker-a-story | worker A story implementation | `a00795f` | V6.1 UI / staging review | NO | NO | NO | KEEP_FOR_NOW |
| codex/v61-worker-b-copy | worker B copy catalog | `9c28a17` | V6.1 UI / staging review | NO | NO | NO | KEEP_FOR_NOW |
| codex/v61-worker-c-server | worker C presentation server work | `50b43ca` | V6.1 UI / staging review | NO | NO | NO | KEEP_FOR_NOW |
| data/v7-stratz-corpus-acquisition | V7 provider/corpus access work | `6bc5b55` | V7 research / owner review | NO | NO | YES | KEEP_FOR_NOW |
| docs/v61-ssot-refresh | V6.1 architecture SSOT | `13afc8b` | V6.1 docs / staging review | NO | NO | NO | KEEP_FOR_NOW |
| execution/free-dna-death-context-local-reuse-pilot | current local-reuse pilot | `98e4714` | exact pilot base / staging review | NO | NO | YES | KEEP; preserve |
| execution/v61-session-drift-phase2 | Session Drift Phase 2 execution | `c34f1a2` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| execution/v61-session-drift-phase3 | Session Drift Phase 3 execution | `e504dd3` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| execution/v61-session-drift-phase3b-eligibility-completion | Phase 3B eligibility | `9fa0f76` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| execution/v61-session-drift-phase3d-fixed-frame | Phase 3D fixed-frame execution | `1260fd4` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/free-dna-death-context-feasibility | Death Context feasibility base | `98e4714` | research / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/free-dna-opendota-parsed-feasibility | parsed-data feasibility | `48f05ea` | research / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-blocker-resolution-nightshift | V6.1 blocker resolution | `3323511` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-family-null-models | family null-model stop | `f1e5961` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-findings-statistical-hardening | findings statistical hardening | `c28c5bc` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-four-family-inference-design | four-family inference design | `31a48b0` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-frozen-repro | frozen artifact reproducibility | `ca5120f` | analytical release lineage / archive | YES | YES | YES, locked | KEEP; analytical lineage |
| research/v61-frozen-repro2 | corrected frozen release reproducibility | `fa05f24` | analytical release lineage / archive | YES | YES | YES, locked | KEEP; analytical lineage |
| research/v61-margin-stability-multiplicity | margin/stability calibration | `44bba6d` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-pool-combat-family-redesign | pool/combat family redesign | `fc3a728` | V6.1 lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-session-drift-phase1-plan | Session Drift Phase 1 plan | `43d8183` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-session-drift-phase3-plan | Session Drift Phase 3 plan | `8e8b30c` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-session-drift-phase3c-continuity-adjudication | Phase 3C continuity | `6fd8d11` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v61-session-drift-phase3d-sampling-frame-study | Phase 3D sampling frame | `2fb1452` | research lineage / staging review | NO | NO | NO | KEEP_FOR_NOW |
| research/v7-five-finding-candidate-menu | V7 candidate menu | `c2ffdfa` | V7 research / owner review | NO | NO | NO | KEEP_FOR_NOW |

All rows not merged into a preserved long-lived ref are retained because they
carry unique research lineage or an unclear owner purpose. The current pilot
branch is retained even though its local diagnostics are ignored by Git.

## Archived/safety branches

| branch | purpose | head | action |
| --- | --- | --- | --- |
| origin/backup/main-before-v61-ui-fix-20260827-0554 | remote safety snapshot | `e32fe83` | KEEP |
| origin/release/v61-railway-candidate | remote release candidate | `f3f3af8` | KEEP |

## Remote branches

| branch | head | merged into main? | merged into staging? | action |
| --- | --- | --- | --- | --- |
| origin/backup/main-before-v61-ui-fix-20260827-0554 | `e32fe83` | YES | YES | KEEP |
| origin/codex/documentation | `f5c6247` | YES | YES | KEEP |
| origin/codex/v61-defect-pass | `b406e36` | YES | NO | KEEP_FOR_NOW; no remote deletion |
| origin/codex/v61-motion-pacing | `2ce777b` | YES | YES | KEEP_FOR_NOW; no remote deletion |
| origin/docs/v61-ssot-refresh | `13afc8b` | NO | NO | KEEP_FOR_NOW |
| origin/main | `6d088f7` | YES | NO | KEEP |
| origin/release/v61-railway-candidate | `f3f3af8` | YES | YES | KEEP |

Remote `origin/HEAD → origin/main` is a symbolic pointer, not an additional
branch. No remote branch was pushed or deleted.

## Worktrees

| path | branch | clean? | safe to remove? | action |
| --- | --- | --- | --- | --- |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card` | `staging` | NO; owner untracked files | NO | KEEP |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-findings-recovery` | `research/v61-findings-recovery` | locked/unavailable | NO | KEEP |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-frozen-repro` | `research/v61-frozen-repro` | locked/unavailable | NO | KEEP |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-frozen-repro2` | `research/v61-frozen-repro2` | locked/unavailable | NO | KEEP |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-death-context-local-reuse-pilot` | current execution branch | clean tracked state; ignored private corpus | NO; private local diagnostics/corpus are unique | KEEP |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-v7-stratz-corpus-acquisition` | `data/v7-stratz-corpus-acquisition` | clean at inventory | NO; active owner research | KEEP |

The stale `wt-v7menu` record pointed to a missing path and was pruned without
deleting its still-unique `research/v7-five-finding-candidate-menu` branch.

## Safe cleanup performed

- Renamed local `codex/v61-case-notes` → `staging` after collision and ancestry
  checks. The old branch had unique work, so the rename preserved it.
- Deleted local `codex/v61-defect-pass` (`b406e36`) and
  `codex/v61-motion-pacing` (`2ce777b`) with non-forcing `git branch -d`; both
  are reachable from `main`, have no active worktree, and remain available as
  remote refs or preserved history.
- Pruned one stale worktree metadata record for the already-missing `wt-v7menu`
  path.
- No raw corpus, `.local` directory, owner worktree, main branch, remote ref,
  or unique analytical branch was deleted.

## Branches intentionally kept

`main`, `staging`, the current execution branch, all research/data/execution
branches listed above, analytical reproducibility branches, safety snapshots,
and all remote branches were kept.

## Unknown branches not touched

No branch with unclear purpose or unique ancestry was deleted. Locked worktrees
were not inspected destructively and were kept.

## Recommended future flow

```text
research/execution branch
→ owner review
→ staging
→ full integration/release gates
→ main
```

## Hygiene counts at inventory

```text
local branches before cleanup: 31
local branches after cleanup and pilot creation: 30
remote branches before: 7
remote branches after: 7
local branches safely deleted: 2
remote branches safely deleted: 0
worktrees removed: 0
stale metadata records pruned: 1
main changed: NO
```
