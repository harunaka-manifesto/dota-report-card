# Data provenance

## Free source boundary

The public Free report is derived from one bounded summary-history request plus
the public profile. Raw payloads remain server-side. The public projection
carries a history hash, date bounds, counts, quality warnings, receipts, and
version fingerprints.

The cost contract is strict:

~~~json
{
  "detail_requests": 0,
  "parse_requests": 0
}
~~~

## Privacy

Public output omits account IDs, source match IDs, normalized/private record
references, raw scorer metrics, and raw match rows. Display name and avatar
are sanitized. Share cards never include a raw identifier.

## Evidence handling

Missing source fields remain missing through normalization, feature coverage,
Element scoring, Pattern qualification, and Portfolio eligibility. Each layer
may lower confidence or return unavailable/no-clear; it cannot create a
synthetic neutral value.

## Hero action artifacts

P01 and P02 are derived from the reviewed hero taxonomy, bounded hero history,
and explicitly versioned relationship, expression, and reliability artifacts.
Matchup and teammate examples are read from checked-in aggregate snapshots
only; when those snapshots do not clear their confidence gate, the report
emits a useful situation and an explicit limitation instead of inventing named
examples. The action provenance versions are included in the Free analysis
fingerprint.
