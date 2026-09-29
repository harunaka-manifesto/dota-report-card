# Achievement threshold corpus review — 2026-09-29

Reviews every frozen `match-achievements-v1` threshold against real parsed Standard matches. It supports the provisional rarity snapshot `local-standard-estimate-2`. It is evidence, not product truth or a merge authorization.

## Sample

- **1,511 unique parsed Standard matches, 11,600 eligible player-rows** (2025-08 to 2026-09-29), evaluated by the real `evaluate_match` with no database.
- Sources: the authorized local research corpus (1,037 matches: the 960-match holdout plus later research pulls) and **1,026 recently parsed matches** fetched on 2026-09-29 through OpenDota `parsedMatches` and `matches/{id}`. After de-duplication and mode filtering they added 474 Standard matches. Raw responses stay in a scratch directory and are not committed.
- This is a *selected* sample. Parsed matches are ones somebody requested a parse for, which is close to the tracker's own audience but not the whole population. Rows within a match are correlated, so the intervals below are slightly optimistic.
- **Field coverage.** `networth_t` and `deaths_log` appear in OpenDota parses only for matches started after roughly 2026-09-10. Older corpus matches carry neither, and the live API does not return them either (checked with one call). They are therefore unevaluable for #6, #8, #10, #11 and #41, and partly for #18. The denominators for those badges come only from recent matches, which is also what production will see for new matches.

## Result

Rates use the evaluable-only denominator. Intervals are 95% Wilson. "stable" means the whole interval sits in one rarity band.

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
- **Tier boundaries.** #6, #11, #14, #23 and #45 straddle a band edge. Their displayed tier is only as good as this sample and stays provisional. #1, #2, #4 and #30 have no static rate because they depend on history.
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
- No threshold value was changed. Which of the fragile thresholds to keep is a product choice (target tier per badge) for the owner; the corpus cannot settle it.

## Provider calls (owner authorized up to Rp10,000)

- **1,352 OpenDota calls:** 651 unauthenticated free-tier calls (including 1 probe) and 701 calls with the project key (`parsedMatches` pages plus `matches/{id}`).
- Billed cost at 0.0001 USD per keyed call is about 0.07 USD, roughly Rp1,150 at an assumed Rp16,500/USD. No parse requests were made. Runtime achievement evaluation still adds zero provider calls.

## Still open

Owner review of the fragile thresholds and of the five band-straddling tiers, and a production-based rarity snapshot once retained active analyses exist.
