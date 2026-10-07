SHELL := /bin/sh
PYTHON ?= uv run python
PYTEST ?= uv run pytest
RUFF ?= uv run ruff
MYPY ?= uv run mypy

.PHONY: install infra-up infra-down db-migrate dev lint typecheck test test-tracker test-integration test-live-smoke docs-check tracker-worker tracker-beat seed-demo tracker-openapi

install:
	uv sync --extra dev

infra-up:
	docker compose -f infra/compose.yaml up -d postgres redis

infra-down:
	docker compose -f infra/compose.yaml down

db-migrate:
	uv run alembic upgrade head

dev:
	uv run uvicorn app.main:app --app-dir services/api --reload --port 8000

lint:
	$(RUFF) check services/api tests scripts

typecheck:
	$(MYPY)

test:
	$(PYTEST) -q

test-tracker:
	@test -n "$(TEST_POSTGRES_URL)" || (echo "TEST_POSTGRES_URL is required (PostgreSQL 16)" && exit 1)
	@test -n "$(TEST_REDIS_URL)" || (echo "TEST_REDIS_URL is required (Redis 7)" && exit 1)
	$(PYTEST) -q tests/tracker

test-integration:
	@test -n "$(TEST_POSTGRES_URL)" || (echo "TEST_POSTGRES_URL is required (PostgreSQL 16)" && exit 1)
	RUN_POSTGRES_MIGRATION_TEST=1 $(PYTEST) -q tests/integration

test-live-smoke:
	@test -n "$(OPENDOTA_API_KEY)" || (echo "OPENDOTA_API_KEY is required" && exit 1)
	@RUN_LIVE_SMOKE=1 $(PYTEST) -q tests/live -m live

docs-check:
	$(PYTHON) scripts/check_docs.py

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
