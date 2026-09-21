# Lane Difficulty research code

Read-only analysis behind [`../LANE-DIFFICULTY-RESEARCH-V1.md`](../../research/LANE-DIFFICULTY-RESEARCH-V1.md).
No STRATZ calls: everything reads cached corpora already under `.local/`.

Run from a working directory containing the generated `.pkl` files, in order:

| Script | What it does |
|---|---|
| `build.py` | ten-player lane rows from `.local/stratz-probe/*/raw` → `rows.pkl` |
| `build_big.py` | tracked-player lane rows from the v7 Pass-2 canonical corpus → `big.pkl` |
| `merge.py` | dedupe on `(match_id, hero, position)` → `merged.pkl` (98,263 matches) |
| `vardecomp.py` | shrunken additive backfitting model + 5-fold CV R² (imported by the rest) |
| `big_analysis.py` | variance decomposition M0–M4 per role/bucket |
| `final_bands.py` | half-sample label stability across band widths — the 20/60/20 decision |
| `baseline_test.py` | difficulty vs hero adjustment against the real personal rolling baseline |
| `placebo.py` | falsification: lane-local vs bracket-proxy, wrong-lane placebo |
| `per_metric.py`, `transfer.py` | per-metric effects and one-score transfer loss |
| `window.py` | 8 / 10 / 12-minute checkpoint comparison |
| `validate.py` | hero effect tables and worked Phantom Assassin examples |
| `stability.py`, `bands.py`, `envspread.py`, `extra.py` | patch stability, sample size, fragmentation counts |

`vardecomp.py` defaults to `rows.pkl`; scripts that use the merged corpus
rebind `vardecomp.rows` on import.
