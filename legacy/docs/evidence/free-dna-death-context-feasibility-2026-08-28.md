# Free DNA Death Context Feasibility

## Status

**PARTIAL — one coherent estimand survives, but OpenDota's teamfight detector and target-panel completeness still require the bounded Tier-2 pilot.**

Recommendation: test one question only: **Of your deaths, how unusually often do they occur inside OpenDota-detected teamfights?** Treat the result as death-context composition, not death risk, KDA, aggression, skill, positioning quality, or causality. Do not add ahead-state, pre-objective, phase, or isolation branches to inflate yield.

## Preflight and firewall

```text
TASK TYPE: ANALYTICAL + DOCUMENTATION, offline feasibility research
ALLOWED SCOPE: immutable local OpenDota tuning corpus, captured match details, request ledgers, repository code/evidence, aggregate local diagnostics
FORBIDDEN SCOPE: providers, replay parse requests, STRATZ, Steam, old holdout, fresh sealed-validation analytics, production behavior, thresholds/artifacts, deployment
STOP CONDITIONS: branch collision; corpus/provenance failure; provider or replay requirement; unresolved primary denominator; sealed data requirement; production change; raw identifiers in tracked output
RESEARCH BASE: 48f05ea67d27d2a316490294448dcb78b099bb20
LATEST MAIN OBSERVED: 6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95
PRIMARY WORKTREE: dirty with unrelated owner files; untouched
TEMP WORKTREE: isolated /tmp/dota-death-context.* worktree
CORPUS: .local/corpora/opendota/v61-session-drift-expansion/ — PRESENT
PRIOR DIAGNOSTICS: .local/diagnostics/free-dna-opendota-parsed-feasibility/ — PRESENT
```

The prior audit's corpus integrity results were reused: 1,609 eligible development/tuning profiles, 556,676 eligible 365-day matches, and 56,219 matches marked `source_version == "22"`. No fresh validation or old holdout output was opened.

## Main recommendation

Advance a single **Fight-Window Death Composition** pilot. For player `p`, let `D_pm` be all deaths in match `m` and `F_pm` be deaths attributed to that player in `teamfights[].players[].deaths`. The descriptive player share is:

```text
S_p = sum_m F_pm / sum_m D_pm
```

The personal estimand is not `S_p` alone. It is the residual:

```text
theta_p = observed fight-window death share
          - expected share under a leave-player-and-match-out matched baseline
```

The primary matched baseline uses role, outcome, player-team ahead-exposure quintile, and patch. Exact-hero control is a required sensitivity. This conditions on the player's deaths and therefore does not reward or punish the number of deaths. It asks where deaths occur, not whether the player dies often.

This remains `PARTIAL` because the 19 captured parsed details prove field shape, not longitudinal completeness or the semantic reliability of the provider's heuristic fight windows. The first four calls of the proposed panel are the live semantic QA gate; no separate call budget is needed.

## Candidate branches

### A. Fight versus non-fight deaths — retain

- **Question:** Of the player's deaths, what share occurs inside OpenDota-detected teamfight windows, and is that share unusual for matched players?
- **Estimand:** observed minus matched expected fight-window death share.
- **Unit:** player-match; aggregate and resample whole matches.
- **Denominator:** all player deaths in selected matches. Minimum pilot support: 25 matches and 100 total deaths. These are pilot sufficiency rules, not production qualification thresholds.
- **Repeated observations:** matches, not deaths.
- **Required fields:** player slot/order, total deaths, teamfight player deaths, hero, lane role, result, advantage timeline, duration, and patch.
- **Confounders:** provider fight detection, hero, role, outcome, game tempo/state, and patch.
- **Null:** the player's fight-death composition equals the matched development-population composition.
- **Null/baseline model:** death-weighted, leave-player-and-match-out post-stratification; match-clustered resampling.
- **Generic-law risk:** high without residualization. Stop if at least 90% of supported profiles share one residual direction.
- **Verdict:** `SURVIVES_AS_SINGLE_PRIMARY_ESTIMAND`.

### B. Ahead-state death exposure — reject as primary

- **Question:** Are deaths unusually concentrated while the player's team is ahead?
- **Estimand:** observed versus exposure- and context-adjusted share of deaths in ahead-state minutes.
- **Denominator:** all deaths plus time spent ahead.
- **Required fields:** exact death timestamps, player side, and the gold-advantage series.
- **Main problem:** detail has killer-side `kills_log`, not a direct per-player death log. Summed kill logs matched total deaths in only 5 of 19 captured parsed details. Inverting logs would silently omit some deaths.
- **Generic-law risk:** very high because death while ahead is an outcome/game-state relationship shared across Dota.
- **Verdict:** `REJECT_PRIMARY`; exact semantics would need live QA and the branch is weaker than A even if reconstructed.

### C. Pre-objective deaths — reject

- **Question:** Are deaths concentrated in a fixed setup window before contestable objectives?
- **Estimand:** death incidence per eligible, non-overlapping pre-objective window.
- **Denominator:** eligible objective windows, not raw objective or death count.
- **Required fields:** exact death timestamps, a frozen objective taxonomy, objective timing, side, and state.
- **Main problem:** the later objective can be enabled by the death, making a retrospective “setup death” label ambiguous. Exact death timing is also indirect.
- **Generic-law risk:** high; both teams commonly lose objectives after deaths.
- **Verdict:** `REJECT_PRIMARY`.

### D. Game-phase death context — exclude from family

- **Question:** Are deaths concentrated in early, mid, or late game?
- **Estimand:** phase-specific death share relative to phase duration and matched context.
- **Denominator:** observed minutes per predeclared phase.
- **Required fields:** exact death timestamps, duration, hero, role, outcome, and patch.
- **Main problem:** phase boundaries are arbitrary and duration conditioning is strong. The likely result is a hero/role/power-curve law.
- **Verdict:** `REJECT_FROM_FAMILY`; potentially descriptive later, but not a second Death Context hypothesis.

### E. Isolation / teammate proximity — reject

- **Question:** Does the player die away from teammates?
- **Denominator:** deaths with time-aligned position observations for the player and teammates.
- **Required fields:** time-resolved positions and exact death timestamps.
- **Main problem:** `lane_pos` is an early-game spatial histogram, not a position timeline. Teamfight `deaths_pos` does not provide teammate locations at the death time.
- **Verdict:** `REJECT`; requires replay/raw movement work and belongs outside Free.

## Tier-2 field feasibility

| field | captured already-parsed detail | replay parse | semantics | caveat | safe |
|---|---|---:|---|---|---|
| death timestamps | indirect through opponents' `kills_log` | no | low | no direct death log; 5/19 match-level count reconciliation | no for primary |
| player identity/slot | `players[].player_slot`, `hero_id` | no | high | present on 190/190 player rows | yes |
| teamfight windows/deaths | `teamfights[start,end,players[].deaths]` | no | medium | heuristic; all 19 details had ten-player arrays | needs QA |
| gold advantage | `radiant_gold_adv` | no | medium | minute team series, not player attribution | needs QA |
| objective timing | `objectives[].time/type` | no | medium | heterogeneous event taxonomy | needs QA |
| kill chronology | `players[].kills_log` | no | medium | killer perspective and incomplete death reconstruction | needs QA only |
| position timeline | only `lane_pos` histogram | yes for full route | high absence confidence | no time-aligned proximity | no |
| hero | `players[].hero_id` | no | high | complete in captured rows | yes |
| lane/role | `lane`, `lane_role` | no | medium | parser heuristic, not position contract | needs QA |
| win/loss | `radiant_win` + slot | no | high | derivable | yes |
| duration | `duration` | no | high | match seconds | yes |
| patch | `patch` | no | high | complete in captured details | yes |

The retained estimand deliberately does not depend on exact death timestamps or position data.

## Opportunity denominator

The primary denominator is **all of the player's deaths** across whole matches. This is a conditional composition question:

```text
numerator   = deaths inside detected teamfight windows
denominator = all deaths
```

This is defensible because the user question is “what kinds of situations lead to your deaths?” It removes raw death propensity from the estimand. It does **not** estimate `P(death | teamfight)`, because stock detail lacks exact alive-time exposure inside each window. Teamfight duration was rejected as the primary denominator for that reason.

Inference treats each match as the independent unit. Deaths remain clustered inside matches for bootstrap, split-half, and repeated-subsample work.

## Personalization and generic-law guard

The pilot must compute the player's observed share and a cross-fitted expected share:

1. Exclude the target profile and target match from its reference rows.
2. Primary post-strata: lane role × outcome × player-team ahead-exposure quintile × patch, requiring at least 100 reference deaths per usable stratum.
3. Exact-hero sensitivity: hero × outcome × patch; fall back to hero × outcome only when the first cell has fewer than 100 reference deaths. This fallback is support-based and frozen before outcomes.
4. Report unadjusted, primary-adjusted, and hero-sensitive residuals separately.
5. Resample whole matches, never individual deaths.
6. Repeat at nested `N={10,15,20,25,30}` and by chronological half.

The branch fails personalization if the dominant residual sign covers at least 90% of supported profiles. It also fails if the controls erase the distribution: fewer than 70% of profiles retain direction or median absolute attenuation is at least 50%.

This directly addresses the prior Presence & Exposure failure, where 98.1% of supported profiles shared one direction after gates.

## One coherent family

The family remains:

> Death Context — What kind of situations repeatedly lead to your deaths?

It has one registered candidate, Fight-Window Death Composition. The other branches are neither labels nor fallback winners. They are discarded. This avoids correlated selection across four mini-findings and keeps one estimand, one baseline, one stability decision, and one eventual family p-value if research later advances to qualification.

No production family universe or multiplicity rule changes in this task.

## Is 20–30 parsed matches plausible?

Existing eligible parsed summary rows provide the death totals below. Each `N` uses the most recent `N` parsed matches among profiles with at least `N`, so cohorts differ by row. Provisional fight opportunities extrapolate from only 19 captured seed details (mean 7.74 detected fights/match); they are shape guidance, not population estimates.

| N | profiles | mean deaths | median deaths | P10–P90 deaths | provisional fight windows | independent match units | assessment |
|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 839 | 81.5 | 81 | 56–108 | 77 | 10 | likely too sparse |
| 15 | 658 | 120.8 | 119 | 85–158 | 116 | 15 | likely too sparse |
| 20 | 536 | 159.6 | 156.5 | 116.5–210 | 155 | 20 | plausible exploratory |
| 25 | 450 | 197.8 | 194 | 144.9–258 | 193 | 25 | minimum pilot support |
| 30 | 391 | 232.7 | 232 | 166–303 | 232 | 30 | recommended pilot support |
| 40 | 294 | 306.6 | 305 | 231.3–393.4 | 309 | 40 | comfortable, low coverage |
| 50 | 237 | 377.5 | 377 | 279–477 | 387 | 50 | comfortable, lower coverage |

Event count is unlikely to be the limiting factor by 20 matches. The bottleneck is the number of independent matches and whether a personal residual survives controls and resampling.

- `MINIMUM PILOT N PER PLAYER = 25`
- `RECOMMENDED PILOT N PER PLAYER = 30`

The panel fetches 30 so it can evaluate all nested prefixes without another call campaign.

## Coverage implication

At 30 parsed matches, 391 of 1,609 development profiles qualify on data availability: **24.30%**. At the minimum 25, 450 profiles qualify: **27.97%**.

This is only the upper bound at the first stage:

```text
data available -> support eligible -> stable signal -> statistically qualified -> published
```

It is not a publication forecast, and the pilot's 32 profiles are not a new calibration population.

## Tier-2 pilot

- Development profiles: **32**.
- Parsed-match minimum: **30**.
- Matches/profile: **30**, nested prefixes `10, 15, 20, 25, 30`.
- Sampling: new private 32-byte salt; HMAC-SHA256 profile rank, then match rank; choose ascending digests before detail inspection.
- Duplicate handling: greedily require 30 globally unique match IDs per profile; skip only structural duplicate/support failures before detail inspection.
- Total match-detail GETs: **960**.
- Maximum physical calls: **960**, zero retries and no replacements based on payload or outcome.
- Replay parse requests: **0**.
- Cost: **Rp1,920 and $0.096 pro rata**, calculated independently.
- Storage ceiling: **384 MiB**. The 19 captured parsed payloads averaged 211,717 bytes and had P95 264,111 bytes; 960 P95-sized bodies are about 242 MiB before manifests/derived outputs.
- Owner approval: required before the first GET.

The first four selected detail GETs are sequential minimal QA. Any marker, shape, transport, or parse-policy failure stops the other 956 calls.

## Latency

The existing local ledger contains sequential request durations:

| request class | N | P50 | P90 | P95 | max |
|---|---:|---:|---:|---:|---:|
| tuning history | 2,848 | 0.807s | 1.343s | 1.542s | 2.859s |
| all seed match details | 1,200 | 0.333s | 0.416s | 0.449s | 0.972s |
| parsed detail subset | 19 | 0.529s | 0.823s | 0.881s | 0.972s |

These observations do not measure concurrent 20/30-detail batches, payload decode/analysis, or total enrichment time. We therefore cannot promise less than one minute.

The pilot must measure request P50/P90/P95/max, bytes/download time, 429/error rate, local calculation time, and end-to-end time at bounded concurrency 1, 5, and 10 with a 240 requests/minute start-rate ceiling. Record wall time for 20- and 30-GET prefixes.

Decision bands:

- ≤5 seconds: excellent synchronous;
- >5–15 seconds: acceptable synchronous;
- >15–30 seconds: borderline;
- >30–60 seconds: prefer progressive/background;
- >60 seconds: unacceptable as blocking Free generation.

For this pilot, a 30-GET total enrichment time above 30 seconds routes the concept to background. Above 60 seconds blocks it from synchronous Free.

## Cost model

Owner assumption: Rp200/100 physical calls and $0.01/100 calls, applied independently.

| scenario | calls | IDR | USD |
|---|---:|---:|---:|
| 1 history + 10 details | 11 | Rp22 | $0.0011 |
| 1 history + 15 details | 16 | Rp32 | $0.0016 |
| 1 history + 20 details | 21 | Rp42 | $0.0021 |
| 1 history + 25 details | 26 | Rp52 | $0.0026 |
| 1 history + 30 details | 31 | Rp62 | $0.0031 |
| 1 history + 40 details | 41 | Rp82 | $0.0041 |
| 1 history + 50 details | 51 | Rp102 | $0.0051 |

The exact pilot uses stored histories and makes 960 detail GETs: Rp1,920 and $0.096 pro rata. The hard owner ceiling is exactly 960 physical calls at those costs; failure stops rather than expanding the budget.

## Pilot success criteria

Continue Death Context only if all conditions pass:

- at least 95% completeness for slot mapping, deaths, teamfight arrays, hero, role, outcome, patch, and advantage timeline;
- every selected detail agrees with the stored parsed marker and no parse endpoint/client is used;
- 30-GET total enrichment is no more than 30 seconds for synchronous consideration; more than 30 seconds means background, more than 60 blocks Free;
- adjusted residual IQR is at least 0.10 and no residual sign covers 90% or more of supported profiles;
- at least 70% direction agreement after controls and hero sensitivity, with median absolute attenuation below 50%;
- at N=25 or N=30, split-half Spearman is at least 0.50 and repeated nested-subsample sign agreement is at least 0.75 among profiles with absolute full residual at least 0.05; and
- the user interpretation remains death-context composition, never aggression, KDA, skill, intent, causal positioning advice, or good/bad deaths.

If a core field fails, controls erase the residual, the common-direction stop triggers, or N=30 remains unstable, drop Death Context. Do not redesign indefinitely or add a weaker branch.

## Reproducibility

- Runner: `scripts/free_dna_death_context_feasibility.py`
- Local diagnostics: `.local/diagnostics/free-dna-death-context-feasibility/`
- Machine-readable outputs: all 14 required files are present.
- Luna execution prompt: `docs/prompts/free-dna-death-context-tier2-pilot-luna.md`

## Integrity

```text
OPENDOTA CALLS = 0
REPLAY PARSE REQUESTS = 0
STRATZ CALLS = 0
OLD HOLDOUT EVALUATED = 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED = 0
PRODUCTION ANALYTICAL BEHAVIOR CHANGED = NO
DEPLOYED = NO
```
