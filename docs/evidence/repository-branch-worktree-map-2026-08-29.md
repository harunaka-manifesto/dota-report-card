# Repository Branch / Worktree Map — 2026-08-29

## Scope

This map records the repository state for the Death Context overnight
completion. It covers local provenance and integration boundaries; it does not
authorize deployment, remote updates, or deletion of user-owned work.

## Branches

| Role | Local ref | SHA | State |
| --- | --- | --- | --- |
| Production baseline | `main` | `6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95` | unchanged |
| Local integration target | `staging` | `c4df42df12f7b14bad0cdbc2e32c7bb632ff81f5` | tracks `origin/staging`; contains current V6.1 UI work |
| Overnight execution | `execution/free-dna-death-context-local-reuse-pilot` | `cf0ff97` | clean tracked worktree; terminal verdict blocked |
| Research base | `research/free-dna-death-context-feasibility` | `98e471453b2ea5b6de418ad9ca8d4e5400c913eb` | frozen Tier-2 pilot base |

The execution branch is not an ancestor of `staging`; their common ancestor is
`2ce777b84bd936a416dfdc7e8cac5d758c04ae57`. The execution changes are
research/documentation/scripts only and do not overlap the staged V6.1 UI
files. Integration therefore belongs in local `staging`, not `main`.

## Worktrees

| Path | Branch / state |
| --- | --- |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card` | `staging`; owner worktree with unrelated untracked files preserved |
| `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card-death-context-local-reuse-pilot` | `execution/free-dna-death-context-local-reuse-pilot`; execution worktree |
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
```

Do not remove the owner worktree, the data worktree, locked research worktrees,
unknown branches, or remote refs. Do not merge `main`, deploy, or modify
production metadata as part of this research task.
