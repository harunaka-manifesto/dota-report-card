# V6.1 Storytelling and Reveal Implementation Report

- Status: implementation complete pending combined Preview verification
- Report date: 2026-08-31
- Base SHA: `b119948069da5890df17ed1be229674864b0fc5f`
- Implementation commit SHA: `8d12c489634a98d815024fa383c658e875831f2f`

This report records the presentation implementation, landing-page follow-up,
worker reliability fix, evidence boundary, and verification supplied by the
implementation run. It does not authorize an analytical release or production
configuration change.

## Outcome

The V6.1 story now has a more varied reveal rhythm while retaining the existing
report payload, page IDs, omission rules, and historical-rendering boundary.
The main change is editorial: receipts, questions, chronology, accumulation,
quiet transitions, and the neutral ending now have distinct jobs. The
implementation does not claim a measured increase in user engagement; it
implements the research-backed mechanics that make recognition, anticipation,
contrast, and ownership possible without adding unsupported personal meaning.

The follow-up also gives the landing page the same receipt-first trust model and
fixes an intermittent production worker lifecycle failure without changing the
report contract or analysis semantics.

## What changed

### Landing page and analysis entry

The landing page now explains one bounded progression: public identifier →
report → reachable evidence. Its hero promises a short story from the public
history actually available to the report, the decorative scope preview says
`Up to 365 days`, and the backstage section explains that unsupported material
is omitted. The form copy no longer implies unqualified habits, roles, or
identity while work is in progress.

The entry flow retains the existing API requests and polling behavior. Visible
and accessible labels now agree, the live loading region receives focus, an
error restores focus to the input, header actions meet the 44px touch target,
and the true 375px layout fits without hiding overflow.

### Celery worker event-loop reliability

Production reuses one `AnalysisService` and its `OpenDotaClient` in each Celery
prefork child. The old task wrapper created and closed a fresh event loop with
`asyncio.run()` for every delivery, so a later task could reuse an HTTP
keep-alive transport bound to the closed prior loop. That raised
`RuntimeError("Event loop is closed")`, which the service correctly hid behind
`ANALYSIS_FAILED / Unexpected analysis failure`.

The worker now reuses one lazy `asyncio.Runner` per worker process and closes it
through Celery's prefork and non-prefork shutdown signals. A regression test
executes two tasks against one loop-bound persistent client and proves both use
the same loop. This is classified as an **INTERNAL IMPLEMENTATION CHANGE**:
task name, arguments, responses, report schema, analytical code, and persisted
data remain unchanged.

### Editorial copy and chapter framing

`apps/web/app/report/[reportId]/v6/story/copy.ts` now uses a more authored
chapter spine:

```text
The Year in Queue
  → When It Worked
  → When It Didn’t
  → The Next Queue
  → The Heroes That Returned
  → Outside the Short List
  → The Scoreboard
  → The Pattern Underneath
  → The Reveal
  → The Year, Reassembled
  → One Layer Deeper
```

Chapter 8 and Page 25 remain structurally absent. Copy now:

- establishes the report as a bounded sequence before the first number;
- frames the busiest week/day as nested chronology rather than two unrelated
  counters;
- asks a question before the longest-match, transfer, and transition moments;
- separates kills, assists, and deaths as impact, connection, and quiet cost;
- describes hero recurrence without calling it comfort, mastery, role, or
  personality;
- replaces “favorite,” “comfort,” “questionable decisions,” matchmaking
  judgments, and generic gamer insults with observable wording;
- changes the final action language to `Share the receipts.` and `Read it
  again.`; and
- keeps all branch copy sourced from supplied variants or existing rendered
  presence. No client-side threshold, ranking, sum, or finding was introduced.

### Curated humor and silent closes

The old global dry-line cadence and `ALWAYS_SILENT_PAGES` list were removed.
`compose.ts` now gives a close only to a small evidence-gated set:

- Page 7 only when the supplied longest match was marked `refused_to_end` and
  was a win;
- Page 10 only for the supplied multi-win streak variant;
- Page 12 only when a supplied breaker win exists;
- Page 18 only for a non-sparse calendar-month era; and
- Page 21 only when the supplied transfer semantic outcome has a known close.

All other pages resolve to the existing `Endstop`. The unit contract for the
full fixture expects dry closes on exactly Pages 7, 10, 12, 18, and 21. This
keeps humor fact-bound and selective; it does not mechanically attach a joke to
every metric or force a three-page punchline run. Branches with zero,
insufficient, sparse, neutral, or unavailable evidence stay quiet where the
receipt has not earned a release.

### Semantic reveal rhythms

`motion.ts` adds seven semantic rhythms and per-page mapping. The shell exposes
the selected rhythm as `data-rhythm`, and CSS provides distinct transition
behavior while preserving static content and reduced-motion composition:

| Rhythm | Job | Current pages |
|---|---|---|
| `immediate` | Let a direct receipt land quickly. | 2, 3, 9, 22, 23 |
| `measured` | Give scope, ledger, or cost room. | 1, 4, 24 |
| `question` | Hold the question before its answer. | 5, 7, 15, 20, 21 |
| `accumulation` | Let a sequence or set build before naming it. | 10, 11, 12, 13, 17, 27, 29, 32 |
| `chronology` | Make order and time the reveal. | 6, 18, 19 |
| `quiet` | Use a calm bridge, boundary, or share close. | 8, 14, 16, 26, 33, 34 |
| `identity` | Hold the final neutral shape long enough to read. | 30 |

The rhythm is a presentation token, not analytical confidence. Ordinary gaps
are 300ms (`immediate`), 480ms (`measured`), 650ms (`question`), 320ms
(`accumulation`), 420ms (`chronology`), 700ms (`quiet`), and 560ms (`identity`).
The existing dominant-value settle/fact hold and identity hold remain separate
semantic holds. No page auto-advances, and the shell still pauses timers while
the document is hidden or a disclosure is open.

### Page-level choreography

The renderers use the existing primitives rather than adding a new payload
shape:

- Pages 1–4 use measured/immediate receipts with scope and ranked split rather
  than a repeated joke close.
- Pages 5–7 use question and chronology framing; Page 7 asks which match kept
  going and keeps the supplied formatted duration as the dominant fact.
- Page 10 reveals the win sequence before settling the count and date range,
  making accumulation perceptible.
- Finding pages still share evidence plumbing, but Page 15 reveals the
  comparable-opportunity sample before the interpretation when that sample
  exists. Page 21 retains the transfer outcome-specific close.
- Pages 17–19 use recurrence, eras, and payoff as a progression rather than
  three unrelated hero lists.
- Pages 22–24 retain exact combat totals and leading-hero rows while removing
  the repetitive joke endings and presenting the group as scoreboard context.
- Pages 26–27 move quietly from visible counters to the registered channels;
  unavailable Element labels remain omitted and the support line uses the
  number that rendered.
- Pages 29–30 and 32–33 now build a neutral report artifact, reassemble the
  observed receipts, and leave the user with share/read-again actions.

### Neutral non-personalized ending

The archetype payload remains `not_ready`. The implementation therefore changes
the frontend constant from `THE RECURRING PLAYER` to `THE YEAR IN QUEUE` and
describes a report assembled from the available window, matches, results, hero
choices, and qualified patterns. Page 30’s action is `Turn the report card`,
which describes the physical
interaction rather than imply a new computation. Page 31 is omitted until a
future payload provides qualified identity anchors; rendered source pages are
not treated as identity evidence.

This is a neutral report artifact, not a per-player archetype. The code does
not seed, rotate, or derive a label from a hero, hash, raw metric, or missing
identity slot. The narrow `not_ready` exception remains limited to
`archetype` and `final_identity_card`; no other module is allowed to render on
`not_ready`. The final card uses the existing truthful match-count/window
fallback and optional display name, while short or possibly truncated histories
avoid the false `365 days of Dota` claim. A future server-owned identity engine
remains responsible for any personalized Signature and its evidence anchors.

## Why the sequence is more engaging

This is an editorial rationale, not an engagement experiment result. The
implementation makes the reading path more engaging by giving the user several
ways to recognize themselves:

1. **Immediate recognition:** a named/anonymous greeting and bounded scope are
   followed by readable receipts. The report earns attention before asking for
   interpretation.
2. **Anticipation:** question rhythms on the busiest week, longest match, and
   finding pages create a small gap between “what are we asking?” and “what did
   the evidence say?”
3. **Memory:** nested week/day chronology, a longest-match object, streak blocks,
   and hero eras turn totals into order and return. A date or sequence gives the
   year a handle.
4. **Contrast:** wins/losses, familiar/changed heroes, and combat signals are
   kept as distinct sides. The user can recognize tension without being handed
   a false middle or a skill judgment.
5. **Progressive disclosure:** Story remains one primary line and one cue;
   Evidence and Methodology hold denominators, alternatives, limitations, and
   exact definitions. This keeps analytical rigor backstage while preserving a
   trustworthy route to the receipt.
6. **Agency:** no auto-advance was added; the first forward action completes an
   unseen reveal and the second advances. Existing Back, keyboard, evidence,
   methodology, share, and read-again controls remain usable.
7. **A shareable close:** `Your year, reassembled.` and `Share the receipts.`
   treat the end as an owned artifact built from prior observations, not as a
   louder unsupported personality label.

The implementation is intentionally not a claim that the new wording is
universally more entertaining. The proper follow-up is owner review or user
research after preview, with attention to comprehension, trust, completion,
sharing, and whether humor feels specific rather than generic.

## Macro emotional beats

The macro arc stays aligned with the frozen order in the product docs:

```text
Recognition → Familiarity → Structure → Adaptability → Adversity
→ Expression → Time → Coherence → Signature → Depth → Share
```

The implementation presents that arc through these current chapter beats:

| Beat | Pages | Emotional job | Editorial movement |
|---|---:|---|---|
| 1. The Year in Queue | 1–7 | Welcome, scale, memory, and a first small climax | Greeting → receipts → nested peak → longest-match question |
| 2. When It Worked | 8–11 | Relief and earned pride | Reframe → win tally → streak accumulation → winning cast |
| 3. When It Didn’t | 12–13 | Pressure without blame | Loss sequence → terminal boundary → aftermath cast |
| 4. The Next Queue | 14–15 | Curiosity about what followed a result | Quiet pivot → post-loss question, comparison, evidence |
| 5. The Heroes That Returned | 16–19 | Familiarity, return, and time | Callback → pool center → eras → supported payoff |
| 6. Outside the Short List | 20–21 | Productive tension | Contrast setup → transfer frontier and evidence |
| 7. The Scoreboard | 22–24 | Visible expression and quiet cost | Impact → connection → deaths as the final receipt |
| 9. The Pattern Underneath | 26–27 | Scale shift and composure | Visible counters → supported channels |
| 10. The Reveal | 29–30 | Synthesis without fabricated identity | Recap callbacks → neutral report card |
| 11. The Year, Reassembled | 32–33 | Ownership and completion | Collage callbacks → scope/provenance → share/read again |
| 12. One Layer Deeper | 34 | Optional intrigue | Real Deep destination only; currently omitted |

The emotional curve is an ordering of existing report states, not sentiment
scoring. Zero, degraded, mixed, insufficient, sparse, and historical inputs
take quieter branches without being forced into the “good year” arc.

## Reveal grammar inventory

The implementation uses these concrete grammars while preserving page IDs:

- **Receipt first:** Pages 1–4 and 9 land the scope, count, duration, ledger,
  or win total before interpretation.
- **Question → answer:** Pages 5, 7, 15, 20, and 21 hold a bounded question
  before the relevant supplied fact/finding. A question never gates access to
  the report or invents a prediction.
- **Accumulation ladder:** Pages 10, 12, 17, 27, 29, and 32 use ordered blocks,
  rows, channels, recap lines, or collage cards. The motion says “these items
  are accumulating,” not “a new threshold was discovered.”
- **Chronology / nested peak:** Pages 6, 18, and 19 make a date relationship or
  era movement the story. A later state is not attributed to a patch, mood,
  decision, or cause.
- **Contrast / split:** Pages 4, 11, 13, 21, and the combat group keep two
  supported sides visible. Mixed evidence is not averaged into “typical.”
- **Boundary / reversal:** Pages 12, 14, 15, 26, and unavailable branches
  state where the recorded sequence ends or what the source cannot answer.
  Missingness is presented as a valid result, not filled with drama.
- **Callback / return:** Pages 16, 19, 29, 32, and 33 reuse prior hero, result,
  era, and scope objects only when the relevant page/evidence exists in the
  composed payload.
- **Quiet evidence:** Pages 8, 14, 16, 26, 27, and 33 use calm transitions,
  labels, and Endstops so uncertainty and completion have room.
- **Neutral identity artifact:** Pages 29–30 display a report shape, never an
  invented personalized archetype, while the payload is `not_ready`. Page 31
  stays absent until the payload can supply qualified identity anchors.
- **Artifact close:** Pages 32–33 turn prior receipts into a share/read-again
  finish; Page 34 remains a real conditional invitation, not a dead CTA.

Motion is semantic: `immediate` is quick receipt, `question` creates a pause,
`accumulation` builds, `chronology` orders time, `quiet` settles, and
`identity` holds the final neutral object. Reduced motion keeps all content and
uses the same page/beat semantics without animated translation.

## Exact compatibility boundary

### Preserved

- Numeric page IDs and order for every rendered page. The full fixture now has
  30 pages because Page 31 is truthfully omitted.
- The `story_payload.page_manifest` source and runtime normalization boundary.
- Nine API compatibility beats and existing module-to-page ownership.
- Finding slots and their server-owned publication, semantic-outcome, evidence,
  confidence, alternative, and omission rules.
- Page 25 absence and Page 28 (`element_distinctiveness`) exclusion.
- Page 14/16/20/27 bridge conditions, Page 31 omission without qualified
  identity anchors, Page 33 final identity fallback, and Page 34 destination
  gate.
- Missing optional fields as omissions or truthful neutral/insufficient/mixed
  states; no fabricated analytical meaning.
- Historical reports without a V6.1 story payload using their existing legacy
  rendering path.
- Story/Evidence/Methodology separation, keyboard focus, reduced motion,
  share privacy, and analytics identifier exclusions.

### Explicitly not changed

- No API route, public schema, report contract, database, infrastructure, or
  migration file. The only backend change is the internal Celery worker loop
  lifecycle described above.
- No Element definition, family root, estimator, baseline, threshold,
  significance/error-control logic, calibration, holdout evidence, or model.
- No rank/MMR, cohort benchmark, actual-role, causal, psychological, or
  inside-match claim.
- No OpenDota player, match-detail, benchmark, or replay-parse QA call.
- No regeneration of reports, analytical artifacts, or production data.

## QA performed

The following results are the verified implementation-run results supplied for
this report:

- Unit story suite: **34 passed**.
- Chromium story E2E: **34 passed**.
- Other engines and reduced-motion story coverage: **133 passed**; **3 expected
  non-Chromium clipboard skips**.
- Complete web E2E suite after the landing and worker follow-up: **377 passed**;
  **27 capability-specific skips**.
- Landing matrix across Chromium, Firefox, WebKit, mobile Safari, and reduced
  motion: **45 passed**, including live-status focus, error focus restoration,
  in-page navigation, touch sizing, and true 375px overflow.
- Backend suite: **599 passed**; **3 expected skips**.
- Worker regression, API, and OpenDota-client focus set: **17 passed**.
- Current fixture and sanitized historical production-shaped fixture: **pass**.
- Full `make typecheck`: **pass** — mypy 210 plus TypeScript.
- Full `make lint`: **pass**.
- `docs-check`: **pass**.
- Clean production build: **pass**, using
  `API_BASE_URL=https://api.example.invalid` after isolating the concurrent
  `.next` cache.
- Desktop, 375px, 320px, 768px, mobile Safari, and reduced-motion traversal:
  **30-page full story, 7 rhythms, zero horizontal overflow, pageerror,
  unexpected console error, hydration error, or overlay**.
- OpenDota QA calls: **0**. Research used one documentation/OpenAPI GET only;
  no player/match/replay endpoint was called for QA.

A Vercel Preview for the earlier story commit loaded successfully. A refreshed
Preview for the combined landing/worker/Opus integration and its existing
persisted-report smoke remain release gates. No OpenDota report was generated
for QA.

## Remaining risks and follow-up

1. **Combined Preview verification is pending.** The earlier story commit reached
   Preview, but the landing/worker follow-up and Opus integration require a new
   deployment and smoke before the final production handoff is considered
   verified.
2. **Neutral ending is intentionally provisional.** The current report can
   show `THE YEAR IN QUEUE`, a report artifact, while the archetype payload is
   `not_ready`; a future server-owned Signature engine must replace it before
   any personalized identity copy ships. The narrow exception must not widen.
3. **Page 34 is reserved, not available.** `resolveDeepDestination` currently
   returns no route. Any future Deep CTA requires a validated destination,
   eligibility, privacy review, and its own compatibility tests.
4. **Build environment isolation should be recorded.** The production build
   passed against an invalid API base after concurrent `.next` cache isolation;
   this proves the build artifact path, not a production API smoke test.
5. **Editorial effectiveness is not yet measured.** The new sequence is a
   research-backed hypothesis. Preview review or user research should test
   comprehension, completion, trust in receipts, perceived specificity of
   humor, share intent, and whether the neutral ending feels honest rather than
   unfinished.
6. **Backend opportunity notes are research-only.** The opportunity scores and
   proposed gates in `v6.1-backend-storytelling-opportunities.md` are hypotheses
   and prioritization aids, not release thresholds or permission to add fields.
7. **Historical story-payload coverage has an honest limit.** The sanitized
   previous-production fixture predates `story_payload` and verifies the legacy
   fallback. No authentic older persisted story payload exists in the repository;
   one was not invented merely to make that test category look populated.

## Top backend opportunities (future work only)

The separate backend research document ranks opportunities by emotional utility,
data defensibility, and implementation/accessibility (`U × D × A`). Those
scores are not current analytical evidence.

| Priority | Opportunity | Feasibility | Safe product boundary |
|---:|---|---|---|
| 1 | Observed record shelf: highest/lowest values in the reviewed window | Summary-cheap | Descriptive, window/mode/scope-bound cards; never all-time or global claims. |
| 2 | Streak arc | Summary-cheap | Keep all-hero and same-hero scope distinct; describe sequence and endpoint, not tilt or cause. |
| 3 | Hero repeat/return arc | Summary-cheap | “You left, then came back” is descriptive; do not turn recurrence into loyalty or personality. |
| 4 | Solo ↔ stack split | Summary-cheap only if `party_size` coverage clears | Within-player comparison only; no friends, motive, mood, or social graph. |
| 5 | Year turning point / chapter change | Summary-cheap data, analytical complexity high | Research-only until predeclared segmentation and sealed validation; no patch or causal story. |
| 6 | Hero matchup memory | Summary-bounded | Defer for endpoint, privacy, and participant-coverage review; never call a global matchup personal. |
| 7 | Recorded role remix | Summary-cheap if optional coverage clears | Recorded hint only, never “true role,” position, intent, or skill. |
| 8 | Cohort benchmark / contextual percentile | Summary-bounded/high | Defer outside the frozen V6.1 boundary; no rank-coded comparison without a separate cohort contract. |
| 9 | Parsed one-match memory / fight-clock highlight | Parsed/Deep | Explicit background/Deep pilot with fixed candidate cap, parser version, cache, privacy review, and no Free dependency. |

The recommended next research order is record shelf, streak arc, hero return,
then solo/stack after a coverage audit. Any parsed, cohort, role, or matchup
work requires a separate release decision and must not be used to validate this
presentation change.

## Files changed in this working state

Presentation, tests, and documentation changes currently visible in the task
worktree:

- `apps/web/app/report/[reportId]/v6/story/archetype-placeholder.ts`
- `apps/web/app/report/[reportId]/v6/story/archetype-card.tsx`
- `apps/web/app/report/[reportId]/v6/story/compose.ts`
- `apps/web/app/report/[reportId]/v6/story/copy.ts`
- `apps/web/app/report/[reportId]/v6/story/motion.ts`
- `apps/web/app/report/[reportId]/v6/story/pages.tsx`
- `apps/web/app/report/[reportId]/v6/story/story-runtime.tsx`
- `apps/web/app/report/[reportId]/v6/story/story-shell.tsx`
- `apps/web/app/report/[reportId]/v6/story/story.module.css`
- `apps/web/app/components/analysis-form.tsx`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/styles/landing.css`
- `apps/web/tests/e2e/home.spec.ts`
- `apps/web/tests/e2e/report-story-v61.spec.ts`
- `apps/web/tests/e2e/fixture-server.mjs`
- `apps/web/tests/unit/story-composition.spec.ts`
- `docs/README.md`
- `docs/product/v6.1-backend-storytelling-opportunities.md`
- `docs/product/v61-story-audit-and-narrative.md`
- `docs/product/v61-storytelling-research.md`
- `docs/product/v61-storytelling-reveal-implementation-report.md`
- `services/api/app/workers/tasks.py`
- `tests/unit/test_worker_tasks.py`

## Completion record

```text
TASK TYPE: PRESENTATION / FRONTEND APPLICATION / BACKEND / DOCUMENTATION
BASE SHA: b119948069da5890df17ed1be229674864b0fc5f
NEW SHA: Recorded in the release handoff
CHANGED FILES: Listed above
BACKEND FILES CHANGED: YES — internal Celery worker lifecycle only
ANALYTICAL FILES CHANGED: NO
PUBLIC REPORT CONTRACT CHANGED: NO
PERSISTED REPORT COMPATIBILITY TESTED: YES
PRODUCTION-SHAPED FIXTURE: PASS
BROWSER E2E: PASS
TYPECHECK: PASS
LINT: PASS
BUILD: PASS
ANALYTICAL BEHAVIOR CHANGED: NO
HOLDOUT RERUN: NO
RECALIBRATION: NO
OPENDOTA QA CALLS: 0 (one documentation/OpenAPI GET for research)
DEPLOYED: NO
SAFE TO MERGE: NO — combined Preview verification is pending.
```
