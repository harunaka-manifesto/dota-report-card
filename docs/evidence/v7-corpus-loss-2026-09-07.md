# Pass-1 history corpus lost from `/private/tmp` — 2026-09-07

```text
SEVERITY: material — irreplaceable research data lost
DETECTED: 2026-09-07 ~02:30 local, by a failing population-parameter export
CAUSE: not attributable with confidence; see §3
RESERVED SPLITS: unaffected (both were always empty)
```

## 1. What was lost

The V7 corpora live under `.local/`, which in the working worktree is a symlink
to `/private/tmp/dota-report-card-v7-research/.local`. **`/private/tmp` is not
durable storage on macOS.**

| layer | before | after |
|---|---:|---:|
| `v7-corpus-2026-09-02/canonical/history` | 900 documents | **0** |
| `v7-corpus-2026-09-02/normalized/history` | 900 accounts × pages | **0 page files** (900 empty directories remain) |
| `v7-corpus-2026-09-02/raw` — history responses | ~2,900 | **1** |
| `v7-corpus-2026-09-02/canonical/parsed` | 235 | 169 |
| `v7-corpus-2026-09-02/normalized/parsed` | — | 10,883 batch files (intact) |
| `v7-pass2-2026-09-04` (all layers) | — | intact |

**The Pass-1 match-history corpus is gone at every layer — raw, normalized and
canonical.** That is 900 accounts (600 DISCOVERY + 300 CANDIDATE_TEST) of
year-long match history, roughly 2,900 provider requests.

The Pass-2 deep corpus — 276 accounts, 104,982 matches, ~13,264 provider
requests — **survived**.

## 2. Consequence

**The 12 Pass-1 Finding families can no longer be refitted from source data.**
Their published parameters survive because they were committed as evidence, but
the corpus that produced them does not. The research remains *auditable* (every
number is in `docs/evidence/`) and is no longer *reproducible from source*.

Nothing in the V7 product is blocked: the frozen population parameters now ship
as a committed artifact derived from the published evidence, and Pass-2 — which
carries 8 of the 16 Finding dimensions, every recommendation and the whole
archetype — is intact.

What is lost is the ability to re-derive Pass-1 differently: a new Pass-1
dimension, a corrected Pass-1 semantic, or an independent recheck of a Pass-1
number would now require re-collection.

## 3. Cause — stated honestly

Not attributable with confidence.

Facts: the `canonical/history`, `canonical/parsed`, `normalized/history` and
`raw` directories all carry an mtime of **2026-09-07 00:00** — a clock
boundary. `normalized/parsed` (mtime 2026-09-02) was untouched. The deletion
was therefore selective in a way a simple recursive delete would not be.

`/private/tmp` on macOS is subject to periodic system cleanup, which is the
most plausible explanation and fits the midnight timestamp. It does not
obviously fit the selectivity — parsed batches of the same age survived.

No agent working in this repository had a charter that touches `.local`; the
relocation worker moved tracked source files under `git mv`, and the survey
worker was read-only. I cannot rule an agent out from timestamps alone, and I
am not going to claim a cause I cannot evidence.

**The durable lesson is independent of the cause: an irreplaceable corpus was
kept only in `/private/tmp`.**

## 4. What was done

1. **Detected** by verification, not by report: the population-parameter export
   returned `players=0 tau=nan` for every Pass-1 dimension where the published
   evidence has 538, 116 and 109. A worker's claim of success would not have
   caught this; running the thing did.
2. **Rebuild attempted and correctly refused.** `canonical` is a pure function
   of `normalized`, so `scripts/stratz_v7_rebuild_canonical.py` was written to
   recompute it using the corpus runner's own `canonicalize_history` /
   `canonicalize_parsed`. It found `normalized/history` also empty and refused
   to write anything. The script remains useful and is committed: it rebuilt
   nothing here, and it verifies every account against the row count recorded
   in `state.json` before writing, so it cannot fabricate a plausible corpus.
3. **Survivors copied to durable storage**, non-destructively, at
   `.local/rescue-2026-09-07/`:
   - Pass-2 canonical, 278 documents, 3.4 GB
   - Pass-1 `normalized/parsed`, 10,883 batches
   - Pass-1 `canonical/parsed` (169), and all manifests
   Verified by count after copying.
4. **Population parameters re-sourced.** The frozen artifact the runtime needs
   is now derived from the committed evidence documents rather than from a
   fresh fit, and records each source document's SHA-256. This was forced by
   the loss and is the better design regardless: the runtime uses exactly the
   numbers that were reviewed, and the artifact rebuilds on any checkout with
   no corpus present.

## 5. Recommended, not done

These need an owner decision and were not taken unilaterally:

- **Move the corpora out of `/private/tmp` entirely.** The rescue copy is a
  copy; the working corpus still lives in the volatile path, and the Pass-2
  raw and normalized layers (~5 GB) were not copied.
- **Decide whether Pass-1 history is worth re-collecting.** Roughly 2,900
  provider requests, well inside a single day's ceiling. It would not reproduce
  the original corpus — the frozen cohort's accounts have played more games
  since — so the rebuilt corpus would be a *different* sample and the published
  Pass-1 numbers could not be re-derived from it exactly.
- **Treat the reserved splits as unaffected.** Both were always empty of data;
  nothing was lost there, and nothing about this changes their status.
