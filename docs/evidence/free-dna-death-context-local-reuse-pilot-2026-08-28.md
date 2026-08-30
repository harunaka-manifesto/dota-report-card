# Free DNA — Death Context Local-Reuse Pilot

## Status

**PARTIAL** — local reuse was audited and the deterministic panel was frozen,
but the retained parsed-detail corpus cannot supply the registered panel.

`LOCAL_REUSE_STATUS = INSUFFICIENT`

## Main result

The retained OpenDota corpus has 1,200 match-detail attempts and 19 parsed
detail bodies (`version = 22`, `od_data.has_parsed = true`). The new private
HMAC panel selected 32 development profiles and 960 globally unique summary
match IDs before outcome inspection. None of those 960 IDs has a retained
parsed body locally. No Death Context player estimates, residuals, controls,
or stability statistics were generated.

The exact local deficit is 32 profiles with at least 30 usable details and 960
panel detail bodies. Do not fetch or substitute another branch. The next
status is `NEED_LIVE_SUPPLEMENT`.

## Local data reuse

| Measure | Result |
| --- | ---: |
| Reusable OpenDota campaign(s) | 1 |
| Parsed local detail records | 19 |
| Unique parsed match details | 19 |
| Development/tuning profiles in source summary corpus | 1,609 |
| Source `version == "22"` tuning rows | 56,219 |
| Deterministically selected profiles | 32 |
| Selected unique panel match IDs | 960 |
| Selected panel details reused | 0 |
| Profiles with ≥10/20/25/30/40/50 local details | 0 / 0 / 0 / 0 / 0 / 0 |
| Full 32×30 local panel | NO |

The Session Drift source is development/tuning lineage. The 1,287 validation
candidate profiles, including the 339 target eligible profiles, were excluded;
old holdout output was not loaded. The tracked OpenDota specimen files were
shape-only/history-only sources with no legitimate panel lineage and were not
used.

Panel selection used only the frozen marker, profile/match HMAC rank, support,
and global match-ID uniqueness. It did not use deaths, fight shares, wins,
heroes, roles, effect sizes, or stability.

## Tier-2 field completeness

On the 19 available parsed details, all audited core fields were present at
100% of their applicable detail, player-match, teamfight, or teamfight-player
denominator. This is shape completeness for a small retained subset, not
longitudinal panel completeness.

The available records contain 190 player rows, 147 teamfight windows, and
1,470 teamfight participant rows. Slot arrays are ten-wide and unique in all
19 details; total deaths, hero, lane, lane role, result/side, duration, patch,
and gold-advantage structures are present. Lane/role and gold advantage remain
parser/team-state semantics with the confidence recorded in the local CSV.

Teamfight semantics are **LIKELY**, not known: all 19 records pass shape,
slot-order, nonnegative-death, ten-player-array, and `fight_deaths <= total
deaths` checks, but the provider detector has no independent ground truth in
the retained data. Ten overlapping window pairs were observed. The frozen
numerator is therefore the provider's indexed teamfight-death sum, not an
independently timestamped unique-death reconstruction.

## Death Context

The registered estimand remains:

```text
unit        = player-match
denominator = all player deaths
numerator   = provider-attributed teamfight player deaths
cluster     = whole matches
```

The local pilot did not evaluate player outcomes because the 32×30 panel was
unavailable. Residual heterogeneity, dominant direction, control retention,
median attenuation, and publication-style verdict are all **NOT EVALUATED**.
The blocked analytical artifacts explicitly record
`LOCAL_PANEL_INSUFFICIENT`.

## Stability and latency

Nested `N={10,15,20,25,30}` stability, chronological halves, controls, and
personalization checks were not run. The frozen design's N=25 minimum and N=30
recommendation remain unchanged and must be tested only after a valid panel is
available.

Existing ledger observations for the 19 parsed details were:

| n | P50 | P90 | P95 | max |
| ---: | ---: | ---: | ---: | ---: |
| 19 parsed details | 0.528625s | 0.823078s | 0.881013s | 0.972216s |
| 1,200 successful detail attempts | 0.333405s | 0.416238s | 0.449187s | 0.972216s |

No 20-detail or 30-detail batch wall time, concurrency comparison, or end-to-
end enrichment time was measured. A synchronous under-one-minute claim is
not supported.

## Reusable Tier-2 corpus

The local Tier-2 layer contains 19 normalized provider-provenanced records,
references existing immutable raw bodies, copies no raw payload, and preserves
raw/normalized digests. Its normalized-record digest is recorded in the local
`tier2_reusable_manifest.json`. It is reusable for future offline research;
it is not a completed Death Context panel.

## Cost savings and future supplement

| Measure | Result |
| --- | ---: |
| Original planned detail GETs | 960 |
| Selected panel details reused | 0 |
| New GETs made | 0 |
| Calls avoided | 0 |
| Estimated cost avoided | Rp0 / $0 |
| New provider spend | Rp0 |
| Maximum future incremental GETs | 960 |
| Estimated future supplement cost | Rp1,920 / $0.096 |

See [the live supplement prompt](../prompts/free-dna-death-context-live-supplement-luna.md).

## Integrity

```text
OpenDota calls = 0
replay parse requests = 0
STRATZ calls = 0
old holdout evaluated = 0
fresh sealed validation analytically evaluated = 0
production analytical behavior changed = NO
deployed = NO
```

No production, API, database, infrastructure, frozen artifact, threshold, or
public report contract files were changed.
