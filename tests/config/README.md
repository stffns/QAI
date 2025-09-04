# Tests de Configuración - QA Intelligence

Este directorio contiene una suite completa de tests unitarios para todo el sistema de configuración de QA Intelligence.

## 📁 Estructura

```
tests/config/
├── test_core_models.py      # Tests para ModelConfig, DatabaseConfig, ToolsConfig
├── test_settings.py         # Tests para Settings principal
├── test_logging_models.py   # Tests para LoggingConfig y LogLevel
├── test_runner.py          # Runner principal para todos los tests
└── README.md              # Esta documentación
```

## 🧪 Archivos de Test

### `test_core_models.py`
**Cobertura**: `config/models/core.py`
- ✅ **ModelConfig**: Validación de proveedores AI, API keys, temperatura, timeouts
- ✅ **DatabaseConfig**: URLs de conexión, pooling, validación de esquemas
- ✅ **ToolConfig**: Configuración individual de herramientas
- ✅ **ToolsConfig**: Orquestación de herramientas, habilitación/deshabilitación
- ✅ **Enums**: ModelProvider, DatabaseType con validación
- ✅ **Variables de entorno**: MODEL_*, DB_*, TOOLS_*
- ✅ **Validadores personalizados**: Azure requirements, API key format

**Tests principales**:
```python
# Validación de proveedores
test_provider_validation()
test_azure_validation()  
test_temperature_validation()

# Configuración de base de datos
test_database_url_validation()
test_sqlite_directory_creation()

# Herramientas
test_default_tools()
test_get_tool_config()
test_is_tool_enabled()
```

### `test_settings.py`
**Cobertura**: `config/settings.py`
- ✅ **Settings**: Clase principal que orquesta toda la configuración
- ✅ **Integración YAML**: Carga de agent_config.yaml
- ✅ **Prioridad**: ENV vars > YAML > defaults
- ✅ **Validación cruzada**: Entre componentes de configuración
- ✅ **Serialización**: Dump/load de configuración completa
- ✅ **Post-init hooks**: Validación automática después de carga

**Tests principales**:
```python
# Carga de configuración
test_yaml_configuration_loading()
test_environment_over_yaml_priority()

# Integración
test_model_config_integration()
test_database_config_integration()
test_tools_config_integration()

# Casos edge
test_malformed_environment_values()
test_missing_required_fields()
```

### `test_logging_models.py`
**Cobertura**: `config/models/logging.py`
- ✅ **LoggingConfig**: Configuración avanzada de logging
- ✅ **LogLevel**: Niveles personalizados (TRACE, SUCCESS, etc.)
- ✅ **File logging**: Rotación, backup, compresión
- ✅ **Console logging**: Override de niveles
- ✅ **JSON logging**: Structured logging para producción
- ✅ **Variables de entorno**: LOG_*
- ✅ **Validación**: Tamaños de archivo, backup count

**Tests principales**:
```python
# Configuración básica
test_default_values()
test_environment_variables_loading()

# Validaciones
test_backup_count_validation()
test_size_format_variations()

# Integración
test_complete_environment_configuration()
test_boolean_environment_parsing()
```

## 🚀 Ejecutar Tests

### Opción 1: Test Runner Integrado
```bash
cd /Users/jaysonsteffens/Documents/QAI
python tests/config/test_runner.py
```

**Funcionalidades del runner**:
- ✅ Validación automática del entorno
- ✅ Ejecución individual o conjunto
- ✅ Reporte de coverage HTML
- ✅ Output colorizado
- ✅ Diagnóstico de errores

### Opción 2: Pytest Directo
```bash
# Todos los tests de config
pytest tests/config/ -v

# Test específico
pytest tests/config/test_core_models.py -v
pytest tests/config/test_settings.py -v
pytest tests/config/test_logging_models.py -v

# Con coverage
pytest tests/config/ --cov=config --cov-report=html
```

### Opción 3: Makefile del Proyecto
```bash
# Si existe en el proyecto
make test-config

# O usar el test general
make test
```

## 📊 Coverage Esperado

| Módulo | Coverage Target | Funcionalidades Cubiertas |
|--------|----------------|---------------------------|
| `config/models/core.py` | **95%+** | Todos los modelos, validadores, env vars |
| `config/settings.py` | **90%+** | Settings principal, YAML loading, integration |
| `config/models/logging.py` | **85%+** | LoggingConfig, LogLevel, file/console logging |
| **Total Config** | **90%+** | Sistema completo de configuración |

## 🧩 Fixtures y Utilidades

### Fixtures Principales
```python
@pytest.fixture
def sample_model_config():
    """ModelConfig preconfigurado para tests"""

@pytest.fixture  
def sample_tools_config():
    """ToolsConfig con herramientas de ejemplo"""

@pytest.fixture
def clean_environment():
    """Limpia variables de entorno para tests aislados"""

@pytest.fixture
def temp_yaml_file():
    """Archivo YAML temporal para tests de carga"""
```

### Patrones de Test Comunes
```python
# Test con env vars
@patch.dict(os.environ, {"MODEL_PROVIDER": "azure"})
def test_environment_loading():
    config = ModelConfig()
    assert config.provider == "azure"

# Test de validación
def test_validation_error():
    with pytest.raises(ValidationError, match="Azure provider requires"):
        ModelConfig(provider="azure")

# Test de serialización
def test_serialization():
    config = ModelConfig()
    data = config.model_dump()
    new_config = ModelConfig(**data)
    assert new_config.provider == config.provider
```

## 🛠️ Debugging Tests

### Tests Fallando?
1. **Verificar imports**:
   ```bash
   python tests/config/test_runner.py
   # Seleccionar opción 3 (Solo validar imports)
   ```

2. **Ejecutar test individual**:
   ```bash
   pytest tests/config/test_core_models.py::TestModelConfig::test_default_values -v -s
   ```

3. **Ver variables de entorno**:
   ```python
   import os
   print({k: v for k, v in os.environ.items() if k.startswith('MODEL_')})
   ```

### Coverage Bajo?
```bash
# Ver líneas no cubiertas
pytest tests/config/ --cov=config --cov-report=term-missing

# Generar reporte HTML detallado  
pytest tests/config/ --cov=config --cov-report=html:htmlcov
open htmlcov/index.html
```

## 📝 Convenciones de Testing

### Nomenclatura
- **Clases**: `TestNombreDelModelo` (ej: `TestModelConfig`)
- **Métodos**: `test_funcionalidad_específica` (ej: `test_azure_validation`)
- **Fixtures**: `nombre_descriptivo_config` (ej: `sample_model_config`)

### Organización de Tests
1. **Valores por defecto** (test_default_values)
2. **Variables de entorno** (test_environment_variables_loading)
3. **Validaciones** (test_*_validation)
4. **Casos edge** (test_edge_cases)
5. **Integración** (test_*_integration)

### Assertions Importantes
```python
# Verificar tipos
assert isinstance(config.tools, list)

# Verificar contenido
assert config.provider in ["openai", "azure", "deepseek"]

# Verificar validación
with pytest.raises(ValidationError, match="specific error message"):
    InvalidConfig()

# Verificar env vars
with patch.dict(os.environ, {"VAR": "value"}):
    assert Config().field == "value"
```

## 🔄 Integración Continua

### Pre-commit Hook
```bash
# Ejecutar tests antes de commit
pytest tests/config/ --quiet
```

### GitHub Actions (si aplica)
```yaml
- name: Test Configuration
  run: |
    pytest tests/config/ --cov=config
    pytest tests/config/ --cov=config --cov-fail-under=85
```

---

## 📞 Support

Si tienes problemas con los tests de configuración:

1. **Ejecuta el diagnóstico**: `python tests/config/test_runner.py` → Opción 3
2. **Verifica el entorno**: Asegúrate de que `config/` esté en el PYTHONPATH
3. **Revisa las dependencias**: `pip install -r requirements-dev.txt`
4. **Consulta logs**: Los tests generan output detallado sobre fallos

**¡Los tests están diseñados para ser informativos y ayudar en el debugging!** 🚀
