# Dota Report Card

An anonymous OpenDota player report built from one bounded summary-history read.

summary history → 17 Elements → 14 Patterns → Hero Portfolio → interactive story → Hero Mirror → share

Free DNA describes observable match behavior. It does not infer motives,
psychological states, grades, or replay-level causes.

## Local start

~~~bash
cp .env.example .env
make install
make test
make dev
~~~

Free mode reads the public profile and one bounded history window of up to 500
summary rows. It performs zero match-detail reads and zero replay-parse
requests. The public contract is free-dna-report-4.0.0.

Hero Portfolio contains Common Thread, Exception, Pool Evolution, and Hero
Mirror. Deep Scan remains an explicit separate mode with its own budgets.

## Architecture

- [Architecture](ARCHITECTURE.md)
- [Free DNA system](docs/architecture/free-dna-system.md)
- [Elements](docs/architecture/elements.md)
- [Patterns](docs/architecture/patterns.md)
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
