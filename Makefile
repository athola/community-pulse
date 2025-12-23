# Makefile for FastAPI backend + React Native frontend + PostgreSQL
# Python environment is managed by uv; targets assume uv is installed locally.
SHELL := /bin/bash
.SHELLFLAGS := -e -u -o pipefail -c

UV?=uv
PY_SRC := src tests
APP_MODULE := community_pulse.api.app:app
MOBILE_DIR?=frontend
NPM?=npm
PRE_COMMIT_HOME?=$(CURDIR)/.cache/pre-commit
VIRTUALENV_APP_DATA?=$(PRE_COMMIT_HOME)/virtualenv

.PHONY: help uv-sync install-frontend lint format typecheck test check demo demo-api demo-mobile demo-db demo-down hooks hooks-clean build clean
.PHONY: unit-test integration-test coverage quick-check seed fetch-data docker-build docker-run ci
.DELETE_ON_ERROR:

help:
	@printf "Available targets:\n"
	@printf "  uv-sync          Install deps (including dev) via uv sync --all-groups\n"
	@printf "  install-frontend Install React Native deps in $(MOBILE_DIR) via npm\n"
	@printf "  lint             Run ruff check across Python sources\n"
	@printf "  format           Apply ruff format\n"
	@printf "  typecheck        Run ty and mypy on Python sources\n"
	@printf "  test             Run pytest suite\n"
	@printf "  check            Run lint, typecheck, and test\n"
	@printf "  demo             Launch API + frontend on localhost (requires two terminals)\n"
	@printf "  demo-db          Start PostgreSQL via docker compose\n"
	@printf "  demo-api         Launch FastAPI app with uvicorn\n"
	@printf "  demo-mobile      Start React Native dev server\n"
	@printf "  demo-down        Stop all containers and remove volumes\n"
	@printf "  build            Build sdist/wheel with uv\n"
	@printf "  hooks            Install git hooks via pre-commit (cached locally)\n"
	@printf "  hooks-clean      Remove pre-commit hooks\n"
	@printf "  clean            Remove caches, .venv, and coverage files\n"
	@printf "\n  --- Quick Targets ---\n"
	@printf "  quick-check      Fast lint-only check for rapid iteration\n"
	@printf "  unit-test        Run only unit tests (skips integration/slow)\n"
	@printf "  integration-test Run only integration tests\n"
	@printf "  coverage         Open HTML coverage report in browser\n"
	@printf "\n  --- Data & Docker ---\n"
	@printf "  fetch-data       Fetch latest HN data to data/ directory\n"
	@printf "  seed             Seed database with fetched HN data\n"
	@printf "  docker-build     Build Docker image for deployment\n"
	@printf "  docker-run       Run app in Docker container\n"
	@printf "\n  --- CI ---\n"
	@printf "  ci               Full CI pipeline (format check + check)\n"

uv-sync:
	$(UV) sync --all-groups

install-frontend:
	@if [ -d "$(MOBILE_DIR)" ]; then \
		cd "$(MOBILE_DIR)" && $(NPM) install --silent; \
	else \
		echo "No $(MOBILE_DIR) directory found; skipping"; \
	fi

lint:
	$(UV) run ruff check $(PY_SRC)

format:
	$(UV) run ruff format $(PY_SRC)

typecheck:
	$(UV) run ty check .
	$(UV) run mypy $(PY_SRC)

test:
	$(UV) run pytest

check: lint typecheck test

demo:
	@echo "Starting Community Pulse demo..."
	@echo ""
	@echo "Run these commands in separate terminals:"
	@echo "  Terminal 1: make demo-api    # Starts backend at http://localhost:8001"
	@echo "  Terminal 2: make demo-mobile # Starts frontend at http://localhost:8081"
	@echo ""
	@echo "Then open http://localhost:8081 in your browser."
	@echo ""
	@echo "API docs available at http://localhost:8001/docs"

demo-db:
	docker compose up -d db

demo-down:
	@# Kill API server on port 8001 if running
	-@lsof -ti :8001 | xargs -r kill 2>/dev/null || true
	docker compose down -v

# Demo targets are blocking; run in separate shells/tmux panes.
demo-api:
	$(UV) run uvicorn $(APP_MODULE) --reload --host 0.0.0.0 --port 8001

demo-mobile:
	@if [ -d "$(MOBILE_DIR)" ]; then \
		cd "$(MOBILE_DIR)" && $(NPM) start; \
	else \
		echo "No $(MOBILE_DIR) directory found; skipping"; \
	fi

hooks:
	@mkdir -p "$(PRE_COMMIT_HOME)"
	PRE_COMMIT_HOME="$(PRE_COMMIT_HOME)" VIRTUALENV_APP_DATA="$(VIRTUALENV_APP_DATA)" $(UV) run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

hooks-clean:
	@mkdir -p "$(PRE_COMMIT_HOME)"
	PRE_COMMIT_HOME="$(PRE_COMMIT_HOME)" VIRTUALENV_APP_DATA="$(VIRTUALENV_APP_DATA)" $(UV) run pre-commit uninstall

build:
	$(UV) build

clean:
	-rm -rf .venv .mypy_cache .pytest_cache .ruff_cache htmlcov coverage.xml

# ─────────────────────────────────────────────────────────────────────────────
# Quick targets for rapid development iteration
# ─────────────────────────────────────────────────────────────────────────────

quick-check: lint
	@echo "Quick check passed (lint only)"

unit-test:
	$(UV) run pytest -m "unit and not slow and not integration" --tb=short

integration-test:
	$(UV) run pytest -m "integration" --tb=short

coverage:
	@if [ -d htmlcov ]; then \
		xdg-open htmlcov/index.html 2>/dev/null || open htmlcov/index.html 2>/dev/null || echo "Open htmlcov/index.html in browser"; \
	else \
		echo "No coverage report found. Run 'make test' first."; \
	fi

# ─────────────────────────────────────────────────────────────────────────────
# Data and Docker targets
# ─────────────────────────────────────────────────────────────────────────────

fetch-data:
	$(UV) run python scripts/fetch_hn_data.py

seed: demo-db
	@echo "Waiting for database to be ready..."
	@sleep 3
	$(UV) run python scripts/seed_db.py

docker-build:
	docker build -t community-pulse:latest .

docker-run: docker-build
	docker run --rm -p 8001:8001 --env-file .env community-pulse:latest

# ─────────────────────────────────────────────────────────────────────────────
# CI target - mirrors what runs in GitHub Actions
# ─────────────────────────────────────────────────────────────────────────────

ci:
	@echo "Running CI pipeline..."
	$(UV) run ruff format --check $(PY_SRC)
	$(MAKE) check
	@echo "CI pipeline passed!"
