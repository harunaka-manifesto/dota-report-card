# Free DNA Death Context Research Design

## Decision

Research one candidate only:

> Of your deaths, how unusually often do they occur inside OpenDota-detected teamfights?

This is a conditional death-context composition. It is not raw death rate, KDA, fight participation, aggression, positioning quality, skill, intent, or causality.

Status is **PARTIAL** until the bounded Tier-2 pilot verifies teamfight semantics, longitudinal completeness, heterogeneity, control survival, stability, and latency. The 2026-08-29 live supplement is collection-blocked and did not produce a pilot estimate.

## Overnight supplement outcome — 2026-08-29

The frozen 32-profile × 30-match panel reproduced with 960 globally unique
match IDs before any detail inspection. The owner-authorized supplement then
made 60 direct OpenDota detail GETs: 59 returned valid parsed details and one
returned HTTP 500. Zero retries, replay parses, replacements, adaptive top-up,
validation use, holdout use, or non-OpenDota calls occurred.

The terminal state is `PILOT_COLLECTION_BLOCKED`. The full panel was not
available, so the registered player-match outcome analysis, residuals,
controls, common-direction guard, bootstrap intervals, and N=10/15/20/25/30
stability were not evaluated. Shape QA on the 59 successful details remains
available as structural evidence only; it cannot satisfy the full-panel gates.

The successful responses were preserved in the canonical ignored Tier-2
corpus. No calibration design was opened, and the production report remains
unchanged. A future provider attempt requires separate authorization and a
new campaign; this campaign is not silently retried.

## Registered estimand

For player `p` and selected match `m`:

- `D_pm`: total deaths from the target player row;
- `F_pm`: sum of `teamfights[].players[target_index].deaths`;
- `X_pm`: hero, lane role, outcome, player-team ahead-exposure, patch, and match metadata.

The observed share is `sum(F_pm) / sum(D_pm)`. The research estimand is:

```text
theta_p = observed fight-window death share
          - expected fight-window death share given X_pm
```

The expected share is estimated from development-panel player rows after excluding the target profile and target match. Player-to-detail mapping uses `player_slot`; array-position agreement is a first-four-call QA gate.

The claim is deliberately conditional on death. Stock parsed detail does not expose exact alive-time within fight windows, so this design does not estimate the rate of death per fight minute.

## Support and dependency

- Minimum research support: 25 selected matches and 100 total deaths.
- Recommended pilot support: 30 matches.
- Independent unit: match.
- Cluster rule: all player/death/fight rows from one match stay together.
- Resampling: whole-match bootstrap only.
- Stability prefixes: nested HMAC-ranked `N={10,15,20,25,30}`.
- Chronological sensitivity: first 15 versus last 15 at N=30.

These are pilot rules, not production thresholds or qualification gates.

## Population baseline and controls

Primary expected shares use death-weighted post-strata:

```text
lane_role × outcome × player-team-ahead-exposure quintile × patch
```

Each usable reference stratum needs at least 100 deaths after leaving the target profile and match out. Unsupported rows abstain; there is no outcome-driven replacement.

Required sensitivities:

1. unadjusted development-population share;
2. the primary role/outcome/state/patch baseline;
3. exact hero × outcome × patch, falling back to hero × outcome only when the first cell has fewer than 100 reference deaths;
4. dominant-hero exclusion;
5. win-only and loss-only estimates where support remains; and
6. whole-match bootstrap intervals and nested-prefix stability.

Ahead exposure is the fraction of observed `radiant_gold_adv` minutes where the target player's team is ahead. Quintile boundaries are computed once from the complete development panel without using death-context outcomes.

## Personalization gates

This is not a personal Finding unless the controlled residual differs across players.

Stop if any condition holds:

- at least 90% of supported profiles share one residual sign;
- adjusted residual IQR is below 0.10;
- control/hero sensitivity retains direction for fewer than 70% of profiles;
- median absolute attenuation after controls is at least 50%; or
- N=30 fails the registered stability criteria.

The common-direction stop is a direct guard against the prior Presence & Exposure failure mode.

## Rejected branches

- **Ahead-state death exposure:** needs indirect death-log reconstruction and is highly vulnerable to a generic lead/outcome law.
- **Pre-objective deaths:** indirect death timing plus retrospective objective anchoring makes the setup claim ambiguous.
- **Game phase:** arbitrary boundaries and hero/role/duration confounding make it weaker and heterogeneous.
- **Isolation/proximity:** no time-aligned teammate position timeline exists in stock parsed detail.

They do not become fallback branches if the primary fails.

## Deterministic panel

- 32 development profiles.
- At least 30 `source_version == "22"` summary matches per selected profile.
- 30 globally unique match IDs per profile; 960 detail GETs total.
- New private 32-byte salt.
- HMAC-SHA256 profile rank, then HMAC-SHA256 match rank, ascending digest.
- Perform selection before opening any new detail payload.
- Greedily skip a profile only when it cannot contribute 30 globally unique parsed IDs after earlier selections.
- No replacement based on response contents, candidate outcome, latency, error, or signal.
- No fresh validation, old holdout, STRATZ, Steam, unparsed matches, or replay parsing.

The first four selected GETs are the semantic QA. Failure stops the panel with four or fewer calls.

## Latency and product routing

Record physical-call latency, bytes/download time, decode time, local analysis time, errors/429s, and end-to-end enrichment. Exercise bounded concurrency 1, 5, and 10 under a 240 request-starts/minute ceiling. Record 20- and 30-GET wall times.

Routing bands:

- ≤5s excellent synchronous;
- >5–15s acceptable synchronous;
- >15–30s borderline;
- >30–60s background/progressive;
- >60s unacceptable as blocking Free generation.

Even if the panel passes analytically, the current Free report must remain unchanged until a separately authorized analytical release and product architecture decision.

## Fixed budget

- 960 physical OpenDota detail GETs maximum.
- Rp1,920 and $0.096 pro rata under the owner-supplied rates.
- 384 MiB local corpus ceiling.
- zero retries;
- zero replay parse requests;
- zero provider calls before explicit owner approval.

## Success and stop

Continue only if:

- core fields are at least 95% complete;
- all details agree with stored parsed state;
- no parse workflow occurs;
- residual IQR is at least 0.10 and the common-direction stop does not trigger;
- controls preserve direction for at least 70% with median attenuation below 50%; and
- at N=25 or 30, split-half Spearman is at least 0.50 and nested-subsample sign agreement is at least 0.75 for nontrivial residuals.

Drop the candidate when a condition fails. Do not weaken gates, expand calls, add profiles, substitute a rejected branch, or inspect validation to rescue it.

## Output boundary

The pilot produces local private raw responses, ledgers, normalized event rows, aggregate completeness/latency/control/stability diagnostics, and a tracked aggregate evidence report without raw account, profile, or match identifiers.

It does not change production code, V6.1 methodology, artifacts, thresholds, public report contracts, database state, infrastructure, or deployment.
