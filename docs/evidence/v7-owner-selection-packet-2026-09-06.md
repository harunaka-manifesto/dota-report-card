# V7 owner selection packet — 2026-09-06

```text
PHASE: V7_OWNER_SELECTION
STATUS: AWAITING OWNER DECISIONS
NEW PROVIDER CALLS: 0
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
```

Research is done and the gates are green
(`docs/evidence/v7-phase-close-qa-2026-09-06.md`). Everything below is a
decision that is yours, not mine. Each carries the measurement that bears on
it, the options with their consequences, and what I would pick — clearly marked
as a recommendation, not a default. **Nothing here has been applied.**

Nine decisions. Three of them (D1, D2, D8) change what the reader sees most.

---

## The budget you are spending

| split | accounts | state |
|---|---:|---|
| DISCOVERY | 600 | spent — all research above |
| CANDIDATE_TEST | 300 | spent once, on the tournament |
| CALIBRATION_RESERVED | 150 | **untouched** |
| SEALED_VALIDATION | 150 | **untouched** |

Pass 2 (parsed, event-level) covers **276 DISCOVERY accounts**. There is no
Pass-2 collection on either reserved split. That constrains D9.

`SEALED_VALIDATION` can be read **once**. Reading it twice makes it a second
calibration set and there is no third.

---

## D1 — Does a score line gate what the reader sees?

**What is at stake.** Whether a Finding can be withheld for being weakly
measured, or whether the report always shows the reader's top five whatever
their scores.

**Measured.** 0.25 is a comparison scale carried from the reliability table, not
a threshold anything was fitted to. Against it: 88.6% of players carry three or
more Findings above the line, 52.5% carry five, and 1.3% (7 players) carry none.

| Findings above 0.25 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---:|---:|---:|---:|---:|---:|
| players | 285 | 110 | 86 | 39 | 16 | 7 |

**Options.**

- **(a) No gate.** Always show the top five. Everyone gets a full report; the
  weakest slates are padded with material that is technically their strongest
  but not strongly measured.
- **(b) Gate at 0.25.** 7 players see fewer than one Finding. Honest, and it
  means some reports are visibly thin.
- **(c) Gate, with a floor of three.** Show at least three regardless, gate
  slots four and five.

**My recommendation: (c).** It keeps the report from ever looking broken while
still refusing to dress up the weakest two slots. But (b) is the more honest
option and I would not argue against you picking it.

**This does not need a reserved split.** It is a product decision you can make
today.

---

## D2 — Strength bands: what do "pronounced / moderate / slight" mean?

**What is at stake.** The contract has three bands and provisional cut points
that the ranking-model document explicitly defers. Until you set them, no
report can render a Finding's strength honestly.

**Measured.** Top-Finding score across 543 players: p5 0.470, p25 0.943, median
1.292, p75 1.723, p95 2.763, max 10.849.

**Options.**

- **(a) Population terciles** on the reserved split — a third of Findings in each
  band by construction.
- **(b) Absolute cuts** tied to `|z| × r`, e.g. pronounced ≥ 2, moderate ≥ 1.
  Bands then mean something fixed, and the mix varies by player.
- **(c) No bands.** Show direction and the estimate; drop the adjective.

**My recommendation: (b).** Terciles make "pronounced" mean "top third of your
own five", which is a ranking wearing an absolute word. (c) is the safest and
the least useful.

**Needs CALIBRATION_RESERVED** if you want the cuts fitted rather than chosen.

---

## D3 — The modal-sign screen sits one point above your best recommendation

**What is at stake.** The screen that keeps circular advice out of section 5.

**Measured.** The cut is 0.95, fixed before the shares were computed.

| dimension | modal-sign share | |
|---|---:|---|
| fight_conversion | 1.0000 | excluded |
| death_clustering | 0.9886 | excluded |
| **last_hits_at_ten** | **0.9466** | **kept — and wins 51% of all slots** |
| spike_usage | 0.8415 | kept |

At a cut of 0.94, last hits is excluded and section 5 loses its strongest and
most actionable recommendation. At 0.96, nothing changes.

**Options.**

- **(a) Keep 0.95.** Accept that the top recommendation sits one point inside the
  line.
- **(b) Raise to 0.98.** Keeps last hits comfortably, still excludes
  fight_conversion (1.0000) but **readmits death_clustering** (0.9886), which
  took 60% of slots on a gap positive for 260 of 263 players.
- **(c) Replace the screen with a window rule** — only dimensions measured before
  a fixed minute are eligible. Principled, and it cuts section 5 to three
  dimensions.

**My recommendation: (a).** Last hits is also the one dimension structurally
protected from this failure mode, being measured entirely before minute 10, so
its high share is explainable rather than suspicious. I want you to see the
sensitivity rather than inherit it.

---

## D4 — Which dimensions actually ship?

**What is at stake.** Sixteen dimensions carry signal; reliability ranges from
0.985 to 0.257.

**Measured**, median reliability: vision_coverage 0.985, duration_tempo 0.976,
death_clustering 0.925, lane_vs_jungle_share 0.924, purchase_tempo 0.921,
deaths_alone_share 0.893, spike_usage 0.887, position_flexibility 0.828,
fight_timing_centroid 0.810, hero_novelty 0.736, closer_vs_comeback 0.651,
post_loss_session_continuation 0.537, lead_retention 0.480,
post_loss_hero_switch 0.463, post_loss_requeue_latency 0.380, fight_conversion
0.257.

**Options.**

- **(a) All sixteen.** Reliability already shrinks weak estimates toward the
  population, so a low-reliability dimension rarely wins a slot anyway.
- **(b) Drop below 0.40** — removes post_loss_requeue_latency and
  fight_conversion.
- **(c) Drop below 0.50** — also removes post_loss_hero_switch and
  lead_retention, and thins section 4 noticeably.

**My recommendation: (a).** The shrinkage is the gate; adding a second one
double-counts the same caution. Worth noting: section 4 ("response to a loss")
is carried mostly by the post-loss families, which sit at the bottom of this
table. Option (c) would leave that section thin.

---

## D5 — Does the archetype ship a three-level tempo axis?

**What is at stake.** Tempo is reliably measured (split-half `r = 0.970`) and
tightly packed: within a mode stratum the terciles sit 0.015–0.018 apart on a
p5–p95 range of about 0.075.

So the ordering is real, and the gap between "early" and "mid" separates
players who are genuinely close.

**Options.**

- **(a) Ship three levels.** The label is a ranking within a narrow band; copy
  must not imply a gulf.
- **(b) Collapse to two** (early / late), splitting at the median — a coarser
  claim, more comfortably supported.
- **(c) Drop tempo**, leaving fight style × modifier = 6 archetypes.

**My recommendation: (a) with constrained copy.** All 18 cells are occupied and
the largest holds 9.6%, so the grid does spread people out. The narrative
document already licenses this section as "for fun, not for science" — the risk
is copy that forgets that, not the axis.

---

## D6 — Do the two special archetypes ship?

**What is at stake.** "The Lighthouse" and "The Closer" bypass the 18-cell grid
at the 98th percentile.

**Measured.** 13 of 262 players (5.0%) — 7 Lighthouse, 6 Closer.

**Options.** **(a)** ship both; **(b)** ship neither and keep a clean 18;
**(c)** ship them at a rarer cut (99th) so a special feels earned.

**My recommendation: (a).** Both are strengths, which matters because section 7
turns the archetype into a share card and a share card must not be an insult.
5% is rare enough to feel like something.

**The 98th-percentile cut is corpus-relative** and will drift as the player base
changes. Whatever you pick needs refreshing alongside D2.

---

## D7 — Minimum matches per arm for a recommendation

**What is at stake.** Constraint 2 of the recommendation model: no
recommendation without a denominator.

**Measured.** At the working value of 15 per arm, 10–24 players per dimension
are refused for insufficient support, and all 265 who qualify anywhere still
receive exactly one recommendation.

**Options.** **(a)** keep 15; **(b)** raise to 25, refusing more players a
recommendation on their best dimension but tightening every gap that survives;
**(c)** fit it against the reserved split.

**My recommendation: (a) now, (c) later.** Nobody is currently left with zero
recommendations, so 15 is not visibly too loose, and this is a cheap thing to
revisit once D2 is being calibrated anyway.

---

## D8 — Which reserved split gets spent, and on what

**What is at stake.** This is the one decision that cannot be undone.

**The position.** `CALIBRATION_RESERVED` (150) and `SEALED_VALIDATION` (150) are
both untouched. D2 and D7 want a calibration set. Nothing so far has been
validated on data it did not help shape — every number in this packet comes
from DISCOVERY, which is where the models were built.

**Options.**

- **(a) Spend CALIBRATION_RESERVED on cut points; keep SEALED_VALIDATION sealed
  until the product is otherwise final.** One honest end-to-end validation
  remains available.
- **(b) Spend both now** — calibrate on one, validate immediately on the other.
  Faster; leaves nothing in reserve for changes made after validation.
- **(c) Ship with the provisional cuts and spend nothing.** Everything stays
  DISCOVERY-derived, and the report has never been checked against data it did
  not shape.

**My recommendation: (a), firmly.** The value of a sealed split is entirely in
having resisted using it. (c) is defensible for a v1 that is explicitly a
prototype, but then the honest framing to the reader is that these are
calibrated against a sample, not validated.

---

## D9 — The parsed-match budget in production

**What is at stake.** Sections 2–6 lean on Pass-2 event data. In research that
is 276 accounts at ~380 parsed matches each; in production it is a per-user
fetch at report time.

**Measured.** Pass 2 spent 13,264 requests against 300 targeted accounts, of
which 276 landed in the corpus — roughly 48 requests per player at a 500-match
target. Provider ceilings are 1,500/hour and
15,000/day, so a day's budget is about **310 full reports**.

**Options.**

- **(a) Full depth per user** (~48 requests). Best report, ~310/day.
- **(b) Capped depth** — the most recent 200 matches, ~20 requests, roughly
  750/day. Archetype needs 20 matches in a mode stratum and recommendations
  need 15 per arm, so both still work; the confidence intervals widen.
- **(c) Two-tier** — capped depth free, full depth on the paid tier. Section 8
  already exists to carry that boundary.

**My recommendation: (c).** It matches the report's own structure and makes the
paid tier a difference in evidence rather than a difference in copy.

**This needs no reserved split** and is independent of everything above.

---

## What happens once you decide

D1, D3, D4, D5, D6 and D9 are product calls I can implement immediately. D2 and
D7 need a calibration run, which is gated on D8. D8 is the only irreversible
one.

Tell me the calls and I will implement them, or take any one of them and I will
put the case for the alternatives in more depth first.
