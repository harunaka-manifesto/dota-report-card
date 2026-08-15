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

During the experiment phase, player history requests are hard-capped at the latest 50 matches. The cap applies even if `HISTORY_LIMIT` is set higher; expand it only after the larger-history experiment is validated.

## Architecture

- services/api/app/opendota is the only layer that knows OpenDota transport details.
- services/api/app/ingestion filters and normalizes source records while retaining coverage and exclusion reasons.
- services/api/app/features calculates facts without publishing conclusions.
- services/api/app/cohorts selects the narrowest valid comparison or fails closed.
- services/api/app/insights evaluates all 22 registered MVP families, applies gates, ranks evidence, and renders approved templates.
- services/api/app/reports assembles the read-only report.
- apps/web only submits identifiers, polls analysis status, and renders API responses.

The default local repository is in-memory so the full path is runnable without infrastructure. PostgreSQL models and an Alembic migration are included for deployment; Celery task wiring is included behind the same orchestration boundary. No replay parse request is ever submitted.

## Verification

~~~bash
make lint
make typecheck
make test
make test-contract
make test-integration
~~~

make test-live-smoke is opt-in and requires OPENDOTA_API_KEY; it is not part of ordinary CI.
