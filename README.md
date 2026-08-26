# Dota Report Card

An anonymous OpenDota player report built from one bounded summary-history read.

summary history → 18 Elements → 11 Patterns → Hero Portfolio → interactive story → Hero Mirror → share

An additive Free DNA v6 path is implemented behind `FREE_DNA_V6_ENABLED`:
summary history → 7 Elements → 5 finding families → 9-beat story → interactions → Deep diagnostics.
It remains disabled until measured synthetic and sealed-holdout gates, human
review, checksum-linked promotion, and operator rollout authorization pass.

Free DNA V6.1 is a second additive, disabled-by-default generation behind
`FREE_DNA_V61_ENABLED`. It preserves the V6.0 7/5 public ontology while adding
a canonical one-physical-request contract, a typed 128-signal private graph,
28 finite semantic outcomes, nested FDR, typed identity slots, and accessible
relationship evidence. It currently has State A fixture/synthetic evidence
only and is not authorized for public release.

Free DNA describes observable match behavior. It does not infer motives,
psychological states, grades, or replay-level causes.

## Local start

~~~bash
cp .env.example .env
make install
make test
make dev
~~~

Free mode reads the public profile and all usable summary rows in the previous
365 days. It performs zero match-detail reads and zero replay-parse requests.
The public contract is free-dna-report-5.2.0; an optional infrastructure cap is
recorded explicitly and is not part of the product definition. Current Pattern
pages use the versioned Wrapped + Depth presentation payload; historical 5.0
and 5.1 snapshots remain readable through their legacy renderer.

Pattern qualification is downstream of the 18 Element zones and gates each
selected clause Element by its registry coverage and confidence. Pattern
actions are additive: they can resolve, fall back, or abstain without changing
whether the Pattern qualified. Drift and Recovery use the shared leave-session-
out comparable baseline, and historical 5.0 snapshots retain their original
versions when read.

Hero Portfolio contains Common Thread, Exception, Pool Evolution, and Hero
Mirror. Deep Scan remains an explicit separate mode with its own budgets.

## AI / Coding Agents

Before modifying this repository, read [AGENTS.md](AGENTS.md).

It contains mandatory production, compatibility, testing, and release rules.
Detailed references live in [docs/agent/](docs/agent/).

## Architecture

- [Architecture](ARCHITECTURE.md)
- [Free DNA system](docs/architecture/free-dna-system.md)
- [Elements](docs/architecture/elements.md)
- [Patterns](docs/architecture/patterns.md)
- [Pattern presentation](docs/architecture/pattern-presentation.md)
- [Hero relationships](docs/architecture/hero-relationships.md)
- [Hero matchups and synergies](docs/architecture/hero-matchups-and-synergies.md)
- [Hero Portfolio](docs/architecture/hero-portfolio.md)
- [Report flow](docs/architecture/report-flow.md)
- [Data provenance](docs/architecture/data-provenance.md)
- [Model catalog](docs/architecture/model-catalog.md)
- [Free DNA V6.1 feature graph](docs/architecture/free-dna-v6.1-feature-graph.md)

The archive contains superseded material and is not the active implementation
contract.

The v6 implementation record is
[dota-player-analysis-revision-implementation-plan.md](dota-player-analysis-revision-implementation-plan.md).
Its statistical and Deep contracts are documented in
[v6 statistics](docs/architecture/free-dna-v6-statistics.md) and
[Deep diagnostics v2](docs/architecture/deep-diagnostics-v2.md). Build reviewed
artifacts with `scripts/build_v6_calibration_artifacts.py`; do not place
production artifacts in `tests/fixtures/v6`. The operator workflow is in the
[v6 release and rollback runbook](docs/operations/free-dna-v6-release.md).
The additive V6.1 status, compatibility matrix, and release boundary are in the
[V6.1 feature graph](docs/architecture/free-dna-v6.1-feature-graph.md) and
[V6.1 release gates](docs/qa/free-dna-v6.1-release-gates.md).

## Verification

~~~bash
make lint
make typecheck
make test
make dna-catalog-check
make docs-check
~~~
