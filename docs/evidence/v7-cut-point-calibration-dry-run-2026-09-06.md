# D2 and D7 calibration — dry run, 2026-09-06

```text
PHASE: V7_CUT_POINT_CALIBRATION
STATUS: MEASURED on DISCOVERY — reserved splits NOT spent
NEW PROVIDER CALLS: 0
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
```

Artifacts: `scripts/v7_calibrate_cut_points.py`,
`docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.json`.

The owner's step 2 was to spend `CALIBRATION_RESERVED` on D2 and D7. Before
spending it I ran the same fitting code on DISCOVERY, which is what the fitter's
`--split` argument exists for. **The dry run answers D7 outright and shows that
D2 cannot be delivered as specified — and that the reserved split would not
change either answer.**

Nothing reserved was read. The recommendation at the end is to spend nothing.

---

## 1. D7 is answered, and the answer is "it does not bind"

Sweeping the minimum matches per arm from 10 to 30:

| minimum per arm | players with a recommendation | gap reliability (median) | priority (median) |
|---:|---:|---:|---:|
| 10 | 265 | 0.981966 | 0.07291 |
| **15** | **265** | **0.981934** | **0.072748** |
| 20 | 262 | 0.982237 | 0.072256 |
| 25 | 262 | 0.982367 | 0.072134 |
| 30 | 258 | 0.982515 | 0.072107 |

Tripling the requirement buys **five ten-thousandths** of median gap
reliability and costs seven players their recommendation. The threshold is not
binding anywhere in the plausible range: the gaps that survive are already
measured well, and the ones that fail do so for want of the dimension, not for
want of matches.

**Proposal: keep 15 and mark D7 settled.** Not because 15 was fitted, but
because the sweep shows the choice does not matter over the range worth
considering. Spending a reserved split to discover that a flat curve is flat
would be spending it for nothing.

---

## 2. D2 cannot be delivered as specified

The owner chose absolute cut points on `|z| × reliability`. A cut point is only
worth having if the band it assigns is not an accident of measurement error, so
each candidate pair was scored by how many Findings have a 95% interval
straddling a cut — those have been given a band the data cannot support.

Across 4,983 player-Findings, the best pair that keeps every band populated
above 5%:

| pronounced ≥ | moderate ≥ | pronounced | moderate | slight | **ambiguous** |
|---:|---:|---:|---:|---:|---:|
| 1.50 | 1.00 | 5.8% | 10.3% | 83.9% | **65.2%** |

Two thirds of Findings would carry a band the interval does not distinguish
from its neighbour.

The candidates that do better on ambiguity do so by emptying the bands:

| pronounced ≥ | moderate ≥ | pronounced | moderate | slight | ambiguous | bands populated |
|---:|---:|---:|---:|---:|---|
| 1.75 | 1.50 | 3.4% | 2.3% | 94.2% | 26.9% | no |
| 2.00 | 1.50 | 2.1% | 3.7% | 94.2% | 27.3% | no |
| 1.50 | 1.25 | 5.8% | 4.0% | 90.2% | 43.1% | no |

There is no pair that is both populated and unambiguous, and the reason is
arithmetic rather than bad luck. A typical player-Finding's 95% interval on
`|z| × r` is about **0.6 wide**, while any band scheme that keeps three bands
populated needs cuts about **0.5 apart**. The interval is wider than the band.

### Why the reserved split does not fix this

The interval width is `1.96 × SE × √D / τ × r` — dominated by *within-player*
measurement error, which is set by how many matches that player has, not by how
many players are in the cohort. Adding 150 accounts sharpens the population
estimate of `τ` slightly and leaves every per-player interval essentially
untouched.

**More players cannot sharpen a per-player band assignment.** Calibrating on
`CALIBRATION_RESERVED` would reproduce this table with different decimals and
the same conclusion.

### What would actually work

Options, in the order I would consider them:

- **(a) Two bands instead of three.** One cut is straddled by fewer Findings
  than two. At a single cut of 1.0 the split is roughly 16% / 84%, which is
  lopsided but honest.
- **(b) Report the band as a range when the interval straddles a cut** —
  "moderate, possibly pronounced". Keeps three bands and stops the report
  claiming a precision it does not have.
- **(c) Drop the adjective** and show direction, the shrunk estimate and its
  interval. This was D2 option (c), which the owner declined; the dry run is
  the argument they did not have at the time.
- **(d) Band the portfolio rather than each Finding.** A reader's *strongest*
  Finding can be banded far more reliably than all five, because the top of a
  slate is further from the cuts.

I have not implemented any of these. D2 is the owner's decision and this is
new information bearing on it, not a mandate to re-decide.

---

## 3. What spending `CALIBRATION_RESERVED` would have cost

Recorded so the decision not to spend it is a measured one.

The split holds **150 frozen account identities and zero collected data**. The
frozen split manifest (digest `ef24c63b…4275d885`, verified intact) also sets
`parsed_subset_counts` to **0** for both reserved splits — no reserved account
was ever designated for parsed collection.

Calibrating anything Pass-2-dependent would therefore have required:

| step | requests | wall clock |
|---|---:|---|
| Pass-1 history for 150 accounts | ≈ 2,935 | ≈ 2 h |
| Pass-2 deep collection for the same 150 | ≈ 6,630 | ≈ 4.5 h |
| **total** | **≈ 9,565** | **≈ 6.5 h** |

Within one day's 15,000-request ceiling. It would also have required
deliberately relaxing `PASS2_SPLIT`, a fail-closed guard that refuses any split
but DISCOVERY at four separate points, and either amending the frozen parsed
subset or accepting that the five parsed-dependent Pass-1 families stay
uncalibrated.

**Recommendation: spend none of it.** D7 is settled by a flat curve. D2 is
blocked by per-player precision, which more accounts do not improve. The
reserved split keeps its value by remaining unspent, and `SEALED_VALIDATION`
remains untouched and unapproved, as instructed.

---

## 4. Standing limits of this dry run

- **DISCOVERY is where the models were built.** The D2 ambiguity figure is
  therefore an optimistic reading, not a pessimistic one — held-out data would
  not make band assignment *more* certain.
- **The fitter is unrun on a reserved split.** `--split` is exercised only on
  DISCOVERY here. It refuses `SEALED_VALIDATION` outright while
  `SEALED_VALIDATION_APPROVED` is `False`.
- **The interval treats reliability as fixed.** `r` is a population-level
  variance ratio and its own uncertainty is an order of magnitude below the
  per-player uncertainty in `z`; folding it in would widen the intervals and
  strengthen the conclusion above rather than weaken it.
