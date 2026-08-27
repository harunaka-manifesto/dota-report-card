# Claude Opus 5 — STRATZ Parsed-Data Enrichment Research

## Mission

Determine what Dota Report can *truthfully* say about a player that it cannot
say today, given STRATZ's parsed match data — and reassess every existing V6.1
finding against that same data.

You produce **research and a plan**. You do not change analytical production
code, you do not deploy, and you do not modify production. Your deliverable is a
written research report plus supporting artifacts.

This is the sibling of `01-luna-max-provider-migration.md`. That document swaps
the provider while holding V6.1's meaning fixed. This one asks what a *new*
analytical generation should measure. Keep the two apart: an idea that changes
what a finding means belongs here, never in the migration.

---

## Recommended Opus 5 execution settings

Thinking enabled. Use the highest effort setting your environment exposes
(`xhigh` if available). This is a long-horizon research task with a large
schema surface and a strict evidence standard; do not optimise for speed.

Delegate at most two genuinely independent tracks (for example: schema/payload
inventory, and existing-finding reassessment). Do not spawn subagents for
routine file reads or to check your own work.

---

## Product principles

> **PHARMA BACKSTAGE. SPOTIFY WRAPPED ONSTAGE.**

Backstage: defensible analytics, explicit provenance, reproducibility,
conservative claims, proper uncertainty, appropriate controls, stable data
contracts, versioned definitions.

Onstage: personal, Dota-native, understandable, surprising, useful, shareable,
progressively disclosed.

The objective is **not** to expose every STRATZ metric. The objective is to
identify *repeated behavioural patterns that meaningfully describe how a player
plays Dota*. More fields is not more insight; it is more hypotheses, and
hypotheses cost multiplicity budget.

Read `AGENTS.md`, `docs/architecture/free-dna-v6.1-feature-graph.md`,
`docs/architecture/free-dna-v6-statistics.md`, `docs/evidence-contract.md`, and
`research/free-dna-v6.1-cheap-history-ceiling.md` before generating candidates.
The last one is the existing analysis of what one cheap history call can and
cannot support; your job is the parsed-data sequel to it.

---

## Analytical / versioning firewall

Immutable historical identities — never rewrite, never re-attribute:

- analytical source SHA `7df38e6d234ae9c4ee425490bc40b8cc92685f85`
- frozen V6.1 artifact digest
  `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0`

Any material change to a feature formula, proxy, eligibility rule, opportunity
or sample definition, statistical test, threshold, multiplicity family,
qualification rule, semantic interpretation, or finding family **is not V6.1**.
Recommend a new lineage following the repository's actual conventions in
`services/api/app/player_analysis_v61/versions.py` (`VERSION_SURFACES`, with
`disposition` ∈ changed/compatible/unchanged/new). Inspect that file before
proposing a version name; do not assume "V6.2" or "V7".

Never reuse the sealed holdout under
`.local/calibration/v61/release-recovery-7df38e6/sealed-holdout/` as a tuning
set. Never mutate historical V6.1 evidence. Existing OpenDota-derived corpora
remain OpenDota-derived.

---

## Current finding inventory

Verified from code at research time. Confirm before relying on it.

**Seven public Elements** (`player_analysis_v6/constants.py::PUBLIC_ELEMENT_KEYS`,
defined in `player_analysis_v6/elements.py`):

| key | measures | unit |
|---|---|---|
| `breadth` | Shannon effective hero count | effective heroes |
| `toolkit` | effective functional-job count over the reviewed taxonomy | effective jobs |
| `involvement` | context-adjusted (kills + assists) per minute | K+A/min |
| `finishing` | context-adjusted kill share of known K+A events | kill share |
| `death_exposure` | context-adjusted deaths per ten minutes | deaths/10min |
| `transfer` | multi-signal agreement between familiar and stretch hero contexts | agreement |
| `consistency` | robust session-to-session agreement across outcome, activity, exposure | dispersion |

**Five finding families** (`FINDING_FAMILY_KEYS`): `pool_shape`, `transfer`,
`post_loss_response`, `combat_expression`, `session_drift`. Family definitions
and publication gates live in `player_analysis_v6/findings.py`.

**28 semantic outcomes** (`player_analysis_v61/semantic_outcomes.py`): 25
`public_candidate`, 3 `shadow_only` (`hero_lifecycle`, `identity_eras`,
`behavioral_loop`). By family: `pool_shape` 6, `transfer` 6, `session_drift` 6,
`post_loss_response` 5, `combat_expression` 5. Opportunity denominators in use:
`matches` (17), `transitions` (5), `sessions` (5), `occurrences` (1).

**Private supporting-signal graph**: `player_analysis_v61/supporting_signals.py`
carries a 128-feature classification catalog with `PUBLIC_ELEMENT_SUPPORT`,
`SUPPORTING`, `CONDITIONAL`, `LONGITUDINAL`, `FINDING_ONLY`, `RESEARCH_ONLY`,
`REJECTED` classifications and per-signal `OpportunityContract`s. **Read this
before inventing anything** — a large amount of design work already exists here,
and several of your candidates will already have a slot.

Statistical machinery: `FDR_Q = 0.05`, Benjamini–Hochberg over five families
(`family_statistics.benjamini_hochberg_five`), clustered bootstrap resampling
**complete sessions** (`DEFAULT_BOOTSTRAP_ITERATIONS = 2_000`,
`clustered-bca-approximation-1.0.0`), `MIN_ELIGIBLE_MATCHES = 30`,
`NORMAL_REPORT_MATCHES = 60`, `MIN_STABLE_SESSIONS = 8`,
`MIN_CONSISTENCY_SESSIONS = 12`, at most three published findings.

Language guards: `FORBIDDEN_FREE_TERMS` in `player_analysis_v6/constants.py` and
`_FORBIDDEN` in `semantic_outcomes.py` ban `aggression`, `intent`, `tilt`,
`fatigue`, `positioning`, `skill`, `causes`, `rank`, `mmr`, `personality`,
`death quality`, `warm-up`, and explicit position labels (`position 1`, `pos1`,
…). Parsed data makes some of these *measurable*; it does not make them
*publishable*. If you propose lifting a guard, argue it explicitly as a separate
decision for the owner.

---

## Current shallow-data limitations

What one OpenDota summary call cannot support, from
`research/free-dna-v6.1-cheap-history-ceiling.md` and the code:

- **Role is nearly invisible.** `lane` / `lane_role` coverage is roughly 2.5% in
  the OpenDota specimen. `summary_normalize.ROLE_HINTS` maps a *lane* enum onto
  role words and the module's own comment concedes it "cannot reliably split
  hard vs soft support without detail evidence." The `role` eligibility flag
  requires `role_confidence >= 0.60`, so role-gated analysis is effectively dark.
- **Performance is a proxy.** `involvement`, `finishing` and `death_exposure`
  are built from kills/deaths/assists and duration. There is no farm, no
  net worth, no lane outcome, no objective participation, no map information.
- **`toolkit` leans on an editorial taxonomy** rather than observed behaviour.
- **`transfer` and `consistency` infer from outcomes plus KDA**, not from what
  the player actually did differently.
- **No within-match time structure at all.** Every element is a match-level
  scalar. Sessions are the only sequencing the system has.
- Party context ~36% coverage; patch-like fields ~2.5%; so no solo-vs-party and
  no patch-specific claims.

This is the ceiling you are being asked to break — carefully.

---

## Verified STRATZ capabilities

Verified against the live API on 2026-08-27. Operational facts are in
`01-luna-max-provider-migration.md` §"Verified STRATZ API facts"; do not
re-derive them. The load-bearing ones for you:

- `take` is capped at **100** matches per request; a 365-day history costs
  roughly 6 requests for a 1.6 matches/day player and ~19 for a heavy one.
- Default token: 20/s, 250/min, 2 000/hour, 10 000/day.
- Partial responses are real: HTTP 200 with both `data` and `errors`.
- Storage / caching / attribution / commercial terms are
  `UNKNOWN — requires owner/STRATZ confirmation`. **This gates any corpus
  collection.** Design the corpus; do not collect it.

### Measured parsed availability

From the checked-in specimen (`.local/stratz-probe/specimen/`, 100 matches,
61.1 days, account 193875165):

| field | coverage |
|---|---|
| `parsedDateTime` non-null | 91 / 100 |
| `players[].position` | 91 / 100 |
| `players[].role` | 93 / 100 |
| `players[].lane` | 93 / 100 |
| `players[].roleBasic` | **100 / 100 — and that is the problem** |

`roleBasic` returns `"CORE"` on every unparsed match where `lane`, `position`
and `role` are all `null`. It is a default, not an observation. **Never treat a
`roleBasic` value as evidence.** Any candidate that depends on it is rejected on
sight.

Parsed coverage is high but not universal, and it is not missing at random —
unparsed matches in the specimen skew Turbo. Treat parsed availability as a
**confounder and a selection mechanism**, not as a background constant.

---

## Verified GraphQL field groups

Verified by live introspection and a live parsed-match response. Names are exact.

**Match level** (`MatchType`): `id`, `didRadiantWin`, `durationSeconds`,
`startDateTime`, `endDateTime`, `lobbyType`, `gameMode`, `gameVersionId`,
`clusterId`, `regionId`, `leagueId`, `isStats`, `parsedDateTime`,
`firstBloodTime`, `towerStatusRadiant/Dire`, `barracksStatusRadiant/Dire`,
`radiantNetworthLeads`, `radiantExperienceLeads`, `radiantKills`, `direKills`,
`bottomLaneOutcome`, `midLaneOutcome`, `topLaneOutcome`, `laneReport`,
`pickBans`, `towerDeaths`, `chatEvents`, `playbackData`, `analysisOutcome`.

**Match-player level** (`MatchPlayerType`): `playerSlot`, `isRadiant`,
`isVictory`, `heroId`, `variant`, `kills`, `deaths`, `assists`, `leaverStatus`,
`numLastHits`, `numDenies`, `goldPerMinute`, `networth`, `experiencePerMinute`,
`level`, `gold`, `goldSpent`, `heroDamage`, `towerDamage`, `heroHealing`,
`partyId`, `isRandom`, `lane`, `position`, `role`, `roleBasic`, `imp`, `award`,
`item0Id`..`item5Id`, `backpack0..2Id`, `neutral0Id`, `invisibleSeconds`,
`abilities`, `stats`, `playbackData`, `heroAverage`, `additionalUnit`.

**Per-player parsed statistics** (`MatchPlayerStatsType`) — confirmed populated
on a real parsed match: `networthPerMinute`, `goldPerMinute`,
`experiencePerMinute`, `lastHitsPerMinute`, `deniesPerMinute`,
`heroDamagePerMinute`, `towerDamagePerMinute`, `healPerMinute`,
`actionsPerMinute`, `impPerMinute`, `heroDamageReceivedPerMinute`,
`tripsFountainPerMinute`, `campStack`, `level`, `killEvents`, `deathEvents`,
`assistEvents`, `itemPurchases` (`time`, `itemId`), `itemUsed`, `wards`
(`time`, `type`, `positionX`, `positionY`), `wardDestruction`, `runes`
(`time`, `rune`), `courierKills`, `towerDamageReport`, `actionReport`,
`locationReport`, `farmDistributionReport`, `abilityCastReport`,
`heroDamageReport`, `inventoryReport`, `spiritBearInventoryReport`,
`matchPlayerBuffEvent`, `allTalks`, `chatWheels`.

**Player playback** (`MatchPlayerPlaybackDataType`): `playerUpdatePositionEvents`,
`playerUpdateGoldEvents`, `playerUpdateLevelEvents`, `playerUpdateHealthEvents`,
`playerUpdateBattleEvents`, `abilityLearnEvents`, `abilityUsedEvents`,
`itemUsedEvents`, `purchaseEvents`, `buyBackEvents`, `csEvents`, `goldEvents`,
`experienceEvents`, `healEvents`, `heroDamageEvents`, `towerDamageEvents`,
`killEvents`, `deathEvents`, `assistEvents`, `inventoryEvents`, `runeEvents`,
`streakEvents`, `spiritBearInventoryEvents`.

**Match playback** (`MatchPlaybackDataType`): `courierEvents`, `runeEvents`,
`wardEvents`, `buildingEvents`, `towerDeathEvents`, `roshanEvents`,
`radiantCaptainHeroId`, `direCaptainHeroId`.

### Fields whose semantics are NOT established

Observed on a real 1 503-second (25-minute) parsed match:

- `networthPerMinute` had **26** entries; `goldPerMinute` had **25**. Array
  lengths differ within the same match. Never assume index alignment across
  arrays, and never assume `len(array) == duration_minutes`.
- `level` returned `[-89, 91, 217, 405, 709, 900, 1008, 1074, 1133, 1269, 1326,
  1430]` — those are level-up **timestamps**, not levels. The field name is
  actively misleading.
- `experiencePerMinute` was spiky with interior zeros (`[118, 202, 146, 257, 97,
  139, 226, 0, 104, …]`) and is not obviously a rate.
- `imp` and `impPerMinute` are proprietary STRATZ AI metrics.
- `analysisOutcome`, `predictedOutcomeWeight`, `streakPrediction` are model
  outputs, not observations.

**Rule: a field whose semantics you have not established from data or official
documentation cannot found a candidate.** Opaque scores in particular —
`imp`, `analysisOutcome`, `award`, `predictedOutcomeWeight` — are rejected
unless you can state exactly what they measure. "STRATZ says the player was
good" is not a behavioural finding, and it imports someone else's model into
ours.

---

## Payload acquisition protocol

Live access is currently **manual**: `api.stratz.com` is unreachable from the
sandboxed environments, and automated requests are answered by a Cloudflare
interstitial unless `User-Agent` is exactly `STRATZ_API`. The working path is
the GraphiQL explorer at `https://api.stratz.com/graphiql`.

Tooling already in the repository:

- `.local/stratz-probe/queries.graphql` — six ready-to-paste probe queries.
- `.local/stratz-probe/stratz_probe.py` — automated harness (env-var token,
  request ceiling, redacted artifacts) for when direct access works.
- `.local/stratz-probe/stratz_to_canonical.py` — maps STRATZ rows onto the V6.1
  projection and runs the repository's own normalizer over them.
- `.local/stratz-probe/specimen/` — the 100-match specimen behind every number
  quoted here, with a regeneration script.

If live access is authorized:

- use the smallest number of requests that answers the question;
- prefer public/sample accounts; record `isAnonymous` and `isStratzPublic`;
- record the exact operation text and a hash of every response;
- save sanitized fixtures **only if** the storage terms permit it — they are
  currently `UNKNOWN`, so default to not persisting raw payloads;
- **do not call OpenDota**;
- do not begin large-scale collection under any circumstances.

If access is unavailable: work from the schema, the checked-in specimen, and
prepared queries; mark every empirical question `BLOCKED — needs payload` and
state exactly which query would resolve it.

> **Do not invent STRATZ field availability. Every serious candidate finding
> must cite the exact verified STRATZ GraphQL field/path(s) that make it
> possible.**

Never fabricate a sample value. If you need a number you do not have, say so.

---

## Payload / schema inventory

Produce, as an artifact:

1. every field path you verified, with source (introspection / observed payload);
2. observed coverage and nullability per path, with sample size;
3. array-length behaviour for every per-minute series;
4. classification of each path as **basic match metadata**, **player metadata**,
   **replay-derived**, or **computed/proprietary STRATZ analytics**;
5. an explicit "semantics unestablished" list.

## Parsed-field taxonomy

Group the verified surface into behavioural domains and, for each, state what it
can and cannot evidence. Investigate only where real data supports it:

lane assignment and lane outcome; role identity and role switching; farm, XP and
net-worth trajectories; lead and deficit dynamics; item purchase timing and
adaptation; skill build order; kill/death/assist timing and clustering; death
context; teamfight participation; objective participation; tower and Roshan
involvement; warding and dewarding including map coordinates; map movement and
region occupancy; rune behaviour; buyback; support economy; camp stacking;
courier behaviour; fight initiation versus follow-up; phase-specific
contribution; draft context; party and teammate context; comeback and throw
contexts.

That list is exploratory. It is **not** evidence that STRATZ exposes each item.

---

## Existing finding reassessment

Do not only add ideas. Produce this table, with a row for **every** current
Element, family and semantic outcome:

| current finding / family | existing feature or proxy | STRATZ opportunity | keep / enhance / replace / retire | version impact | reason |
|---|---|---|---|---|---|

For each, answer explicitly:

- Is the current proxy still appropriate?
- Can STRATZ evidence it more directly?
- Would direct evidence materially change what it means?
- Is it too broad? Should it split?
- Is it redundant once parsed data exists?
- Can it be made more role-fair?
- Does parsed data make it more statistically powerful?
- Does new context expose confounding the current analysis misses?
- Should it remain exactly unchanged?

Two known starting points, already established, that you must carry forward:

- **`role_hint` is the weakest link in V6.1.** STRATZ `position` gives
  `POSITION_1`..`POSITION_5` at ~91% coverage versus ~2.5% for OpenDota's lane
  proxy. Measured on the specimen with the repository's own normalizer,
  `lane`-derived and `position`-derived role disagree on **16 of 91** rows
  (17.6%), and 12 of those are `OFF_LANE` + `POSITION_4` — soft supports that
  the lane-shaped mapping labels `offlane`, which `ROLE_HINTS` treats as a core
  role. This is a textbook `REPLACE_PROXY`. It requires a new lineage, and it
  changes `role_adjusted_provisional` normalization for `involvement`,
  `finishing` and `death_exposure` — so it touches three of seven public
  Elements even though none of their formulas change.
- **Higher coverage is itself an analytical change.** Moving role coverage from
  ~2.5% to ~91% changes the eligible population for every role-gated element
  with no formula edit at all. Quantify this before proposing anything built on
  top of it.

---

## Candidate-generation methodology

1. Establish the verified field inventory first. No candidate before inventory.
2. Read `supporting_signals.py` and map candidates onto existing signal slots
   where they already exist. Prefer filling a designed slot to inventing a new one.
3. Generate broadly, then cut hard.
4. For each candidate, name the **behaviour**, not the metric. "Buys a defensive
   item earlier after a bad lane" is a behaviour. "Average item timing" is a
   column.
5. Reject anything whose meaning reduces to "you won more."

**Generate at least 50 raw candidate ideas before consolidation**, if — and only
if — the verified payload supports that many. If it does not, state plainly why
the verified data supports fewer and do not manufacture filler. Filler is worse
than a short list.

## Candidate specification

Every serious candidate must carry all four blocks.

**Product** — candidate name; family; opportunity classification; the player
question it answers; why a Dota player cares; identity resonance; actionability;
shareability; an example headline; an example explanation; a visualization or
interaction concept.

**Data** — exact STRATZ GraphQL paths; source objects; replay-parsed dependency;
nullability; historical availability; patch dependency; request and query-cost
implications; whether it needs `playbackData`; the exact derived-feature
definition, precisely enough to implement.

**Statistical design** — unit of analysis; opportunity definition; eligibility;
minimum opportunities; repeated-measures structure; confounders; role
normalization; hero normalization; game-duration normalization; skill-context
normalization if needed; effect definition; uncertainty; stability requirement;
multiplicity family; negative control or falsification test; publication
criteria; invalidation criteria.

**Product safety** — outcome leakage; causality overstatement; role bias;
core/support fairness; hero-specific bias; sparse-data risk; patch fragility;
privacy implications.

**Validation** — development corpus; calibration requirement; backtest; sealed
holdout requirement; Dota-player manual review; regression implications.

### Required opportunity classification

Assign exactly one, and defend it:

- **A. ENHANCE_EXISTING** — same conceptual finding, stronger or more direct evidence.
- **B. REPLACE_PROXY** — a more direct measure supersedes an indirect one.
  Requires a new analytical generation even if the copy barely changes.
- **C. NEW_SUBFINDING** — new behaviour under an existing family.
- **D. NEW_FAMILY** — a distinct repeated behavioural dimension.
- **E. BACKSTAGE_EVIDENCE_ONLY** — improves qualification or evidence; not player-facing alone.
- **F. PRESENTATION_ENRICHMENT** — richer explanation, unchanged analytical semantics.
- **G. REJECT** — noisy, redundant, confounded, outcome-leaky, too sparse,
  patch-fragile, too expensive, or simply not meaningful.

---

## Statistical methodology

Match the machinery already in use: BH-FDR at `q = 0.05` across families,
clustered bootstrap resampling complete sessions, interval-inside-ROPE or
practical-effect contracts, minimum opportunity counts, abstention over
speculation. Read `player_analysis_v6/statistics.py`,
`player_analysis_v61/estimators.py`, `hierarchical.py` and
`family_statistics.py` before proposing a test.

New problems that parsed data introduces, which you must address explicitly:

- **Within-match observations are not independent.** Twenty deaths in one match
  are one match, not twenty samples. State the clustering level for every
  candidate: event → match → session → player.
- **Time series invite spurious structure.** A per-minute curve has enough
  degrees of freedom to find a "breakpoint" in noise. Pre-declare shapes.
- **Multiplicity explodes.** Every new event stream multiplies candidate
  contrasts. More fields is not more evidence; it is more chances to be wrong.
  Define hypothesis families *before* looking, cluster correlated candidates,
  and control FDR within the declared family structure.
- **Opportunity counts, not match counts, gate power.** A player with 60
  eligible matches may have three buyback opportunities. Every candidate needs
  its own opportunity denominator, following the `OpportunityContract` pattern.
- **Parsed availability is a selection mechanism.** ~9% of specimen matches are
  unparsed and skew Turbo. Analysing only parsed matches conditions on a
  non-random subset. Address it or declare it a limitation.

Distinguish, for every candidate: more raw fields / more observations / more
*independent opportunities* / more hypotheses. Only the third increases power.
Do not cherry-pick dozens of correlated metrics and call the survivors
personality.

## Confounders and fairness

Every candidate must be checked against: role, hero, hero facet, game duration,
game mode (Turbo distorts every rate and economy measure), patch
(`gameVersionId`), region, party context, team tempo, lane matchup, draft
context, and parsed availability.

Core/support fairness is a first-class requirement. Warding, stacking, buyback
and support-economy signals must not become "supports are worse." Farm and
net-worth signals must not become "cores are better." A candidate that only
works for one role is a role-specific candidate and must say so.

Rank and MMR remain forbidden as analytical inputs
(`FORBIDDEN_ANALYTICAL_FIELDS`, and the V6.1 audit asserts
`rank_or_mmr_used: False`). STRATZ exposes `actualRank`, `averageRank`,
`bracket`, `seasonRank` and `behaviorScore`. Do not build on them. If you
believe skill-context normalization is unavoidable for a candidate, that is an
owner decision to surface, not a decision to make.

## Opportunity / sample analysis

For each Tier 1 and Tier 2 candidate, estimate the opportunity count available
to a typical player in a 365-day window, using the specimen's observed rate
(1.64 matches/day → ~597 matches/year, of which ~49% clear V6.1's current mode
eligibility) as the anchor. State the minimum viable opportunity count and what
fraction of players would qualify. A beautiful finding that fires for 4% of
players is a Tier 3 experiment.

---

## Required outputs

Produce these sections in your report, in this order.

**50+ raw ideas** — one line each: behaviour, the STRATZ path(s) that would
evidence it, and a first-pass classification. Breadth first; do not self-censor
here, but do not invent field availability either.

**Deduplication** — collapse near-duplicates, cluster correlated candidates, and
say what merged into what. Correlation clustering matters: ten variations on
"farm efficiency" are one hypothesis, not ten.

**Ranking model** — score serious candidates 1–5 on: player resonance; identity
value; actionability; novelty; shareability; analytical defensibility; role
fairness; sample availability; patch robustness; implementation complexity;
STRATZ query cost; visualization potential. **Define the weights and justify
them.** Analytical defensibility and role fairness should not be worth the same
as shareability, and you must say why you chose what you chose. Do not rank by
coolness.

**Tier 1** — high-value, reasonably defensible candidates for the first
STRATZ-native analytical iteration. Full candidate specification for each.

**Tier 2** — promising but methodologically harder. Full specification, plus
what would have to be true to promote them.

**Experimental ideas (Tier 3)** — research experiments, with the specific
question each would answer.

**Rejected ideas** — with the reason. This section is load-bearing; a rejection
list is how the next reader avoids re-proposing the same bad idea.

---

## Research corpus plan

Design, **but do not collect**, a reproducible STRATZ-native research corpus.
No crawl is authorized by this document, and the storage/attribution terms are
still `UNKNOWN`.

Cover: cohort selection and sampling frame; rank diversity (as a *sampling*
consideration only, not an analytical input); role diversity; hero diversity;
match depth per player; patch coverage; public-data eligibility and
`isStratzPublic` / `isAnonymous` handling; player privacy; exact GraphQL
operation snapshots; schema snapshot and drift detection; raw response
provenance; raw and normalized digests; normalizer version; deterministic
splitting; development / calibration / test separation; a **fresh** sealed
holdout; and request-budget arithmetic against the 10 000/day token ceiling.

State the total request cost of the proposed corpus explicitly. At ~6 requests
per player-year, a 1 000-player corpus is ~6 000 requests — most of a daily
budget. That arithmetic belongs in the plan.

## New analytical lineage / validation plan

Propose the lineage and validation path, adapted to the repository's actual
conventions:

```text
STRATZ research
→ development corpus
→ feature design
→ calibration
→ reproducibility / synthetic checks
→ fresh sealed holdout
→ product and content review
→ staging
→ owner-authorized production
```

Name the version surfaces that would change, in the vocabulary of
`versions.py::VERSION_SURFACES`, with a `disposition` for each. Say explicitly
which surfaces stay `unchanged` — that list is as important as the changed one.

## Future Luna implementation roadmap

A prioritized, dependency-ordered implementation sequence for the engineering
worker: what must exist before what, which acquisition changes are prerequisites
(parsed data means per-match queries, which is a different cost regime from the
history pull), which artifacts must be rebuilt, and where the owner decision
points sit.

## Expected artifacts

1. The research report (this structure).
2. Verified field inventory with coverage and nullability.
3. Existing-finding reassessment table.
4. Ranked candidate catalog with full specifications for Tier 1 and Tier 2.
5. Research corpus protocol.
6. Prepared GraphQL operations for every empirical question you could not answer.
7. An explicit `BLOCKED` list.

---

## Definition of Done

- [ ] current STRATZ schema inspected, not remembered
- [ ] field availability never invented
- [ ] representative real or recorded payloads inspected where access permitted
- [ ] exact STRATZ GraphQL paths cited for every serious candidate
- [ ] current V6.1 findings inspected from code, not from docs alone
- [ ] every current Element, family and semantic outcome reassessed
- [ ] every opportunity classified A–G and defended
- [ ] 50+ raw ideas considered, if verified payload richness supports it
- [ ] no filler invented to reach 50
- [ ] ideas deduplicated and correlation-clustered
- [ ] candidates ranked with justified weights
- [ ] derived features precisely defined
- [ ] units and opportunity denominators defined per candidate
- [ ] confounders documented per candidate
- [ ] role fairness considered
- [ ] hero bias considered
- [ ] patch dependence considered
- [ ] multiplicity addressed at the family level
- [ ] within-match dependence addressed
- [ ] parsed-availability selection bias addressed
- [ ] opaque STRATZ scores rejected unless their meaning is established
- [ ] `roleBasic` rejected as evidence
- [ ] cool stats separated from identity findings
- [ ] current proxy replacements identified
- [ ] analytical-version impact explicit per candidate
- [ ] research-corpus protocol proposed, with request-cost arithmetic
- [ ] no corpus collected
- [ ] existing sealed holdout not used as tuning data
- [ ] future calibration and validation path specified
- [ ] no analytical production implementation
- [ ] no production changes
- [ ] prioritized future implementation roadmap produced

## Final research report format

```markdown
## Research status
PASS | PARTIAL | BLOCKED

## Headline conclusion
Max one short paragraph.

## Verified capability summary
What STRATZ genuinely adds, in behavioural terms.

## Existing finding reassessment
The full table.

## Tier 1 recommendations
## Tier 2 recommendations
## Experimental
## Rejected

## Statistical risks introduced
## Analytical lineage recommendation
## Research corpus plan
## Implementation roadmap

## Blocked / unresolved
Every empirical question you could not answer, with the query that would.

## Production safety
Explicitly: production code / deployment / configuration / database /
analytical artifacts — changed or not. Expected: NO to all.
```
