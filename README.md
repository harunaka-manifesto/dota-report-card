# Dota Report Card

An anonymous OpenDota player report that separates raw payloads, normalized facts, reusable features, cohort comparisons, and deterministic evidence-backed narratives.

## Local start

~~~bash
cp .env.example .env
make install
make test
make dev
~~~

The default .env.example source is the sanitized fixture adapter. Set OPENDOTA_SOURCE=live and provide OPENDOTA_API_KEY only for a live run. The key is sent in an Authorization Bearer header by the server and is never accepted from the browser.

The recorded example account is 193875165. Open http://localhost:8000/docs for the API or run the web app with pnpm --dir apps/web dev.

## Deployment

The Next.js web app and FastAPI analysis service are separate deployments. On
the Vercel web project, set `API_BASE_URL` to the public HTTPS origin of the
deployed FastAPI service (for example, `https://api.example.com`). Browser calls
use the web app's same-origin `/v1` proxy; do not expose the OpenDota key through
a `NEXT_PUBLIC_` variable.

On the API deployment, set `OPENDOTA_SOURCE=live` and `OPENDOTA_API_KEY`. The API
also needs its production persistence/execution dependencies (`DATABASE_URL`
and `REDIS_URL`) when `APP_ENV=production`. Adding only `OPENDOTA_API_KEY` to the
Vercel web project does not deploy or configure the FastAPI service.

Player DNA reads up to 200 cheap summary rows by default. Deep Scan has separate configurable ceilings (`MAX_DEEP_MATCHES`, `MAX_PARSE_REQUESTS`, and `MAX_DATA_COST_PER_REPORT`) and never hydrates every history row. The default parse budget is zero; parsing remains an explicit capability behind the budget boundary.

For the expected-behavior contract used by bug-busting agents, see [the system behavior baseline](docs/system-behavior-baseline.md).

## Architecture

- services/api/app/opendota is the only layer that knows OpenDota transport details.
- services/api/app/ingestion filters and normalizes source records while retaining coverage and exclusion reasons.
- services/api/app/features calculates facts without publishing conclusions.
- services/api/app/cohorts selects the narrowest valid comparison or fails closed.
- services/api/app/patterns detects summary-only Player DNA observations and app/hypotheses maps them to deterministic explanations.
- services/api/app/selection globally deduplicates diagnostic match candidates using marginal information gain and cost.
- services/api/app/insights evaluates the existing rich families, applies gates, ranks evidence, and renders approved templates.
- services/api/app/reports assembles the read-only report.
- apps/web only submits identifiers, polls analysis status, and renders API responses.

The default local repository is in-memory so the full path is runnable without infrastructure. PostgreSQL models and Alembic migrations are included for deployment; Celery task wiring is included behind the same orchestration boundary. Free analysis submits no replay parse request and performs no individual-match reads.

## Verification

~~~bash
make lint
make typecheck
make test
make test-contract
make test-integration
~~~

make test-live-smoke is opt-in and requires OPENDOTA_API_KEY; it is not part of ordinary CI.
