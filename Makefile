# Makefile for QA Intelligence project (venv-aware)
.PHONY: help install install-dev test lint format type-check security clean build docs run

# Virtualenv tooling
VENV_DIR := .venv
PY := $(VENV_DIR)/bin/python
PIP := $(PY) -m pip
PYTEST := $(PY) -m pytest
RUFF := $(PY) -m ruff
PYLINT := $(PY) -m pylint
BLACK := $(PY) -m black
ISORT := $(PY) -m isort
MYPY := $(PY) -m mypy
BANDIT := $(PY) -m bandit
SAFETY := $(PY) -m safety
MKDOCS := $(PY) -m mkdocs
BUILD := $(PY) -m build
TWINE := $(PY) -m twine
PRECOMMIT := $(PY) -m pre_commit

# Default target
help:
	@echo "QA Intelligence - Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  setup-hooks   Setup pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  test         Run tests with coverage"
	@echo "  test-fast    Run tests without coverage"
	@echo "  lint         Run linting (pylint + ruff)"
	@echo "  format       Format code (black + isort)"
	@echo "  type-check   Run type checking (mypy)"
	@echo "  security     Run security checks (bandit)"
	@echo "  qa-check     Run all quality checks"
	@echo ""
	@echo "Project:"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  docs         Build documentation"
	@echo "  run          Run QA agent (use ARGS=\"--flags\")"
	@echo "  run-teams    Run QA teams demo"
	@echo "  run-metrics  Run Prometheus exporter (port 9400)"
	@echo "  run-server   Run WebSocket server + Prometheus"
	@echo "  run-stack    Run complete stack (Agent + WebSocket + Prometheus)"
	@echo ""
	@echo "Database Migration:"
	@echo "  migrate-to-supabase  Run complete Supabase migration"
	@echo "  demo-supabase        Demo migration readiness and flow"
	@echo "  check-supabase       Check Supabase configuration"
	@echo "  init-supabase-db     Initialize database tables"
	@echo "  test-supabase        Test database connection"
	@echo ""

# Installation
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e '.[dev]'

setup-hooks:
	$(PRECOMMIT) install
	$(PRECOMMIT) install --hook-type commit-msg

# Testing
test:
	$(PYTEST) --cov=src --cov=config --cov-report=html --cov-report=term-missing

test-fast:
	$(PYTEST) -x --no-cov

test-integration:
	$(PYTEST) -m integration

test-unit:
	$(PYTEST) -m unit

# Code quality
lint:
	$(PYLINT) src/ scripts/ config
	$(RUFF) check src/ scripts/ config

format:
	$(BLACK) src/ scripts/ config
	$(ISORT) src/ scripts/ config

# QA Agent specific validation
## consolidated below

validate-improvements:
	@echo "🔍 Validating code quality improvements..."
	python scripts/validate_improvements.py

show-improvements:
	@echo "📊 Showing improvement summary..."
	python scripts/improvement_summary.py

lint-qa-agent:
	@echo "🔍 Linting QA Agent specifically..."
	python -m pylint src/agent/qa_agent.py --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,too-few-public-methods,import-error

# Logging & Monitoring
test-logging:
	@echo "🧪 Testing Loguru logging system..."
	python src/logging_config.py

test-qa-logging:
	@echo "🧪 Testing QA Agent with Loguru..."
	python -c "from src.agent.qa_agent import QAAgent; agent = QAAgent(); print('✅ QA Agent with Loguru working!')"

demo-logging:
	@echo "🎭 Running comprehensive logging demonstration..."
	python scripts/logging_demo.py

show-loguru-summary: ## Show comprehensive Loguru implementation summary
	@echo "🔧 Loguru Implementation Summary"
	@echo "================================"
	@python scripts/loguru_summary.py

show-instructions-fix: ## Demonstrate the instructions logging bug fix
	@echo "🐛 Instructions Logging Bug Fix Demo"
	@echo "===================================="
	@python scripts/instructions_bug_demo.py

show-tools-validation: ## Demonstrate the tools validation and normalization improvements
	@echo "🔧 Tools Validation & Normalization Demo"
	@echo "========================================"
	@python scripts/tools_validation_demo.py

view-logs:
	@echo "📋 Viewing recent logs..."
	@if [ -f logs/qa_intelligence.log ]; then tail -20 logs/qa_intelligence.log; else echo "No logs found yet"; fi

view-errors:
	@echo "🚨 Viewing recent errors..."
	@if [ -f logs/errors.log ]; then tail -10 logs/errors.log; else echo "No error logs found"; fi

view-performance:
	@echo "⚡ Viewing performance metrics..."
	@if [ -f logs/performance.log ]; then tail -10 logs/performance.log; else echo "No performance logs found"; fi


clean-logs:
	@echo "🧹 Cleaning old logs..."
	@rm -rf logs/
	@echo "✅ Logs cleaned"

# Database Migration
migrate-to-supabase: ## Run Supabase migration setup and validation
	@echo "🚀 Starting Supabase migration..."
	$(PY) scripts/migrate_to_supabase.py

check-supabase: ## Check Supabase configuration and connection
	@echo "🔍 Checking Supabase setup..."
	$(PY) -c "from config.supabase import is_supabase_configured; print('✅ Configured' if is_supabase_configured() else '❌ Not configured')"

init-supabase-db: ## Initialize Supabase database with tables
	@echo "🏗️ Initializing Supabase database..."
	$(PY) -c "from database.connection import init_database; init_database()"

test-supabase: ## Test Supabase database connection
	@echo "🧪 Testing Supabase connection..."
	$(PY) -c "from database.connection import test_connection; test_connection()"

demo-supabase: ## Run Supabase migration demo and readiness check
	@echo "🎭 Running Supabase migration demo..."
	$(PY) scripts/demo_supabase_migration.py

type-check:
	$(MYPY) src/ scripts/ config

security:
	$(BANDIT) -r src/ -f json -o security-report.json
	$(SAFETY) check

qa-check: format lint type-check security test-fast
	@echo "✅ QA checks completed"

# Documentation
docs:
	$(MKDOCS) build

docs-serve:
	$(MKDOCS) serve

# Build & Distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	$(BUILD)

publish: build
	$(TWINE) upload dist/*

# Application
run:
	$(PY) scripts/run_qa_agent.py $(ARGS)

run-teams:
	$(PY) scripts/demo_qa_teams_integration.py

run-metrics:
	$(PY) -m src.observability.prometheus_exporter

run-server:
	@echo "🌐 Starting WebSocket Server + Prometheus (Managed)..."
	$(PY) scripts/start_services.py

run-server-parallel:
	@echo "🌐 Starting WebSocket Server + Prometheus (Parallel)..."
	@echo "WebSocket Server: http://localhost:8765"
	@echo "Prometheus Metrics: http://localhost:9400/metrics"
	@echo "Press Ctrl+C to stop both services"
	$(PY) -m src.observability.prometheus_exporter & \
	$(PY) run_websocket_server.py

run-stack:
	@echo "🚀 Starting Complete QA Intelligence Stack..."
	@echo "QA Agent: Interactive chat mode"
	@echo "WebSocket Server: http://localhost:8765" 
	@echo "Prometheus Metrics: http://localhost:9400/metrics"
	@echo "Press Ctrl+C to stop all services"
	$(PY) -m src.observability.prometheus_exporter & \
	$(PY) run_websocket_server.py &

run-demo:
	$(PY) scripts/demo_qa_intelligence.py

validate-teams:
	$(PY) scripts/validate_agno_teams.py

inspect-memory:
	$(PY) scripts/inspect_memory.py

# Development utilities
deps-check:
	$(PIP) list --outdated

deps-update:
	$(PY) -m pip_review --local --interactive || true

profile:
	$(PY) -m cProfile -o profile.stats scripts/run_qa_agent.py
	$(PY) -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# CI/CD helpers
ci-install:
	$(PIP) install -e '.[dev]'

ci-test:
	$(PYTEST) --cov=src --cov-report=xml --junitxml=junit.xml

ci-lint:
	$(RUFF) check src/ scripts/ config.py --format=github
	$(PYLINT) src/ scripts/ config.py --output-format=json --reports=no --score=no > pylint-report.json || true

# Docker (if needed)
docker-build:
	docker build -t qa-intelligence .

docker-run:
	docker run -it --rm qa-intelligence

# Environment management
env-create:
	python -m venv .venv
	@echo "Activate with: source .venv/bin/activate"

env-requirements:
	pip freeze > requirements-lock.txt

# Git hooks
pre-commit:
	pre-commit run --all-files

# Performance monitoring
benchmark:
	$(PYTEST) benchmarks/ --benchmark-only --benchmark-sort=mean

# Git workflow (solo developer)
push-branch:
	@echo "� Pushing current branch..."
	@git push origin $$(git branch --show-current)

prepare-pr: qa-check test push-branch
	@echo "✅ All checks passed, ready for PR"
	@echo "🌐 Go to: https://github.com/stffns/QAI/compare/develop...$$(git branch --show-current)"
	@git status

prepare-release: clean qa-check test
	@echo "🚀 Preparing release..."
	@git status
