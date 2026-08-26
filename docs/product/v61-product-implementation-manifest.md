# Free DNA V6.1 product implementation manifest

Status: **FROZEN FOR PRODUCT IMPLEMENTATION**  
Freeze date: 2026-08-25  
Repository root: `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`  
Report contract: `free-dna-report-6.1.0`  
Story contract: `free-story-6.1.0`

This is the exact input for the next product worker. It covers presentation,
copy, report-assembly presentation, privacy-safe interaction presentation, and
the smallest existing share-renderer correction. It does not authorize changes
to analytical semantics, model behavior, calibration, holdout evidence,
runtime eligibility, deployment, or production authorization.

## Direction and scope freeze

The user request is the implementation boundary. The attached direction
documents are inputs to that boundary:

- Prompt B — Write the `design.md` Constitution for Dota DNA was read in full.
  It governs the Sequencing Field, visual continuity, progressive disclosure,
  uncertainty states, accessibility, motion, and share inheritance.
- Prompt C — Visualize the Complete Dota DNA Report was read in full. Its 33
  screens are a maximal storyboard/reference arc, not a mandatory page count.
  The existing nine API beats compose, merge, collapse into disclosures, or
  omit those screens according to actual backend output.

The frozen story order is:

> Recognition → Familiarity → Structure → Adaptability → Adversity →
> Expression → Time → Coherence → Signature → Depth → Share

The primary UI is editorial and story-first. Story uses one human question,
one headline, and one visual cue. Evidence and Methodology are explicit,
progressive disclosures; methodology never interrupts the primary story.
Neutral results are intentional and interesting, insufficient results are calm
and unresolved rather than error-like, and mixed results show their valid sides
without flattening them. No public surface infers psychology, motive, emotion,
skill, actual role, positioning, death quality, fatigue, intent, or cause.

The filename audit is complete. The correct file is
`docs/product/v61-copy-data-basis-matrix.md`. The previously reported doubled
“matrix” path was a final-response typo only; no filesystem rename is needed.

## Current share implementation audit

### Current capabilities

- `services/api/app/share/service.py` exposes the deterministic SVG route through
  `GET /v1/reports/{report_id}/share/{card_type}`.
- V6.1 uses `share-svg-6.1.0` for cache-key and response-header binding.
- Server candidates are filtered for eligibility before rendering. Current card
  kinds are identity, strongest finding, and hero mirror, with a maximum of
  three candidates.
- `show_name` and `show_avatar` are supported share preferences; SVG output has
  accessible title/description metadata, immutable caching, and `noindex`.
- The route is already a stable report/card linkage for the current report
  surface. A new public share service, signed-link service, CDN, or image host
  is not required for this batch.

### Current limitations

- `apps/web/app/report/[reportId]/v6/report-story-v6.tsx` currently offers
  `Copy text` only; it does not fetch, preview, download, or invoke native
  share for the server SVG.
- The shared `_build_v6_share_svg` footer uses `V6_RENDERER_VERSION` even for a
  V6.1 card. The response header is correct, but the visible renderer stamp is
  not.
- The share renderer consumes generic candidate/title/reason fields; it does
  not yet present the Prompt C gallery as a coherent set of standalone,
  evidence-derived cards.
- The V6.1 hero portfolio base rows currently contain `hero_id`, `match_count`,
  `share`, functional jobs, and evidence refs. They do not contain hero win
  rate or human display labels at the public presentation boundary.
- The current frontend does not provide the Prompt B/C Sequencing Field
  continuity, actual 2–3 Element Discovery teaser, adaptive reference-screen
  composition, final Signature surface, or distinct Story/Evidence/Methodology
  hierarchy.

### Actual Prompt B/C requirement and minimum solution

Prompt B requires share cards to inherit the report's Element language,
Signature strip, typography, grid, hero treatment, and evidence hierarchy.
Prompt C requires a readable standalone gallery of actual cards. It names
possible surfaces, but only returned eligible outputs may appear. The minimum
solution is:

1. Frontend fetches the existing eligible SVG routes, shows an actual-candidate
   gallery after Signature, and supports preview, download, native share, and
   clipboard fallback.
2. Existing share backend is extended only to correct the V6.1 renderer stamp
   and, if needed, server-bound card title/body metadata. Eligibility remains
   server-owned.
3. No new backend capability is introduced. No card is synthesized from a
   missing finding, no win rate is invented, and no fixed card count is shown.

## Current versus historical provenance

The current adjudicated provenance accepted for this product review is:

- holdout execution SHA `7df38e6d234ae9c4ee425490bc40b8cc92685f85`;
- independent adjudication verifier SHA `020118260abde18350be4c0605c1473d1756435e`;
- original holdout consumed; no rerun;
- 339/339 unique profiles, zero errors, one execution, zero OpenDota calls;
- corrected adjudication `HOLDOUT_ADJUDICATION_PASS`;
- adjudication artifact SHA `7ddbc5ddd22ca77a3200852f82b5f5af3c2293e6816b183b107c73d62bacde57`;
- artifact bundle `a6c1d0c08ceef553150c401b0711b24eb89aa4d316105b8977373f3cc79c4865`;
- corpus `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216`;
- split `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231`.

This is corrected adjudication of the consumed original execution. It is not a
holdout rerun, model change, calibration change, release authorization, or
production enablement.

### Exact documentation-only patch plan

This plan is separate from the product implementation changes below. It must
be applied by the release owner without rewriting historical values.

1. `docs/qa/free-dna-v6.1-release-gates.md`

   - Replace the opening status paragraph with:

     > Current status: **blocked pending remaining calibration/evaluation
     > evidence and separate release authorization**. The original one-time
     > holdout has a corrected adjudication pass recorded below; V6.1 remains
     > disabled and this document does not authorize production.

   - Insert a `Current adjudicated holdout provenance` block immediately after
     the opening paragraph containing the nine current facts and all current
     digests listed above. State explicitly: `original holdout consumed;
     no rerun; HOLDOUT_ADJUDICATION_PASS; release authorization remains false`.
   - Retitle `Failed release disposition` as `Historical failed release
     diagnostic (immutable)` and add one sentence before its existing values:
     `The SHA and 298/339 with 41 errors below describe an earlier failed
     release diagnostic; do not overwrite or treat them as the current
     adjudicated execution.` Keep every existing SHA, count, error category, and
     interval-methodology statement unchanged.
   - Add `The replacement holdout precommit and scan sections below describe a
     future replacement workflow; they are not evidence that the current
     consumed holdout was recollected.` before the replacement precommit gate.
   - Keep State B/C blocked and keep all future commands unchanged. This patch
     reconciles scope and provenance; it does not turn the adjudication pass
     into release approval.

2. `docs/operations/free-dna-v6.1-release.md`

   - Replace the opening paragraph with:

     > V6.1 remains disabled. This runbook documents the future replacement,
     > build, evaluation, authorization, and rollback workflow. The current
     > adjudicated result is the consumed original holdout recorded in the
     > release-gates document; this runbook does not authorize production and
     > does not request a rerun.

   - Insert a `Current adjudicated holdout reference` block after the opening
     paragraph with the execution SHA, verifier SHA, `339/339 unique`, `0
     errors`, `1 execution`, `0 OpenDota calls`, `HOLDOUT_ADJUDICATION_PASS`,
     adjudication artifact SHA, bundle SHA, corpus SHA, split SHA, and the
     sentence `The original holdout is consumed and remains a blocked release
     gate.`
   - Keep the `Consumed holdout and replacement protocol` commands and explain
     that they are future replacement steps. Do not substitute the current
     adjudication digests into their future materialization command inputs.
   - Keep `docs/qa/free-dna-v6.1-existing-corpus-calibration-record.md`
     unchanged. It is already explicitly a historical State B record with old
     corpus/split/artifact digests and release unauthorized; its 339/339 facts
     are historical evidence, not the current adjudicated record.

3. No other checked-in V6.1 release document requires a provenance rewrite.
   `docs/reviews/v61-state-c-release-readiness.md` and this manifest carry the
   current-versus-historical distinction for the implementation decision.

## Frozen implementation changes

Each change is independently source-bound. “Existing fields only” means no new
semantic output, estimator, denominator, threshold, or qualification path.

### A-01 — Story rail and adaptive chapter composition

CHANGE ID: `A-01`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: The renderer exposes compatibility beat names and the old
implementation order, with recommendation/Deep before a final Signature/share
conclusion. 33 reference screens are not represented as an explicit adaptive
composition rule.  
REQUIRED BEHAVIOR: Preserve the nine compatibility IDs and render the rail as
Start, Shape, Pool, Change, After loss, Match, Session, Signature, Share. Keep
each beat skippable. Compose the 33 reference screens into beats, disclosures,
or omissions from actual output; never add placeholder pages.  
EXACT COPY:

- `We sequenced your Dota.`
- `Here’s what we found in the way you play.`
- Rail labels: `Start`, `Shape`, `Pool`, `Change`, `After loss`, `Match`,
  `Session`, `Signature`, `Share`.
- `How we measured this`.

DATA CONDITION: Valid V6.1 report; beat availability remains server-derived
from existing `pages`, `story`, findings, Elements, portfolio, Deep, and share
candidate fields.  
VISUAL MODE: Discovery-first editorial field; sparse cells and sequence strips
transform between chapters. No dashboard rail or front-loaded metric receipt.
  
STORY POSITION: Recognition → Familiarity → Structure → Adaptability →
Adversity → Expression → Time → Coherence → Signature → Depth → Share.  
EVIDENCE DISCLOSURE: Story shows one headline and one cue. `Why this?`, `See
what changed`, and `How we measured this` remain explicit disclosures.  
NEUTRAL STATE: `Your report is ready, even when some signals stay quiet.`  
INSUFFICIENT STATE: `Some of your year is here; the missing pieces stay
uncalled.`  
MIXED STATE: `Some parts of the year are clear. Others stay open to context.`  
ACCESSIBILITY REQUIREMENT: Preserve keyboard navigation, visible focus,
progress semantics, skip controls, screen-reader chapter labels, reduced-motion
static equivalents, narrow-mobile layout, and 200% zoom without horizontal
scrolling.  
PRIVACY REQUIREMENT: Do not place report IDs, account IDs, raw match/session
IDs, rank/MMR, protected references, or identity text in analytics.  
SHARE REQUIREMENT: The Share beat remains after Signature and shows zero or
more actual server-eligible candidates; it never creates a candidate.  
SOURCE-BINDING IMPACT: Presentation order and labels only; API IDs, report
schema, evidence gates, and finding order remain unchanged.  
DEFINITION OF DONE: Rail labels and order match this manifest; absent output
shortens the composed story; no reference-screen placeholder is added; all
keyboard/reduced-motion/mobile/zoom checks pass; no analytical/runtime file is
changed.

### A-02 — Account-recognition opening

CHANGE ID: `A-02`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/types.ts`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: `identity.display_name`/`avatar_url` are typed but not used as
a deliberate account-recognition specimen in the story.  
REQUIRED BEHAVIOR: After the opening, render an optional display name/avatar
specimen. If either field is absent, keep the recognition copy and omit the
missing profile detail; do not create a synthetic name, avatar, or account
metadata.  
EXACT COPY:

- `Yep. This is you.`
- `Your year is ready to recognize.`
- Neutral: `No single finding owns the headline yet. Your Elements are the
  shape we can describe.`
- Insufficient: `Your identity is still forming from this sample.`
- Mixed: `Your shape has more than one side. The slots below keep them separate.`

DATA CONDITION: `identity.display_name` and `identity.avatar_url` are optional;
`identity_summary.slots.primary` is required for a PRIMARY slot.  
VISUAL MODE: One profile specimen inside a precise crop/frame; cells from the
opening resolve into the profile, not a generic dashboard card.  
STORY POSITION: Recognition → Familiarity, reference screen 02.  
EVIDENCE DISCLOSURE: Profile context stays in Discovery; slot text, refs, and
the observed-versus-user-reported boundary open in Evidence.  
NEUTRAL STATE: `No single finding owns the headline yet. Your Elements are the
shape we can describe.`  
INSUFFICIENT STATE: `Your identity is still forming from this sample.`  
MIXED STATE: `Your shape has more than one side. The slots below keep them
separate.`  
ACCESSIBILITY REQUIREMENT: Avatar has meaningful alt text when a display name is
present and empty alt when decorative; name and observed shape are separately
announced; focus order follows the story.  
PRIVACY REQUIREMENT: Never render account ID, rank, MMR, private token, or raw
identity slot key. Display name/avatar are the only profile context.  
SHARE REQUIREMENT: Share preferences may use the existing `show_name` and
`show_avatar` controls; omission remains the default-safe path.  
SOURCE-BINDING IMPACT: Uses existing identity fields only; no identity meaning
or eligibility change.  
DEFINITION OF DONE: Screen 02 renders the exact copy and optional fields,
omits absent fields cleanly, passes accessible image/name checks, and has no
identifier leakage.

### A-03 — Element teaser and Sequencing Field identity

CHANGE ID: `A-03`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: The seven-Element ledger presents metric/confidence/receipt
content too early and reads as a dashboard.  
REQUIRED BEHAVIOR: Discovery shows the strongest 2–3 available Elements in the
server-supplied order. Evidence retains all seven with status, evidence refs,
and limitations. The client does not rank from raw values.  
EXACT COPY:

- `Seven signals kept showing up.`
- `Start with the strongest 2–3 available signals.`
- Neutral: `The seven signals do not all point in one direction. That is part
  of the shape.`
- Insufficient: `Some signals need more history before they can speak clearly.`
- Mixed: `Some signals hold while others move.`

DATA CONDITION: `elements[0..6]` exist; Discovery uses only available/status-
eligible records in server order, and Evidence renders the complete seven.  
VISUAL MODE: Sequencing Field bands; Breadth spreads/branches, Toolkit varies
modular cells, Involvement pulses links, Finishing converges, Death Exposure
opens edges, Transfer bridges, and Consistency aligns cadence. Geometry, texture,
motion, and text must reinforce the cue; hue alone is insufficient.  
STORY POSITION: Familiarity, reference screen 04; full Element evidence may be
revisited in Synthesis.  
EVIDENCE DISCLOSURE: Full seven labels, status, denominator, refs, and
limitations live behind the Element evidence disclosure.  
NEUTRAL STATE: `The seven signals do not all point in one direction. That is
part of the shape.`  
INSUFFICIENT STATE: `Some signals need more history before they can speak
clearly.`  
MIXED STATE: `Some signals hold while others move.`  
ACCESSIBILITY REQUIREMENT: Each band has a text label and status, the 2–3 teaser
has an accessible list equivalent, and all evidence values remain available at
200% zoom and reduced motion.  
PRIVACY REQUIREMENT: Do not expose raw metric keys, IDs, q-values, p-values,
private supporting keys, or user identity text in Story or analytics.  
SHARE REQUIREMENT: An Element appears as a share card only if a matching server
candidate is returned; the teaser does not create one.  
SOURCE-BINDING IMPACT: Presentation only; seven Element definitions, order,
estimators, status gates, and evidence refs stay server-owned.  
DEFINITION OF DONE: Discovery renders exactly 2–3 available server-ordered
signals, Evidence renders all seven, every Element has a non-color equivalent,
and no metric receipt appears in the initial reveal.

### A-04 — Hero familiarity and adaptive pool field

CHANGE ID: `A-04`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: Hero introduction is mixed with prediction/timeline mechanics;
the UI can treat the pool as a map and the current type does not guarantee
human labels.  
REQUIRED BEHAVIOR: Introduce heroes before pool findings, show only actual
portfolio fields, and adapt the pool chapter to hero rows, core/stretch/outer
edge, mapped jobs, and existing chronological timeline when present. The map
reference becomes a field/timeline plus table; no unsupported pan/zoom is added.
  
EXACT COPY:

- `Before the patterns, there are the heroes.`
- `If we had to start with one hero…`
- `One hero doesn’t describe your Dota.`
- `There’s a difference between a hero you’ve played…`
- `…and a hero that actually belongs to your Dota.`
- `Here’s who lives where.`
- Neutral: `Your hero list has no single front row yet.`
- Insufficient: `Not enough usable hero history to map the pool.`
- Mixed: `The front row changes by part of the year.`

DATA CONDITION: Use `hero_portfolio.heroes[*].match_count`, `share`, reviewed
display label, `functional_jobs`, `hero_portfolio.timeline`, `evolution`, and
existing portfolio-shape fields only. The current output has no hero win rate;
do not display or calculate one.  
VISUAL MODE: Hero specimens are extracted from the sequence strip and assemble
into core/stretch/outer-edge bands and early/middle/late field positions. Narrow
pools use fewer larger samples; broad pools use aggregation/clusters.  
STORY POSITION: Familiarity → Structure, reference screens 05–12.  
EVIDENCE DISCLOSURE: Show observed match count/share, mapped-job coverage,
timeline counts, and taxonomy limitation only in Evidence.  
NEUTRAL STATE: `Your hero list has no single front row yet.`  
INSUFFICIENT STATE: `Not enough usable hero history to map the pool.`  
MIXED STATE: `The front row changes by part of the year.`  
ACCESSIBILITY REQUIREMENT: Every hero specimen has a text row with name,
match_count, and share; the field has a table equivalent; timeline controls have
labels and `aria-valuetext`; reduced motion uses discrete early/middle/late
states.  
PRIVACY REQUIREMENT: Render no numeric hero ID, raw evidence ref, account ID,
rank/MMR, or private taxonomy key.  
SHARE REQUIREMENT: Hero identity/pool share surfaces appear only when the
server returns an eligible candidate; the UI does not offer a hero card for
every row.  
SOURCE-BINDING IMPACT: Existing portfolio presentation only; no hero win-rate
field, role inference, or new pool statistic.  
DEFINITION OF DONE: Heroes precede pool interpretation, every shown fact comes
from an existing field, the timeline/table fallback works, and no raw IDs or
invented win-rate values reach public UI or share.

### A-05 — Relationship chapters: Transfer, post-loss, match, session

CHANGE ID: `A-05`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: Relationship panels combine question, reveal, evidence,
interpretation, receipt, and recommendation. The session and post-loss
surfaces can read as causal or psychological.  
REQUIRED BEHAVIOR: Present one question first, show the registered outcome only
when published, expose neutral/insufficient/mixed states, and move evidence and
methodology below the reveal. Use relationship visuals that transform existing
cells/bands rather than inventing new semantics.  
EXACT COPY:

- `What survives when the hero changes?`
- `What does your Dota look like after a loss?`
- `Once the horn sounds, what keeps showing up?`
- `One match shows expression. A session shows whether it holds.`
- Qualified outcome copy is the exact `semantic_outcome_key` row in
  `docs/product/v61-copy-data-basis-matrix.md`.
- Transfer neutral: `The familiar and stretch parts of your pool stay within
  the supported range.`
- Post-loss neutral: `Your next-choice movement stays about the same across the
  supported result states.`
- Combat neutral: `Involvement and death exposure stay compatible in the
  supported comparison.`
- Session neutral: `Your covered expression stays compatible across completed
  session positions.`
- Insufficient: `Not enough signal to call this one.` followed by the one
  server-supplied factual reason.
- Mixed: `One signal holds while another moves.` or the exact registered mixed
  variant when the matrix row supplies one.

DATA CONDITION: Findings and Element/family state are read from existing
`findings`, `supporting_evidence`, `elements`, `session_curve`, and interaction
payloads. `published`, `status`, `interaction.enabled`, and evidence refs remain
server-owned.  
VISUAL MODE: Transfer bridge across familiar/stretch bands; post-loss fork from
the result-state cell; match relationship/two-version field; session discrete
G1–G5+ chronology.  
STORY POSITION: Adaptability → Adversity → Expression → Time, reference screens
13–27.  
EVIDENCE DISCLOSURE: One to three factual cues, plain denominator, comparison,
alternative, and limitation in Depth 2; exact estimator/version and coverage
in Depth 3.  
NEUTRAL STATE: Use the family-specific neutral strings above; do not say “not
significant.”  
INSUFFICIENT STATE: `Not enough signal to call this one.` plus exactly one
factual denominator/coverage reason.  
MIXED STATE: Show both component rows and their registered labels; never average
or rename the result `typical`.  
ACCESSIBILITY REQUIREMENT: Every bridge/fork/two-axis/chronology visual has a
table or text equivalent, labeled controls, keyboard operation, focus state,
reduced-motion before/after or discrete frames, and readable narrow/zoom layout.
  
PRIVACY REQUIREMENT: Do not expose match IDs, session IDs, raw family keys,
protected cohort refs, or inference language in the public response, UI, or
analytics.  
SHARE REQUIREMENT: Only server-eligible findings may be offered as share cards;
recommendations and neutral/insufficient branches never become standalone
cards.  
SOURCE-BINDING IMPACT: Presentation of registered outcomes only; no client
ranking, outcome derivation, or qualification.  
DEFINITION OF DONE: Each family begins with its human question, every state is
distinct, Story/Evidence/Methodology are progressive, visual/table equivalents
match, and no unsupported causal or psychological wording remains.

### A-06 — Three-depth disclosure and state honesty

CHANGE ID: `A-06`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: `MetricReceipt` and claim/evidence/interpretation/
recommendation tabs compete with the first reveal; neutral, insufficient,
mixed, suppressed, and unavailable states are not consistently distinct.  
REQUIRED BEHAVIOR: Implement progressive Story → Evidence → Methodology depth
for every major insight and render status-specific narrative states.  
EXACT COPY:

- Story controls: `Why this?`, `See what changed`, `Show the comparison`.
- Methodology control: `How we measured this`.
- Neutral: `Your pattern held remarkably steady.` when that family’s registered
  neutral line is not more specific.
- Insufficient: `Not enough signal to call this one.`
- Mixed: `Some parts of the year are clear. Others stay open to context.`
- Unavailable: `Not available` only when the source itself is absent.

DATA CONDITION: Use server `status`, `published`, evidence refs, limitations,
claim contract, alternatives, and methodology fields.  
VISUAL MODE: Discovery sparse; Evidence grid-aligned with one dominant
explanation and 1–3 cues; Methodology compact and drawer-based. Empty content is
calm, not error-red.  
STORY POSITION: All beats; most visible in Shape, Change, After loss, Match,
Session, Signature, and Share.  
EVIDENCE DISCLOSURE: Story has no interval notation, estimator, q-value,
coverage decimal, cost, or raw sample label. Evidence has denominator,
comparison, baseline/before-after, one to three facts, and limitation.
Methodology has exact estimator, window, request boundary, session unit,
missingness, alternatives, error control, and version labels.  
NEUTRAL STATE: Registered family-neutral copy with complete supported range.  
INSUFFICIENT STATE: `Not enough signal to call this one.` plus one factual
reason; no fake empty error.  
MIXED STATE: Both supported components remain visible.  
ACCESSIBILITY REQUIREMENT: Disclosure controls are keyboard reachable and
screen-reader labeled; state is announced in text, not color alone; focus moves
into opened content; reduced motion preserves understanding.  
PRIVACY REQUIREMENT: Methodology may describe boundaries but never exposes
account/match/session IDs, private paths, protected refs, or raw keys.  
SHARE REQUIREMENT: Only qualified, server-eligible identity/finding/mirror
content can enter Share; state copy alone never grants eligibility.  
SOURCE-BINDING IMPACT: Moves existing fields between presentation depths; no
semantic meaning or gate changes.  
DEFINITION OF DONE: All target states and three depths have exact copy and
accessible equivalents; technical receipts are absent from Story; no generic
empty state masks a known status.

### A-07 — Evidence-derived Signature and depth handoff

CHANGE ID: `A-07`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: The renderer ends at Hero Mirror/Deep and has no final
Signature artifact visibly assembled from previously shown material.  
REQUIRED BEHAVIOR: Render a collectible but non-fantasy Signature from only
server PRIMARY/TWIST/ANCHOR slots, Elements, published findings, and a
human-labeled hero/common-thread anchor. Omit absent slots. Show Depth only for
actual claim contracts/Deep questions; do not promise a fixed count.  
EXACT COPY:

- `None of these patterns lives alone.`
- `They keep resolving into the same underlying shape.`
- `Your Dota Signature.`
- `Why this describes your Dota.`
- `This is the layer we can see for free.`
- `There’s more underneath it.`
- Neutral: `Your Dota Signature is still taking shape.`
- Insufficient: `There is not enough stable evidence to name a Signature yet.`
- Mixed: `Your Signature has a clear core and a context-dependent twist.`

DATA CONDITION: `identity_summary.slots`, Element refs, up to three published
findings, `hero_portfolio` anchor/common thread, and evidence refs.  
VISUAL MODE: Synthesis relationship map and compressed barcode/signature strip;
reuse prior cells/bands/bridges/forks/chronology. No tarot, RPG, horoscope, or
fixed player-type treatment.  
STORY POSITION: Coherence → Signature → Depth, reference screens 28–32.  
EVIDENCE DISCLOSURE: `Why this describes your Dota.` opens exactly Signals,
Twist, and Anchor evidence groups when available, with refs and limitations.  
NEUTRAL STATE: `Your Dota Signature is still taking shape.`  
INSUFFICIENT STATE: `There is not enough stable evidence to name a Signature
yet.`  
MIXED STATE: `Your Signature has a clear core and a context-dependent twist.`  
ACCESSIBILITY REQUIREMENT: Signature relationships have a list/table equivalent
with the same labels and refs; no understanding depends on motion, contrast
passes grayscale, and card text remains readable at 200% zoom.  
PRIVACY REQUIREMENT: No numeric hero ID, account ID, raw evidence ref, rank/MMR,
private slot key, or protected cohort reference is rendered or tracked.  
SHARE REQUIREMENT: The Signature card exists only when the server's identity
candidate is eligible; absent/partial/descriptive-only slots remain in-report.  
SOURCE-BINDING IMPACT: Presentation of existing slots and evidence; Signature
is evidence-derived and does not create a new identity taxonomy.  
DEFINITION OF DONE: Signature follows all relationship chapters, each descriptor
traces to a displayed source, missing slots stay absent, Depth names only actual
offers, and no unsupported identity label is introduced.

### A-08 — Actual share gallery and native-share/download flow

CHANGE ID: `A-08`  
TYPE: `A FRONTEND-ONLY`  
CURRENT FILE(S): `apps/web/app/report/[reportId]/v6/report-story-v6.tsx`; `apps/web/app/report/[reportId]/v6/report-story-v6.module.css`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: Main V6.1 composer offers text copy only and does not present
the server SVG as a standalone collectible gallery.  
REQUIRED BEHAVIOR: After Signature, fetch only `eligible=true` candidates from
the existing share route, show a contact-sheet/gallery of actual outputs, and
support SVG preview, download, `navigator.share` when available, and clipboard
fallback. Use the report URL as the landing link when a link is shared.  
EXACT COPY:

- `Your Dota DNA, in pieces.`
- `Choose the part that feels most like you.`
- `Download card`
- `Share card`
- `Copy link`
- `Copy text`
- No-card neutral: `Your story is ready to keep, even when no standalone card
  clears the share gate.`
- No-card insufficient: `No standalone share card is eligible from this report.`
- Mixed: `Some parts are share-ready; the rest stays inside the report.`

DATA CONDITION: `report_id`, `share_candidates[*].eligible`, candidate kind,
reason/blockers, evidence refs, and the existing
`/v1/reports/{report_id}/share/{card_type}` route.  
VISUAL MODE: Standalone editorial contact sheet; each card inherits the
Signature strip, Element language, grid, typography, hero treatment, and
evidence hierarchy.  
STORY POSITION: Share, after Signature and Depth.  
EVIDENCE DISCLOSURE: Card preview remains readable outside the app; eligibility
and source rationale are available as a compact disclosure, not a raw key dump.
  
NEUTRAL STATE: `Your story is ready to keep, even when no standalone card clears
the share gate.`  
INSUFFICIENT STATE: `No standalone share card is eligible from this report.`  
MIXED STATE: `Some parts are share-ready; the rest stays inside the report.`  
ACCESSIBILITY REQUIREMENT: Each card has a heading/description, keyboard
selection, focus state, explicit download/share labels, error recovery, text
alternative, and no motion-dependent interaction.  
PRIVACY REQUIREMENT: Never display or track account/report/match/session IDs,
tokens, raw hero IDs, rank/MMR, self-estimates as evidence, or protected refs.
  
SHARE REQUIREMENT: Client filters server candidates only; no client-created
candidate, no ineligible card, no recommendation card, no fixed card count.
Download uses the server SVG; native share includes the existing report URL when
available and uses clipboard fallback otherwise.  
SOURCE-BINDING IMPACT: Client integration only; eligibility, card content, and
privacy filters remain server-owned.  
DEFINITION OF DONE: Actual eligible cards preview/download/share correctly,
empty/error/cancel paths are accessible, the report URL is stable, and no
standalone output contains raw identifiers.

### B-01 — V6.1 copy catalog replacement

CHANGE ID: `B-01`  
TYPE: `B COPY-CATALOG-ONLY`  
CURRENT FILE(S): `services/api/app/player_analysis_v61/copy.py`; `services/api/app/player_analysis_v61/versions.py`; `docs/product/v61-copy-data-basis-matrix.md`  
TARGET FILE(S): Same files; `docs/product/v61-story-content-spec.md`  
CURRENT BEHAVIOR: Semantic registry strings are safe and server-owned but use
research vocabulary such as compatible/frontier/variance in the foreground.  
REQUIRED BEHAVIOR: Replace foreground strings with the exact matrix-bound
human copy while retaining every semantic outcome key, evidence meaning,
alternative, forbidden-token guard, and copy version/source-binding review.
  
EXACT COPY: The complete exact string set is the headline, neutral,
insufficient, mixed, evidence, and limitation content in Sections 5–8 of
`docs/product/v61-copy-data-basis-matrix.md`. Required anchors include:
`More of your observed expression travels when the hero changes.`, `What does
your Dota look like after a loss?`, `Once the horn sounds, what keeps showing
up?`, `One match shows expression. A session shows whether it holds.`, `Your Dota
Signature.`, and `Not enough signal to call this one.` No new sentence may be
constructed from a raw key.  
DATA CONDITION: Matrix `required_condition` for the specific screen, Element,
family, or `semantic_outcome_key` is true; otherwise use its exact state
variant.  
VISUAL MODE: No visual change; copy supports Discovery, Evidence, Methodology,
and Synthesis modes.  
STORY POSITION: All story surfaces, in the frozen arc.  
EVIDENCE DISCLOSURE: Matrix evidence labels and limitations remain in Depth 2/3;
they do not move into the headline.  
NEUTRAL STATE: The exact row `neutral_variant`.  
INSUFFICIENT STATE: The exact row `insufficient_variant`.  
MIXED STATE: The exact row `mixed_variant`.  
ACCESSIBILITY REQUIREMENT: Copy remains readable at narrow width/200% zoom,
uses no color-only state, and preserves accessible labels.  
PRIVACY REQUIREMENT: No copy string may contain account IDs, match/session IDs,
rank/MMR, protected refs, or raw private keys.  
SHARE REQUIREMENT: Copy catalog changes do not grant share eligibility; only
server candidates can expose a string in Share.  
SOURCE-BINDING IMPACT: Bump/review the V6.1 copy surface only; preserve outcome
keys, claim contracts, alternatives, gates, and forbidden-token checks.  
DEFINITION OF DONE: Matrix and catalog enumerate the same registered outcomes,
catalog checks pass, all exact screen/state strings are covered, and no
analytical/model/calibration artifact changes.

### C-01 — Report/page presentation payload alignment

CHANGE ID: `C-01`  
TYPE: `C REPORT-ASSEMBLY-PRESENTATION`  
CURRENT FILE(S): `services/api/app/player_analysis_v6/story.py`; `services/api/app/reports/dna_assembly_v61.py`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files  
CURRENT BEHAVIOR: The server provides fixed nine-beat payloads and observed
fields, but chapter labels, reference composition, actual sample count, state
variants, and depth cues are not consistently presentation-bound.  
REQUIRED BEHAVIOR: Add/use presentation metadata inside existing page/story
content surfaces for the nine production labels, reference-screen composition,
actual `metadata.eligible_match_count`, state, evidence refs, and depth controls.
Do not add a new analytical field or change the strict nine-page tuple.  
EXACT COPY:

- `Start`, `Shape`, `Pool`, `Change`, `After loss`, `Match`, `Session`,
  `Signature`, `Share`.
- `{metadata.eligible_match_count} matches. One recurring signal.`
- `Here’s what we found in the way you play.`
- `How we measured this`.

DATA CONDITION: Existing `pages`, `story`, `metadata`, `identity`, `elements`,
findings, portfolio, methodology, and share fields.  
VISUAL MODE: Presentation payload identifies Discovery/Evidence/Synthesis mode
and Sequencing Field continuity; it does not compute a visual score.  
STORY POSITION: All beats.  
EVIDENCE DISCLOSURE: Payload must point to the existing evidence refs and
methodology fields used by the frontend; it must not duplicate raw receipts in
Story.  
NEUTRAL STATE: Existing server-bound neutral state with the approved human
sentence.  
INSUFFICIENT STATE: Existing server-bound insufficient state with one factual
reason.  
MIXED STATE: Existing server-bound mixed state with both component references.
  
ACCESSIBILITY REQUIREMENT: Payload exposes labels/status/refs needed for text,
table, disclosure, keyboard, reduced-motion, narrow, and zoom equivalents.  
PRIVACY REQUIREMENT: No new public identifiers; omit raw IDs from presentation
fields and analytics.  
SHARE REQUIREMENT: Payload may identify actual eligible candidates only; it may
not widen `share_candidates`.  
SOURCE-BINDING IMPACT: Presentation metadata only; preserve report schema,
element/family/outcome contracts, and server state.  
DEFINITION OF DONE: Frontend can render exact chapter/depth/state behavior from
existing fields without client inference, and schema/runtime analytical tests
remain unchanged.

### C-02 — Human hero labels and safe Signature/hero-mirror payloads

CHANGE ID: `C-02`  
TYPE: `C REPORT-ASSEMBLY-PRESENTATION`  
CURRENT FILE(S): `services/api/app/player_analysis_v6/hero_portfolio.py`; `services/api/app/reports/dna_assembly_v61.py`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; existing reviewed hero taxonomy provider under `services/api/app/heroes/`  
CURRENT BEHAVIOR: V6.1 portfolio rows expose numeric `hero_id` and functional
jobs without a public human hero name; Hero Mirror can fall back to raw fact
keys or IDs.  
REQUIRED BEHAVIOR: At the public presentation boundary, bind each displayed
hero to an existing reviewed human `name`/portrait label and observed
`match_count`/`share`; remove or suppress numeric ID/raw reference display. Use
the same safe label for Signature ANCHOR and Hero Mirror.  
EXACT COPY:

- `Before the patterns, there are the heroes.`
- `If we had to start with one hero…`
- `One hero doesn’t describe your Dota.`
- `Your Dota Signature.`
- `Why this describes your Dota.`
- Hero fact labels: `Matches`, `Share of your year`, `Mapped jobs`.

DATA CONDITION: Existing portfolio `hero_id`, count, share, reviewed taxonomy
name/portrait, functional jobs, timeline, and evidence refs; no win-rate field.
  
VISUAL MODE: Hero specimen, pool bands, and Signature anchor use one recurring
visual object; portrait is optional decoration, label is mandatory.  
STORY POSITION: Familiarity → Structure → Coherence → Signature → Share.  
EVIDENCE DISCLOSURE: Evidence may show human hero name, match count/share,
mapped-job label, and source limitation; no raw ID/ref.  
NEUTRAL STATE: `Your hero list has no single front row yet.`  
INSUFFICIENT STATE: `Not enough usable hero history to map the pool.`  
MIXED STATE: `The front row changes by part of the year.`  
ACCESSIBILITY REQUIREMENT: Portrait alt text and text/table row use the same
human label; all values have a nonvisual equivalent; no label relies on color.
  
PRIVACY REQUIREMENT: Numeric hero IDs, account IDs, match/session IDs, and raw
`player_behavior` keys never reach public UI, share SVG, or analytics.  
SHARE REQUIREMENT: Hero Mirror/identity cards use only safe labels and actual
server eligibility; no card is generated from a raw portfolio row.  
SOURCE-BINDING IMPACT: Presentation enrichment from the already reviewed hero
taxonomy; no new role inference, win rate, or semantic outcome.  
DEFINITION OF DONE: Every public hero fact has a human label, raw IDs are absent
from UI/share/analytics, Signature ANCHOR is traceable, and no new hero metric is
added.

### C-03 — Server-bound share candidate content

CHANGE ID: `C-03`  
TYPE: `C REPORT-ASSEMBLY-PRESENTATION`  
CURRENT FILE(S): `services/api/app/reports/dna_assembly_v61.py`; `services/api/app/share/service.py`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files  
CURRENT BEHAVIOR: Share candidates are eligible and privacy-gated, but card
content is generic and does not consistently carry the Signature/evidence
hierarchy into standalone output.  
REQUIRED BEHAVIOR: Keep the existing candidate kinds and maximum three. Bind
card title/body/labels to actual server output: identity uses eligible
Signature/identity slots, finding uses the exact matrix headline and a bounded
reason/evidence line, and hero mirror uses human hero labels and observed facts.
The client cannot synthesize a missing card.  
EXACT COPY:

- Identity title: `Your Dota Signature` only when the identity candidate is
  eligible.
- Finding title: exact matrix headline for the returned registered outcome.
- Hero mirror title: `Hero Mirror` with the returned human hero/common-thread
  label.
- Evidence label: `Observed in your summary history.`
- Limitation label: `Summary history only. No detail or replay reads.`

DATA CONDITION: Existing `share_candidates[*].eligible`, kind, reason, blockers,
evidence refs, identity slots, published finding, and hero mirror fields.  
VISUAL MODE: Standalone SVG/card inherits Element identity, Signature strip,
grid, typography, hero treatment, and evidence hierarchy; no app-only context
is required to understand the card.  
STORY POSITION: Share after Signature.  
EVIDENCE DISCLOSURE: One bounded evidence line and limitation are included in
the standalone artifact; raw refs remain private.  
NEUTRAL STATE: Do not create a finding card; use `Your story is ready to keep,
even when no standalone card clears the share gate.`  
INSUFFICIENT STATE: Do not create a card; use `No standalone share card is
eligible from this report.`  
MIXED STATE: Show only the eligible candidate subset; use `Some parts are
share-ready; the rest stays inside the report.`  
ACCESSIBILITY REQUIREMENT: SVG has title/description, readable contrast, text
labels independent of color, and a corresponding HTML/text preview.  
PRIVACY REQUIREMENT: No raw account/report/match/session IDs, numeric hero IDs,
protected refs, or self-estimates as evidence in SVG/text/analytics.  
SHARE REQUIREMENT: Candidate eligibility remains server-owned; existing route
and cache key remain stable; no new card type or public share endpoint.  
SOURCE-BINDING IMPACT: Presentation payload/card copy only; candidate selection,
claim contract, evidence refs, and privacy gates stay unchanged.  
DEFINITION OF DONE: Every returned eligible card is standalone-readable,
source-bound, human-labeled, version-stamped, and privacy-safe; ineligible or
missing outputs cannot be displayed.

### C-04 — Privacy-safe follow-up presentation response

CHANGE ID: `C-04`  
TYPE: `C REPORT-ASSEMBLY-PRESENTATION`  
CURRENT FILE(S): Existing V6 interaction response path in `services/api/app/api/routes.py`; `apps/web/lib/v6/interaction-client.ts`; `apps/web/app/report/[reportId]/v6/types.ts`  
TARGET FILE(S): Same files; `apps/web/tests/e2e/report-v6.spec.ts`  
CURRENT BEHAVIOR: The follow-up comparison response can include `match_ids`,
which violates the public aggregate-only presentation posture even though the
strict report schema hides identifiers.  
REQUIRED BEHAVIOR: Keep the five-game verification interaction aggregate-only;
remove raw match IDs from the user-facing response and client type. Preserve
the factual comparison and non-causal guardrail.  
EXACT COPY:

- `This compares the next five matching games. It does not claim causality or
  change your Signature.`
- Incomplete: `The check-in is not ready yet.`
- Queued: `Your deeper question is queued.`

DATA CONDITION: Existing server-authored follow-up aggregate/verification fields
and status.  
VISUAL MODE: Compact aftercare disclosure after Signature/share; no raw-row
table.  
STORY POSITION: Optional aftercare after Session and after Signature/share; never
the report conclusion.  
EVIDENCE DISCLOSURE: Show aggregate count/progress and registered guardrail only;
do not show match IDs or raw transition rows.  
NEUTRAL STATE: `The check-in is not ready yet.` when no verified progress exists.
  
INSUFFICIENT STATE: `The check-in is not ready yet.` plus the server factual
missing condition.  
MIXED STATE: `Some parts of the check-in are ready; the rest stays unresolved.`
  
ACCESSIBILITY REQUIREMENT: Progress has text and `aria-valuenow`/`aria-valuemax`
when available; status/errors are announced; keyboard controls remain native.
  
PRIVACY REQUIREMENT: Strip match/session IDs and protected refs from response,
client state, UI, and analytics; aggregate counts only.  
SHARE REQUIREMENT: Follow-up output never becomes a standalone share card.  
SOURCE-BINDING IMPACT: Privacy/presentation projection only; verification rule,
five-game contract, and causal flag remain unchanged.  
DEFINITION OF DONE: API/client response contains aggregate fields only, existing
guardrail copy is preserved, privacy tests reject IDs, and the follow-up remains
optional after Signature/share.

### F-01 — Existing V6.1 share renderer extension

CHANGE ID: `F-01`  
TYPE: `F INFRA/SHARING`  
CURRENT FILE(S): `services/api/app/share/service.py`; `services/api/app/share/__init__.py`; `services/api/app/api/routes.py`  
TARGET FILE(S): Same files  
CURRENT BEHAVIOR: `/v1/reports/{report_id}/share/{card_type}` exists and the
response header/cache key use V6.1, but `_build_v6_share_svg` visibly stamps the
shared `V6_RENDERER_VERSION` constant even for V6.1 output.  
REQUIRED BEHAVIOR: Select the renderer footer/version from the report schema;
V6.1 SVG must display `FREE DNA / SHARE-SVG-6.1.0`, while V6.0 retains its own
stamp. Preserve the current eligibility filter, cache key, headers, noindex,
and immutable response behavior.  
EXACT COPY: `FREE DNA / SHARE-SVG-6.1.0` for V6.1; existing V6.0 footer for
V6.0.  
DATA CONDITION: Report schema version and existing eligible candidate payload.
  
VISUAL MODE: Standalone SVG with the current fixed grid and the C-03 card
content; no new hosting or transport.  
STORY POSITION: Share artifact only.  
EVIDENCE DISCLOSURE: Keep title/description and bounded evidence/limitation
labels; no raw refs.  
NEUTRAL STATE: Route returns no finding card when candidate is not eligible and
the frontend uses the exact no-card copy.  
INSUFFICIENT STATE: Route rejects/omits an ineligible card; no fallback SVG is
invented.  
MIXED STATE: Route renders only the eligible requested candidate; frontend
handles a partial gallery.  
ACCESSIBILITY REQUIREMENT: Preserve SVG title/description and HTML/text
fallback; version footer is supplementary, not the only state cue.  
PRIVACY REQUIREMENT: Preserve current noindex/cache/privacy guards; never add
IDs to SVG or query payload beyond the existing report route.  
SHARE REQUIREMENT: Existing route remains the stable downloadable/shareable
artifact path. No new backend capability, signed link, CDN, or endpoint.  
SOURCE-BINDING IMPACT: Renderer metadata/presentation only; cache/version
binding must remain deterministic and report-schema-aware.  
DEFINITION OF DONE: V6.1 footer is correct, V6.0 footer is unchanged, existing
share service tests pass, cache keys/headers remain bound, and no new endpoint
or analytical dependency is added.

## Classification summary

Every frozen change is classified below. Counts are change groups, not files.

### A FRONTEND-ONLY — 8

`A-01`, `A-02`, `A-03`, `A-04`, `A-05`, `A-06`, `A-07`, `A-08`.

### B COPY-CATALOG-ONLY — 1

`B-01`.

### C REPORT-ASSEMBLY-PRESENTATION — 4

`C-01`, `C-02`, `C-03`, `C-04`.

### D BACKEND-SEMANTIC — 0

No new Element, family, finding, outcome, denominator, threshold, qualification,
or semantic backend behavior is allowed.

### E ANALYTICAL/MODEL — 0

No estimator, model, calibration, threshold, holdout, evidence, or statistical
artifact change is allowed.

### F INFRA/SHARING — 1

`F-01` is an extension of the existing share renderer only. New backend
capability count: **0**.

## Release and implementation gates

The next worker may start only after this manifest is accepted as the input.

- Prompt B and Prompt C were read in full.
- The missing-direction blocker is removed; all stale source-document blocker
  wording is removed from active product/review docs.
- The 33-screen arc is adaptive, not fixed pagination.
- The exact emotional order, story-first hierarchy, Story/Evidence/Methodology,
  neutral/insufficient/mixed states, Signature evidence rule, and actual-output-
  only share rule are frozen.
- The correct matrix filename is verified.
- Current adjudicated provenance and the immutable historical record are
  distinguished; the exact release-doc patch plan is above.
- Existing share capability and limits are recorded; minimum scope is narrowed
  to frontend integration plus F-01.
- All implementation changes are classified; D=0 and E=0.
- No holdout rerun, calibration rerun, model change, runtime semantic change,
  authorization action, or deployment action is part of this manifest.

SAFE TO START PRODUCT IMPLEMENTATION: **YES**, after this manifest is accepted.
Release authorization remains **NO** until the separate provenance documentation
patch and all release gates are approved.
