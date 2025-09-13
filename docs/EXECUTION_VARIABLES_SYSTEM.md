# Sistema de Variables de Ejecución - QA Intelligence

## 🎯 Descripción General

El sistema de variables de ejecución permite al agente QA gestionar dinámicamente los placeholders y valores de ejecución utilizados en los tests automatizados. Esto elimina la necesidad de hardcodear valores y permite que el agente adapte los tests a diferentes ambientes y condiciones. Aunque fue diseñado inicialmente para colecciones de Postman, es genérico y puede usarse con cualquier herramienta de testing.

## 🏗️ Arquitectura

### Componentes Principales

1. **Campo JSON `execution_variables`** en `app_environment_country_mappings`
2. **ExecutionVariablesManager** - Gestión de datos
3. **PostmanAgentTool** - Interface del agente
4. **PostmanEndpointImporter** - Extracción automática

### Estructura de Datos

```json
{
  "variables": {
    "base_url": "{{BASE_URL}}",
    "api_key": "{{API_KEY}}", 
    "user_id": "{{USER_ID}}",
    "tenant_id": "{{TENANT_ID}}",
    "access_token": "{{ACCESS_TOKEN}}",
    "correlation_id": "{{CORRELATION_ID}}"
  },
  "runtime_values": {
    "base_url": "https://api-prod.example.com",
    "api_key": "sk_live_abc123",
    "user_id": "user_12345",
    "tenant_id": "tenant_67890"
  },
  "metadata": {
    "last_updated": "2025-12-09T10:30:00Z",
    "updated_by": "qa_agent",
    "version": "1.0"
  }
}
```

## 🔧 Implementación Técnica

### 1. Migración de Base de Datos

```bash
python database/migrations/add_execution_variables_field.py
```

**Resultado**:

- ✅ Campo `execution_variables` agregado tipo JSON
- ✅ Estructura inicial aplicada a registros existentes
- ✅ Verificación exitosa

### 2. Modelo SQLModel Actualizado

```python
# En AppEnvironmentCountryMapping
execution_variables: Optional[Dict[str, Any]] = Field(
    default=None,
    sa_column=Column(SQLAlchemyJSON),
    description="Postman collection variables and runtime values"
)
```

### 3. ExecutionVariablesManager

**Funcionalidades principales**:

```python
manager = ExecutionVariablesManager()

# Obtener variables de un mapping
variables = manager.get_mapping_variables(app_id, env_id, country_id)

# Actualizar valores runtime
success = manager.update_runtime_values(app_id, env_id, country_id, {
    "api_key": "new_key_123",
    "user_id": "test_user_456"
})

# Agregar nuevas plantillas
success = manager.add_variable_template(app_id, env_id, country_id, {
    "new_var": "{{NEW_VAR}}"
})

# Inicializar variables para nuevo mapping
success = manager.initialize_execution_variables(app_id, env_id, country_id)
```

### 4. Herramienta del Agente

```python
from src.agent.tools.execution_variables_manager import (
    get_execution_variables,
    update_postman_runtime_values,
    add_execution_variables,
    initialize_mapping_variables
)

# Obtener variables (usando IDs reales de la base de datos)
vars = get_execution_variables(app_id=1, env_id=1, country_id=1)

# Actualizar durante ejecución de test  
success = update_postman_runtime_values(app_id=1, env_id=1, country_id=1, {
    "access_token": "new_token_xyz"
})

# Las variables se integran automáticamente con PostmanEndpointImporter
postman_env = postman_agent_tool.generate_postman_environment("EVA", "STA", "RO")
```

## 📥 Importación Automática

### PostmanEndpointImporter Mejorado

El importador ahora extrae automáticamente variables de:

1. **Collection variables** - Variables definidas en la colección
2. **Environment variables** - Variables del archivo de ambiente
3. **Request content** - Variables encontradas en URLs, headers, body

**Ejemplo de uso**:

```python
importer = PostmanEndpointImporter(session)

result = importer.import_collection(
    collection_path=Path("collection.json"),
    environment_path=Path("environment.json"),
    application_code="EVA",
    environment_code="STA", 
    country_code="RO"
)

# Resultado incluye información de variables
print(f"Variables extraídas: {result['execution_variables']['variables_extracted']}")
print(f"Valores runtime: {result['execution_variables']['runtime_values_set']}")
```

## 🤖 Casos de Uso del Agente

### 1. Gestión Dinámica durante Tests

```python
# El agente puede actualizar variables en tiempo real
def update_test_environment():
    # Obtener token OAuth2 actualizado
    new_token = get_fresh_oauth_token()
    
    # Actualizar en todas las configuraciones
    postman_agent_tool.update_test_variables("EVA", "STA", "RO", {
        "access_token": new_token,
        "correlation_id": generate_correlation_id()
    })
```

### 2. Configuración de Ambientes

```python
# Configurar ambiente de testing
def setup_test_environment():
    # Inicializar variables estándar
    postman_agent_tool.initialize_variables_for_new_test("EVA", "UAT", "FR")
    
    # Agregar variables específicas del test
    postman_agent_tool.add_new_variables("EVA", "UAT", "FR", {
        "test_user_id": "{{TEST_USER_ID}}",
        "test_scenario": "{{TEST_SCENARIO}}"
    })
```

### 3. Generación de Archivos de Ambiente

```python
# Exportar configuración actual a Postman
def export_to_postman():
    env_data = postman_agent_tool.generate_postman_environment("EVA", "PRD", "RO")
    
    with open("eva_prod_ro.postman_environment.json", "w") as f:
        json.dump(env_data, f, indent=2)
```

## 📊 Beneficios Implementados

### ✅ Para el Agente QA

1. **Gestión Dinámica**: Actualizar variables durante ejecución de tests
2. **Configuración Automática**: Inicializar ambientes de test rápidamente  
3. **Adaptabilidad**: Modificar comportamiento según condiciones de test
4. **Trazabilidad**: Metadata de cambios para auditoría

### ✅ Para el Equipo de Testing

1. **Separación de Concerns**: Variables de infraestructura vs. lógica de negocio
2. **Reutilización**: Mismo test en múltiples ambientes
3. **Mantenibilidad**: Actualizaciones centralizadas
4. **Flexibilidad**: Nuevas variables sin cambios de código

### ✅ Para DevOps/Infraestructura

1. **Configuración Centralizada**: Un lugar para todas las variables
2. **Ambientes Múltiples**: Soporte nativo para staging/UAT/production
3. **Integración Postman**: Compatibilidad completa con herramientas existentes
4. **Auditoría**: Tracking completo de cambios

## 🔄 Flujo de Trabajo

### Importación Inicial

```
1. Importar colección Postman → PostmanEndpointImporter
2. Extraer variables automáticamente → extract_and_update_execution_variables()
3. Almacenar en app_environment_country_mappings → execution_variables field
4. Inicializar con valores por defecto → ExecutionVariablesManager
```

### Ejecución de Tests

```  
1. Agente obtiene variables → postman_agent_tool.get_variables_for_test()
2. Actualiza valores dinámicos → update_test_variables()
3. Ejecuta requests con variables actualizadas
4. Registra cambios para auditoría → metadata tracking
```

### Mantenimiento

```
1. Agregar nuevas variables → add_new_variables() 
2. Actualizar configuraciones → update_test_variables()
3. Exportar a Postman → generate_postman_environment()
4. Sincronizar ambientes → list_all_test_configurations()
```

## 📈 Estadísticas de Implementación

- **✅ Migración**: 1 registro actualizado exitosamente
- **✅ Testing**: ExecutionVariablesManager probado con 9 variables
- **✅ Integración**: PostmanAgentTool funcional
- **✅ Extracción**: PostmanEndpointImporter actualizado

## 🚀 Próximos Pasos Sugeridos

1. **Mapeo Dinámico Códigos ↔ IDs**: Resolver conversión automática de códigos a IDs
2. **Interface Web**: Dashboard para gestión visual de variables
3. **Sincronización Postman**: Import/export bidireccional con Postman
4. **Templates Predefinidos**: Plantillas para diferentes tipos de aplicaciones
5. **Validación de Variables**: Verificar que las variables necesarias estén definidas

---

**Implementado**: Diciembre 2025  
**Estado**: ✅ Funcional y Probado  
**Contacto**: QA Intelligence Agent
