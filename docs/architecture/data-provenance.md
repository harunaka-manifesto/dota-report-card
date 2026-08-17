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
