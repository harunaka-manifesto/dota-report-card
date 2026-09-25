# Dota Tracker and the live legacy Report Card

The maintained release and reproducibility reference is Free DNA V6.1 on the
OpenDota lineage. Its runtime, persisted reports, artifacts, and release gates
remain explicit and independently versioned; an owner-authorized package is
not the same thing as a production deployment.

Current development targets the native iOS **Dota Tracker**. Start with its
[product documentation](docs/tracker/README.md),
[architecture](docs/tracker/architecture/README.md), and
[implementation ledger](docs/tracker/architecture/IMPLEMENTATION-LEDGER.md).
The tracker backend (`services/api/app/tracker/`, mobile API at `/mobile/v1`) is implemented
and verified locally against PostgreSQL and Redis but not deployed; the ledger records what is
verified, what remains open for owner decisions, and the external blockers. To run and test it,
see the [tracker runbook](docs/tracker/operations/README.md).

## Live legacy report product

The following describes the retained report-card implementation. It is not
the product or provider contract for the tracker. V7 is an older staging
lineage; it does not define the tracker’s system behavior.

```text
V6.1 / OpenDota reference → persisted reports, rollback, reproducibility
V7 / STRATZ staging       → retained runtime and research evidence
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
Detailed references live in [legacy/docs/agent/](legacy/docs/agent/).

## Architecture

- [Architecture](ARCHITECTURE.md)
- [Free DNA system](legacy/docs/architecture/free-dna-system.md)
- [Elements](legacy/docs/architecture/elements.md)
- [Patterns](legacy/docs/architecture/patterns.md)
- [Pattern presentation](legacy/docs/architecture/pattern-presentation.md)
- [Hero relationships](legacy/docs/architecture/hero-relationships.md)
- [Hero matchups and synergies](legacy/docs/architecture/hero-matchups-and-synergies.md)
- [Hero Portfolio](legacy/docs/architecture/hero-portfolio.md)
- [Report flow](legacy/docs/architecture/report-flow.md)
- [Data provenance](legacy/docs/architecture/data-provenance.md)
- [Model catalog](legacy/docs/architecture/model-catalog.md)
- [Free DNA V6.1 feature graph](legacy/docs/architecture/free-dna-v6.1-feature-graph.md)

The archive contains superseded material and is not the active implementation
contract.

The V6.0 implementation record is retained as V6.1 lineage evidence. Its
statistical and Deep contracts are documented in
[V6 statistics](legacy/docs/architecture/free-dna-v6-statistics.md) and
[Deep diagnostics v2](legacy/docs/architecture/deep-diagnostics-v2.md). Build reviewed
artifacts with `scripts/build_v6_calibration_artifacts.py`; do not place
production artifacts in `tests/fixtures/v6`. The operator workflow is in the
[V6 release and rollback runbook](legacy/docs/operations/free-dna-v6-release.md). The
V6.1 status, compatibility matrix, and release boundary are in the
[V6.1 feature graph](legacy/docs/architecture/free-dna-v6.1-feature-graph.md) and
[V6.1 release gates](legacy/docs/qa/free-dna-v6.1-release-gates.md).
The V7 provider boundary is [documented here](legacy/docs/architecture/stratz-v7-provider-contract.md),
and analytical agents must read the [learnings and gotchas manual](legacy/docs/agent/analytical-learnings-and-gotchas.md).

## Verification

~~~bash
make lint
make typecheck
make test
make test-v7-stratz
make dna-catalog-check
make docs-check
~~~
