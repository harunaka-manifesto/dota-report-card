# Free DNA V6.1 State C product narrative review

Review date: 2026-08-26
Scope: product narrative, content, comprehension, language, evidence disclosure, privacy, accessibility, and package/readiness review.
Analytical scope: read-only audit. No estimator, threshold, semantic qualification, schema, runtime, calibration, holdout, evidence, or release artifact was changed.

## Executive verdict

**Product narrative status: PASS.**

The V6.1 analytical contract is capable of supporting a strong summary-only
story: seven public Elements, five finding families, at most three qualified
outcomes, typed PRIMARY/TWIST/ANCHOR identity slots, finite relationship
interactions, bounded alternatives, a five-game non-causal verification rule,
opaque Deep handoffs, and up to three privacy-gated share candidates.

The implemented renderer is the State C product: nine adaptive beats present
Recognition→Share, human-first headlines lead each chapter, Evidence and
Methodology are progressive disclosures, uncertainty states are distinct, and
the final Signature/share surfaces use only server-authored eligible content.
Recommendation, follow-up, and Deep remain optional aftercare rather than the
identity conclusion.

The implementation passed 61 focused API/unit tests, full static checks, a
production web build, 45 browser scenarios across Chromium, Firefox, WebKit,
mobile Safari, and reduced motion, plus desktop and 375px visual review. The
stable analytical projection is unchanged at
`ff9cacf408a1978874c160682aff88b41bcc30c8b1b2490f5562ef70d893da5b`.

The required product direction is applied as the editorial rule:

> Pharma backstage. Spotify Wrapped onstage.

The analytical machinery earns the right to tell a story. It is not the story.

## Review basis and limitations

### Repository sources read

- `docs/architecture/free-dna-v6.1-feature-graph.md`
- `docs/architecture/dota-dna-ssot.md`
- `docs/architecture/elements.md`
- `docs/architecture/pattern-presentation.md`
- `docs/architecture/report-flow.md`
- `docs/qa/free-dna-v6.1-release-gates.md`
- `docs/design/free-dna-v6.1-figma-documentation-update-agent-brief.md`
- `docs/generated/free-dna-v6.1-copy-review.md`
- `services/api/app/reports/dna_assembly_v61.py`
- `services/api/app/api/report_schemas_v61.py`
- `services/api/app/player_analysis_v6/`
- `services/api/app/player_analysis_v61/`
- `services/api/app/share/service.py`
- `services/api/app/api/routes.py`
- `apps/web/app/report/[reportId]/page.tsx`
- `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`
- `apps/web/app/report/[reportId]/v6/types.ts`
- `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`
- `apps/web/tests/e2e/report-v6.spec.ts`

The graphify repository index was used as a navigation aid. Its V6.1 graph
snapshot is stale relative to the checked-in V6.1 implementation, so the
implementation and strict schema remain authoritative.

### Editorial-source reconciliation

The governing “Prompt B — Write the design.md Constitution for Dota DNA” and
“Prompt C — Visualize the Complete Dota DNA Report” documents were read in full
on 2026-08-25. Prompt B is the constitution for visual grammar, pacing,
progressive disclosure, uncertainty, accessibility, and share inheritance.
Prompt C is the maximal storyboard/reference arc. Its 33 screens are not a
fixed page count: the existing nine API beats compose, merge, or omit them
according to actual backend output.

Material corrections applied to this review are the account-recognition opening,
the strongest 2–3 Element teaser before the full seven-Element Evidence view,
actual eligible-match sample copy, hero match-count/share-only facts, the
timeline/table adaptation of the pool-map concept, the earned evidence-derived
Signature, explicit Story/Evidence/Methodology depths, and an actual-output-only
share gallery. The Sequencing Field reuses cells, bands, clusters, links, forks,
chronology, and recombination; it is not a new analytical layer.

### Release-provenance boundary

The task supplies the current analytical/runtime provenance as:

- holdout execution SHA `7df38e6d234ae9c4ee425490bc40b8cc92685f85`;
- verifier/adjudication SHA `020118260abde18350be4c0605c1473d1756435e`;
- one execution, 339/339 unique profiles, zero errors, zero OpenDota calls;
- `HOLDOUT_ADJUDICATION_PASS`;
- adjudication artifact SHA `7ddbc5ddd22ca77a3200852f82b5f5af3c2293e6816b183b107c73d62bacde57`;
- artifact bundle `a6c1d0c08ceef553150c401b0711b24eb89aa4d316105b8977373f3cc79c4865`;
- corpus `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216`;
- split `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231`.

Those facts were accepted as current adjudicated provenance for this product
review and were not rerun. The original holdout is consumed and remains a
blocked release gate; `HOLDOUT_ADJUDICATION_PASS` records corrected adjudication
of that execution, not authorization, calibration, retraining, or a new holdout.
The checked-in release-gates/runbook documents contain earlier failed or future
replacement-workflow statements. Their historical evidence is immutable. An
exact current-versus-historical patch plan is frozen in the implementation
manifest; no analytical file is changed in this batch.

## Product principles

1. **Human question before metric.** The first sentence answers what a Dota
   player naturally wonders: what is my pool, what survives a hero change, what
   changes after a loss, what holds across a session?
2. **One idea per viewport.** A reveal has one primary headline and one visual
   gesture. Evidence is a second depth, not a competing headline.
3. **Story first, proof underneath.** Story is the default; evidence is an
   intentional “Why?” or “See what changed”; methodology is optional.
4. **Observed behavior only.** Summary history can describe choices, events,
   exposure, results, and session position. It cannot read motive, emotion,
   personality, role certainty, positioning, death quality, fatigue, or cause.
5. **Narrative uncertainty.** Qualifying results are confident within their
   boundary; neutral results are interestingly neutral; insufficient results
   are honest and factual; mixed results show both sides.
6. **Dota-native, not slang-heavy.** Use hero pool, familiar hero, stretch
   choice, after a loss, fight, match, session, and exposure where those terms
   match the backend contract. Do not use “tilt,” “clutch,” “carry,” or role
   slang as an inferred identity.
7. **Signature, not a fixed type.** The final synthesis is a traceable Dota DNA
   Signature made from supported Elements, findings, and hero-pool properties.
   It is not a personality type, class, horoscope, or grade.
8. **No unsupported screen inflation.** The 33-screen reference is an arc, not
   a requirement to invent backend outputs. Production uses nine API story
   beats and composes the reference beats inside them.
9. **Share the surprising truth.** A share card may contain only a server-
   eligible identity, strongest finding, or hero mirror. Weak or unavailable
   evidence is not made more dramatic to improve shareability.
10. **Sequencing Field continuity.** Cells, bands, clusters, links, divergence,
    chronology, and signature strips transform across chapters so the final
    Signature is visibly assembled from previously shown evidence.
11. **Actual outputs determine density.** Fewer findings shorten the story;
    insufficient and neutral states are intentional content, not missing-page
    errors. No fixed count, win rate, map behavior, or deeper analysis is
    promised without a corresponding field.

## Pre-implementation problems (resolved by this batch)

### P0 — The emotional arc is out of order

The current order is self-estimate → identity → pool prediction → combat
expression → strongest finding → layers → recommendation → hero mirror → Deep.
The intended arc is Recognition → Familiarity → Structure → Adaptability →
Adversity → Expression → Time → Coherence → Signature → Depth → Share.
The current page order makes a recommendation and five-game commitment feel
like the report's conclusion before the user has seen a synthesized signature.

### P0 — Technical evidence is in the foreground

`MetricReceipt` makes `Estimate`, `95% interval`, `Sample`, `Sessions`, and
`Confidence` a primary finding surface. These are valid evidence fields, but
they belong at Depth 2 or Depth 3. The default story must lead with the human
question, editorial answer, and visual evidence cue.

### P0 — V6.1 is presented as “06”

The renderer's wordmark and rail say `FREE DNA 06` / `V6`. A V6.1 report is
selected correctly by the route, but the visible identity is wrong and makes
the additive V6.1 contract indistinguishable from V6.0.

### P0 — No final Dota DNA Signature exists

The API has typed identity slots and evidence-backed identity content, but the
current renderer stops at Hero Mirror/Deep. It has no final synthesis surface
that combines the slots, Elements, findings, and hero anchor into a traceable
signature before sharing.

### P1 — The current copy is safe but analytical

The 25 public-candidate V6.1 outcome claims are registry-owned and bounded, but
phrases such as “summary expression,” “distance frontier,” “practically
compatible,” “conditional variance decomposition,” and “mapped function
context” are evidence language, not a Spotify-Wrapped-style reveal.

### P1 — Evidence layers are incomplete

The current finding tabs are `claim`, `evidence`, `interpretation`, and
`recommendation`. They do not provide a first-class `Why this?` evidence view
and a distinct `How we measured it` methodology view. The methodology currently
appears at the end of the Deep beat and foregrounds cost fields.

### P1 — Neutral, mixed, and insufficient states are generic

`EmptyState` gives a truthful fallback, but it does not tell a player whether a
finding is neutral, insufficient, mixed, suppressed, or unavailable. The story
needs narrative variants, not one generic “No strongest finding” state.

### P1 — Hero evidence can leak implementation vocabulary

`HeroMirrorCard` renders `Object.entries(mirror.player_behavior)` keys directly.
The V6.1 identity composer can fall back to `Stable core: <hero IDs>` when a
human anchor is absent. Both require human labels and display names before a
public story is approved.

### P1 — Share is currently text-copy only in the main renderer

The server owns a V6.1 SVG renderer and privacy gates, but the current browser
composer offers `Copy text` only. The product spec requires a collectible share
surface; the image/native-share/download path is not wired into this renderer.

### P1 — Source-bound release documentation is inconsistent

The task's corrected adjudication provenance and the checked-in release-gate
record refer to different release histories. No production decision should be
made until the release owner reconciles them in a separate authorized
source-binding action.

## Pre-implementation screen and state inventory (historical audit input)

The table classifies the current product as **Discovery**, **Evidence**, or
**Synthesis**. “Keep” means preserve the capability and revise its placement or
copy; it does not mean the current implementation is already approved.

| Screen/state | Current purpose, copy, and data | Current mode | Current problem | Disposition and target |
|---|---|---|---|---|
| `load-report` | Server component fetches `/v1/reports/{reportId}`. There is no Free V6.1 loading screen in the page component. | Discovery | A slow request has no story-shaped waiting state. | **Add frontend state.** Opening/Recognition: “We’re sequencing your Dota.” Do not show technical request language. |
| `report-404` | `notFound()` for a missing report. | Discovery | Next.js default not-found treatment is not a product explanation. | **Rewrite.** “This report is no longer available.” Secondary: “Start a new Free DNA report to sequence a fresh year.” |
| `report-fetch-error` | Generic thrown error: “The report could not be loaded.” | Discovery | Correct but impersonal; no retry or safe route is named. | **Rewrite.** “Your Dota sequence is taking a break.” Secondary: “Try again, or start a new report.” |
| `profile-identification` | Free V6.1 already carries optional `identity.display_name` and `identity.avatar_url`, but the current story does not make profile context a deliberate screen. Legacy Deep Scan exposes account ID/name/rank. | Discovery | Free should identify the report without exposing account IDs, rank, or a dashboard header. | **Add/merge.** Use optional display name/avatar in the opening and share preference; never show account ID, rank, or MMR. |
| `topbar` | `FREE DNA 06`; “Summary-only identity report”; save/resume/delete journey controls. | Discovery | Version is wrong for V6.1; “summary-only” is methodology language; controls compete with the opening. | **Rewrite.** `FREE DNA 6.1`; “Your Dota, seen as a shape.” Keep save/delete as quiet utility actions. |
| `conflict-alert` | “This saved journey has a newer version.” / “Choose whether to load it or save your local progress over it.” | Discovery | Necessary state is written like a sync tool and interrupts the story. | **Keep capability, rewrite.** “Your saved journey has a newer chapter.” Buttons: “Use latest” / “Keep this version.” |
| `rail-and-progress` | V6 rail with Estimate, Identity, Pool, Combat, Finding, Layers, Action, Mirror, Deep; `Beat X of 9`; all beats optional. | Discovery | Labels describe implementation beats, not the emotional arc; recommendation appears before synthesis/share. | **Move/relabel.** Use “Start, Shape, Pool, Change, After loss, Match, Session, Signature, Share.” Keep skip and progress semantics. |
| `self-estimate` | “Start with your read”; “Before the report speaks, make a quick estimate”; four identity choices; “Reveal my report.” | Discovery | The self-report is clear but opening on a question before recognition makes the product feel like a survey. | **Move/merge.** Make it a short optional prelude after scope; preserve storage under `user_reported` only. |
| `identity-reveal` | “The observed shape”; “The headline below comes from the report’s observed evidence, not from your estimate”; locked reveal; identity headline/supporting lines/evidence refs. | Discovery | Strong trust boundary, but current identity headlines include analytical or over-broad language; no typed slot composition is foregrounded. | **Keep and rewrite.** “Yep. This is you.” Show optional display name/avatar, then a 2–3 Element teaser; reveal PRIMARY, one plain support line, and the ANCHOR only when server-supplied. |
| `element-ledger` | Seven cards show glyph, label, confidence, formatted metric, zone, and sample matches. Copy: “Observed summary signals stay distinct from your self-reported answers.” | Evidence | Numeric metric and confidence are too prominent; seven cards are a dashboard inside the reveal. | **Move/merge.** Show the strongest 2–3 available signal bands in Discovery; keep all seven in Evidence with values, sample, and limitations. |
| `pool-prediction` | “Predict the pool”; “Make a call, then scrub through the observed Pool Evolution”; server options, observed answer, reveal. | Discovery | Good Wrapped interaction, but it is too early and focuses on prediction before “before the patterns, the heroes.” | **Move/expand.** Put after hero familiarity; add core/stretch/tail evidence where available. |
| `pool-timeline` | “Pool Evolution scrub”; range input and timeline marks; selected summary/evidence. | Evidence | Scrubber is a visual gesture without a clear human question; summary can be raw server wording. | **Rewrite/merge.** “Here’s who lives where.” Use existing thirds/evolution only when present; present a timeline/field plus text/table alternative, not an invented spatial map. |
| `combat-self-estimate` | “How do you show up in fights?”; “Estimate how participation and exposure travel together”; four choices. | Discovery | “Show up in fights” can imply inside-game behavior that summary data cannot observe. | **Rewrite/move.** “What does your scoreboard expression usually look like?” Put after the post-loss chapter. |
| `combat-finding-reveal` | Finding reveal, then “Combat Expression is unavailable in this report.” when absent. | Discovery | Safe fallback, but “combat expression” and finding text are not player-first. | **Keep capability, rewrite.** “Once the horn sounds, what keeps showing up?” Use involvement/exposure bounded copy. |
| `strongest-finding` | “The strongest finding”; “Compare matched evidence before deciding what it means”; finding claim, interpretation, relationship, receipt. | Synthesis/Evidence mixed | It tries to reveal, prove, interpret, and quantify in one viewport. | **Split.** Reveal in Story; “Why?” evidence drawer; “How we measured it” methodology drawer. |
| `relationship-evidence` | Native `<details>` with “Only supported aggregate evidence is shown”; table fallback over nested interaction values. | Evidence | Good accessible fallback, but raw keys are humanized only by replacing underscores and may expose implementation labels. | **Keep and rewrite labels.** Every interaction gets a reviewed table/disclosure copy. |
| `metric-receipt` | `Estimate`, `95% interval`, `Sample`, `Sessions`, `Confidence`. | Evidence | Technical fields are visible at the same hierarchy as the claim. | **Move.** Depth 2 uses “Across X comparable matches” / “Across Y sessions”; Depth 3 can expose interval and estimator labels. |
| `secondary-finding` | “Look underneath”; four tabs: claim, evidence, interpretation, recommendation. | Synthesis/Evidence mixed | It lacks alternatives and methodology; recommendation is not always available; secondary finding may be absent. | **Rewrite/merge.** Use “What changes the first signal?” then progressive `Why`, `What else could explain it`, and `How measured`. |
| `recommendation` | “Choose a next experiment”; server-authored choices; “Commit to five games.” | Synthesis | The word “experiment” and commitment appear before signature/share; it can read as a treatment plan. | **Move to Depth/aftercare.** Keep only when a recommendation and two metrics exist; describe as a five-game check-in, not identity change. |
| `follow-up` | “Five-game follow-up”; `0/5 context-matching games`; “This does not claim causality or a new identity.” | Evidence | Correct guardrail, but progress is presented as a primary story beat and the interaction response includes private `match_ids`. | **Move and privacy-review.** Keep as optional aftercare; expose aggregate comparison only. |
| `hero-mirror-closed` | “Meet your Hero Mirror”; “A mirror is eligible only when the server says its evidence can stand alone”; “Reveal Hero Mirror.” | Discovery | Eligibility language leads instead of the personal question. | **Rewrite.** “Which hero carries the shape?” Eligibility becomes Evidence/Methodology copy. |
| `hero-mirror-open` | Hero headline/body plus raw `player_behavior` keys and values; eligibility sentence. | Discovery/Evidence mixed | Raw keys, technical values, and eligibility status compete with the mirror reveal. | **Rewrite.** Human hero name and one comparison visual in Story; facts in Evidence; no raw IDs. |
| `share-composer` | “Share candidates”; “Only server-eligible cards appear here. Self-estimates are never used as evidence”; radio cards; `Copy text`. | Share/Synthesis | No image/native-share/download path; generic candidate payload can be weak; share appears before a final signature. | **Move/rebuild frontend.** Show a contact-sheet gallery after Signature; fetch only eligible identity/finding/mirror SVGs from the existing route, with download/native-share and clipboard fallback. |
| `deep-diagnostic` | “Choose your Deep question”; “Route the next analysis from a question this report can actually support”; up to three radio questions; “Send to Deep.” | Depth | Correctly gated, but Deep is placed as the final page without a preceding signature/share conclusion. | **Move after share.** Preserve offered-question-only routing and opaque cohort reference. |
| `deep-response` | “Deep response”; raw message/status from the API. | Depth | Status text may expose job language rather than a next user question. | **Rewrite.** “Your deeper question is queued.” Use factual status and never imply a result before completion. |
| `methodology` | “Free boundary”; notes; `Detail reads`; `Parses`; shown inside Beat 9. | Methodology | Cost/accounting is too late and too technical; no explicit three-depth contract. | **Move/reshape.** “How we measured this” disclosure available from every evidence panel; keep cost facts inside methodology only. |
| `empty-state` | Generic “Not available” plus message; “No strongest finding was published”; “No recommendation was published”; “No evidence-qualified Deep question was offered.” | Evidence | Truthful but not narrative; cannot distinguish neutral, insufficient, mixed, suppressed, or unavailable. | **Rewrite variants.** Use family-specific neutral/insufficient/mixed copy in the state machine. |
| `save/resume/delete` | “Save journey,” “Saved,” “Saved journey resumed,” “Delete saved journey,” conflict and error statuses. | Utility | Uses journey/session terms without a small privacy explanation. | **Keep, quiet, rewrite.** “Save your place” / “Remove saved place”; explain that answers are user-reported and bearer-token protected. |
| `deep-scan-route` | Separate legacy route shows account ID/name/rank, “Superpowers,” “Contradictions and context,” “Work on next,” and evidence details. | Discovery/Evidence mixed | It is not the Free V6.1 summary story and contains identity/rank/dashboard language. | **Keep isolated or audit separately.** Do not merge into Free V6.1; never use “superpowers” or rank in the V6.1 story. |

## Seven Elements storytelling contract

The exact backend definitions remain unchanged. The following is the approved
presentation contract for the next implementation batch.

| Element | Backend definition and data | Human question | Story interpretation | Evidence cue | Methodology label | Never say |
|---|---|---|---|---|---|---|
| Breadth | “How widely your matches are distributed across heroes.” Effective hero count, top shares, HHI, stable core, and chronological pool shape from `supporting:portfolio_shape`. | “How wide is your hero pool?” | Focused: “A small group carries most of your year.” Broad: “Your year reaches across a wide hero pool.” Typical: “Your pool has a center with room around it.” | Hero share visual plus core/tail labels. | “Effective hero distribution and annual hero shares.” | “You are a specialist,” “you are versatile,” or any personality label. |
| Toolkit | “How many functional jobs your hero choices cover in the reviewed taxonomy.” Fractional job mass, effective jobs, coverage, taxonomy version and sensitivity. | “Do your heroes solve the same job—or different ones?” | Narrow: “Different heroes, similar jobs.” Versatile: “Your heroes cover different jobs.” Typical: “Your pool covers a mix of jobs without one clear edge.” | Hero names grouped into mapped jobs; coverage note. | “Fractional job mass in the reviewed hero taxonomy.” | “You always play support/carry,” actual role, lane certainty, or skill. |
| Involvement | “Context-adjusted kills plus assists per minute.” Duration-adjusted event activity, baseline, 30-match/8-session/80%-coverage gate. | “How often are you in the scoreboard action?” | Frequent: “Your adjusted involvement shows up often.” Quieter: “Your adjusted involvement stays on the quieter side.” Typical: “Your involvement sits near its supported range.” | Simple activity direction and comparable-match count. | “Context-adjusted kills plus assists per minute.” | aggression, positioning, fight entry, leadership, or intent. |
| Finishing | “Context-adjusted share of known kill-plus-assist events that are kills.” Beta-binomial event-weighted kill share, at least 100 events, 30 event matches, 8 sessions. | “When credited action happens, how much of it is kills?” | Personal: “More of your credited action lands as kills.” Shared: “Your credited action leans more toward assists.” Typical: “Your credited action stays balanced between kills and assists.” | Kill/assist split using known scoreboard events. | “Beta-binomial share of known kill-plus-assist events.” | finishing intent, objective conversion, clutch ability, or motive. |
| Death Exposure | “Context-adjusted deaths per ten minutes.” Duration-adjusted deaths, baseline, 30-match/8-session/80%-coverage gate. | “How much death exposure shows up in your matches?” | Lower: “Your adjusted death rate sits on the lower-exposure side.” Higher: “Your adjusted death rate sits on the higher-exposure side.” Typical: “Your death exposure stays near its supported range.” | Deaths-per-ten-minutes direction and context band. | “Context-adjusted deaths per ten minutes.” | death quality, positioning, recklessness, fear, or intention. |
| Transfer | “Agreement when a familiar hero context is compared with stretch choices.” Cross-fitted core/reliable-stretch/experimental-edge distance bands and outcome/activity/survival components. | “What survives when the hero changes?” | Qualified copy comes from the Transfer outcome table below; neutral: “The supported comparison does not separate familiar and stretch contexts.” | Familiar vs stretch comparison with one visible boundary. | “Cross-fitted multi-signal distance bands.” | causality, adaptability as a personality trait, positioning, or intent. |
| Consistency | “Robust session-to-session agreement across outcome, activity, and death exposure.” Information-weighted session dispersion, shrinkage, 12-session gate. | “Does your expression hold from session to session?” | Consistent: “Your expression holds together across sessions.” Variable: “Your expression changes more from session to session.” Typical: “Your sessions stay within a mixed range.” | Session-position or session-spread visual. | “Information-weighted session-to-session agreement.” | tilt, fatigue, discipline, emotional resilience, or causality. |

Element values, zones, intervals, sample counts, and coverage are not shown in
the Story layer. They are available through the Evidence and Methodology
depths defined in `docs/product/v61-story-content-spec.md`.

## Five finding-family story contracts

| Family | Human question | Reveal structure and allowed headlines | Neutral form | Insufficient form | Mixed form | Do not claim | Next transition |
|---|---|---|---|---|---|---|---|
| Pool Shape | “What kind of pool do you actually carry?” | Show hero names first, then core/stretch/tail and jobs. Use one registered outcome: “Your pool is wider than it first looks—but it has a center.” / “Your hero names cover more ground than the jobs behind them.” / “A compact hero set covers a wider mix of jobs.” / “Your hero names moved more across the year than the jobs they covered.” | “No single pool shape separated cleanly.” | “Not enough stable pool history to call the shape.” | “Your pool has two valid layers: the names move, while the jobs hold.” Only when both supported layers qualify. | specialist/versatile personality, actual role, patch causality, or why the player chose a hero. | “Your pool tells us where you usually play. But what happens when the hero changes?” |
| Transfer | “When the hero changes, what comes with you?” | Reveal the supported familiar/stretch boundary. Use the exact outcome line for `clean_transfer`, `results_stop_first`, `expression_stops_first`, `involvement_boundary`, `exposure_boundary`, or `localized_function_bottleneck`. | “The supported comparison does not separate familiar and stretch contexts.” | “Not enough comparable familiar and stretch matches to call transfer.” | “Your answer changes by signal: one part travels, another does not.” | improvement, causality, personality adaptability, positioning, or motive. | “Dota moves you off-script in more than one way. A different hero is one. A loss is another.” |
| Post-Loss Response | “What do you pick after a loss?” | Show same-session transition states, then one registered line: “After one loss, your next choice stays closer to your prior path.” / “After two or more losses, your next choice changes differently.” / “Your next choice moves differently after wins and losses.” / “Your next-choice movement stays about the same after wins and losses.” / “Your next choice changes after the result, while the next result stays unresolved.” | “No single result state separated your next-choice movement.” | “Not enough same-session transitions to call a post-loss pattern.” | “The one-loss and two-plus-loss states do not tell the same story.” | tilt, anger, recovery, resilience, motive, or causal effect of a loss. | “What you pick next is one response. What you do once the horn sounds is another.” |
| Combat Expression | “What does your game look like once the horn sounds?” | Keep involvement and exposure separate, then reveal one supported line: “Involvement holds while death exposure moves.” / “Death exposure holds while involvement moves.” / “Similar summary expression can arrive with different results.” / “Similar results can arrive with different summary expression.” / “More of the expression variance sits in one supported context.” | “Involvement and death exposure stay compatible in the supported comparison.” | “Not enough context-resolved matches to call combat expression.” | “It depends on the signal: involvement and exposure do not move together.” | aggression, positioning, intent, death quality, skill, or why a result happened. | “One match shows expression. A session shows whether it holds.” |
| Session Drift | “What changes later in a session?” | Use completed-session positions only. Reveal one supported line: “Game 1 has a different supported shape from later games.” / “A covered part of your expression moves as the session continues.” / “The first clear break appears at the registered session position.” / “Your pool changes across a session while summary expression stays compatible.” / “Completed session endings differ after the registered result state.” | “Your covered expression stays compatible across completed session positions.” | “Not enough completed sessions to call a session pattern.” | “The session story changes by what you measure.” | fatigue, warm-up, focus, stopping intent, cause, or psychological state. | “We’ve been looking at what changes. Now look at what keeps showing up.” |

The exact outcome-to-field binding and all 25 public headline variants are in
`docs/product/v61-copy-data-basis-matrix.md`.

## Copy-overclaim classification

The required classification is applied to every current primary claim family.
Individual registry keys are listed in the matrix and retain their exact
semantic key; they are not silently renamed.

| Classification | Current claim/surface | Finding | Required treatment |
|---|---|---|---|
| A — engaging + supported | Self-estimate options such as “I mostly repeat a small hero set.” | Separates user-reported belief from server observation. | Keep as optional self-report; never use as evidence. |
| A — engaging + supported | “Your self-estimates are never used as evidence.” | Correct interaction/privacy boundary. | Keep in the Evidence/share disclosure. |
| A — engaging + supported | “This does not claim causality or a new identity.” | Correct follow-up guardrail. | Keep in aftercare, shorten visually. |
| B — supported but too analytical | All 25 public `SEMANTIC_COPY_REGISTRY` claims, including “Outcome and summary expression remain compatible through the supported distance frontier.” | Semantically bounded and registry-owned, but not understandable in 2–3 seconds. | Keep the semantic key and evidence meaning; use the human headline variants in the new catalog/presentation layer. |
| B — supported but too analytical | “Here is the pattern the summary evidence supports.” | Accurate but sounds like a report disclaimer. | Rewrite to “This is the shape your year leaves behind.” Keep the boundary in the secondary line. |
| B — supported but too analytical | “Compare matched evidence before deciding what it means.” | Good Evidence intent, weak as a Story headline. | Use as the Evidence-depth instruction after the reveal. |
| B — supported but too analytical | “Only supported aggregate evidence is shown.” | Correct but implementation-shaped. | Use in methodology/disclosure, not in the first reveal. |
| C — engaging but stronger than evidence | “You carry your game beyond familiar heroes.” | The transfer estimator measures bounded summary compatibility, not a general game identity. | Replace with “More of your observed expression travels when the hero changes.” |
| C — engaging but stronger than evidence | “A loss changes what you choose in a visible way.” | It can read as a causal psychological reaction; the contract is same-session association. | Replace with “After a loss, your next observed choice changes.” |
| C — engaging but stronger than evidence | “Your summary expression rises across completed session positions.” | Could be read as fatigue/warm-up or a general trajectory. | Replace with the registered session outcome plus “completed sessions” limitation. |
| D — unsupported psychology/causation | Legacy Deep Scan “Superpowers” and any “work on next” wording that labels a player weakness or skill. | Not a V6.1 summary-only identity contract. | Keep the route isolated; do not reuse in V6.1. |
| D — unsupported psychology/causation | Any future use of tilt, anger, fatigue, resilience, discipline, confidence, personality, or “because.” | Rejected boundary in the V6.1 vocabulary and supporting-signal registry. | Remove. No copy variant may restore it. |
| E — technical/methodological content in wrong layer | `Estimate`, `95% interval`, `Sample`, `Sessions`, `Confidence`; raw estimator, q-value, FDR, bootstrap, coverage, and cost labels. | Valid audit data, wrong default hierarchy. | Move to Depth 2/3. |
| E — technical/methodological content in wrong layer | `FREE DNA 06`, `Summary-only identity report`, “Detail reads,” “Parses.” | Version/cost/provenance information is not the opening emotion. | Correct V6.1 label; move boundary/cost to methodology. |

The three shadow-only outcomes—`hero_lifecycle`, `identity_eras`, and
`behavioral_loop`—are not current user-facing claims. They remain protected
from Story, share, and Deep question surfaces.

### V6.1 public semantic-key coverage

Every public-candidate key is covered by the classification above and the
copy/data matrix. They are all **B — supported but too analytical** in the
current registry wording; the proposed human headline is a presentation/copy
rewrite, not a semantic change.

| Family | Public keys classified B | Required treatment |
|---|---|---|
| Pool Shape | `hidden_center`, `names_wide_jobs_narrow`, `names_narrow_jobs_wide`, `names_changed_jobs_held` | Keep fields, outcome keys, alternatives, and gates; use the pool headlines in the matrix. |
| Transfer | `clean_transfer`, `results_stop_first`, `expression_stops_first`, `involvement_boundary`, `exposure_boundary`, `localized_function_bottleneck` | Keep bounded frontier meaning; replace “compatible/frontier” foreground language with the human transfer lines. |
| Post-Loss Response | `one_loss_runback`, `two_loss_switch`, `result_shaped_pool`, `result_invariant_response`, `adjustment_without_recovery` | Keep same-session denominator; remove recovery/motive implications from the foreground. |
| Combat Expression | `involvement_holds_exposure_moves`, `exposure_holds_involvement_moves`, `same_expression_different_results`, `different_expression_same_results`, `localized_variance` | Keep separate summary components; move estimator and variance terminology to Methodology. |
| Session Drift | `opening_game_signature`, `gradual_session_drift`, `predeclared_breakpoint`, `selection_only_drift`, `bounded_stopping_response` | Keep completed-session/direct-position contract; remove fatigue, warm-up, and stopping-intent interpretations. |

The current V6 identity headline families are also covered: pool-shape
headlines are B; “You carry your game beyond familiar heroes” and “A loss
changes what you choose in a visible way” are C; combat quadrant headlines are
B; session-rise/fade headlines are B with a C risk if they are presented as
fatigue or improvement. The proposed identity surface uses typed slots and the
matrix-bound headlines instead.

## Pre-implementation product-comprehension review (resolved)

The ten-question test from the product direction was applied to every current
Discovery/Reveal surface. A screen passes only when all ten answers are true.

| Surface | 2–3 second point | One idea | Needs statistics? | Strong sentence primary? | Human before terminology? | Natural Dota question? | Evidence interrupts? | Advances arc? | Personally specific? | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Opening/topbar | No | Yes | No | No | No | No | No | Partial | No | NEEDS IMPLEMENTATION |
| Self-estimate | Yes | Yes | No | Yes | Yes | Yes | No | Partial | User-specific only | PASS with move |
| Identity reveal | Partial | Yes | No | Yes | Partial | Yes | Yes, via refs/ledger | Yes | Yes | NEEDS IMPLEMENTATION |
| Seven Elements ledger | No | No; seven cards plus receipt | Sometimes | No | No | Partial | Yes | Partial | Yes | NEEDS IMPLEMENTATION |
| Pool prediction/timeline | Yes | Mostly | No | Yes | Yes | Yes | Partial | Yes | Yes | NEEDS IMPLEMENTATION |
| Combat reveal | Partial | No when receipt/finding is present | Sometimes | Partial | No | Partial | Yes | Yes | Yes | NEEDS IMPLEMENTATION |
| Strongest finding | No | No; reveal/proof/interpretation/receipt | Yes in current view | No | No | Partial | Yes | Yes | Yes | NEEDS IMPLEMENTATION |
| Secondary/layers | Partial | No; four tabs plus evidence refs | Yes in current view | Partial | Partial | Partial | Yes | Yes | Yes | NEEDS IMPLEMENTATION |
| Recommendation | Yes | Yes | No | Yes | Yes | Partial | No | No, before synthesis | Yes | MOVE/REWRITE |
| Hero Mirror | Partial | No; facts and eligibility compete | No | Partial | No | Yes | Yes | Yes | Yes | NEEDS IMPLEMENTATION |
| Deep | Yes | Yes | No | Yes | Yes | Yes | No | Yes after share | Yes | MOVE |
| Signature/share (missing) | Not available | Not available | No | Not available | Not available | Required | Not available | Required | Required | BLOCKED BY IMPLEMENTATION |

The current renderer has good semantic controls—native radios, buttons,
`progress`, focus outlines, reduced-motion CSS, and an accessible relationship
table—but comprehension is a product hierarchy problem, not only a semantic
HTML problem.

## Dota-language review

### Keep

- hero pool;
- familiar hero and stretch choice;
- after a loss;
- next choice;
- fight/horn when used as a chapter bridge;
- match and session;
- involvement and death exposure when immediately explained;
- “what survives when the hero changes?”;
- “one match versus a session.”

### Rewrite or explain once

- `summary expression` → “the scoreboard shape we can observe” on first use;
- `mapped jobs` → “the functional jobs attached to those heroes”;
- `distance frontier` → “the nearest supported point where the comparison changes”;
- `compatible` → “stays within the supported range”;
- `chronological thirds` → “early, middle, and late parts of the year”;
- `independent sessions` → “separate sessions” in Evidence;
- `session position` → “game 1, game 2, game 3, game 4, game 5+”;
- `same-session transition` → “the next choice in the same session.”

### Prohibited in the V6.1 foreground

`tilt`, `anger`, `fatigue`, `warm-up`, `confidence` as a player trait,
`personality`, `skill`, `aggression`, `positioning`, `fight entry`, `death
quality`, `intent`, `because`, `causes`, `causal`, rank, MMR, and actual role
claims. These terms remain useful in code guards and methodology audit notes
only where they describe a prohibited inference.

## Evidence-layer review

Every major insight uses exactly three depths.

### Depth 1 — Story

Default. Contains one human question, one headline, one visual cue, and at
most one simple number or share. It does not show p-values, q-values, FDR,
interval notation, estimator names, bootstrap counts, threshold names,
coverage decimals, or cost fields.

### Depth 2 — Evidence

Opened with “Why this?” / “See what changed” / “Show the comparison.” Contains
the comparison, plain-language denominator (“Across 41 comparable matches”;
“Across 9 sessions”), a simple baseline or before/after cue, one to three
evidence facts, and the factual limitation. It may show the exact hero/job or
session labels that explain the visual.

### Depth 3 — Methodology

Opened with “How we measured it.” Contains the exact estimator definition,
365-day summary-only boundary, one-history-request rule, session independence,
coverage/missingness, alternatives, error-control note, artifact/version
labels, and technical intervals when useful. It never exposes raw rows,
account IDs, match IDs, rank/MMR, protected cohorts, or rejected signals.

The current `MetricReceipt` belongs in Depth 2/3, not in the reveal. The
current methodology section must be available from each relevant evidence
panel rather than only at Beat 9.

## Pre-implementation major risks (resolved except source binding)

| Risk | Severity | Why it matters | Safe handling |
|---|---|---|---|
| Current adjudicated provenance and checked-in release documents use different time/status scopes | High | A corrected holdout pass could be mistaken for release authorization, or historical failure could be mistaken for the current adjudicated record. | Keep historical evidence immutable; apply the exact current-state patch plan in the implementation manifest before release authorization. |
| Prompt B constitution and Prompt C storyboard are applied as a fixed-page design | Medium | The storyboard's 33 screens could force invented content when fields are absent. | Treat 33 as a reference arc; adapt page count to actual evidence and eligible outputs. |
| Story copy changes semantic wording | High | Copy is versioned and source-bound; a prose-only change can alter claims. | Treat the proposed consumer copy as one copy-catalog change; review provenance before implementation. |
| Current frontend locks the old nine-beat order in tests | Medium | Tests prove the current renderer, not the desired narrative. | Update frontend tests only in the implementation batch; no analytical test rerun is needed for copy alone. |
| Raw hero IDs / object keys appear in public surfaces | High | Human comprehension and privacy boundary fail. | Require human display-name mapping and reviewed fact labels in assembly/presentation. |
| Follow-up response includes `match_ids` | High | Strict report schema forbids raw IDs, but the interaction response should preserve the same public privacy posture. | Remove from user-facing response or keep server-private and verify with an API privacy test. |
| Share renderer uses `V6_RENDERER_VERSION` in V6.1 SVG footer | Medium | A V6.1 card can be stamped as V6.0. | Correct in the presentation/share implementation batch, with no analytical change. |
| Legacy Deep Scan terminology leaks into Free | Medium | “Superpowers” and rank language change the product type. | Keep route isolated; do not reuse its copy or data model. |

## Recommended production story structure

Production remains nine server-defined beats, but each beat composes the
reference arc rather than exposing implementation labels.

| Production beat | Emotional job | Reference screens composed | Default surface |
|---|---|---|---|
| 1. Opening | Recognition | 01–03 | “We sequenced your Dota.” Scope is a small supporting line. |
| 2. Shape | Recognition → Familiarity | 02, 04 | PRIMARY identity plus seven signal scan. |
| 3. Pool | Familiarity → Structure | 05–12 | Heroes first, then Breadth/Toolkit/core/stretch/timeline. |
| 4. Transfer | Structure → Adaptability | 13–15 | Question, qualified reveal, evidence drawer. |
| 5. After loss | Adaptability → Adversity | 16–19 | Same-session result-state transition. |
| 6. Match | Adversity → Expression | 20–23 | Involvement/Finishing/Death Exposure relationship. |
| 7. Session | Expression → Time | 24–27 | Completed session positions and drift/neutral state. |
| 8. Signature | Time → Coherence → Signature | 28–31 | Synthesis of Elements, findings, hero anchor, and typed slots. |
| 9. Depth/share | Signature → Depth → Share | 32–33 | Three-depth controls, eligible share cards, optional Deep route. |

Recommendation/five-game verification is an optional aftercare drawer from
the relevant qualified finding. It must not replace or precede Signature/share.
The exact screen copy, conditions, state variants, transitions, and data basis
are the implementation source of truth in:

- `docs/product/v61-story-content-spec.md`
- `docs/product/v61-copy-data-basis-matrix.md`
- `docs/product/v61-story-state-machine.md`

The copy/data matrix filename is exactly
`docs/product/v61-copy-data-basis-matrix.md`. The previously reported doubled
“matrix” segment was a final-response path typo only; no filesystem rename is
needed. The exact implementation manifest is
`docs/product/v61-product-implementation-manifest.md`.

## Implemented gap report

The counts below are change groups, not file counts. They are intentionally
kept separate from analytical/model work. Every listed frontend, copy,
presentation, privacy, and sharing group was completed in this batch.

### FRONTEND-ONLY — 8 groups

1. Recompose the nine beats into the Recognition→Share order and relabel the
   rail/progress surfaces.
2. Correct V6.1 topbar/version wording and quiet utility controls.
3. Implement the three-depth Story/Evidence/Methodology disclosure hierarchy.
4. Add human-first visual compositions and nonvisual equivalents for Elements,
   pool shape, and all six relationship kinds.
5. Render narrative neutral, insufficient, mixed, suppressed, and unavailable
   states instead of one generic empty component.
6. Render typed identity slots as Signature and humanize hero/mirror facts.
7. Move recommendation/follow-up and Deep after Signature/share; keep them
   optional and gated.
8. Wire actual share image/native-share/download behavior and loading/error
   states without changing report semantics.

### COPY-CATALOG-ONLY — 1 group

1. Add the approved consumer-facing headline, secondary, evidence-label,
   neutral, insufficient, and mixed strings for V6.1 public outcomes while
   retaining the same semantic keys and forbidden-token guards. The catalog and
   its contract regressions are committed without changing semantic keys.

### REPORT-ASSEMBLY-PRESENTATION — 4 groups

1. Supply story/chapter labels and reference-screen composition metadata for
   the fixed nine beats.
2. Supply human evidence cues and state variants tied to existing fields.
3. Supply display-name-safe Signature/ANCHOR payloads and reviewed mirror fact
   labels; never fall back to hero IDs.
4. Supply share-card title/body/image metadata for the existing eligible
   candidate types and stamp V6.1 renderer metadata correctly.

### INFRA/SHARING — 1 group

1. Correct the existing V6.1 share renderer footer/card metadata path; do not
   create a new public share service or image-hosting capability.

### BACKEND-SEMANTIC — 0 groups

No new Element, family, outcome, denominator, threshold, comparison, or
qualification behavior is required by this specification.

### ANALYTICAL/MODEL — 0 groups

No estimator, model, calibration artifact, holdout, threshold, or statistical
evidence change is authorized or required.

## Post-implementation release disposition

The product narrative, Dota language, data basis, privacy, copy-overclaim,
comprehension, and accessibility reviews pass. Production enablement remains
blocked because `AnalysisService._load_v61_artifacts()` currently uses the
deployment `RELEASE_COMMIT_SHA` as the required source for the immutable
analytical bundle and authorization. A newer presentation-only API/worker SHA
therefore cannot be represented truthfully without a separate validated
analytical-source binding. This architecture blocker does not change the
analytical result and does not justify recalibration or a holdout rerun.
