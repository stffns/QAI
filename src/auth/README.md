# Sistema OAuth Integrado para QA Intelligence

## 🚀 Resumen de la Implementación

Este módulo proporciona generación de tokens OAuth reales para pruebas de Gatling, completamente integrado con el esquema de base de datos del proyecto QA Intelligence.

### ✅ Lo que se implementó

1. **Migración completa de Scala a Python**
   - Análisis y conversión del código Scala original (`UserMap.scala`, `ClientIdMap.scala`, `OIDCAuthentication.scala`)
   - Implementación en Python con bibliotecas modernas (`jose`, `requests`, `sqlite3`)

2. **Integración con esquema QAI existente**
   - Tablas OAuth integradas con `app_environment_country_mappings`
   - Relaciones FK consistentes con `apps_master`, `environments_master`, `countries_master`
   - Preservación del diseño SOLID del proyecto QAI

3. **Base de datos con constraints y validaciones**
   - Constraints de integridad referencial
   - Validaciones de datos (email, teléfono, URLs)
   - Índices de performance optimizados

4. **Herramienta de generación de tokens**
   - API simple para el agente QA
   - Soporte para múltiples configuraciones
   - Tokens JWT reales con firma ES256

## 📁 Estructura de Archivos

```
src/auth/
├── migrations/
│   ├── create_oauth_integrated_tables.py    # Migración inicial (no usada)
│   └── integrate_existing_oauth_tables.py   # Migración de integración ✅
├── get_real_oauth_token.py                  # Implementación original ✅
├── get_real_oauth_token_integrated.py       # Versión integrada con BD ✅
├── qa_oauth_tool.py                         # Herramienta final para agente QA ✅
└── oauth_models_integrated.py               # Modelos SQLModel integrados ✅
```

## 🗄️ Esquema de Base de Datos

### Tablas Principales

#### `oauth_users`

```sql
CREATE TABLE oauth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    given_name VARCHAR(100) NOT NULL,
    family_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    gender VARCHAR(10) NOT NULL,
    password_hash VARCHAR NOT NULL,
    mapping_id INTEGER NOT NULL REFERENCES app_environment_country_mappings(id),
    is_active BOOLEAN DEFAULT 1,
    test_purpose VARCHAR,
    locale VARCHAR(10) DEFAULT 'en-US',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `oauth_jwks`

```sql
CREATE TABLE oauth_jwks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    environment_id INTEGER NOT NULL REFERENCES environments_master(id),
    key_id VARCHAR(100) NOT NULL UNIQUE,
    jwk_content TEXT NOT NULL,
    algorithm VARCHAR(10) DEFAULT 'ES256',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `oauth_app_clients`

```sql
CREATE TABLE oauth_app_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES apps_master(id),
    environment_id INTEGER NOT NULL REFERENCES environments_master(id),
    client_id VARCHAR(255) NOT NULL UNIQUE,
    client_name VARCHAR(100) NOT NULL,
    callback_url VARCHAR(500) NOT NULL,
    resource_url VARCHAR(500),
    needs_resource_param BOOLEAN DEFAULT 0,
    default_scopes VARCHAR(200) DEFAULT 'openid profile email',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Relaciones FK

- `oauth_users.mapping_id` → `app_environment_country_mappings.id`
- `oauth_jwks.environment_id` → `environments_master.id`
- `oauth_app_clients.application_id` → `apps_master.id`
- `oauth_app_clients.environment_id` → `environments_master.id`

## 🛠️ Uso

### 1. Ejecutar Migración (solo primera vez)

```bash
python src/auth/migrations/integrate_existing_oauth_tables.py
```

### 2. Listar Configuraciones Disponibles

```bash
python src/auth/qa_oauth_tool.py --list
```

Salida esperada:

```
📋 CONFIGURACIONES OAUTH DISPONIBLES
==================================================
✅ CONFIGURACIONES COMPLETAS:
   EVA STA RO - EVA | Staging | Romania

⚠️  CONFIGURACIONES INCOMPLETAS:
   SCIK PRO US - Faltan: usuarios, JWKs
```

### 3. Generar Token OAuth

```bash
python src/auth/qa_oauth_tool.py EVA STA RO
```

Salida esperada:

```
🎉 TOKEN OAUTH GENERADO EXITOSAMENTE
============================================================
Access Token: eyJhbGciOiJFUzI1NiIs...
Token Type: Bearer
Expires In: 3600 segundos
Scope: openid profile email phone
Generated At: 2025-01-11T14:27:08+00:00

📊 Configuración:
   App: EVA
   Environment: STA
   Country: RO
   User: qa.auto.soco.ro+2@gmail.com
   Client ID: 84d70f23-df50...
```

### 4. Integración con Agente QA

```python
from src.auth.qa_oauth_tool import QAOAuthTool

# Inicializar herramienta
oauth_tool = QAOAuthTool()

# Listar configuraciones
configs = oauth_tool.list_configurations()
print(f"Configuraciones disponibles: {len(configs)}")

# Generar token
result = oauth_tool.get_token("EVA", "STA", "RO")

if result['success']:
    token = result['access_token']
    print(f"Token generado: {token[:30]}...")
else:
    print(f"Error: {result['error']}")
```

## 🔧 Configuración de Datos

### Datos de Ejemplo Incluidos

La migración automáticamente inserta:

1. **JWK para STA** (SCIK-QA-STA-20210408-47QNY)
2. **Client OAuth para EVA STA** (84d70f23-df50-4ed2-9d60-263366326c9d)
3. **Usuario de prueba** (<qa.auto.soco.ro+2@gmail.com>)

### Agregar Nuevas Configuraciones

#### 1. Agregar Usuario OAuth

```sql
INSERT INTO oauth_users (
    email, given_name, family_name, phone_number, gender, 
    password_hash, mapping_id, locale
) VALUES (
    'test.user@example.com',
    'Test',
    'User',
    '+1234567890',
    'male',
    'password_hash_here',
    1,  -- mapping_id válido
    'en-US'
);
```

#### 2. Agregar JWK para Nuevo Ambiente

```sql
INSERT INTO oauth_jwks (
    environment_id, key_id, jwk_content, algorithm
) VALUES (
    2,  -- environment_id para PRO
    'SCIK-QA-PRO-20240101-ABCD',
    '{"kty":"EC","crv":"P-256","x":"...","y":"...","d":"..."}',
    'ES256'
);
```

#### 3. Agregar Client OAuth

```sql
INSERT INTO oauth_app_clients (
    application_id, environment_id, client_id, client_name, callback_url
) VALUES (
    1,  -- application_id para EVA
    2,  -- environment_id para PRO
    'client-id-here',
    'EVA PRO Client',
    'http://localhost/callback'
);
```

## 🔍 Validación y Testing

### Verificar Integridad de Base de Datos

```sql
-- Verificar usuarios con mappings completos
SELECT 
    ou.email,
    am.app_code,
    em.env_code,
    cm.country_code
FROM oauth_users ou
JOIN app_environment_country_mappings aecm ON ou.mapping_id = aecm.id
JOIN apps_master am ON aecm.application_id = am.id
JOIN environments_master em ON aecm.environment_id = em.id
JOIN countries_master cm ON aecm.country_id = cm.id;

-- Verificar configuraciones completas
SELECT 
    am.app_code,
    em.env_code,
    cm.country_code,
    COUNT(DISTINCT ou.id) as users,
    COUNT(DISTINCT oj.id) as jwks,
    COUNT(DISTINCT oac.id) as clients
FROM app_environment_country_mappings aecm
JOIN apps_master am ON aecm.application_id = am.id
JOIN environments_master em ON aecm.environment_id = em.id
JOIN countries_master cm ON aecm.country_id = cm.id
LEFT JOIN oauth_users ou ON ou.mapping_id = aecm.id AND ou.is_active = 1
LEFT JOIN oauth_jwks oj ON oj.environment_id = em.id AND oj.is_active = 1
LEFT JOIN oauth_app_clients oac ON oac.application_id = am.id 
    AND oac.environment_id = em.id AND oac.is_active = 1
GROUP BY am.id, em.id, cm.id
HAVING users > 0 AND jwks > 0 AND clients > 0;
```

### Test de Token JWT

```python
import json
import base64

def decode_jwt_payload(token):
    """Decodificar payload JWT sin verificar firma"""
    parts = token.split('.')
    payload_encoded = parts[1]
    
    # Agregar padding si es necesario
    payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_padded)
    
    return json.loads(payload_bytes.decode())

# Usar con token generado
token = "eyJhbGciOiJFUzI1NiIs..."
payload = decode_jwt_payload(token)
print(json.dumps(payload, indent=2))
```

## 🚨 Troubleshooting

### Error: Configuration not found

**Problema**: `Configuration not found: EVA STA RO`

**Solución**:

1. Verificar que existe el mapping: `SELECT * FROM app_environment_country_mappings WHERE ...`
2. Ejecutar migración si es necesario: `python src/auth/migrations/integrate_existing_oauth_tables.py`

### Error: Incomplete configuration

**Problema**: `Incomplete configuration, missing: oauth_user`

**Solución**:

1. Listar configuraciones: `python src/auth/qa_oauth_tool.py --list`
2. Agregar componentes faltantes (usuario, JWK, client) según sección "Agregar Nuevas Configuraciones"

### Error: Database not found

**Problema**: `QAI Database not found: data/qa_intelligence.db`

**Solución**:

1. Verificar ruta de trabajo: `pwd` debe ser el directorio raíz del proyecto QAI
2. Verificar que existe la base de datos: `ls -la data/qa_intelligence.db`

## 🎯 Integración con Gatling

### Ejemplo de Uso en Tests Gatling

```scala
// En tu escenario Gatling, usar el token generado
val httpProtocol = http
  .baseUrl("https://api.example.com")
  .authorizationHeader("Bearer " + generatedToken)

val scn = scenario("OAuth Test")
  .exec(
    http("Authenticated Request")
      .get("/api/protected-resource")
      .check(status.is(200))
  )
```

### Script Python para Gatling

```python
#!/usr/bin/env python3
"""
Generar tokens OAuth para tests Gatling
"""
import sys
from src.auth.qa_oauth_tool import QAOAuthTool

def main():
    if len(sys.argv) != 4:
        print("Uso: python generate_oauth_tokens.py APP ENV COUNTRY")
        sys.exit(1)
    
    app, env, country = sys.argv[1:4]
    
    tool = QAOAuthTool()
    result = tool.get_token(app, env, country)
    
    if result['success']:
        # Solo imprimir el token para usar en Gatling
        print(result['access_token'])
    else:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📋 Estado del Proyecto

### ✅ Completado

- [x] Análisis y migración del código Scala original
- [x] Integración con esquema QAI existente
- [x] Base de datos con constraints y FK
- [x] Herramienta de generación de tokens
- [x] API para integración con agente QA
- [x] Documentación completa
- [x] Testing y validación

### 🎯 Resultado Final

**Configuración EVA STA RO completamente funcional:**

- ✅ Usuario OAuth: `qa.auto.soco.ro+2@gmail.com`
- ✅ JWK activo: `SCIK-QA-STA-20210408-47QNY`
- ✅ Client OAuth: `84d70f23-df50-4ed2-9d60-263366326c9d`
- ✅ Token generado: `eyJhbGciOiJFUzI1NiIs...` (JWT válido con firma ES256)

### 🔄 Próximos Pasos

1. **Extender configuraciones**: Agregar más combinaciones app/env/country según necesidades
2. **Integrar con agente QA**: Usar `QAOAuthTool` como herramienta del agente
3. **Optimizar Gatling**: Implementar generación de tokens en tiempo real para tests
4. **Monitoreo**: Agregar métricas y logging para tokens generados

---

**Autor**: QA Intelligence Team  
**Fecha**: Enero 2025  
**Versión**: 1.0.0
