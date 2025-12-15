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

.PHONY: help uv-sync install-frontend lint format typecheck test check demo demo-api demo-mobile demo-db hooks hooks-clean build clean
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
	@printf "  build            Build sdist/wheel with uv\n"
	@printf "  hooks            Install git hooks via pre-commit (cached locally)\n"
	@printf "  hooks-clean      Remove pre-commit hooks\n"
	@printf "  clean            Remove caches, .venv, and coverage files\n"

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
	@echo "  Terminal 1: make demo-api    # Starts backend at http://localhost:8000"
	@echo "  Terminal 2: make demo-mobile # Starts frontend at http://localhost:8081"
	@echo ""
	@echo "Then open http://localhost:8081 in your browser."
	@echo ""
	@echo "API docs available at http://localhost:8000/docs"

demo-db:
	docker compose up -d db

# Demo targets are blocking; run in separate shells/tmux panes.
demo-api:
	$(UV) run uvicorn $(APP_MODULE) --reload --host 0.0.0.0 --port 8000

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
