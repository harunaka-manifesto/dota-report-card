# Hero knowledge pipeline

The hero knowledge pipeline creates reviewable, versioned data for
recommendations and future Deep Dive analysis. It is a build-time pipeline;
the production API never scrapes and never invokes an LLM. The v5.2 semantic
freeze produces an approved full-roster snapshot. Runtime analysis uses
`FullRosterHeroKnowledgeProvider` against that snapshot; its structural
taxonomy adapter remains an explicit compatibility fallback only when a
generated record is unavailable or unapproved.

```text
Valve datafeed ───────┐
                      ├─ source normalization + provenance
OpenDota aggregates ──┘
Valve Plus (optional) ─┘
            ↓
deterministic mechanics, behavior, and confidence derivation
            ↓
versioned knowledge snapshot + manifest
            ↓
read-only HeroKnowledgeRepository
```

DOTABUFF is outside this graph. It is documented as an unsupported automated
source in [Hero data sources](hero-data-sources.md) and has no adapter,
fixture, command, or release role.

## Repository layout

The implementation lives under `scripts/hero_knowledge/` so source-fetch
dependencies do not inflate the API runtime package. Generated artifacts are
kept separate:

```text
services/api/app/heroes/data/
├── raw/valve/<snapshot-id>/
├── raw/opendota/<snapshot-id>/
├── raw/valve_plus/<snapshot-id>/
├── normalized/valve/<snapshot-id>.json
├── normalized/opendota/<snapshot-id>.json
├── normalized/valve_plus/<snapshot-id>.json
├── semantics/full-roster-v1.json
├── semantics/pilot-v1.json                 # historical pilot
├── knowledge/hero-knowledge-semantic-freeze-full-roster-v1.json
└── hero-knowledge-manifest.json
```

Raw snapshots are intentionally not bundled into normal CI fixtures. The
pipeline stores them for reproducibility, while tests use small representative
fixtures under `tests/fixtures/hero_knowledge/`.

## Product-facing record

Each `HeroKnowledgeRecord` contains:

```yaml
identity: canonical Valve ID, key, display name, attribute, complexity
mechanics: abilities, innate abilities, facets, talents, base stats
functions: primary and secondary reviewed jobs
demands: commitment, access, execution, exposure, and evidence-backed bands
capabilities: initiation, save, mobility, fight control, push, and other facts
position_credibility: primary, secondary, unsupported, or unknown for positions 1–5
empirical:
  bracket_performance: OpenDota picks/wins by source-labeled population
  duration_profile: OpenDota duration bins and observed outcomes
  item_profile: OpenDota item IDs, phases, counts, and shares
  matchup_profile: OpenDota opponent observations with population note
  optional_valve_plus: optional enrichment or {}
editorial: structured review fields plus existing source-file provenance
derived_characteristics: behavior and confidence outputs
provenance: field sources, source versions, timestamps, and rule versions
```

Unknown is a first-class value. A missing semantic fact is omitted or marked
`unknown`; a parser does not insert `0.5` merely because it lacks evidence.
Numbers are retained only when a source exposes a real number, such as a win
rate, match count, duration bin, or base stat.

## Mechanical derivation

Rules in `scripts/hero_knowledge/derive/mechanics.py` inspect normalized Valve
ability text and stats. Each emitted characteristic includes the ability/base
stat references and `mechanic-rules-1.0.0`. These are structured evidence
categories, not generated user-facing prose.

## Empirical derivation

OpenDota is the required empirical baseline. Its aggregate counts are
sample-aware and source-labeled. Item output is described as build
concentration, not item strength or causality. Duration output uses explicit
sample thresholds. Matchup output preserves `opendota_aggregate` and does not
claim a narrower player population. OpenDota does not expose lane-role
distribution in these payloads, so role flexibility remains explicitly
unknown rather than inferred from an unrelated field.

Valve Plus can add optional structured enrichment when its fixture/schema gate
passes. Its absence, unavailability, or invalid schema never blocks the
required Valve/OpenDota build.

Existing `heroes_metadata/*.md` files remain build-time editorial/research
evidence. The scraper never generates production copy and never overwrites
that corpus.

The checked-in full-roster semantic layer is controlled data, not user-facing
copy. It freezes the functional-job vocabulary, demand families, finite bands,
and review status for all 127 heroes. OpenDota support is `unknown` in the
allowed local corpus, so no current-meta claim is made. The ten-hero pilot
layer remains available under `semantics/pilot-v1.json` for historical review
and regression fixtures; it is not the active roster denominator.

## Current v5.2 artifact map

| Layer | Version or path | Role |
|---|---|---|
| Knowledge schema | `hero-knowledge-schema-1.0.0` | Normalized generated-record contract |
| Semantic rules | `hero-semantics-5.2.0` | Runtime semantic vocabulary/rules |
| Reviewed snapshot | `hero-knowledge-semantic-freeze-full-roster-v1` | 127 approved records |
| Semantic vocabulary | `hero-semantics-full-roster-v1` | `services/api/app/heroes/data/semantics/full-roster-v1.json` |
| Snapshot manifest | `services/api/app/heroes/data/hero-knowledge-manifest.json` | Declares active snapshot path, checksum, sources, schema, and freeze status |
| Snapshot file | `services/api/app/heroes/data/knowledge/hero-knowledge-semantic-freeze-full-roster-v1.json` | Checked-in reviewed records |
| Historical pilot | `hero-knowledge-semantic-freeze-pilot-v1` / `hero-semantics-pilot-v1` | `semantics/pilot-v1.json`; retained for review/regression history |
| Runtime provider | `FullRosterHeroKnowledgeProvider` | Active full-roster snapshot plus explicit compatibility fallback |
| Taxonomy fallback | `hero-taxonomy-2026-08-16` / `hero-taxonomy-manifest-1.0.0` | Full-roster structural compatibility data |
| Offline fixtures | `tests/fixtures/hero_knowledge/{valve,opendota}/` | Parser and source-schema checks |
| Outcome fixtures | `tests/fixtures/semantic_freeze/pattern-outcome-cases.json` | Semantic P01–P11 branch coverage |

The manifest is `full-roster-reviewed`, generated at `2026-08-22T00:00:00Z`,
and lists 127 approved heroes. Its `pilot_history_path` points to the
historical ten-hero layer so the active snapshot and its predecessor cannot be
confused.

## Commands

```bash
python -m scripts.hero_knowledge.cli fetch valve --hero axe
python -m scripts.hero_knowledge.cli normalize valve --snapshot-id <id>
python -m scripts.hero_knowledge.cli fetch opendota --hero axe
python -m scripts.hero_knowledge.cli normalize opendota --snapshot-id <id>
python -m scripts.hero_knowledge.cli fetch valve-plus
# Historical pilot fixture/build mode:
python -m scripts.hero_knowledge.cli build --pilot
python -m scripts.hero_knowledge.cli validate all --all
python -m scripts.hero_knowledge.cli diff --old <old.json> --new <new.json>

# One scheduler-friendly end-to-end run:
python -m scripts.hero_knowledge.cli refresh --force-refresh

# Offline OpenDota fixture path for parser/tests:
python -m scripts.hero_knowledge.cli refresh \
  --opendota-fixture-dir tests/fixtures/hero_knowledge/opendota \
  --hero axe

# Rebuild the active checked-in v5.2 full-roster semantic-freeze snapshot:
python -m scripts.generate_semantic_freeze_snapshot
# Regenerate the historical ten-hero pilot review artifact:
PYTHONPATH=services/api python scripts/generate_hero_knowledge_pilot_review.py
```

The required OpenDota path fails non-zero when a selected endpoint is
unavailable or drifts schema. Valve Plus reports its optional health state and
continues. Active v5.2 analysis composes the generated snapshot through
`FullRosterHeroKnowledgeProvider`; the report records its knowledge,
semantic-rule, and semantic-outcome versions. `SnapshotHeroKnowledgeProvider`
remains the direct reviewed-snapshot adapter, while
`TaxonomyHeroKnowledgeProvider` remains an explicit structural compatibility
adapter for historical callers and features that have not migrated yet.

## Recommendation contracts

Semantic recommendations are deterministic and versioned separately from hero
knowledge as `hero-recommendations-semantic-1.1.0`; active branch copy is
`free-dna-semantic-copy-5.2.0` and is reviewed in
`docs/generated/free-dna-v5.2-copy-review.md`. `double_down` maximizes familiar jobs and low learning distance;
`adjacent_move` keeps an anchor while adding a new job; `fill_gap` requires an
added job in the exact displayed coverage family; `change_angle` keeps an
anchor while changing reviewed demands; and `specialist` requires a reviewed
specialist demand signal. Position credibility is resolved independently from
broad taxonomy roles. Unknown position evidence remains `unknown` and cannot
be promoted into a primary or secondary fit.
