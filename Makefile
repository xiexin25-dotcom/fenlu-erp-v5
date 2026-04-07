.PHONY: help install up down logs migrate dev test lint fmt typecheck clean worktree-init

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python deps via uv
	uv sync --all-extras

up:  ## Start postgres + redis + minio
	docker compose up -d postgres redis minio
	@sleep 2
	@docker compose ps

down:  ## Stop all containers
	docker compose down

logs:  ## Tail container logs
	docker compose logs -f

init-db:  ## Create the 4 lane schemas
	docker compose exec -T postgres psql -U fenlu -d fenlu_v5 < infra/init.sql

migrate:  ## Apply alembic migrations
	uv run alembic -c infra/alembic.ini upgrade head

migration:  ## Generate a new migration: make migration name="add_widget"
	uv run alembic -c infra/alembic.ini revision --autogenerate -m "$(name)"

dev:  ## Run api-gateway with auto-reload (port 8000)
	uv run uvicorn apps.api_gateway.main:app --reload --port 8000

dev-plm:  ## Run Lane 1 worktree on port 8001
	uv run uvicorn apps.api_gateway.main:app --reload --port 8001

dev-mfg:  ## Run Lane 2 worktree on port 8002
	uv run uvicorn apps.api_gateway.main:app --reload --port 8002

dev-scm:  ## Run Lane 3 worktree on port 8003
	uv run uvicorn apps.api_gateway.main:app --reload --port 8003

dev-mgmt:  ## Run Lane 4 worktree on port 8004
	uv run uvicorn apps.api_gateway.main:app --reload --port 8004

test:  ## Run pytest
	uv run pytest -v

test-cov:  ## Run pytest with coverage
	uv run pytest --cov=packages --cov=apps --cov-report=term --cov-report=html

lint:  ## Run ruff check
	uv run ruff check .

fmt:  ## Auto-format with ruff
	uv run ruff format .
	uv run ruff check --fix .

typecheck:  ## Run mypy strict
	uv run mypy packages apps

check: lint typecheck test  ## Run all checks (CI parity)

clean:  ## Remove caches
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .mypy_cache -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .ruff_cache -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage

worktree-init:  ## Create the 4 lane worktrees
	@echo "Creating 4 lane worktrees as siblings of this directory..."
	git worktree add ../fenlu-v5-product       -b feat/product-lifecycle    main
	git worktree add ../fenlu-v5-production    -b feat/production           main
	git worktree add ../fenlu-v5-supply-chain  -b feat/supply-chain         main
	git worktree add ../fenlu-v5-management    -b feat/management-decision  main
	@echo "✓ done. cd into each and run 'claude code .'"
