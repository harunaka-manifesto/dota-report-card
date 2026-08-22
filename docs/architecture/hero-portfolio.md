# Hero Portfolio

Hero Portfolio is an independent summary-history layer. It asks four human
questions about the established hero pool; it does not reuse a Pattern score,
assign a global player label, or infer personality. The current portfolio
version is `hero-portfolio-1.2.0` plus the versioned
`hero-portfolio-config-1.0.0`; Hero Mirror is `hero-mirror-1.2.0`.

## Shared input and eligibility

All four insights start from the bounded normalized summary matches. The
shared eligibility record tracks hero match count, pool share, recency,
taxonomy coverage, and per-insight inclusion. Common Thread and Exception
require usable taxonomy, at least a 3% pool share, recency or sustained use,
and their sample gates. Mirror has its own metric gate and deliberately does
not require taxonomy coverage. A tiny or stale hero cannot win merely because
it is unusual.

Public unavailable/no-clear states are first-class results. The API returns the
reason and limitations rather than manufacturing an answer. Choice options are
deterministically pseudo-shuffled from a seed built from report facts; raw
match IDs are never used as an analytics or UI seed.

Generated hero knowledge is an additional build-time input seam, not a runtime
network dependency. Portfolio behavior continues to use the reviewed taxonomy
until the versioned ten-hero knowledge pilot has passed manual review. When it
is adopted, the report fingerprint must record the knowledge version alongside
the existing taxonomy and relationship versions.

## Common Thread

### Question

“What keeps showing up across your established heroes?” The user chooses one
functional trait and then compares the guess with the evidence-backed result.

### Input and algorithm

Taxonomy trait values are aggregated across eligible heroes. Each hero’s match
weight is capped at 35% of total eligible usage (with a floor of 3 weighted
matches), so one heavily sampled hero cannot dominate. Each trait combines
weighted coverage (70%) and the share of eligible heroes carrying the trait
(30%).

The winner must have weighted coverage at least `0.35` and beat the runner-up
by at least `0.03`. Confidence combines winner value, established-hero count,
and the margin. A result with fewer than three eligible taxonomy-covered heroes
or no dominant winner is unavailable. The output includes the winner,
secondary traits, weighted coverage, hero count, denominator, confidence, four
plausible options, and per-option feedback.

### Interaction and copy states

The question starts unanswered and its Reveal control is disabled. Choices are
radio semantics with `aria-checked`; selecting one does not mutate the report.
Reveal is a one-way, live-announced comparison. Correct and incorrect choices
receive contextual catalog copy. “This describes what the heroes tend to offer;
it does not prove those tools were used correctly in every match” is the
boundary copy.

### Tests that protect it

Protect the dominant trait, 35% hero-weight cap, tiny-hero exclusion,
insufficient taxonomy coverage, ambiguous winner, four options, deterministic
ordering, correct-position variation, contextual wrong feedback, and no raw
match identifiers in the seed or public output.

## Exception

### Question

“Which hero gives your pool a different kind of Dota?” Different is explicitly
not better or worse.

### Input and algorithm

At least four eligible taxonomy-covered heroes are required. Each hero is
represented by the versioned taxonomy trait vector. For each candidate, the
candidate is excluded from the comparison centroid; the Euclidean distance of
that candidate to the remaining pool centroid is its outlier score. The winner
needs distance at least `0.32` and a runner-up margin of at least `0.06`.

Confidence combines winner sample size, distance, and margin. The result
contains pool traits, exception traits, distance, margin, confidence, and
exactly four options when a clear winner exists: the winner plus three
nearest-to-pool distractors. A no-clear result is not a quiz. Its public
payload keeps only the bounded `no_clear_exception` answer for compatibility,
and the story immediately presents “Your pool has no odd one out.” Fewer than
four eligible heroes is unavailable.

### Interaction and copy states

When a clear outlier exists, the question is unanswered until a radio option
is selected and correct/wrong choices receive catalog feedback. When no hero
clears the distance and margin gates, the client renders the catalog-owned
no-outlier insight without radio options or Reveal. The result says that a hero
breaks the pool’s functional shape more clearly, not that the player is that
hero.

### Tests that protect it

Protect clear outlier, distance and margin floors, runner-up margin, no-clear
as an immediate insight, tiny-hero exclusion, taxonomy failure, win-rate
irrelevance, deterministic unbiased option position, exact option count, and
contextual wrong feedback.

## Pool Evolution

### Question

“How do you think your hero pool has changed recently?” This is a self-
assessment, not a score. The user chooses a description before the computed
read is revealed once, immediately in the same story page.

### Input, windows, and algorithm

Only chronologically usable matches with a hero ID participate. The method
requires at least 24 usable rows, then takes two equal-size windows: the
immediately preceding window and the most recent window, capped at 24 rows
each. It does not compare an arbitrary long “earlier history” with a short
recent slice.

Each window reports its own taxonomy coverage and must reach the `0.80` gate.
Hero distribution shift and taxonomy-toolkit distribution shift are measured
with normalized Jensen–Shannon distance. The named thresholds are:

| Constant | Value |
|---|---:|
| Minimum window size | 12 |
| Maximum window size | 24 |
| Taxonomy coverage per window | 0.80 |
| Hero shift | 0.22 |
| Toolkit shift | 0.18 |
| Stable-core top-trait overlap | 0.35 |

The four variants are `new_heroes_new_toolkit`, `new_heroes_same_toolkit`,
`stable_core_new_branch`, and `broadly_stable`. Patch/time changes add a
limitation and reduce confidence by a `0.72` penalty. The result exposes both
window sample sizes and both coverage values, so “balanced windows” is an
auditable claim rather than copy.

### Availability and interaction

Insufficient total history, an undersized earlier/recent window, or taxonomy
coverage below 80% in either window yields unavailable. The question choices
are not scored and do not change the computed result. The reveal page is
locked on direct scroll until the self-assessment is answered and the Reveal
control is activated. Reduced motion removes the visual transition but not the
gate.

### Copy and tests

Human variant copy includes “New heroes. Same taste.”, “Your pool changed
direction…”, “Your pool is growing a new branch…”, and “More stable than it
feels.” The tests protect equal chronological windows, all four variants,
insufficient total/side history, per-window taxonomy coverage, patch warning,
determinism, and the rule that a one-off hero cannot dominate the distribution
shift.

## Hero Mirror

### Question and boundary

Hero Mirror asks which sufficiently sampled hero most resembles the player’s
observable way of participating in matches. Preferred copy is:

> Of the heroes you've played enough for us to trust, {hero} is where your
> usual Dota shows up most clearly.

The qualifier is “Not your best hero. Not necessarily your most played.” The
guardrail is “This is not a personality test. We're not saying you are {hero}.
We're saying your games on {hero} most closely resemble the way you usually
play Dota.”

### Shared behavior units

Player and candidate references use the same four components from
`hero_portfolio.behavior`:

| Component | Unit / label basis | Similarity scale |
|---|---|---:|
| Involvement | `(kills + assists) / match minutes`, events per minute | 0.35 |
| Finishing | `kills / (kills + assists)`, kill share | 0.20 |
| Deaths | `deaths / match minutes × 10`, deaths per 10 minutes | 0.75 |
| Role context | role distribution total variation | 1.00 |

Role distribution is one component, not seven independent dimensions. Missing
role context reduces dimension coverage; it never invents a dominant role.
Public labels use realistic zones: Quiet–Everywhere, Setup–Cleanup, and
Elusive–Frequent.

### Eligibility and scoring

Mirror eligibility requires at least four hero matches, a 3% pool share,
recency or sustained use, and valid summary metrics in at least 75% of that
hero’s rows. Valid rows require a duration of at least ten minutes plus
non-negative kills, deaths, and assists. Taxonomy is used only for names and
context; a taxonomy failure does not make behavior ineligible.

For each candidate, candidate matches are excluded from the independent
reference when possible. If fewer than 12 independent reference rows exist, a
capped fallback adds at most half the candidate sample, with a minimum of
three, and applies a `0.82` uncertainty penalty. Candidate behavior is shrunk
toward the reference with observed weight `min(1, sample / 20)`. Similarity is
the weighted exponential distance across the available components. A result
must clear:

- sample confidence `0.35`;
- dimension coverage `0.75`;
- final score `0.55`; and
- runner-up margin `0.04`.

Tiny samples therefore cannot win, a 100% win rate has no scoring path, and
candidate exclusion plus shrinkage prevent self-reference from masquerading as
similarity. If no candidate clears the gates, the public state is
`no_clear_mirror`; if no metric-eligible candidate exists, it is unavailable.

### Interaction and tests

The Mirror is closed on entry. The button, Enter/Space keyboard interaction,
and horizontal pointer/touch drag all open the same reveal. Drag requires a
horizontal movement of at least 35% of the card width; vertical movement is
left to native page scrolling. Completion is announced in a live region and is
tracked once. Reduced motion removes the cover transition but keeps button and
keyboard behavior.

Protect tiny-sample exclusion, win-rate irrelevance, candidate-excluded and
capped fallback references, shrinkage, runner-up margin, no-clear state,
taxonomy-independent eligibility, four-component unit goldens, one-component
role treatment, missing-role coverage, deterministic winner, and realistic
labels.
