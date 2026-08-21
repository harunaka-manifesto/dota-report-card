# Hero matchups and synergies

P02 may name representative enemy and teammate heroes, but only when the
relationship is supported by a versioned aggregate artifact. A player's own
bounded history is not a large enough sample for global matchup or synergy
claims.

## Artifacts

The report reads these checked-in snapshots only:

- `services/api/app/heroes/data/aggregate_matchups.v1.json` —
  `hero-matchups-1.0.0`
- `services/api/app/heroes/data/aggregate_synergies.v1.json` —
  `hero-synergies-1.0.0`
- the finite situation vocabulary in `app.heroes.evidence` —
  `hero-situations-1.0.0`

The initial snapshots are intentionally empty until a reviewed public-data
refresh is available. This makes the safe behavior explicit: P02 still
explains the functional difference and useful situation, but omits unsupported
hero-name examples instead of inventing counters or guaranteed synergy.

## Refresh and confidence policy

An offline refresh may use public aggregate match data such as OpenDota hero
matchups and sufficiently large teammate-pair samples. The refresh must store
hero IDs, sample size, adjusted score, confidence, patch scope, reason tags,
and artifact version. Pair scores must use sample-size adjustment, shrink
extreme values, respect patch freshness, and clear a confidence gate before a
name is selected.

The report-time selector sorts only eligible records by confidence, adjusted
score, sample size, and stable hero ID. It never fetches pairwise data per
report.

## Situation-first copy

The finite situation taxonomy describes why an expression difference matters:
reliable initiation, difficult-to-reach enemy backlines, save/reset needs,
wave clear, global pressure, sustained frontline presence, disengage, and
similar reviewed situations. Copy states the abstract situation first and
names representative heroes second. Examples are evidence, not deterministic
counters or guaranteed teammate combinations, and every example is omitted
when its artifact confidence is insufficient.
