# Achievement threshold corpus review — 2026-09-29

Reviews every frozen `match-achievements-v1` threshold against real parsed Standard matches. It supports the frozen tiers `badge-tiers-v1` (originally the snapshot `local-standard-estimate-2`). It is evidence, not product truth or a merge authorization.

## Sample

- **1,511 unique parsed Standard matches, 11,600 eligible player-rows** (2025-08 to 2026-09-29), evaluated by the real `evaluate_match` with no database.
- Sources: the authorized local research corpus (1,037 matches: the 960-match holdout plus later research pulls) and **1,026 recently parsed matches** fetched on 2026-09-29 through OpenDota `parsedMatches` and `matches/{id}`. After de-duplication and mode filtering they added 474 Standard matches. Raw responses stay in a scratch directory and are not committed.
- This is a *selected* sample. Parsed matches are ones somebody requested a parse for, which is close to the tracker's own audience but not the whole population. Rows within a match are correlated, so the intervals below are slightly optimistic.
- **Field coverage.** `networth_t` and `deaths_log` appear in OpenDota parses only for matches started after roughly 2026-09-10. Older corpus matches carry neither, and the live API does not return them either (checked with one call). They are therefore unevaluable for #6, #8, #10, #11 and #41, and partly for #18. The denominators for those badges come only from recent matches, which is also what production will see for new matches.

## Result at the starting thresholds

(#6, #11, #23, #42 and #45 were later changed; see the tier freeze below.) Rates use the evaluable-only denominator. Intervals are 95% Wilson. "stable" means the whole interval sits in one rarity band.

| Badge | Hits / evaluable | Rate | 95% interval | Tier | Interval vs band edges |
|---|---|---|---|---|---|
| #6 Two Clocks Ahead | 33 / 830 | 3.98% | 2.84%–5.53% | Epic | Epic–Rare |
| #8 20-Minute Turnaround | 46 / 1,660 | 2.77% | 2.08%–3.68% | Epic | stable |
| #10 Gold Engine | 79 / 2,490 | 3.17% | 2.55%–3.94% | Epic | stable |
| #11 Mid Advantage, Real Siege | 51 / 834 | 6.12% | 4.68%–7.95% | Rare | Epic–Rare |
| #13 Relentless Presence | 202 / 11,200 | 1.80% | 1.57%–2.07% | Epic | stable |
| #14 Untouchable Contributor | 97 / 11,600 | 0.84% | 0.69%–1.02% | Legendary | Legendary–Epic |
| #15 Flawless Finisher | 67 / 11,600 | 0.58% | 0.46%–0.73% | Legendary | stable |
| #17 Five in a Flash | 225 / 11,398 | 1.97% | 1.73%–2.25% | Epic | stable |
| #18 Early Duelist | 432 / 4,069 | 10.62% | 9.71%–11.60% | Rare | stable |
| #20 Fight Closer | 1,121 / 6,960 | 16.11% | 15.26%–16.99% | Rare | stable |
| #22 Damage Anchor | 1,045 / 6,960 | 15.01% | 14.19%–15.87% | Rare | stable |
| #23 Clean Teamfight | 359 / 6,960 | 5.16% | 4.66%–5.70% | Rare | Epic–Rare |
| #25 Behind but Fighting | 215 / 5,034 | 4.27% | 3.75%–4.87% | Epic | stable |
| #37 Vision Double Duty | 301 / 4,639 | 6.49% | 5.82%–7.23% | Rare | stable |
| #41 Camp Architect | 74 / 1,876 | 3.94% | 3.15%–4.92% | Epic | stable |
| #42 Support Everywhere | 720 / 4,480 | 16.07% | 15.03%–17.18% | Rare | stable |
| #44 Offlane Siege | 226 / 2,282 | 9.90% | 8.74%–11.20% | Rare | stable |
| #45 Siege without Dying | 50 / 4,564 | 1.10% | 0.83%–1.44% | Epic | Legendary–Epic |
| #49 Healing Hand | 383 / 4,640 | 8.25% | 7.50%–9.08% | Rare | stable |
| #50 Control Specialist | 313 / 4,634 | 6.75% | 6.07%–7.51% | Rare | stable |

- Every single-match badge has at least 50 hits, none is dead, and none is Common. Awarded proofs were spot-checked (for example #6 with 90 last hits at 10:00 and 12,098 net worth at 20:00; #45 with 11,430 tower damage, a 48% team share and 0 deaths).
- **Tier boundaries.** #6, #11, #14, #23 and #45 straddle a band edge. Their frozen tier is only as good as this sample. #1, #2, #4 and #30 have no static rate because they depend on history.
- **Near Common.** #20 (16.1%), #22 (15.0%) and #42 (16.1%) are stably Rare but close to the 20% edge. The #30 repeat list (`REPEATABLE_FEATS`) is unchanged and still valid: no listed badge is Common.

## Sensitivity (threshold x0.75 / x1 / x1.25)

Fragile (a 25% move changes the rate several-fold and can change the tier):

- #6 net worth at 20:00: 15.5% / 4.0% / 0.2%
- #10 gain 10 to 20 minutes: 10.6% / 3.2% / 0.3%
- #22 damage share: 35.0% / 15.0% / 4.0%
- #23 enemy deaths: 29.3% / 5.2% / 0.4%
- #37 observer kills: 22.9% / 6.5% / 3.1%
- #42 involvement: 25.4% / 16.1% / 4.4%
- #13 involvement: 3.5% / 1.8% / 0.5%
- #25 damage share: 9.2% / 4.3% / 1.5%
- #41 stacks: 10.8% / 3.9% / 2.7%
- #50 disable seconds: 14.0% / 6.8% / 3.6%
- #20 personal kills: lowering 3 to 2 gives 49.1%

Robust: #8 (the 10-minute deficit condition binds, not the 20-minute one), #6's last-hit floor, #11 tower damage, the #14 and #15 minimums, #25 damage floor, #37 observers placed, and the #44, #45 and #49 secondary conditions.

## Change made because of the review

- **#18 Early Duelist evidence gap.** It required every death to have `time_dead`. Recent parses omit that on about 5% of late deaths (733 of 14,871 death entries in the sampled paid matches), so 35% of recent rows lost the badge. #18 needs only death *start* times. The retained source now carries `achievement_source.death_times`: all `time` values, withheld if the log length disagrees with the summary death count. Recent-row coverage rose from 65% to essentially all, and the rate is 10.6% (432 / 4,069). Unit tests cover complete, contradicting and missing logs.
- Threshold values were then adjusted for the tier freeze below (owner: tiers must never move after real users earn badges, no preferred tier per badge, and ideally every tier holds at least one badge).

## Tier freeze (owner decision, 2026-09-29) — `badge-tiers-v1`

Tiers are static data in `achievement_rules.py` (`BADGE_TIERS`, part of the pinned digest), never re-derived from live data. To put each badge firmly inside one band, five thresholds moved to round values, with the corpus rate (95% interval) each produces:

| Threshold change | Was | Now | Rate at the new value |
|---|---|---|---|
| #6 net worth at 20:00 | 12,000 | 12,500 | 3.13% (2.15–4.55%) Epic |
| #11 early lead at 10:00 | 1,000 | 1,500 | 3.72% (2.63–5.23%) Epic |
| #23 player damage in the fight | 2,000 | 1,500 | 6.03% (5.50–6.62%) Rare |
| #45 share of team tower damage | 40% | 50% | 0.72% (0.52–1.01%) Legendary |
| #42 kill involvement | 60% | 50% | 23.4% (22.2–24.7%) **Common** |

- **Common.** No badge could be Common at its starting thresholds (the closest were #20, #22 and #42 at 15–16%). Lowering #42 to 50% involvement (the same level #41 already uses) puts it well above 20%, so Support Everywhere is the one Common badge. Because #30 repeats only non-Common feats, #42 left `REPEATABLE_FEATS`. #20's floor is a stated count (3 kills), so it stays Rare.
- **#14 Untouchable Contributor** keeps its 10-assist rule (its copy says double-digit): 0.84% (0.69–1.02%), Legendary, its interval touches the 1% edge by 0.02 points. Accepted.
- **History badges (#1, #2, #4, #30)** cannot be measured from single matches, and the corpus has too few same-account histories (60 accounts with 6+ matches). They were simulated: for each role, real per-match metric values and earned badges drawn from the recent corpus (net worth, damage and tower share, last hits, camps stacked, fight presence and observer wards; three measurable metrics per role from OpenDota data alone), users with 24, 60 or 120 matches, a 60% main role, and 3, 6 or 12 heroes with Zipf weights. Strict personal best after five priors, exactly as `build_analysis` does.

| Badge | Simulated rate per match | Frozen tier |
|---|---|---|
| #1 Double Record | 2.5–2.9% across all 9 settings | Epic |
| #2 Clean Sweep | 0.34–0.52% | Legendary |
| #4 Record on a New Hero | 2.2–4.9% | Epic |
| #30 Hero Specialist | 1.1% (24 matches, 12 heroes) to 17.5% (120 matches, 3 heroes); 6.5% at 60 matches and 6 heroes | Rare |

  #30 grows with history length and hero concentration, so no single figure fits every user. Rare was chosen for the middle case and because Pro users keep long histories. With full four-metric histories (STRATZ-sourced) #1 and #2 run somewhat higher; #2 is the badge nearest a band edge.

### Final tiers (24)

- **Common (1):** #42.
- **Rare (9):** #18, #20, #22, #23, #30, #37, #44, #49, #50.
- **Epic (10):** #1, #4, #6, #8, #10, #11, #13, #17, #25, #41.
- **Legendary (4):** #2, #14, #15, #45.

Every measured badge's frozen tier equals the band of its corpus rate (checked by test), and the corpus rates above were re-verified by running the real evaluator with the final thresholds.

## Provider calls (owner authorized up to Rp10,000)

- **1,352 OpenDota calls:** 651 unauthenticated free-tier calls (including 1 probe) and 701 calls with the project key (`parsedMatches` pages plus `matches/{id}`).
- Billed cost at 0.0001 USD per keyed call is about 0.07 USD, roughly Rp1,150 at an assumed Rp16,500/USD. No parse requests were made. Runtime achievement evaluation still adds zero provider calls.

## Still open

Owner review of the fragile thresholds and of the five band-straddling tiers, and a production-based rarity snapshot once retained active analyses exist.

## Re-measurement after the independent QA fixes

Independent QA found that #25 rejected any gold-advantage curve not starting at 0, but 272 of 1,027 recently fetched parses start at a real nonzero 0:00 reading (the starting team gold difference). Re-running the real evaluator on the same 1,511 matches with the corrected rules (nonzero origin accepted, exact kill-log match, real zero team kills or tower damage counted as evidence) gives: #25 279 / 6,960 (4.01%, still Epic), #11 31 / 848, #13 202 / 11,600, #17 211 / 10,846, #18 422 / 3,914, #41 74 / 1,916, #42 1,049 / 4,640, #44 226 / 2,320, #45 33 / 4,640. No frozen tier changed. `RATE_COUNTS` holds these counts and a test keeps each in its frozen band.
