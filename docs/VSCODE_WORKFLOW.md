# VS Code Development Workflow - QA Intelligence

Este documento describe las tareas y configuraciones de VS Code creadas para optimizar el flujo de trabajo de desarrollo del proyecto QA Intelligence.

## 🚀 Tareas Principales

### Ejecución de Aplicación

#### `🚀 Start QA Agent (Chat)`

- **Comando:** `python run_qa_agent.py`
- **Uso:** Inicia el agente QA en modo chat interactivo
- **Acceso:** `Cmd+Shift+P` → "Tasks: Run Task" → Seleccionar tarea
- **Panel:** Nueva ventana de terminal con foco

#### `🌐 Start WebSocket Server`

- **Comando:** `python run_websocket_server.py`
- **Uso:** Inicia el servidor WebSocket para comunicación en tiempo real
- **Tipo:** Tarea en background (no bloquea)
- **Panel:** Nueva ventana de terminal sin foco

#### `👥 Start QA Teams Demo`

- **Comando:** `make run-teams`
- **Uso:** Inicia la demostración de colaboración entre equipos QA
- **Panel:** Nueva ventana de terminal con foco

#### `🚀 Quick Start: Agent + WebSocket`

- **Tipo:** Tarea compuesta (ejecuta múltiples tareas en paralelo)
- **Uso:** Inicia tanto el agente QA como el servidor WebSocket simultáneamente
- **Ideal para:** Desarrollo full-stack

### Testing y Quality Assurance

#### `🧪 Run Tests`

- **Comando:** `make test`
- **Uso:** Ejecuta todos los tests con reporte de coverage
- **Problem Matcher:** Python (errores aparecen en "Problems" panel)

#### `⚡ Run Tests (Fast)`

- **Comando:** `make test-fast`
- **Uso:** Ejecuta tests sin coverage para ejecución rápida
- **Ideal para:** Desarrollo iterativo

#### `🔍 Quality Check (All)`

- **Comando:** `make qa-check`
- **Uso:** Ejecuta checks completos (lint, type, security)
- **Recomendado:** Antes de commits importantes

#### `🔒 Security Check`

- **Comando:** `make security`
- **Uso:** Análisis de seguridad con Bandit
- **Problem Matcher:** Python

#### `📊 Type Check`

- **Comando:** `make type-check`
- **Uso:** Verificación de tipos con MyPy
- **Problem Matcher:** Python

### Desarrollo y Mantenimiento

#### `🎨 Format Code`

- **Comando:** `make format`
- **Uso:** Formatea código con Black e isort
- **Presentación:** Silenciosa (no interrumpe)

#### `🧹 Clean Build Artifacts`

- **Comando:** `make clean`
- **Uso:** Limpia archivos de build y cache
- **Presentación:** Silenciosa

#### `🔧 Install Dependencies`

- **Comando:** `make install`
- **Uso:** Instala dependencias de producción

#### `🛠️ Install Dev Dependencies`

- **Comando:** `make install-dev`
- **Uso:** Instala dependencias de desarrollo y configura pre-commit hooks

#### `🔄 Database Migration`

- **Comando:** `python database/migrations/add_solid_fields.py`
- **Uso:** Ejecuta migraciones de base de datos

#### `🏗️ Full Setup (Development)`

- **Tipo:** Tarea con dependencias secuenciales
- **Uso:** Setup completo de desarrollo (limpia + instala + configura)
- **Dependencia:** Ejecuta primero "Clean Build Artifacts"

## 🐛 Configuraciones de Debug

### Configuraciones Disponibles

#### `🚀 Debug QA Agent`

- **Programa:** `run_qa_agent.py`
- **Args:** `--user-id debug_user@qai.com`
- **Uso:** Debug del agente principal

#### `🌐 Debug WebSocket Server`

- **Programa:** `run_websocket_server.py`
- **Uso:** Debug del servidor WebSocket

#### `🧪 Debug Tests`

- **Módulo:** `pytest`
- **Args:** `tests/ -v --tb=short`
- **Uso:** Debug de todo el suite de tests

#### `🔧 Debug Current Test File`

- **Módulo:** `pytest`
- **Args:** `${file} -v --tb=short`
- **Uso:** Debug del archivo de test actual

#### `🔄 Debug Database Migration`

- **Programa:** `database/migrations/add_solid_fields.py`
- **Uso:** Debug de migraciones

#### `👥 Debug QA Teams`

- **Programa:** `scripts/demo_qa_teams_integration.py`
- **Uso:** Debug de la demo de equipos

### Configuraciones de Debug

- **Tipo:** `debugpy` (nueva extensión de Python)
- **Console:** Terminal integrado
- **PYTHONPATH:** Configurado automáticamente
- **justMyCode:** `false` (permite debug de dependencias)

## ⌨️ Snippets de Código

### Snippets Disponibles

#### `qa-agent` - Clase de Agente QA

```python
class ClassName:
    """Description"""
    
    def __init__(self, params):
        """Initialize ClassName"""
        pass
```

#### `qa-repo` - Patrón Repository

```python
class ModelClassRepository(BaseRepository[ModelClass]):
    """Repository for ModelClass operations"""
    
    def get_by_field(self, field: type) -> Optional[ModelClass]:
        # Implementation
```

#### `qa-model` - Clase SQLModel

```python
class ModelName(SQLModel, TimestampMixin, AuditMixin, table=True):
    """Model description"""
    __tablename__ = "table_name"
    # Fields...
```

#### `qa-test` - Caso de Test

```python
def test_test_name(self, fixtures):
    """Test description"""
    # Arrange, Act, Assert pattern
```

#### `qa-async` - Función Async

```python
async def function_name(params) -> ReturnType:
    """Function description"""
    # Implementation with error handling
```

#### `qa-logger` - Setup de Logger

```python
from src.logging_config import get_logger
logger = get_logger("ComponentName")
```

#### `qa-config` - Modelo de Configuración

```python
class ConfigName(BaseModel):
    """Configuration description"""
    # Pydantic fields...
```

#### `qa-exception` - Clase de Excepción

```python
class ExceptionName(Exception):
    """Exception description"""
    # Custom exception with context
```

## ⚙️ Configuraciones del Workspace

### Python Environment

- **Intérprete:** `.venv/bin/python`
- **PYTHONPATH:** Configurado automáticamente para `src/`
- **Activación automática:** Habilitada

### Testing

- **Framework:** pytest
- **Auto-discovery:** Habilitado
- **Directorio:** `tests/`

### Formatting & Linting

- **Formatter:** Black (línea 88 caracteres)
- **Import sorting:** isort
- **Linting:** pylint, mypy, bandit
- **Format on save:** Habilitado
- **Organize imports on save:** Habilitado

### File Management

- **File nesting:** Habilitado para organizar archivos relacionados
- **Exclusiones:** `__pycache__`, `.pytest_cache`, logs, etc.
- **Asociaciones:** YAML, Python, Makefile

## 🎯 Flujos de Trabajo Recomendados

### 1. Desarrollo Diario

```bash
1. Start QA Agent (para testing interactivo)
2. Format Code (antes de commits)
3. Run Tests (Fast) (durante desarrollo)
4. Quality Check (All) (antes de push)
```

### 2. Setup Inicial de Proyecto

```bash
1. Full Setup (Development)
2. Database Migration
3. Run Tests (validar setup)
```

### 3. Debugging

```bash
1. Set breakpoints en código
2. Launch Debug QA Agent (o la configuración apropiada)
3. Usar Debug Console para inspección
```

### 4. Deployment Preparation

```bash
1. Clean Build Artifacts
2. Quality Check (All)
3. Security Check
4. Run Tests (full coverage)
```

## 📋 Atajos de Teclado

### Tareas

- `Cmd+Shift+P` → "Tasks: Run Task" → Seleccionar tarea
- `Cmd+Shift+P` → "Tasks: Restart Running Task"
- `Cmd+Shift+P` → "Tasks: Terminate Task"

### Debug

- `F5` → Start Debugging
- `Shift+F5` → Stop Debugging
- `F9` → Toggle Breakpoint
- `F10` → Step Over
- `F11` → Step Into

### Testing

- `Cmd+Shift+P` → "Python: Run All Tests"
- `Cmd+Shift+P` → "Python: Run Current Test File"

## 🚀 Comandos Rápidos

### Terminal

```bash
# Activar entorno virtual
source .venv/bin/activate

# Ejecutar agente rápidamente
python run_qa_agent.py

# Tests rápidos
make test-fast

# Limpiar y reinstalar
make clean && make install-dev
```

### VS Code Command Palette

- `> Tasks: Run Task` - Ejecutar cualquier tarea
- `> Python: Select Interpreter` - Cambiar intérprete de Python
- `> Test: Run All Tests` - Ejecutar todos los tests
- `> Debug: Start Debugging` - Iniciar debug

Este workflow está diseñado para maximizar la productividad en el desarrollo del proyecto QA Intelligence, proporcionando acceso rápido a todas las operaciones comunes y facilitando el debugging y testing.
