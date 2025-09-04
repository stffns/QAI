# Variables de Entorno para QA Intelligence

QA Intelligence ahora soporta la configuración completa a través de variables de entorno definidas en el archivo `.env`. Este documento describe todas las variables disponibles.

## 📋 Variables Principales

### 🤖 Configuración del Modelo

```bash
# Proveedor del modelo (openai, azure, deepseek)
MODEL_PROVIDER=openai

# ID/nombre del modelo
MODEL_ID=gpt-4o-mini

# Temperatura del modelo (0.0 - 2.0)
MODEL_TEMPERATURE=0.7

# Timeout en segundos
MODEL_TIMEOUT=30

# Máximo de tokens (opcional)
MODEL_MAX_TOKENS=4000

# Semilla para respuestas determinísticas (opcional)
MODEL_SEED=42

# URL base personalizada (opcional)
MODEL_BASE_URL=https://api.openai.com/v1

# Formato de respuesta (opcional)
MODEL_RESPONSE_FORMAT=json
```

### 🔑 API Keys

El sistema detecta automáticamente las API keys basándose en el proveedor:

```bash
# Para OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_ORGANIZATION=org-...  # Opcional
OPENAI_PROJECT=proj_...      # Opcional

# Para DeepSeek
DEEPSEEK_API_KEY=sk-...

# Para Azure OpenAI
AZURE_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### 💾 Configuración de Base de Datos

```bash
# URL principal de la base de datos
DB_URL=sqlite:///./data/qa_intelligence.db

# Rutas específicas de bases de datos
QA_AGENT_DB_PATH=data/qa_conversations.db
QA_RAG_DB_PATH=data/qa_intelligence_rag.db
QA_KNOWLEDGE_DB_PATH=data/qa_knowledge.db

# Configuración avanzada de la base de datos
DB_ECHO=false                # Habilitar logging de SQL
DB_POOL_SIZE=20             # Tamaño del pool de conexiones
DB_MAX_OVERFLOW=30          # Máximo overflow de conexiones
```

### 🌍 Configuración de la Aplicación

```bash
# Entorno de ejecución
ENVIRONMENT=development      # development, staging, production

# Configuración de logging
LOG_LEVEL=DEBUG             # DEBUG, INFO, WARNING, ERROR
DEBUG=true                  # Habilitar modo debug

# Directorio de datos
QA_DATA_DIR=data
```

### 🌐 Configuración WebSocket

```bash
# Habilitar servidor WebSocket
WEBSOCKET_ENABLED=false
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
WEBSOCKET_SECRET_KEY=your-secret-key
WEBSOCKET_MAX_CONNECTIONS=100
```

## 📚 Prioridad de Configuración

QA Intelligence carga la configuración en el siguiente orden de prioridad:

1. **Variables de entorno** (mayor prioridad)
2. **Archivo .env**
3. **Archivo agent_config.yaml**
4. **Valores por defecto** (menor prioridad)

## 🧪 Verificar Configuración

Puedes verificar que las variables de entorno se cargan correctamente:

```bash
# Ejecutar script de pruebas
python test_env_loading.py

# Verificar configuración actual
python -c "
from config import get_settings
settings = get_settings()
print('Model:', settings.model.provider, settings.model.id)
print('Database:', settings.database.url)
print('API Key configured:', bool(settings.model.api_key))
"
```

## 🔧 Ejemplos de Uso

### Configuración para Desarrollo

```bash
# .env para desarrollo
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
MODEL_PROVIDER=openai
MODEL_ID=gpt-4o-mini
MODEL_TEMPERATURE=0.7
OPENAI_API_KEY=sk-proj-...
```

### Configuración para Producción

```bash
# .env para producción
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
MODEL_PROVIDER=azure
MODEL_ID=gpt-4
MODEL_TEMPERATURE=0.3
AZURE_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4
DB_URL=postgresql://user:pass@localhost:5432/qa_intelligence
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

### Cambiar Proveedor a DeepSeek

```bash
# Configuración para DeepSeek
MODEL_PROVIDER=deepseek
MODEL_ID=deepseek-chat
DEEPSEEK_API_KEY=sk-...
MODEL_TEMPERATURE=0.7
```

## 🚀 Aplicar Cambios

Los cambios en el archivo `.env` se aplican automáticamente al reiniciar la aplicación:

```bash
# Reiniciar el agente
python run_qa_agent.py

# Reiniciar el servidor WebSocket
python src/websocket/server.py
```

## 🔒 Seguridad

- **Nunca** commitees el archivo `.env` con API keys reales al repositorio
- Usa diferentes archivos `.env` para cada entorno (desarrollo, staging, producción)
- Considera usar un gestor de secretos para producción
- Rota las API keys regularmente

## 📝 Notas

- Las variables de entorno siempre tienen prioridad sobre los archivos de configuración
- Si una variable no está definida, se usará el valor por defecto
- Las API keys se detectan automáticamente basándose en el proveedor configurado
- Los directorios de base de datos se crean automáticamente si no existen
