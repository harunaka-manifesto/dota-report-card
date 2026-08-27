# Dota DNA V6.1 — Presentation Direction Proposal

Status: **proposal for review. Nothing implemented.**
Task type: PRESENTATION / UI (frontend-only)
Evaluated commit: `2ce777b84bd936a416dfdc7e8cac5d758c04ae57` (`codex/v61-motion-pacing`)
Contracts read: `AGENTS.md`, `apps/web/AGENTS.md`, `docs/agent/persisted-report-compatibility.md`, `docs/product/v61-story-state-machine.md`

---

## 0. How this was evaluated, and one repo discrepancy

**Discrepancy to confirm before any implementation.** The connected working tree is checked out on `main` (`e523d85`), and `main` does **not** contain `2ce777b8`. The three primary files on `main` are the pre-motion versions. `git branch --contains 2ce777b8` returns `codex/v61-motion-pacing` and three research branches only. Everything below was evaluated against `2ce777b8` explicitly, not against the working tree. Nothing in the working tree was modified.

The experience was run, not read. `tests/e2e/fixture-server.mjs` was booted against the `2ce777b8` renderer and driven with a real browser at 1440×900, 1000×700, 768×500, 375×812 and 375×600, in both motion modes, across `v61-3-fixture`, `v61-0-fixture` and `v61-historical-production-fixture`. Timings below are measured, not inferred. No OpenDota calls were made; no report was regenerated.

Compatibility spot-check (unchanged, and it holds): the historical production-shaped fixture composes 10 pages, correctly omitting `pool-layers`, all `finding-*`, and `coherence`, with zero page errors. The 0-finding fixture composes 12 and still reaches `share` and `end`. Conditional omission is working and must survive whatever we do next.

---

## 1. Current-experience critique

I have separated defects that are measurable and would fail review from things that are legitimately your call.

### 1.1 Genuine problems, in severity order

**D1 — Content is silently clipped off-screen at 375px on the fourth screen of the story.**
On the scope receipt at 375×812, the final fact renders as `5 most-played heroes` whose bounding box ends at **x = 492.5 in a 375px viewport** — 117px of the sentence is cut off. The subtitle `give us somewhere familiar to start` is cut off with it. Same at 768×500 (right edge 800 in a 768 viewport). Cause: `.odometer { white-space: nowrap }` wrapping the digits *and* the unit, inside an `h1` at `clamp(48px, 10vw, 96px)`.

This is the worst kind of layout bug because the current release gate cannot see it: `.viewport { overflow-x: hidden }` swallows the overflow, so `document.documentElement.scrollWidth - clientWidth` reads **0**, and the existing Playwright assertion `toBeLessThanOrEqual(1)` passes on a screen that is visibly truncated. The check is measuring the wrong thing.

**D2 — Every page takes two to three seconds to finish arriving, and the first 600ms of that is a blank screen.**
Measured, time from `Next` to element at full opacity, 1440×900, motion enabled:

| Page | bridge | headline | detail |
|---|---:|---:|---:|
| `lead-hero` | 645ms | 1583ms | 3085ms |
| `hero-front-row` | — | 648ms | 2111ms |
| `pool-width` | 654ms | 1564ms | 3119ms |
| `pool-movement` | 642ms | 1540ms | 3100ms |
| `finding-transfer` | 650ms | 1554ms | 3114ms |
| `finding-post-loss` | 687ms | 1546ms | 3089ms |
| `coherence` | 641ms | 1546ms | 3083ms |
| `signature-setup` | 679ms | 1572ms | 3073ms |
| `signature-reveal` | — | 674ms | 2098ms |
| `share` | 644ms | 1579ms | 3117ms |

A frame-by-frame capture of one bridge page: at t=300ms the screen is **completely black** — the outgoing page has left and the incoming has not mounted. From t=600 to t=2100 the *only* thing on screen is a 15px, 58%-opacity grey bridge sentence. The headline lands at 2.1s. The supporting observation lands at 3.1s.

Three separate failures are stacked here:

- The delays are absolute from mount (`animation-delay: 1400ms` / `2400ms` on `.detail`, `2000ms` / `3000ms` on `.evidenceButton`), so they are the same on all fourteen pages regardless of narrative job. Arrival, a hero list, and the Signature all run the same clock.
- The order inverts the product principle. The claim appears 1.5 seconds before the observation that supports it. For 1.5 seconds the reader is looking at an unsupported assertion, which is exactly the posture the backstage/onstage split exists to avoid.
- The bridge gets a 1.5-second solo. A bridge is connective tissue; it is being staged as a beat.

**D3 — Rapid `Next` presses advance nothing and blank the screen.**
Eight `Next` presses at 80ms intervals over 789ms advanced **zero** pages; page opacity was 0 from ~410ms onward, and the story settled on the *first* page only after the presses stopped. `navigate()` clears the in-flight `transitionTimer` and restarts a fresh 280ms timer while `pageIndex` stays uncommitted, so any press cadence faster than 280ms starves the commit indefinitely. A reader who double-taps gets a black screen and no progress. This is a correctness bug, not a pacing preference.

**D4 — The odometer displays numbers that are false while it animates.**
Each digit column rolls independently through the full 0–9 wheel while the unit sits at full opacity from the start, so on the receipt the screen legibly reads `14 matches` and `6 most-played heroes` for several hundred milliseconds en route to `72 matches` and `5 most-played heroes`. `.odometerDigits` also animates its `width`, so a 3-digit → 2-digit change shifts the whole line horizontally mid-roll and the digits visibly mis-register.

For a product whose entire premise is that we earn the right to say something, a number that legibly states a wrong fact for 400ms is a rigor problem, not a motion preference. It is also the one animation in the report that a reader could screenshot.

**D5 — Backward navigation replays the full reveal.**
Measured `Back` into `finding-transfer`: headline @1544ms, detail @3091ms — identical to forward. `key={page.id}` on `.page` remounts the node and every CSS animation restarts. Going back means waiting three seconds to re-read something you already read. The brief asks that Back feel like reversing the investigation; today it is a full re-performance.

**D6 — The bridge and the headline overlap on `signature-setup`.**
Reproduced at both 1440×900 and 375×812: `The individual findings have finished pretending they're unrelated.` is rendered struck through by `The pattern underneath the patterns.` The `.center` layout has no reserved gap between `.bridge` and `.lead` at that type size, and the headline's focus ring compounds it. This lands on the page immediately before the narrative climax.

**D7 — The headline carries a visible focus ring on every page turn, for pointer users.**
Verified with a real mouse click on the right edge zone: `document.activeElement.tagName === "H1"` and `el.matches(":focus-visible") === true`, so Chromium paints a UA outline around the headline. Every screenshot in this evaluation shows a hard rectangle around the headline. The focus move itself is right and must stay — it is what makes the story navigable by screen reader. The visual cost of it should not be paid by pointer users.

**D8 — Short-height mobile composes as if height were unlimited.**
At 375×600, `signature-reveal` has **305px of content below the fold** with no scroll affordance, no type step-down, and no layout adaptation. The brief names short-height mobile as a support target; today the page simply runs off the bottom.

**D9 — The Signature climax says the same sentence twice within one viewport.**
`identity_summary.headline` is the `h1`, and `slots.primary.text` is the same string rendered again in the right column under a `PRIMARY` label. Confirmed in both the current fixture and the historical fixture. The single most important screen in the report reads as a rendering error.

**D10 — Evidence is a separate application with an inverted hierarchy.**
The dialog's title is the claim you just read, set at `clamp(26px, 5vw, 44px)`, on top of the same claim at 68px behind it. The genuinely new information — `72 comparable matches`, `18 sessions`, alternatives, limitations — is the smallest and dimmest type on screen. The dialog opens centered with no spatial relationship to the `ⓘ` that summoned it, and its 1px 35%-white border on a `rgb(0 0 0 / .82)` backdrop over a black page gives it almost no edge. On mobile it covers half the screen and the claim alone fills five lines of it.

The `ⓘ` affordance itself is a 23px glyph occupying its own 44px grid column on desktop, vertically detached from the claim it supports; on mobile it floats alone in dead space below the text with nothing connecting it to anything.

**D11 — Ten of fourteen pages are the same composition.**
`.split` — centered bridge, left 68px headline, right detail column — carries `lead-hero`, `hero-front-row`, `pool-width`, `pool-layers`, `pool-movement`, all `finding-*`, `coherence`, `signature-reveal` and `share`. Chapters are typographically labelled but spatially identical. On `finding-post-loss` the right column is 40% of the page width holding one eight-word sentence; the rest is void.

**D12 — The alignment axis breaks on every bridge page.**
`.bridge` is `justify-self: center` while `.headline` is left-aligned in the `.lead` column. The eye lands centered, then jumps left. Between 768px and 1024px, where `.split` is a single column capped at 880px, this is at its worst.

**D13 — Mobile is a collapsed desktop.**
Same order, same alignment, same rhythm, same reveal clock, content top-loaded with large dead space beneath on most pages. The progress bar becomes fourteen ~19px dashes across 335px — at 20 pages it is unreadable as a progress indicator.

**D14 — The Coherence page asserts convergence and shows none.**
`The findings stop looking separate.` followed by one supporting sentence. The one page whose entire job is to demonstrate a relationship between things you have already read is the one page with no visual relationship on it. The composer already knows which pages were referenced (`referencedPages`), and the renderer does not use that knowledge spatially.

**D15 — Share is the densest screen in the report and follows the sparsest.**
Display name, signature line, all seven signal labels, five hero names, three finding headlines and a button, all in undifferentiated grey at one size. The signature line also appears twice on that screen (page subtitle plus share summary). After the Signature reveal, this reads as a data dump rather than a closing artifact.

### 1.2 Matters of taste — your call, not defects

- Monochrome plus Plus Jakarta Sans. It works and it should stay.
- The voice of the bridge lines. Reads well; not a design issue.
- Sentence-case declarative headlines. Right for the product.
- `ⓘ` versus a word. I'd argue for a word, but reasonable people differ.
- The 8.3-second scope receipt's *existence*. I think the length is a risk (see §6) but the receipt itself is the best idea in the current build.
- Headline size **as an absolute value** is taste. Headline size **relative to its measure** is not: 68px in a ~480px column is roughly seven characters per line and produces five- and six-line headlines. That specific mismatch is a craft defect.

---

## 2. Three creative directions

These are three different answers to "what is a page in this report", not three skins.

### Direction A — **Case File**

**Central idea.** The report is an investigation record. A page is a *sheet*, and every sheet has a persistent margin. The claim and the observation that supports it live on the same sheet, on the same measure, physically adjacent — and evidence unfolds the sheet downward in place rather than opening a window on top of it. Nothing floats over the story.

**Layout behavior.** A narrow persistent margin column (chapter name, position in the investigation) and a wide sheet. The claim sits at the sheet's optical top third; the supporting observation sits directly beneath it on the same left edge, joined by a hairline rule that starts at the claim's baseline. Evidence expands the sheet under the observation, pushing nothing off-screen because the sheet is already the scroll container.

**Motion behavior.** Type is *set*, not faded: an `overflow: hidden` wrapper with an inner `translateY` reveals lines in reading order. Between pages the margin persists and only the sheet changes, so the frame of the investigation never blinks. The margin's position marker moves — that movement is the transition's subject.

**Interaction behavior.** Press-and-hold anywhere on a sheet dims the interpretation and brightens the observation plus its hairlines: a "show your work" gesture that reuses the muscle memory already taught by the receipt. Keyboard equivalent on the same element. Evidence is a disclosure on the sheet, not a dialog.

**Typography character.** One display size only, 40–52px. Heavy use of 11px letterspaced caps as structural labels. Tabular figures everywhere. Evidence sets on a deliberately narrower measure than the story so the reader can feel they have gone one layer down without a new surface.

**Emotional arc.** Recognition = a blank sheet receiving its first mark. Familiarity = names in the margin. Structure = layers stacked on one sheet. Adaptability/Adversity/Expression/Time = one sheet each, margin advancing. Coherence = previously seen sheet markers migrate into the margin of a single sheet. Signature = the margin collapses into the sheet; there is nothing left to index.

**Mobile.** Margin becomes a 24px top strip carrying the same information. Sheet is full-bleed. Evidence expands inline, which is strictly better than a half-screen dialog.

**Reduced motion.** Line reveals become instantaneous; the margin marker still moves position (it is layout state, not decoration); hairlines are static; hold-to-inspect is unchanged.

**Strengths.** Strongest backstage identity of the three. Structurally fixes D10 (evidence detachment), D11 (repetition — the margin gives chapters a real spatial job), D14 (Coherence has something to converge). Very Dota-native in tone without any graphic.

**Risks.** Can drift clinical and cold if the type is not warm. The margin costs horizontal space that mobile does not have. "Paper" is a metaphor one step away from skeuomorphism, and the moment it grows a texture or a shadow it is dead.

**Complexity.** Medium. CSS grid, one inline-disclosure state, one new hold state. No library.

---

### Direction B — **Continuous Field**

**Central idea.** Not slides. One tall investigation surface that the viewport travels along. A claim you have read does not disappear — it recedes upward and compresses to a single line in a residue stack at the top edge. By the time you reach Coherence, the lines it is talking about are literally still on screen above it, so convergence is shown rather than asserted.

**Layout behavior.** Single generous column. Each station occupies roughly one viewport. A persistent compressed stack of prior claims pinned to the top edge, growing by one line per page.

**Motion behavior.** A `translateY` on a track, 420ms. The outgoing claim compresses to one line as it exits; the incoming station rises. Backward reverses exactly — the residue line re-expands into the claim. This is the only direction where Back is genuinely a reversal.

**Interaction behavior.** Residue lines are focusable and clickable to jump back. Edge zones still work. Never auto-advances.

**Typography character.** Modest display, 40–48px, long measure, evidence inset narrower. The residue stack is 13px with a hard truncation rule.

**Emotional arc.** Extremely strong from Coherence onward. Signature = the whole residue stack collapses into one line.

**Mobile.** The residue stack is the problem: at fourteen pages it eats the top third of a 812px screen and more of a 600px one.

**Reduced motion.** The track jumps rather than slides; residue still accumulates. Meaning survives.

**Strengths.** Best answer to narrative continuity and to D14 and D5. Genuinely memorable.

**Risks.** Serious ones. It fights the `100dvh` single-page model the whole state machine is built on. Fourteen residue lines is visual noise, and the report can be twelve to fifteen pages depending on findings — the stack is unbounded by the composer. Focus management across a virtual track is where accessibility bugs live. It risks reading as a long scroll page, which destroys the deliberate page-turn that makes the current build feel authored. And it puts the most pressure on the smallest viewport.

**Complexity.** High. Track container, per-station measurement, a residue model, reworked focus handling, and meaningful risk to the existing `data-page-id` e2e contract.

---

### Direction C — **Two Voices**

**Central idea.** The fundamental unit of this report is not a page — it is a pair: *what was observed*, and *what it means*. Every page is composed as a call and response between two typographic registers on one shared measure, and **the observation lands first**. The reader earns the claim in reading order instead of being told and then shown. Chapter identity comes from the ratio and the order of the two voices, not from new geometry.

**Layout behavior.** Two bands stacked on one measure, separated by a hairline whose vertical position encodes the chapter's ratio. Familiarity is observation-heavy, hairline low. Structure is balanced, hairline centered. Adversity leads with interpretation and answers with observation — the bands swap order. Coherence sets three observations against one interpretation. Signature dissolves the hairline entirely: one voice, nothing beneath it.

**Motion behavior.** One motion idea, applied everywhere: **replacement**. The observation band writes; the interpretation band answers by pushing the hairline to its chapter position. That single push is the page's transition and its internal staging at once. Nothing else moves.

**Interaction behavior.** Evidence expands the *observation* band — it is more of the same voice, one layer deeper, which is exactly what evidence is. Hover/focus on the interpretation raises the observation's contrast, wiring claim to support without a click.

**Typography character.** Two registers, defined once and never violated. Observation: 15–17px, tabular figures, +0.02em, up to 68ch. Interpretation: 34–48px, −0.02em, 20–28ch. Bridges are a third, quieter register at the top of the sheet, never a solo.

**Emotional arc.** Recognition is one voice alone. Familiarity introduces the second. Every finding chapter is a question answered. Coherence stacks answers. Signature returns to one voice, and the return is the payoff.

**Mobile.** Best of the three by a distance: two stacked bands are natively a phone layout, so mobile stops being a collapsed desktop and becomes the reference composition that desktop widens.

**Reduced motion.** Bands appear composed, hairline already at its chapter position. Order and meaning fully preserved because they are encoded in layout, not in timing.

**Strengths.** Directly fixes the pacing inversion in D2, which is the deepest problem in the current build. Makes the pharma/wrapped duality *structural* rather than decorative. Cheapest of the three. Lowest accessibility risk. Gives Evidence an obvious home.

**Risks.** Less cinematic than A. The hairline device could read as mechanical if it moves too visibly. It depends on there being an observation string on every page, and there is not: `pool-width`, `signature-setup`, `arrival` and `end` have a headline and no supporting observation. The behavior when a voice is absent must be defined, not improvised.

**Complexity.** Low to medium. Two band classes, chapter-keyed ratios, one replacement motion. No library, no new state beyond a nav-source flag.

---

## 3. Recommended direction

**Recommendation: Direction C as the composition grammar, with Direction A's persistent margin and in-place evidence adopted into it. Direction B is rejected, with one idea kept.**

Call it **Case Notes**: two voices on a sheet, in a margin that remembers where you are.

**Why C is the spine.** The most serious thing wrong with the current build is not that it looks repetitive — it is that it consistently shows the conclusion before the evidence and then waits 1.5 seconds. That is the product principle inverted in the timing layer. C fixes it structurally rather than by retuning delays, which means it cannot regress the next time someone changes an animation value. Nothing else on the list is as load-bearing.

**Why A's margin comes with it.** C on its own gives chapters a ratio but not a place. The margin supplies chapter differentiation, position-in-investigation, and — critically — a persistent frame that does not blink between pages, which is what removes the blank-screen artifact in D2 without any timing trick. It also gives Coherence something real to do: referenced findings already exist in the composer as `referencedPages`, and the margin is where they can gather.

**Why A's in-place evidence comes with it.** The Evidence dialog is the clearest violation of "one layer beneath the story, not a separate application". An inline disclosure in the observation band inherits context by construction, needs no opening choreography, and preserves orientation on close for free because nothing ever moved.

**Why B is rejected.** Its payoff is concentrated in two pages and its cost is spread across the whole architecture: it fights `100dvh`, it is worst on the smallest viewport, it has an unbounded residue stack, and it puts the `data-page-id` contract and the focus model at risk. That is a bad trade against a release gate that requires historical persisted reports to keep rendering.

**The one idea kept from B.** A phrase may be carried between two specific consecutive pages where the composer already guarantees a relationship — `signature-setup` → `signature-reveal`, and `pool-width` → `pool-layers`. Not a general mechanism, not applied anywhere else, and it degrades to nothing when either page is omitted.

**Balance check.**

| Criterion | Assessment |
|---|---|
| Emotional impact | High and earned. The payoff is the return to one voice at Signature, set up from page one. |
| Comprehension | The largest single gain. Observation before claim; one alignment axis per page; complete page in under 700ms. |
| Dota identity | Comes from restraint and forensic tone, not ornament. No graphics, no gradients, nothing to break the rules over. |
| Restraint | One motion idea, one display size, two type registers. Easy to keep honest. |
| Accessibility | Lowest-risk of the three. Meaning lives in layout, so reduced motion is a real equivalent rather than a downgrade. |
| Feasibility | Three files. No dependency. No composer change. No `StoryPage` change. |
| Compatibility | Chapter behavior keys off `page.chapter` and `page.id`, which every persisted report already has. Absent voices degrade by omission. |

---

## 4. Motion system

### 4.1 Principles

1. **Motion answers "what changed."** If a reader cannot say what moved and why, the animation is removed.
2. **One thing moves at a time.** Everything else is already still when it starts.
3. **Direction encodes narrative direction.** Forward advances along the reading axis; backward is the exact inverse, never a different animation.
4. **Nothing the reader needs arrives after 900ms.** The only exception is the Signature reveal.

### 4.2 Tokens

```
--ease-enter: cubic-bezier(.22, 1, .36, 1);   /* existing, keep */
--ease-exit:  cubic-bezier(.4, 0, 1, 1);
--ease-move:  cubic-bezier(.32, .72, 0, 1);   /* hairline, margin marker */

--d-tap:    140ms;   /* control feedback */
--d-swap:   220ms;   /* text replacement */
--d-page:   320ms;   /* page change, total */
--d-settle: 480ms;   /* numbers, evidence disclosure */
--d-hold:   640ms;   /* Signature only */

--stagger: 70ms;     /* max 3 steps, max 210ms total added delay */
```

### 4.3 Page transition rule

The frame never blanks. The margin, the progress bar and the hairline are persistent DOM; only the two bands change.

| t | Forward | Backward |
|---:|---|---|
| 0ms | Press committed. `pageIndex` updates **immediately**. | Same. |
| 0–140ms | Outgoing bands leave: opacity → 0, `translateY(-4px)`, `--ease-exit`. | Identical but `translateY(+4px)`. |
| 80ms | Incoming frame mounts under the outgoing layer. No gap. | Same. |
| 120ms | Margin marker moves to the new position, `--d-page`, `--ease-move`. Incoming bridge (if any) appears here. | Marker moves back; bridge of the destination page appears. |
| 220ms | **Primary reading target visible.** Observation band for observation-led chapters, interpretation band for interpretation-led chapters. | Both bands appear together — you have read this page before. |
| 420ms | Second band visible; hairline arrives at its chapter position. | — |
| 620ms | Evidence affordance visible. | 220ms. |
| **≤700ms** | **Page complete.** | **≤320ms.** |

**Backward is deliberately faster and unstaged.** Reversing an investigation means re-seeing, not re-performing. This is the fix for D5 and it costs one boolean.

**The bridge becomes the transition.** Instead of a 1.5-second solo, the incoming page's bridge line is what occupies the 120–220ms window while the bands change. It is present in the composed page too, so reduced motion and screen readers get it as ordinary top-of-page text. This satisfies "bridges that begin before the next page fully arrives" and deletes the dead time in one move.

### 4.4 Chapter transition behavior

Chapters are not separate animations. A chapter change moves two things it would otherwise not move: the margin's chapter label swaps by replacement (`--d-swap`), and the hairline travels to the new ratio using `--ease-move` over `--d-page` instead of appearing in place. Within a chapter the hairline does not move at all. That difference is the entire chapter-transition vocabulary, and it is enough.

### 4.5 Metric behavior

`OdometerNumber` keeps its public props, its `aria-label`, its `data-odometer-value` attribute and its rendered text. Its internals change:

- **No value cycling.** Digits are revealed by a mask travelling upward over the settled number, `--d-settle`, `--ease-enter`. **No false intermediate value is ever displayed.** (Fixes D4.)
- **Unit appears at +80ms after the digits settle**, never before. A number is never legible next to a unit it does not yet equal.
- **Width is reserved from the final value** in `ch`. No `width` transition, no horizontal shift.
- **Where two numbers are compared**, the second replaces the first (`--d-swap`); it does not roll between them.
- Digits use `font-variant-numeric: tabular-nums` (already present) so the mask edge is straight.

### 4.6 Interruption and cancellation

- Navigation commits on press. `pageIndex` advances immediately; the outgoing content animates out from a held layer. **One press, one page, always.** (Fixes D3.)
- A press during a transition cancels the in-flight exit and enters the new page at full speed. It never restarts a hold.
- Presses arriving faster than 120ms skip entrance choreography for pages that were never seen.
- Document hidden: all timed sequences pause (the receipt already does this correctly — extend the same `pauseReasons` set to the page reveal).
- Dialog open: navigation keys are already suppressed. Keep.

### 4.7 Dialog behavior

- **Evidence is no longer a dialog.** It is a disclosure inside the observation band: 200ms height + opacity, `--ease-enter`, focus moves to the first revealed line, `Escape` and the same control collapse it and return focus. Orientation is preserved because nothing moved.
- **Methodology and Exit stay native `<dialog>`.** 160ms, 6px rise. Their backdrop gets a real edge: raise the surface off pure black and give the dialog a 1px border at 55% rather than 35%.

### 4.8 Reduced motion equivalents

Every rule has a static equivalent that preserves **order and meaning**, never merely "no animation":

| Rule | Reduced-motion equivalent |
|---|---|
| Band entrance | Both bands composed at once, no transform. |
| Hairline travel | Hairline already at its chapter ratio on mount. |
| Margin marker | Marker at its position on mount; label already swapped. |
| Bridge-as-transition | Bridge is ordinary top-of-page text (it always is). |
| Number mask | Number and unit printed together. |
| Evidence disclosure | Instant open/close, focus behavior unchanged. |
| Carried phrase | Phrase present on both pages, no movement. |
| Receipt | Static accumulated list (see §6), hold-to-pause still functional. |

---

## 5. Responsive layout system

### 5.1 Measures and caps

| Element | Measure | Max |
|---|---|---|
| Interpretation (display) | 20–28ch | — |
| Observation (body) | 45–68ch | 640px |
| Bridge | 40–56ch | 560px |
| Evidence disclosure | 52–62ch | 580px |
| Page frame | — | **1120px** (down from 1280) |

The page cap drops because the two-band grammar wants a shared measure, not two stretched columns. This alone resolves D11's 40%-empty right column.

### 5.2 Breakpoints

| Range | Behavior |
|---|---|
| ≤ 479px | Compact phone. Margin becomes a 24px top strip. Bands full-bleed, 20px gutters. Display steps to 30–36px. |
| 480–767px | Phone. As above, display 34–40px. |
| 768–1023px | Tablet. Margin returns as a 96px left column. Single shared measure, left-aligned. Display 38–44px. |
| ≥ 1024px | Desktop. Margin 140px. Bands on a shared 640px measure offset from the margin, not stretched across the viewport. Display 40–52px. |
| `(max-height: 700px)` | Short. Display steps down one stop; band gap halves; bridge collapses into the margin strip. |
| `(max-height: 560px)` | Very short. Display steps down two stops; if the observation band still exceeds its space it scrolls **within the band**, bounded by a hairline edge and a visible scroll cue (a fade edge would need a gradient, which the constraint list rules out), and the page itself never scrolls. (Fixes D8.) |

### 5.3 Alignment rules

- **One alignment axis per page.** A centered bridge above a left-aligned headline is forbidden. (Fixes D12.)
- `arrival`, `signature-reveal` and `end` are the only centered compositions. Everything else is left-aligned to the margin edge.
- Statement pages anchor their optical center to 42% of the available height, not 50% — text reads high.

### 5.4 Chapter-specific layout variants

Keyed off the existing `page.chapter` string. No new data.

| Chapter | Hairline ratio | Order | Note |
|---|---|---|---|
| Recognition | none | interpretation only | One voice. |
| Familiarity | 0.38 | observation → interpretation | Names first. |
| Structure | 0.50 | observation → interpretation | Layers visible. |
| Adaptability | 0.55 | interpretation → observation | The question leads. |
| Adversity | 0.62 | interpretation → observation | Highest contrast page. |
| Expression | 0.50 | observation → interpretation | Two measures kept apart. |
| Time | 0.44 | observation → interpretation | Sequence reads down. |
| Coherence | 0.70 | observations (n) → interpretation | Stacked answers. |
| Signature | none | interpretation only | Hairline dissolves. |
| Share / End | none | closing artifact | See §6. |

An unknown chapter string falls back to `0.50 / observation → interpretation`. Historical reports with chapters we have not seen render correctly rather than breaking.

### 5.5 Progress indicator

Same DOM, same `role="progressbar"`, same `aria-valuenow` / `aria-valuetext` — the existing assertions must keep passing. Presentation changes below 600px width or above 12 pages: segments merge into one continuous rule with chapter ticks rather than page dashes. Fourteen 19px dashes stop being information. (Fixes D13.)

### 5.6 Vertical overflow

No page may exceed the viewport without a visible cue. The rule is: the interpretation band never scrolls; the observation band may, with a hairline edge and a focusable scroll region; the page frame never does.

---

## 6. Page-by-page storyboard

Conditional pages stay conditional. Every page below disappears cleanly when its composer gate fails, and the margin, progress and page count recalculate — unchanged from today.

### `arrival` — Recognition
- **Purpose.** "That's my account."
- **Start.** Empty sheet. Margin present but unmarked.
- **Final.** Centered. Eyebrow `DOTA DNA`, name-led headline, one quiet line beneath. No hairline, no observation band.
- **Reading order.** Eyebrow → headline → line.
- **Entrance.** Margin rule draws once (240ms). Headline at 220ms. Line at 380ms. Nothing else.
- **Internal staging.** None. This page is one gesture.
- **Interaction.** Edge zones, Next, keyboard. No evidence.
- **Exit.** Bands leave upward; margin persists and takes its first mark.
- **Backward.** Not reachable except via Read again, which enters at 0ms with no stagger.
- **Mobile.** Identical, display 34–40px, anchored at 42% height.
- **Reduced motion.** Composed at once.

### `scope-receipt` — Recognition
- **Purpose.** Establish scope and consent to the method. This is the strongest idea in the build and it should keep its ambition.
- **Change I am proposing.** The receipt **accumulates instead of replacing**. Each fact prints as a new line beneath the previous ones, so at the end all four facts are on screen together — which is what a receipt is, fixes the "what did it say?" problem, gives reduced motion an exact equivalent, and lets each line wrap on a normal measure. **That last point is the fix for D1**: with `white-space: normal` on the line and `nowrap` confined to the digit group, `5 most-played heroes` cannot be clipped at 375px.
- **Duration.** Compress 8.3s → **5.4s** (1.3s per fact, 0.5s settle). Eight seconds of non-interactive time on screen two is the report's highest drop-off risk, and accumulation makes a shorter hold readable.
- **Start.** Blank sheet, margin marked `01`.
- **Final.** Four left-aligned lines: `365 days / of Dota`, `72 matches / made the cut`, `7 signals / did the measuring` with the seven labels beneath, `5 most-played heroes / give us somewhere familiar to start`. Hero line omitted when `heroCount` is 0, exactly as today.
- **Reading order.** Top to bottom, permanently.
- **Entrance / staging.** Line n prints with the number mask (§4.5), unit at +80ms, subtitle at +200ms. Signal labels stagger at 70ms, capped.
- **Interaction.** Press-and-hold or Space pauses, unchanged, with `data-paused` preserved. Add a one-time 11px hint under the first line — it disappears after the first pause or after fact two. The hold is currently undiscoverable.
- **Exit.** Standard.
- **Backward.** Returning to the receipt shows the **completed** list, no replay. `data-receipt-stage` reports final. (Today it restarts, which is a small cruelty.)
- **Mobile.** Same list, 20px gutters, display 30–36px. Lines wrap.
- **Reduced motion.** The completed list, immediately. Identical final state — the current static variant already does this and it is the right model.

### `lead-hero` — Familiarity
- **Purpose.** "That sounds like how I play."
- **Composition.** Observation band leads: hero name at display weight with `24 matches · 33% of the year` on the same measure. Hairline at 0.38. Interpretation beneath: `Most-played is a starting point. One hero still doesn't describe your Dota.`
- **Reading order.** Bridge (margin) → name + numbers → interpretation.
- **Entrance.** Name at 220ms; numbers mask at 300ms; hairline to 0.38 at 420ms; interpretation at 420ms.
- **Interaction.** None beyond navigation. No evidence ref exists here and none should be implied.
- **Exit / backward.** Standard; backward composed.
- **Mobile.** Native — this page is already two bands.
- **Reduced motion.** Composed.

### `hero-front-row` — Familiarity
- **Purpose.** Widen from one name to a group.
- **Composition.** Observation band is the four rows on the shared measure; interpretation above them is the short headline. Order stays observation-led but the headline is the *first* row's context, so it sits at the top with the hairline immediately under it (ratio 0.38 inverted for this page only — the list is the payload).
- **Entrance.** Headline 220ms; rows stagger 70ms, **capped at three visible steps** so a five-row list does not take 350ms.
- **Interaction.** Rows are not interactive. Do not make them interactive.
- **Mobile.** Rows keep their hairline separators; numbers right-aligned with tabular figures.

### `pool-width` — Structure
- **Purpose.** "I hadn't noticed that."
- **Composition.** No observation string exists for this page. **Voice-absent rule applies**: the interpretation band takes the full measure, the hairline is omitted, and the evidence disclosure control takes the position the observation band would have occupied. The page reads as a claim with its support one press away — which is truthful about what the report has.
- **Entrance.** Headline 220ms; subtitle 380ms; evidence control 620ms.
- **Interaction.** Evidence disclosure expands beneath the subtitle. This is the report's first evidence moment and it should feel like opening a drawer in the same desk, not a new window.
- **Mobile.** Same; disclosure expands inline.

### `pool-layers` — Structure
- **Purpose.** The pool has layers.
- **Composition.** Observation band is the three bands (`REGULAR` / `ROTATING` / `OCCASIONAL`) as three labelled lines on one measure. Hairline 0.50. Interpretation beneath.
- **Carried phrase.** When `pool-width` preceded it, its headline's final clause persists in the margin as this page's chapter note. This is the one B-idea retained, and it degrades to nothing if `pool-width` was omitted.
- **Entrance.** Bands stagger 70ms ×3; hairline 420ms; interpretation 420ms.
- **Interaction.** Evidence disclosure when `evidenceRefs` is non-empty — and **not rendered at all** when the composer produced no evidence, which is already the behavior and must survive.

### `pool-movement` — Structure
- **Purpose.** The pool moved.
- **Composition.** Timeline as three sequential observation lines (`Earlier` / `Middle` / `Recent`), reading down. Hairline 0.44 (Time-like ratio despite the Structure chapter — sequence wants a lower centre). Interpretation beneath.
- **Entrance.** Lines stagger **in chronological order**, 70ms, which is the one place where stagger carries meaning rather than decoration.
- **Backward.** Composed; the stagger does not replay.

### `finding-transfer` / `finding-post-loss` / `finding-combat` / `finding-session`
- **Purpose.** "That explains something." Each is a question answered.
- **Composition.** Interpretation-led (the family question, from `subtitle`), hairline at the chapter ratio, observation beneath (`description[0]`, the server's interpretation line), evidence disclosure under that.
- **Why interpretation-led here specifically.** These are the only pages where the composer supplies a *question*. A question before its answer is the correct order and the only place in the report where the claim may precede the observation.
- **Entrance.** Eyebrow 120ms; question 220ms; claim 340ms; hairline + observation 460ms; evidence control 620ms.
- **Internal staging.** Three steps maximum. The eyebrow is not a step.
- **Interaction.** Evidence disclosure. Hover/focus on the claim raises observation contrast from 72% to 88% — a free, quiet way to wire claim to support.
- **Adversity gets the report's one contrast move**: its ground steps from `#000` to `#0A0A0A` and its hairline is 1px brighter. Nothing else. That is the whole "contrast for Adversity" idea, and it should stay that small.
- **Mobile.** Native two bands.
- **Reduced motion.** Composed; contrast step still applies (it is not motion).

### `coherence` — Coherence
- **Purpose.** "These things actually connect."
- **Composition.** This page finally does its job. The composer already computes `referencedPages`. Render **each referenced finding's chapter label as a line in the observation band**, stacked, with the interpretation beneath them at hairline 0.70. The lines are the same chapter labels the reader has been seeing in the margin for the last four pages, so recognition is immediate.
- **Entrance.** The referenced chapter labels **move in from the margin's position** — a 320ms `--ease-move` translate from the margin x-offset to the band. This is the single most expressive motion in the report and it is spent here, once, on the one page whose subject is convergence. Then the interpretation arrives at 540ms.
- **Reading order.** Referenced labels → interpretation → supporting lines.
- **Interaction.** Evidence disclosure lists the same rows the current dialog does.
- **Backward.** Composed, labels already in place, no travel.
- **Mobile.** Labels arrive from the top strip instead of the left margin. Same idea, correct axis.
- **Reduced motion.** Labels present in the band on mount. The convergence is still legible because it is spatial, not temporal.
- **Conditional.** Unchanged — omitted entirely when fewer than two pages share identity refs.

### `signature-setup` — Signature
- **Purpose.** The breath before the reveal.
- **Fixes D6.** Centered, one voice, a reserved minimum gap of `2.5rem` between the bridge and the headline, and the bridge takes the margin's chapter note position rather than floating above the headline.
- **Composition.** Bridge in margin. Headline centered. Slot names (`Primary. Twist. Anchor.`) as a single quiet line beneath.
- **Entrance.** This is the one page allowed a hold: headline at 220ms, then **640ms of nothing**, then the slot-names line at 860ms. The pause is the point.
- **Exit.** The slot-names line **is carried** into `signature-reveal` as its labels. B's idea, second and last use.
- **Mobile / reduced motion.** Composed; the hold becomes a static composition.

### `signature-reveal` — Signature
- **Purpose.** The climax. "This is recognizably my Dota."
- **Fixes D9.** The headline is the Signature. When `slots.primary.text` matches the headline after normalization, **the PRIMARY slot renders as a label and scope caption attached to the headline** rather than repeating the sentence. When they differ, both render. This omits a duplicate render; it invents nothing and reinterprets nothing.
- **Composition.** Interpretation alone at the top on a wide measure — no hairline, because the Signature has no band beneath it. `PRIMARY` label + scope directly under the headline. `TWIST` and `ANCHOR` as two equal statements below, at observation register, clearly subordinate.
- **Reading order.** Eyebrow → Signature → primary scope → twist → anchor → supporting lines → evidence.
- **Entrance.** `--d-hold` choreography, the only page over 700ms: eyebrow 120ms, Signature 260ms, hairline **dissolves** (the only time it leaves) 420ms, primary caption 560ms, twist 720ms, anchor 860ms, supporting lines 1000ms, evidence 1150ms. Total 1.15s and it is earned once.
- **Interaction.** Evidence disclosure = the three-part evidence map.
- **Backward.** Composed at 320ms, no hold. You do not re-earn a reveal.
- **Mobile.** Display steps to 30–36px so the Signature is **three lines, not six**. At 375×600 the twist and anchor move into a scrollable observation band with a hairline edge and a scroll cue. (Fixes D8.)
- **Reduced motion.** Fully composed; hairline absent on mount.
- **Conditional.** Unchanged — both Signature pages omitted together when `signatureIsReady` is false.

### `share` — Share
- **Purpose.** A deliberate closing artifact, not a summary dump.
- **Fixes D15.** Three tiers instead of one grey block: (1) the Signature line, at interpretation register, once — remove the duplicate by rendering the page subtitle only when it differs from `share.signature`; (2) the findings, as up to three observation lines; (3) heroes and signal labels demoted to a single 12px caption row. The copy control is the page's only primary action and looks like it.
- **Composition.** Centered, framed by the margin, with a visible boundary — this is the one page in the report that should read as an object with edges.
- **Entrance.** Signature 220ms; findings stagger 70ms ×3 at 380ms; caption row 620ms; button 700ms.
- **Interaction.** Copy: button label does not change; a `role="status"` line beneath confirms, exactly as today. On failure the selectable input appears, as today. Add a 140ms press response so the tap feels answered.
- **Mobile.** Same three tiers, stacked; caption row wraps to two lines.
- **Reduced motion.** Composed.

### `end` — End
- **Purpose.** Close and offer the two honest next moves.
- **Composition.** Centered, one voice, three text controls on one row with real separation (`gap: 32px`, each 44×44 minimum, which they already meet vertically but not visually).
- **Entrance.** Headline 220ms; line 380ms; controls 560ms.
- **Interaction.** `Read again` returns to `arrival` with **no stagger** and direction `backward` — a rewind, not a fresh start.
- **Mobile.** Controls stack at ≤479px with 12px gaps.
- **Reduced motion.** Composed.

### Voice-absent rule (applies to every page)

| Available | Composition |
|---|---|
| Both voices | Two bands, chapter hairline ratio. |
| Interpretation only | Full-measure interpretation, no hairline, evidence control takes the observation's position. |
| Observation only | Full-measure observation, no hairline, no interpretation placeholder. |
| Neither | The composer would not have produced the page. |

No placeholder text, no invented supporting line, no "not available" copy unless the state machine already specifies that exact string.

---

## 7. Interaction state matrix

| Interaction | Idle | Active / pressed | Focus | Interrupted | Document hidden | Reduced motion |
|---|---|---|---|---|---|---|
| **Pointer edge zone (56px)** | No visual. Cursor unchanged. | 140ms 2px inward nudge of the page frame on the pressed side, released on commit. | n/a | Press during transition commits the next page immediately. | Press ignored while hidden. | Nudge omitted; commit identical. |
| **Semantic Back / Next** | Visually hidden, in tab order. | Standard press feedback. | **Becomes fully visible on focus** — opacity 1, solid ground, 2px outline, 56×44 minimum. Non-negotiable and already correct today. | Same as edge zone. | — | Identical. |
| **Keyboard ←/→** | — | Commits immediately, one page per press. | Suppressed while a dialog is open and inside form fields (already correct). | Repeat key advances one page per repeat, never starves. | Ignored. | Identical. |
| **Press-and-hold receipt** | Hint line visible until first pause or fact two. | `data-paused="true"`, all sequences pause, `aria-live` announces. | Space held = same state; blur releases. | Navigation while held releases cleanly. | `hidden` is its own pause reason; stacking is already correct. | Hold still pauses the accumulation and the hint still shows. |
| **Evidence open** | Control at 620ms, 44×44, labelled with a word not a glyph. | Disclosure expands 200ms; focus moves to first revealed line. | Control has visible focus; expanded region is a focusable landmark. | Navigating away collapses without animation. | Paused. | Instant expand, same focus move. |
| **Evidence close** | — | Collapses 200ms; **focus returns to the control**; scroll position unchanged because nothing moved. | — | — | — | Instant. |
| **Exit** | Text control, top right. | Opens native dialog, 160ms. | Ring visible. | — | — | No rise. |
| **Exit — Stay / Exit report** | — | `Stay` closes and restores focus to the opener (correct today). | — | — | — | — |
| **Methodology** | Control on `end` only. | Native dialog, 160ms. | Ring visible. | — | — | No rise. |
| **Copy link** | Button, primary treatment. | 140ms press response; `role="status"` announces `Report link copied.` | Ring visible. | — | — | Status appears without transform. |
| **Copy failure** | — | Status announces failure; selectable input appears and is selected (correct today). | Input focusable and labelled. | — | — | Identical. |
| **Read again** | Text control on `end`. | Returns to `arrival`, direction backward, no stagger, focus to headline. | Ring visible. | — | — | Identical. |
| **Headline focus after navigation** | — | — | **Ring shown only when the last navigation source was keyboard.** Root carries `data-nav-source="pointer\|keyboard"`; the focus move itself always happens. (Fixes D7 without weakening keyboard support.) | — | — | Identical. |

---

## 8. Implementation plan

### 8.1 Files

**Modify — these three only.**

| File | Change |
|---|---|
| `apps/web/app/report/[reportId]/v6/report-story-v6.tsx` | Transition commit model; `data-chapter` / `data-nav-source` attributes; `OdometerNumber` internals; `ScopeReceipt` accumulation; Evidence dialog → inline disclosure; `SignatureSlots` duplicate-primary handling. |
| `apps/web/app/report/[reportId]/v6/report-story-v6.module.css` | Token block; two-band grammar; chapter-keyed variants; responsive system; progress presentation; reduced-motion equivalents. |
| `apps/web/tests/e2e/report-v6.spec.ts` | New assertions in §8.5; existing assertions preserved except the receipt's stage timings, which change deliberately. |

**Do not touch.** `story-v61.ts`, `normalize-v61-report.ts`, `types.ts`, `page.tsx`, `fixture-server.mjs`, the historical fixture payload, anything under `services/`, `infra/`, `migrations/`, or any analytical code. No package added.

### 8.2 The `StoryPage` contract stays closed

Chapter behavior is derived in the **renderer** from `page.chapter` and `page.id`, both of which already exist on every persisted report, via a local `const CHAPTER_LAYOUT: Record<string, {ratio: number; order: "observation-first" | "interpretation-first"}>` with a default fallback. `data-chapter` is a DOM attribute, not a `StoryPage` field. **No property is added to `StoryPage` and the composer is not modified.** This is the discipline that keeps a presentation change from becoming a contract change.

### 8.3 CSS architecture

1. A token block at the top of the module: eases, durations, measures, band ratios, neutral steps. Every value below references it.
2. Two band classes, `.voiceObservation` and `.voiceInterpretation`, each defining one type register and nothing else.
3. Chapter variants as `[data-chapter="Adversity"]` selectors that set **only** `--hairline-ratio`, `--band-order` and, for Adversity, `--ground`. No chapter selector may set type, spacing or timing — that is how twelve chapters become twelve bespoke layouts nobody can maintain.
4. Responsive rules in one block at the bottom, in the breakpoint order of §5.2, including both `max-height` queries.
5. One `prefers-reduced-motion` block that maps each rule to its §4.8 equivalent. Not a blanket `animation: none`.

**Specificity discipline.** Today `.page:has(.bridge) .detail { animation-delay: 2400ms }` and friends form a second timing system layered on the first. Delete that pattern entirely; timing lives in one place, driven by tokens and a `--step` variable, never by structural `:has()` overrides.

### 8.4 Local helpers and state

Three small additions, no library:

- `useCommittedTransition()` — commits `pageIndex` on press and returns `{ outgoing, direction, phase }`; the outgoing node is held for 140ms. Replaces the current timer-driven commit and is the fix for D3.
- `usePrintedNumber()` — replaces the digit-wheel internals of `OdometerNumber`. **Public props, `aria-label`, `data-odometer-value` and rendered text are unchanged**, so `getByLabel("24 matches")` and the `data-odometer-value` assertions keep passing.
- `navSource` ref on the root — `"pointer"` or `"keyboard"`, set by the handler that initiated navigation, read only by CSS.

State changes: `phase` becomes `{ from, to }`; add `bridgeLead: boolean`; add `evidenceOpen: boolean` (replacing the `"evidence"` dialog case). `openDialog` keeps `"methodology"` and `"exit"`.

### 8.5 Playwright coverage

**Add.**

1. **Real clipping check.** For every text node on `scope-receipt` at 375×812 and 768×500, assert `getBoundingClientRect().right <= innerWidth + 1`. The existing `scrollWidth` check cannot catch D1 because `overflow-x: hidden` masks it — this is the assertion that would have caught it.
2. **One press, one page.** Eight `Next` presses at 80ms must land eight pages ahead (or at `end`), and page opacity must never read 0 for more than 100ms during the sequence.
3. **Page completion budget.** For each composed page, time from `Next` to final-content opacity ≥ 0.98 must be **< 900ms** (Signature reveal: < 1300ms).
4. **No blank frame.** Sample page opacity every 30ms across a transition; assert it is never 0 while a `[data-page-id]` is mounted.
5. **No overlap on `signature-setup`.** Bridge and headline bounding boxes must not intersect, at 375×812 and 1440×900.
6. **Short height.** At 375×600, every composed page either fits or exposes a focusable scroll region with a visible cue.
7. **Evidence disclosure.** Opens inline, moves focus, `Escape` collapses, focus returns to the control, `data-page-id` unchanged throughout.
8. **Pointer focus ring.** After a real edge click, the headline is `document.activeElement` **and** `data-nav-source="pointer"`; after `ArrowRight`, `data-nav-source="keyboard"`.
9. **Backward is composed.** `Back` into a finding page reaches final content in < 400ms.
10. **Signature has no duplicate sentence.** On both fixtures, the `signature-reveal` page's text must not contain the identity headline twice.

**Preserve unchanged.** All page-id composition and omission tests; the conditional-page matrix; `aria-valuetext`; the historical production fixture sweep; the analytics forbidden-field scan; `img, svg, canvas` count of 0 — **which means every rule and hairline in this proposal is a CSS border, never an SVG**; the removed-UI and private-field scan; the copy-link origin/pathname test.

**Run timing assertions in Chromium only**, matching the existing receipt-timing tests, which already `test.skip` on non-Chromium projects. Layout, clipping, focus and compatibility assertions run on every project.

**Deliberately changed.** The receipt's stage timings (2200/1850/2800/1800 → the §6 accumulation schedule). `data-receipt-stage`, `data-paused`, the space-hold behavior and the exactly-once `report.scope_sequence_completed.v1` guarantee all stay.

### 8.6 Browser risks

| Risk | Mitigation |
|---|---|
| `clip-path` text reveal in Safari | Use `overflow: hidden` + inner `translateY`. No `clip-path` on text. |
| `:focus-visible` on programmatic focus differs across engines | Do not rely on it. Gate the ring on `data-nav-source`, which we control. |
| `100dvh` on older Safari | Already in use; keep the existing `min-height: 100%` fallback on `.page`. |
| `text-wrap: balance` unsupported | Purely cosmetic degradation; measures are capped in `ch` regardless. |
| `@media (max-height)` and mobile URL-bar resize | Test at 375×600 and 375×560 with the bar both shown and hidden; avoid values that flip across a 60px delta. |
| `:has()` in older engines | Delete the `:has()`-based timing overrides rather than extending them (§8.3). |
| Native `<dialog>` behavior variance | Reduced surface — only Methodology and Exit remain dialogs. |

### 8.7 Not over-engineering this

No animation library. Everything specified is `transform`, `opacity`, `height`, one mask, and one held node — CSS and the current React implementation cover all of it, and a library would add a dependency for effects we have explicitly ruled out.

No new page types, no new page IDs, no `StoryPage` fields, no composer changes, no new analytics events, no chapter-bespoke layouts beyond three CSS custom properties each. Two new hooks and one ref. If the diff grows past those three files, something has gone wrong and the change should stop and be re-scoped.

---

## 9. Acceptance criteria

Observable, checkable, and mostly automatable.

**Reading rhythm**
- Every composed page reaches final content in **< 900ms** from press (Signature reveal < 1300ms), measured as today's table was measured.
- Page opacity is never 0 for more than 100ms while a page is mounted. No blank frame exists.
- Backward navigation reaches final content in **< 400ms** and replays no stagger.
- No page has more than three staged steps, and no stagger adds more than 210ms.

**Hierarchy**
- Every page uses exactly two type registers plus labels. A third register appearing anywhere is a defect.
- On every page with both voices, the observation is legible before or at the same moment as the interpretation — never after.
- One alignment axis per page. No centered element sits above a left-aligned element.
- No sentence appears twice within one viewport on any page of either fixture.

**Meaningful motion**
- For each animation in the module, a reviewer can state what changed and where to look. Any that cannot be defended in one sentence is deleted before review.
- Numbers never display a value other than 0 or their final value. The unit never appears before the digits have settled.
- The margin-to-band travel on Coherence is the only translate over 8px in the report.

**Narrative continuity**
- The margin, progress and hairline are continuously present across every transition.
- The bridge is visible before the page it introduces has composed.
- The two carried phrases (`pool-width` → `pool-layers`, `signature-setup` → `signature-reveal`) appear on both pages, and their absence when either page is omitted causes no layout gap.

**Mobile**
- Zero clipped text at 375×812, 375×600 and 768×500, verified by bounding-box assertion rather than `scrollWidth`.
- The Signature headline is **three lines or fewer** at 375px.
- Every page at 375×600 either fits or exposes a visible, focusable scroll cue.
- The progress indicator remains legible as progress at fourteen pages on a 375px screen.

**Accessibility**
- `prefers-reduced-motion` preserves reading order, staged meaning and every interaction. No feature is reachable only through motion.
- Semantic Back/Next remain hidden but fully revealed on focus, at 56×44 or larger.
- All interactive targets are 44×44 or larger, verified by bounding box, not by `min-height` alone.
- Keyboard and pointer reach identical outcomes for every interaction in §7.
- The headline focus move still occurs on every navigation; only its ring is conditional.
- No `img`, `svg` or `canvas` element exists in the report.
- No horizontal document overflow at 375, 768, 1440, or at 200% zoom.

**Compatibility**
- `v61-historical-production-fixture` composes the same 10 pages, in the same order, with zero page errors and zero console errors.
- All conditional-omission cases produce the same page sets as today.
- No report regeneration, no schema change, no analytics event added or renamed, no OpenDota call.
- `git diff --name-only` touches exactly the three files in §8.1.

**Completion and engagement, without dark patterns**
- Pages never advance automatically; every advance follows a press or a key.
- No swipe navigation, no quiz, no artificial suspense, no countdown, no upsell.
- The only hold longer than 700ms in the entire report is the Signature reveal, and it happens once.
- Exit is available from every page and confirms before leaving.
- If completion rate is instrumented, the target is measured on `report.story_page_left.v1` dwell distribution — a healthy result is a **flatter** dwell curve than today's, since today's floor is inflated by 2–3s of unavoidable animation wait per page.

---

## 10. What I want from you before implementation

1. **The branch discrepancy in §0** — confirm `codex/v61-motion-pacing` is the base, since the working tree is not on it.
2. **Direction sign-off** — C-as-grammar plus A's margin and inline evidence, or a different weighting.
3. **One new UI string.** The receipt's hold hint is the only new copy in this proposal. It is instructional, not analytical, but the state machine puts copy-catalog strings behind source-binding review — tell me whether you want to author it, drop it, or route it through that review.
4. **The receipt.** I am proposing accumulation and 8.3s → 5.4s. That is the change most likely to be a matter of taste rather than defect, and it is your call.
5. **The Signature duplicate (D9).** My fix omits a duplicated render. If you would rather change what the composer selects, that is a `story-v61.ts` change and a different conversation.
6. **Whether D1 and D3 get fixed now, separately, ahead of any redesign.** They are live defects on the evaluated branch and they do not need this proposal to be approved.
