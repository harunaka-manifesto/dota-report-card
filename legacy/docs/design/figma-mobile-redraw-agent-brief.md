# Dota Report Card — Figma Mobile Redraw Agent Brief

## Execution contract

You are the implementation agent for the Free DNA mobile redraw. Perform the
Figma edit. Do not return another proposal, moodboard, or implementation plan.

1. Open Figma file `D3uhn7WPXFsX1DiCIVklyg`.
2. Locate section node `247:32`. Preserve that exact section node and preserve
   its existing link. Do not replace, rename, move, or recreate the section.
3. Build the replacement frames and reusable system inside section `247:32`.
   The mobile frame size is exactly `393 × 852` pixels.
4. Build and screenshot the complete replacement set before deleting any old
   children. Keep the existing 24-screen wireframes in place until the new
   frames have passed the validation checklist in this brief.
5. After validation, delete the old 24-screen wireframes and only the old
   children that they contain. Do not delete the section node, its link, or
   any shared library asset that is reused by the replacement.
6. Return the created, changed, and deleted node IDs, plus the required final
   screenshots. The edit is not complete until those IDs and screenshots are
   returned.

The final response must state that the Figma edit was executed. Do not say that
the work is ready for another agent and do not ask the user to apply the edit.

## Code and content source of truth

Use the verified implementation in the shared repository as the behavioral
source of truth. The Figma file is a visual reconstruction of this behavior;
it must not invent a second product flow.

- `apps/web/app/report/[reportId]/dna/report-story-v4.tsx` — `ReportChapter`,
  `REPORT_CHAPTERS`, chapter composition, qualified/unavailable filtering,
  selected Element/Pattern behavior, Hero Portfolio questions, Hero Mirror
  reveal, privacy-safe analytics events, and human fallback copy.
- `apps/web/app/components/story/glyphs.tsx` — the typed 29-glyph registry,
  palettes, geometry IDs, 64 × 64 SVG viewBox, gradients, monochrome mode,
  knockout mode, accessible names, and uniqueness guard.
- `apps/web/app/components/story/glyph-registry.ts` — the public registry seam
  used by the report and test checks.
- `apps/web/app/styles/tokens.css` — core color, type, spacing, radius, focus,
  and control variables.
- `apps/web/app/styles/base.css` — self-hosted Plus Jakarta Sans, base controls,
  focus treatment, loading progress, and reduced-motion defaults.
- `apps/web/app/styles/landing.css` — landing specimen grid and profile-input
  layout.
- `apps/web/app/styles/report.css` and `apps/web/app/styles/responsive.css` —
  chapter layouts, desktop rail, mobile dock, tiles, detail panels, Hero
  Mirror, share controls, mobile breakpoints, and reduced-motion behavior.
- `apps/web/app/globals.css` and `apps/web/app/layout.tsx` — style import order,
  font loading, metadata, and the dark application shell.
- `apps/web/app/page.tsx` and `apps/web/app/components/analysis-form.tsx` —
  profile entry, privacy copy, SSE status updates, visibility-aware polling,
  literal errors, and report routing.
- `apps/web/app/components/share/share-controls.tsx` — name/avatar toggles,
  share/download fallback behavior, and the privacy guarantee.
- `services/api/app/content/free_dna/en.json` — legacy-compatible page,
  Element, Pattern, Portfolio, story, and presentation copy.
- `services/api/app/content/free_dna/semantic_en.json` — finite semantic
  outcome/recommendation copy.
- `services/api/app/share/service.py` — deterministic final SVG composition,
  Midnight Specimen share geometry, safe avatar allowlist, escaping, and
  privacy footer.
- `tone_of_voice.md` — identity cadence and anti-patterns.

Do not change application code as part of this Figma task. If the code and an
old wireframe disagree, use the code and the requirements below.

## Product flow and mobile navigation

The final experience is one normally scrolling identity report:

`Profile → analysis → Summary → Elements → Patterns → Heroes → You → share`

The report has exactly five chapters:

1. `Summary` — the leading identity shape, visible immediately.
2. `Elements` — the personal ingredients behind the shape.
3. `Patterns` — relationships that persist between heroes.
4. `Heroes` — the combined Hero Portfolio and its next experiment.
5. `You` — the teased-then-revealed Hero Mirror and share artifact.

At mobile widths, use a persistent bottom dock with exactly five items:
`Summary`, `Elements`, `Patterns`, `Heroes`, `You`. The dock is 64 px high plus
`env(safe-area-inset-bottom)`, has a dark shell, a top divider, an active
chapter accent, and a minimum 48 px hit target per item. Use reusable dock
components and accessible button labels. Do not create page fractions, screen
numbers, progress dots, scroll snapping, or a 24-screen sequence.

At desktop widths, preserve the implementation intent of the fixed left
chapter rail and normally scrolling chapters. The Figma deliverable itself is
mobile-only, but do not draw a desktop-only interaction into the mobile frames.

## Required 393 × 852 frame set

Create these 12 canonical frames, in this order. Name them with the numeric
prefix so the sequence is unambiguous.

### 01 — Profile input

Show the landing page from `HomePage` and `AnalysisForm`:

- top line: `Free DNA / 01` and `A closer look at your play`;
- eyebrow: `THE SHAPE OF YOUR PLAY`;
- headline: `Your Dota habits, made visible.`;
- lead: `Give us a public profile. We'll turn the matches into a compact
  portrait of how you move through Dota — the parts you recognize, and the
  parts that keep sneaking back into the draft.`;
- label: `Public profile, Steam ID, or Steam profile URL`;
- large input with `193875165` placeholder;
- primary button: `Build report`;
- helper: `Try 193875165 if you want to take it for a spin.`;
- quiet privacy note: `Public profile details only. No password, no account
  connection, and no performance theatre required.`;
- right/low visual object: the eight-cell aurora specimen grid with the
  captions `Arrive early`, `Hold the line`, `Change shape`, `Keep pace`, `Find
  the edge`, `Take the long way`, `Reset`, and `Return`;
- specimen caption: `Identity is a pattern, not a rank.` / `Built from the way
  you actually play.`

On a 393 px viewport, stack the specimen below the form while preserving the
20 px reading gutter and the large headline hierarchy.

### 02 — Analysis in progress

Show the same profile surface in its busy state:

- button becomes `Reading your pattern…` and is disabled;
- status panel has `Free DNA / Reading`;
- headline: `Finding the shape in your matches.`;
- animated-looking progress track with a static reduced-motion equivalent;
- status examples from `stageCopy`: `Finding your public profile.`, `Your
  player is in view.`, `Looking through your recent matches.`, `Finding the
  moments that repeat.`, `Turning match history into habits.`, `Looking for the
  heroes that feel like you.`, `Giving your Elements a name.`, `Arranging your
  Elements.`, `Connecting the Patterns.`, `Building your Hero Portfolio.`,
  `Putting your Dota shape together.`, and `Your pattern is ready.`;
- no fake percentage, sample count, confidence label, source label, or method
  explanation.

### 03 — Identity dashboard / Summary

Use a full-height `Summary` chapter frame:

- kicker `01 / SUMMARY / YOUR CURRENT SHAPE`;
- the player display name or `Your Dota identity`;
- one dominant identity headline sourced from the leading qualified Pattern,
  with the leading Element as the fallback;
- one explanatory signature sentence;
- primary action `See the pieces ↘`;
- secondary action `Meet the hero pool`;
- one aurora identity tile with the leading Pattern/Element glyph, caption
  `YOUR LEADING SIGNAL`, label, and a short human explanation;
- three quiet orientation beats: `01 Read the headline`, `02 Follow the texture`,
  `03 Choose your next experiment`.

The Summary must communicate the leading identity without requiring the user to
open another chapter. Keep it conclusion-first; do not display quality,
confidence, coverage, evidence, cohort, denominator, provenance, source, or
methodology labels.

### 04 — Element grid

Use the `Elements` chapter:

- kicker `02 / ELEMENTS / THE RAW MATERIAL`;
- title `The pieces of your Dota pattern`;
- lead `These are the tendencies that keep turning up in the way you move
  through a game.`;
- a two-column mobile grid of available Elements only;
- square raised tiles, 8 px grid gap, glyph at 52 px in its own clipped art
  cell, `ELEMENT` caption, Element label, and a maximum two-line narrative;
- selected tile uses the chapter accent border and inner selected state;
- unavailable individual Elements are omitted. If the entire feature cannot
  resolve, show the human state `Still forming` and a short explanation.

The implementation has 18 registered Elements. The frame may scroll within the
chapter; do not compress all 18 into unreadable microtype.

### 05 — Element detail

Show one selected Element state beneath the grid:

- selected glyph at 88 px in a square detail-art cell;
- Element label as an eyebrow;
- conclusion-first detail headline;
- if a score exists, a left/right lean meter with human axis labels and no
  numeric score;
- if the score is unavailable, use `This one is still finding its edges.`;
- a short note such as `Right now, this reads as …` or `The useful read is
  still taking shape.`;
- 24 px panel padding on desktop intent, 18 px on the mobile detail panel.

### 06 — Pattern grid

Use the `Patterns` chapter:

- kicker `03 / PATTERNS / THE CONNECTIONS`;
- title `The habits hiding between the heroes`;
- lead `A pattern is the part that keeps happening even when the surface
  details change.`;
- show qualified, story-eligible Patterns only;
- two-column square tile grid on mobile, with Pattern glyph, `PATTERN` caption,
  label, and conclusion-first lead;
- selected Pattern has the chapter accent border and inner selected state;
- if no Pattern resolves, show `No pattern wants the spotlight yet. That is a
  valid answer.` under the `Still forming` state.

Do not show a count of qualified Patterns, a page fraction, or a reason why a
different Pattern did not qualify.

### 07 — Pattern detail and next experiment

Show a selected Pattern detail panel:

- Pattern glyph at 92 px;
- Pattern label;
- personal interpretation headline;
- short lead describing the relationship without proof scaffolding;
- an experiment card with the caption `NEXT EXPERIMENT` and one useful action;
- use the actual semantic copy when safe, otherwise the human fallback from
  the implementation;
- do not draw `What we saw`, `Why it matters`, `What this actually means`,
  `Evidence details`, confidence, coverage, raw metrics, or provenance.

The server retains evidence fields and historical presentation keys for schema
compatibility, but those fields are not part of this identity-facing Figma
surface.

### 08 — Combined Hero Portfolio

Use one `Heroes` chapter frame, not separate legacy pages:

- kicker `04 / HEROES / THE PORTFOLIO`;
- title `Your hero pool is a point of view`;
- lead `The names move around. The way you solve problems leaves a clearer
  trail.`;
- three square overview cards: `Common thread`, `The exception`, and `Pool
  evolution`;
- each card shows the available personal conclusion or `Still forming` / a
  human no-clear state;
- three question cards: Common Thread, The Exception, and Pool Evolution;
- each question supports selected choices, a reveal action, a revealed result,
  and a no-clear/unavailable state;
- use `Reveal the read`, `Read revealed`, `YOU SPOTTED IT`, `A USEFUL
  CORRECTION`, and `USEFUL ANSWER` as appropriate;
- one practical next experiment remains the dominant action;
- no forced guess options when an entire portfolio feature is unavailable.

Keep the chapter readable as one combined portfolio. Do not recreate the former
24-screen Wrapped sequence.

### 09 — Hero Mirror closed

Use the `You` chapter with the Mirror teaser closed:

- kicker `05 / YOU / THE MIRROR`;
- title `One last comparison`;
- lead explaining that the report ends with the hero that most clearly reflects
  usual decisions;
- a larger rounded Hero Mirror card (the main deliberate exception to square
  geometry);
- card label `HERO MIRROR`;
- human closed title/copy;
- primary button `Reveal Hero Mirror`;
- gesture hint `Swipe across the card, or use the button.`;
- show no hero portrait unless a specific hero is the subject of the revealed
  state.

The closed Mirror is teased until the `You` chapter. It is not a required
Summary or Heroes tile.

### 10 — Hero Mirror revealed

Show the revealed Mirror state in the same card:

- for an available Mirror, show the named hero and a comparison table with
  `Behavior`, `Your shape`, and the hero name;
- comparison rows are `Involvement`, `Finishing`, `Deaths`, and `Role context`;
- preserve the identity framing: the hero is a visual rhyme, not a personality
  diagnosis or skill grade;
- for unavailable/no-clear Mirror, show `No single hero mirrors your current
  shape yet.` and `That is still a useful result. Your identity is not asking
  for one mascot today.`;
- missing behavior values use `Still forming`.

The Mirror interaction supports click/tap, keyboard Enter/Space, and horizontal
drag. In Figma, show the closed and open frames and annotate the transition as
an interaction prototype if appropriate.

### 11 — Share preview and customization

Show the final share controls beneath the `You` chapter:

- eyebrow `Share preview`;
- a preview of the deterministic final SVG;
- name toggle `Include name`;
- avatar toggle `Include avatar`;
- primary action `Share report`;
- secondary action `Download card`;
- literal status examples `Report link copied.`, `Card download started.`,
  `Copy the report link from your browser to share it.`, and `The share card
  could not be generated.`;
- privacy note: `Your account ID is never included in a share card.`

The final SVG is `1080 × 1350` (4:5 transport size) with a dark Midnight
Specimen shell, warm text, square section geometry, clipped layered aurora
gradients, grain/dither, identity headline, strongest Elements/Patterns/Hero
Portfolio/Mirror, safe escaped text, allowlisted HTTPS avatar handling, and the
footer `PRIVATE BY DEFAULT · NO PLAYER ID · NO RAW MATCH DATA`. It is rendered
by `share-svg-5.0.0` and must never display raw IDs, raw match rows, proof
counts, or internal enum values.

### 12 — Component strip

Create a compact state inventory frame at 393 × 852 containing representative
instances of the shared components, each with a visible label outside the
component where useful:

- landing input default, focused, invalid, and busy;
- loading progress and reduced-motion loading;
- literal error/failed analysis state;
- report `Still forming` unavailable state;
- no-clear Pattern, Portfolio, and Mirror states;
- selected Element tile and selected Pattern tile;
- Hero Mirror closed/open states;
- share fallback/error state;
- keyboard focus ring and disabled button state.

This frame is a QA inventory, not a thirteenth product screen. Keep it clearly
labelled as `COMPONENT STRIP`.

## Visual system

### Midnight Specimen language

- Structural shell: near-black void, warm-white reading surfaces, strict square
  geometry, and luminous aurora identity cells.
- Default radius: `0px`.
- Larger rounding only for avatars, the Hero Mirror (`20 px` desktop intent,
  `16 px` mobile), and the final share artifact (`12 px`).
- Clip every aurora mesh inside its own grid cell. Do not let a gradient blob
  float across unrelated cells.
- Use restrained grain/dithering over large gradients.
- Do not use glassmorphism, generic uncontained gradient blobs, glossy 3D art,
  neon borders, decorative hero art, stock icon packs, letters inside glyphs,
  or hero silhouettes.
- A hero portrait is allowed only when the specific hero is being discussed.

### Core variables

Use these exact values as Figma color variables. Hex case is not meaningful;
the value is.

| Variable | Value |
| --- | --- |
| Void | `#0B0C0B` |
| Surface | `#141513` |
| Raised | `#1C1E1B` |
| Dark line | `#30332E` |
| Paper | `#F2EFE7` |
| Muted paper | `#DDD9CF` |
| Ink | `#101110` |
| Text | `#F7F4EC` |
| Muted text | `#A3A59D` |
| Coral | `#F27D68` |
| Saffron | `#F4BB57` |
| Lilac | `#B7A8E8` |
| Cobalt | `#4C7DFF` |
| Cyan | `#68D4D8` |
| Violet | `#8F70D8` |
| Magenta | `#E96BA7` |
| Orange | `#F18B47` |
| Chartreuse | `#B9E65D` |
| Amber | `#F4B04F` |
| Aqua | `#5DD4C6` |
| Crimson | `#E35B63` |
| Electric blue | `#549BFF` |

Chapter accents in the verified report CSS are:

| Chapter | Accent | Accent 2 | Accent 3 | Background |
| --- | --- | --- | --- | --- |
| Summary | `#FF7568` | `#F5BB49` | `#AD97FF` | Void |
| Elements | `#4B7CFF` | `#35D8E8` | `#9B75FF` | Surface |
| Patterns | `#ED4FA6` | `#FF9147` | `#46398E` | Void |
| Heroes | `#C1EE4F` | `#FFB847` | `#43D9D0` | Surface |
| You | `#E64C62` | `#8C69FF` | `#3F9AFF` | Void |

### Typography

Create a Plus Jakarta Sans variable font family/style set from
`apps/web/app/fonts/PlusJakartaSans-Variable.ttf`. Use the same family for all
Figma text styles:

| Style | Size / leading | Weight | Tracking |
| --- | --- | --- | --- |
| Display | `56 / 0.91` | 800 | `-0.055em` |
| Chapter title | `40 / 0.96` | 800 | `-0.055em` |
| Card title | `24 / 1.04` | 750–800 | `-0.045em` |
| Lead | `18 / 1.38` | 500 | normal |
| Body | `15 / 1.5` | 500 | normal |
| Label | `11 / 1.2` | 700–800 | uppercase, `0.12–0.14em` |
| Metadata | `12 / 1.35` | 600 | normal |

Use tabular figures for personal numbers. Do not introduce a second typeface.

### Geometry and layout

- Mobile gutter: 20 px. The verified 393 px report uses this gutter at the
  chapter level.
- Mobile grid: four-column intent, 8 px gap; two columns for the Element,
  Pattern, and glyph tile grids at the 393 px breakpoint.
- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 72 px.
- Primary controls: minimum 48 px high.
- Primary reading panels: 24 px internal padding; mobile detail panels may use
  18 px where the code does.
- Tiles: square, 1 × 1, 2 × 1, 2 × 2, or full width; keep one dominant
  headline, one visual object, and one obvious action per state.
- Mobile dock: 64 px plus safe-area inset.
- Desktop intent: 12-column content area with fixed left chapter rail; do not
  make the mobile frames depend on the rail.

## Exact 29-glyph registry

Create reusable components named `Glyph/Element/{Name}` and
`Glyph/Pattern/{Name}`. Every component must use a normalized `64 × 64` vector
frame with 8 px optical padding, work at 20/32/64 px and hero scale, remain
legible in monochrome, and use no letters, stock icons, or silhouettes.

The geometry ID and two-color palette below are the exact values in
`apps/web/app/components/story/glyphs.tsx`. Recreate the corresponding
`GlyphShape` geometry; do not substitute an icon with a similar name. Use
gradient strokes/fills on neutral surfaces, `currentColor` in monochrome, and
light/dark knockout treatment over aurora tiles.

### Elements (18)

| Key | Name | Palette | Geometry ID | Construction |
| --- | --- | --- | --- | --- |
| `hero_pool_breadth` | Breadth | `#2D6BFF → #35D8E8` | `three-expanding-rays` | Three rays expand from one centre, with three open corner markers. |
| `hero_pool_stability` | Stability | `#68748F → #9A9CFF` | `braced-central-square` | Central square held by four outside braces. |
| `hero_exploration_rate` | Exploration | `#7753F7 → #FF72C7` | `broken-orbit-escaping-dot` | Broken orbit with an escaping arrow and dot. |
| `toolkit_breadth` | Toolkit | `#FFAE42 → #FF6D32` | `asymmetric-four-lobed-cross` | Asymmetric four-lobed cross with unequal arms. |
| `post_loss_familiarity_shift` | Familiarity | `#FF806F → #E83D6F` | `nested-returning-doorways` | Three nested returning doorway loops. |
| `role_breadth` | Role | `#3D55D9 → #B39AFF` | `five-sector-tilted-pentagon` | Tilted pentagon divided into five sectors. |
| `combat_involvement` | Involvement | `#FF9B31 → #FFE15B` | `converging-arrows-central-spark` | Four converging arrows around a central spark. |
| `finisher_orientation` | Finishing | `#E53F45 → #FF893E` | `closing-aperture` | Four closing aperture arms and a central circle. |
| `death_exposure` | Deaths | `#F0444F → #4C323A` | `interrupted-descending-pillar` | Descending pillar interrupted at its centre. |
| `off_pool_performance` | Transfer | `#39D7D0 → #3276E9` | `offset-bridge-platforms` | Offset bridge stepping between platforms. |
| `off_pool_activity_stability` | Presence | `#B5E85A → #29B9A3` | `open-radiating-rings` | Open radiating rings with cardinal rays. |
| `performance_volatility` | Volatility | `#F450B5 → #8057E8` | `unequal-wave-broken-frame` | Unequal waveform inside a broken frame. |
| `recent_form_shift` | Form | `#7CE6BB → #356ADD` | `tilted-rising-plane` | Tilted plane with a rising inner line. |
| `recent_activity_shift` | Pace | `#FFD744 → #FF7B30` | `accelerating-diagonal-slashes` | Three accelerating diagonal slashes with small lead marks. |
| `session_length_tendency` | Duration | `#76D67E → #35D6D1` | `elongated-hourglass` | Elongated hourglass with curved sides. |
| `late_session_performance` | Drift | `#BBA6FF → #4E83DA` | `progressively-offset-bands` | Four progressively offset horizontal bands. |
| `post_loss_activity_shift` | Tempo | `#FF5CC8 → #FF8744` | `alternating-beat-columns` | Four alternating beat columns of different heights. |
| `post_loss_performance_response` | Recovery | `#5EE290 → #B9E83E` | `upward-rebound-path` | Rebound path rises through a final arrow. |

### Patterns (11)

| Key | Name | Palette | Geometry ID | Construction |
| --- | --- | --- | --- | --- |
| `same_playbook` | Same Playbook | `#865CFF → #40D8E8` | `different-tiles-shared-center` | Four different outer tiles share one central circle. |
| `comfort_edge` | Comfort Edge | `#F06C89 → #FFD662` | `crossed-inner-square` | Inner square crossed beyond its outer boundary. |
| `partial_transfer` | Partial Transfer | `#3ED5D0 → #FA7F7A` | `half-dissolving-bridge` | Bridge starts solid and dissolves into separated marks. |
| `versatile_core` | Versatile Core | `#61D77C → #4C79DC` | `unequal-hex-spokes` | Unequal spokes radiate from a central hexagonal frame. |
| `proven_flexibility` | Proven Flexibility | `#3F70E6 → #B7E04E` | `articulated-bending-lattice` | Articulated lattice bends around two central nodes. |
| `controlled_presence` | Controlled Presence | `#B1E85A → #28B9A5` | `field-square-brackets` | Radiating field is held by four square brackets. |
| `session_fade` | Session Fade | `#FF9A40 → #8B5BE6` | `descending-arc-dimming-nodes` | Descending arc with progressively dimmer nodes. |
| `session_rise` | Session Rise | `#FFD749 → #3F8CE8` | `ascending-arc-brightening-nodes` | Ascending arc with progressively brighter nodes. |
| `bounceback` | Bounceback | `#48D78A → #F79A47` | `compressed-spring-release` | Compressed spring releases toward an arrow. |
| `performance_slide` | Performance Slide | `#E54859 → #8052D8` | `descending-offset-slabs` | Three descending offset slabs. |
| `presence_tax` | Presence Tax | `#FFD74A → #E64953` | `ring-wedge-toll-bar` | Radiant ring has a missing wedge and toll bar. |

Pattern glyphs may inherit fragments from Element geometry, but the final
silhouette must remain unique. Confirm `29` registry entries and `29` unique
geometry IDs at 20 px, 64 px, monochrome, and gradient-tile scale.

## Copy and no-scaffolding rules

Use the verified copy catalogs and the identity cadence in `tone_of_voice.md`:

1. personal conclusion;
2. recognisable explanation;
3. optional vivid personal statistic;
4. useful implication;
5. optional dry turn.

Allow roughly one earned dry beat per chapter. Keep privacy, input, errors,
destructive actions, permissions, and sharing literal.

The player-facing Figma surface must not visibly include:

- confidence, coverage, evidence, provenance, cohort, denominator, source,
  methodology, sample size, effective sample size, raw metrics, proof counts,
  qualification gates, or internal enum/version labels;
- page fractions, screen-count language, or the former 24-screen sequence;
- repeated generic headings `What we saw`, `Why it matters`, or `What this
  actually means`;
- claims about mood, intent, personality, skill grade, or causality that the
  report does not establish.

The API continues to preserve qualification gates, internal evidence fields,
historical report compatibility, and public payload shape. Do not delete those
concepts from the Figma artifact by exposing them as UI; they are server-side
contract details. The frontend's `containsAnalysisLanguage` and
`safeCatalogCopy` behavior chooses human fallbacks when catalog text contains
analytical language.

## States, accessibility, and responsive behavior

- All primary controls are at least 48 px high and have visible keyboard focus
  rings.
- Use real headings in order, labelled regions, `aria-current` for the active
  dock/rail item, `aria-pressed` for selected tiles, `aria-live` for analysis,
  portfolio reveals, Mirror results, and share status, and `role="status"` for
  unavailable states.
- Glyphs are decorative when the adjacent label already names them; otherwise
  expose the accessible glyph name from the registry.
- The profile input accepts a public OpenDota profile, Steam ID, or Steam
  profile URL. Error messages are literal and actionable.
- Analysis uses server events when available and visibility-aware polling as
  the authoritative fallback. The Figma busy frame must not imply a guaranteed
  percentage or timing.
- Selected Element and Pattern tiles remain visibly selected and keyboard
  operable.
- Hero questions are radio-style choices with a disabled reveal action until a
  choice exists. No-clear and unavailable states do not invite guesses.
- Hero Mirror opens from button, Enter/Space, or horizontal drag. Reduced motion
  removes smooth scrolling and tile/Mirror transitions; progress becomes a
  static completed track.
- The mobile report uses normal scroll. `scroll-snap-type` is explicitly none.
- At desktop intent, preserve the 92 px chapter rail, 12-column layout, and
  three-column portfolio/question grids. At mobile, use the 20 px gutter,
  two-column glyph grids, stacked detail panels, stacked portfolio cards, and
  the fixed dock.

## Versions and implementation behavior

The Figma metadata or handoff notes must record these exact versions:

- legacy copy: `free-dna-copy-5.5.0`;
- semantic copy: `free-dna-semantic-copy-5.3.0`;
- share renderer: `share-svg-5.0.0`;
- public report schema remains `free-dna-report-5.2.0`;
- story interaction version remains `free-story-5.3.0`;
- semantic outcome registry remains `pattern-outcomes-5.2.0`;
- semantic recommendations remain `hero-recommendations-semantic-1.1.0`.

The public report payload remains unchanged. Historical reports remain readable.
Weak individual findings disappear; an entire unresolved feature gets a short
human state. Share output never contains account IDs, raw match rows, or raw
internal enum labels. Analytics remains privacy-safe and records chapter,
selection, reveal, and share events without identity fields.

## Figma component and variable build

Create reusable Figma components and variants before assembling the frames:

- `Shell/Topline`, `Shell/State`, `Shell/Chapter`;
- `Control/Input`, `Control/PrimaryButton`, `Control/QuietButton`,
  `Control/Choice`, `Control/Toggle`, `Control/Focus`, `Control/Progress`;
- `Navigation/ChapterDock` with five-item active/inactive variants;
- `Navigation/ChapterRail` for desktop intent;
- `Chapter/Heading`, `Chapter/Kicker`, `Chapter/Unavailable`;
- `Tile/Identity`, `Tile/Glyph`, `Tile/Stat`, `Tile/Question`, `Tile/Experiment`;
- `Panel/ElementDetail`, `Panel/PatternDetail`, `Panel/Mirror`,
  `Panel/ShareControls`;
- `Glyph/Element/{Name}` for every Element and `Glyph/Pattern/{Name}` for every
  Pattern in the registry above;
- `Share/FinalCard` with name/avatar/privacy variants;
- `State/Loading`, `State/Error`, `State/NoClear`, `State/Unavailable`, and
  `State/ReducedMotion`.

Create variables for the core colors, chapter palettes, spacing scale, control
height, dock height, radii, type styles, and focus ring. Use component
properties for selected/unselected, available/unavailable, open/closed,
busy/idle, reduced-motion, name on/off, and avatar on/off. Keep the default
geometry square; opt into rounding only for the documented exceptions.

## Build, screenshot, validate, then delete

Before deleting anything in section `247:32`:

1. Create all 12 replacement frames and all shared components/variables.
2. Wire prototype links for dock navigation, Summary actions, tile selection,
   Hero question reveal, Mirror reveal, share toggles, and back/scroll behavior.
3. Capture screenshots of the replacement while the old 24 frames are still
   present. Validate frame dimensions, content, hierarchy, glyph legibility,
   and state variants.
4. Fix every mismatch found by the checklist below.
5. Capture the required final screenshots again.
6. Only now delete the old 24-screen wireframes and their obsolete children.
7. Verify that section `247:32` and its existing link are unchanged.

## Final QA checklist

### Structure and behavior

- [ ] File is `D3uhn7WPXFsX1DiCIVklyg` and section `247:32` is preserved.
- [ ] Exactly 12 canonical mobile frames exist at `393 × 852`.
- [ ] The five dock labels are exactly Summary, Elements, Patterns, Heroes, You.
- [ ] Mobile scroll is normal; no page fraction, scroll snap, or 24-screen
  sequence remains.
- [ ] Summary communicates the leading identity without chapter navigation.
- [ ] Hero Mirror is teased until You and has closed/open/unavailable states.
- [ ] Share preview has name/avatar customization and literal fallback states.
- [ ] Old 24-screen children are deleted only after replacement screenshots pass.

### Visual system

- [ ] Midnight Specimen void/surface/paper colors match the variable table.
- [ ] Default geometry is square; only avatar, Mirror, and final share artifact
  use intentional rounding.
- [ ] Aurora meshes are clipped to cells and have restrained grain/dither.
- [ ] Plus Jakarta Sans styles and weights are present and used everywhere.
- [ ] Chapter palettes match the verified CSS values.
- [ ] Primary controls are at least 48 px and the mobile gutter is 20 px.

### Glyph system

- [ ] All 18 Element and 11 Pattern glyph components exist with exact names.
- [ ] All 29 geometry IDs are unique and match the source registry.
- [ ] Every glyph works at 20, 32, 64, and hero scale.
- [ ] Every glyph remains distinct in monochrome and over aurora tiles.
- [ ] No glyph contains letters, stock icons, hero silhouettes, or labels.

### Content and privacy

- [ ] No visible confidence, coverage, evidence, provenance, cohort,
  denominator, source, methodology, sample, raw metrics, or internal version
  labels appear in the identity frames.
- [ ] No-clear and unavailable states are human and short; unavailable
  individual findings are hidden.
- [ ] Copy follows conclusion → explanation → optional statistic → implication
  → optional dry turn.
- [ ] Error, privacy, sharing, and destructive-action copy stays literal.
- [ ] Share card includes identity headline, strongest Elements/Patterns,
  Hero Portfolio, Hero Mirror, and privacy guarantee without raw IDs.

### Accessibility and motion

- [ ] Heading hierarchy and labelled regions are present in every frame.
- [ ] Selected, focus, disabled, busy, no-clear, error, and unavailable states
  are visibly distinct.
- [ ] Keyboard users can navigate inputs, dock items, tiles, choices, reveal,
  Mirror, and share controls.
- [ ] Reduced-motion variant removes smooth scrolling and transitions while
  retaining state meaning.
- [ ] Text remains readable at 200% zoom intent and long player names wrap.

### Required final handoff

Return:

- Figma file ID and preserved section ID;
- created node IDs (frames, components, variables, styles, and glyphs);
- changed node IDs;
- deleted node IDs (the old 24-screen children only);
- screenshot of the overall `247:32` section;
- screenshot of the Summary frame;
- screenshot of the Pattern detail frame;
- screenshot of the Hero Mirror revealed frame;
- screenshot of the Share preview/customization frame;
- a concise list of validation checks passed and any remaining issue.

Do the edit, validate it, remove the old children only after validation, and
return the node IDs and screenshots. Do not return a second proposal.
