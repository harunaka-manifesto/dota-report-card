# Offlane detected-fight feasibility sample — 2026-09-27

**Decision: ship Graph B from retained OpenDota replay evidence.** The
predeclared gate required at least 100 supported, replay-ready matches and at
least 90% with valid fight arrays and per-player fields. The initial capped
sample had 99 qualifying matches and 93 valid arrays. An owner-authorized
continuation added two distinct qualifying Standard matches with valid arrays:
**95/101 (94.1%)** passed the gate. This does not authorize historical OpenDota
fetching; matches without stored fight evidence remain unavailable.

## Owner-authorized continuation

- Seven successful, unauthenticated HTTP reads: one current parsed-match listing,
  two older parsed-match listings, two initial match reads and two verification
  reads of those same matches. A sandbox-blocked local
  attempt never reached OpenDota. No API key or parse request was used. Direct
  provider billing was **Rp0**, below the Rp8,000 ceiling.
- To avoid repeating the initial study's three most recent listing pages, the
  continuation used listing cursors one million and ten million match IDs below
  the current head. Matches `9016991624` and `9007991606` were both ranked All
  Pick with positive replay versions. They contained respectively six and nine
  fight segments, all with valid in-match windows and ten player records carrying
  the required damage, deaths and killed fields. Both had ten human players,
  passed the tracker summary and replay validators, and returned `AVAILABLE`
  from the production fight validator. Their initial read latencies were 1.175
  and 1.613 seconds; these are two samples, not an availability SLA.
- Their full responses were saved only in the newly created ignored `.local/`
  continuation directories. The existing private corpus was not inspected.

Combined coverage is **101 qualifying matches: 74 Standard, 27 Turbo**, with
fight counts ranging from 0 to 20, median 10, and 990 detected segments. The
six invalid arrays remain the five pregame-window and one post-duration-window
cases in the initial sample. The detailed overlap, header disagreement and
zero-damage counts below apply to that initial 99-match audit; the two added
matches were checked for the predeclared gate fields and valid windows.

## Initial capped sample: method and budget

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

## Initial capped sample: coverage and edge cases

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

No end-to-end availability distribution was captured. For fresh matches, using
an already stored OpenDota response adds no Match Detail read call; availability
still follows replay finalization. This study does not authorize a historical
OpenDota production path.
