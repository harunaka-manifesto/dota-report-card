# Free DNA Model Guide

This is the human-readable guide to the behavioral model behind the Free Dota
Report Card. It explains every active Element, Pattern, and context Archetype:
what it notices, what information it is derived from, how it is structured,
what a result means, what it cannot mean, and where it travels next.

The short version is:

**summary observations → Elements → Patterns → context Archetypes → Findings**

The existing [model catalog](model-catalog.md) remains useful as a compact,
generated registry reference. This document is the companion for people who
want the whole picture without opening the implementation.

## 1. What the model is

The model is a layered way to describe recurring match behavior without
pretending that a bounded match history can reveal a player’s private motives
or personality.

| Layer | Plain-English definition | The question it answers | What it does not do |
| --- | --- | --- | --- |
| Observation | A recorded fact from a match or session | What happened? | It does not interpret the fact. |
| Element | One narrow, measurable behavioral tendency | What recurring signal is visible? | It does not summarize the whole player. |
| Pattern | A reviewed relationship between Elements | What becomes interesting when two or more signals meet? | It does not invent a cause. |
| Context Archetype | A local label inside one named group | Which recognizable style is closest in this context? | It is not one global personality verdict. |
| Finding | A player-facing story selected from upstream results | What is worth telling the player first? | It does not recalculate the evidence. |

An Element can use several low-level measurements internally, but it resolves
to one human idea. A Pattern always depends on upstream Elements. An Archetype
classifies those semantic results inside its own group. A Finding chooses and
phrases what survived those gates.

## 2. Where it is derived from

There are three different kinds of source here, and they should not be mixed
up.

### The design source

The attached implementation plan is a design and implementation instruction.
It defines the intended ontology, evidence boundary, naming rules, review gates,
and documentation requirements. It is not itself a live player result.

### The active product source

The shipped behavior model is defined by the active registries and summary-only
scorers. The human-readable explanation in this guide is derived from those
current definitions and their tests. The generated [model catalog](model-catalog.md)
is checked against the registries by the documentation checks.

### The data source

Free mode uses one bounded public summary-history read. Depending on the
Element, that history can provide:

- hero choices and match chronology;
- wins, losses, kills, deaths, assists, and match duration;
- credible role-context hints when the summary fields support them;
- inferred sessions from timestamps and gaps between matches;
- a versioned hero taxonomy for broad toolkit groupings.

Free mode does not read individual match-detail records and does not request
replay parsing. That boundary is part of the meaning of every active result.

The future Deep path can add selected match-detail or parsed-replay evidence,
but it is a separate, explicitly budgeted path. It is not silently present in
the Free score.

## 3. How to read a result

### The axis matters more than the number

Every active Element has a named axis. The left side and right side are two
descriptions of the same observable behavior. A score near the left end means
the left description is more visible; a score near the right end means the
right description is more visible. A score near the middle means the history
does not lean strongly either way.

These are normalized positions, not population percentiles. A high value is
not automatically good, and a low value is not automatically bad. “Higher”
means “more of the right-hand description.”

### Evidence status

- **Available** means the Element cleared its minimum sample and coverage gates.
- **Limited** means a score exists, but the evidence is thinner or less stable.
- **Unavailable** means the required evidence is not there. It is not quietly
  turned into a neutral middle score.

Confidence is separate from direction. A result can point clearly to one side
and still have limited confidence if the sample is small, coverage is uneven,
or the comparison is sensitive to the session window.

### What every result carries

Each result has a score position, an evidence count, coverage, confidence,
stability or quality signals, readable receipts, and named confounders. A
receipt says what comparison was actually made. A confounder says what else
could have shaped that comparison.

### How Patterns and Archetypes fail safely

A Pattern needs every required Element and requires the required Elements to
clear the confidence gate. If a required Element is missing or too weak, the
Pattern is suppressed or unavailable.

An Archetype group needs enough reliable Elements to make a local comparison.
If the evidence is too thin, it returns **Still taking shape**. If the leading
prototype and runner-up are too close, it also stays unclassified instead of
forcing a label.

## 4. Dimensions: the organizing map

Dimensions group related Elements. They are organizational domains, not
automatic personality scores. There is no single “Hero Identity score” that
pretends to summarize every hero-related signal.

| Dimension | Status | What belongs here |
| --- | --- | --- |
| Hero Identity | Free active | Hero selection, familiarity, exploration, and the toolkit underneath picks. |
| Role Identity | Free active | Concentration and movement in credible role-context hints. |
| Combat Expression | Free active | Kill involvement and how kills and assists are distributed. |
| Economy | Planned Deep | Farming, item timing, and resource conversion. |
| Map & Objectives | Planned Deep | Objective pressure, vision, movement, and map conversion. |
| Risk & Survival | Free active | Death exposure and the limited survival context visible in summary data. |
| Adaptability | Free active | Whether activity and observable performance travel across contexts. |
| Consistency & Form | Free active | Variation and recent movement in observable performance and activity. |
| Session Response | Free active | Session shape and what changes as a session continues or follows a result. |
| Progression | Planned extension | Longer change-over-time comparisons beyond this bounded report. |

Role Identity is active as a dimension and as Elements, but the current Free
model does not force a separate Role Identity Archetype group. That is an
intentional distinction: a dimension can organize useful measurements without
needing a label set of its own.

## 5. The 23 active Free Elements

All Elements in this section are **Free · Active** and use the
`summary_history` evidence tier. The catalog IDs are stable documentation
labels; the display names are the language intended for people.

### E01 — Hero Pool Breadth

**Definition:** Whether hero picks are concentrated in a small pool or spread
across a wider pool.

**Derived from:** Hero choices in the bounded history. The calculation combines
the share held by the most-picked heroes, how evenly picks are distributed, and
the effective number of heroes used. It is not just a count of unique heroes.

**Structure:** **Specialized → Broad.** It needs at least 30 matches with a
usable hero choice.

**What it means:** A lower result says a smaller group of heroes carries more
of the observed selection. A higher result says the selection is more spread
out. Neither position says whether the player is better or worse.

**Why it exists:** Hero breadth is the foundation for separating a specialist,
an explorer, and several useful “the names changed, the toolkit did not”
relationships.

**Used by:** Broad Pool, Narrow Toolkit; Broad Pool, Narrow Safety Zone;
Specialist, Transferable Style; Role Anchor, Hero Explorer; Hero Anchor, Role
Flex; and the Hero Identity Archetype group.

**Limits:** Patch changes, hero availability, queue context, and the bounded
history window can all change the visible pool. A broad pool is not proof of
adaptability, and a narrow pool is not proof of limitation.

### E02 — Hero Pool Stability

**Definition:** How similar the player’s hero distribution is across earlier
and later parts of the observed history.

**Derived from:** Dated hero choices split into earlier and later windows. The
two distributions are compared for similarity, with window-sensitivity checks
when enough history exists.

**Structure:** **Changing → Stable.** It needs at least 60 dated hero rows so
there is a meaningful earlier-versus-later comparison.

**What it means:** A higher result means the player returns to a similar mix of
heroes over time. A lower result means the distribution moved more between the
windows.

**Why it exists:** It prevents a recent change in results from being mistaken
for a complete change in selection identity. It is also part of the distinction
between Explorer and Free Agent.

**Used by:** Form Changed, Style Didn’t; and the Hero Identity Archetype group.

**Limits:** A low result is not “inconsistent” or “indecisive.” Patches, new
heroes, role changes, and the chosen history window can all move the
distribution.

### E03 — Hero Exploration

**Definition:** How often later picks fall outside a hero pool established by
earlier history.

**Derived from:** The first part of the dated history establishes familiar
heroes. The later evaluation window is then checked for picks outside that
earlier pool. The later outcomes do not define familiarity.

**Structure:** **Familiar picks → Exploratory picks.** It needs at least 60
dated rows, including a usable later evaluation window.

**What it means:** A higher result means leaving the earlier pool is a visible
part of selection. A lower result means later picks more often return to the
established pool.

**Why it exists:** It distinguishes a player who has a broad pool from a player
who is actively exploring, without treating exploration as a virtue or a flaw.

**Used by:** It helps distinguish the Hero Identity prototypes and is an
optional supporting signal for Signature Strength With a Tax.

**Limits:** A short recent window can make exploration look unusually large.
The result describes pick movement; it does not establish why a hero was
chosen.

### E04 — Toolkit Breadth

**Definition:** Whether the player’s heroes ask for a narrow recurring toolkit
or for a wider mix of tools.

**Derived from:** Each picked hero is looked up in the versioned hero taxonomy.
The strongest taxonomy traits are combined into a stable toolkit signature,
and the distribution of those signatures is measured for breadth. This is why
hero count and toolkit count can tell different stories.

**Structure:** **Narrow toolkit → Diverse toolkit.** It needs at least 30
taxonomy-covered hero rows and at least 80% taxonomy coverage.

**What it means:** A lower result means many heroes resolve to similar
toolkits. A higher result means the selected heroes represent a wider set of
toolkits.

**Why it exists:** It catches the useful contradiction where the hero list is
large but the underlying way of playing is more concentrated.

**Used by:** Broad Pool, Narrow Toolkit; and the Craftsman and Adapter shapes
inside the Hero Identity group.

**Limits:** The taxonomy is editorial and versioned. It is a useful grouping
tool, not an objective statement that two heroes are identical.

### E05 — Signature Dependence

**Definition:** How much the observable performance proxy holds up on an
established hero pool compared with later off-pool matches.

**Derived from:** An earlier history window establishes familiar heroes. In the
later evaluation window, familiar and off-pool matches are compared using the
existing summary-level performance proxy.

**Structure:** **Little dependence → High dependence.** The comparison needs
roughly 15 usable familiar matches and 15 usable comparison matches; the
registry’s minimum sample is 30.

**What it means:** A higher result means the familiar pool carries a stronger
performance edge over the off-pool comparison. A lower result means the
performance proxy travels more evenly.

**Why it exists:** It lets the report say “this strength has a boundary” while
keeping the strength visible. High dependence is not automatically a flaw.

**Used by:** Signature Strength With a Tax; optionally Broad Pool, Narrow Safety
Zone; and the Specialist, Craftsman, and Free Agent prototype comparisons.

**Limits:** Hero learning, patches, role mix, draft quality, and the split
between earlier and later windows can all shape the difference. It is not a
test of comfort, confidence, or willingness.

### E06 — Post-Loss Familiarity Shift

**Definition:** Whether the next hero becomes more familiar after a loss than
after a win.

**Derived from:** Valid within-session transitions. For each next match, the
earlier hero history defines a familiar set, then the next pick is compared
after a previous loss and after a previous win.

**Structure:** **Explores after losses → Returns to familiarity after losses.**
It needs at least 15 valid post-loss and 15 valid post-win transitions, with a
registry minimum sample of 30.

**What it means:** A higher result means the next pick more often returns to
the established pool after a loss. A lower result means the next pick is more
often outside that pool after a loss.

**Why it exists:** It captures selection response without smuggling in a
mental-state explanation.

**Used by:** Losses Change Picks More Than Pace; Losses Change Pace More Than
Picks; optionally Broad Pool, Narrow Safety Zone; and the Session Style group’s
supporting context.

**Limits:** Session gaps, stopping behavior, parties, and which transitions
remain observable affect the comparison. It does not measure fear, tilt,
trust, anger, or confidence.

### E07 — Role Breadth

**Definition:** How concentrated the player’s credible role-context hints are.

**Derived from:** Summary lane or role fields after the existing confidence
normalization. The result combines the share held by the dominant hint and the
spread across hints.

**Structure:** **Role-anchored → Role-flexible.** It needs at least 30 credible
role rows and at least 40% role coverage.

**What it means:** A lower result means one role context appears more often. A
higher result means the credible hints cover more contexts.

**Why it exists:** It separates hero identity from role context. A player can
change heroes while staying role-anchored, or keep a narrower hero pool while
moving across role contexts.

**Used by:** Role Anchor, Hero Explorer and Hero Anchor, Role Flex.

**Limits:** These are summary role hints, not parsed positions. Missing hints
reduce coverage, and a role hint cannot establish initiation, support duties,
or a precise Dota position.

### E08 — Role Switching

**Definition:** How often the credible role context changes between adjacent
games.

**Derived from:** Dated, role-eligible adjacent pairs, preferably inside a
session when the session information is available. A transition counts when
the two role hints differ.

**Structure:** **Usually same context → Frequently switches context.** It needs
at least 20 valid role transitions.

**What it means:** A higher result means role-context changes are common in the
observed transitions. A lower result means adjacent contexts more often match.

**Why it exists:** Role breadth says how spread the overall distribution is;
Role Switching says how often the context changes from one game to the next.

**Used by:** It is an active Role Identity Element. No current Free Pattern or
Archetype prototype consumes it; it remains available for future reviewed
relationships.

**Limits:** Missing role hints disappear from the transition denominator.
Summary hints also cannot tell us whether the player deliberately changed
position or simply received a noisy label.

### E09 — Combat Involvement

**Definition:** How frequently the player is involved in kills relative to time
played.

**Derived from:** Kills plus assists per minute for eligible matches. When
enough credible role hints exist, the result is compared with a provisional
role baseline; otherwise it stays more self-relative and its confidence is
limited.

**Structure:** **Lower involvement → Higher involvement.** It needs at least
30 matches with usable kills, assists, and duration.

**What it means:** A higher result means more kill-event involvement per unit
of time. A lower result means less visible involvement relative to time.

**Why it exists:** It gives the combat Archetype group a participation signal
that is separate from finishing kills and separate from deaths.

**Used by:** High Involvement, Controlled Exposure; High Involvement, High
Exposure; Selective Finisher; and every Combat Expression Archetype comparison.

**Limits:** Team tempo and hero style affect involvement rate. Summary K/D/A
cannot identify who initiated a fight, arrived first, controlled a target, or
converted an objective.

### E10 — Finisher Orientation

**Definition:** The split between kills and assists when the player is involved
in kill events.

**Derived from:** Kills divided by kills plus assists, with a provisional role
expectation and shrinkage when enough credible role rows exist.

**Structure:** **Assist-oriented → Kill-oriented.** It needs at least 30 matches
and at least 100 total involvement events.

**What it means:** A higher result means a larger share of the player’s
involvement is recorded as kills. A lower result means assists make up more of
the involvement.

**Why it exists:** It describes event distribution without turning a kill share
into a story about character.

**Used by:** Selective Finisher and all Combat Expression Archetype
comparisons.

**Limits:** Team kill totals, role mix, and the situation around each event are
only partly visible. It does not mean selfishness, leadership, playmaking, or
kill stealing.

### E11 — Death Exposure

**Definition:** How frequently the player dies relative to time played and the
role context visible in the summary.

**Derived from:** Deaths per ten minutes for eligible matches. With enough
credible role hints, the result uses a provisional role reference; otherwise it
uses a broader bounded reference and keeps the language cautious.

**Structure:** **Lower exposure → Higher exposure.** It needs at least 30
matches with usable deaths and duration.

**What it means:** A higher result means more deaths per unit of time in the
observed history. A lower result means lower death exposure.

**Why it exists:** It keeps the cost side of combat participation visible. A
player can be highly involved and controlled, or highly involved and highly
exposed; one number should not hide the trade-off.

**Used by:** High Involvement, Controlled Exposure; High Involvement, High
Exposure; Selective Finisher; and every Combat Expression Archetype comparison.

**Limits:** Some heroes and roles structurally trade deaths for map value.
Summary data cannot tell us the cost of a particular death or whether it
protected an objective.

### E12 — Off-Pool Performance

**Definition:** How well the observable performance proxy transfers away from
the established hero pool.

**Derived from:** An earlier window establishes familiar heroes. A later
evaluation window compares familiar-pool and off-pool matches. The split is
chronological so future outcomes do not define past familiarity.

**Structure:** **Drops off-pool → Travels off-pool.** It needs at least 40
usable evaluation observations, with roughly 20 in each comparison cell.

**What it means:** A higher result means the performance proxy stays closer or
improves off-pool. A lower result means the familiar-pool comparison is
stronger.

**Why it exists:** It separates hero range from transfer. The player may pick
widely, but the result signal may or may not travel with that range.

**Used by:** Broad Pool, Narrow Safety Zone; Signature Strength With a Tax;
Activity Travels Better Than Results; optionally Specialist, Transferable
Style; and the Hero Identity group’s Adapter comparison.

**Limits:** Patch, draft quality, role mix, and hero learning can differ
between the two windows. This is a summary performance proxy, not a complete
skill rating.

### E13 — Off-Pool Activity Stability

**Definition:** Whether combat involvement stays similar when the player leaves
the familiar hero pool.

**Derived from:** The same chronological familiar/off-pool split used for
Off-Pool Performance, but comparing kills plus assists per minute. The score
rewards a small difference while keeping the signed difference in the private
receipt.

**Structure:** **Activity changes off-pool → Activity travels off-pool.** It
needs at least 24 usable observations, with roughly 12 in each cell.

**What it means:** A higher result means the visible activity rate travels
well. A lower result means activity changes more when the hero context changes.

**Why it exists:** It lets the model distinguish “you stop showing up” from
“you show up, but the result conversion falls.” That distinction is the heart
of Activity Travels Better Than Results.

**Used by:** Specialist, Transferable Style and Activity Travels Better Than
Results.

**Limits:** Role and team tempo can change with hero choice. Stable activity is
not proof that mechanics, timings, or teamfight decisions are identical.

### E14 — Off-Role Performance

**Definition:** How well the observable performance proxy transfers outside
established role contexts.

**Derived from:** An earlier role history establishes familiar contexts. A
later evaluation window compares familiar-role and off-role matches, provided
credible role coverage is strong enough.

**Structure:** **Drops off-role → Travels off-role.** It needs at least 24
usable role-labeled observations and at least 50% role coverage, with roughly
12 observations in each comparison cell.

**What it means:** A higher result means performance travels more evenly beyond
the established role contexts. A lower result means the familiar contexts
carry a stronger performance signal.

**Why it exists:** It gives Adaptability a role-context counterpart to
Off-Pool Performance.

**Used by:** It is an active Adaptability Element. No current Free Pattern or
Archetype prototype consumes it; the summary role evidence is not yet strong
enough to support a larger reviewed relationship.

**Limits:** Summary role hints have a lower evidence ceiling than parsed
positions. Hero choice, draft, and the meaning of the hint can all change
between groups.

### E15 — Performance Volatility

**Definition:** How much the observable performance proxy varies from match to
match.

**Derived from:** Robust dispersion across per-match performance values. The
calculation uses a median-based spread so one extreme game does not decide the
whole result.

**Structure:** **Steadier → More variable.** It needs at least 30 usable
performance observations.

**What it means:** A higher result means the match-to-match proxy moves around
more. A lower result means the proxy is more tightly grouped.

**Why it exists:** It gives Consistency & Form a direct variation signal rather
than relying only on recent direction.

**Used by:** It is an active Consistency & Form Element. No current Free Pattern
or Archetype prototype consumes it.

**Limits:** The proxy is not a complete performance model. Matchups, teammates,
patches, duration, and role context can all contribute to variation.

### E16 — Recent Form Shift

**Definition:** Whether recent observable performance differs from the
preceding reference window.

**Derived from:** The most recent usable matches are compared with the earlier
reference window using robust center values. The direction is kept visible.

**Structure:** **Recent decline → Recent improvement.** The registry minimum is
45 usable observations, with the scorer using a recent window of about 20 and
the preceding window of about 40 when available.

**What it means:** A higher result means recent proxy performance improved
relative to the preceding window. A lower result means it declined. The middle
means no material movement cleared the comparison scale.

**Why it exists:** It lets the report talk about current form without
relabeling the player’s whole identity.

**Used by:** Form Changed, Style Didn’t.

**Limits:** Opponents, patches, hero mix, and role mix are not controlled. A
recent shift is a bounded comparison, not a permanent trend forecast.

### E17 — Recent Activity Shift

**Definition:** Whether combat involvement has changed recently.

**Derived from:** Recent versus preceding kills-plus-assists-per-minute values,
using the same time-aware comparison style as Recent Form Shift.

**Structure:** **Recently less involved → Recently more involved.** It needs at
least 45 usable activity observations.

**What it means:** A higher result means recent activity is higher than the
preceding window. A lower result means recent activity is lower.

**Why it exists:** Form can move while activity stays similar, or activity can
move while form stays similar. This Element keeps those possibilities apart.

**Used by:** Form Changed, Style Didn’t.

**Limits:** Team tempo and role mix can differ between windows. More activity is
not automatically better activity.

### E18 — Long-Game Performance Shift

**Definition:** Whether the observable performance proxy differs between long
and short games.

**Derived from:** Long matches of roughly 45 minutes or more are compared with
shorter matches of roughly 35 minutes or less, leaving the middle range out of
the initial contrast when possible.

**Structure:** **Falls in long games → Improves in long games.** It needs at
least 20 usable matches, with at least 10 in each comparison group.

**What it means:** A higher result means the proxy is stronger in long games.
A lower result means it is weaker in long games.

**Why it exists:** It makes duration context visible without calling a long
game a test of endurance by itself.

**Used by:** It is an active Consistency & Form Element. No current Free Pattern
or Archetype prototype consumes it.

**Limits:** Duration is shaped by both teams and by the game state. A long-game
comparison cannot establish why a match lasted longer.

### E19 — Session Length Tendency

**Definition:** Whether the player usually plays short bursts or longer runs of
matches.

**Derived from:** Inferred sessions built from match start times and gaps. It
combines typical matches per session, the share of sessions reaching five or
more games, and typical elapsed session duration.

**Structure:** **Short bursts → Long sessions.** It needs at least 25 dated
matches across at least 10 usable sessions.

**What it means:** A higher result means longer sessions are more common. A
lower result means the observed history is more burst-shaped.

**Why it exists:** Session shape is the context needed before late-session and
post-result changes can be read sensibly.

**Used by:** Long Session Tax; Marathon Stability; and every Session Style
Archetype comparison.

**Limits:** The history boundary can cut off the start or end of a real
session. A session length is a description of queue behavior, not a statement
about discipline.

### E20 — Late-Session Performance

**Definition:** Whether observable performance rises or falls as a session
continues.

**Derived from:** Independent multi-game sessions. Performance is compared
across session positions, especially game one versus game three and later,
using within-session slopes and session-window sensitivity.

**Structure:** **Declines later → Improves later.** It needs at least 12
independent multi-game sessions and enough early and late observations; the
registry minimum sample is 27.

**What it means:** A higher result means later positions in a session carry a
stronger proxy signal. A lower result means the later positions give some edge
back.

**Why it exists:** It turns “one more game” into a measurable context without
making the context a permanent label.

**Used by:** Long Session Tax; Marathon Stability; and the Session Style
Archetype group.

**Limits:** Players may stop after difficult or successful games. Role and hero
mix can change across session positions. The result is a within-history
association, not proof that fatigue caused the movement.

### E21 — Post-Loss Performance Response

**Definition:** How next-match observable performance differs after a loss
compared with after a win.

**Derived from:** Valid adjacent transitions inside sessions. The next match
after a win is compared with the next match after a loss using the summary
performance proxy.

**Structure:** **Lower after losses → Higher after losses.** It needs at least
15 post-win and 15 post-loss transitions.

**What it means:** A higher result means the next-match proxy is higher after
losses in the observed transitions. A lower result means it is lower.

**Why it exists:** It gives Session Response a result-based counterpart to
post-loss pick and activity changes.

**Used by:** It is optional support for Losses Change Picks More Than Pace and
the Reset Player prototype in Session Style.

**Limits:** Matchmaking, parties, stopping behavior, hero changes, and the
choice to queue again can all shape the next match. It does not measure
resilience, tilt, or emotional recovery.

### E22 — Post-Loss Activity Shift

**Definition:** Whether next-match combat involvement changes after a loss
compared with after a win.

**Derived from:** Valid within-session next-match transitions, comparing
kills-plus-assists per minute after the two preceding outcomes.

**Structure:** **Slower after losses → More active after losses.** It needs at
least 15 valid transitions in each comparison group.

**What it means:** A higher result means the next match is more active after a
loss. A lower result means it is less active.

**Why it exists:** It lets the model separate a selection response from an
activity response. That separation powers two different loss-related Patterns.

**Used by:** Losses Change Picks More Than Pace; Losses Change Pace More Than
Picks; and the Reset Player prototype as optional support.

**Limits:** The next role, hero, team tempo, and party context may differ. A
pace shift is observable; its reason is not.

### E23 — Post-Loss Death Exposure Shift

**Definition:** Whether next-match death exposure changes after a loss
compared with after a win.

**Derived from:** Valid within-session transitions, comparing deaths per unit
of time in the next match after the two preceding outcomes.

**Structure:** **Lower exposure after losses → Higher exposure after losses.** It
needs at least 15 valid transitions in each comparison group.

**What it means:** A higher result means next-match death exposure is higher
after losses. A lower result means it is lower.

**Why it exists:** It gives the model a separate exposure signal so a change in
post-loss activity is not mistaken for a change in cost.

**Used by:** It is optional support for High Involvement, High Exposure and
Losses Change Pace More Than Picks. It is also optional context for Session
Style.

**Limits:** Hero and role changes affect death exposure. The summary cannot say
whether a particular death was costly, necessary, or avoidable.

## 6. The 15 active Free Patterns

Patterns are a finite, reviewed set. The model does not test every possible
pair of Elements and then fish for a story. Each Pattern below has named
dependencies, a qualification shape, and a clear reason to exist.

In practical terms, “clearly high” usually means an Element is around 0.62 or
above on its right-hand axis. “Clearly low” usually means around 0.42 or below
on its left-hand axis. Middle-band rules are called out where they matter.
Those boundaries are versioned production gates, not universal laws of Dota.

All Patterns here are **Free · Active** and use summary-history evidence. A
qualified Pattern can produce a same-key editorial Finding, but story selection
may still choose only the strongest few for the report.

### P01 — Broad Pool, Narrow Toolkit

**Kind:** Identity

**Formed from:** [E01 Hero Pool Breadth](#e01--hero-pool-breadth) and [E04
Toolkit Breadth](#e04--toolkit-breadth). Both are required.

**Qualification:** Hero Pool Breadth is clearly broad while Toolkit Breadth is
clearly narrow.

**What it captures:** Many hero names resolve to a smaller set of recurring
tools.

**What it means:** The selection range is bigger than the underlying toolkit.
That can be useful versatility at the draft level with a more recognizable
mechanical or strategic through-line underneath.

**Why it matters:** It separates hero count from the playstyle repeated below
the hero count.

**What it does not prove:** It does not prove that the player is predictable,
one-dimensional, or unable to learn a new tool.

**Downstream:** It can support the Hero Identity group, especially the
Craftsman prototype. Its matching editorial Finding is “You play a lot of
heroes. Fewer game plans.”

### P02 — Broad Pool, Narrow Safety Zone

**Kind:** Contradiction

**Formed from:** [E01 Hero Pool Breadth](#e01--hero-pool-breadth) and [E12
Off-Pool Performance](#e12--off-pool-performance). Optional support comes from
[E06 Post-Loss Familiarity Shift](#e06--post-loss-familiarity-shift) and [E05
Signature Dependence](#e05--signature-dependence).

**Qualification:** The hero pool is clearly broad while off-pool performance is
clearly below the familiar-pool side.

**What it captures:** Selection range and performance range are not the same
size.

**What it means:** The player explores broadly, but familiar heroes carry the
stronger observable performance signal.

**Why it matters:** It keeps the strength and the boundary in the same frame.

**What it does not prove:** It does not prove fear, lack of confidence, or a
desire to avoid experimentation.

**Downstream:** It produces a matching editorial Finding. It does not directly
contribute a named Pattern to an Archetype group, although its Elements can
still influence the Hero Identity prototype comparison.

### P03 — Specialist, Transferable Style

**Kind:** Identity

**Formed from:** [E01 Hero Pool Breadth](#e01--hero-pool-breadth) and [E13
Off-Pool Activity Stability](#e13--off-pool-activity-stability). Optional
support comes from [E12 Off-Pool Performance](#e12--off-pool-performance).

**Qualification:** The hero pool is clearly narrow while off-pool activity
stability is clearly high.

**What it captures:** A narrow selection preference sits beside a similar
combat-activity shape outside that pool.

**What it means:** The small pool may be preference rather than a visible
activity limit.

**Why it matters:** It prevents a specialist label from quietly becoming a
deficit label.

**What it does not prove:** It does not prove equal performance, equal
decision quality, or mastery on every off-pool hero.

**Downstream:** It can support the Hero Identity group and its matching
editorial Finding.

### P04 — Role Anchor, Hero Explorer

**Kind:** Identity

**Formed from:** [E07 Role Breadth](#e07--role-breadth) and [E01 Hero Pool
Breadth](#e01--hero-pool-breadth).

**Qualification:** Role breadth is clearly anchored while hero breadth is
clearly broad.

**What it captures:** Hero choice varies while the credible role context stays
more concentrated.

**What it means:** The role context is the through-line; the hero names move
around it.

**Why it matters:** It answers whether identity looks more role-shaped than
hero-shaped in this history.

**What it does not prove:** It does not identify an exact position or establish
that the player consciously chose the role.

**Downstream:** It produces a matching editorial Finding. There is no current
Role Identity Archetype group, so it does not directly choose an Archetype.

### P05 — Hero Anchor, Role Flex

**Kind:** Identity

**Formed from:** [E01 Hero Pool Breadth](#e01--hero-pool-breadth) and [E07 Role
Breadth](#e07--role-breadth).

**Qualification:** Hero breadth is clearly narrow while role breadth is clearly
flexible, with enough role coverage to trust the contrast.

**What it captures:** A smaller hero pool appears across a wider range of
credible role contexts.

**What it means:** The hero identity stays close while the role context moves.

**Why it matters:** It keeps hero identity and role identity from being treated
as the same thing.

**What it does not prove:** It does not prove role mastery, position swapping,
or deliberate role experimentation.

**Downstream:** It produces a matching editorial Finding, but no current
Role Identity Archetype consumes it directly.

### P06 — Signature Strength With a Tax

**Kind:** Leak

**Formed from:** [E05 Signature Dependence](#e05--signature-dependence) and
[E12 Off-Pool Performance](#e12--off-pool-performance). Optional support comes
from [E03 Hero Exploration](#e03--hero-exploration).

**Qualification:** Familiar-pool dependence is clearly high while off-pool
performance is clearly lower.

**What it captures:** Established heroes are a real performance strength, and
leaving them carries a measurable cost.

**What it means:** The signature is doing useful work. The constraint is that
the same performance signal is not yet traveling as far outside it.

**Why it matters:** The report can name the strength first and the trade-off
second. That is more useful than calling the whole result a weakness.

**What it does not prove:** It does not prove that experimentation is bad or
that the player should stop trying new heroes.

**Downstream:** It produces a matching editorial Finding. Its Elements can
shape Hero Identity prototypes, but the Pattern itself is not a direct optional
Pattern for the current group classifier.

### P07 — Activity Travels Better Than Results

**Kind:** Contradiction

**Formed from:** [E13 Off-Pool Activity Stability](#e13--off-pool-activity-stability)
and [E12 Off-Pool Performance](#e12--off-pool-performance).

**Qualification:** Off-pool activity remains clearly stable while off-pool
performance is clearly below the familiar-pool comparison.

**What it captures:** The player keeps showing up at a similar activity rate,
but the result proxy does not travel as well.

**What it means:** The visible gap is more specific than “you stop
participating.” The missing mechanism is likely somewhere deeper than event
volume.

**Why it matters:** It creates a clean handoff to questions about laning,
timings, fight arrival, or conversion without claiming that summary history
already answered them.

**What it does not prove:** It does not identify the missing mechanism or prove
that activity is mechanically identical across heroes.

**Downstream:** It can support the Hero Identity group’s Adapter comparison and
produces a matching Finding. It also opens a Deep diagnostic hook:

- Does laning efficiency stay stable off-pool?
- Do item timings become more variable?
- Does teamfight arrival shift?

The Deep evidence families named by the Pattern are lane efficiency, item
timing reliability, and teamfight participation.

### P08 — High Involvement, Controlled Exposure

**Kind:** Style

**Formed from:** [E09 Combat Involvement](#e09--combat-involvement) and [E11
Death Exposure](#e11--death-exposure).

**Qualification:** Combat involvement is clearly high while death exposure is
clearly low.

**What it captures:** Frequent kill-event participation without a similarly
high death rate.

**What it means:** The player shows up often without paying for every arrival.

**Why it matters:** It keeps participation and exposure as separate signals.

**What it does not prove:** It does not establish aggression, initiation,
positioning quality, or objective conversion.

**Downstream:** It supports the Combat Expression group and especially the
Enabler or Skirmisher prototype comparisons. Its matching Finding can become a
Combat Expression story.

### P09 — High Involvement, High Exposure

**Kind:** Style

**Formed from:** [E09 Combat Involvement](#e09--combat-involvement) and [E11
Death Exposure](#e11--death-exposure). Optional support comes from [E23
Post-Loss Death Exposure Shift](#e23--post-loss-death-exposure-shift).

**Qualification:** Both involvement and death exposure are clearly high.

**What it captures:** Frequent participation arrives with frequent deaths per
unit of time.

**What it means:** The player is present in many events, and the exposure bill
is visible too.

**Why it matters:** It turns a vague “aggressive” impression into a measurable
participation/exposure trade-off.

**What it does not prove:** It does not say whether the deaths were badly
timed, strategically necessary, or worth an objective.

**Downstream:** It supports the Combat Expression group and can influence the
High Involvement, High Exposure or Balanced prototype comparison. It also opens
a Deep question: **Which fight timings carry the highest cost?** The named Deep
evidence families are death cost and teamfight participation.

### P10 — Selective Finisher

**Kind:** Style

**Formed from:** [E09 Combat Involvement](#e09--combat-involvement), [E10
Finisher Orientation](#e10--finisher-orientation), and [E11 Death
Exposure](#e11--death-exposure).

**Qualification:** Involvement is lower or moderate, finisher orientation is
clearly high, and death exposure is clearly controlled.

**What it captures:** Fewer visible events combine with a higher kill share and
lower exposure.

**What it means:** The player does not need to be present for every event to
end up with a meaningful finishing share.

**Why it matters:** It describes event distribution without turning it into a
motive story.

**What it does not prove:** It does not mean kill stealing, selfishness, or
that every kill was the right choice.

**Downstream:** It supports the Combat Expression group and its Selective
Finisher prototype. Its matching Finding can become a combat-style story.

### P11 — Losses Change Picks More Than Pace

**Kind:** Trajectory

**Formed from:** [E06 Post-Loss Familiarity Shift](#e06--post-loss-familiarity-shift)
and [E22 Post-Loss Activity Shift](#e22--post-loss-activity-shift). Optional
support comes from [E21 Post-Loss Performance Response](#e21--post-loss-performance-response).

**Qualification:** Familiarity moves clearly toward the established pool after
losses while activity stays near its middle band.

**What it captures:** Selection changes more than visible combat pace.

**What it means:** The next hero moves toward familiarity, but the activity
signal stays comparatively close.

**Why it matters:** It replaces unsafe language about trust or tilt with a
selection response that can actually be observed.

**What it does not prove:** It does not explain why the pick changes or what
the player feels after a loss.

**Downstream:** It supports the Session Style group’s optional pattern context,
especially the Reset Player comparison, and produces a matching Finding.

### P12 — Losses Change Pace More Than Picks

**Kind:** Trajectory

**Formed from:** [E06 Post-Loss Familiarity Shift](#e06--post-loss-familiarity-shift)
and [E22 Post-Loss Activity Shift](#e22--post-loss-activity-shift). Optional
support comes from [E23 Post-Loss Death Exposure Shift](#e23--post-loss-death-exposure-shift).

**Qualification:** Familiarity remains near its middle band while activity moves
clearly after losses.

**What it captures:** Activity changes more than hero familiarity.

**What it means:** The player’s next-game pace shifts while the hero choice
stays comparatively close to the established pool.

**Why it matters:** It separates selection response from activity response. Two
players can both queue again after losses and change very different things.

**What it does not prove:** It does not name the reason for the pace change or
claim that the next game was emotionally charged.

**Downstream:** It produces a matching Finding. It is not a direct optional
Pattern for the current Session Style classifier, though its Elements can
support that group.

### P13 — Long Session Tax

**Kind:** Leak

**Formed from:** [E19 Session Length Tendency](#e19--session-length-tendency)
and [E20 Late-Session Performance](#e20--late-session-performance). Optional
support comes from [E21 Post-Loss Performance Response](#e21--post-loss-performance-response).

**Qualification:** Long sessions are common while later-session performance is
clearly lower.

**What it captures:** The player often reaches the later games, but the edge
starts to leak there.

**What it means:** Game four or later is a useful context to test. It is not a
permanent label attached to every future session.

**Why it matters:** It turns session shape into a concrete stopping or opt-in
experiment.

**What it does not prove:** It does not prove fatigue, burnout, or a causal
effect of playing longer.

**Downstream:** It supports the Session Style group and especially the
Front-Loaded prototype. Its matching Finding can be the current experiment
story: make game four an explicit opt-in, then compare later-session results
with the earlier-session baseline.

### P14 — Marathon Stability

**Kind:** Edge

**Formed from:** [E19 Session Length Tendency](#e19--session-length-tendency)
and [E20 Late-Session Performance](#e20--late-session-performance).

**Qualification:** Long sessions are common while later-session performance
holds or improves.

**What it captures:** A long-session context without the late-session leak.

**What it means:** The available history shows the player’s observable edge
surviving farther into a session.

**Why it matters:** It is the strength counterpart to Long Session Tax. Long
sessions are not automatically a problem; the result depends on what happens
inside them.

**What it does not prove:** It does not prove endless stamina or guarantee that
the next long session will behave the same way.

**Downstream:** It supports the Session Style group and especially the Grinder
prototype. Its matching Finding can become the session-strength story.

### P15 — Form Changed, Style Didn’t

**Kind:** Trajectory

**Formed from:** [E16 Recent Form Shift](#e16--recent-form-shift), [E02 Hero Pool
Stability](#e02--hero-pool-stability), and [E17 Recent Activity Shift](#e17--recent-activity-shift).

**Qualification:** Recent performance moves materially, hero distribution stays
stable, and recent activity stays near its middle band.

**What it captures:** Current form changed more than selection identity or
visible combat activity.

**What it means:** The recent result signal moved through a familiar style.

**Why it matters:** It keeps current form separate from a claim that the
player’s identity or playstyle broke down.

**What it does not prove:** It does not establish a new permanent trend or
identify the opponents, patch changes, or matchups responsible.

**Downstream:** It produces a matching Finding. It is not a direct optional
Pattern for a current Archetype group.

## 7. The three context Archetype groups

An Archetype is a recognizable label inside one context, not a single verdict
about the whole player. The classifier compares a player’s reliable Element
shape with a finite set of local prototypes. It keeps the runner-up and the
margin so a close call can stay visible.

All current groups are **Free · Active**.

### How classification works

1. The group gathers only relevant Elements with enough confidence.
2. Each prototype describes an expected shape, such as broad hero use or
   assist-oriented involvement.
3. The closest supported prototype wins only if the required Elements are
   reliable.
4. A thin result or a near tie returns **Still taking shape** rather than a
   forced label.

The three groups can disagree without contradiction. A player can be an
Explorer in Hero Identity, an Enabler in Combat Expression, and a Sprinter in
Session Style. They answer different questions.

### Group A — Hero Identity

**Definition:** The shape of hero selection and the toolkit underneath it.

**Core Elements:** E01 Hero Pool Breadth, E02 Hero Pool Stability, and E03 Hero
Exploration. Toolkit Breadth, Signature Dependence, and Off-Pool Performance
can refine the comparison.

**Group gate:** At least three reliable relevant Elements, including the core
selection signals. A minimum confidence score of roughly the moderate gate is
required.

**Supporting Patterns:** Broad Pool, Narrow Toolkit; Specialist, Transferable
Style; Activity Travels Better Than Results.

#### A1 — Specialist

**Identity statement:** Repeated depth in a small, familiar pool.

**Why we think so:** Hero breadth is low, stability is high, exploration is low,
and familiar-pool dependence may be high.

**The upside:** Familiarity can create a clear, repeatable game plan.

**The tension:** A small pool may leave fewer options when the draft, patch, or
matchup asks for a different tool.

**Watch for:** Whether off-pool activity or performance actually drops before
calling the pool restrictive.

**Nearest neighbors:** Craftsman when the pool contains several heroes with a
shared toolkit; Free Agent when breadth and exploration rise.

#### A2 — Craftsman

**Identity statement:** Several heroes, one recurring set of tools.

**Why we think so:** Breadth is low to medium, toolkit breadth is narrower,
stability is high, and Signature Dependence may reinforce the shape. Broad Pool,
Narrow Toolkit is useful support.

**The upside:** The player can change the hero without abandoning a familiar
way of solving the game.

**The tension:** New hero names may not add as much new coverage as the draft
screen suggests.

**Watch for:** Whether a taxonomy update changes the toolkit grouping.

**Nearest neighbors:** Specialist when the pool gets smaller; Explorer when
selection becomes more novelty-driven.

#### A3 — Explorer

**Identity statement:** Novelty is a visible part of selection.

**Why we think so:** Hero breadth and exploration are high while pool stability
is lower.

**The upside:** The player keeps opening new routes through the hero pool.

**The tension:** A moving pool gives less repeated evidence for any one hero or
toolkit.

**Watch for:** Whether the extra range travels into Off-Pool Performance or
remains mostly a selection signal.

**Nearest neighbors:** Free Agent when no small subset dominates at all;
Adapter when range and performance transfer travel together.

#### A4 — Adapter

**Identity statement:** Range that usually travels with the performance.

**Why we think so:** Breadth, exploration, and toolkit breadth are high, with
Off-Pool Performance acting as a useful confirmation when available. Activity
Travels Better Than Results is an optional related Pattern, but an Adapter is
not required to have that Pattern.

**The upside:** The selection range is supported by a performance signal that
travels beyond the familiar pool.

**The tension:** Broad range still carries more moving parts and more draft
choices to manage.

**Watch for:** Whether taxonomy coverage and off-pool comparison cells stay
large enough to support the label.

**Nearest neighbors:** Explorer when exploration is high but transfer is mixed;
Free Agent when no signature subset remains.

#### A5 — Free Agent

**Identity statement:** No small hero subset dominates the observable identity.

**Why we think so:** Hero breadth is high, stability is lower, exploration is
visible, and Signature Dependence is low when that optional signal is present.

**The upside:** The player has a wide selection surface without one obvious
signature carrying the whole story.

**The tension:** A broad identity can be harder to summarize and harder to
anchor when the match asks for a repeatable plan.

**Watch for:** The difference between genuine range and a bounded window that
simply contains several short-lived experiments.

**Nearest neighbors:** Explorer when exploration is the stronger signal;
Adapter when transfer is the stronger signal.

### Group B — Combat Expression

**Definition:** How summary-visible kill involvement is distributed, within the
limits of kills, assists, deaths, and time.

**Core Elements:** E09 Combat Involvement, E10 Finisher Orientation, and E11
Death Exposure. The group can classify with a minimum reliable subset, but the
third signal improves the explanation.

**Free evidence limit:** Summary K/D/A and duration cannot identify initiation,
teamfight positioning, control contribution, objective conversion, or the cost
of a particular death. The labels stay inside that boundary.

**Supporting Patterns:** High Involvement, Controlled Exposure; High
Involvement, High Exposure; Selective Finisher.

#### B1 — Skirmisher

**Identity statement:** Frequent involvement with a meaningful finishing share.

**Why we think so:** Combat involvement is high and Finisher Orientation leans
above the middle, with moderate exposure often completing the shape.

**The upside:** The player is present in many kill events and finishes a
meaningful portion of them.

**The tension:** Frequent presence can still come with a cost that summary
data cannot locate.

**Watch for:** Whether higher involvement is paired with controlled or high
Death Exposure.

**Nearest neighbors:** Enabler when assists dominate; High Involvement, High
Exposure when deaths rise.

#### B2 — Enabler

**Identity statement:** Frequent involvement with more assists than finishes
and controlled exposure.

**Why we think so:** Combat involvement is high, Finisher Orientation is lower,
and Death Exposure is controlled.

**The upside:** The player appears in many events without needing the final
credit each time.

**The tension:** Summary data cannot tell us whether the assists came from
setups, follow-up damage, or simply being nearby.

**Watch for:** Teamfight participation and control contribution in a future
Deep read.

**Nearest neighbors:** Skirmisher when finishing share rises; Connector when
overall involvement is more moderate.

#### B3 — Selective Finisher

**Identity statement:** Fewer events, a higher finishing share, and lower
exposure.

**Why we think so:** Involvement is lower or moderate, Finisher Orientation is
high, and Death Exposure is low.

**The upside:** The player’s visible events are selective and carry a strong
finishing share.

**The tension:** Fewer events also means less summary evidence about everything
that happened outside the recorded kills and assists.

**Watch for:** Whether the finisher share remains high across roles and hero
mixes.

**Nearest neighbors:** Skirmisher when involvement rises; Connector when the
kill share moves toward assist-oriented.

#### B4 — Connector

**Identity statement:** Assist-oriented involvement without a large exposure
bill.

**Why we think so:** Involvement is moderate, Finisher Orientation is low, and
Death Exposure is low.

**The upside:** The player connects to kill events while keeping exposure
comparatively contained.

**The tension:** Summary K/D/A does not reveal which invisible contributions
made those connections useful.

**Watch for:** Parsed teamfight and control evidence before describing the
connection as setup or initiation.

**Nearest neighbors:** Enabler when involvement increases; Balanced when the
signals move toward the center.

#### B5 — Balanced

**Identity statement:** No strong extreme across the summary-visible combat
Elements.

**Why we think so:** Involvement, finishing share, and exposure sit near the
middle or do not separate strongly enough to justify a sharper label.

**The upside:** The summary history does not force a dramatic combat story.

**The tension:** “Balanced” can mean genuinely even or simply that the current
evidence is not sharp enough.

**Watch for:** The confidence, runner-up, and receipts—not the label alone.

**Nearest neighbors:** Any of the four directional prototypes when one axis
clears a stronger gate.

### Group C — Session Style

**Definition:** How sessions are shaped and what changes as a session
continues.

**Core Elements:** E19 Session Length Tendency and E20 Late-Session Performance.
Post-Loss Performance Response, Post-Loss Activity Shift, Post-Loss Familiarity
Shift, and Post-Loss Death Exposure Shift are optional context.

**Group gate:** At least two reliable session Elements for most prototypes;
Reset Player additionally needs a usable post-loss performance comparison.

**Supporting Patterns:** Long Session Tax; Marathon Stability; Losses Change
Picks More Than Pace.

#### C1 — Sprinter

**Identity statement:** Shorter sessions, with little game-four evidence.

**Why we think so:** Session Length Tendency is low. Late-session behavior may
be unavailable because there are not many late games.

**The upside:** The observed session shape limits exposure to the late-session
context.

**The tension:** There is less evidence about what happens when the session
continues.

**Watch for:** Do not read limited late-game evidence as late-session decline.

**Nearest neighbors:** Even-Keel when sessions are medium and late performance
is neutral; Front-Loaded when long sessions become common and decline appears.

#### C2 — Grinder

**Identity statement:** Longer sessions where later performance holds up.

**Why we think so:** Session Length Tendency is high and Late-Session
Performance is neutral to positive. Marathon Stability is useful support.

**The upside:** The usual observable edge survives farther into the session.

**The tension:** Long sessions still contain more queue decisions and more
opportunities for the context to change.

**Watch for:** Whether the stable late-session result remains consistent across
session-gap definitions.

**Nearest neighbors:** Second Wind when later performance improves clearly;
Even-Keel when the session is less long-shaped.

#### C3 — Second Wind

**Identity statement:** Performance improves as the session goes on.

**Why we think so:** Session length is medium or long and Late-Session
Performance is clearly positive.

**The upside:** Later games carry a stronger observable performance signal.

**The tension:** A late improvement can coexist with selection or role changes
that summary data cannot fully separate.

**Watch for:** Whether the result is stable across independent sessions rather
than carried by one long run.

**Nearest neighbors:** Grinder when improvement is closer to neutral;
Even-Keel when the late movement is not large enough to clear the gate.

#### C4 — Front-Loaded

**Identity statement:** Long sessions are common, but the later games give back
some edge.

**Why we think so:** Session Length Tendency is high and Late-Session
Performance is clearly negative. Long Session Tax is useful support.

**The upside:** The first part of the session provides a clear baseline for an
explicit stop-or-continue experiment.

**The tension:** The late-session comparison is a real leak in this history,
but its cause is not identified.

**Watch for:** Whether a deliberate game-four opt-in changes the result over
several sessions.

**Nearest neighbors:** Grinder when late performance holds; Sprinter when long
sessions are no longer common.

#### C5 — Reset Player

**Identity statement:** The next game changes in a measurable way after a loss.

**Why we think so:** Session context is available and Post-Loss Performance
Response is meaningfully above the middle, with Post-Loss Activity Shift as
optional support.

**The upside:** A loss is followed by a next-game change that can be described
and tested rather than guessed at.

**The tension:** “Reset” names an observable next-match response, not an inner
state or a promise that the response is beneficial in every match.

**Watch for:** Whether hero, role, party, and team tempo changed at the same
time.

**Nearest neighbors:** Even-Keel when the next-game contrast is close to the
middle; Sprinter when session evidence is too short for a response story.

#### C6 — Even-Keel

**Identity statement:** Session position and post-loss shifts stay close to
neutral.

**Why we think so:** Session length, late-session performance, and any available
post-loss performance response stay near the center.

**The upside:** The current history does not show a strong session-shaped leak
or spike.

**The tension:** Neutral can mean stable, mixed, or simply not large enough to
clear a reviewed gate.

**Watch for:** Confidence and the number of independent sessions before
turning “even” into a strong claim.

**Nearest neighbors:** Grinder or Sprinter when session length moves away from
the center; Front-Loaded or Second Wind when late-session movement becomes
clear.

## 8. Dependency matrices

These tables are the quick relationship view. The sections above explain the
relationships in full sentences.

### Element → Pattern

| Element | Patterns that consume it |
| --- | --- |
| E01 Hero Pool Breadth | P01, P02, P03, P04, P05 |
| E02 Hero Pool Stability | P15 |
| E03 Hero Exploration | P06 optional |
| E04 Toolkit Breadth | P01 |
| E05 Signature Dependence | P02 optional, P06 |
| E06 Post-Loss Familiarity Shift | P02 optional, P11, P12 |
| E07 Role Breadth | P04, P05 |
| E08 Role Switching | None in the current reviewed Pattern set |
| E09 Combat Involvement | P08, P09, P10 |
| E10 Finisher Orientation | P10 |
| E11 Death Exposure | P08, P09, P10 |
| E12 Off-Pool Performance | P02, P06, P07; P03 optional |
| E13 Off-Pool Activity Stability | P03, P07 |
| E14 Off-Role Performance | None in the current reviewed Pattern set |
| E15 Performance Volatility | None in the current reviewed Pattern set |
| E16 Recent Form Shift | P15 |
| E17 Recent Activity Shift | P15 |
| E18 Long-Game Performance Shift | None in the current reviewed Pattern set |
| E19 Session Length Tendency | P13, P14 |
| E20 Late-Session Performance | P13, P14 |
| E21 Post-Loss Performance Response | P11 optional, P13 optional |
| E22 Post-Loss Activity Shift | P11, P12 |
| E23 Post-Loss Death Exposure Shift | P09 optional, P12 optional |

An Element with no current Pattern consumer is not dead code. It is an active,
readable measurement that can appear in a dimension view or become the basis
for a future reviewed relationship.

### Pattern → required Elements

| Pattern | Required Elements | Optional support |
| --- | --- | --- |
| P01 Broad Pool, Narrow Toolkit | E01, E04 | — |
| P02 Broad Pool, Narrow Safety Zone | E01, E12 | E06, E05 |
| P03 Specialist, Transferable Style | E01, E13 | E12 |
| P04 Role Anchor, Hero Explorer | E07, E01 | — |
| P05 Hero Anchor, Role Flex | E01, E07 | — |
| P06 Signature Strength With a Tax | E05, E12 | E03 |
| P07 Activity Travels Better Than Results | E13, E12 | — |
| P08 High Involvement, Controlled Exposure | E09, E11 | — |
| P09 High Involvement, High Exposure | E09, E11 | E23 |
| P10 Selective Finisher | E09, E10, E11 | — |
| P11 Losses Change Picks More Than Pace | E06, E22 | E21 |
| P12 Losses Change Pace More Than Picks | E06, E22 | E23 |
| P13 Long Session Tax | E19, E20 | E21 |
| P14 Marathon Stability | E19, E20 | — |
| P15 Form Changed, Style Didn’t | E16, E02, E17 | — |

### Pattern → direct Archetype support

| Pattern | Directly listed Archetype group support |
| --- | --- |
| P01 Broad Pool, Narrow Toolkit | Hero Identity; especially Craftsman as supporting evidence |
| P02 Broad Pool, Narrow Safety Zone | None directly; its Elements can still affect Hero Identity fit |
| P03 Specialist, Transferable Style | Hero Identity |
| P04 Role Anchor, Hero Explorer | None; there is no current Role Identity group |
| P05 Hero Anchor, Role Flex | None; there is no current Role Identity group |
| P06 Signature Strength With a Tax | None directly |
| P07 Activity Travels Better Than Results | Hero Identity; useful support for Adapter |
| P08 High Involvement, Controlled Exposure | Combat Expression |
| P09 High Involvement, High Exposure | Combat Expression |
| P10 Selective Finisher | Combat Expression |
| P11 Losses Change Picks More Than Pace | Session Style |
| P12 Losses Change Pace More Than Picks | None directly; its Elements can still affect Session Style fit |
| P13 Long Session Tax | Session Style; especially Front-Loaded |
| P14 Marathon Stability | Session Style; especially Grinder |
| P15 Form Changed, Style Didn’t | None directly |

### Archetype → contributing Elements and Patterns

| Archetype group | Core Elements | Optional Elements | Supporting Patterns |
| --- | --- | --- | --- |
| Hero Identity | E01, E02, E03 | E04, E05, E12 | P01, P03, P07 |
| Combat Expression | E09, E10, E11 | — | P08, P09, P10 |
| Session Style | E19, E20 | E21, E22, E06, E23 | P13, P14, P11 |

| Prototype | Most characteristic inputs |
| --- | --- |
| Specialist | Low E01, high E02, low E03; E05 may be high |
| Craftsman | Low-to-medium E01, low E04, high E02; P01 is useful support |
| Explorer | High E01 and E03, lower E02 |
| Adapter | High E01, E03, E04, and usually E12 |
| Free Agent | High E01 and E03, lower E02 and E05 |
| Skirmisher | High E09, meaningful E10, moderate E11 |
| Enabler | High E09, low E10, controlled E11 |
| Selective Finisher | Lower E09, high E10, low E11 |
| Connector | Moderate E09, low E10, low E11 |
| Balanced | All three combat inputs near the middle |
| Sprinter | Low E19; late-session evidence may be limited |
| Grinder | High E19, neutral-to-positive E20; P14 helps |
| Second Wind | Medium/high E19, high E20 |
| Front-Loaded | High E19, low E20; P13 helps |
| Reset Player | E19 available and E21 meaningfully positive; E22 may refine |
| Even-Keel | E19, E20, and available post-loss inputs near the middle |

### Data source → active Elements

| Source family | Elements it can support |
| --- | --- |
| Hero choices | E01, E02, E03, E05, E06, E12, E13 |
| Match outcomes | E05, E06, E12, E14, E15, E16, E18, E20, E21, E22, E23 |
| Kills, assists, and duration | E09, E10, E11, E13, E17, E22, E23 |
| Deaths and duration | E11, E23 |
| Credible role hints | E07, E08, E09, E10, E11, E14, E17, E23 |
| Timestamps and chronology | E02, E03, E05, E06, E08, E12, E14, E16, E17, E19, E20, E21, E22, E23 |
| Inferred sessions | E06, E19, E20, E21, E22, E23 |
| Versioned hero taxonomy | E04 |

### Tier → current model surface

| Tier | What is available |
| --- | --- |
| Free · Active | 23 Elements, 15 Patterns, and three context Archetype groups, all from one bounded summary-history read. |
| Deep · Planned | Match-detail and parsed-replay Elements, Patterns, and Archetype groups listed below. They are not part of Free scoring. |

## 9. Planned Deep model surface

This section is deliberately separate from the active catalog. These are model
targets, not promises that the current report can calculate them.

Deep evidence may require selected match details or replay-derived collections.
It should be fetched only when the product explicitly chooses the cost and the
required coverage exists.

### Planned Elements: Laning

| Planned Element | Why Free cannot support it reliably | Expected evidence |
| --- | --- | --- |
| Lane Efficiency | Summary history does not show gold or experience movement through a lane. | Gold/experience timelines, last hits, denies, lane fields, and parsed positions. |
| Creep-Score Pressure | A final last-hit count does not show pressure over time. | Last-hit and deny timelines. |
| Deny Pressure | Summary rows do not show denied creeps in context. | Deny events and lane timelines. |
| Early Kill Pressure | A match K/D/A total cannot isolate the early lane window. | Kill/death timing and lane context. |
| Lane Recovery | Summary history cannot show how a lane deficit was recovered. | Gold/experience curves and lane timelines. |

### Planned Elements: Economy

Farm Intensity, Farm Efficiency, Gold Conversion, Recovery Farming, Item Timing
Reliability, Itemization Flexibility, and Resource Sacrifice are planned.
They require combinations of GPM, XPM, net worth, gold timelines, purchase
logs, item timings, ward or support spend, damage, and objective outputs.

### Planned Elements: Advanced Combat

Teamfight Participation, Damage Contribution, Control Contribution, Fight
Survival, Pickoff Orientation, and Buyback Aggression are planned. They require
teamfight records, damage relationships, control events, kill/death logs, and
buyback logs. This is the evidence needed before using words such as
“initiator,” “controller,” or “fight arrival.”

### Planned Elements: Map & Objectives

Tower Pressure, Objective Conversion, Roshan Orientation, Vision Contribution,
Ward Efficiency, Rotation Frequency, and Map Spread are planned. They require
tower and objective events, Roshan records, ward logs, and movement or position
timelines.

### Planned Elements: Risk & Survival enrichment

Early Death Exposure, Death Cost, Positioning Exposure, and Advantage
Protection are planned. They require death timestamps, gold or experience
advantage curves, positions, and fight context.

### Planned Deep Patterns

The current plan names these reviewed targets: Lane Winner, Map Loser; High
Activity, Low Conversion; Farm Without Pressure; Mechanics Travel, Timing
Doesn’t; Recovery Specialist; Resource-Sacrifice Enabler; Ahead but
Unprotected; Late Fight Arrival; Off-Pool Item-Timing Variance; and Vision
Without Conversion.

Each would need its own dependency list, evidence gate, and copy limits before
it could become active. A Free Pattern can point at a Deep question, but it
cannot quietly publish the Deep conclusion.

### Planned Deep Archetype groups

The planned groups are Economy and Map & Objectives. Their named prototypes
are:

- Economy: Accelerator, Investor, Converter, Sacrificer, Recovery Farmer.
- Map & Objectives: Hunter, Pusher, Rotator, Controller, Objective Player.

Advanced Combat evidence may later enrich or replace parts of the Free Combat
Expression group, but that is a future evidence decision, not a current Free
classification.

## 10. Worked traces: from data to story

These examples show the allowed path. The arrows are a dependency explanation,
not a second analytics engine.

### Trace 1: many heroes, one toolkit

**Source:** Hero choices plus the versioned hero taxonomy.

**Observed shape:** Hero Pool Breadth is high. Toolkit Breadth is low, with
enough taxonomy coverage.

**Pattern:** Broad Pool, Narrow Toolkit qualifies.

**Archetype context:** The Hero Identity group may move toward Craftsman if
stability and the rest of the core selection evidence support it.

**Finding:** “You play a lot of heroes. Fewer game plans.”

**Allowed explanation:** The hero names change more than the taxonomy’s toolkit
groupings do.

**Not allowed:** “You are one-dimensional,” “you refuse to adapt,” or any claim
about why the player chooses those heroes.

### Trace 2: activity travels, results do not

**Source:** Chronological hero familiarity split, kills, assists, duration, and
the summary performance proxy.

**Observed shape:** Off-Pool Activity Stability is high. Off-Pool Performance is
low compared with the familiar-pool comparison.

**Pattern:** Activity Travels Better Than Results qualifies.

**Archetype context:** The Pattern can support the Hero Identity group’s Adapter
comparison, but the group may still choose another prototype.

**Finding:** “Your activity travels farther than your results do.”

**Deep handoff:** Investigate lane efficiency, item timing reliability, and
teamfight participation. Those are questions for richer evidence.

**Not allowed:** “Your mechanics are fine but your decisions are bad.” The
summary history shows a gap, not the missing mechanism.

### Trace 3: long sessions, late-session leak

**Source:** Match timestamps, inferred sessions, session positions, and the
summary performance proxy.

**Observed shape:** Session Length Tendency is high. Late-Session Performance is
low across independent multi-game sessions.

**Pattern:** Long Session Tax qualifies.

**Archetype context:** The Session Style group may move toward Front-Loaded.

**Finding:** “Game four is where the edge starts to leak.”

**Player experiment:** Make game four an explicit opt-in for several sessions,
then compare game-four-plus performance with the earlier-session baseline.

**Not allowed:** “You get tired after three games” as a causal diagnosis.

## 11. What this model intentionally does not claim

The boundaries are part of the product, not editorial footnotes.

- No tilt, anger, fear, trust, confidence, selfishness, leadership, or hidden
  intent claims.
- No clinical or personality diagnosis.
- No causal claim from a within-history association.
- No population percentile unless a separate, versioned cohort distribution
  actually supports one.
- No exact Dota position from a summary role hint.
- No initiation, control, positioning, objective conversion, or death-cost
  claim from summary K/D/A and duration alone.
- No “good” or “bad” label attached to a normalized score without a separate
  product-approved directional meaning.
- No Deep conclusion inferred from a Free Pattern’s diagnostic question.
- No forced Pattern when a required Element is missing or weak.
- No forced Archetype when evidence is thin or the leading prototypes are too
  close to call.

The model can say what the history shows, what relationship is visible, and
what richer evidence would be worth checking next. That is enough. Dota will
provide the remaining drama for free.

## 12. Versioning and maintenance

The current active registries are versioned independently:

| Registry | Current version | Active surface |
| --- | --- | --- |
| Dimensions | dimensions-1.0.0 | 10 organizing dimensions |
| Free Elements | free-elements-1.0.0 | 23 Elements |
| Free Patterns | free-patterns-1.0.0 | 15 Patterns |
| Context Archetypes | free-archetypes-1.0.0 | Three groups, 16 prototypes |
| Findings | free-findings-3.0.0 | Editorial bridge from qualified upstream results |

The production definition sources are:

- [Dimension definitions](../../services/api/app/behavior/dimensions.py)
- [Element definitions](../../services/api/app/behavior/elements/registry.py)
- [Element scoring](../../services/api/app/behavior/elements/service.py)
- [Pattern definitions](../../services/api/app/behavior/patterns/registry.py)
- [Pattern qualification](../../services/api/app/behavior/patterns/service.py)
- [Archetype definitions](../../services/api/app/behavior/archetypes/registry.py)
- [Archetype classification](../../services/api/app/behavior/archetypes/classifier.py)
- [Finding bridge](../../services/api/app/findings/behavior.py)

The generated [model catalog](model-catalog.md) should be refreshed when a
registry changes. This human guide should also be updated when a definition’s
meaning, evidence boundary, downstream dependency, or user-facing limits
change. Run the catalog and documentation checks before treating a model
change as complete.

## 13. Glossary

**Summary history** — The bounded collection of public match-summary rows used
by Free mode. It contains useful totals and timestamps, not replay-level
events.

**Performance proxy** — The existing summary-level comparison signal used for
form and transfer questions. It is useful for bounded comparisons, not a full
performance rating.

**Activity** — Kills plus assists per unit of match time. It describes visible
kill-event involvement, not all useful work in a Dota game.

**Role hint** — A credible role or lane-context signal inferred from summary
fields. It is not a parsed position and should not be written as certainty.

**Hero taxonomy** — A versioned editorial grouping of hero traits and toolkits.
It makes “many heroes, similar tools” measurable, but it remains a maintained
classification.

**Familiar pool** — A set of heroes or role contexts established from earlier
history before a later comparison window. It is defined without looking ahead
at the later outcomes.

**Coverage** — The share of the relevant history that contains the fields needed
for an Element or comparison.

**Effective sample** — A conservative view of how much independent evidence a
comparison really has. Two small comparison groups should not look like one
large sample merely because their row counts add together.

**Stability** — How much the result agrees across relevant windows, session-gap
policies, or other sensitivity checks.

**Receipt** — A readable evidence item such as a group size, distribution
similarity, median activity rate, or loss-versus-win difference.

**Confounder** — A known factor that may shape a result without being separated
by the current evidence, such as patch, role mix, hero style, stopping behavior,
or team tempo.

**Qualified Pattern** — A Pattern whose required Elements are present, pass the
confidence gates, and meet the reviewed relationship threshold.

**Suppressed Pattern** — A candidate that was considered but did not clear its
relationship or confidence threshold.

**Still taking shape** — The safe Archetype fallback when the group lacks enough
reliable evidence or its leading prototypes are too close to call.
