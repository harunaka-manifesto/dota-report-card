# Dota Report Card — Free Player DNA UX Blueprint

**Status:** Concept / wireframe direction  
**Primary goal:** Define the end-to-end free report experience after a player enters a Steam ID.  
**Visual direction:** Handwritten-paper-wireframe. Prioritize concept, hierarchy, rhythm, and interaction over polished visual design.  
**Interaction model:** One swipe / wheel gesture / trackpad gesture = one viewport = one report page, using smooth native-feeling vertical scroll snapping rather than explicit Next/Previous buttons.

---

## 1. Product idea

The free report should feel like a **personal reveal**, not an analytics dashboard.

The player should move through three emotional stages:

1. **Recognition** — “Yeah, that is how I play.”
2. **Discovery** — “I did not realize I had that pattern.”
3. **Identity** — “This result feels specifically mine.”

The report should answer:

> **Who am I as a Dota player?**

It should **not** overreach into:

> Why do I lose?  
> What tactical mistakes do I make?  
> What should I fix mechanically?

Those questions belong to the paid Deep Dive, where selected full-match data can support stronger performance diagnoses.

---

## 2. Data boundary

### Free report source

Use the OpenDota player match-history payload:

`GET /players/{account_id}/matches?limit=500`

Target approximately the latest **500 eligible matches**.

Useful summary-level fields include:

- `match_id`
- `player_slot`
- `radiant_win`
- `duration`
- `game_mode`
- `lobby_type`
- `hero_id`
- `start_time`
- `kills`
- `deaths`
- `assists`
- `party_size`
- `lane_role`
- `lane`
- `is_roaming`
- `patch`
- `region`
- related optional summary metadata

### Important boundary

The free report should not imply knowledge of:

- item timings
- warding quality
- healing impact
- objective decision-making
- fight selection
- net-worth efficiency
- map positioning
- teamfight execution
- detailed lane performance
- draft logic

Those require full-match or parser-derived data.

### Product-owned hero metadata required

OpenDota summary data tells us **which hero was played**, but does not by itself provide the semantic hero taxonomy needed for Spotify-style hero recommendations.

Maintain a separate hero metadata layer containing traits such as:

- primary/common roles
- melee / ranged
- initiation
- mobility
- pickoff
- teamfight
- save
- sustain
- burst
- sustained damage
- wave clear
- push
- frontline
- scaling
- farming dependency
- global presence
- micro intensity
- complexity
- repositioning

This taxonomy powers:

- Hero Pattern
- Signature Hero interpretation
- Recommended Expansion Heroes

---

# 3. Experience principles

## 3.1 One page = one thought

Every report page should communicate **one primary idea**.

Bad:

> Hero breadth + role distribution + win rate + most-played heroes + archetype all visible together.

Good:

> **You know what you like.**  
> Focused ●──────── Exploratory  
> 68% of your games came from 8 heroes.

Then swipe.

---

## 3.2 Interpretation before statistics

Hierarchy:

1. **Human statement**
2. **Identity label / spectrum**
3. **Evidence**
4. Optional small methodology note

Example:

> **You rarely wander far from home.**  
>
> **Focused**  
> Focused ●──────── Exploratory  
>
> 68% of your last 200 matches came from 8 heroes.

Do not lead with:

> Hero entropy: 0.31

---

## 3.3 Evidence should feel like a receipt

Every major claim should have at least one visible supporting fact.

Useful receipt patterns:

- “68% of your matches came from 8 heroes.”
- “74% of role-classified matches point to the same role.”
- “Your results fall 9 percentage points outside your familiar pool.”
- “You average 0.46 combat involvements per minute.”
- “Your next-game results stay nearly unchanged after a loss.”

Avoid showing statistical machinery unless the user asks for methodology.

---

## 3.4 Neither end of a DNA spectrum is inherently better

DNA is identity, not grading.

Prefer:

> Focused ↔ Exploratory

Avoid:

> Limited ↔ Versatile

Prefer:

> Resetting ↔ Outcome-sensitive

Avoid:

> Mentally strong ↔ Tilter

The report may describe patterns, but must not diagnose psychology from match history.

---

## 3.5 Shareability is designed, not appended

Each major section ends with a **purpose-built summary page**.

Share pages should:

- fit cleanly into portrait social formats
- contain minimal but identifying context
- make sense without the rest of the report
- avoid exposing Steam IDs unless the player explicitly enables them
- include product branding subtly
- include “Based on X recent matches”

---

# 4. Navigation and scrolling model

## Primary navigation

Vertical, full-viewport storytelling.

- One page occupies approximately `100dvh`.
- Use CSS/native scroll snapping rather than JavaScript hijacking.
- Recommended behavior: `scroll-snap-type: y mandatory` or `proximity` after testing.
- Each page: `scroll-snap-align: start`.
- Preserve natural trackpad momentum.
- Do not force instantaneous snap during active scrolling.
- On touch, one decisive swipe should normally settle on the next/previous page.
- Mouse wheel should remain usable without requiring a precise wheel notch.
- Keyboard support:
  - `↓`, `PageDown`, `Space` → next page
  - `↑`, `PageUp`, `Shift+Space` → previous page
  - `Home` → beginning
  - `End` → finale

## Progress

Use a small persistent progress treatment:

`DNA  4/8`  
or  
`● ● ● ○ ○`

Do not use a giant stepper.

Section changes can use a handwritten tab / paper-edge label:

- DNA
- HEROES
- PLAYER CARD

## Backward navigation

The user may freely scroll upward. Never lock previous pages.

## Reduced motion

Respect `prefers-reduced-motion`.

When enabled:

- remove parallax
- remove exaggerated card rotation
- remove hero-image fly-ins
- keep simple fades
- preserve scroll snapping only if it remains comfortable

---

# 5. Archetype header rule

## Format

**The [Archetype]**  
*Descriptor 1 • Descriptor 2 • Descriptor 3*

Example:

> **The Craftsman**  
> *Focused • Role-anchored • Resilient*

## Rules

1. Exactly **one** core archetype.
2. Exactly **three** descriptors.
3. Descriptors come from the player’s most distinctive DNA results.
4. Do not use a fixed descriptor trio per archetype.
5. Each descriptor should add different information.
6. Prefer descriptors from different behavioral groups when possible.
7. Avoid repeating the archetype name in descriptor form.
8. Descriptors must be readable without methodology knowledge.
9. Archetype is the memorable identity; descriptors are the personalized fingerprint.
10. Two players may share an archetype but should often have different descriptor trios.

---

# 6. Free DNA dimensions

These dimensions are intended to be **orthogonal questions**, not synonyms for the same hero-pool behavior.

---

## 6.1 Breadth

**Question:** What do you play?

**Spectrum:**  
**Focused ↔ Exploratory**

**Definition:**  
How concentrated or distributed the player’s hero choices are.

**Data:**

- `hero_id`
- number of unique heroes
- top-3 hero match share
- top-5 hero match share
- top-10 hero match share
- hero pick distribution
- hero-pool entropy
- recency-weighted hero distribution where useful

**Interpretation examples:**

Focused:

> “You know what you like.”

Exploratory:

> “Hero select is part of the game for you.”

---

## 6.2 Role

**Question:** Where do you play?

**Spectrum:**  
**Anchored ↔ Fluid**

**Definition:**  
How strongly the player repeatedly occupies the same role/lane identity.

**Data:**

- `lane_role`
- `lane`
- `is_roaming`
- `hero_id` as supporting role evidence
- dominant role share
- role-distribution entropy
- proportion of role-classifiable matches

**Important:**  
OpenDota role/lane summary labels are hints, not replay-proven positions. If coverage is weak, lower confidence or omit the dimension from the top-three descriptors.

**Interpretation examples:**

Anchored:

> “You tend to know where you belong before the draft is over.”

Fluid:

> “Your role changes more often than your identity does.”

---

## 6.3 Adaptability

**Question:** Does your game travel?

**Spectrum:**  
**Comfort-bound ↔ Transferable**

**Definition:**  
How much the player’s observable performance changes when leaving familiar heroes and/or roles.

**Data:**

- `hero_id`
- role hints
- wins/losses
- `kills`
- `deaths`
- `assists`
- performance on high-frequency heroes
- performance on low-frequency heroes
- performance in dominant role vs secondary roles
- role-normalized summary performance where possible

**Core measurement idea:**

Compare performance:

`familiar context` vs `less familiar context`

Do not define “adaptable” merely as “plays many heroes.”

**Interpretation examples:**

Comfort-bound:

> “Your best Dota tends to live inside familiar territory.”

Transferable:

> “Changing the tools does not change you very much.”

---

## 6.4 Activity

**Question:** How often are you in the action?

**Spectrum:**  
**Reserved ↔ Involved**

**Definition:**  
How frequently the player appears in observable combat outcomes relative to match time and role context.

**Data:**

- `kills`
- `assists`
- `duration`
- role hints
- `(kills + assists) / minute`
- role-normalized combat activity
- activity distribution across matches

**Important:**  
This is **activity**, not quality.

A highly involved player is not automatically better. A reserved player is not automatically passive or bad.

**Interpretation examples:**

Reserved:

> “You do not need to be in every piece of action.”

Involved:

> “Where something happens, you tend to be nearby.”

---

## 6.5 Orientation

**Question:** When involved, what part do you usually play?

**Spectrum:**  
**Finisher ↔ Facilitator**

**Definition:**  
Whether the player’s observable combat contribution skews more toward kills or assists.

**Data:**

- `kills`
- `assists`
- `duration`
- role hints
- `kills / (kills + assists)`
- `assists / (kills + assists)`
- role-normalized kill/assist composition

**Important:**  
This must be normalized by role as much as possible. Otherwise support players will automatically appear facilitator-heavy.

**Interpretation examples:**

Finisher:

> “You tend to be the name at the end of the play.”

Facilitator:

> “You tend to be part of the reason someone else gets the kill.”

---

## 6.6 Resilience

**Question:** Does the previous game follow you into the next one?

**Spectrum:**  
**Resetting ↔ Outcome-sensitive**

**Definition:**  
How strongly the result of previous matches correlates with observable performance in subsequent matches.

**Data:**

- chronological `start_time`
- win/loss
- next-match K/D/A
- next-match role/hero context
- performance after one loss
- performance after consecutive losses
- performance after wins
- win/loss streak transitions

**Important:**  
Never label this “tilt” from summary data.

Allowed:

> “Your next games tend to change after losses.”

Not allowed:

> “You tilt after losing.”

**Interpretation examples:**

Resetting:

> “The last result rarely seems to follow you into the next queue.”

Outcome-sensitive:

> “Your sessions tend to develop momentum—for better or worse.”

---

## 6.7 Endurance

**Question:** What happens as a session continues?

**Spectrum:**  
**Front-loaded ↔ Sustained**

**Definition:**  
How observable performance changes from early to later matches within an inferred play session.

**Data:**

- `start_time`
- `duration`
- wins/losses
- K/D/A
- inferred session boundaries
- game index within session
- performance slope from Game 1 → Game 2 → Game 3 → Game 4+

**Session inference:**  
Use a configurable inactivity gap to split sessions. Start with a product assumption such as 90–120 minutes and validate against real data.

**Interpretation examples:**

Front-loaded:

> “Your sharpest Dota tends to arrive early.”

Sustained:

> “You tend to hold your level even when the session gets long.”

---

## 6.8 Rhythm

**Question:** How do you naturally consume Dota?

**Spectrum:**  
**Short-burst ↔ Grinder**

**Definition:**  
The player’s natural session-length pattern independent of whether their performance improves or deteriorates.

**Data:**

- `start_time`
- `duration`
- inferred sessions
- matches/session
- session duration
- distribution of short vs long sessions
- recurrence of long chains

**Important:**  
Rhythm is behavior, not endurance.

A player can be:

- Grinder + Front-loaded
- Grinder + Sustained
- Short-burst + Front-loaded
- Short-burst + Sustained

**Interpretation examples:**

Short-burst:

> “You tend to play Dota in concentrated doses.”

Grinder:

> “Once you start queueing, you tend to stay.”

---

# 7. Screen inventory

## Happy-path report

1. Steam ID Input
2. Player Found
3. Analysis
4. Report Reveal
5. DNA Intro
6. Breadth
7. Role
8. Adaptability
9. Activity
10. Orientation
11. Resilience
12. Endurance
13. Rhythm
14. Archetype Reveal
15. DNA Summary / Share
16. Heroes Intro
17. Signature Hero
18. Comfort Picks
19. Hero Pattern
20. Hero Recommendations
21. Heroes Summary / Share
22. Final Player Card
23. Deep Dive Teaser

Although there are 23 report pages/states, engineering should only need roughly **10–12 reusable templates**.

---

# 8. Screen-by-screen UX specification

---

## Screen 01 — Steam ID Input

### Job

Get the player into the analysis with as little friction as possible while setting the tone.

### Primary copy

**Headline**

> **What kind of Dota player are you?**

**Supporting copy**

> Paste your Steam profile, Steam ID, or supported player identifier. We’ll read your recent match history and build your Dota DNA.

**Input placeholder**

> Steam ID or profile URL

**CTA**

> **Analyze my Dota**

### Secondary content

Small handwritten annotation:

> ~200 recent matches  
> No replay parsing required

Optional small report-preview thumbnails:

- DNA
- Heroes
- Player Card

### Data

No OpenDota request until a valid identifier can be resolved.

### Interactions

**Paste / type**
- Validate format non-destructively.
- Do not show errors before the player finishes typing.

**Analyze my Dota**
1. Resolve Steam/player identifier.
2. Transition to Player Found if identity is sufficiently certain.
3. If there is a single unambiguous public profile, Player Found may auto-advance after a short visual beat.

**Enter key**
- Same as CTA.

### Error states

Invalid identifier:

> **We couldn’t read that ID.**  
> Try a Steam profile URL, Steam ID, or supported player ID.

Private/unavailable profile:

> **We found the player, but not enough public match history to build a report.**

### Wireframe direction

```text
┌──────────────────────────────────────┐
│           DOTA REPORT CARD           │
│                                      │
│   What kind of Dota player are you?  │
│                                      │
│   ┌──────────────────────────────┐   │
│   │ Steam ID or profile URL      │   │
│   └──────────────────────────────┘   │
│                                      │
│        [ ANALYZE MY DOTA ]           │
│                                      │
│  ~200 recent matches                 │
│  hand-drawn arrow → “free DNA”       │
└──────────────────────────────────────┘
```

---

## Screen 02 — Player Found

### Job

Create recognition and prevent analyzing the wrong account.

### Primary content

- player avatar if available from profile resolution
- player name
- account identifier in subdued form
- optionally rank tier if already safely available from profile data; otherwise omit

**Headline**

> **Found you.**

**Supporting copy**

> We’ll use your recent public matches to build this report.

**CTA**

> **That’s me**

Secondary:

> Not me

### Interactions

**That’s me**
- Begin summary fetch / analysis.
- Move immediately into Screen 03.

**Not me**
- Return to Screen 01 with the previous input preserved and selected.

### Wireframe

```text
┌──────────────────────────────────────┐
│               Found you.             │
│                                      │
│              ( avatar )              │
│             PLAYER NAME              │
│            ID •••••••123             │
│                                      │
│             [ THAT’S ME ]            │
│                 Not me               │
└──────────────────────────────────────┘
```

---

## Screen 03 — Analysis

### Job

Turn unavoidable processing into anticipation.

### Principle

Do not show a generic spinner with “Loading.”

Show the analytical story being assembled.

### Progressive analysis messages

Suggested sequence:

1. **Finding your recent matches**
2. **Mapping your hero habits**
3. **Reading your role patterns**
4. **Tracing your combat tendencies**
5. **Rebuilding your play sessions**
6. **Looking at what happens after wins and losses**
7. **Finding the heroes that define you**
8. **Building your Dota DNA**

### Data process

1. Fetch up to ~500 summary rows.
2. Normalize win/loss from `player_slot` + `radiant_win`.
3. Filter ineligible rows if product rules require.
4. Build chronological order.
5. Calculate hero-pool metrics.
6. Calculate role metrics where coverage permits.
7. Calculate familiarity/adaptability.
8. Calculate activity/orientation.
9. Infer sessions.
10. Calculate resilience/endurance/rhythm.
11. Score dimensions.
12. Select archetype.
13. Select top-three descriptors.
14. Calculate signature hero and comfort pool.
15. Run hero semantic-pattern matcher.
16. Generate recommendation candidates.

### Visual behavior

Use rough hand-drawn match strips and hero portrait placeholders moving into clusters.

Avoid fake progress percentages unless processing stages map reliably to progress.

Better:

`5 of 8 patterns found`

than:

`73%`

### Interaction

No Next button.

When complete:

- hold final state briefly enough to register
- show:

> **We found your pattern.**

- the next natural downward swipe reveals Screen 04

Allow scroll to continue immediately.

### Failure

If analysis partially succeeds:

> **We found enough to build most of your DNA.**  
> Some dimensions are hidden because the match history did not contain enough reliable data.

Do not block the entire report for one missing dimension.

---

## Screen 04 — Report Reveal

### Job

Create a clean emotional transition from processing to storytelling.

### Copy

> **We found your pattern.**

Small:

> Based on 187 recent public matches.

Optional:

> Swipe to meet your Dota self ↓

### Interaction

- Swipe/scroll downward begins the report.
- No explicit Next button required.
- Clicking/tapping the bottom handwritten arrow advances one page as an accessibility alternative.

### Visual

Almost empty paper.

Large marker circle / underline around “pattern.”

---

# SECTION 1 — YOUR DOTA DNA

---

## Screen 05 — DNA Intro

### Job

Explain what DNA means without making the player read methodology.

### Copy

**Kicker**

> YOUR DOTA DNA

**Headline**

> **Eight ways your habits keep showing up.**

**Body**

> Not a grade. Not an MMR prediction. Just the patterns that make your Dota look like yours.

Small receipt:

> Based on 187 matches across the last 5 months.

### Interaction

Swipe down.

### Visual

Hand-drawn eight-axis doodle / fingerprints / hero scribbles.

---

## Screens 06–13 — DNA Dimension Template

All eight dimensions use one reusable component with controlled visual variants.

### Component anatomy

1. editorial statement
2. current-end label
3. spectrum
4. evidence receipt
5. optional contextual annotation
6. methodology affordance

### Base wireframe

```text
┌──────────────────────────────────────┐
│  DNA  1/8                            │
│                                      │
│  “You know what you like.”           │
│                                      │
│             FOCUSED                  │
│                                      │
│  Focused ─────●──────── Exploratory  │
│                                      │
│  68% of your matches came from       │
│  just 8 heroes.                      │
│                                      │
│           [ how we got this ]        │
└──────────────────────────────────────┘
```

### “How we got this”

Do not leave the report flow.

Open a bottom sheet / paper card overlay containing:

- plain-language methodology
- source fields
- sample size
- confidence
- close gesture

Example:

> We looked at how many heroes you played, how concentrated your top picks were, and how evenly your games were spread across the pool.

---

## Screen 06 — Breadth

### Preferred copy logic

**Focused side**

Headline candidates:

> **You know what you like.**

> **Your hero pool has a center of gravity.**

> **You would rather know your tools than own every tool.**

**Exploratory side**

> **Hero select is part of the adventure.**

> **You rarely stay in one corner of the roster.**

### Receipt examples

- “68% of your games came from 8 heroes.”
- “You played 31 unique heroes in your last 200 matches.”
- “Your top 5 heroes account for only 22% of your games.”

### Source

`hero_id`

### Visualization

- hand-drawn hero portrait stack
- top heroes physically clustered on Focused side
- scattered portraits for Exploratory

---

## Screen 07 — Role

### Preferred copy logic

Anchored:

> **Your role is part of your identity.**

Fluid:

> **You move where the game needs you.**

### Receipt examples

- “74% of role-classified matches point to the same role.”
- “No single role accounts for more than 39% of your classified matches.”

### Source

`lane_role`, `lane`, `is_roaming`, supporting `hero_id`

### Confidence handling

If role coverage is low:

- show a small `LOWER CONFIDENCE` handwritten stamp
- or skip Role as a descriptor
- the page may still appear if there is enough directional evidence

---

## Screen 08 — Adaptability

### Preferred copy

Comfort-bound:

> **Your best Dota has familiar faces.**

Transferable:

> **Changing heroes does not change you very much.**

### Receipt examples

- “Your win rate is 8 points higher on your 10 most familiar heroes.”
- “Your observable output stays nearly flat outside your most-played heroes.”

### Source

`hero_id`, role hints, win/loss, K/D/A

### Visualization

Two roughly sketched zones:

`HOME TURF` vs `OUTSIDE`

Show difference, not just absolute performance.

### Guardrail

If sample outside comfort pool is too small:

> “Not enough off-pool games to call this confidently.”

Do not fabricate the dimension.

---

## Screen 09 — Activity

### Preferred copy

Reserved:

> **You pick your moments.**

Involved:

> **Where something happens, you tend to be there.**

### Receipt examples

- “You average 0.44 kill-or-assist involvements per minute.”
- “Your combat activity sits high relative to your role mix.”

### Source

`kills`, `assists`, `duration`, role hints

### Visualization

Hand-drawn event dots along a match timeline.

Do not use a kills-only visual.

---

## Screen 10 — Orientation

### Preferred copy

Finisher:

> **You tend to put the period on the play.**

Facilitator:

> **You are often part of the reason someone else gets the kill.**

### Receipt examples

- “46% of your kill-or-assist involvement is yours to finish.”
- “Your contribution skews heavily toward assists even after role adjustment.”

### Source

`kills`, `assists`, role hints

### Visualization

Simple illustrated chain:

`CREATE → CONNECT → FINISH`

Place the player’s mark closer to one end.

---

## Screen 11 — Resilience

### Preferred copy

Resetting:

> **The last game usually stays in the last game.**

Outcome-sensitive:

> **Your sessions tend to develop momentum.**

### Receipt examples

- “Your next-game result barely changes after a loss.”
- “After consecutive losses, your next-game performance drops noticeably.”

### Source

`start_time`, win/loss, K/D/A, chronological sequence

### Guardrail

Never use:

- tilt
- rage
- mental weakness
- emotional instability

unless the player self-reports those things elsewhere.

### Visualization

Hand-drawn sequence:

`L → ? → ?`

or a line that either resets to baseline or carries momentum.

---

## Screen 12 — Endurance

### Preferred copy

Front-loaded:

> **Your sharpest Dota tends to arrive early.**

Sustained:

> **You keep your shape deep into a session.**

### Receipt examples

- “Your first two games outperform Games 4+ by 7 percentage points.”
- “Your results stay almost flat from Game 1 through Game 5.”

### Source

`start_time`, `duration`, win/loss, K/D/A, inferred sessions

### Visualization

Game cards:

`1  2  3  4  5+`

Sketch performance line across them.

---

## Screen 13 — Rhythm

### Preferred copy

Short-burst:

> **You play Dota in concentrated doses.**

Grinder:

> **Once you start queueing, you tend to stay.**

### Receipt examples

- “Your typical session is 2 matches.”
- “41% of your sessions reach 5+ matches.”

### Source

`start_time`, `duration`, inferred sessions

### Visualization

Handwritten session strips:

`●●`  
`●●●●●●`  
etc.

---

## Screen 14 — Archetype Reveal

### Job

Turn eight separate dimensions into one memorable identity.

### Content

**Kicker**

> YOUR ARCHETYPE

**Primary**

> **THE CRAFTSMAN**

**Fingerprint**

> *Focused • Role-anchored • Resilient*

**Synthesis**

> You approach Dota by finding a structure that works, then deepening it. Your pool has a clear center, your role identity is stable, and individual results rarely seem to knock you far off course.

### Source

All eight normalized DNA scores.

### Archetype selection

The archetype should be derived from the combined profile, not from a single dominant score.

The top-three descriptors should use the three most distinctive, reliable dimensions.

### Interaction

- Tap descriptor → reveal its DNA page summary in a small overlay.
- Swipe down → section summary.
- Optional `Why this archetype?` → concise methodology sheet.

### Visual

This should be one of the visually loudest pages in the free report.

Paper-wireframe version:

- giant handwritten archetype name
- rough marker highlight
- three descriptors circled
- tiny evidence arrows pointing backward

---

## Screen 15 — DNA Summary / Share

### Job

Create a standalone shareable output for Section 1.

### Content

> **MY DOTA DNA**
>
> **THE CRAFTSMAN**
>
> *Focused • Role-anchored • Resilient*
>
> Focused      ●───────○ Exploratory  
> Anchored     ●───────○ Fluid  
> Comfort      ●───────○ Transferable  
>
> Based on 187 recent matches

Do not show all eight spectra if it becomes visually dense. Prefer:

- archetype
- three descriptors
- three miniature spectrum positions

### Actions

**Share**
- Open native share sheet when supported.
- Generate a privacy-safe image card.
- Suggested share text:
  - “Apparently I’m The Craftsman.”
  - Never include private identifiers automatically.

**Copy link**
- Copy report permalink if the product supports stable report URLs.

**Download image**
- Optional on desktop.

### Interaction after share

Return user to the exact same page; never reset scroll position.

---

# SECTION 2 — YOUR HEROES

---

## Screen 16 — Heroes Intro

### Job

Shift from abstract identity to the heroes that express it.

### Copy

> **Your heroes are not random.**

Supporting:

> Some define you. Some feel like home. And together, they reveal what kinds of tools you keep reaching for.

### Visual

Scatter recent hero portraits like printed cutouts on paper.

The most relevant heroes are subtly circled but not explained yet.

---

## Screen 17 — Signature Hero

### Job

Identify the single hero that best expresses the player’s observed identity.

### Definition

The Signature Hero is **not automatically**:

- the most played
- the highest win rate
- the best KDA

It is the hero with the strongest combined relationship to the player’s identity.

### Candidate score inputs

Illustrative only; weights should be tuned:

- play frequency
- recency
- persistence across time/patches
- role alignment
- comfort performance
- representativeness of hero-pattern traits
- sufficient sample size

Example conceptual score:

`SignatureScore = frequency + persistence + role_fit + comfort_fit + semantic_fit`

### Copy

> **If your Dota had a face, it would probably be Earth Spirit.**

Label:

> YOUR SIGNATURE HERO

Hero:

> **EARTH SPIRIT**

Support:

> You keep returning to him, he sits directly inside your role identity, and his play pattern matches the heroes that define the rest of your pool.

### Source

OpenDota:
- `hero_id`
- `start_time`
- `patch`
- role hints
- result/KDA as supporting context

Product hero taxonomy:
- semantic hero traits

### Interaction

Tap `Why this hero?`

Show 3 receipts, e.g.:

- `#1 by repeat frequency`
- `Played across 4 recent patches`
- `Matches 5/6 traits in your comfort cluster`

---

## Screen 18 — Comfort Picks

### Job

Show the small group of heroes where the player repeatedly returns and appears most at home.

### Definition

Comfort is a combination of:

- meaningful frequency
- recency
- repeat behavior
- stable enough observable results
- role fit

Not merely “highest win rate.”

### Copy

> **This is your home turf.**

Show 3–5 hero cards.

Each card should have one short reason:

> Tusk  
> **Always comes back**

> Clockwerk  
> **Role-perfect**

> Earth Spirit  
> **The centerpiece**

### Source

`hero_id`, `start_time`, result, K/D/A, role hints

### Interaction

Tap a hero card:
- expand inline or bottom sheet
- games played
- win rate
- simple K/D/A context
- “why it counts as comfort”

Do not turn this into a full stats table.

---

## Screen 19 — Hero Pattern

### Job

Convert the comfort pool into a higher-level identity insight.

### Copy

> **You keep choosing heroes that let you start things.**

Supporting:

> Your comfort pool clusters around mobile initiators: heroes that can enter first, create a target, and move the fight before the fight moves them.

### Source

OpenDota:
- player comfort/most-relevant `hero_id`s

Product hero taxonomy:
- semantic tags for those heroes

### Pattern extraction

1. Take Signature Hero + Comfort Picks.
2. Aggregate hero trait tags.
3. Find traits that over-index across the group.
4. Remove generic traits shared by too many Dota heroes.
5. Choose 1–3 human-readable themes.
6. Generate one synthesis statement.

### Examples

- mobile initiators
- scaling ranged carries
- defensive teamfight supports
- high-mobility spellcasters
- durable frontline controllers
- pickoff-focused roamers
- lane-dominant tempo cores

### Guardrail

Only make semantic claims covered by the product-owned hero taxonomy.

---

## Screen 20 — Hero Recommendations

### Job

Turn identity into a light, useful action without pretending to coach the player.

### Concept

Spotify:

> Because you like X, Y, Z → you may like A, B, C.

### Copy

> **Stay in character. Expand the cast.**

Supporting:

> These heroes share the parts of Dota you already seem to enjoy, but stretch your pool in slightly different directions.

### Recommendation logic

Candidate hero should:

1. share important traits with Signature + Comfort heroes
2. plausibly fit one of the player’s common roles
3. not already be heavily played
4. introduce at least one useful adjacent trait
5. avoid recommending only current meta heroes unless meta is explicitly part of the model

### Example

Because you play:

`Earth Spirit • Tusk • Clockwerk`

Try:

**Nyx Assassin**
> Same pickoff instinct, more information play.

**Spirit Breaker**
> Same desire to start action, much more global reach.

**Hoodwink**
> Keeps the setup/pickoff identity while moving you into a ranged toolset.

### Source

Player side:
- summary hero/role data

Recommendation side:
- product hero taxonomy

### Interaction

Tap recommendation:
- show `Why it fits`
- `What will feel familiar`
- `What will feel new`

Optional future action:

`Add to my try list`

If no persistent account feature exists yet, omit rather than fake it.

---

## Screen 21 — Heroes Summary / Share

### Job

Compress the Hero section into a second shareable identity card.

### Content

> **MY HERO DNA**
>
> Signature  
> **EARTH SPIRIT**
>
> Comfort  
> Tusk • Clockwerk • Puck
>
> Pattern  
> **Mobile initiators**
>
> Try next  
> **Nyx Assassin**

### Actions

Same sharing behavior as DNA Summary.

### Visual

Signature hero dominates.

Comfort heroes appear as small taped-photo thumbnails.

Recommendation appears as a handwritten sticky note:

> “try this next → NYX”

---

# FINALE

---

## Screen 22 — Final Player Card

### Job

Create the definitive free-report output.

This is the most shareable page in the entire report.

### Content hierarchy

> **[PLAYER NAME]’S DOTA DNA**
>
> **THE CRAFTSMAN**
>
> *Focused • Role-anchored • Resilient*
>
> Signature Hero  
> **EARTH SPIRIT**
>
> Hero Pattern  
> **Mobile initiators**
>
> Queue Rhythm  
> **Long-session player**
>
> 187 recent matches analyzed

### Optional micro-fact

One highly distinctive fact may appear:

> “68% of matches came from 8 heroes.”

Only one. Do not overload.

### Actions

**Share player card**

Primary.

**Restart / analyze another player**

Secondary.

**View methodology**

Tertiary.

### Privacy

Before first share, offer a lightweight privacy check if necessary:

- show player name: on/off
- show avatar: on/off
- never show raw Steam ID by default

---

## Screen 23 — Deep Dive Teaser

### Job

Convert identity curiosity into performance curiosity.

### Principle

Do not say:

> Pay to unlock more stats.

Say:

> DNA told you **who you are**.  
> Deep Dive tells you **what actually works, what breaks, and what to learn next**.

### Copy

**Headline**

> **You know your Dota identity. Now find out what it costs you—and where it wins.**

Possible supporting bullets:

> Deep Dive selects the matches that best explain your patterns and investigates:
>
> - how you convert leads
> - where your games turn
> - item and economy patterns
> - fight and objective behavior
> - repeatable strengths
> - specific habits worth changing

### CTA

> **Unlock Deep Dive**

Secondary:

> Keep my free report

### Interaction

Primary CTA enters pricing/checkout flow.

Do not destroy or hide the free report.

Back returns to Final Player Card.

---

# 9. Archetype system — current working taxonomy

These are working product archetypes, not permanent statistical truth. They should eventually be tested against real player distributions.

## Craftsman

Typical:

- Focused
- Anchored
- Comfort-bound
- moderate Activity

Meaning:

> Builds mastery through repetition and a clearly defined way of playing.

## Specialist Playmaker

Typical:

- Focused
- Anchored
- Comfort-bound
- highly Involved
- Finisher-leaning

Meaning:

> Masters a narrow toolkit and uses it aggressively to influence games.

## Specialist Enabler

Typical:

- Focused
- Anchored
- Comfort-bound
- highly Involved
- Facilitator-leaning

Meaning:

> Deeply understands a specific role/hero ecosystem and uses it to enable teammates.

## Operator

Typical:

- Focused/moderate Breadth
- Anchored
- Transferable
- Reserved
- Finisher-leaning

Meaning:

> Selective about involvement and prefers decisive moments over constant action.

## Steward

Typical:

- Focused/moderate Breadth
- Anchored
- Transferable
- Reserved
- Facilitator-leaning

Meaning:

> Structured and team-oriented; contributes without needing constant visibility.

## Playmaker

Typical:

- moderate/broad Breadth
- Fluid
- Transferable
- highly Involved
- Finisher-leaning

Meaning:

> Seeks agency and action regardless of exact hero or role.

## Conductor

Typical:

- moderate/broad Breadth
- Anchored or Fluid
- Transferable
- highly Involved
- Facilitator-leaning

Meaning:

> Constantly involved, primarily by connecting and enabling the team.

## Adapter

Typical:

- Exploratory
- Fluid
- Transferable
- balanced Activity
- balanced Orientation

Meaning:

> Comfortable solving different kinds of Dota problems without depending heavily on familiarity.

## Explorer

Typical:

- Exploratory
- Fluid
- Comfort-bound
- variable Activity

Meaning:

> Loves trying different things, though effectiveness still improves with familiarity.

## Maverick

Typical:

- Exploratory
- Fluid
- Transferable
- highly Involved
- Finisher-leaning

Meaning:

> Independent, action-oriented, and comfortable constantly changing approach.

## Utility Player

Typical:

- Exploratory
- Fluid
- Transferable
- Facilitator-leaning

Meaning:

> Willingly becomes whatever the draft or team seems to need.

## Traditionalist

Typical:

- Focused
- Anchored
- Transferable
- balanced Activity

Meaning:

> Has a strong, stable identity without being completely dependent on specific comfort picks.

## Free Agent

Typical:

- Broad
- Fluid
- Transferable
- balanced Orientation

Meaning:

> Has little attachment to one hero pool, role, or contribution pattern.

---

# 10. Descriptor selection

Every archetype header gets exactly three descriptors.

## Candidate descriptors

### Breadth
- Focused
- Exploratory

### Role
- Role-anchored
- Role-fluid

### Adaptability
- Comfort-driven
- Adaptable

### Activity
- Selective
- Highly involved

### Orientation
- Finisher-minded
- Facilitator-minded

### Resilience
- Resilient
- Momentum-sensitive

### Endurance
- Fast starter
- Sustained

### Rhythm
- Short-session player
- Long-session player

## Selection rule

1. Calculate normalized dimension scores.
2. Calculate distance from neutral/population midpoint.
3. Discount dimensions with weak data coverage.
4. Rank by distinctiveness × confidence.
5. Select three descriptors.
6. Prefer descriptor diversity:
   - at least one “how you play” descriptor
   - ideally one hero/role identity descriptor
   - optionally one session/mental-pattern descriptor
7. Do not force category diversity if a player has three overwhelmingly distinctive results elsewhere.

---

# 11. Copy system

## Voice

The product should sound:

- perceptive
- concise
- lightly playful
- evidence-backed
- Dota-literate

It should not sound:

- clinical
- motivational
- judgmental
- like generic coaching
- like a horoscope

## Recommended sentence pattern

### Observation

> **You know what you like.**

### Label

> Focused

### Receipt

> 68% of your last 187 matches came from eight heroes.

### Interpretation

Optional:

> Your pool has a clear center of gravity.

The page usually does **not** need more than this.

---

# 12. Handwritten-paper-wireframe visual direction

The prototype should deliberately look unfinished enough that stakeholders discuss **the idea**, not gradients.

## Base

- off-white paper background
- subtle paper texture
- imperfect black/graphite strokes
- handwritten annotations
- marker highlights
- taped hero images / photocopy treatment
- rough circles and arrows
- intentionally imperfect chart lines
- monochrome or extremely limited accent use

## Typography hierarchy

Use styles conceptually like:

**Large handwritten headline**
> “You know what you like.”

**Heavy marker result**
> FOCUSED

**Simple readable body**
> 68% of your matches came from 8 heroes.

The body text should remain highly legible; do not use handwriting for every sentence.

## Components

### Spectrum

```text
Focused ───────●──────────── Exploratory
```

Make it look hand-drawn, but position is data-accurate.

### Receipt

```text
┌───────────────────────────┐
│ 68%                       │
│ of matches came from      │
│ only 8 heroes             │
└───────────────────────────┘
       ↖ tiny note: “yep”
```

### Hero card

```text
┌───────────────┐
│   [ PORTRAIT ]│
│               │
│ EARTH SPIRIT  │
│ centerpiece   │
└───────────────┘
```

### Confidence

Use a stamp:

`HIGH CONFIDENCE`

or

`LIMITED ROLE DATA`

Do not show decimal confidence scores in the primary experience.

---

# 13. Motion direction

Motion should reinforce **reveal**, not spectacle.

## Page entrance

- paper/ink elements settle into place
- marker underline draws once
- spectrum dot slides to the player’s position
- evidence number counts only when it improves comprehension

## Hero screens

- portraits behave like photos placed on a desk
- comfort heroes can slide into a cluster
- recommendation hero can appear as a new sticky note

## Archetype reveal

Slightly stronger:

1. archetype name appears
2. marker underline draws
3. three descriptors stamp in sequentially

Avoid confetti.

## Native-feeling scroll

Do not animate the scroll position with long easing after every wheel event.

Let browser/touch scrolling happen naturally, then allow snapping to settle the nearest page.

---

# 14. Data confidence and missing-data UX

Not every player will have 200 clean matches or complete optional fields.

The report must degrade gracefully.

## Match count

Always disclose:

> Based on 142 recent public matches.

Do not pretend it is always 200.

## Dimension coverage

Each dimension has:

- minimum sample threshold
- coverage threshold
- confidence
- fallback

Example:

### Role

If only 24/180 matches have credible role hints:

Do not present:

> **Role-anchored**

Instead:

> **We couldn’t read your role pattern confidently enough yet.**

This can appear as a folded-note page or the page can be skipped depending on pacing tests.

## Hero recommendations

If semantic hero taxonomy is unavailable:

- do not fake recommendations
- show Signature + Comfort only
- hide Hero Pattern/Recommendations until taxonomy exists

---

# 15. Edge-state screens

These are not part of the happy-path 23 pages but must be designed.

## A. Invalid Steam identifier

From Input.

## B. Player found, insufficient public match history

Copy:

> **Not enough public Dota to read yet.**

> We found the account, but not enough recent public matches to build a reliable DNA profile.

Actions:

- Try another account
- Learn what data is needed

## C. Partial report

Copy:

> **Most of your DNA is readable. A few signals are faint.**

Continue with the report and mark missing dimensions.

## D. API failure

Copy:

> **OpenDota didn’t answer cleanly this time.**

Actions:

- Retry
- Return to input

Do not blame the player.

## E. Hero metadata missing

Still allow DNA report. Omit semantic recommendations.

---

# 16. Analytics instrumentation

Track enough product behavior to improve the storytelling.

## Entry funnel

- Steam ID input focused
- ID pasted
- Analyze clicked
- player resolved
- analysis started
- analysis completed
- analysis failed

## Report engagement

For every report page:

- page viewed
- dwell time
- forward/backward direction
- methodology opened
- methodology closed

## Share

- DNA card share initiated
- DNA card shared
- Hero card share initiated
- Final Player Card share initiated
- copy link
- image saved

## Conversion

- Deep Dive teaser viewed
- Deep Dive CTA clicked
- checkout started
- purchase completed

## Useful product questions

- Which dimension pages are re-read?
- Which page gets screenshotted/shared most?
- Do players share section cards or only the finale?
- Does seeing Hero Recommendations increase Deep Dive intent?
- Which archetypes have unusually high/low share rates?
- Are users abandoning because there are too many pages?
- Do users open methodology when a result surprises them?

---

# 17. Recommended first prototype scope

Do **not** build all algorithmic complexity before validating the storytelling.

## Prototype V1

Build:

1. Input
2. Analysis
3. Reveal
4. DNA Intro
5. one reusable Dimension screen
6. Archetype Reveal
7. DNA Summary
8. Heroes Intro
9. Signature Hero
10. Comfort Picks
11. Hero Pattern
12. Recommendations
13. Heroes Summary
14. Final Player Card
15. Deep Dive Teaser

Populate the eight Dimension pages through the one reusable template.

Use realistic fixture data for 3–5 fictional player profiles:

- focused support specialist
- broad role-flex player
- aggressive mid playmaker
- long-session comfort-driven carry
- highly exploratory utility player

The goal of this prototype is to validate:

- pacing
- comprehension
- emotional payoff
- whether 8 DNA pages feel too long
- whether archetype synthesis feels earned
- whether Hero Recommendations feel genuinely personal
- whether the final card is worth sharing

---

# 18. Recommended end-to-end story

```text
PASTE STEAM ID
      ↓
FOUND YOU
      ↓
ANALYZING YOUR MATCHES
      ↓
WE FOUND YOUR PATTERN
      ↓
────────────────────────
YOUR DOTA DNA
────────────────────────
Breadth
Role
Adaptability
Activity
Orientation
Resilience
Endurance
Rhythm
      ↓
YOUR ARCHETYPE
      ↓
DNA SHARE CARD
      ↓
────────────────────────
YOUR HEROES
────────────────────────
Signature Hero
Comfort Picks
Hero Pattern
Recommended Expansion
      ↓
HERO SHARE CARD
      ↓
────────────────────────
YOUR PLAYER CARD
────────────────────────
Final identity summary
      ↓
SHARE
      ↓
UNLOCK DEEP DIVE
```

The free experience begins with:

> **Who am I?**

and ends by creating the next curiosity:

> **Now that I know who I am, what does that mean for how I actually perform?**

That is the handoff into the paid Deep Dive.
