# Imo Ijinle Academy LMS — root developer commands
# On Windows without make, use: pwsh -File scripts/dev.ps1

COMPOSE := docker compose -f infra/docker-compose.yml
INFRA_SERVICES := postgres redis minio mailpit
BACKEND_DIR := backend
FRONTEND_DIR := frontend
API_URL ?= http://127.0.0.1:8000
OPENAPI_PATH ?= $(API_URL)/api/schema/
OPENAPI_OUT := $(FRONTEND_DIR)/openapi/schema.json
OPENAPI_TYPES := $(FRONTEND_DIR)/src/lib/api/schema.d.ts

.PHONY: dev down migrate seed test lint typecheck gen-api e2e bootstrap minio-init

dev: minio-init
	$(COMPOSE) up -d $(INFRA_SERVICES)

minio-init:
	$(COMPOSE) up -d minio
	$(COMPOSE) run --rm minio-init

down:
	$(COMPOSE) down

migrate:
	cd $(BACKEND_DIR) && uv run python manage.py migrate

seed:
	cd $(BACKEND_DIR) && uv run python manage.py seed_demo

test: test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && uv run pytest -q

test-frontend:
	cd $(FRONTEND_DIR) && pnpm test -- --run

lint: lint-backend lint-frontend

lint-backend:
	cd $(BACKEND_DIR) && uv run ruff check . && uv run ruff format --check .

lint-frontend:
	cd $(FRONTEND_DIR) && pnpm lint

typecheck:
	cd $(FRONTEND_DIR) && pnpm typecheck
	cd $(BACKEND_DIR) && uv run mypy .

gen-api:
	@mkdir -p $(FRONTEND_DIR)/openapi $(FRONTEND_DIR)/src/lib/api
	curl -sf "$(OPENAPI_PATH)" -o $(OPENAPI_OUT)
	cd $(FRONTEND_DIR) && pnpm exec openapi-typescript openapi/schema.json -o src/lib/api/schema.d.ts

e2e:
	cd $(FRONTEND_DIR) && pnpm exec playwright test

bootstrap: dev migrate seed
	@echo "Infra is up; run backend and frontend dev servers locally (see README.md)."
