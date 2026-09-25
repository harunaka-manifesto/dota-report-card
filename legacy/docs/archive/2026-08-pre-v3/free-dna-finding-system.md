# Free DNA finding system

The Free report is now a deterministic, summary-only finding-led product. The
public story is assembled from one immutable report snapshot; the UI does not
recalculate analytics and no runtime language model is used to write claims.

```text
summary history
  -> canonical eligible rows
  -> DNA features + eight dimensions
  -> cross-signal finding signals
  -> gated finding candidates
  -> ranked/conflict-checked story
  -> identity, experiment, and share cards
```

## Boundary and invariants

- Free uses the existing bounded player profile/history path and performs no
  match-detail reads, replay parsing, or new paid data requests.
- Finding inputs are limited to normalized summary history, existing DNA
  features/dimensions, existing summary pattern observations, and the factual
  hero identity/taxonomy already derived from that corpus.
- Every public finding has at least two evidence receipts. Receipts describe
  a metric, comparison, sample size, coverage, and confidence; raw match IDs,
  account IDs, and normalized rows remain private.
- Copy is catalog-driven and checked for causal, psychological, diagnostic,
  and guaranteed-outcome overclaims.
- The eight dimensions remain in the report as supporting evidence and in the
  DNA X-ray page. Findings add synthesis; they do not replace the dimensions.
- The public report is noindex and expires through the existing report
  retention path.

## Domain package

The backend package at `services/api/app/findings/` owns the new behavior:

| Module | Responsibility |
|---|---|
| `models.py` | Immutable private signals, candidates, experiments, and story selections. |
| `context.py` | Summary-only context adapter. It asserts that finding and DNA populations are identical. |
| `signals.py` | Derives dimension, DNA-feature, summary-pattern, session, and hero signals. |
| `registry.py` | Versioned finite registry of supported findings, priors, thresholds, and concept tags. |
| `evaluator.py` | Evaluates rules and applies publication gates; suppressed candidates stay internal for QA. |
| `ranking.py` | Stable editorial ranking with deterministic key tie-breaking. |
| `conflicts.py` | Redundancy/conflict suppression and thesis/strength/edge/leak/experiment slot selection. |
| `experiments.py` | Player-observable behavior checks attached to eligible findings. These do not promise automatic follow-up tracking. |
| `copy.py` | Finding copy resolution and neutral-claim linting. |

The current registry covers cross-signal stories such as broad-pool/narrow-
safety-zone, many heroes/same toolkit, activity versus results, loss-response
changes, session tax, long-game edge/leak, form versus identity, strength with
a tax, signature-hero mechanism, role versus hero identity, volatile results
with stable style, and a hidden-strength fallback.

## Evidence and publication

Signals are grouped into these evidence families:

- `dimension` — one of the eight existing DNA dimensions;
- `dna_feature` — hero pool, role, activity, performance, session, or related
  feature facts;
- `summary_pattern` — an existing summary-only pattern detector result;
- `hero_identity` / `hero_pattern` — factual hero identity and taxonomy-backed
  toolkit information;
- `session` and `derived_summary` — bounded session transitions and derived
  summary comparisons.

A candidate is publishable only when it has two or more receipts, the required
number of distinct evidence families, sufficient confidence, the required
sample sizes, and non-zero coverage. Finding confidence weights the weakest
receipt most heavily (`0.65 * weakest + 0.35 * mean`) and is then mapped to
`limited`, `moderate`, or `high`. A candidate also receives a stable priority
from confidence, surprise, specificity, consequence, actionability, and
shareability. Low-confidence or redundant candidates are omitted from the
public story rather than softened into unsupported claims.

The finding registry, ranking algorithm, conflict selector, story selector,
and report schema each carry an explicit version. Those versions participate
in Free completed-report compatibility fingerprints, so changing a rule,
ranking, story selection, or public contract cannot silently reuse an old
snapshot.

## Public contract

`services/api/app/reports/dna_assembly.py` emits
`free-dna-report-2.0.0`. The validator in
`services/api/app/api/report_schemas.py` enforces:

- exactly eight dimension keys;
- public finding receipts without private provenance fields;
- unique finding and page IDs;
- story page order matching the page array;
- finding and experiment page references resolving to public objects;
- identity-card, DNA X-ray, and deep-dive pages;
- no raw account/match identifiers or legacy/deep payloads.

The validator still accepts the existing v1 Free schema, and the web app keeps
the v1 story renderer for compatibility. New reports use the v2 finding-led
renderer. The v2 share set is `identity`, `exposed`, and `strength`; the
existing `dna`, `heroes`, and `final` card aliases remain available so older
links and clients do not break.

## Frontend story

`apps/web/app/report/[reportId]/dna/report-story-v2.tsx` renders one vertical
story from the API page order. It supports keyboard navigation, hash/session
resume, finding evidence disclosure, related dimension spectra, experiment
instructions, identity sharing, the eight-dimension DNA X-ray, the hero identity
card, and a Deep Scan handoff. Telemetry is provider-neutral and identifier-free;
page views/exits, finding views, evidence opens, experiment views, and finding
share starts/completions carry report-safe context only.

## Extension seam

Deep Scan can reuse the immutable finding models, ranking, conflict selection,
copy lint, and story contracts after its richer evidence families are mapped
into the same interfaces. Free must remain summary-only: a Deep finding must
never be allowed to enter the Free evaluator merely because it has a similar
headline.
