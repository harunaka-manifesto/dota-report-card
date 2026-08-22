# Hero data sources and governance

Access date: `2026-08-22`

Status: `implemented`

The automated source stack is intentionally bounded. Source permission does
not expand this implementation beyond the plan: DOTABUFF is excluded from the
automated pipeline, and no challenge bypass, stealth automation, identity
rotation, CAPTCHA solving, or manually copied HTML is part of the system.

## Supported source stack

| Provider | Meaning | Retrieval policy | Release gate |
| --- | --- | --- | --- |
| Valve Dota 2 datafeed | Canonical hero identity and official mechanics | Build-time live fetch, cached and versioned | Required |
| OpenDota aggregate API | Baseline empirical hero context | Build-time live fetch, cached and versioned | Required |
| Valve Dota Plus public web endpoints | Optional experimental enrichment | Fixture seam only until an endpoint contract is separately validated | Non-blocking |
| Existing `heroes_metadata/*.md` corpus | Editorial and strategy research input | Checked-in build-time evidence; never overwritten | Review input |

## Explicitly unsupported automated source

| Provider | Status | Reason | Policy |
| --- | --- | --- | --- |
| DOTABUFF | `unsupported_automated_source` | `cloudflare_access_constraint` | Do not call, bypass, or retain a dormant adapter/fixture path |

This is a product and operational boundary, not a statement about whether a
particular account has permission to access the site. The repository contains
no DOTABUFF adapter, command, fixture, or release dependency.

## Valve / Dota 2

Valve is the source of truth for canonical hero identity and official game
mechanics. The ingestion adapter uses the public datafeed rather than rendered
hero pages:

- [Hero roster](https://www.dota2.com/datafeed/herolist?language=english)
- [Hero detail](https://www.dota2.com/datafeed/herodata?hero_id=2&language=english)
- [Patch list](https://www.dota2.com/datafeed/patchnoteslist?language=english)

The allowed fetch scope is the roster, one detail response per selected hero,
and the patch list. Requests use a descriptive user-agent, a disk cache,
bounded concurrency, finite retries, deterministic output ordering, and
recorded raw payload hashes. Missing optional fields remain `null`, empty
lists, or explicit unknowns; they are never converted into neutral scores.

## OpenDota

The required empirical adapter uses the public endpoints documented by
[OpenDota](https://docs.opendota.com/):

- `GET /heroStats`
- `GET /heroes/{hero_id}/durations`
- `GET /heroes/{hero_id}/itemPopularity`
- `GET /heroes/{hero_id}/matchups`

The normalized record retains the source URL, fetch time, raw hash, parser
version, and endpoint-specific population notes. `heroStats` rank-tier/public
and professional fields retain their source labels. Matchup rows are labeled
`opendota_aggregate`; because the matchup payload does not identify a narrower
population, the pipeline does not call those rows general-player or
professional-only evidence.

OpenDota facts map to the canonical empirical fields:

- `bracket_performance`: picks, wins, and rates by source-labeled population;
- `duration_profile`: duration bins and observed games/wins;
- `item_profile`: item IDs, purchase phase, observed counts, and shares;
- `matchup_profile`: opponent IDs, observed games/wins, and population note;
- `optional_valve_plus`: an empty object unless optional enrichment is present.

OpenDota outages, malformed payloads, or incomplete required hero coverage make
the fetch/build command fail non-zero. The raw partial snapshot remains
available for diagnosis; the API is never asked to fetch it at runtime.

## Optional Valve Dota Plus enrichment

Valve Plus is represented as a non-blocking provider with the states
`available`, `partial`, `invalid_schema`, and `unavailable`. The current
implementation records `unavailable` unless a fixture is supplied; it does
not make an undocumented service endpoint a release dependency. Optional
failure cannot block Valve/OpenDota knowledge generation.

## Provenance and refresh policy

Every normalized source snapshot and generated knowledge record carries source
versions, timestamps, raw hashes where available, and derivation rule versions.
The API reads only a frozen generated snapshot; it never makes source requests
during report generation.

- Valve: check weekly and force refresh after a known gameplay patch.
- OpenDota: refresh on the same build-time cadence; required-source failure is
  visible and non-zero.
- Valve Plus: refresh only when its optional contract/fixture is intentionally
  supplied.
- Editorial: review heroes affected by mechanical or schema changes.
