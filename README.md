# Dota Report Card

The maintained release and reproducibility reference is Free DNA V6.1 on the
OpenDota lineage. Its runtime, persisted reports, artifacts, and release gates
remain explicit and independently versioned; an owner-authorized package is
not the same thing as a production deployment.

Forward development is V7 on the staging line. V7 uses STRATZ-native raw and
normalized data, a new canonical analytical layer, and newly re-derived
Findings. It does not preserve V6/V6.1 estimators merely to make the provider
look interchangeable.

```text
V6.1 / OpenDota reference → persisted reports, rollback, reproducibility
V7 / STRATZ staging       → provider foundation → future analytical rebuild
older generations         → unsupported product targets
```

The retained V5.2-compatible OpenDota path and V6.0 implementation are kept
only where current wiring, persisted compatibility, V6.1 lineage, or unique
evidence still requires them.

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

The V6.0 implementation record is retained as V6.1 lineage evidence. Its
statistical and Deep contracts are documented in
[V6 statistics](docs/architecture/free-dna-v6-statistics.md) and
[Deep diagnostics v2](docs/architecture/deep-diagnostics-v2.md). Build reviewed
artifacts with `scripts/build_v6_calibration_artifacts.py`; do not place
production artifacts in `tests/fixtures/v6`. The operator workflow is in the
[V6 release and rollback runbook](docs/operations/free-dna-v6-release.md). The
V6.1 status, compatibility matrix, and release boundary are in the
[V6.1 feature graph](docs/architecture/free-dna-v6.1-feature-graph.md) and
[V6.1 release gates](docs/qa/free-dna-v6.1-release-gates.md).
The V7 provider boundary is [documented here](docs/architecture/stratz-v7-provider-contract.md),
and analytical agents must read the [learnings and gotchas manual](docs/agent/analytical-learnings-and-gotchas.md).

## Verification

~~~bash
make lint
make typecheck
make test
make test-v7-stratz
make dna-catalog-check
make docs-check
~~~
