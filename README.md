# Dota Report Card

An anonymous OpenDota player report that turns one bounded summary-history read
into observable Dota patterns with receipts. The current Free report is layered:

`summary observations → 23 Elements → finite Patterns → three context Archetypes → editorial Findings → story`

The copy is deliberately specific about what the data can support. Summary
history can describe recurring match behavior. It cannot prove a motive, a
psychological state, or a replay-level cause.

## Local start

```bash
cp .env.example .env
make install
make test
make dev
```

The default `.env.example` source is the sanitized fixture adapter. Set
`OPENDOTA_SOURCE=live` and provide `OPENDOTA_API_KEY` only for a live run. The
key is sent in an Authorization Bearer header by the server and is never
accepted from the browser.

The recorded example account is `193875165`. Open
`http://localhost:8000/docs` for the API, or run the web app with
`pnpm --dir apps/web dev`.

## Free and Deep Scan

Free mode reads the public profile plus one bounded history window of up to 500
summary rows. It performs zero match-detail reads and zero replay-parse
requests. Missing fields remain missing, and every report carries the cost and
quality metadata for the run.

Deep Scan is an explicit, separate mode. It may inspect selected match details
under its configured budgets; it does not turn Free’s summary observations into
causal claims by default.

New Free analyses publish the strict `free-dna-report-3.0.0` contract. Existing
v1/v2 snapshots remain readable. The API client and web route select the story
renderer by schema version.

## Architecture

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — short system map and invariants.
- [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md) — pipeline ownership, evidence rules, and compatibility.
- [`docs/architecture/free-dna-model-guide.md`](docs/architecture/free-dna-model-guide.md) — the complete human-readable explanation of every active Element, Pattern, and context Archetype.
- [`docs/architecture/model-catalog.md`](docs/architecture/model-catalog.md) — generated registry catalog for the active Free model.
- [`docs/evidence-contract.md`](docs/evidence-contract.md) — evidence and provenance requirements.
- [`docs/opendota-data-inventory.md`](docs/opendota-data-inventory.md) — source fields and their limits.
- [`tone_of_voice.md`](tone_of_voice.md) — user-facing copy rules.

## Verification

```bash
make lint
make typecheck
make test
make test-contract
make test-integration
make dna-catalog-check
make docs-check
```

`make test-live-smoke` is opt-in and requires `OPENDOTA_API_KEY`; it is not part
of ordinary CI.

## Deployment

The Next.js web app and FastAPI analysis service are separate deployments. On
the Vercel web project, set `API_BASE_URL` to the public HTTPS origin of the
FastAPI service. Browser calls use the web app’s same-origin `/v1` proxy; do not
expose the OpenDota key through a `NEXT_PUBLIC_` variable.

On the API deployment, set `OPENDOTA_SOURCE=live` and `OPENDOTA_API_KEY`. The
API also needs its production persistence/execution dependencies
(`DATABASE_URL` and `REDIS_URL`) when `APP_ENV=production`.
