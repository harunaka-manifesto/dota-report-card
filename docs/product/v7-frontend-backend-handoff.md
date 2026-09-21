> **Legacy report-card documentation — non-authoritative for Dota Tracker.**
> For current product and architecture rules, start at [Dota Tracker](../tracker/README.md).
> Retained for the live report product, compatibility and historical evidence.

# V7 frontend/backend handoff

Status: **backend analytical runtime and contract usable; public generation entry point not yet exposed**.
Story and UI decisions live in `V7 Master Experience Plan v1.md`. This document
only defines the backend boundary.

## Entry points and versions

- Typed persisted read: `GET /v1/v7/reports/{report_id}`.
- Assembly: `app.player_analysis_v7.assembly.assemble_v7_capability`.
- Contract: `v7-capability-payload-2.0.0`.
- Descriptive facts: `v7-descriptive-facts-1.0.0`.
- Display semantics: `v7-display-semantics-1.0.0`.
- Public projection: `v7-public-projection-1.0.0`.

`app.player_analysis_v7.service.V7RuntimeService` implements acquisition through
persistence and is attached when the STRATZ provider is selected. A public
generation endpoint is intentionally deferred to product integration. The typed
read rejects non-V7 persisted documents.

## Contract use

`descriptive_facts.scope` distinguishes requested and observed intervals,
eligible/parsed/acquired counts, provider-reported completeness, and the depth
limit. Only `coverage_status=complete` permits maximum language such as
“busiest”. A truncated report uses its real dates and “recorded” semantics.

`hero_cast.heroes` is eligible usage ordered by count then stable hero ID.
Tie fields prevent that serialization tie-break becoming a false favorite.
Missing display metadata omits that display row and never triggers a provider
call.

`activity_memory` is seven consecutive UTC dates and is omitted unless two
non-overlapping populated stretches exist and the selected stretch has at least
three games. `monthly_hero_contrast` requires adjacent fully covered months,
ten eligible games per month, unique leaders at 30% or more, and different
heroes. `completed_loss_run` is private, never share-safe, and only describes a
loss sequence immediately followed by a recorded win.

For contrast Findings, use `own_contrast_direction`; never substitute
`direction`/`sign(z)`. `display_semantics.findings` supplies the exact estimand,
unit, and conversion policy. In particular, `lead_retention` is a
decided-ahead/decided-behind win-indicator contrast, `purchase_tempo` is
normalized progress at the eighth purchase, and `vision_coverage` is own
observer-ward uptime—not literal map area or quality.

`recommendation` is private and associational. Its instruction and verification
must match the canonical registry, with `upstream_of_result=true` and
`outcome_contaminated=false`. `archetype` is absent unless all approved axes
qualify; never synthesize a default. A Special replaces the normal public
identity and must not expose its percentile cut.

`public_projection` is the only default public/share input. It selects Special,
normal Archetype, favorable Finding, named hero, activity, or honest
count/window in that order. It excludes Recommendation, loss run, scores,
intervals, rank, raw history, research identifiers, and private provenance.

## Persistence and editorial boundary

`V7ReportLifecycle` reuses completed reports and the repository's atomic
in-flight coalescing. Its analytical identity excludes presentation/story
versions, so an editorial revision does not require acquisition. Reopening a
persisted report reads the saved projection without recomputation or provider
access.

Frontend may choose scene order, progressive disclosure, framing, layout, and
motion. It must never parse raw history, calculate dates or hero leaders, rank
Findings, convert adjusted/log values without a supported conversion, select a
Recommendation or Archetype, sanitize the private report for sharing, or
import research code.

Credential-free state fixtures live at
`tests/fixtures/v7/master-plan-descriptive-states.json`; executable checks are
in `tests/unit/test_v7_descriptive.py` and
`tests/unit/test_v7_capability_payload.py`. They contain no real identifiers.
