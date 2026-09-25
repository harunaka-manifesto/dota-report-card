# Dota Tracker

Backend for **Dota Tracker**, a native iOS app. The backend acquires match data from OpenDota
and STRATZ, stores it once per match, analyses it, and serves a mobile API — it never lets the
client call a provider directly. See [`docs/tracker/README.md`](docs/tracker/README.md) for
product meaning, [`docs/tracker/architecture/README.md`](docs/tracker/architecture/README.md)
for system behaviour, and [`docs/tracker/architecture/IMPLEMENTATION-LEDGER.md`](docs/tracker/architecture/IMPLEMENTATION-LEDGER.md)
for what is implemented, verified, and still open. The backend runs locally against PostgreSQL
and Redis; it is not deployed.

## Quickstart

```bash
cp .env.example .env
make install
make infra-up            # docker compose: postgres + redis
make db-migrate           # alembic upgrade head
make dev                  # FastAPI: legacy /v1, /mobile/v1, /store, /internal/tracker
TEST_POSTGRES_URL=… TEST_REDIS_URL=… make test-tracker
make tracker-worker PRIORITY=0   # one terminal per priority: 0, 1, 2, 3
make tracker-beat
DATABASE_URL=… make seed-demo    # fixture-backed personas with bearer tokens
make tracker-openapi              # export the /mobile/v1 OpenAPI document
```

Full setup, verification commands, and what each test suite proves are in the
[tracker runbook](docs/tracker/operations/README.md).

## Where to go next

- [Product documentation (feature SSOTs)](docs/tracker/README.md)
- [Architecture and ADRs](docs/tracker/architecture/README.md)
- [Operations runbook](docs/tracker/operations/README.md)
- [Mobile API](docs/tracker/api/README.md)
- [Implementation ledger](docs/tracker/architecture/IMPLEMENTATION-LEDGER.md)

## AI / coding agents

Read [`AGENTS.md`](AGENTS.md) before making changes.

## Legacy report card

This repository also hosts the deprecated but **live-in-production** Dota Report Card / Free
DNA product, entirely under [`legacy/`](legacy/README.md). It is not the tracker's product or
architecture reference — see [`legacy/README.md`](legacy/README.md) and
[`legacy/AGENTS.md`](legacy/AGENTS.md) before touching it.
