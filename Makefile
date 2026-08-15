SHELL := /bin/sh
PYTHON ?= uv run python
PYTEST ?= uv run pytest
RUFF ?= uv run ruff
MYPY ?= uv run mypy
PNPM ?= pnpm
WEB_BIN ?= apps/web/node_modules/.bin

.PHONY: install infra-up infra-down db-migrate dev lint typecheck test test-contract test-integration test-e2e test-live-smoke api-client

install:
	uv sync --extra dev
	$(PNPM) --dir apps/web install --ignore-scripts --frozen-lockfile=false

infra-up:
	docker compose -f infra/compose.yaml up -d postgres redis

infra-down:
	docker compose -f infra/compose.yaml down

db-migrate:
	uv run alembic upgrade head

dev:
	uv run uvicorn app.main:app --app-dir services/api --reload --port 8000

lint:
	$(RUFF) check services/api tests
	cd apps/web && ./node_modules/.bin/next lint

typecheck:
	$(MYPY)
	cd apps/web && ./node_modules/.bin/tsc --noEmit

test:
	$(PYTEST) -q

test-contract:
	$(PYTEST) -q tests/contract

test-integration:
	$(PYTEST) -q tests/integration

test-e2e:
	cd apps/web && ./node_modules/.bin/playwright test

test-live-smoke:
	@test -n "$(OPENDOTA_API_KEY)" || (echo "OPENDOTA_API_KEY is required" && exit 1)
	RUN_LIVE_SMOKE=1 OPENDOTA_SOURCE=live OPENDOTA_API_KEY="$(OPENDOTA_API_KEY)" $(PYTEST) -q tests/live -m live

api-client:
	$(PYTHON) scripts/generate_api_client.py
