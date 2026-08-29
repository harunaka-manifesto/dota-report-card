# Repository Branch / Worktree Map — 2026-08-29

## Scope

This map records the repository state for the Death Context overnight
completion and its owner-authorized continuation. It covers local provenance
and integration boundaries; it does not authorize deployment, remote updates,
or deletion of user-owned work.

## Branches

| Role | Local ref | SHA | State |
| --- | --- | --- | --- |
| Production baseline | `main` | `6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95` | unchanged |
| Local integration target | `staging` | includes `6eb00f9` | local staging fast-forwarded through the continuation handoff; `main` unchanged |
| Overnight execution | `execution/free-dna-death-context-local-reuse-pilot` | `9911c26` | fully integrated; local branch and worktree removed after preservation |
| Continuation execution | deleted after integration | `6eb00f9` | blocked at 950/960; tip is reachable from local `staging` |
| Research base | `research/free-dna-death-context-feasibility` | `98e471453b2ea5b6de418ad9ca8d4e5400c913eb` | frozen Tier-2 pilot base |

The overnight and continuation execution tips are reachable from local
`staging`. The continuation changes are research/documentation/scripts only
and do not overlap the staged V6.1 UI files. Integration therefore belongs in
local `staging`, not `main`.

## Worktrees

| Path | Branch / state |
| --- | --- |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card` | `staging`; owner worktree with unrelated untracked files preserved |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-death-context-local-reuse-pilot` | removed after canonical artifact preservation; tip `9911c26` remains reachable from `staging` |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-death-context-continuation` | removed after `6eb00f9` was proven reachable from local `staging` |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-v7-stratz-corpus-acquisition` | `data/v7-stratz-corpus-acquisition`; retained data worktree |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-findings-recovery` | `research/v61-findings-recovery`; locked initializing worktree |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-frozen-repro` | `research/v61-frozen-repro`; locked initializing worktree |
| `/sessions/rcw-01rq9g37eta2rpt1vaxdsbkm/research-v61-frozen-repro2` | `research/v61-frozen-repro2`; locked initializing worktree |

The staging owner worktree currently has these unrelated untracked paths and
they are preserved:

```text
docs/design/ (one V7 owner-untracked file)
docs/dota-v6.1-main-script.md
docs/evidence/
docs/prompts/
research/stratz-enrichment/
```

## Integration and cleanup rule

The safe handoff is:

```text
execution research
  → local staging integration
  → owner review
  → main only after separate release approval
```

Before any cleanup, prove the execution SHA is reachable from local `staging`
and preserve the canonical ignored local artifacts:

```text
.local/corpora/opendota/free-dna-tier2/
.local/diagnostics/free-dna-death-context-live-pilot/
.local/diagnostics/free-dna-death-context-overnight/
.local/diagnostics/free-dna-death-context-continuation/
```

Do not remove the owner worktree, the data worktree, locked research worktrees,
unknown branches, or remote refs. Do not merge `main`, deploy, or modify
production metadata as part of this research task.
