# DocExtract AI — developer commands
#
# Usage: make <target>   (run `make help` to list targets)

COMPOSE_FILE := docker/docker-compose.yml

.DEFAULT_GOAL := help

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

.PHONY: help
help: ## Show this help
    @grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
        | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: init
init: ## Create the project folder structure (scripts/init_project.sh)
    bash scripts/init_project.sh

.PHONY: install
install: ## Install all dependencies (Python)
    cd apps/api && pip install -e ".[dev]"
    # Web install activates in Phase 9
    # cd apps/web && npm install

# ------------------------------------------------------------------
# Development
# ------------------------------------------------------------------

.PHONY: dev-api
dev-api: ## Start the FastAPI dev server (http://localhost:8000)
    cd apps/api && uvicorn app.main:app --reload

.PHONY: dev-web
dev-web: ## Start the Next.js dev server (http://localhost:3000)
    cd apps/web && npm run dev

.PHONY: dev-docker
dev-docker: ## Start all Docker services (Local Docker Mode)
    docker compose -f $(COMPOSE_FILE) up --build

# ------------------------------------------------------------------
# Quality
# ------------------------------------------------------------------

.PHONY: lint
lint: ## Run ruff check + eslint
    cd apps/api && ruff check .
    cd apps/web && npm run lint

.PHONY: format
format: ## Run ruff format + prettier
    cd apps/api && ruff format .
    cd apps/web && npx prettier --write .

.PHONY: typecheck
typecheck: ## Run mypy + tsc --noEmit
    cd apps/api && mypy .
    cd apps/web && npx tsc --noEmit

.PHONY: test
test: ## Run pytest + vitest
    cd apps/api && pytest
    cd apps/web && npm run test

.PHONY: test-e2e
test-e2e: ## Run Playwright tests
    cd apps/web && npx playwright test

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------

.PHONY: migrate
migrate: ## Run alembic upgrade head
    cd apps/api && alembic upgrade head

.PHONY: migration
migration: ## Create a new alembic migration (name=...)
    cd apps/api && alembic revision --autogenerate -m "$(name)"

.PHONY: seed
seed: ## Run the seed script
    cd apps/api && python -m app.db.seed

# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------

.PHONY: seed-demo
seed-demo: ## Seed demo data (accounts + sample documents)
    cd apps/api && python -m app.db.seed --demo

.PHONY: reset-demo
reset-demo: ## Reset demo data (delete documents, re-seed)
    cd apps/api && python -m app.db.seed --reset-demo

# ------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------

.PHONY: docker-up
docker-up: ## docker compose up --build
    docker compose -f $(COMPOSE_FILE) up --build

.PHONY: docker-down
docker-down: ## docker compose down
    docker compose -f $(COMPOSE_FILE) down

.PHONY: docker-clean
docker-clean: ## docker compose down -v (also deletes volumes and data)
    docker compose -f $(COMPOSE_FILE) down -v