SHELL := /bin/sh
PYTHON ?= uv run python
PYTEST ?= uv run pytest
RUFF ?= uv run ruff
MYPY ?= uv run mypy
PNPM ?= pnpm
WEB_BIN ?= legacy/apps/web/node_modules/.bin

.PHONY: seed-demo tracker-openapi install infra-up infra-down db-migrate dev lint typecheck test test-tracker test-v7-stratz test-contract test-integration test-e2e test-live-smoke api-client taxonomy-validate dna-catalog dna-catalog-check copy-review-catalog copy-review-catalog-check docs-check hero-knowledge-refresh

install:
	uv sync --extra dev
	$(PNPM) --dir legacy/apps/web install --ignore-scripts --frozen-lockfile=false

infra-up:
	docker compose -f infra/compose.yaml up -d postgres redis

infra-down:
	docker compose -f infra/compose.yaml down

db-migrate:
	uv run alembic upgrade head

dev:
	PYTHONPATH=legacy/services/api:$$PYTHONPATH uv run uvicorn app.main:app --app-dir services/api --reload --port 8000

lint:
	$(RUFF) check services/api legacy/services/api tests legacy/tests scripts legacy/scripts
	cd legacy/apps/web && ./node_modules/.bin/next lint

typecheck:
	$(MYPY)
	cd legacy/apps/web && ./node_modules/.bin/tsc --noEmit

test:
	$(PYTEST) -q

test-tracker:
	@test -n "$(TEST_POSTGRES_URL)" || (echo "TEST_POSTGRES_URL is required (PostgreSQL 16)" && exit 1)
	@test -n "$(TEST_REDIS_URL)" || (echo "TEST_REDIS_URL is required (Redis 7)" && exit 1)
	$(PYTEST) -q tests/tracker

test-v7-stratz:
	$(PYTEST) -q tests/unit/test_stratz_client.py legacy/tests/unit/test_stratz_normalize.py legacy/tests/unit/test_v7_provider_architecture.py

test-contract:
	$(PYTEST) -q legacy/tests/contract

test-integration:
	$(PYTEST) -q tests/integration legacy/tests/integration

test-e2e:
	cd legacy/apps/web && ./node_modules/.bin/playwright test

test-live-smoke:
	@test -n "$(OPENDOTA_API_KEY)" || (echo "OPENDOTA_API_KEY is required" && exit 1)
	@RUN_LIVE_SMOKE=1 OPENDOTA_SOURCE=live $(PYTEST) -q tests/live -m live

api-client:
	$(PYTHON) legacy/scripts/generate_api_client.py

taxonomy-validate:
	$(PYTHON) legacy/scripts/validate_hero_taxonomy.py

dna-catalog:
	$(PYTHON) legacy/scripts/generate_dna_model_catalog.py

dna-catalog-check:
	$(PYTHON) legacy/scripts/generate_dna_model_catalog.py --check

copy-review-catalog:
	$(PYTHON) legacy/scripts/generate_copy_review_catalog.py

copy-review-catalog-check:
	$(PYTHON) legacy/scripts/generate_copy_review_catalog.py --check

docs-check:
	$(PYTHON) scripts/check_docs.py
	$(PYTHON) legacy/scripts/check_legacy_docs.py

hero-knowledge-refresh:
	$(PYTHON) -m legacy.scripts.hero_knowledge.cli refresh --force-refresh

# Run each priority in its own terminal/process. Never combine P0/P1 with P3.
tracker-worker:
	@test "$(PRIORITY)" = 0 -o "$(PRIORITY)" = 1 -o "$(PRIORITY)" = 2 -o "$(PRIORITY)" = 3 || (echo "PRIORITY must be 0, 1, 2 or 3" && exit 1)
	uv run celery -A app.tracker.worker:celery_app worker -Q tracker-p$(PRIORITY) -n tracker-p$(PRIORITY)@%h --concurrency=1 --loglevel=INFO

tracker-beat:
	uv run celery -A app.tracker.worker:celery_app beat --loglevel=INFO

# Fixture-backed local personas for every mobile state; no provider calls.
seed-demo:
	@test -n "$(DATABASE_URL)" || (echo "DATABASE_URL must point at a migrated local PostgreSQL database" && exit 1)
	$(PYTHON) -m scripts.tracker_seed_demo

# Re-export the isolated mobile OpenAPI document after a reviewed contract change.
tracker-openapi:
	$(PYTHON) -m scripts.tracker_export_openapi
