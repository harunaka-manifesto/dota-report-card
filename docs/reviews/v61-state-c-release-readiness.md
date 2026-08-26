# Free DNA V6.1 State C release readiness

Review date: 2026-08-26
Decision scope: product narrative/content/comprehension readiness only
Analytical/runtime changes in this batch: none
Production authorization in this batch: none

## Executive decision

**Current user experience ready to ship: YES.**

**Implementation required: COMPLETE.**

The supplied analytical/runtime provenance is accepted for this review as a
completed, adjudicated one-time holdout execution. The V6.1 implementation has
the necessary summary-only capabilities and strict privacy/schema guards. The
State C product implementation is complete: story ordering, human-first copy,
progressive evidence disclosure, Signature/share conclusion, explicit
uncertainty states, human hero labels, and aggregate-only follow-up responses
are implemented and verified without changing analytical behavior.

Prompt B, the design constitution, and Prompt C, the complete storyboard, were
read in full on 2026-08-25. Prompt B governs visual grammar and disclosure;
Prompt C is a maximal 33-screen reference arc. The implementation remains the
existing nine API beats and adapts screen count to actual evidence.

This document does not authorize rollout, deployment, holdout rerun, evidence
regeneration, calibration, retraining, recalibration, threshold change, schema
change, semantic qualification change, or backend analytical change.

## Summary table

| Review area | Status | Evidence | State C disposition |
|---|---|---|---|
| **STATISTICAL REVIEW** | **PASS** | Current adjudicated provenance: execution SHA `7df38e6d234ae9c4ee425490bc40b8cc92685f85`, verifier/adjudication SHA `020118260abde18350be4c0605c1473d1756435e`, adjudication artifact `7ddbc5ddd22ca77a3200852f82b5f5af3c2293e6816b183b107c73d62bacde57`, exactly once, 339/339 unique profiles, zero errors, zero OpenDota calls, `HOLDOUT_ADJUDICATION_PASS`. | Accept as unchanged analytical evidence for this documentation review. Do not rerun. Copy must remain inside the registered claim contracts. |
| **DOTA LANGUAGE** | **PASS** | All 25 public semantic outcomes use the reviewed human-first catalog; hero/job labels are public display labels. | Keep research vocabulary inside Evidence/Methodology. |
| **DATA BASIS** | **PASS** | Headlines, state variants, Signature slots, and share candidates remain bound to existing report fields and the copy/data matrix. | No new data source or client inference introduced. |
| **PRIVACY** | **PASS** | Follow-up payloads omit `session_id` and raw `match_ids`; public hero anchors require display names; interaction analytics remain identifier-safe. | Regression coverage is in API/unit and browser tests. |
| **COPY OVERCLAIM** | **PASS** | Qualified, neutral, insufficient, and mixed copy stays within registered claim contracts; shadow-only outcomes remain private. | No psychology, cause, rank/MMR, or unsupported gameplay claim. |
| **PRODUCT COMPREHENSION** | **PASS** | Nine adaptive beats now run Recognition→Share with Story/Evidence/Methodology depth, final Signature, and optional aftercare/Deep. | 2–3-second visual review passed at desktop and 375px. |
| **ACCESSIBILITY** | **PASS** | Native controls, headings, labels, progress, disclosures, relationship tables, focus treatment, reduced motion, 200% zoom, and 375px no-overflow are verified across the browser matrix. | Maintain the existing semantic and visual regression coverage. |
| **PACKAGE/CONTAINER INTEGRITY** | **BLOCKED** | The adjudicated bundle is `a6c1d0c08ceef553150c401b0711b24eb89aa4d316105b8977373f3cc79c4865`, but the local assembled package is stale and dirty-bound. The source-binding fix must be packaged from the clean candidate with separate deploy and analytical source metadata. | Create a fresh owner-authorized package from the immutable adjudicated bundle after the source-binding fix is committed. |

## Internal statistical review versus user copy

The statistical review passes the supplied unchanged evidence boundary. That
does not require putting statistical machinery on the first screen.

The V6.1 contract correctly provides:

- exactly seven public Elements and five family roots;
- at most three published outcomes;
- two evidence groups for public candidates;
- family-root and within-family hierarchical error control;
- abstention for missing, neutral, insufficient, and suppressed states;
- outcome-specific denominators and session gates;
- summary-only 365-day input with one physical history request;
- no detail reads, replay parses, rank, MMR, or raw public rows;
- explicit alternatives and non-causal five-game verification;
- protected opaque Deep handoffs;
- server-gated share candidates.

The current product problem is not that p-values, q-values, confidence
intervals, sample sizes, or estimator names are absent from Story. The problem
is that valid evidence receipts are currently too close to the headline. The
implementation must preserve the evidence and move its presentation to the
correct depth.

## Product readiness gates

| Gate | Pass condition | Current result | Required owner action |
|---|---|---|---|
| Narrative order | Recognition → Familiarity → Structure → Adaptability → Adversity → Expression → Time → Coherence → Signature → Depth → Share. | PASS in nine adaptive beats. | None. |
| Human-first copy | Primary headline understandable in 2–3 seconds and Dota-native. | PASS in rendered desktop/mobile review. | None. |
| Semantic boundary | No psychology, cause, role, positioning, death-quality, rank, or MMR inference. | PASS in catalog, schema, privacy, and overclaim review. | None. |
| Three depths | Story, Evidence, Methodology are distinct and progressive. | PASS through native disclosures. | None. |
| State honesty | Qualified, neutral, insufficient, mixed, suppressed, and unavailable have distinct states. | PASS in fixtures and browser coverage. | None. |
| Element contract | All seven exact meanings are visible without turning them into traits or scores. | PASS; teaser is separate from the full Evidence ledger. | None. |
| Family contract | All five families have human question, reveal, evidence, and bounded fallbacks. | PASS. | None. |
| Signature | Deterministic Dota DNA Signature with traceable PRIMARY/TWIST/ANCHOR evidence. | PASS; absent/unlabeled slots are omitted. | None. |
| Shareability | Only eligible identity/finding/mirror cards are visible and the image/native share path works. | PASS locally across preview, native share, download, link, and text fallbacks. | Production endpoint verification remains blocked by access. |
| Accessibility | Every new visual has keyboard/table/disclosure/reduced-motion/narrow/200% equivalent. | PASS across 45 browser scenarios and rendered review. | None. |
| Privacy | No public or analytics identifier leakage; follow-up stays aggregate-only. | PASS with dedicated unit/API/browser regressions. | None. |
| Source binding | Product direction, copy version, presentation payload, and release provenance agree. | BLOCKED: one runtime setting currently binds both deployed source and immutable analytical source. | Add a separate validated analytical-source binding before packaging/deploy. |

## Pre-implementation package facts (historical audit input)

The implementation audit found these useful existing controls:

- `FreeDnaReportV61Schema` enforces the seven Elements, five family records,
  maximum three published findings, exact nine-page order, opaque Deep handoff,
  one-request history contract, no rank/MMR, and no private report keys.
- `dna_assembly_v61.py` overlays V6.1 estimators and semantic contracts without
  changing the V6.0 base route, and redacts unpublished branch claims.
- `report-story-v6.tsx` preserves self-report under `user_reported`, uses native
  form controls, and has a text/table relationship fallback.
- The CSS supports visible focus, narrow layouts, 200% zoom test coverage, and
  `prefers-reduced-motion: reduce`.
- The server share service has a `share-svg-6.1.0` renderer and filters to
  eligible candidates.
- The current V6.1 identity object can carry optional `display_name` and
  `avatar_url`; the hero portfolio currently supplies observed `hero_id`,
  `match_count`, `share`, and functional jobs, but not hero win rate or human
  display labels in the base portfolio rows.

These were foundations, not a product pass. Before this implementation the renderer used `FREE DNA
06`, technical metric receipts, raw mirror fact keys, an old beat order, and a
copy-only share action. The server share footer also uses the V6.0 renderer
constant inside the shared V6 SVG builder; this is a presentation/share defect
to correct in the authorized implementation batch. No new share endpoint is
required: the existing report/card route is stable and server-gated.

## Copy and content disposition

### Keep

- the fixed nine-beat API grammar;
- server-owned outcome keys, claim contracts, alternatives, verification, and
  interaction kinds;
- self-estimate separation and `user_reported` storage;
- the strict zero/one/two/three finding behavior;
- the one-history-request summary-only boundary;
- typed PRIMARY/TWIST/ANCHOR slots;
- native controls and nonvisual relationship fallbacks;
- server eligibility for share and Deep.

### Rewrite or move

- `Summary-only identity report` → `Your Dota, seen as a shape.` in the topbar;
- `The strongest finding` → the family question and human reveal;
- `Estimate / 95% interval / Sample / Sessions / Confidence` → Evidence or
  Methodology;
- `Choose a next experiment` → `Try this next` in optional aftercare;
- raw `player_behavior` keys → reviewed human fact labels;
- V6.0 `06` wordmark → explicit V6.1 label;
- generic `No strongest finding was published` → family-specific neutral or
  insufficient story state;
- `Copy text` alone → server image/native-share/download plus clipboard fallback.

### Remove from Free V6.1

- legacy Deep Scan “Superpowers,” rank, and dashboard language;
- any psychology/cause inference;
- shadow-only lifecycle/eras/loop outcomes;
- raw identifiers and protected cohort references;
- recommendation as a primary conclusion before Signature/share.

## Implemented gap report

Counts are change groups, not files.

### FRONTEND-ONLY CHANGES — 8

1. Reorder/relabel the nine beat presentation to the production story arc.
2. Correct V6.1 topbar/rail labels and quiet utility states.
3. Implement Story/Evidence/Methodology progressive disclosure.
4. Add human-first visual compositions and accessible relationship fallbacks.
5. Implement family-specific qualified/neutral/insufficient/mixed/suppressed/
   unavailable states.
6. Add Signature/Why Signature rendering and humanized Hero Mirror facts.
7. Move recommendation/follow-up and Deep after Signature/share while keeping
   them optional and gated.
8. Wire server share image/native-share/download plus loading/error states.

### COPY-CATALOG CHANGES — 1

1. Add the human-first V6.1 outcome headlines, evidence labels, neutral,
   insufficient, and mixed variants from the copy-data matrix under a reviewed
   copy-version/source-binding change.

### REPORT-ASSEMBLY PRESENTATION CHANGES — 4

1. Add chapter/reference-screen composition metadata to the existing nine pages.
2. Add server-bound human evidence cues and state variants.
3. Replace numeric hero-ID anchor fallback with reviewed human display labels.
4. Correct V6.1 share payload/renderer metadata and candidate card content.

### INFRA/SHARING CHANGES — 1

1. Correct the existing V6.1 share renderer footer/card metadata path. Do not
   add a new public share service, image host, or analytical endpoint.

### BACKEND-SEMANTIC CHANGES — 0

No new semantic output or backend analytical behavior is required.

### ANALYTICAL/MODEL CHANGES — 0

No estimator, model, threshold, calibration, holdout, or evidence change is
required or permitted.

## Definition-of-done checklist

- [x] Prompt B constitution and Prompt C storyboard were read in full; the 33
  screens are treated as an adaptive reference arc, not fixed pagination.
- [x] Product copy/data/state specifications reconcile the exact emotional arc,
  three depths, uncertainty states, Signature evidence, and actual-output-only
  sharing.
- [x] Current adjudicated provenance is recorded with execution/verifier,
  adjudication artifact, bundle, corpus, and split digests; the original
  holdout remains consumed and is not rerun.
- [x] Release-owner applies the documentation-only current-versus-historical
  patch plan without rewriting historical evidence.
- [x] The nine API beats render the reference arc in the production order.
- [x] All 33 reference screens have an explicit merged/omitted disposition.
- [x] All seven Elements use the exact backend meaning and approved human copy.
- [x] All five families have qualified, neutral, insufficient, and mixed states.
- [x] Every headline remains bound to a matrix row and existing field.
- [x] Story, Evidence, and Methodology are separate depths.
- [x] Signature uses only traceable PRIMARY/TWIST/ANCHOR content.
- [x] Share shows only server-eligible identity/finding/mirror cards.
- [x] Share gallery renders only actual eligible candidates; it does not promise
  storyboard card types that the report did not return.
- [x] Raw IDs, rank/MMR, protected refs, and identifiers are absent from public
  UI, share output, and analytics.
- [x] Accessibility checks cover keyboard order, focus, screen-reader labels,
  table/disclosure alternatives, reduced motion, narrow mobile, and 200% zoom.
- [x] No runtime/model/calibration files, holdout evidence, or release artifacts
  are changed as part of copy/presentation implementation.
- [x] `docs/product/v61-copy-data-basis-matrix.md` is the verified filename; no
  filesystem rename is required.

## Blockers

1. The source-binding release fix must keep `RELEASE_COMMIT_SHA` as the
   truthful deployment identity while validating the immutable bundle and
   authorization against `FREE_DNA_V61_ANALYTICAL_SOURCE_SHA`.
2. The only assembled local V6.1 package is stale
   (`173089781cf85d6c360c5ad0a2739697b7de1e62`, dirty=true) and cannot be
   deployed.
3. Production deployment credentials, URLs, running database revision, and
   API/worker identities are unavailable in this workspace.

## Next safe action

The source-binding fix adds mandatory production
`FREE_DNA_V61_ANALYTICAL_SOURCE_SHA=7df38e6d234ae9c4ee425490bc40b8cc92685f85`
for V6.1 bundle and authorization validation while `RELEASE_COMMIT_SHA`
continues to identify the truthful product/API/worker deploy. This is source
bookkeeping only and does not alter analytical behavior. The final clean
candidate SHA is recorded in the release packet after commit; it is not the
holdout execution or verifier SHA.
