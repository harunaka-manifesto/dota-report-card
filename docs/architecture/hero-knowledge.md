# Hero knowledge pipeline

The hero knowledge pipeline creates reviewable, versioned data for
recommendations and future Deep Dive analysis. It is a build-time pipeline;
the production API never scrapes and never invokes an LLM. The v5.2 semantic
freeze adds a reviewed pilot overlay to the generated snapshot and makes that
snapshot the active provider for semantic hero recommendations.

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
├── semantics/pilot-v1.json
├── knowledge/<knowledge-version>.json
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
functions: primary and secondary derived jobs
demands: commitment, access, execution, exposure, and evidence-backed bands
capabilities: initiation, save, mobility, teamfight, push, and other facts
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

The checked-in pilot semantic layer is controlled data, not user-facing copy.
It freezes the functional-job vocabulary, demand families, finite bands, and
review status for Axe, Centaur Warrunner, Puck, Dazzle, Nature's Prophet,
Phantom Assassin, Beastmaster, Oracle, Meepo, and Invoker. OpenDota support is
`unknown` in the offline pilot fixture, so recommendation confidence is
reduced and no current-meta claim is made.

## Commands

```bash
python -m scripts.hero_knowledge.cli fetch valve --hero axe
python -m scripts.hero_knowledge.cli normalize valve --snapshot-id <id>
python -m scripts.hero_knowledge.cli fetch opendota --hero axe
python -m scripts.hero_knowledge.cli normalize opendota --snapshot-id <id>
python -m scripts.hero_knowledge.cli fetch valve-plus
python -m scripts.hero_knowledge.cli build --pilot
python -m scripts.hero_knowledge.cli validate all --all
python -m scripts.hero_knowledge.cli diff --old <old.json> --new <new.json>

# One scheduler-friendly end-to-end run:
python -m scripts.hero_knowledge.cli refresh --force-refresh

# Offline OpenDota fixture path for parser/tests:
python -m scripts.hero_knowledge.cli refresh \
  --opendota-fixture-dir tests/fixtures/hero_knowledge/opendota \
  --hero axe

# Rebuild the checked-in v5.2 semantic-freeze pilot snapshot and review gate:
python -m scripts.generate_semantic_freeze_snapshot
PYTHONPATH=services/api python scripts/generate_hero_knowledge_pilot_review.py
```

The required OpenDota path fails non-zero when a selected endpoint is
unavailable or drifts schema. Valve Plus reports its optional health state and
continues. Active v5.2 analysis consumes the generated snapshot through
`SnapshotHeroKnowledgeProvider`; the report records its knowledge and
semantic-outcome versions. `TaxonomyHeroKnowledgeProvider` remains an
explicit compatibility adapter for historical callers and features that have
not migrated yet.
