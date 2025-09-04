# QA Intelligence - AI Agent Instructions

## Project Overview
QA Intelligence is a specialized AI chat agent built with **Agno 1.8.1** framework, designed for QA Testing and Intelligence workflows. It features a modular SOLID architecture with Memory v2, optional reasoning capabilities, and configurable AI models.

## Architecture Pattern
This project follows **Single Responsibility Principle (SRP)** with specialized manager classes:

- **QA Agent** (`src/agent/qa_agent.py`) - Main coordinator orchestrating all components
- **Model Manager** - Handles OpenAI/Azure/DeepSeek model configuration via Pydantic validation
- **Tools Manager** - Manages DuckDuckGo search, Python execution, calculator tools
- **Storage Manager** - Configures Agno Memory v2 with SQLite backend
- **Reasoning Manager** - Optional O3/O1/DeepSeek reasoning capabilities (disabled by default)

**Key Pattern**: All managers accept dependency injection and follow the same interface contract for consistent configuration.

## Essential Development Workflows

### Running the Agent
```bash
# Primary entry point (modular components)
python run_qa_agent.py

# Alternative direct execution  
source .venv/bin/activate && python src/agent/qa_agent.py

# Teams collaboration demo
make run-teams

# Full test suite with coverage
make test
```

### Configuration Management
Configuration is **YAML-driven** with Pydantic validation:

```yaml
# agent_config.yaml - Primary configuration
model:
  provider: "openai"  # openai, azure, deepseek
  id: "gpt-4"
  temperature: 0.7

reasoning:
  enabled: false  # Enable for deep analysis
  type: "agent"   # "model", "tools", "agent"

tools:
  web_search: true
  python_execution: true
  calculator: true
```

**Critical**: Use `python config.py` to validate current configuration. Environment variables in `.env` override YAML settings.

### Database Architecture
This project implements **Repository Pattern with SOLID principles**:

```python
# Usage pattern for all database operations
from database.repositories import create_unit_of_work_factory

uow_factory = create_unit_of_work_factory(engine)
with uow_factory.create_scope() as uow:
    user = uow.users.create_user(user_data)
    # Auto-commit on context exit
```

**Database Locations**:
- `data/qa_intelligence.db` - Main application data
- `data/qa_conversations.db` - Chat history (Memory v2)
- `data/qa_intelligence_rag.db` - Vector/RAG storage

## Project-Specific Conventions

### Import Patterns
The codebase uses **absolute imports with fallback handling**:

```python
# Standard pattern throughout the project
try:
    from config import get_config
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from config import get_config
```

### Error Handling Strategy
All components use **structured exception hierarchies**:

```python
# Repository exceptions
EntityNotFoundError    # 404-style errors
InvalidEntityError     # Validation failures  
DuplicateEntityError   # Constraint violations
DatabaseConnectionError # Infrastructure issues

# Agent exceptions
AgentCreationError     # Component initialization
ConfigurationError     # Config validation
ModelManagerError      # AI model issues
```

### Logging Architecture
Uses **Loguru with structured logging**:

```python
from src.logging_config import get_logger, LogExecutionTime, LogStep

logger = get_logger("ComponentName")

with LogExecutionTime("Operation name", "ComponentName"):
    # Performance-tracked code
    
with LogStep("Step description", "ComponentName"):
    # Detailed operation logging
```

## Testing Strategy

### Test Structure
```bash
# Repository pattern validation
pytest tests/test_solid_repositories.py -v

# Component integration tests  
pytest tests/test_integration_complete.py -v

# Configuration validation
pytest tests/test_config_validation.py -v
```

**Test Database Pattern**: All tests use in-memory SQLite (`sqlite:///:memory:`) with automatic schema creation via `SQLModel.metadata.create_all(engine)`.

### Key Test Fixtures
```python
@pytest.fixture
def uow_factory(self, engine):
    """Unit of Work factory for repository tests"""
    from database.repositories.unit_of_work import UnitOfWorkFactory
    return UnitOfWorkFactory(engine)
```

## Development Tools

### Makefile Commands
```bash
make install-dev     # Install dev dependencies + pre-commit hooks
make qa-check        # Run all quality checks (lint, type, security)
make test           # Tests with coverage report
make format         # Black + isort formatting
make clean          # Remove build artifacts
```

### Type Safety
Project uses **strict Pydantic v2 validation**:
- All config models in `config/models.py` are Pydantic dataclasses
- Repository patterns use SQLModel (Pydantic + SQLAlchemy)
- Enable `mypy` for full type checking compliance

## Integration Points

### Agno Framework Integration
**Memory v2 Setup**:
```python
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory

memory_db = SqliteMemoryDb(
    table_name="qa_user_memories",
    db_file="data/qa_conversations.db"
)
storage = Memory(model=OpenAIChat(id="gpt-4o-mini"), db=memory_db)
```

### Tool Registration Pattern
```python
# Tools follow consistent loading pattern in ToolsManager
from agno.tools.duckduckgo import DuckDuckGo
from agno.tools.python import PythonTools
from agno.tools.calculator import CalculatorTools

# All tools auto-register via tools_config YAML settings
```

## Critical Development Rules

### **Database Management**
- **DO NOT** create new databases unless explicitly requested by the user
- Use existing database paths: `data/qa_intelligence.db`, `data/qa_conversations.db`, `data/qa_intelligence_rag.db`
- Follow the established repository pattern for all database operations

### **Error Handling Philosophy**
- **DO NOT** create fallbacks that hide errors - let exceptions bubble up properly
- Use the structured exception hierarchy (`EntityNotFoundError`, `InvalidEntityError`, etc.)
- Preserve error information for debugging - avoid generic "something went wrong" messages

### **Data Integrity**
- **DO NOT** create simulated/fake data unless explicitly requested
- Use real data sources or empty states when data is unavailable
- Respect data validation rules defined in Pydantic models

## Critical Files to Understand

1. **`agent_config.yaml`** - Central configuration driving all behavior
2. **`src/agent/qa_agent.py`** - Main orchestrator implementing SRP pattern  
3. **`database/repositories/base.py`** - Repository pattern foundation
4. **`config/models.py`** - Pydantic validation schemas
5. **`run_qa_agent.py`** - Primary executable entry point

When modifying components, always maintain the dependency injection pattern and ensure configuration changes are reflected in both YAML and Pydantic models.
