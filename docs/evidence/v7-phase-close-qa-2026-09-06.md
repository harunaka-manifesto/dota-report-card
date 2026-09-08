# V7 phase close — QA record, 2026-09-06

```text
PHASE: V7_PHASE_CLOSE
STATUS: VERIFIED — gates green, published artifacts reproduce
NEW PROVIDER CALLS: 0
CORPUS READ: YES — DISCOVERY only
CANDIDATE_TEST READ: NO
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
```

This closes the research phase. Nothing here spends a reserved split, and after
the owner's decisions of 2026-09-06 nothing remaining requires one — see
`docs/evidence/v7-owner-decisions-2026-09-06.md` for the outcomes and
`docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.md` for why D2 and
D7 closed without spending `CALIBRATION_RESERVED`.

Re-verified after the owner's decisions landed: the archetype and
recommendation artifacts still reproduce byte-identically, and the Finding
pipeline was regenerated under the D1 gate.

## 1. Gates

| gate | result |
|---|---|
| `pytest tests/unit` | 1,176 passed |
| `mypy` | no issues in 221 source files |
| `ruff check` | clean |
| `check_docs` | ok |

## 2. Reproduction

Every published artifact was regenerated from a clean run after the rank fence
was wired into both corpus loaders, and compared against the committed file.

| artifact | result |
|---|---|
| `v7-archetype-axes-2026-09-06.json` | byte-identical |
| `v7-finding-pipeline-2026-09-05.json` | identical (excluding `code_sha`) |
| `v7-recommendation-selection-2026-09-06.json` | byte-identical |

The fence therefore changes nothing except what it refuses. That was the point
of re-running rather than reasoning about it.

## 3. What the phase produced

| report section | status | coverage |
|---|---|---|
| 1 — history | contract only; receipts, not Findings | — |
| 2 — what is good | ranked Findings | 97.8% get a full five-slot slate |
| 3 — what is costing you | ranked Findings | 95.8% get all three sections covered |
| 4 — response to a loss | ranked Findings | 88.6% carry three or more above the 0.25 line |
| 5 — what to improve | one recommendation, seven eligible dimensions | 265 of 276 Pass-2 players; none get zero |
| 6 — archetype | 18-cell grid plus two specials | 262 of 276; all 18 cells occupied, largest 9.6% |
| 7–9 — share card, paid bridge, closing | contract only | assembly over material that now exists |

Sixteen dimensions carry between-player signal. Five estimate `tau` at exactly
zero, including the negative control, which is the result that says the
estimator is not manufacturing Findings from noise.

## 4. Defects this phase caught by running things

Recorded because each was found by measurement rather than review, and each
would have shipped.

| defect | consequence had it shipped |
|---|---|
| `D` read at a fixed batch length fell back to independence on four Pass-2 dimensions | `lane_to_map` would have published a Finding whose entire spread was measurement error |
| A measured `D` below 1.0 was accepted | free reliability for two dimensions |
| The archetype tempo axis was a turbo detector (`r = 0.889` with queue share) | players labelled by the queue they pick, not how they play |
| Session dispersion used population variance | the modifier biased ~12% toward "metronome" |
| `tau_d` used as the recommendation denominator | section 5 ships nothing at all |
| The win/loss arm projected out as a context factor | a population comparison presented as a personal gap |
| The upstream rule alone let `fight_conversion` through | 168 of 265 players told something that restates that they lost |
| `spike_usage` excluded by argument rather than measurement | a valid recommendation lost |
| Rank fencing was a docstring | nothing would have caught a feature reading rank |

## 5. Standing limits

Carried forward, not resolved:

- **`D` is a lower bound where the variance-ratio curve has not plateaued**, so
  those reliabilities are upper bounds. Contrast families plateau; level
  families largely do not over a 365-day window.
- **`spike_usage` changes estimand between the census and the ranking** — median
  there, mean here.
- **Pass 2 has no negative control of its own.** The two zero collapses are
  reassuring, not designed.
- **Archetype and Pass-2 Findings need parsed matches**, so research coverage is
  the 276-player Pass-2 subset.
- **Most cut points are now settled.** The 0.95 modal-sign screen (D3) and the
  15-match-per-arm minimum (D7) are final; the strength bands (D2) were dropped
  rather than calibrated. The 0.25 score line stands as the D1 gate. The
  98th-percentile archetype special cut is the one provisional value left, and
  it is refreshed from pilot data rather than from a reserved split.
