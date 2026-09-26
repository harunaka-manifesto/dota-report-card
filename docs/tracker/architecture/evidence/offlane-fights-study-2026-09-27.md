# Offlane detected-fight feasibility sample — 2026-09-27

**Decision: hold Graph B.** The predeclared gate required at least 100 supported,
replay-ready matches and at least 90% with valid fight arrays and per-player
fields. The capped sample yielded **99** qualifying matches. **93/99 (93.9%)**
passed the conservative segment validator, so coverage cleared 90% but the
minimum sample size missed by one. Do not publish the detected-fights API or
start historical OpenDota fetching on this evidence.

## Method and budget

- Paginated the public OpenDota `parsedMatches` listing, then read the listed
  matches. Qualified Standard ranked/unranked All Pick or Turbo with positive
  replay version. No API key was used.
- Stopped at **250 counted attempts**, including one local network failure and
  15 HTTP 429 responses. There were 231 match responses and three successful
  listing pages. The first page was mostly unsupported modes, so this is a
  convenience sample of recently parsed matches, not a representative launch
  cohort. Slower 2.5-second pacing avoided further 429s in the final 146 calls.
- Full responses were saved only in the newly created, ignored `.local/`
  directories `offlane-match-graphs-2026-09-27-network` and
  `offlane-match-graphs-2026-09-27-part3`. The one-call failed attempts have
  their own study summaries. No raw match data is committed.
- Direct provider billing for these unauthenticated requests was not observed;
  the 250-attempt limit was the binding study cap.

## Coverage and edge cases

| Measure | Observed |
|---|---:|
| Qualifying matches | 99: 72 Standard, 27 Turbo |
| Present fight arrays | 99/99 |
| Detected fight segments | 975; median 10 per match, range 0–20 |
| Valid empty arrays | 1/99 |
| Segments with ten player entries | 975/975 |
| Player entries with damage, deaths and killed fields | 9,750/9,750 for each field |
| Matches passing conservative window and player validation | 93/99 (93.9%) |
| Invalid match windows | 5 pregame negative starts; 1 end after match duration |
| Overlapping windows within valid matches | 49 overlaps |
| Fight-header death count disagreement within valid matches | 47 segments |
| Tied per-player hero-death trades within valid matches | 103 of 902 segments |
| Zero-damage player entries with other activity within valid matches | 869 |

The fight-count distribution over all 99 qualifying matches was:

| Fights | 0 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Matches | 1 | 2 | 1 | 5 | 8 | 10 | 11 | 8 | 14 | 12 | 5 | 7 | 4 | 4 | 1 | 3 | 2 | 1 |

All 99 had the required per-player fields; the six failures came from the
chosen 0-to-duration X-domain validator. A future fight design must decide
whether to show pregame fights and post-duration parser windows. It should
derive the death trade from per-player deaths because header totals sometimes
disagree. Tied death trades need an explicit even outcome. Overlap is a valid parser segmentation edge case, so windows must
not be assumed disjoint. Zero damage must mean only no recorded damage in
that segment, not that the offlaner was absent.

No per-request latency distribution was captured. For fresh matches, using an
already stored OpenDota response would add no Match Detail read call; end-to-end
availability still follows the existing replay finalization path. This study
does not authorize a historical OpenDota production path.
