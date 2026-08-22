# Pattern presentation

Free DNA v5.2 keeps the existing Elements → Patterns qualification model and
adds a versioned Wrapped + Depth presentation layer. Pattern qualification and
recommendation evidence remain backend-owned; the web app renders the
immutable presentation payload and does not recalculate scores.

## Story contract

Every surfaced Pattern follows the same bounded sequence:

1. **Reveal** — a human-readable conclusion.
2. **Visual proof** — one reusable visual family backed by structured facts.
3. **Interpretation** — one reviewed explanation of what the evidence supports.
4. **Do this next** — a reviewed hero or practice action when the gates clear.
5. **Deep Dive** — an optional premium bridge to the next diagnostic question.

The API carries IDs and facts rather than arbitrary prose:

```text
pattern_id
outcome_id
semantic_outcome_id / semantic_outcome_version
visual_variant
proof_data
interpretation_id
recommendation_id / recommendation_context
semantic_recommendation_id / semantic_recommendation_version
deep_dive_id
evidence_refs
raw_metrics
confidence
presentation_version
```

`services/api/app/behavior/presentation.py` owns the finite Pattern → outcome
→ visual mapping. `services/api/app/behavior/display_bands.py` owns the
human-readable thresholds. `services/api/app/content/free_dna/semantic_en.json`
owns active semantic branch copy, while `en.json` remains the legacy
compatibility catalog. `content/renderer.py` restricts substitutions to
approved display facts. No runtime LLM call or fragment-built sentence is
allowed in this path.

## Visual families

| Patterns | Visual family | Primary proof |
|---|---|---|
| P01 Same Playbook | `hero_job_cluster` | Full hero names grouped by repeated jobs |
| P02 Comfort Edge | `hero_reliability_ladder` | Anchor / Close / Still developing pool |
| P03 Partial Transfer | `transfer_split` | Familiar versus off-pool presence and result direction |
| P04 Versatile Core | `toolkit_orbit` | Covered, thin, and missing functions |
| P05 Proven Flexibility | `flex_window_grid` | Valid window, hero counts, and functional jobs |
| P06/P07 recovery patterns | `post_loss_transition` | Loss → next game direction and supported context |
| P08/P09 presence patterns | `presence_exposure_map` | Involvement versus death-exposure bands |
| P10/P11 session patterns | `session_curve` | Game 1 through Game 5+ with display bands |

The web components live under
`apps/web/app/components/story/patterns/`. The old renderer remains a
fallback for historical reports that predate the presentation payload. Active
v5.2 reports use `PatternStoryScreen` and the reusable visual families.

## Human display bands

The primary story does not expose deltas, z-scores, K+A rates, or internal
bucket names. Stable thresholds translate evidence into reviewed labels:

- Relative performance: Much stronger, Stronger, About usual, Weaker, or
  Much weaker than usual.
- Presence: Shows up often, About usual, or Shows up less.
- Death exposure: High cost, Typical cost, or Low cost.
- Session position: Game 1, Game 2, Game 3, Game 4, or Game 5+.
- Session curve: Above usual, About usual, Below usual, Lowest point, Slow
  start, Warming up, or Strongest.

Raw values remain in `raw_metrics` and expanded evidence for auditability; the
presentation layer is responsible for keeping them out of the reveal and
interpretation copy.

## Versions and compatibility

The current report remains `free-dna-report-5.2.0`; the interaction closure is
versioned independently as `free-story-5.3.0` with `pattern-presentation-5.2.0`.
The active meaning layer is `pattern-outcomes-5.2.0` (32 semantic outcome
branches) plus `hero-recommendations-semantic-1.1.0` (14 semantic
recommendation IDs). Active branch copy is
`free-dna-semantic-copy-5.2.0`; `free-dna-copy-5.4.0` is the legacy
11-record catalog retained for historical snapshots and compatibility reads.
The Element registry is `free-elements-5.2.0` and the Pattern registry remains
`free-patterns-5.1.0`. Hero knowledge has an independent version family and
enters the API through the composed full-roster provider, not through raw
source scrapes.

Reports with schema v5.0 or v5.1 remain readable. Their absence of a
presentation payload selects the legacy story renderer; they are never
silently reinterpreted with a newer hero-knowledge snapshot or semantic copy
catalog. The complete artifact and fixture map is maintained in the
[v5.2 SSOT](dota-dna-ssot.md).

## Editorial QA

Run `make copy-review-catalog` to regenerate
`docs/generated/free-dna-v5.2-copy-review.md`. The generator enumerates all
32 registered semantic outcome branches and 14 recommendation IDs, plus the
11 historical compatibility records, with exact resolved strings, approved
placeholders, evidence requirements, and fallback status. `make docs-check` and
`make copy-review-catalog-check` fail if the generated review surface is stale
or either catalog contains an invalid branch or placeholder.
