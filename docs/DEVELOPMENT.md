# QA Intelligence Development Guide

## 🚀 Quick Start

### Installation
```bash
# Install development dependencies
make install-dev

# Setup pre-commit hooks
make setup-hooks
```

### Running the Application
```bash
# Run main QA agent
make run

# Run teams demo
make run-teams

# Validate teams functionality
make validate-teams
```

## 🛠️ Development Workflow

### Code Quality
```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# Security checks
make security

# Run all quality checks
make qa-check
```

### Testing
```bash
# Run all tests with coverage
make test

# Fast tests (no coverage)
make test-fast

# Unit tests only
make test-unit

# Integration tests only
make test-integration
```

### Documentation
```bash
# Build docs
make docs

# Serve docs locally
make docs-serve
```

## 📋 Project Standards

### Code Style
- **Black** for code formatting (line length: 88)
- **isort** for import sorting
- **Pylint** for code analysis
- **Ruff** for fast linting
- **MyPy** for type checking

### Testing
- **Pytest** for testing framework
- Minimum 80% code coverage required
- Tests organized by: unit, integration, QA, memory, teams

### Security
- **Bandit** for security analysis
- **Safety** for dependency vulnerability checking
- Pre-commit hooks for automated checks

### Git Workflow
- Conventional commits enforced
- Pre-commit hooks mandatory
- All quality checks must pass

## 🏗️ Architecture

### Core Components
- `src/agent/` - Main QA agent implementation
- `src/core/` - Core utilities and managers
- `scripts/` - Executable scripts and demos
- `docs/` - Documentation

### Configuration
- `pyproject.toml` - Project configuration and dependencies
- `agent_config.yaml` - Agent-specific configuration
- `.env` - Environment variables

## 📦 Dependencies

### Production
- **agno** - AI agent framework
- **openai** - OpenAI API client
- **fastapi** - Web framework
- **pydantic** - Data validation
- **sqlalchemy** - Database ORM

### Development
- **pytest** - Testing
- **black** - Code formatting
- **pylint** - Linting
- **mypy** - Type checking
- **pre-commit** - Git hooks

## 🔧 Configuration

### pyproject.toml Features
- Modern Python packaging (PEP 621)
- Comprehensive tool configurations
- Development dependencies separation
- Entry points for CLI scripts
- Quality gates and standards

### Available Scripts
- `qa-agent` - Main QA agent
- `qa-teams` - Teams demo
- `qa-memory` - Memory inspector
- `qa-demo` - General demo

## 📊 Quality Gates

### Code Quality
- **Coverage**: Minimum 80%
- **Linting**: No pylint/ruff errors
- **Type Checking**: MyPy validation
- **Security**: Bandit + Safety checks
- **Formatting**: Black + isort compliant

### Testing
- All tests must pass
- Unit and integration test separation
- Performance benchmarks available

## 🚨 Troubleshooting

### Common Issues
1. **Import errors**: Check PYTHONPATH and package structure
2. **Configuration errors**: Validate `agent_config.yaml` and `.env`
3. **Dependency conflicts**: Use `make deps-check` and `make deps-update`
4. **Pre-commit failures**: Run `make qa-check` locally first

### Debug Commands
```bash
# Check project health
make qa-check

# Validate configuration
python config.py

# Test specific components
python scripts/validate_agno_teams.py
python scripts/inspect_memory.py
```
