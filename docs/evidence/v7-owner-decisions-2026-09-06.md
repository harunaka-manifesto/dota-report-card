# V7 owner decisions — outcomes, 2026-09-06

```text
PHASE: V7_OWNER_DECISIONS
STATUS: ALL NINE CLOSED — no reserved split spent
NEW PROVIDER CALLS: 0
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
```

The packet in `docs/evidence/v7-owner-selection-packet-2026-09-06.md` put nine
decisions to the owner. This records what came back and where each one lives in
code. The machine-readable copy is `services/api/app/player_analysis_v7/research/owner_decisions.py`,
and `tests/unit/test_v7_owner_decisions.py` holds every one of them in place —
including the six that were "keep what is already there", because a behaviour
that matches a decision by accident is one refactor away from violating it.

## 1. The nine

| | decision | choice | where it lives |
|---|---|---|---|
| **D1** | Score line gates the reader's slate | floor of three, gate slots 4–5 | `ranking.apply_score_gate` |
| **D2** | Strength bands | **dropped entirely** | removed from `report_contract` |
| **D3** | Circularity screen cut | keep 0.95 | `recommendation.MODAL_SIGN_SHARE_LIMIT` |
| **D4** | Which dimensions ship | all sixteen | no reliability floor, by test |
| **D5** | Tempo levels | keep three | `archetype.TEMPO_LEVELS` |
| **D6** | Special archetypes | ship both | `archetype.SPECIAL_LABELS` |
| **D7** | Minimum matches per arm | keep fifteen | `recommendation.MIN_PER_ARM` |
| **D8** | Reserved splits | spend neither | both untouched |
| **D9** | Production acquisition | full depth, persist and reuse | `acquisition_policy` |

**No decision retains a claim on a reserved split.** `NEEDS_RESERVED_SPLIT` is
empty and a test holds it empty, so reintroducing such a claim is a deliberate
act rather than a flag someone flips.

## 2. D2 changed on measurement, and it is the one worth reading

The owner first chose absolute cut points on `|z| × reliability`, to be fitted
against `CALIBRATION_RESERVED`. Running the fitter on DISCOVERY first showed
the bands cannot be assigned honestly at any cut points:

- Over **4,983 player-Findings**, the best pair keeping all three bands
  populated above 5% leaves **65.2%** with a 95% interval straddling a boundary.
- Pairs that reduce ambiguity do it by emptying the top bands.
- The cause is arithmetic: a typical interval on `|z| × r` is about **0.6 wide**
  and three populated bands need cuts about **0.5 apart**.
- The interval is dominated by *within-player* measurement error, set by a
  player's match count rather than cohort size, so **more accounts cannot narrow
  it**. The reserved split would have reproduced the same table.

The owner's revised call is D2 = (c): drop the adjective. A Finding now carries
direction, score, and a shrunk point estimate with its interval — which says
what a band would have said, at the precision the data actually supports.

`StrengthBand`, `default_strength_band` and the band-monotonicity payload check
are gone from the contract. The invariant that remains is the one worth
enforcing: `score = |z| × reliability`.

## 3. D7 closed without spending anything either

Sweeping the minimum matches per arm from 10 to 30 moves median gap reliability
from **0.981966 to 0.982515** — five ten-thousandths — while coverage falls from
265 players to 258. The threshold does not bind anywhere in the range worth
considering.

Fifteen stands because the curve is flat, not because fifteen was fitted. The
distinction is recorded in the decision record so nobody later mistakes it for a
calibrated value.

## 4. What is still open

- **D6's 98th-percentile special cut** is corpus-relative and remains
  provisional. With both reserved splits staying untouched it is fixed for the
  pilot and refreshed from real pilot data. It is the only provisional value
  left.
- **Report sections 7–9** (share card, paid bridge, closing) exist in the
  contract and have no assembly, because there is no V7 report pipeline to
  assemble into yet.
- **D9's persistence half** is stated as requirements against
  `acquisition_policy.PERSISTENCE_REQUIREMENTS`, not built. The policy decides;
  the storage wiring lands with that same pipeline.

## 5. Both reserved splits remain sealed

`CALIBRATION_RESERVED`: 150 frozen identities, zero rows collected, unspent.

`SEALED_VALIDATION`: 150 frozen identities, zero rows collected, unopened.
`SEALED_VALIDATION_APPROVED` is `False`; the calibration fitter refuses the
split outright while it stays false, and the corpus reader fails closed on both
reserved splits regardless. It is opened only on the owner's express approval.
