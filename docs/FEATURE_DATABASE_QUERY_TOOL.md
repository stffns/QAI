# Feature: Database Query Tool para Apps y Países

## 🎯 Objetivo
Crear un tool personalizado para Agno que permita consultar la base de datos de aplicaciones y países del sistema QA Intelligence, proporcionando capacidades de búsqueda y análisis inteligente.

## 📋 Análisis de Datos Existentes

### Tablas Identificadas:
- **`apps_master`**: Aplicaciones del sistema
- **`countries_master`**: Países y regiones  
- **`application_country_mapping`**: Relación apps-países

### Estructura de Datos:

#### Apps Master
```sql
- id (PK)
- app_code (VARCHAR(50)) - Código único de la app
- app_name (VARCHAR(255)) - Nombre de la aplicación
- description (TEXT) - Descripción
- base_url_template (VARCHAR(500)) - Template de URL
- is_active (BOOLEAN) - Estado activo
- created_at, updated_at
```

#### Countries Master
```sql
- id (PK)
- country_name (VARCHAR(255)) - Nombre del país
- country_code (VARCHAR(10)) - Código ISO
- region (VARCHAR(100)) - Región geográfica
- currency_code (VARCHAR(10)) - Moneda
- timezone (VARCHAR(50)) - Zona horaria
- is_active (BOOLEAN) - Estado activo
- created_at, updated_at
```

#### Application Country Mapping
```sql
- mapping_id (PK)
- application_id (FK) - Referencia a apps_master
- country_id (FK) - Referencia a countries_master
- is_active (BOOLEAN) - Estado del mapping
- launched_date - Fecha de lanzamiento
- deprecated_date - Fecha de deprecación
- created_at, updated_at
```

## 🏗️ Arquitectura de Implementación

### 1. Modelos SQLAlchemy (database/models/)
```
database/models/
├── __init__.py
├── apps.py          # Modelo Apps Master
├── countries.py     # Modelo Countries Master  
└── mappings.py      # Modelo Application Country Mapping
```

### 2. Repositorios (database/repositories/)
```
database/repositories/
├── apps_repository.py      # CRUD para apps
├── countries_repository.py # CRUD para países
└── mappings_repository.py  # CRUD para mappings
```

### 3. Tool Agno (src/tools/)
```
src/tools/
└── database_query_tool.py  # Tool principal para Agno
```

### 4. Servicios de Consulta (src/services/)
```
src/services/
└── database_query_service.py  # Lógica de negocio
```

## 🔧 Funcionalidades del Tool

### Consultas Básicas:
- `apps.list()` - Listar todas las aplicaciones activas
- `countries.list()` - Listar todos los países activos
- `apps.find(code="EVA")` - Buscar app por código
- `countries.find(code="RO")` - Buscar país por código

### Consultas Relacionales:
- `apps.get_countries("EVA")` - Países donde está disponible una app
- `countries.get_apps("RO")` - Apps disponibles en un país
- `mappings.active()` - Mappings activos
- `mappings.by_region("Europe")` - Apps por región

### Consultas Analíticas:
- `stats.apps_by_region()` - Estadísticas de apps por región
- `stats.countries_coverage()` - Cobertura geográfica
- `stats.launch_timeline()` - Timeline de lanzamientos

### Consultas en Lenguaje Natural:
- "¿Qué aplicaciones están disponibles en Francia?"
- "¿En qué países está disponible EVA?"
- "¿Cuáles son las apps más populares en Europa?"
- "¿Cuándo se lanzó ONEAPP en Romania?"

## 📚 Casos de Uso

### Para QA Testing:
- Verificar que las aplicaciones estén configuradas correctamente
- Validar disponibilidad geográfica antes de pruebas
- Identificar inconsistencias en mappings
- Generar reportes de cobertura de testing

### Para Análisis de Negocio:
- Análisis de penetración geográfica
- Identificación de oportunidades de expansión
- Reportes de estado de aplicaciones
- Análisis de timeline de lanzamientos

## 🎭 Interfaz del Tool

### Comandos Directos:
```python
# Listar apps
tool.execute("list_apps")

# Buscar por código
tool.execute("find_app", {"code": "EVA"})

# Relaciones
tool.execute("app_countries", {"app_code": "EVA"})
```

### Consultas en Lenguaje Natural:
```python
# El tool interpretará automáticamente
tool.execute("query", {"text": "apps available in Romania"})
tool.execute("query", {"text": "countries for ONEAPP"})
```

## 🔄 Flujo de Implementación

### Fase 1: Fundación (Modelos y Repositorios)
1. Crear modelos SQLAlchemy para las 3 tablas
2. Implementar repositorios base con CRUD
3. Crear unit of work pattern para transacciones
4. Tests básicos de modelos y repositorios

### Fase 2: Servicio de Consultas
1. Implementar DatabaseQueryService
2. Crear métodos para consultas complejas
3. Añadir análisis y estadísticas
4. Tests de servicio

### Fase 3: Tool Agno
1. Crear DatabaseQueryTool para Agno
2. Implementar parser de comandos
3. Integrar con servicio de consultas
4. Documentación de comandos

### Fase 4: Integración y Testing
1. Integrar tool en ToolsManager
2. Tests de integración completos
3. Validación con WebSocket
4. Documentación de usuario

## 🧪 Estrategia de Testing

### Unit Tests:
- Modelos SQLAlchemy con in-memory DB
- Repositorios con datos de prueba
- Servicio con mocks

### Integration Tests:
- Tool con base de datos real
- WebSocket con consultas complejas
- Performance con datasets grandes

### Validation Tests:
- Queries en lenguaje natural
- Edge cases y errores
- Concurrencia y locks

## 📊 Métricas de Éxito

### Funcionalidad:
- ✅ Todas las consultas básicas funcionando
- ✅ Relaciones correctas entre entidades
- ✅ Parsing de lenguaje natural efectivo
- ✅ Performance < 100ms para consultas simples

### Integración:
- ✅ Tool registrado correctamente en Agno
- ✅ WebSocket responde con datos estruturados
- ✅ No hay conflictos con otros tools
- ✅ Logs y errores manejados correctamente

### Calidad:
- ✅ Cobertura de tests > 90%
- ✅ No memory leaks en consultas largas
- ✅ Documentación completa
- ✅ Código siguiendo patrones SOLID

## 🚀 Próximos Pasos

1. **Crear modelos SQLAlchemy** → Empezar con apps.py
2. **Implementar repositorio base** → Patrón repository establecido
3. **Servicio de consultas básicas** → CRUD operations
4. **Tool Agno mínimo viable** → Primeras consultas
5. **Integración WebSocket** → Testing en tiempo real
6. **Funcionalidades avanzadas** → Lenguaje natural y analytics

---

**Rama:** `feature/database-query-tool`  
**Estimación:** 2-3 días de desarrollo  
**Dependencias:** Sistema SOLID ya implementado, WebSocket funcional
