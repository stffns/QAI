# Sistema de Escenarios de Testing - QA Intelligence

## 🎯 Resumen del Sistema

El Sistema de Escenarios de Testing permite organizar y ejecutar APIs en grupos específicos para diferentes tipos de pruebas (performance, functional, smoke testing, etc.), resolviendo el problema de tener que ejecutar todos los endpoints cuando solo necesitas subconjuntos específicos.

## 📊 Componentes Implementados

### 1. **Base de Datos** ✅

- **`test_scenarios`**: Tabla principal de escenarios
- **`test_scenario_endpoints`**: Relación entre escenarios y endpoints
- **Migración automática**: Población de datos por defecto

### 2. **TestScenarioManager** ✅

- **Creación de escenarios**: Diferentes tipos (SMOKE, FUNCTIONAL, PERFORMANCE, etc.)
- **Gestión de endpoints**: Asignación, orden de ejecución, configuración
- **Consultas**: Obtener escenarios completos con endpoints

### 3. **Integración con API Tools** ✅

- **Ejecución de escenarios**: Ejecutar todos los endpoints de un escenario
- **Métricas avanzadas**: Success rate, tiempo total, fallos críticos
- **Herramientas @tool**: Disponibles para el QA Agent

## 🚀 Cómo Usar el Sistema

### Crear un Nuevo Escenario

```python
from src.agent.tools.test_scenarios_manager import TestScenarioManager
from database.models.test_scenarios import TestScenarioType

manager = TestScenarioManager()

# Crear escenario de regresión
result = manager.create_scenario(
    mapping_id=1,
    scenario_name='API Regression Test',
    scenario_type=TestScenarioType.REGRESSION,
    description='Regression testing for critical API flows',
    target_concurrent_users=5,
    max_execution_time_minutes=20
)
```

### Agregar Endpoints a un Escenario

```python
# Agregar endpoints específicos
result = manager.add_endpoints_to_scenario(
    scenario_id=7,
    endpoint_ids=[1, 2, 5, 8, 10],
    is_critical=True,
    weight=3,
    auto_order=True  # Ordena automáticamente por método HTTP
)
```

### Ejecutar un Escenario Completo

```python
from src.agent.tools.api_tools import qa_api_tools

# Ejecutar escenario con base URL personalizada
result = qa_api_tools.execute_test_scenario(
    scenario_id=1,
    base_url='https://api.example.com'  # Override de configuración
)

print(f"Status: {result['overall_status']}")
print(f"Success Rate: {result['summary']['success_rate_percent']:.1f}%")
print(f"Total Time: {result['summary']['total_time_ms']:.0f}ms")
```

### Listar Escenarios Disponibles

```python
# Para un mapping específico
scenarios = qa_api_tools.list_available_scenarios(mapping_id=1)

for scenario in scenarios:
    print(f"📋 {scenario['name']} ({scenario['type']}) - {scenario['endpoints_count']} endpoints")
```

## 📋 Tipos de Escenarios Disponibles

| Tipo | Emoji | Descripción | Uso Típico |
|------|-------|-------------|------------|
| **SMOKE** | 💨 | Pruebas básicas de disponibilidad | CI/CD, deploys |
| **FUNCTIONAL** | 🧪 | Pruebas funcionales completas | Testing completo |
| **PERFORMANCE** | 🚀 | Pruebas de carga y rendimiento | Load testing |
| **REGRESSION** | 🔄 | Pruebas de regresión | Releases |
| **SECURITY** | 🔒 | Pruebas de seguridad | Security testing |
| **INTEGRATION** | 🔗 | Pruebas de integración | System testing |
| **BUSINESS_FLOW** | 💼 | Flujos de negocio E2E | User journeys |

## 🎛️ Configuración Avanzada

### Parámetros de Escenario

```python
scenario = manager.create_scenario(
    mapping_id=1,
    scenario_name="Performance Test",
    scenario_type=TestScenarioType.PERFORMANCE,
    target_concurrent_users=50,        # Usuarios concurrentes
    max_execution_time_minutes=15,     # Tiempo máximo
    ramp_up_time_seconds=30,          # Tiempo de ramp-up
    stop_on_critical_failure=True,    # Parar en fallo crítico
    retry_failed_endpoints=2,         # Reintentos automáticos
    priority=1                        # Prioridad de ejecución
)
```

### Configuración de Endpoints

```python
manager.add_endpoints_to_scenario(
    scenario_id=1,
    endpoint_ids=[1, 2, 3],
    is_critical=True,              # Endpoint crítico
    weight=5,                      # Peso para load balancing
    custom_timeout_ms=10000,       # Timeout personalizado
    expected_status_codes=[200, 201], # Códigos esperados
    depends_on_endpoint_ids=[1],   # Dependencias
    notes="Critical authentication flow"
)
```

## 🔧 Herramientas del QA Agent

Las siguientes herramientas están disponibles automáticamente en el QA Agent:

### `list_test_scenarios(mapping_id)`

Lista todos los escenarios disponibles para un mapping específico.

**Uso en chat:**

```
"Muéstrame los escenarios disponibles para el mapping 1"
```

### `execute_test_scenario(scenario_id, base_url="")`

Ejecuta un escenario completo con opción de override de base URL.

**Uso en chat:**

```
"Ejecuta el escenario de smoke test con ID 1 usando la URL https://api.test.com"
```

## 📊 Métricas y Resultados

### Resultado de Ejecución de Escenario

```json
{
  "scenario_id": 1,
  "scenario_name": "Basic Smoke Test",
  "scenario_type": "SMOKE",
  "overall_status": "✅ PASSED",
  "summary": {
    "success_count": 18,
    "failed_count": 2,
    "error_count": 1,
    "total_executed": 21,
    "success_rate_percent": 85.7,
    "total_time_ms": 2500
  },
  "endpoints_results": [
    {
      "endpoint_id": 1,
      "name": "GET /health",
      "status": "✅ SUCCESS",
      "response_code": 200,
      "response_time_ms": 120,
      "performance": "🚀 FAST"
    }
  ]
}
```

### Estados de Resultados

| Estado | Significado | Condición |
|--------|-------------|-----------|
| **✅ PASSED** | Escenario exitoso | ≥90% success rate, sin errores críticos |
| **⚠️ PARTIAL** | Parcialmente exitoso | 50-90% success rate |
| **❌ FAILED** | Escenario fallido | <50% success rate o errores críticos |

## 🎯 Casos de Uso Reales

### 1. Smoke Testing en CI/CD

```python
# Escenario automático para cada deploy
smoke_scenario = manager.create_performance_scenario_for_mapping(
    mapping_id=1,
    concurrent_users=1,
    scenario_name="Deploy Validation"
)
```

### 2. Performance Testing Gradual

```python
# Escenarios escalonados de performance
for users in [10, 25, 50, 100]:
    manager.create_performance_scenario_for_mapping(
        mapping_id=1,
        concurrent_users=users,
        scenario_name=f"Load Test - {users} users"
    )
```

### 3. Testing por Módulos

```python
# Escenarios por funcionalidad
auth_endpoints = [1, 2, 3]  # Login, logout, refresh
user_endpoints = [4, 5, 6]  # Profile, settings, preferences

manager.add_endpoints_to_scenario(auth_scenario_id, auth_endpoints)
manager.add_endpoints_to_scenario(user_scenario_id, user_endpoints)
```

## 🛠️ Estado Actual del Sistema

### ✅ Completado

1. **Migración de BD**: Tablas creadas y pobladas automáticamente
2. **TestScenarioManager**: Manager completo con todas las operaciones CRUD
3. **Integración API**: Ejecución de escenarios desde QAAPITools
4. **Herramientas Agent**: Funciones @tool disponibles para el QA Agent
5. **Validación**: Sistema probado y funcionando

### 📊 Métricas de Implementación

- **Escenarios creados automáticamente**: 6 (2 SMOKE, 2 FUNCTIONAL, 2 PERFORMANCE)
- **Relaciones endpoint-escenario**: 60+ automáticamente pobladas
- **Tipos de escenario soportados**: 8 tipos diferentes
- **Herramientas disponibles**: execute_test_scenario, list_test_scenarios

### 🎯 Próximos Pasos Sugeridos

1. **Interfaz Web**: Dashboard para gestionar escenarios visualmente
2. **Scheduling**: Ejecución automática programada de escenarios
3. **Reporting**: Reportes históricos y comparativos
4. **Templates**: Plantillas de escenarios por industria/tipo de API
5. **CI/CD Integration**: Webhooks y APIs para integración externa

## 🎉 Beneficios Obtenidos

### ✅ Problema Resuelto

- **Antes**: Ejecutar TODOS los endpoints para cualquier tipo de test
- **Después**: Ejecutar SOLO los endpoints relevantes para cada tipo de test

### 🚀 Ventajas del Sistema

1. **Flexibilidad**: Diferentes tipos de escenarios para diferentes necesidades
2. **Eficiencia**: Solo ejecutar lo necesario, ahorro de tiempo y recursos
3. **Organización**: Endpoints agrupados lógicamente por propósito
4. **Configurabilidad**: Timeouts, pesos, dependencias, orden personalizable
5. **Escalabilidad**: Fácil agregar nuevos tipos y configuraciones
6. **Automatización**: Población automática de escenarios por defecto
7. **Métricas**: Resultados detallados con análisis de performance

### 💡 Casos de Uso Resueltos

- **Deploy validation**: Smoke tests rápidos post-deploy
- **Load testing**: Performance tests escalonados
- **Regression testing**: Pruebas específicas de funcionalidades críticas
- **Development testing**: Subconjuntos de APIs para desarrollo local
- **Integration testing**: Flujos E2E de business logic

¡El Sistema de Escenarios de Testing está completamente implementado y listo para uso productivo! 🎉
