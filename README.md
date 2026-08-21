# Dota Report Card

An anonymous OpenDota player report built from one bounded summary-history read.

summary history → 18 Elements → 11 Patterns → Hero Portfolio → interactive story → Hero Mirror → share

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
The public contract is free-dna-report-5.0.0; an optional infrastructure cap is
recorded explicitly and is not part of the product definition.

Hero Portfolio contains Common Thread, Exception, Pool Evolution, and Hero
Mirror. Deep Scan remains an explicit separate mode with its own budgets.

## Architecture

- [Architecture](ARCHITECTURE.md)
- [Free DNA system](docs/architecture/free-dna-system.md)
- [Elements](docs/architecture/elements.md)
- [Patterns](docs/architecture/patterns.md)
- [Hero relationships](docs/architecture/hero-relationships.md)
- [Hero matchups and synergies](docs/architecture/hero-matchups-and-synergies.md)
- [Hero Portfolio](docs/architecture/hero-portfolio.md)
- [Report flow](docs/architecture/report-flow.md)
- [Data provenance](docs/architecture/data-provenance.md)
- [Model catalog](docs/architecture/model-catalog.md)

The archive contains superseded material and is not the active implementation
contract.

## Verification

~~~bash
make lint
make typecheck
make test
make dna-catalog-check
make docs-check
~~~
