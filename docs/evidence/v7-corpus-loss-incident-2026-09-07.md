# Incident — V7 Pass-1 history corpus lost, 2026-09-07

```text
SEVERITY: material — irreplaceable research source data lost
CAUSE: UNATTRIBUTED
DETECTED: 2026-09-07, ~02:30 local (Asia/Jakarta)
RESERVED SPLITS: unaffected — both were always empty of collected data
NEW PROVIDER CALLS DURING RESPONSE: 0
```

Supersedes the preliminary note `v7-corpus-loss-2026-09-07.md`, which reported
two figures from memory that were wrong. Every number below is measured from
disk by `scripts/v7_corpus_inventory.py`.

## 1. Discovery

Detected by verification, not by report. The population-parameter export
returned `players=0 tau=nan` for every Pass-1 Finding dimension where the
published evidence records 538, 116 and 109. A worker's claim of success would
not have surfaced this; running the thing did.

Last known good: the Finding pipeline reproduced identically from this corpus
on 2026-09-06 (`v7-phase-close-qa-2026-09-06.md` §2), so the loss falls between
that run and 02:30 on 2026-09-07.

## 2. Cause — UNATTRIBUTED

Not proven, and not asserted.

Evidence: `canonical/history`, `canonical/parsed`, `normalized/history` and
`raw` all carry an mtime of **2026-09-07 00:00**. `normalized/parsed`
(mtime 2026-09-02) was untouched.

A midnight timestamp is consistent with scheduled cleanup of `/private/tmp`,
which is not durable storage on macOS. It is **evidence, not proof of
mechanism**, and it does not explain the selectivity: Pass-1
`normalized/parsed` batches of the same age survived, as did the entire Pass-2
tree in a sibling directory.

No agent working in this repository had a charter that touches `.local`. That
does not exonerate one; it means the available evidence does not identify a
mechanism. **CAUSE: UNATTRIBUTED.**

The durable lesson does not depend on the cause: an irreplaceable corpus was
kept only under `/private/tmp`, reached through a symlink that made the path
look durable.

## 3. Inventory — measured, not recalled

### Two figures the preliminary note got wrong

| reported | actual |
|---|---|
| "`normalized/history` retained all 900 accounts" | **900 account directories exist and every one is empty** — 0 page files. The first count counted directories. |
| "Pass-2 survivors: 276" vs "278 files" | **278 canonical documents exist.** 2 contain no product-context rows at all, so 276 accounts reach analysis. Not a loss — a filter (`is_pass2_product_context`). |

### PASS-1 — `v7-corpus-2026-09-02`

| layer | files | accounts | rows | bytes | status |
|---|---:|---:|---:|---:|---|
| raw | 21,032 | — | — | 178.2 MB | **history responses lost** — only 1 `GetPlayerHistoryPage` survives; the rest are parsed batches |
| normalized/history | **0** | 900 dirs, all empty | 0 | 0 B | **lost** |
| normalized/parsed | 10,883 | 235 dirs (177 populated) | — | 486.3 MB | intact |
| canonical/history | **0** | **0** | **0** | 0 B | **lost** |
| canonical/parsed | 169 | 169 | 87,711 | 429.9 MB | partial (was 235; CANDIDATE_TEST 119, DISCOVERY 50) |
| manifests | 2 | — | — | 12.3 MB | intact |
| ledgers | 1 | — | — | 68.9 MB | intact |
| derived | 1 | — | — | 62.0 KB | intact |

Durable path: `<repo>/.local/corpora/stratz/v7-corpus-2026-09-02`
Volatile path (retained, unmodified): `/private/tmp/dota-report-card-v7-research/.local/corpora/stratz/v7-corpus-2026-09-02`
Hash manifest: 171 files, 463,617,312 bytes — built and verified.
Reproducibility: **history fits are NOT source-reproducible.** Parsed layer is.

### PASS-2 — `v7-pass2-2026-09-04`

| layer | files | accounts | rows | bytes | status |
|---|---:|---:|---:|---:|---|
| raw | 26,508 | — | — | 1.4 GB | intact |
| normalized | 13,253 | 278 dirs, all populated | — | 3.4 GB | intact |
| canonical | 278 | 278 (all DISCOVERY) | 104,982 | 3.4 GB | intact |
| manifests | 2 | — | — | 3.6 MB | intact |
| ledgers | 1 | — | — | 39.3 MB | intact |

Durable path: `<repo>/.local/corpora/stratz/v7-pass2-2026-09-04`
Hash manifest: 280 files, 3,651,258,616 bytes — built and verified.
Reproducibility: **fully source-reproducible.** Canonical can be re-derived
from normalized, which can be re-derived from raw.

Of the 278 canonical documents, 276 carry at least one product-context row and
so appear in analysis; 101,581 of the 104,982 collected rows are
product-context.

### Derived evidence (committed, unaffected)

All analytical outputs remain in `docs/evidence/`: the finding pipeline,
recommendation selection, archetype axes, cut-point calibration, capability
atlas, tournament and portfolio documents. None was lost.

## 4. What was recovered

1. **Rebuild attempted and correctly refused.** `canonical` is a pure function
   of `normalized`, so `scripts/stratz_v7_rebuild_canonical.py` was written to
   recompute it with the collector's own `canonicalize_history` /
   `canonicalize_parsed`. It found `normalized/history` empty and wrote
   nothing. It is committed regardless: it verifies each rebuilt account
   against the row count `state.json` recorded at collection time before
   writing, so it cannot fabricate a plausible corpus.
2. **Everything surviving was copied to durable storage** — the full 9.5 GB
   tree, both corpora, all layers, `rsync -a` preserving mtimes. Verified by
   per-layer inventory and by SHA-256 manifest over the immutable layers.
3. **The active corpus path no longer touches `/private/tmp`.** The worktree
   symlink was repointed after verification. The volatile copy is retained,
   unmodified, and may be deleted at the owner's discretion.

## 5. What cannot be reconstructed

The Pass-1 match-history corpus — 900 accounts (600 DISCOVERY, 300
CANDIDATE_TEST), roughly 2,900 provider requests.

**It is permanently unavailable.** Per owner decision, it will not be
re-collected as a replacement: time has advanced, so a fresh 365-day window
would be a different sample and could not restore source reproducibility of the
published results. Any future Pass-1 collection is a **new lineage** with its
own acquisition date, manifest and corpus id, and must never be presented as a
restoration of this one.

## 6. Provenance status of published claims

| claim | auditable | source-reproducible |
|---|---|---|
| The 12 Pass-1 Finding families (`duration_tempo`, `hero_novelty`, the three post-loss families, `position_flexibility`, `fight_timing_centroid`, `purchase_tempo`, `lead_retention`, `lane_recovery_participation`, `transfer_risk`, `transfer_activity`) | yes — figures committed | **no** |
| `side_sensitivity` negative control | yes | **no** |
| The 8 Pass-2 Finding dimensions | yes | yes |
| All 9 recommendation dimensions | yes | yes |
| Archetype axes and cuts | yes | yes |
| Frozen population parameters | yes | derived from committed evidence, not refit |

**Required caveat.** Any statement about a Pass-1 family must not claim source
reproducibility. The numbers are auditable — they are committed, digested and
traceable — but the corpus that produced them no longer exists.

## 7. Downstream work unaffected

The V7 backend phase does not depend on the lost corpus. The runtime consumes
frozen population parameters, which are derived from committed evidence; the
assembler, service boundary, persistence, fixtures and handoff need no corpus
at all. Pass-2, which carries 8 of the 16 Finding dimensions, every
recommendation and the entire archetype, is intact and reproducible.

## 8. Prevention

`app/player_analysis_v7/research/durability.py` refuses a corpus root that
resolves onto `/tmp`, `/private/tmp` or `/var/tmp`, and **follows symlinks** —
the path that lost this data read as `<repo>/.local/corpora/...` and a literal
string check would have passed it. Wired into the corpus loader, the freeze
loader, the Pass-2 loader, and both collectors' output roots (which is also
their resume/checkpoint root). Override requires an environment variable set to
an exact acknowledgement sentence; a truthy `1` is rejected.
