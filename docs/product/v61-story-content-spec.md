# Free DNA V6.1 story and content specification

Status: implementation source of truth for the next product-presentation batch
Report contract: `free-dna-report-6.1.0`
Story contract: `free-story-6.1.0`
Copy contract to review: `free-dna-semantic-copy-6.1.0`
Scope: frontend composition, presentation payloads, and copy catalog only. No analytical, model, threshold, schema, calibration, holdout, or runtime behavior change is included.

## 1. Purpose and non-negotiables

This document converts the approved product direction into exact production
content. It adapts the 33-screen reference arc to the existing V6.1 API limit
of nine ordered beats. The reference screens are compositional guidance, not a
fixed page count: a screen may merge, collapse into a disclosure, or be omitted
when the corresponding output is absent. It does not create an eighth Element,
a sixth family, a new identity taxonomy, a new estimator, a new comparison, or
a new data source.

The experience must feel personal, surprising, paced, visual, collectible,
Dota-native, and immediately understandable. The rigorous analytical system is
backstage; the story is onstage.

The product observes summary behavior. It does not infer motive, emotion,
personality, skill, actual role, positioning, death quality, fatigue, intent,
or cause. Every variable-looking word in this document is a display choice for
an existing field, not permission to widen the data contract.

## 1A. Direction reconciliation

The governing constitution and the complete storyboard were read in full on
2026-08-25. The constitution governs the visual grammar and disclosure order;
the storyboard supplies the maximal reference arc. Both are applied only where
the existing V6.1 report provides the data.

The frozen product order is:

> Recognition → Familiarity → Structure → Adaptability → Adversity →
> Expression → Time → Coherence → Signature → Depth → Share

The primary UI is editorial and story-first. Story leads with one question,
one human headline, and one visual gesture. Evidence and Methodology are
explicit disclosures; they explain the headline without interrupting the first
read. Neutral findings remain intentional results, insufficient findings remain
calm and unresolved rather than error-like, and mixed findings show both valid
sides rather than flattening them.

The visual system is the Sequencing Field: observation cells, match ticks,
repeated cells, evidence bands, sequence strips, clusters, relationship links,
divergence, pulse density, chronology, alignment/recombination, and a compressed
signature strip are reused as the report advances. Discovery is sparse, Evidence
is grid-aligned with one dominant explanation and 1–3 cues, and Synthesis reuses
prior objects so the Signature is visibly earned. Element color, geometry,
texture, and motion are visual encodings only; every Element remains legible
without hue alone. Motion must have a static semantic equivalent.

The storyboard's account-recognition opening uses optional
`identity.display_name` and `identity.avatar_url`; it never exposes an account
ID or rank. Its sample-size examples use the actual
`metadata.eligible_match_count`. Its hero cards show only available
`match_count` and `share` fields; the current report does not provide hero win
rate, so win rate is not rendered. Its pool-map concept is implemented as the
existing chronological/timeline field plus an accessible table, not as an
invented spatial map or unsupported pan/zoom interaction. Its deeper-layer and
share-gallery copy names only actual eligible outputs.

## 2. Data and story vocabulary

Use these words consistently in the user interface:

| Backend term | Story term | Evidence term |
|---|---|---|
| `summary_history` | your year / your matches | 365-day summary history |
| `breadth_effective_count` | pool width | effective hero distribution |
| `fractional_job_mass` | mapped jobs | functional jobs in the reviewed taxonomy |
| `involvement_adjusted` | scoreboard involvement | context-adjusted kills plus assists per minute |
| `finishing_adjusted` | credited action split | known kill-plus-assist event share |
| `death_exposure_adjusted` | death exposure | context-adjusted deaths per ten minutes |
| `transfer_outcome_delta` | what travels when the hero changes | familiar/stretch distance bands |
| `consistency_outcome_dispersion` | session-to-session hold | information-weighted session agreement |
| `post_loss_response` | next choice after a loss | same-session result-state transitions |
| `session_drift` | what changes later in a session | completed-session positions G1–G5+ |
| `qualified` | the evidence cleared the gate | registered evidence groups and error control passed |
| `limited` / `descriptive` | early shape / descriptive only | sample, sessions, coverage, and limitations |
| `unavailable` / `suppressed` | not enough to call | missingness, coverage, or release suppression reason |

Do not expose raw enum keys, signal keys, estimator names, q-values, p-values,
FDR, bootstrap counts, threshold names, account IDs, match IDs, rank, MMR,
protected cohort references, or private supporting-signal codes in Story.

## 3. Three UI depths

Every major insight uses the same three depths.

### Depth 1 — Story

Default. One human question, one primary headline, one visual cue, and at most
one simple number or share. The strongest sentence is large and readable in
2–3 seconds. Do not show interval notation, estimator names, coverage
decimals, sample labels such as `n=`, q-values, or cost accounting.

### Depth 2 — Evidence

Opened by `Why this?`, `See what changed`, or `Show the comparison`. Show the
relevant comparison, a plain denominator, one simple baseline/before-after
cue, one to three factual evidence lines, and the limitation. Examples:

- “Across 41 comparable matches.”
- “This showed up across 9 sessions.”
- “The familiar and stretch ranges separate here.”
- “The next-choice movement stays within the supported range.”

### Depth 3 — Methodology

Opened by `How we measured it`. Show the exact estimator definition, 365-day
summary-only boundary, one history-request rule, session independence,
coverage/missingness, alternatives, hierarchical error-control note, and
version/artifact labels. Technical intervals may appear here when useful.

Use this exact global methodology copy:

> This report reads one 365-day summary-history window. It uses one history
> request, no detail or replay reads, and treats sessions—not individual
> matches—as the independent comparison unit. It has seven public Elements and
> five finding families. A finding appears only when its registered evidence
> and error-control checks clear; otherwise the story stays neutral or says
> there is not enough signal. No rank or MMR is used.

## 4. Production story grammar

The API still returns exactly nine ordered, skippable beats:

| Beat | API id | Production label | Emotional job | Reference screens composed |
|---:|---|---|---|---|
| 1 | `self-estimate` | Start | Recognition | 01, optional self-estimate |
| 2 | `identity-reveal` | Shape | Recognition → Familiarity | 02–04 |
| 3 | `pool-evolution` | Pool | Familiarity → Structure | 05–12 |
| 4 | `combat-expression` | Change | Structure → Adaptability | 13–15 and transfer bridge |
| 5 | `strongest-finding` | After loss | Adaptability → Adversity | 16–19 |
| 6 | `secondary-finding` | Match | Adversity → Expression | 20–23 |
| 7 | `recommendation` | Session | Expression → Time | 24–27 plus optional aftercare |
| 8 | `hero-mirror` | Signature | Time → Coherence → Signature | 28–31 |
| 9 | `deep-fork` | Share | Signature → Depth → Share | 32–33 plus optional Deep |

The API beat IDs remain unchanged for compatibility. The UI rail and headings
use the production labels above. Recommendation/five-game verification is an
optional aftercare drawer from the qualified finding; it is not the report
conclusion. The Signature and share surfaces must be visible before a user is
asked to enter Deep or commit to a follow-up.

## 5. Exact 33-screen reference content

The following entries are the complete content contract for the reference arc.
Each reference screen is rendered inside a production beat, merged into a
card/disclosure, or omitted when its backend condition is absent. No new
analytical output is implied by a reference screen.

### Chapter A — Opening / Recognition

#### 01 — We sequenced your Dota

- **Production surface / mode:** Beat 1 Start; Discovery.
- **Backend condition:** A valid V6.1 report with `schema_version`, `metadata`,
  `reproducibility`, and `quality`.
- **User question:** “What if my year could be seen as one shape?”
- **Exact primary copy:** “We sequenced your Dota.”
- **Exact secondary copy:** “Here’s what we found in the way you play.”
- **Evidence cue:** “365-day summary history · seven signals · five pattern families.”
- **CTA / disclosure:** `Start with your shape →`; secondary disclosure `How we measured this`.
- **Neutral variant:** “Your report is ready, even when some signals stay quiet.”
- **Insufficient variant:** “Some of your year is here; the missing pieces stay uncalled.”
- **Mixed variant:** “Some parts of the year are clear. Others stay open to context.”
- **Transition in:** None; this is the opening.
- **Transition out:** “Before the patterns, meet the heroes that carry your year.”
- **Data basis:** `metadata.data_from`, `metadata.data_to`, `reproducibility.history_contract`, `quality.available_elements`, `quality.published_findings`.
- **Forbidden stronger claim:** Never say the report knows the player’s personality, skill, motive, or complete Dota identity.

#### 02 — This is you

- **Production surface / mode:** Beat 2 Shape; Discovery.
- **Backend condition:** The report identity object exists. Show optional
  `identity.display_name` and `identity.avatar_url` only when present; show a
  Signature PRIMARY only when `identity_summary.slots.primary` is present.
- **User question:** “What does my Dota look like when the year is all in one frame?”
- **Exact primary copy:** “Yep. This is you.”
- **Exact secondary copy:** “Your year is ready to recognize.”
- **Evidence cue:** Optional display name/avatar specimen and, when available,
  PRIMARY text, one supporting line, and ANCHOR label; no raw slot keys.
- **CTA / disclosure:** `Reveal your shape`; `Why this?`; `How we measured it`.
- **Neutral variant:** “No single finding owns the headline yet. Your Elements are the shape we can describe.”
- **Insufficient variant:** “Your identity is still forming from this sample.”
- **Mixed variant:** “Your shape has more than one side. The slots below keep them separate.”
- **Transition in:** “We sequenced your Dota.”
- **Transition out:** “Before the patterns, there are the heroes.”
- **Data basis:** `identity.display_name`, `identity.avatar_url`,
  `identity_summary.headline`, `identity_summary.supporting_lines`,
  `identity_summary.slots.primary`, `identity_summary.slots.anchor`, and their
  `evidence_refs`.
- **Forbidden stronger claim:** Never render `identity_summary` as a personality type, diagnosis, grade, or fixed player type.

#### 03 — Analysis scope

- **Production surface / mode:** Small scope card inside Beats 1–2; Evidence/Methodology, not a standalone analytical result.
- **Backend condition:** `reproducibility` and `methodology` exist.
- **User question:** “What did this report actually look at?”
- **Exact primary copy:** “{metadata.eligible_match_count} matches. One recurring signal.”
- **Exact secondary copy:** “Across your recent Dota history.”
- **Evidence cue:** Plain-language chips: `365 days`, `summary only`, `one history request`.
- **CTA / disclosure:** `How we measured this`.
- **Neutral variant:** “The scope stays the same even when a particular signal stays quiet.”
- **Insufficient variant:** “A missing field narrows what this report can call.”
- **Mixed variant:** “Some comparisons have full context; others stay summary-only.”
- **Transition in:** “We sequenced your Dota.”
- **Transition out:** “Seven signals kept showing up.”
- **Data basis:** `metadata.eligible_match_count`, `reproducibility.history_contract`,
  `request_manifest`, `methodology.free_summary_only`,
  `methodology.population_window_days`, `cost`.
- **Forbidden stronger claim:** Never imply replay, item, lane, role, rank, MMR, or inside-game evidence was used.

### Chapter B — Elements / Hero familiarity

#### 04 — Seven signals

- **Production surface / mode:** Beat 2 Shape; Discovery with a visual scan.
- **Backend condition:** Exactly seven `elements` with the V6.1 keys.
- **User question:** “What parts of my game make up this shape?”
- **Exact primary copy:** “Seven signals kept showing up.”
- **Exact secondary copy:** “Start with the strongest 2–3 available signals.”
- **Evidence cue:** A 2–3 signal Discovery teaser chosen from server-supplied
  available order, followed by all seven labeled marks/cards in Evidence; no raw
  metric receipt in Story.
- **CTA / disclosure:** `See the seven signals`; each card opens `Why this?`.
- **Neutral variant:** “The seven signals do not all point in one direction. That is part of the shape.”
- **Insufficient variant:** “Some signals need more history before they can speak clearly.”
- **Mixed variant:** “Your shape is a mix: some signals hold, others move.”
- **Transition in:** “Yep. This is you.”
- **Transition out:** “Before the patterns, there are the heroes.”
- **Data basis:** `elements[*].key`, `status`, `zone`, `confidence`, `evidence_refs`.
- **Forbidden stronger claim:** Never call the seven signals traits, skills, or a score.

#### 05 — Before the patterns, the heroes

- **Production surface / mode:** Beat 3 Pool; Discovery.
- **Backend condition:** `hero_portfolio.heroes` or equivalent reviewed hero rows are present.
- **User question:** “Which heroes actually carry my year?”
- **Exact primary copy:** “Before the patterns, there are the heroes.”
- **Exact secondary copy:** “These are the names that carry your year.”
- **Evidence cue:** Human-readable hero names, top-share bars, and a `core / stretch / outer edge` legend when those fields are available.
- **CTA / disclosure:** `See the pool`; `Show the numbers` opens hero-share evidence.
- **Neutral variant:** “Your hero list has no single front row yet.”
- **Insufficient variant:** “Not enough usable hero history to map the pool.”
- **Mixed variant:** “The front row changes by part of the year.”
- **Transition in:** “Seven signals kept showing up.”
- **Transition out:** “If we had to start with one hero…”
- **Data basis:** `hero_portfolio.heroes`, `supporting_evidence.portfolio_shape`, reviewed hero names and top shares.
- **Forbidden stronger claim:** Never label a hero as the player’s true role, personality, or skill expression.

#### 06 — Most-played hero

- **Production surface / mode:** Beat 3 Pool; Discovery card inside the hero introduction.
- **Backend condition:** A top-1 hero share and human display name are available.
- **User question:** “Which hero shows up most in my year?”
- **Exact primary copy:** “If we had to start with one hero…”
- **Exact secondary copy:** “Your most-played hero is a starting point, not the whole story.”
- **Evidence cue:** Top-1 human hero name, observed `match_count`, and `share` of
  eligible matches. Do not display hero win rate because it is not supplied by
  the current V6.1 portfolio output.
- **CTA / disclosure:** `See the rest of the pool`.
- **Neutral variant:** “No single hero takes the lead.”
- **Insufficient variant:** “Not enough usable matches to name a front-runner.”
- **Mixed variant:** “The lead changes across the year.”
- **Transition in:** “Before the patterns, there are the heroes.”
- **Transition out:** “One hero doesn’t describe your Dota.”
- **Data basis:** `hero_portfolio.heroes[0].match_count`,
  `hero_portfolio.heroes[0].share`, reviewed hero display-name mapping, and
  `metadata.eligible_match_count`.
- **Forbidden stronger claim:** Never say the most-played hero is the player’s main identity or best hero.

#### 07 — Top heroes

- **Production surface / mode:** Beat 3 Pool; Discovery/Evidence visual.
- **Backend condition:** At least one human-readable top hero row; top-3/top-5 may be absent.
- **User question:** “Which heroes repeat, support, or stretch the pool?”
- **Exact primary copy:** “One hero doesn’t describe your Dota.”
- **Exact secondary copy:** “The rest of the pool shows what repeats and what stretches the shape.”
- **Evidence cue:** Human hero names, observed match counts and shares, and
  core/stretch/outer-edge grouping only when the server supplies it. Do not
  render win rate.
- **CTA / disclosure:** `Open the pool structure`.
- **Neutral variant:** “Your heroes share the front row.”
- **Insufficient variant:** “The pool is too small to separate a front row from the rest.”
- **Mixed variant:** “The front row changes between early, middle, and late year.”
- **Transition in:** “If we had to start with one hero…”
- **Transition out:** “There’s a difference between a hero you’ve played…”
- **Data basis:** `hero_portfolio.heroes[*].match_count`,
  `hero_portfolio.heroes[*].share`, `portfolio_shape.top1_share`, `top3_share`,
  `top5_share`, `stable_core_hero_ids`, `reliable_stretch_hero_ids`, reviewed
  display names.
- **Forbidden stronger claim:** Never call the front row comfort, mastery, or intent without a supported semantic outcome.

### Chapter C — Pool shape

#### 08 — Touched vs yours

- **Production surface / mode:** Beat 3 Pool; merged Discovery card, not a separate comparison to the entire Dota hero pool.
- **Backend condition:** `portfolio_shape` has hero distribution and mapped job mass.
- **User question:** “Is my pool only a list of names?”
- **Exact primary copy:** “There’s a difference between a hero you’ve played…”
- **Exact secondary copy:** “…and a hero that actually belongs to your Dota.”
- **Evidence cue:** Side-by-side `hero names` and `mapped jobs` mass; show taxonomy coverage.
- **CTA / disclosure:** `See the pool layers`.
- **Neutral variant:** “Your hero names and mapped jobs move together.”
- **Insufficient variant:** “Not enough taxonomy coverage to compare names with jobs.”
- **Mixed variant:** “Your names and jobs tell different parts of the story.”
- **Transition in:** “One hero doesn’t describe your Dota.”
- **Transition out:** “How wide is your hero pool?”
- **Data basis:** `portfolio_shape.fractional_job_mass`, `effective_job_count`, `effective_hero_count`, `taxonomy_coverage`, `taxonomy_sensitivity`.
- **Forbidden stronger claim:** Never compare the player to every possible hero or claim actual role coverage.

#### 09 — Pool breadth

- **Production surface / mode:** Beat 3 Pool; Discovery with an Element visual.
- **Backend condition:** `elements[breadth]` and its estimate/status exist.
- **User question:** “How wide is my hero pool?”
- **Exact primary copy:** Use the exact zone line: `A small group carries most of your year.` / `Your year reaches across a wide hero pool.` / `Your pool has a center with room around it.`
- **Exact secondary copy:** “Breadth describes how your matches spread across heroes, not how many names you have seen once.”
- **Evidence cue:** Effective hero distribution, top shares, stable core, and one chronological marker when available.
- **CTA / disclosure:** `Why this?`; `How we measured Breadth`.
- **Neutral variant:** “Your pool has a middle-of-the-road spread.”
- **Insufficient variant:** “Not enough history to call the shape of your pool.”
- **Mixed variant:** “Your pool is broad overall, with a smaller center underneath.”
- **Transition in:** “Your pool is more than the names on it.”
- **Transition out:** “A broad pool can still have a center.”
- **Data basis:** `elements.breadth.metric`, `zone`, `sample_size`, `supporting_evidence.portfolio_shape.shannon_effective_heroes`, top shares, HHI.
- **Forbidden stronger claim:** Never say specialist, versatile person, comfort player, or broad-minded player.

#### 10 — Pool concentration

- **Production surface / mode:** Beat 3 Pool; Discovery/Synthesis visual.
- **Backend condition:** `stable_core_hero_ids` or `core_hero_ids` plus concentration evidence.
- **User question:** “Where does the center of my pool sit?”
- **Exact primary copy:** “A broad pool can still have a center.”
- **Exact secondary copy:** “The heroes that repeat most are the anchor; the rest show how far the pool reaches.”
- **Evidence cue:** Stable core, top-50%-mass count, top-1/top-3 share, and HHI rendered as shape—not as a score.
- **CTA / disclosure:** `Show the core`; `Why this?`.
- **Neutral variant:** “Your pool has no single concentration edge.”
- **Insufficient variant:** “Not enough repeated hero history to find a stable center.”
- **Mixed variant:** “The center is stable, while the outer pool keeps moving.”
- **Transition in:** “A broad pool can still have a center.”
- **Transition out:** “Your pool has a core, a stretch, and an edge.”
- **Data basis:** `portfolio_shape.core_hero_ids`, `stable_core_hero_ids`, `top_shares`, `hhi`, `top50_mass_hero_count`.
- **Forbidden stronger claim:** Never call the core a comfort zone, safe choice, or psychological home.

#### 11 — Pool layers

- **Production surface / mode:** Beat 3 Pool; Discovery/Synthesis visual.
- **Backend condition:** Core, reliable stretch, or outer-edge arrays are present.
- **User question:** “What is the shape inside my pool?”
- **Exact primary copy:** “Your pool has a core, a stretch, and an edge.”
- **Exact secondary copy:** “The core repeats. The stretch widens the comparison. The outer edge stays descriptive.”
- **Evidence cue:** Three labeled bands using human hero names; do not show raw IDs.
- **CTA / disclosure:** `Open the pool map`.
- **Neutral variant:** “The pool layers stay close together.”
- **Insufficient variant:** “Not enough repeated choices to separate pool layers.”
- **Mixed variant:** “The core is stable, but the stretch behaves differently.”
- **Transition in:** “A broad pool can still have a center.”
- **Transition out:** “How did your pool move across the year?”
- **Data basis:** `stable_core_hero_ids`, `reliable_stretch_hero_ids`, `experimental_tail_hero_ids` rendered as `outer edge`, `cross_fitted`, and distance bands.
- **Forbidden stronger claim:** Never say the outer edge represents experimentation, risk appetite, or intention.

#### 12 — Hero pool map

- **Production surface / mode:** Beat 3 Pool; Evidence visual with accessible table/disclosure.
- **Backend condition:** `chronological_thirds`, `hero_jsd`, `job_jsd`, or `hero_portfolio.timeline` is available.
- **User question:** “How did my pool move across the year?”
- **Exact primary copy:** “Here’s who lives where.”
- **Exact secondary copy:** “Move through early, middle, and late to see what changed—and what held.”
- **Evidence cue:** Existing chronological thirds/timeline points, hero/job
  distribution movement, and coverage note. This is a field/timeline visual,
  not an invented spatial map.
- **CTA / disclosure:** `Move through the pool`; `Show the table`; `How we measured it`.
- **Neutral variant:** “Your hero and mapped-job shape stayed close across the year.”
- **Insufficient variant:** “Not enough chronological history to map pool movement.”
- **Mixed variant:** “The hero names moved more than the mapped jobs.”
- **Transition in:** “Your pool has a core, a stretch, and an edge.”
- **Transition out:** “Your pool tells us where you usually play. But what happens when the hero changes?”
- **Data basis:** `portfolio_shape.chronological_thirds`, `hero_jsd`, `job_jsd`, `hero_portfolio.evolution`, `hero_portfolio.timeline`.
- **Forbidden stronger claim:** Never attribute movement to a patch, draft, mood, or deliberate choice.

### Chapter D — Transfer

#### 13 — Transfer question

- **Production surface / mode:** Beat 4 Change; Discovery bridge.
- **Backend condition:** Transfer family record exists, whether published, neutral, or insufficient.
- **User question:** “What survives when the hero changes?”
- **Exact primary copy:** “When the hero changes, what comes with you?”
- **Exact secondary copy:** “Your pool shows the choice. Transfer asks what happens to the supported expression.”
- **Evidence cue:** Familiar → stretch → outer-edge path; do not show a score.
- **CTA / disclosure:** `Reveal Transfer`; `Why this?` after reveal.
- **Neutral variant:** “The familiar and stretch parts of your pool stay within the supported range.”
- **Insufficient variant:** “Not enough comparable familiar and stretch matches to ask this one confidently.”
- **Mixed variant:** “Your answer changes by signal.”
- **Transition in:** “Your pool tells us where you usually play. But what happens when the hero changes?”
- **Transition out:** “Dota moves you off-script in more than one way. A different hero is one. A loss is another.”
- **Data basis:** `findings[family=transfer]`, `supporting_evidence.transfer_frontier`, `elements.transfer`.
- **Forbidden stronger claim:** Never say the player adapts, succeeds, fails, or carries their skill as a general trait.

#### 14 — Transfer reveal

- **Production surface / mode:** Beat 4 Change; Discovery reveal.
- **Backend condition:** A published `transfer` family outcome with `claim_contract`, `interaction.enabled`, and evidence refs.
- **User question:** “What actually travels with the hero change?”
- **Exact primary copy by outcome:**
  - `clean_transfer`: “More of your observed expression travels when the hero changes.”
  - `results_stop_first`: “The result changes before your expression does.”
  - `expression_stops_first`: “Your expression changes before the result does.”
  - `involvement_boundary`: “Involvement holds farther into the hero change.”
  - `exposure_boundary`: “Death exposure holds farther into the hero change.”
  - `localized_function_bottleneck`: “The supported gap sits in one mapped job context.”
- **Exact secondary copy:** “This is bounded to the familiar, stretch, and supported distance bands in your history.”
- **Evidence cue:** One finite relationship visual: core boundary, two versions, or mapped-function comparison.
- **CTA / disclosure:** `Why this?`; `What else could explain it?`; `How we measured it`.
- **Neutral variant:** “The supported comparison does not separate familiar and stretch contexts.”
- **Insufficient variant:** “Not enough comparable familiar and stretch matches to call transfer.”
- **Mixed variant:** “Your answer changes by signal: one part travels, another does not.”
- **Transition in:** “When the hero changes, what comes with you?”
- **Transition out:** “Dota moves you off-script in more than one way. A different hero is one. A loss is another.”
- **Data basis:** Exact `semantic_outcome_key`, `claim_contract.claim`, `claim_contract.alternatives`, `interaction.kind`, `supporting_evidence.transfer_frontier`, and finding evidence refs.
- **Forbidden stronger claim:** Never say “your game always travels,” “you lose skill off-pool,” or “the hero change caused the result.”

#### 15 — Transfer evidence

- **Production surface / mode:** Beat 4 Change; Depth 2 Evidence.
- **Backend condition:** Same as Screen 14; when no outcome is published, show the neutral/insufficient card instead.
- **User question:** “Why does the transfer story look that way?”
- **Exact primary copy:** “See what changed when the hero changed.”
- **Exact secondary copy:** “The comparison keeps outcome, activity, and death exposure separate.”
- **Evidence cue:** Familiar/stretch counts, sessions, distance-band boundary, and one to three component rows. Use plain denominators.
- **CTA / disclosure:** `Close evidence`; `How we measured it`.
- **Neutral variant:** “The supported components stay compatible across the comparison.”
- **Insufficient variant:** “The comparison has fewer than the required supported opportunities.”
- **Mixed variant:** “The components do not move together, so both sides stay visible.”
- **Transition in:** “More of your observed expression travels when the hero changes.”
- **Transition out:** “Dota moves you off-script in more than one way. A different hero is one. A loss is another.”
- **Data basis:** `finding.signal_keys`, `supporting_evidence.transfer_frontier.distance_bands`, `sample_size`, `independent_session_count`, `coverage`, `interaction`.
- **Forbidden stronger claim:** Never expose raw match IDs or convert a component difference into a causal explanation.

### Chapter E — Post-loss / Adversity

#### 16 — Off-script bridge

- **Production surface / mode:** Beat 5 After loss; Discovery bridge.
- **Backend condition:** Post-loss family record exists; no finding is required for the bridge.
- **User question:** “What does a result change in the next choice?”
- **Exact primary copy:** “A loss can move the script too.”
- **Exact secondary copy:** “We only describe the next observed choice in the same session.”
- **Evidence cue:** A simple result → next-choice path with no direction assumed.
- **CTA / disclosure:** `Ask what happens after a loss`.
- **Neutral variant:** “The next choice does not separate cleanly by result state.”
- **Insufficient variant:** “There are not enough same-session transitions to ask this safely.”
- **Mixed variant:** “The one-loss and two-plus-loss states do not tell the same story.”
- **Transition in:** “Dota moves you off-script in more than one way. A different hero is one. A loss is another.”
- **Transition out:** “What does your Dota look like after a loss?”
- **Data basis:** `supporting_evidence.result_response`, `cross_session_transitions=0`, state keys `win`, `one_loss`, `two_plus_losses`, `win_streak`.
- **Forbidden stronger claim:** Never say the loss caused a choice, revealed emotion, or shows recovery/tilt.

#### 17 — Post-loss question

- **Production surface / mode:** Beat 5 After loss; Discovery question.
- **Backend condition:** `post_loss_response` family record is present.
- **User question:** “What does your Dota look like after a loss?”
- **Exact primary copy:** “What does your Dota look like after a loss?”
- **Exact secondary copy:** “The next choice is the signal. The reason for it stays outside the data.”
- **Evidence cue:** One-loss vs two-plus-loss state cards; include wins as context when available.
- **CTA / disclosure:** `Reveal your next-choice pattern`.
- **Neutral variant:** “Your next-choice movement stays about the same across the supported result states.”
- **Insufficient variant:** “Not enough same-session transitions to call a post-loss pattern.”
- **Mixed variant:** “The answer changes between one loss and two or more.”
- **Transition in:** “A loss can move the script too.”
- **Transition out:** “What you pick next is one response. What you do once the horn sounds is another.”
- **Data basis:** `result_response.states`, transition denominator, session count, same-hero rate, movement interval, next-result rate.
- **Forbidden stronger claim:** Never use tilt, anger, frustration, recovery, resilience, or intentional adjustment.

#### 18 — Post-loss reveal

- **Production surface / mode:** Beat 5 After loss; Discovery reveal.
- **Backend condition:** A published `post_loss_response` outcome.
- **User question:** “What does the next choice do after the result?”
- **Exact primary copy by outcome:**
  - `one_loss_runback`: “After one loss, your next choice stays closer to your prior path.”
  - `two_loss_switch`: “After two or more losses, your next choice changes differently.”
  - `result_shaped_pool`: “Your next choice moves differently after wins and losses.”
  - `result_invariant_response`: “Your next-choice movement stays about the same after wins and losses.”
  - `adjustment_without_recovery`: “Your next choice changes after the result, while the next result stays unresolved.”
- **Exact secondary copy:** “This is a same-session transition pattern, not a reason or a recovery story.”
- **Evidence cue:** `after_x` relationship with one-loss/two-plus-loss rows and a next-result guardrail when available.
- **CTA / disclosure:** `Why this?`; `See both result states`; `How we measured it`.
- **Neutral variant:** “No single result state separated your next-choice movement.”
- **Insufficient variant:** “Not enough same-session transitions to call this one.”
- **Mixed variant:** “The one-loss and two-plus-loss states do not tell the same story.”
- **Transition in:** “What do you pick after a loss?”
- **Transition out:** “What you pick next is one response. What you do once the horn sounds is another.”
- **Data basis:** Exact `semantic_outcome_key`, `result_response.states`, transition/session gate, outcome claim contract and alternatives.
- **Forbidden stronger claim:** Never say “you tilt,” “you recover,” “you panic,” or “the loss makes you switch.”

#### 19 — Post-loss evidence

- **Production surface / mode:** Beat 5 After loss; Depth 2 Evidence.
- **Backend condition:** Finding is published or family state is neutral/insufficient.
- **User question:** “What did the same-session comparison actually see?”
- **Exact primary copy:** “The comparison follows the next choice, not the reason behind it.”
- **Exact secondary copy:** “Rows are grouped by result state inside the same session.”
- **Evidence cue:** Opportunities, sessions, same-hero rate, movement direction/range, and next-result guardrail where present.
- **CTA / disclosure:** `Close evidence`; `How we measured it`.
- **Neutral variant:** “The complete supported range keeps the result states together.”
- **Insufficient variant:** “The report found fewer than the required same-session opportunities.”
- **Mixed variant:** “The result states separate in one component and stay together in another.”
- **Transition in:** “After one loss, your next choice stays closer to your prior path.”
- **Transition out:** “What you pick next is one response. What you do once the horn sounds is another.”
- **Data basis:** `supporting_evidence.result_response`, finding `signal_keys`, denominator, intervals, and `cross_session_transitions=0`.
- **Forbidden stronger claim:** Never show raw transition IDs, match IDs, or a causal result statement.

### Chapter F — Combat expression

#### 20 — Into the match

- **Production surface / mode:** Beat 6 Match; Discovery bridge.
- **Backend condition:** The seven Elements include Involvement/Finishing/Death Exposure records, even if some are unavailable.
- **User question:** “Once the horn sounds, what can the summary actually show?”
- **Exact primary copy:** “The hero is only the start of the match.”
- **Exact secondary copy:** “The next layer is the scoreboard expression we can observe.”
- **Evidence cue:** Involvement, Finishing, and Death Exposure marks; no claim about positioning or intent.
- **CTA / disclosure:** `Into the match`.
- **Neutral variant:** “The covered match signals stay close together.”
- **Insufficient variant:** “The summary does not have enough context-resolved matches for this layer.”
- **Mixed variant:** “The match story changes by signal.”
- **Transition in:** “What you pick next is one response. What you do once the horn sounds is another.”
- **Transition out:** “What does your game look like once the horn sounds?”
- **Data basis:** `elements.involvement`, `elements.finishing`, `elements.death_exposure`, and their supporting evidence.
- **Forbidden stronger claim:** Never imply inside-game movement, fight entry, aggression, or intent.

#### 21 — Combat question

- **Production surface / mode:** Beat 6 Match; Discovery question.
- **Backend condition:** Combat family record exists.
- **User question:** “What does your game look like once the horn sounds?”
- **Exact primary copy:** “Once the horn sounds, what keeps showing up?”
- **Exact secondary copy:** “Involvement and death exposure are separate signals—not a judgment.”
- **Evidence cue:** Two-axis visual or two-card comparison with a text/table fallback.
- **CTA / disclosure:** `Reveal match expression`.
- **Neutral variant:** “Involvement and death exposure stay compatible in the supported comparison.”
- **Insufficient variant:** “Not enough context-resolved matches to call combat expression.”
- **Mixed variant:** “It depends on the signal: involvement and exposure do not move together.”
- **Transition in:** “The hero is only the start of the match.”
- **Transition out:** “One match shows expression. A session shows whether it holds.”
- **Data basis:** Combat family record, `involvement`, `death_exposure`, `finishing`, and relationship interaction kind.
- **Forbidden stronger claim:** Never call a quadrant aggression, safety, skill, or death quality.

#### 22 — Combat reveal

- **Production surface / mode:** Beat 6 Match; Discovery reveal.
- **Backend condition:** Published `combat_expression` outcome.
- **User question:** “Which part of the match expression moves?”
- **Exact primary copy by outcome:**
  - `involvement_holds_exposure_moves`: “Involvement holds while death exposure moves.”
  - `exposure_holds_involvement_moves`: “Death exposure holds while involvement moves.”
  - `same_expression_different_results`: “Similar summary expression can arrive with different results.”
  - `different_expression_same_results`: “Similar results can arrive with different summary expression.”
  - `localized_variance`: “More of the expression variance sits in one supported context.”
- **Exact secondary copy:** “The comparison stays with covered scoreboard rates; it does not explain what happened inside a game.”
- **Evidence cue:** `two_versions` or `variance_decomposition` visual; label each component in plain language.
- **CTA / disclosure:** `Why this?`; `Show the two signals`; `How we measured it`.
- **Neutral variant:** “The covered match signals stay within the supported range.”
- **Insufficient variant:** “Not enough context-resolved matches to call this one.”
- **Mixed variant:** “One signal holds while another moves.”
- **Transition in:** “What does your game look like once the horn sounds?”
- **Transition out:** “One match shows expression. A session shows whether it holds.”
- **Data basis:** Exact combat outcome, `supporting_evidence.involvement`, `finishing`, `death_exposure`, interaction payload, and claim contract.
- **Forbidden stronger claim:** Never say the player was aggressive, passive, positioned well, reckless, or caused the result.

#### 23 — Combat evidence

- **Production surface / mode:** Beat 6 Match; Depth 2 Evidence.
- **Backend condition:** Published, neutral, or insufficient combat family state.
- **User question:** “What are the two signals doing underneath?”
- **Exact primary copy:** “See the two match signals side by side.”
- **Exact secondary copy:** “Involvement counts adjusted kills plus assists per minute. Death exposure counts adjusted deaths per ten minutes.”
- **Evidence cue:** Simple ranges/baselines, context coverage, comparable matches, and sessions; show no raw estimator name in the first panel.
- **CTA / disclosure:** `Close evidence`; `How we measured it`.
- **Neutral variant:** “Neither covered signal separates beyond the supported range.”
- **Insufficient variant:** “The required context coverage is not present for this comparison.”
- **Mixed variant:** “One signal separates; the other stays within range.”
- **Transition in:** “Involvement holds while death exposure moves.”
- **Transition out:** “One match shows expression. A session shows whether it holds.”
- **Data basis:** `supporting_evidence.involvement`, `finishing`, `death_exposure`, `coverage`, `sample_size`, `independent_session_count`, limitations.
- **Forbidden stronger claim:** Never render “fight entry,” positioning, intent, or death quality.

### Chapter G — Session drift / Time

#### 24 — One match vs session

- **Production surface / mode:** Beat 7 Session; Discovery bridge.
- **Backend condition:** `session_curve` exists, including a truthful unavailable/insufficient state.
- **User question:** “Does one match tell the whole session story?”
- **Exact primary copy:** “One match shows expression. A session shows whether it holds.”
- **Exact secondary copy:** “We use completed sessions and direct game positions, not a fatigue story.”
- **Evidence cue:** G1–G5+ position rail and completed-session count.
- **CTA / disclosure:** `See the session curve`.
- **Neutral variant:** “The covered shape stays compatible from game 1 to later games.”
- **Insufficient variant:** “Not enough completed sessions to compare positions.”
- **Mixed variant:** “The pool and summary expression do not move in the same way.”
- **Transition in:** “One match shows expression. A session shows whether it holds.”
- **Transition out:** “What changes later in a session?”
- **Data basis:** `supporting_evidence.session_curve.positions`, `censored_sessions`, `opportunity_rule=direct-position-denominators`.
- **Forbidden stronger claim:** Never say fatigue, warm-up, focus, stamina, or intended stopping.

#### 25 — Session question

- **Production surface / mode:** Beat 7 Session; Discovery question.
- **Backend condition:** Session family record exists.
- **User question:** “Is game five still the same summary shape?”
- **Exact primary copy:** “Is game five still the same summary shape?”
- **Exact secondary copy:** “The first game and later positions stay separate so the curve remains readable.”
- **Evidence cue:** Direct-position labels G1, G2, G3, G4, G5+.
- **CTA / disclosure:** `Reveal the session shape`.
- **Neutral variant:** “Your covered expression stays compatible across completed session positions.”
- **Insufficient variant:** “Not enough completed sessions to call a session pattern.”
- **Mixed variant:** “The session story changes by what you measure.”
- **Transition in:** “One match is a snapshot. A session shows the shape moving.”
- **Transition out:** “A covered part of your expression moves as the session continues.”
- **Data basis:** `findings[family=session_drift]`, `session_curve`, direct positions, completed sessions, censored sessions.
- **Forbidden stronger claim:** Never say later games prove fatigue, decline, improvement, or intention.

#### 26 — Session reveal

- **Production surface / mode:** Beat 7 Session; Discovery reveal.
- **Backend condition:** Published `session_drift` outcome.
- **User question:** “What does the completed-session curve show?”
- **Exact primary copy by outcome:**
  - `opening_game_signature`: “Game 1 has a different supported shape from later games.”
  - `gradual_session_drift`: “A covered part of your expression moves as the session continues.”
  - `predeclared_breakpoint`: “The first clear break appears at the registered session position.”
  - `selection_only_drift`: “Your pool changes across a session while summary expression stays compatible.”
  - `bounded_stopping_response`: “Completed session endings differ after the registered result state.”
- **Exact secondary copy:** “This uses completed sessions and direct game positions. Selection into longer sessions remains an alternative.”
- **Evidence cue:** `session_curve` line/position visual with a text table alternative.
- **CTA / disclosure:** `Why this?`; `Show the session positions`; `How we measured it`.
- **Neutral variant:** “Your covered expression stays compatible across completed session positions.”
- **Insufficient variant:** “Not enough completed sessions to call this one.”
- **Mixed variant:** “The pool changes, while the covered expression stays compatible.”
- **Transition in:** “What changes later in a session?”
- **Transition out:** “We’ve been looking at what changes. Now look at what keeps showing up.”
- **Data basis:** Exact outcome, `session_curve.positions`, censoring, direct-position denominator, finding contract and alternatives.
- **Forbidden stronger claim:** Never say fatigue, warm-up, loss of focus, stopping intention, or cause.

#### 27 — Session evidence

- **Production surface / mode:** Beat 7 Session; Depth 2 Evidence.
- **Backend condition:** Published, neutral, or insufficient session family state.
- **User question:** “How did the session curve earn that sentence?”
- **Exact primary copy:** “See the session positions underneath.”
- **Exact secondary copy:** “Each point uses completed sessions and direct game-position opportunities.”
- **Evidence cue:** G1/G2/G3/G4/G5+ rows with matches, sessions, result rate where available, and censored-session note.
- **CTA / disclosure:** `Close evidence`; `How we measured it`.
- **Neutral variant:** “The complete supported ranges overlap across the session positions.”
- **Insufficient variant:** “One or more positions do not have the required opportunities and sessions.”
- **Mixed variant:** “The choice curve moves while the covered expression curve stays together.”
- **Transition in:** “Game 1 has a different supported shape from later games.”
- **Transition out:** “We’ve been looking at what changes. Now look at what keeps showing up.”
- **Data basis:** `supporting_evidence.session_curve`, position `matches`, `sessions`, `result_rate`, `censored_sessions`, limitations.
- **Forbidden stronger claim:** Never report a fatigue or warm-up conclusion.

### Chapter H — Synthesis / Signature

#### 28 — None of these lives alone

- **Production surface / mode:** Beat 8 Signature; Synthesis.
- **Backend condition:** At least three public Elements exist. Findings may be zero to three.
- **User question:** “How do these signals connect?”
- **Exact primary copy:** “None of these patterns lives alone.”
- **Exact secondary copy:** “The shape comes from how the signals line up.”
- **Evidence cue:** Reuse the seven signal marks and highlight only the Elements/findings with evidence refs.
- **CTA / disclosure:** `See the underlying shape`.
- **Neutral variant:** “The signals stay distinct; no single one takes over the story.”
- **Insufficient variant:** “The report has descriptive pieces, but not enough qualified connections for a stronger synthesis.”
- **Mixed variant:** “Some signals hold while others move. The tension is part of the shape.”
- **Transition in:** “We’ve been looking at what changes. Now look at what keeps showing up.”
- **Transition out:** “They keep resolving into the same underlying shape.”
- **Data basis:** Seven `elements`, published finding summaries, `identity_summary.slots`, `supporting_evidence` refs.
- **Forbidden stronger claim:** Never collapse the synthesis into a global score, grade, or personality type.

#### 29 — Underlying shape

- **Production surface / mode:** Beat 8 Signature; Synthesis.
- **Backend condition:** PRIMARY/TWIST/ANCHOR slots or descriptive identity fallback.
- **User question:** “What keeps showing up underneath the individual findings?”
- **Exact primary copy:** “They keep resolving into the same underlying shape.”
- **Exact secondary copy:** “The primary thread, the twist, and the hero anchor stay tied to their evidence.”
- **Evidence cue:** Three slot cards with scope and evidence refs; absent slots remain absent.
- **CTA / disclosure:** `Show me the Signature`; `Why this signature?`.
- **Neutral variant:** “The signals describe a shape, but no single through-line clears the identity gate.”
- **Insufficient variant:** “The underlying shape is still forming from this sample.”
- **Mixed variant:** “The primary thread and the twist point in different directions; both stay visible.”
- **Transition in:** “None of these patterns lives alone.”
- **Transition out:** “Your Dota Signature.”
- **Data basis:** `identity_summary.slots.primary`, `.twist`, `.anchor`, `compatibility_checks`, chronological-third stability, finding evidence refs.
- **Forbidden stronger claim:** Never turn a slot into “you are a [type]” or imply psychological identity.

#### 30 — Dota DNA Signature

- **Production surface / mode:** Beat 8 Signature; Synthesis/Share precursor.
- **Backend condition:** Signature may be complete, partial, descriptive, or unavailable. A complete signature requires traceable slot evidence.
- **User question:** “What is recognizably my Dota?”
- **Exact primary copy:** “Your Dota Signature.”
- **Exact secondary copy:** “A name for the supported pattern—not a fixed player type.”
- **Evidence cue:** `PRIMARY` + `TWIST` + `ANCHOR`, each with human text, scope, and one visual ref.
- **CTA / disclosure:** `Why this signature?`; `Open the layers`; `Share this` only when eligible.
- **Neutral variant:** “Your Dota Signature is still taking shape.”
- **Insufficient variant:** “There is not enough stable evidence to name a Signature yet.”
- **Mixed variant:** “Your Signature has a clear core and a context-dependent twist.”
- **Transition in:** “They keep resolving into the same underlying shape.”
- **Transition out:** “It comes from what keeps showing up together.”
- **Data basis:** Typed identity slots, seven Elements, up to three published findings, hero portfolio anchor, evidence refs.
- **Forbidden stronger claim:** Never invent a class, horoscope, psychological label, or universal player type.

#### 31 — Why this signature

- **Production surface / mode:** Beat 8 Signature; Depth 2 Synthesis/Evidence.
- **Backend condition:** At least one Signature slot or descriptive identity map exists.
- **User question:** “Why did this Signature land on me?”
- **Exact primary copy:** “Why this describes your Dota.”
- **Exact secondary copy:** “Open the Elements, finding, and hero core that earned the Signature.”
- **Evidence cue:** A three-part evidence map: dominant Elements, strongest qualified finding if any, and hero anchor/core.
- **CTA / disclosure:** `Why this?`; `How we measured it`.
- **Neutral variant:** “The evidence supports a shape, not a single Signature sentence.”
- **Insufficient variant:** “The Signature cannot be made more specific from the available history.”
- **Mixed variant:** “The evidence is coherent in the core and mixed in the context-dependent layer.”
- **Transition in:** “Your Dota Signature.”
- **Transition out:** “This is the layer we can see for free.”
- **Data basis:** Slot evidence refs, `elements[*].evidence_refs`, strongest/secondary published findings, `supporting:portfolio_shape`.
- **Forbidden stronger claim:** Never say “this proves why you play,” “this is your true style,” or “this causes your results.”

### Chapter I — Depth / Share

#### 32 — Deeper layers

- **Production surface / mode:** Beat 9 Share; Depth 2/3.
- **Backend condition:** Claim contract exists for a published finding, or methodology exists for any report. Deep questions appear only when offered.
- **User question:** “What can I see underneath the headline?”
- **Exact primary copy:** “This is the layer we can see for free.”
- **Exact secondary copy:** “There’s more underneath it.”
- **Evidence cue:** Three controls: `Why this?`, `What else could explain it?`, `How we measured it`.
- **CTA / disclosure:** `Open the layers`; optional `Ask Deep this question`; `Skip Deep`.
- **Neutral variant:** “There is no stronger branch to open here, but the report boundary remains available.”
- **Insufficient variant:** “This report has no evidence-qualified Deep question.”
- **Mixed variant:** “The evidence supports more than one valid context, so both layers stay open.”
- **Transition in:** “Why this describes your Dota.”
- **Transition out:** “Your Dota DNA, in pieces.”
- **Data basis:** `claim_contract.claim`, `.alternatives`, `.verification`, `.deep_handoff`, `methodology`, `diagnostic_questions`.
- **Forbidden stronger claim:** Never promise a deeper answer, imply detail/replay access before it exists, or expose an opaque cohort ref.

#### 33 — Share your DNA

- **Production surface / mode:** Beat 9 Share; Share.
- **Backend condition:** Show only server-eligible `share_candidates`; allowed kinds are dynamic identity, strongest finding, and hero mirror. Maximum three.
- **User question:** “Which part of this story would I send to a Dota friend?”
- **Exact primary copy:** “Your Dota DNA, in pieces.”
- **Exact secondary copy:** “Choose the part that feels most like you.”
- **Evidence cue:** Gallery/contact sheet of server-rendered eligible cards;
  no self-estimate, raw IDs, account ID, rank, MMR, or raw match data.
- **CTA / disclosure:** `Share Signature`; `Share strongest finding`; `Share Hero Mirror`; `Download card`; `Copy link`; `Copy text` as fallback.
- **Neutral variant:** “Your story is ready to keep, even when no standalone card clears the share gate.”
- **Insufficient variant:** “No standalone share card is eligible from this report.”
- **Mixed variant:** “Some parts are share-ready; the rest stays inside the report.”
- **Transition in:** “There’s more underneath it.”
- **Transition out:** Optional `Ask Deep this question`; otherwise finish.
- **Data basis:** `share_candidates[*].eligible`, `kind`, `evidence_refs`, `blockers`, `share-svg-6.1.0`; Signature/identity slots; strongest published finding; hero mirror.
- **Forbidden stronger claim:** Never make an ineligible finding shareable, include a recommendation as a standalone card, or turn a weak signal into a stronger slogan.

## 6. Exact transition copy

Use these transitions verbatim or with only grammatical localization:

1. **Pool → Transfer:** “Your pool tells us where you usually play. But what happens when the hero changes?”
2. **Transfer → Post-loss:** “Dota moves you off-script in more than one way. A different hero is one. A loss is another.”
3. **Post-loss → Combat:** “What you pick next is one response. What you do once the horn sounds is another.”
4. **Combat → Session:** “One match shows expression. A session shows whether it holds.”
5. **Session → Synthesis:** “We’ve been looking at what changes. Now look at what keeps showing up.”

## 7. Seven Element copy contract

The following are the exact Story/neutral/insufficient variants. The evidence
and methodology labels are deliberately short; their complete data basis is in
the matrix.

| Element | Story question | Strong / zone variants | Neutral | Insufficient | Evidence cue | Methodology label |
|---|---|---|---|---|---|---|
| Breadth | “How wide is your hero pool?” | “A small group carries most of your year.” / “Your year reaches across a wide hero pool.” / “Your pool has a center with room around it.” | “Your pool has a middle-of-the-road spread.” | “Not enough history to call the shape of your pool.” | Effective hero spread, top shares, stable core. | “Effective hero distribution and annual hero shares.” |
| Toolkit | “Do your heroes solve the same job—or different ones?” | “Different heroes, similar jobs.” / “Your heroes cover different jobs.” / “Your pool covers a mix of jobs without one clear edge.” | “Your mapped jobs stay in the middle of the supported range.” | “Not enough mapped hero context to call your toolkit.” | Fractional job mass and taxonomy coverage. | “Fractional job mass in the reviewed hero taxonomy.” |
| Involvement | “How often are you in the scoreboard action?” | “Your adjusted involvement shows up often.” / “Your adjusted involvement stays on the quieter side.” / “Your involvement sits near its supported range.” | “Your involvement sits near its supported range.” | “Not enough context-resolved matches to call involvement.” | Adjusted kills plus assists per minute. | “Context-adjusted kills plus assists per minute.” |
| Finishing | “When credited action happens, how much of it is kills?” | “More of your credited action lands as kills.” / “Your credited action leans more toward assists.” / “Your credited action stays balanced between kills and assists.” | “Your credited action stays balanced between kills and assists.” | “Not enough known kill-plus-assist events to call finishing.” | Known kill/assist event split. | “Beta-binomial share of known kill-plus-assist events.” |
| Death Exposure | “How much death exposure shows up in your matches?” | “Your adjusted death rate sits on the lower-exposure side.” / “Your adjusted death rate sits on the higher-exposure side.” / “Your death exposure stays near its supported range.” | “Your death exposure stays near its supported range.” | “Not enough context-resolved matches to call death exposure.” | Adjusted deaths per ten minutes. | “Context-adjusted deaths per ten minutes.” |
| Transfer | “What survives when the hero changes?” | Outcome-specific copy from Section 5, Screen 14. | “The supported comparison does not separate familiar and stretch contexts.” | “Not enough comparable familiar and stretch matches to call transfer.” | Familiar/stretch distance bands. | “Cross-fitted multi-signal distance bands.” |
| Consistency | “Does your expression hold from session to session?” | “Your expression holds together across sessions.” / “Your expression changes more from session to session.” / “Your sessions stay within a mixed range.” | “Your sessions stay within a mixed range.” | “Not enough completed sessions to call consistency.” | Session-to-session outcome/activity/exposure spread. | “Information-weighted session-to-session agreement.” |

### Visual Element identities

These are visual encodings, not analytical definitions. The renderer must pair
each with text, geometry, texture, and motion so hue is never the only cue:

| Element | Geometry / texture | Motion meaning |
|---|---|---|
| Breadth | spread, branching, and widening cell intervals | cells distribute or gather according to observed hero distribution |
| Toolkit | modular repeated units with controlled variation | units recombine into mapped-job groupings |
| Involvement | pulse links and connection density | links pulse only when the covered signal is being revealed |
| Finishing | converging cells and closed bands | marks converge on the observed action split |
| Death Exposure | open edges and threshold crossings | edges expose the supported boundary without dramatizing it |
| Transfer | bridge continuity across two bands | the same structure preserves or diverges across familiar/stretch contexts |
| Consistency | cadence and regular alignment | repeated cells hold or shift across sessions |

Discovery shows only a fragment of these identities; Evidence exposes the
supporting band; Synthesis recombines the same objects into the Signature.

## 8. Five finding-family copy contract

### Pool Shape

- **Question:** “What kind of pool do you actually carry?”
- **Qualified headlines:**
  - `hidden_center`: “Your pool is wider than it first looks—but it has a center.”
  - `names_wide_jobs_narrow`: “Your hero names cover more ground than the jobs behind them.”
  - `names_narrow_jobs_wide`: “A compact hero set covers a wider mix of jobs.”
  - `names_changed_jobs_held`: “Your hero names moved more across the year than the jobs they covered.”
- **Evidence line:** “Hero shares, stable core, mapped-job mass, and chronological pool movement.”
- **Neutral:** “No single pool shape separated cleanly.”
- **Insufficient:** “Not enough stable pool history to call the shape.”
- **Mixed:** “Your pool has two valid layers: the names move, while the jobs hold.”

### Transfer

- **Question:** “What survives when the hero changes?”
- **Qualified headlines:**
  - `clean_transfer`: “More of your observed expression travels when the hero changes.”
  - `results_stop_first`: “The result changes before your expression does.”
  - `expression_stops_first`: “Your expression changes before the result does.”
  - `involvement_boundary`: “Involvement holds farther into the hero change.”
  - `exposure_boundary`: “Death exposure holds farther into the hero change.”
  - `localized_function_bottleneck`: “The supported gap sits in one mapped job context.”
- **Evidence line:** “Familiar and stretch contexts are compared through cross-fitted distance bands.”
- **Neutral:** “The supported comparison does not separate familiar and stretch contexts.”
- **Insufficient:** “Not enough comparable familiar and stretch matches to call transfer.”
- **Mixed:** “Your answer changes by signal: one part travels, another does not.”

### Post-Loss Response

- **Question:** “What do you pick after a loss?”
- **Qualified headlines:**
  - `one_loss_runback`: “After one loss, your next choice stays closer to your prior path.”
  - `two_loss_switch`: “After two or more losses, your next choice changes differently.”
  - `result_shaped_pool`: “Your next choice moves differently after wins and losses.”
  - `result_invariant_response`: “Your next-choice movement stays about the same after wins and losses.”
  - `adjustment_without_recovery`: “Your next choice changes after the result, while the next result stays unresolved.”
- **Evidence line:** “Same-session transitions grouped by win, one loss, two-plus losses, and win streak.”
- **Neutral:** “No single result state separated your next-choice movement.”
- **Insufficient:** “Not enough same-session transitions to call a post-loss pattern.”
- **Mixed:** “The one-loss and two-plus-loss states do not tell the same story.”

### Combat Expression

- **Question:** “What does your game look like once the horn sounds?”
- **Qualified headlines:**
  - `involvement_holds_exposure_moves`: “Involvement holds while death exposure moves.”
  - `exposure_holds_involvement_moves`: “Death exposure holds while involvement moves.”
  - `same_expression_different_results`: “Similar summary expression can arrive with different results.”
  - `different_expression_same_results`: “Similar results can arrive with different summary expression.”
  - `localized_variance`: “More of the expression variance sits in one supported context.”
- **Evidence line:** “Involvement, finishing, and death exposure are shown as separate covered summary signals.”
- **Neutral:** “Involvement and death exposure stay compatible in the supported comparison.”
- **Insufficient:** “Not enough context-resolved matches to call combat expression.”
- **Mixed:** “It depends on the signal: involvement and exposure do not move together.”

### Session Drift

- **Question:** “What changes later in a session?”
- **Qualified headlines:**
  - `opening_game_signature`: “Game 1 has a different supported shape from later games.”
  - `gradual_session_drift`: “A covered part of your expression moves as the session continues.”
  - `predeclared_breakpoint`: “The first clear break appears at the registered session position.”
  - `selection_only_drift`: “Your pool changes across a session while summary expression stays compatible.”
  - `bounded_stopping_response`: “Completed session endings differ after the registered result state.”
- **Evidence line:** “Completed sessions and direct positions G1 through G5+; censored endings remain noted.”
- **Neutral:** “Your covered expression stays compatible across completed session positions.”
- **Insufficient:** “Not enough completed sessions to call a session pattern.”
- **Mixed:** “The session story changes by what you measure.”

## 9. Signature rules

### Title rule

Use the exact public title `Your Dota Signature`. The internal contract may
retain `Dota DNA Signature` as a stable key, but the UI must not substitute a
fixed player type, class, grade, “superpower,” or psychological label.

### Descriptor rule

Render only server-supplied `PRIMARY`, `TWIST`, and `ANCHOR` slot text. The
descriptor line has this order:

1. PRIMARY text and scope `This year` when present;
2. TWIST text and its server-supplied scope when present;
3. ANCHOR text with `Observed annual core` when present.

If a slot is absent, omit it; do not fill the gap with a generic player type or a
hero ID. ANCHOR must use a reviewed human hero/common-thread label. The
presentation layer may shorten a slot for visual fit only by removing a
non-semantic leading phrase; it may not rewrite its meaning.

### Interpretation rule

Use: “A name for the supported pattern—not a fixed player type.” Follow with
the `Why this signature?` evidence map. Do not use “because”; list the
observed Elements, qualified finding, and hero anchor instead.

### Evidence map

The Signature evidence map contains exactly three groups when available:

- **Signals:** selected Element labels and zones with evidence refs;
- **Twist:** the first published moderate/high-confidence finding with its
  semantic key and alternatives;
- **Anchor:** human hero/common-thread label bound to
  `supporting:portfolio_shape`.

### Share rule

The Signature can be the identity share card only when the server marks the
identity candidate eligible. Self-estimates, descriptive-only identity,
recommendations, raw values, and unavailable slots never become share copy.

## 10. Interaction and accessibility content

- Every reveal is keyboard reachable and has a visible focus state.
- Every visual relationship has a table or disclosure containing the same
  labels and values.
- Range scrubbing has labeled marks and an `aria-valuetext` equivalent.
- Reduced motion removes scan/transition effects but keeps all content and
  gates.
- At 200% zoom and narrow mobile, the headline remains readable without
  horizontal scrolling; evidence can stack below Story.
- Color is never the only state cue; use text such as `qualified`, `neutral`,
  `not enough signal`, or `not available` in the appropriate depth.
- Empty and unavailable states remain calm content, not error red; an API
  failure is the only state that uses an error treatment.
- The self-estimate is visibly labeled `Your read` and is never visually
  merged with `Observed shape`.
- Analytics may record page/family/interaction/status keys but not account ID,
  report ID, player name, identity text, outcome direction, zone, raw match ID,
  access token, or protected cohort reference.

### Required alternative states

- **Neutral:** A sequence that barely changes is shown as deliberate stability;
  use the registered neutral sentence and do not add decorative drama.
- **Insufficient:** Use “Not enough signal to call this one.” plus the factual
  missing denominator or coverage reason. The visual stays incomplete, not
  broken or error-red.
- **Mixed/context-dependent:** Show the two valid components or paths together;
  never average them into a middle label.
- **Narrow pool:** Use fewer, larger, deeper samples and state that the pool is
  narrow without inferring intent.
- **Broad pool:** Use aggregation and clusters rather than dozens of tiny hero
  images.
- **No fixed player type:** Keep the collectible `Dota Signature` grounded in
  descriptors and evidence, with no fabricated label.
- **Reduced motion:** Replace morph with crossfade, movement with before/after,
  progressive drawing with stepped reveal, and animated chronology with
  discrete frames.

## 11. Implementation boundary

The next implementation batch may change only:

- web composition, copy placement, visual hierarchy, disclosure behavior,
  accessibility labels, and share controls;
- V6.1 copy catalog/presentation strings after source-binding review;
- story/page/share presentation payloads that already bind to existing fields.

It must not change:

- the seven Element definitions or estimators;
- the five family roots, 28 outcome registry, denominators, or qualification;
- thresholds, baselines, bootstrap, calibration, holdout evidence, or model;
- the strict V6.1 schema or one-request summary boundary;
- the protected Deep cohort format;
- any V5.2 or V6.0 snapshot behavior.
