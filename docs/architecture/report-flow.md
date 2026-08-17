# Report flow

## Public v4 shape

The strict top-level contract is:

identity, metadata, versions, quality, elements, patterns, highlights,
hero_portfolio, story, pages, shares, deep_dive, methodology, and cost.

There are exactly 17 public Element entries and 14 public Pattern entries.
Private scorer metrics, source IDs, raw rows, and account IDs are not in the
schema.

## Story order

1. Element scan
2. Three Element highlights
3. Up to three Pattern highlights
4. Common Thread question/reveal
5. Exception question/reveal
6. Pool Evolution question/reveal
7. Hero Mirror reveal
8. Final card and share
9. Deep Dive teaser

Every page has a stable ID and story.ordered_pages must equal serialized page
order. A user must choose an answer before a Portfolio reveal; wrong choices
are non-punitive and unavailable insights explain their evidence limit.

## Interaction telemetry

The web story emits versioned events for page views, Element/Pattern
expansion, Portfolio question/answer/reveal, Mirror start/completion, share
open/completion/failure, and Deep Dive CTA clicks. Payloads contain no account
ID, report ID, player name, or raw match ID.
