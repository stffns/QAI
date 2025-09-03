# Makefile for QA Intelligence project
.PHONY: help install install-dev test lint format type-check security clean build docs run

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
	@echo "  run          Run QA agent"
	@echo "  run-teams    Run QA teams demo"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

setup-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Testing
test:
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-fast:
	pytest -x --no-cov

test-integration:
	pytest -m integration

test-unit:
	pytest -m unit

# Code quality
lint:
	pylint src/ scripts/ config.py
	ruff check src/ scripts/ config.py

format:
	black src/ scripts/ config.py

# QA Agent specific validation
qa-check: lint type-check test-fast
	@echo "✅ QA checks completed"

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

show-loguru-summary:
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
	isort src/ scripts/ config.py

type-check:
	mypy src/ scripts/ config.py

security:
	bandit -r src/ -f json -o security-report.json
	safety check

qa-check: format lint type-check security test
	@echo "✅ All quality checks passed!"

# Documentation
docs:
	mkdocs build

docs-serve:
	mkdocs serve

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
	python -m build

publish: build
	python -m twine upload dist/*

# Application
run:
	python scripts/run_qa_agent.py

run-teams:
	python scripts/demo_qa_teams_integration.py

run-demo:
	python scripts/demo_qa_intelligence.py

validate-teams:
	python scripts/validate_agno_teams.py

inspect-memory:
	python scripts/inspect_memory.py

# Development utilities
deps-check:
	pip list --outdated

deps-update:
	pip-review --local --interactive

profile:
	python -m cProfile -o profile.stats scripts/run_qa_agent.py
	python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# CI/CD helpers
ci-install:
	pip install -e ".[dev]"

ci-test:
	pytest --cov=src --cov-report=xml --junitxml=junit.xml

ci-lint:
	ruff check src/ scripts/ config.py --format=github
	pylint src/ scripts/ config.py --output-format=json --reports=no --score=no > pylint-report.json || true

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
	python -m pytest benchmarks/ --benchmark-only --benchmark-sort=mean
