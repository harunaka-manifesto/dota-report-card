# V6.1 Story Audit and Narrative Implementation Brief

- Status: documentation-only audit of the shipped V6.1 story renderer
- Audit date: 2026-08-30
- Scope: current page inventory, narrative jobs, reveal rhythms, bridges, and ending semantics
- Non-goal: changing page IDs, payload fields, analytical behavior, or report-generation logic

This audit reads the current implementation, not the intended future contract.
The renderer and tests are the source of truth for what currently reaches a
reader. The external precedent and community findings that inform the
recommendations live in [V6.1 storytelling and reveal research](v61-storytelling-research.md).
The copy/data binding remains in [the V6.1 copy/data-basis matrix](v61-copy-data-basis-matrix.md).

## Decision summary

The current shell has a strong mechanical foundation: one composed page array,
manifest-driven omissions, persistent state, a mid-reveal navigation rule,
keyboard focus, inline evidence, a native methodology dialog, and reduced-motion
support. The principal narrative weakness is not missing data. It is that many
pages still use the same delivery shape: a heading, a dominant number or list,
one support line, and an optional dry line. The page order is already a usable
arc; the revamp should give the existing slots different editorial jobs.

Prescriptive direction:

1. Keep the current page IDs, ordering, module-to-page map, manifest contract,
   omission gates, and historical-report fallback.
2. Assign each existing slot a reveal grammar—receipt, chronology, question,
   accumulation, contrast, boundary, callback, quiet evidence, synthesis, or
   artifact—rather than one universal card template.
3. Keep every foreground claim at the same evidence level as the current
   payload. A more personal sentence may be shorter or warmer; it may not add
   skill, role, motive, causality, cohort membership, or psychological identity.
4. Replace mathematical joke cadence with a small, explicit set of fact-bound
   closes. The candidate pages and their evidence gates are part of the
   editorial architecture rather than a counter over rendered pages.
5. Make the identity ending feel earned through visible callbacks and an
   evidence map. Do not invent per-player archetype data while
   `archetype`/`final_identity_card` remain `not_ready`.
6. Preserve a real omission as an omission. Page 25 and Page 28 remain absent;
   Page 34 remains conditional on a validated destination and currently does
   not render.

## How to read the inventory

Each row answers six questions:

- **Module / condition** — what owns the slot and when composition can include it;
- **Evidence** — the runtime fields the renderer reads;
- **Current packaging / reveal** — the actual copy and primitives in
  `copy.ts`, `pages.tsx`, `motion.ts`, and `story-shell.tsx`;
- **Context / emotion** — the current chapter job and intended reader feeling;
- **Weakness** — a narrative or trust risk, not a request to change analysis;
- **Improved job** — a concrete editorial assignment that preserves the slot.

“Current” means the code as audited. It includes the narrow frontend exception
that permits the constant archetype placeholder to render while two modules are
`not_ready`; that exception is called out explicitly because it must not become
a source of fabricated personalization.

## Current composition rules

`composeStory` parses `story_payload.page_manifest`, rejects page 25, rejects
page 28 (`element_distinctiveness` has no renderer), rejects unknown or
unshippable modules, and sorts by numeric page. It then adds only frontend-owned
bridges that have a connected destination:

- Page 14 only when Page 15 (`post_loss`) renders;
- Page 16 when at least one of Pages 17–19 renders;
- Page 20 only when Page 21 (`transfer`) renders;
- Page 27 only when Page 26 renders and there is at least one usable Element;
- Pages 29–30 when `archetype` renders; Page 31 only when at least two
  evidence anchors are present;
- Page 33 when `final_identity_card` resolves to a non-null final identity;
- Page 34 only when a validated Deep destination exists. The current resolver
  always returns `null`, so Page 34 is currently absent.

The full fixture therefore traverses:

```text
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15
→ 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 26 → 27 → 29 → 30
→ 31 → 32 → 33
```

Page 25 and Page 28 never appear. Page 34 has a renderer but is not reachable
without a real destination. The E2E contract expects 31 pages for the full
fixture, and the unit suite checks the same omission behavior across finding and
degraded combinations.

## Complete slot inventory

### Recognition and the good-news run: Pages 1–11

| Page | Module / condition | Evidence | Current packaging / reveal | Context / emotion | Weakness | Improved job |
|---:|---|---|---|---|---|---|
| 1 | `hello`; manifest module in `available`/`degraded` state | `display_name`, `history_materially_short`, requested window and observed window | `chapterType` greeting at Beat 0, scope line at Beat 1, then `Close`; named and anonymous variants; “All of it” dry line is suppressed for short history | Chapter 1, welcome and trust; the reader should feel addressed without being profiled | The scope line is familiar product language and the 365-day framing can feel generic before any personal receipt appears | **Orientation / promise.** Keep the greeting and exact window boundary, then use a quiet “here is what this report can see” setup. Make the first forward action disclose scope, not a joke. |
| 2 | `match_count`; normal or limited volume variant | `match_count`, `volume_variant` | `DominantFact` count with a beat-held value, support “That’s how much Dota happened this year,” optional Ancient joke | Chapter 1, scale recognition; pride or amused concern | The first substantive page repeats the annual count pattern common to recap products and uses the same fact/support/dry sequence as Page 3 | **Receipt first.** Keep the count as the canonical anchor, but let the visual accumulation or a simple “this is the sample” question create context. Humor is optional and only after the scope is understood. |
| 3 | `hours_in_matches`; `minutes`, `hours`, or unavailable variant | `display_value`, `display_unit`, coverage fields | `DominantFact` value/unit, support line, optional “impressive or concerning” dry line | Chapter 1, investment; mild self-recognition | Consecutive dominant metrics make the opening read like an odometer; “impressive or concerning” is reusable across any high count | **Contrast / human scale.** Present time as the cost of the match count: count → duration → one restrained release. If coverage is limited, make that boundary the emotional beat instead of a joke. |
| 4 | `rank_points`; positive, negative, or zero variant | `points_absolute`, direction, ranked matches/wins/losses, classification reliability | `DominantSentence` with direction-specific copy, ranked scope, win/loss split, silent Endstop | Chapter 1, stakes and self-assessment; tension rather than celebration | “Climbed” or “finished below” is a strong verdict before the reader has seen the denominator; this page is still another number stack | **Tension / ledger.** Let direction, ranked sample, and split arrive as three parts of one ledger. Avoid implied overall skill or rank; the emotional job is “where the year moved,” not a grade. |
| 5 | `busiest_week`; hours or match-count variant | Week start/end, match count, supplied display value/unit | `chapterType` “one week stood above the rest,” date range, count/hours, optional plans joke | Chapter 1, first memory handle; surprise and recognition | Page 5 and Page 6 are adjacent peak-volume receipts with nearly identical reveal pacing and no change in question | **Chronology / peak.** Treat the week as a highlighted interval in the year. Let the date range land first, then the count; use the next page as a scale shift rather than another independent stat. |
| 6 | `busiest_day`; hours or match-count variant | Date, match count, inside-busiest-week, display value/unit | `chapterType` “inside that week…” or “one single day…,” date, count/hours, optional full-shift joke | Chapter 1, escalation; disbelief turning into amused intimacy | Same heading → date → count → joke structure as Page 5; “full shift” is a generic metaphor | **Escalation / nested reveal.** Explicitly nest the day inside the week and use the relationship as the reveal: “the peak had a peak.” Keep the dry line only when hours are supported and volume is not limited. |
| 7 | `longest_match`; standard or `refused_to_end` variant | Supplied duration string, hero, date, outcome, optional K/D/A, `on_busiest_day`, `refused_to_end` | `chapterType` lead, `DominantFact` supplied formatted duration, hero/date/KDA line, outcome line, optional “Nobody was calling GG” | Chapter 1, first mini-climax; suspense and comic endurance | The page has a good fact but treats the K/D/A as a side note; “refused to end” can imply a match story beyond duration | **Miniature climax.** Reveal duration as the object, then place date/hero/outcome as a caption. Use the “refused” framing only from the supplied flag; never call it a comeback, throw, or clutch without event evidence. |
| 8 | `wins_bridge`; wins or zero variant | Module `copy_variant` and win count | Frontend bridge, short heading, optional “You did, in fact, win some Dota” close | Chapter 2, tonal reset; relief and permission to enjoy the good news | The bridge is useful but “Alright” is a generic reset and the optional joke restarts the dry-line cadence after Page 7 | **Reframe / invitation.** Change the question from “how much” to “what went well.” Use a clean transition and let Page 9 carry the first receipt; humor should be selected only if the preceding emotional density warrants it. |
| 9 | `win_summary`; zero, one, or many variant | Wins, universe match count, optional winningest day | Zero state is a chapter heading + Endstop; normal state uses `DominantFact`, total matches, winningest day, Endstop | Chapter 2, earned good news; pride without a grade | Zero and non-zero states have very different shapes; normal state is another count followed by a smaller count, with no visual relationship | **Tally → context.** Keep the total wins as the receipt, then let winningest day become a contextual echo. For zero, the quiet Endstop is correct; do not force motivational copy. |
| 10 | `winning_streak`; single-win or streak variant | Length, start/end dates | Heading, `DominantFact`, `Sequence` blocks, date range, optional matchmaking joke; value and sequence share Beat index 1 | Chapter 2, suspense and triumph | The sequence and dominant value reveal together, so the accumulation is seen but not felt; “matchmaking behaved itself” is a math-adjacent joke | **Accumulation ladder.** Disclose the run as blocks first, let the length settle, then reveal dates. A dry line is optional and should describe the observed run, not matchmaking or luck. |
| 11 | `top_win_heroes`; ranked or unavailable | Ordered hero rows with wins and matches | Heading selects three/few/one wording, `OrderedStack`, “Keep them close” close | Chapter 2, celebration and affinity | The same ordered-list primitive returns on Pages 13 and 17; the close turns a win count into “keep them close,” which hints at comfort/strategy | **Contrast / cast.** Introduce the heroes as a cast around the win pattern, then show rows. Say “showed up for wins,” not “carried,” “best,” or “main.” Reserve the stack primitive for one page in this run or change its reveal order. |

### Adversity and the post-loss turn: Pages 12–16

| Page | Module / condition | Evidence | Current packaging / reveal | Context / emotion | Weakness | Improved job |
|---:|---|---|---|---|---|---|
| 12 | `losing_streak`; broken, observation-ended, history-boundary, or unavailable | Length, start/end dates, terminal state, optional breaker hero/date/outcome | Heading, loss `Sequence`, positional microcopy (“One more,” “And another,” “And… yeah”), dominant length, dates, terminal explanation, optional breaker thank-you | Chapter 3, adversity; tension, recognition, and dark humor | This is the most varied reveal, but the microcopy can feel like a fixed theatrical script and “pile up” language can invite a tilt reading; terminal states need careful distinction | **Accumulation → boundary/reversal.** Keep the blocks and explicit terminal state. Use one editorially chosen line only when the sequence earns it; say where observation ends rather than implying motive. The breaker is a return point, not proof of recovery. |
| 13 | `top_loss_heroes`; ranked or unavailable | Loss hero rows, optional breaker, roughest day | Breaker lead or neutral lead, optional second line, `OrderedStack`, roughest day, “They were there for you. Technically.” | Chapter 3, aftermath; sympathy with a little levity | Repeats Page 11’s list geometry and risks turning loss association into blame or hero quality; “technically” is a broad roast | **Aftermath / cast contrast.** Start from the streak’s terminal state when present, then show which heroes were present for losses. Keep the roast conditional and aimed at the count pattern, never the player or hero. |
| 14 | Frontend bridge; only when Page 15 renders | No payload data; presence of post-loss finding | Two beats: “Losing is one thing.” then “What you did next is more interesting.”, silent Endstop | Chapter 4, pivot; curiosity and suspense | It says “more interesting” without naming the question; the page is short enough to feel like a pause or a loading gap | **Reversal / question setup.** Use the quiet pause deliberately, then make the next question feel narrower: outcome → next choice. Keep it only when Page 15 exists, as composition already does. |
| 15 | `post_loss` finding; finding slot must be available and content claim + interpretation must exist | Claim, interpretation, comparable opportunities, confidence, evidence statement, alternatives | Shared `FindingPage`: question, claim, interpretation, optional sample count, `InlineEvidence`, conditional close; four/five beats | Chapter 4, inspection; curiosity and cautious vulnerability | The shape is identical to Page 21, and confidence is surfaced as a label without a richer explanation of what is unresolved | **Question → answer → boundary.** Keep the question but vary the visual from transfer. Put the result-state comparison before the prose interpretation, make the comparable denominator legible, and keep “association” language visible in Evidence. |
| 16 | Frontend bridge; only when at least one of Pages 17–19 renders | No payload data; presence of hero portfolio surfaces; `heroBridgeCombined` if Page 15 absent | If Page 15 absent, one combined heading; otherwise two-beat bridge; silent Endstop | Chapter 5, continuity; return from adversity to recurring heroes | “Questionable decisions” is a generic inference and may be read as a judgment; the combined line can compress too many ideas | **Callback / return.** Name the shift from result states to recurring choices without moralizing. When Page 15 is absent, make the combined line an honest bridge to the hero pool, not a claim that choices were questionable. |

### Hero portfolio, transfer, and combat: Pages 17–24

| Page | Module / condition | Evidence | Current packaging / reveal | Context / emotion | Weakness | Improved job |
|---:|---|---|---|---|---|---|
| 17 | `hero_pool`; concentrated, broad, neutral, or unavailable | Hero rows, total matches, top-five share, concentration band | Heading selects full/few copy, `OrderedStack`, top-five share, optional hero-pool/hero-puddle close | Chapter 5, familiarity; recognition and belonging | A full list is a receipt but not yet a story; “hero puddle” is memorable but can sound like a generic roast and suggests comfort | **Center / field.** Reveal the pool as a center with an outer edge, using the existing rows and share. Describe observed concentration only; do not translate it into comfort, mastery, role, or personality. |
| 18 | `hero_eras`; calendar-month or sparse fallback | Period dates, match counts, empty/sparse flags, top heroes | Heading, optional “Drag through your year,” interactive `HeroEras` range, optional obsession joke; sparse fallback omits prompt | Chapter 5, change over time; exploration and nostalgia | The primary interaction is a range control, so a reader who only presses Next may not experience the narrative movement; “obsession” implies motive | **Chronology / eras.** Let the static/default state show the most recent usable period, then make the range an optional exploration. Use “phase” or “period” wording; never attribute cause to a patch or mood. |
| 19 | `hero_era_payoff`; persistence, takeover, steady, or unavailable | Persistence hero/period count, takeover hero/period, steady flag | Heading, one or two payoff lines, optional dry line, optional direct transition line when transfer absent | Chapter 5, interpretation; nostalgia and recognition | Two payoff lines can arrive as another stacked assertion; “takeover” and “phase” can overstate identity without the timeline visible | **Callback / payoff.** Choose one supported relationship as the emotional sentence, then point back to the era timeline. If transfer is absent, the direct transition should be the only bridge into combat. |
| 20 | Frontend bridge; only when Page 21 renders | No payload data; presence of transfer finding | Two beats: “Knowing your favorite heroes is easy.” then “The interesting part…”; silent Endstop | Chapter 6, outside comfort zone; curiosity | “Favorite” is not a measured field—the payload has most-played heroes—and the bridge repeats the generic “interesting part” move from Page 14 | **Contrast setup.** Say “the heroes you played most” or “the names changed” and ask what, if anything, held. Use the existing transfer finding as the answer, not a new comfort-zone assertion. |
| 21 | `transfer` finding; finding slot must be available and content claim + interpretation must exist | Transfer claim, interpretation, semantic outcome key, confidence, evidence contract | Shared `FindingPage`: question, claim, interpretation, evidence; semantic key chooses one of two dry lines | Chapter 6, adaptability; tension and self-recognition | It has the same question → claim → interpretation → evidence package as Page 15; “How much travels?” can imply general adaptability; dry line can imply identity | **Contrast / frontier.** Present familiar and changed-hero contexts as two visible sides. Keep the supported distance boundary and semantic outcome key. Humor, if selected, should point to the evidence relationship rather than to a fixed persona. |
| 22 | `kills`; available or zero | Total kills, leading hero, individual rows | `DominantSentence` total, leading-hero line, optional top-games heading and `OrderedStack`; no dry line by design | Chapter 7, body count; spectacle and impact | The dominant sentence plus leading hero plus top rows is a rigid metric template; “kills” can pull the reader toward performance judgment | **Impact / receipt.** Keep the total exact, then frame the leading hero as a scene partner in the count. Use the individual rows as evidence for a selected match sequence, not as a leaderboard claim. |
| 23 | `assists`; available or zero | Total assists, leading hero, individual rows | Same combat template, with teamwork dry line when total non-zero | Chapter 7, body count; connection and relief | The same template repeats immediately and the joke turns an aggregate into “teamwork,” which is an interpretation not measured by the field | **Connection / counterpoint.** Make this the relational counterpoint to kills: the same scoreboard surface, different credited action. Keep the exact number and avoid asserting collaboration quality or intent. |
| 24 | `deaths`; available or zero | Total deaths, leading hero, individual rows | Same combat template, “Dota collected…” dominant sentence, leading hero, rows, “we looked at everything” dry line | Chapter 7, body count; consequence and release | Three adjacent pages make the report feel mathematical; “collected” and “bloodiest” add theatrical judgment and the dry line is generic | **Cost / quiet return.** Let deaths be the final visible receipt before the analytical bridge, with calmer pacing and no blame. If humor is used, it must be earned by a supplied sequence/detail, not by death as a punchline. |

### Seven signals and synthesis: Pages 26–34

| Page | Module / condition | Evidence | Current packaging / reveal | Context / emotion | Weakness | Improved job |
|---:|---|---|---|---|---|---|
| 26 | Frontend bridge; manifest page with `module: null` | No payload data; presence of Page 24 and Page 26 | Two beats: “Kills, assists, deaths—that’s the visible part.” then “Underneath…”; silent Endstop | Chapter 9, abstraction pivot; curiosity and depth | It implies hidden analysis without immediately naming what the reader can see; the phrase “underneath” can suggest more precision than summary history provides | **Scale shift / boundary.** Close the combat receipts and state that the next section compares seven registered signals. Keep the bridge conceptual but make the next page’s available/limited channels the proof. |
| 27 | Frontend bridge; only when Page 26 and at least one usable Element exist | Element keys, labels, and statuses; channels with unavailable values omitted | Heading, `SignalField` of canonical keys, support line, Endstop | Chapter 9, orientation; awe and composure | “Measured seven ways” sounds like all seven values are equally available; the support question can sound like a personality test | **Quiet evidence field.** Show each available label and its measured/limited state; make omission visible without fabricating a neutral score. The page should orient the reader before any identity language. |
| 28 | `element_distinctiveness` is not renderable in this release | No rendered evidence; module is explicitly filtered from manifest | No renderer and no progress position; hand-edited manifest entries are rejected | Intended analytical distinctiveness page, but not part of the shipped story | Any copy or visual reference would create an orphaned analytical surface and break the page-count contract | **Stay absent.** Do not add a “not ready” card or placeholder. If distinctiveness becomes shippable later, it needs a new contract/test decision, not a silent client exception. |
| 29 | `archetype`; `available`/`degraded` or narrow `not_ready` exception | Recap lines derived only from rendered pages; archetype anchor presence; preview card state | Recap heading uses first rendered line, later lines appear as beats, “Put it all together…,” then an `ArchetypeCard` preview | Chapter 10, synthesis buildup; anticipation | The preview card introduces the constant archetype before the reader has seen an evidence map; a static card can imply the identity is already known | **Evidence mosaic prelude.** Keep the recap lines as callbacks, but replace the premature identity impression with a muted map of the actual rendered anchors. The card preview may exist as a frame, not as personalized data. |
| 30 | `archetype`; same narrow exception; only page that turns the card | No per-player archetype data while module is `not_ready`; `ARCHETYPE_PLACEHOLDER`; local `archetypeRevealed` state | `ArchetypeCard` with “Reveal your archetype” button in motion mode, face-up in reduced motion/after reveal, 1-second identity hold, silent Endstop | Chapter 10, reveal; curiosity and ceremony | `THE RECURRING PLAYER` and its description are constant across users. A button makes the reveal feel personal even though no personalized result exists | **Qualified reveal gate.** Keep the interaction mechanics and page ID, but only present a personalized label/description from server-owned identity data with refs. Until then, show a clearly non-personalized “story so far” state or a neutral closure; never seed, rotate, or infer a label client-side. |
| 31 | `archetype`; included only with at least two rendered anchors | Anchor keys derived from pages 15, 17, and 21; placeholder labels/bodies currently supplied by frontend constant | Heading asks “Why THE RECURRING PLAYER?”, face-up card, gated anchor list, silent Endstop | Chapter 10, explanation; validation and trust | The anchors are presence-gated but their body text is constant and the heading names a constant. This is an explanation of a placeholder, not evidence-backed identity | **Evidence map, not rationale.** Keep the page only when a real identity has at least two valid refs. Show each actual source signal and its supported wording; absent/invalid refs remove the item. With no identity engine, do not render a personalized “why” sentence. |
| 32 | `card_collage`; card collage data and rendered-page membership | Manifest cards, card modules/labels/values/details, set of composed pages | Collage list reveals as one beat with staggered delays, then chapter close and optional dry line | Chapter 11, DNA/collection; ownership and relief | The collage can become a dense inventory after a sparse identity section; “several thousand clicks” is another generic mathematical release | **Artifact mosaic.** Use the collage as a callback wall: each card should represent a fact already encountered, and the selected line should summarize the shape, not the click count. Keep the geometry/overflow guarantees. |
| 33 | `final_identity_card`; narrow `not_ready` exception plus fallback identity resolver | `final_identity_card.data` when supplied; otherwise universe match count/window and optional display name | Compact always-face-up `ArchetypeCard`, match count/lookback, `ShareControl`, “Run it back”; name beat is optional | Chapter 11, ownership/share; completion and agency | The card still carries the constant archetype, so the final artifact can broadcast fabricated personalization; the fallback match count is honest but visually subordinate | **Artifact close with provenance.** Make scope and the strongest qualified line the shareable identity. If no server-owned Signature exists, label the close as the report’s observed shape rather than a personalized archetype. Keep share/run-back controls and privacy-safe fallback. |
| 34 | `deep`; renderer exists only when a non-null validated destination is composed | `modules.deep.data.available` plus a real destination; current `resolveDeepDestination` always returns null | If reachable: heading, second layer sentence, Deep link, optional dry line; currently never composed | Chapter 12, optional depth; intrigue | A dead CTA is correctly prevented today, but the source copy promises another layer even when no destination exists | **Conditional invitation.** Keep the slot and ID reserved. Render only when a validated destination and eligible deep analysis exist; otherwise end at Page 33 without a “coming soon” or placeholder. |

## Before → after story map

This map changes the editorial job, not the slot order. Page IDs and payload
conditions remain exactly as audited above.

| Current run | Current dominant grammar | After the revamp | Reveal grammar mix |
|---|---|---|---|
| Pages 1–7: Your Year | Five fact/support sequences, then a longest-match fact | Establish scope, show volume, nest a week inside a day, and end on one bounded match memory | Receipt first → contrast → chronology → miniature climax |
| Pages 8–11: The Good News | Bridge → wins count → streak blocks → hero list | Move from permission to good news, let a streak accumulate, then introduce a cast around the result | Reframe → tally/context → accumulation → contrast |
| Pages 12–15: Adversity | Loss blocks plus fixed microcopy → loss list → bridge → finding template | Let the sequence create pressure, state where observation ends, then ask the narrow next-choice question | Accumulation → boundary/reversal → aftermath cast → question/answer |
| Pages 16–19: Your Heroes | Conditional bridge → hero list → draggable eras → payoff lines | Return to recurring names, let chronology establish movement, then callback to one supported payoff | Callback → center/field → chronology → payoff |
| Pages 20–21: Outside the Comfort Zone | Bridge → same finding template as Page 15 | Replace “favorite/comfort” framing with a familiar-vs-changed contrast and preserve the frontier boundary | Contrast setup → contrast/frontier |
| Pages 22–24: Body Count | Three near-identical dominant stat/list pages | Make kills, assists, and deaths three perspectives on one scoreboard return, with only one selected release if earned | Impact → connection → quiet cost |
| Pages 26–27: Seven Signals | Abstract bridge → seven-channel field | Name the source of the next layer, show available/limited channels, and pause before synthesis | Scale shift → quiet evidence |
| Pages 29–31: Archetype | Recap → constant card reveal → constant “why” anchors | Accumulate only actual rendered callbacks, map evidence, and reveal a server-owned identity only when qualified | Evidence mosaic → qualified reveal → evidence map |
| Pages 32–34: DNA / depth | Dense collage → constant final card/share → currently unreachable CTA | Turn prior receipts into a standalone artifact, preserve share/run-back, and make depth a real conditional invitation | Artifact mosaic → artifact close → optional depth |

### Macro emotional curve

```text
orient → recognize scale → find a memory handle → enjoy a win → feel pressure
→ inspect what followed → return to recurring heroes → test a boundary
→ see the visible body → widen to seven signals → assemble evidence
→ earn/withhold identity → own the artifact → optionally go deeper
```

The curve should not be implemented as sentiment scoring. It is an editorial
ordering of existing states. A zero, insufficient, mixed, or historical report
can take a quieter branch while preserving the same page IDs and honest
omissions.

## Prescriptive implementation brief

### Invariants to keep

1. **Page identity is frozen.** Keep `PAGE_CHAPTER`, `STORY_MODULE_PAGES`, the
   numeric page IDs, and the `page_manifest` normalization path. Do not add
   Page 25, resurrect Page 28, or renumber the ending.
2. **Omission is compositional.** Keep the existing gates for Pages 14, 16, 20,
   27, 31, 33, and 34. A bridge is added only when it introduces a page that
   actually renders. Never add a generic fallback page to preserve visual
   symmetry.
3. **Runtime JSON wins.** Existing persisted payloads may lack story bands,
   chronology, finding content, identity slots, comparison rows, or optional
   copy. The renderer must omit or use the truthful neutral/insufficient/mixed
   state; it must not derive a new sentence from a missing field.
4. **No analytical expansion.** This brief does not authorize new estimators,
   thresholds, cohorts, rank logic, event parsing, OpenDota calls, or backend
   fields. The improved reveal is a presentation change over existing values.
5. **Evidence remains accessible.** Keep inline Evidence for findings and the
   global Methodology dialog. The foreground line and its denominator/boundary
   must remain connected for keyboard, mobile, and reduced-motion readers.
6. **Motion remains optional.** Keep the shell’s no-auto-advance behavior,
   mid-reveal completion rule, visibility/dialog pause, focus movement, and
   reduced-motion instant composition. A new grammar must work as static DOM.
7. **Humor remains bounded.** Select closes from supported page data and
   editorial rhythm. Do not make every numeric page own a joke, and do not use
   a page counter as a substitute for editorial selection.

### Reveal grammar assignments

Implement the following as explicit page-level presentation decisions. The
existing runtime primitives are sufficient: `DominantFact`,
`DominantSentence`, `Sequence`, `OrderedStack`, `HeroEras`, `SignalField`,
`InlineEvidence`, `ArchetypeCard`, and `Endstop`.

| Pages | Grammar | Implementation direction |
|---|---|---|
| 1–4 | Receipt, contrast, ledger | Keep dominant values, but vary whether the next beat is scope, duration context, or ranked split. Do not attach a dry line to every fact. |
| 5–7 | Chronology, nested peak, miniature climax | Use date relationships as the reveal. The day should read as inside the week; the longest match should land as a bounded memory object. |
| 8–11 | Reframe, tally/context, accumulation, cast | Let Page 10’s sequence settle before the count/date support. Treat Page 11 as a cast around wins, not a second leaderboard. |
| 12–15 | Accumulation, boundary, aftermath, question | Preserve terminal-state copy and evidence. Vary Page 15 from Page 21 by making the result-state comparison visual and keeping the association boundary explicit. |
| 16–19 | Callback, center/field, chronology, payoff | Use earlier loss/win context only when the relevant page rendered. Make the era interaction optional and the static sequence complete. |
| 20–21 | Contrast setup, frontier | Remove “favorite”/“comfort” implication. Show familiar and changed contexts side by side or sequentially, with neutral/mixed states intact. |
| 22–24 | Impact, connection, quiet cost | Keep all three exact totals. Change pacing and sentence order so the group reads as one scoreboard return rather than three repeated metric cards. |
| 26–27 | Scale shift, quiet evidence | Name the seven registered channels and their availability. Do not imply a hidden score or complete measurement when labels are absent. |
| 29–31 | Evidence mosaic, qualified reveal, evidence map | Build anticipation from actual recap lines and anchor refs. The card may turn only for server-owned identity data; `not_ready` must not become a personalized placeholder. |
| 32–34 | Artifact mosaic, artifact close, conditional depth | Use the collage as a visual callback, make Page 33’s scope/provenance legible in the share artifact, and keep Page 34 unreachable until a real destination exists. |

### Bridge and callback rules

- A bridge must answer “why this next?” in one sentence. It should not merely
  announce a new data type.
- Page 14 changes the question from loss to next choice; Page 16 changes it from
  result response to recurring heroes; Page 20 changes it from hero names to
  what remains across a hero change; Page 26 changes it from visible counters to
  registered signals.
- When a source page is omitted, use only the fixed combined/direct transition
  already supported by composition. Do not reference a finding, era, or anchor
  that is not in the composed page set.
- A callback must point to an actual value or label already shown in the current
  payload. Callback copy is a compatibility surface: an older report that lacks
  an optional anchor must not receive a sentence that pretends it saw one.
- The final synthesis should cite the same sources that appeared in the arc.
  “Put it all together” is allowed as a transition; it is not evidence.

### Humor selection rules

The prior code limited dry-line runs mathematically. The revamp replaces that
mechanism with an editorial gate:

1. Is the line about a supplied fact, sequence, or relationship?
2. Would the line remain true if Evidence were opened?
3. Does it avoid skill, role, motive, mental state, causality, and blame?
4. Does it still read as affectionate on a zero, loss-heavy, or limited report?
5. Does this page need humor, or is a silent Endstop the better rhythm?

Prefer one well-timed release after a sequence or callback. Avoid automatic
mathematical releases such as “several thousand clicks,” jokes that turn a
most-played hero into a personality, or wording that describes a player as
tilted, addicted, safe, reckless, or carried. If data is missing, remove the
joke with the optional surface.

### Archetype buildup and ending rules

The current code documents a narrow exception for `archetype` and
`final_identity_card` because both modules are `not_ready`. That exception must
not be widened. In particular:

- do not seed a label from `story_input_sha256`, rotate labels, or choose a
  label from hero names in the browser;
- do not call the constant `THE RECURRING PLAYER` a personalized archetype;
- do not render Page 31’s placeholder “why” as if its three anchor bodies were
  analytical findings;
- do not fabricate `identity_summary.slots`, evidence refs, confidence, or
  provenance to make the reveal card feel complete.

The earned ending can still be implemented with the current contract:

1. Page 29 recaps only pages that actually rendered. Preserve that gating and
   use the recap as a visible callback list.
2. Page 30 may preserve the reveal interaction as a shell capability, but its
   face must be clearly neutral/non-personalized until the payload supplies a
   valid identity result. The button should never imply a hidden computation
   that did not run.
3. Page 31 should explain only server-owned identity slots and refs. If fewer
   than two defensible anchors exist, composition already omits it; keep that
   omission rather than padding the page.
4. Page 32 should make the collage the memory object: cards refer back to
   observed pages, not to a new identity claim.
5. Page 33 should make report scope, match count, and the strongest eligible
   share candidate legible even when the identity card is neutral. Share and
   Run It Back remain useful without a personalized archetype.
6. Page 34 should be an actual deep-analysis invitation only when the route and
   destination are validated. Until then, ending at Page 33 is the honest
   ending, not an incomplete one.

### Acceptance checklist for the implementation owner

This is a documentation brief, not an execution report. The eventual code
change should prove:

- current and historical persisted fixtures traverse without regeneration;
- the full fixture still uses the exact current page IDs and skips 25/28/34;
- finding, degraded, zero, sparse, mixed, and unavailable branches preserve
  truthful omissions;
- each new reveal works on direct static render, reduced motion, keyboard, and
  Back/Next traversal;
- Page 15 and Page 21 no longer feel like accidental copies while preserving
  their shared evidence contract;
- no three-page mathematical joke cadence remains, and every remaining joke is
  data-bound and optional;
- identity pages never claim a personalized archetype when the payload is
  `not_ready` or lacks valid refs;
- share cards contain no private identifiers and remain legible as standalone
  artifacts;
- browser checks cover first-to-last, backward, Evidence, Methodology, Share,
  End, Read Again, 375px mobile, desktop, reduced motion, overflow, pageerror,
  console-error, and hydration-error conditions.

## Audit provenance

Files read for this audit:

- `apps/web/app/report/[reportId]/v6/story/copy.ts`
- `apps/web/app/report/[reportId]/v6/story/compose.ts`
- `apps/web/app/report/[reportId]/v6/story/motion.ts`
- `apps/web/app/report/[reportId]/v6/story/pages.tsx`
- `apps/web/app/report/[reportId]/v6/story/story-shell.tsx`
- `apps/web/app/report/[reportId]/v6/story/story-runtime.tsx`
- `apps/web/app/report/[reportId]/v6/story/payload-types.ts`
- `apps/web/app/report/[reportId]/v6/story/copy-variants.ts`
- `apps/web/app/report/[reportId]/v6/story/archetype-placeholder.ts`
- `apps/web/tests/unit/story-composition.spec.ts`
- `apps/web/tests/e2e/report-story-v61.spec.ts`
- `docs/product/v61-storytelling-research.md`

No frontend, backend, analytical, fixture, or test file was changed for this
audit. No browser, unit, or E2E test was run, as requested for this
documentation-only assignment.
