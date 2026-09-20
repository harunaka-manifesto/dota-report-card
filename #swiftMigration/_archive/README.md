# Archive — evidence and history

> ⚠️ **Nothing in this folder is active product truth.**
>
> Everything here is superseded, non-normative, or exploratory. Candidate tables, thresholds, recommendations and open questions in these documents reflect the state at the time they were written. **Do not implement from them, do not design from them, and do not cite them to overrule an active SSOT.**
>
> The single exception is [`engine_specs/`](#engine_specs) — see below.
>
> Active product documentation lives in the feature folders described in [`../README.md`](../README.md).

Relative links **inside** archived documents may point at paths that no longer exist. That is expected. The mapping below tells you where each document's content went.

---

## superseded_ssots/

The original V1 contracts. Their content is consolidated into the feature folders; they are kept so the provenance of every consolidated rule is traceable.

| Document | Was | Consolidated into |
|---|---|---|
| `dota-tracker-v1-product-ssot.md` | LOCKED master product SSOT | `app_foundation/`, plus every feature SSOT |
| `match-lifecycle-v1.md` | ACTIVE SSOT | `app_foundation/SSOT.md` §4 |
| `role-resolution-and-correction-v1.md` | ACTIVE SSOT | `app_foundation/SSOT.md` §5; correction UX in `match_detail/` |
| `role-metrics-and-baselines-v1.md` | ACTIVE SSOT | `app_foundation/SSOT.md` §6–§9, §12 |
| `progress-and-history-v1.md` | LOCKED SSOT | `app_foundation/SSOT.md` §11, §14; `progress/`; `history/` |
| `Onboarding & Cold Start V1 — Single Source of Truth.md` | LOCKED SSOT | `onboarding/`; `settings_account/` |
| `living-player-profile-v1.md` | PROPOSED SSOT | `profile/` |

The metrics SSOT also contains **non-normative implementation audit** sections describing a candidate branch as of 2026-09-13. Those were snapshots of code state, never product contract, and are not carried forward.

---

## engine_specs/

**These two remain engineering-normative for algorithms.** They are here, not in the active surface, because a designer never needs them and their *product meaning* is fully captured in the active SSOTs.

| Document | Normative for | Subordinate to |
|---|---|---|
| `POST-MATCH-INSIGHTS-SSOT.md` | Insight-card specifications, eligibility thresholds, severity ladders, the frozen match-shape classifier, vision reconstruction, ranking and selection, contract versioning. Its machine-readable companion is `generated_data/post-match-final-audit-data/final-candidate-contract.json`. | `match_detail/SSOT.md` for product meaning |
| `CONTEXT-ADJUSTED-PERFORMANCE-V1.md` | Context-adjustment parameter derivation, coefficients, caps, per-metric context classes, failure/unavailable rules, validation evidence and production conditions. | `app_foundation/SSOT.md` §10 for product meaning |

If an annex and an active SSOT disagree on **what the product means**, the active SSOT wins and the annex is wrong. If they disagree on **a threshold or an algorithm**, that is a defect to fix, not a choice to make silently.

`CONTEXT-ADJUSTED-PERFORMANCE-V1.md` §17 lists edits it required to other SSOTs. **Every one of those edits has been applied** in the consolidation — see `app_foundation/SSOT.md` §10 (comparison semantics, context classes, floor rule, hard invariants), §11.1 (trend calibration floor), §5.6 (rebuild scope), and `match_detail/SSOT.md` §2 (insights never read context).

---

## decision_history/

| Document | What it is |
|---|---|
| `POST-MATCH-INSIGHT-DECISIONS-V1.md` | How the post-match insight owner calls were reached. Explicitly retained as decision history; superseded for normative behaviour by the engine spec. |

---

## research/

Non-normative feasibility, capability and architecture work.

| Document | What it is |
|---|---|
| `post-match-intelligence-feasibility-v1.md` | Feasibility study and proposed design for post-match intelligence. |
| `post-match-intelligence-deep-research-v2.md` | Provider capability research and live validation; superseded earlier data-capability claims. |
| `ten-player-match-intelligence-v1.md` | Ten-player acquisition and insight design; superseded for data-capability claims by the above. |
| `VISION-INSIGHT-ENRICHMENT-RESEARCH.md` | Whether the vision-cleared candidate deserved a card slot. |
| `LANE-DIFFICULTY-RESEARCH-V1.md` | The original lane-difficulty hypothesis. Superseded as the leading hypothesis by `engine_specs/CONTEXT-ADJUSTED-PERFORMANCE-V1.md`. |
| `native-ios-backend-reuse-audit.md` | Architecture audit recommending a native SwiftUI client over the existing backend, with a thin generated mobile contract. Not product documentation, and not a decision this folder governs. |

---

## validation/

Validation reports and audits. Each has its evidence in `generated_data/`.

| Document | What it is |
|---|---|
| `post-match-deterministic-candidate-validation-v1.md` | Validated candidate menu across the four locked families. |
| `post-match-tier-b-match-shape-validation-v1.md` | Match-shape / fallback intelligence validation. Its §13 recommendation was never SSOT. |
| `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` | Final ranking, history-claim and player-context audit; closed the last open areas. |
| `SMOKE-TO-KILLS-VALIDATION.md` | Validation spike for the optional playback enrichment. |

---

## generated_data/

Machine outputs and the research code that produced them. Kept so any number in a validation report can be reproduced.

| Folder | Contents |
|---|---|
| `post-match-candidate-validation-data/` | Candidate results, definitions, examples, metrics — plus `research-code/`. |
| `post-match-tier-b-validation-data/` | Shape definitions, classifications, threshold grids, review sheets (`.md` / `.html`), result JSONs — plus `research-code/`. |
| `post-match-final-audit-data/` | Ranking/holdout/coverage results, every rating file, review sheets, the **`final-candidate-contract.json`** machine-readable insight contract — plus `research-code/`. |

Note: research code for these three sits inside its data folder rather than under `scripts/`, so the relative paths in the reports that reference it still resolve.

---

## scripts/

Standalone research code with no co-located data folder.

| Folder | Contents |
|---|---|
| `lane-difficulty-research-code/` | Lane-difficulty research, including `pass2/` — the reproduction code for the context-adjustment model. |
| `vision-insight-research-code/` | Vision-enrichment research code. |

None of this code runs at build time or at runtime. Nothing in the repository outside `#swiftMigration/` referenced these paths before the reorganisation, and nothing does now.
