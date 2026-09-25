# Free DNA V6.1 Figma documentation update agent brief

Status: State D Markdown handoff ready; Figma execution blocked on user input.

This brief documents the State A implementation contract. It does not imply
State B calibration, State C public-release approval, or completed Figma work.

## Objective

Document the additive V6.1 product in the existing Figma knowledge base while
preserving every V5.2 and V6.0 frame as historical/current compatibility
evidence. This is a documentation update, not permission to redesign the
runtime contract.

Non-goals: do not create an eighth Element, a sixth family, a player type,
runtime threshold, public experimental view, or interaction unsupported by the
API. Do not modify repository code or enable rollout flags in the Figma task.

## Source of truth

Use, in order:

1. `docs/architecture/free-dna-v6.1-feature-graph.md`
2. `docs/decisions/0001-free-dna-v6.1-additive-generation.md`
3. V6.1 registries and strict API schema
4. generated V6.1 model/copy catalogs
5. existing Figma V5.2 knowledge-base conventions

Direct repository references:

- [V6.1 feature graph](../architecture/free-dna-v6.1-feature-graph.md)
- [V6.1 statistics](../architecture/free-dna-v6-statistics.md#v61-statistical-branch)
- [relationship presentation](../architecture/pattern-presentation.md#v61-relationship-presentation)
- [report flow](../architecture/report-flow.md#v61-opt-in-flow)
- [evidence contract](../evidence-contract.md)
- [release gates](../qa/free-dna-v6.1-release-gates.md)
- [generated copy review](../generated/free-dna-v6.1-copy-review.md)

Implementation anchors are
`services/api/app/api/report_schemas_v61.py`,
`services/api/app/reports/dna_assembly_v61.py`,
`services/api/app/player_analysis_v61/semantic_outcomes.py`, and
`apps/web/app/report/[reportId]/v6/report-story-v6.tsx`. Verification anchors
are `tests/unit/test_free_dna_v61_contract.py`,
`tests/unit/test_v61_contract_boundaries.py`, and
`tests/unit/test_v61_estimators.py`.

Runtime values must come from report evidence. Do not turn example values into
thresholds, imply rank/MMR, or add causal, personality, positioning, death-
quality, fatigue, tilt, or intent language.

## Required pages and frames

- A generation map showing V5.2, V6.0, and additive V6.1 compatibility.
- The canonical one-request input projection, missingness/coverage behavior,
  hashes, and the detail/parse/rank/MMR prohibition.
- Seven Element documentation frames.
- Five family-root frames with nested semantic outcomes and the two-stage FDR
  gate.
- A private 128-signal graph overview that exposes classifications and rejected
  boundaries without presenting private signals as public results.
- PRIMARY, TWIST, and ANCHOR identity states, including empty-slot examples.
- All finite relationship interactions plus keyboard/table/disclosure and
  reduced-motion alternatives.
- Claim layers: observation, interpretation, alternatives, recommendation,
  two-metric five-game verification, limits, and optional opaque Deep handoff.
- State A/B/C release-readiness documentation and shadow-only treatment for
  lifecycle, eras, and behavioral loops.

## Required component states

Show qualified, mixed, insufficient, unavailable, suppressed, and experimental
evidence states. Show zero, one, two, and three published outcomes. Include
possibly-truncated history and sub-80% optional-field coverage. Include
relationship disclosure closed/open, keyboard focus, 200% zoom, narrow mobile,
and reduced-motion variants.

V6.1 must remain coherent with zero published outcomes. In that state the
combat, strongest, secondary, recommendation, and Deep beats are unavailable
or skippable; no suppressed branch claim, question, or finding share card may
appear. One-, two-, and three-outcome examples may use only registered,
qualified fixtures.

## Compatibility and annotation rules

Label all V6.1 frames `free-dna-report-6.1.0`. Keep V6.0 labels and examples
unchanged. Annotate every example as illustrative. Link semantic frame names to
registered outcome keys and interaction kinds. Mark `hero_lifecycle`,
`identity_eras`, and `behavioral_loop` as shadow-only and not public/shareable.

The implementation registers 25 public-candidate definitions and withholds the
three shadow-only definitions above. Because all V6.1 generation flags default
off and State B/C evidence is absent, Figma must document the implemented
contract without labeling any V6.1 outcome as publicly launched.

## Verification checklist

- Counts are exactly 7 Elements, 5 roots, 28 semantic outcomes, and 128 private
  signals.
- All 18 version surfaces match the checked-in matrix.
- No public frame exposes raw rows, match/account IDs, protected cohorts,
  research-only signals, or rejected inference.
- Copy matches the generated V6.1 copy-review catalog.
- Every visual relationship has a nonvisual equivalent.
- State A is not labeled production-ready.

## Required user input before Figma work

Provide the target Figma file URL/key and the destination page or parent node.
No file, page, or node identifier is inferred from older documentation.

The V5.2 SSOT contains a historical Report-file link, but it is not sufficient
authority to select a V6.1 destination. The user must explicitly confirm the
target file and parent page/node; this is the only blocking user input.

## Data-to-design mapping

| API path | Component/state | Display rule | Fallback | Implementation proof |
|---|---|---|---|---|
| `schema_version`, `versions.*` | generation annotation | exact V6.1 labels | retain V6.0 labels | strict schema |
| `quality.published_findings` | story variant | 0–3 only | truthful zero state | assembly contract test |
| `elements[0..6]` | seven Element cards | server estimate/status/interval/coverage | unavailable, never neutral | estimator tests |
| `findings[*].published` | outcome reveal | branch only when true | family-not-published state | branch-leak test |
| `findings[*].claim_contract` | claim layers | claim, evidence, interpretation, alternatives, optional recommendation/verification | absent when unpublished | copy registry |
| `findings[*].interaction.kind` | relationship interaction | finite registered kind | text evidence table/disclosure | web types/renderer |
| `identity_summary.slots` | identity composition | PRIMARY + optional TWIST + ANCHOR | absent slot remains absent | identity slot test |
| `supporting_evidence` | evidence disclosure | selected bounded evidence only | insufficient/unavailable | public schema |
| `reproducibility.history_contract` | provenance | hashes, counts, completeness, coverage | truncation warning | parity test |
| `claim_contract.verification` | follow-up | five games, primary + guardrail | “too early to tell” | strict schema |
| `claim_contract.deep_handoff` | Deep CTA | opaque cohort ref + alternatives | no CTA when unpublished | branch-leak test |
| `share_candidates` | share composer | eligible registered candidate | identity/Mirror or no finding card | privacy test |

Analytics annotations must not include account/report/match identifiers, player
name, outcome direction, Element zone, or identity text as dimensions.

## Accessibility and responsive annotations

- Keyboard order reaches reveal controls and evidence disclosure in reading
  order; pointer gestures are never the only path.
- Every relationship graphic has a real table/disclosure alternative with the
  same labels and values.
- State does not rely on color alone; annotate text/icon/state names and
  screen-reader labels.
- Reduced motion removes transitions without removing content or gates.
- Document narrow mobile, long copy, visible focus, and 200% zoom. Tables may
  scroll inside a labeled region but cannot clip values.

## Prototype behavior

Prototype only payload-supported transitions. Reveal state does not change the
statistical result. Resume can restore the immutable report and presentation
progress but cannot reselect outcomes. Verification stays “too early to tell”
until five qualifying post-cutoff games exist. Unsupported interactions fall
back to static copy plus evidence table. Do not animate continuous precision
when the API provides only a band or bounded state.

## Figma-agent deliverables and Definition of Done

- Update pages, components, state diagrams, prototypes, and annotations without
  changing historical V6.0 frames.
- Supply a changelog with links to every changed node and its decision.
- Complete parity and accessibility checklists against the paths/states above.
- Provide exports for zero/one/two/three findings, every finite interaction,
  unavailable/mixed/truncated states, follow-up, share, and Deep handoff.
- Return unresolved questions rather than encoding invented behavior.
- Confirm lifecycle, era, and loop candidates remain internal/shadow-only and
  the document does not claim a public launch.
