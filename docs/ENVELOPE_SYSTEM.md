# WebSocket Envelope System - Implementación Completa

## 🎯 Resumen del Sistema de Envelope Común

Hemos implementado exitosamente un **sistema de envelope común con uniones discriminadas** para el protocolo WebSocket de QA Intelligence. Este sistema utiliza campos estándares y payload tipado para comunicación robusta y type-safe.

## 📦 Estructura del Envelope

### Campos Estándares
```json
{
  "type": "chat_message",           // MessageType enum - discriminador
  "version": "2.0",                 // ProtocolVersion enum
  "id": "uuid-string",              // Identificador único del mensaje
  "ts": 1756913803742,              // Timestamp Unix en milisegundos
  "payload": { ... },               // Payload tipado por unión discriminada
  "session_id": "session_123",      // ID de sesión (opcional)
  "user_id": "user_456",            // ID de usuario (opcional)  
  "correlation_id": "parent-msg-id" // ID de correlación (opcional)
}
```

### Campos del Envelope
- **`type`**: Enum `MessageType` que actúa como discriminador para el payload
- **`version`**: Enum `ProtocolVersion` para compatibilidad multi-versión
- **`id`**: UUID único generado automáticamente para cada mensaje
- **`ts`**: Timestamp Unix en milisegundos para ordenamiento temporal
- **`payload`**: Contenido tipado usando uniones discriminadas
- **`session_id`**: Identificador de sesión para contexto
- **`user_id`**: Identificador de usuario para autorización
- **`correlation_id`**: Para trazabilidad de request/response

## 🏗️ Payloads con Uniones Discriminadas

### Tipos de Payload Soportados

#### 1. ChatMessagePayload
```python
{
  "message_type": "chat_message",
  "content": "Hello, this is a test message",
  "attachments": [...],           # Opcional
  "metadata": {"client": "web"}   # Opcional
}
```

#### 2. AgentResponsePayload
```python
{
  "message_type": "agent_response",
  "content": "This is the agent's response",
  "response_type": "text",         # text, markdown, json, etc.
  "tools_used": ["web_search"],    # Opcional
  "execution_time": 1.5,           # Opcional
  "confidence": 0.95,              # Opcional [0.0-1.0]
  "metadata": {...}                # Opcional
}
```

#### 3. SystemEventPayload
```python
{
  "message_type": "system_event",
  "event_name": "connection_established",
  "description": "User connected successfully",    # Opcional
  "severity": "info",              # info, warning, error, critical
  "data": {...}                    # Opcional
}
```

#### 4. ErrorEventPayload
```python
{
  "message_type": "error_event",
  "error_code": "VALIDATION_ERROR",
  "error_message": "Invalid input format",
  "details": "...",                # Opcional
  "stack_trace": "...",            # Opcional
  "retry_count": 0                 # Contador de reintentos
}
```

#### 5. ConnectionEventPayload
```python
{
  "message_type": "connection_event",
  "event_type": "connected",       # connected, disconnected, reconnected
  "client_info": {...},            # Opcional
  "session_data": {...}            # Opcional
}
```

#### 6. HealthCheckPayload
```python
{
  "message_type": "health_check",
  "status": "ping",                # ping, pong
  "timestamp": 1756913803.742,
  "metrics": {...}                 # Opcional
}
```

## 🔧 Factory Pattern para Creación

### WebSocketEnvelopeFactory

```python
# Crear mensaje de chat
envelope = WebSocketEnvelopeFactory.create_chat_message(
    content="Hello World",
    session_id="sess_123",
    user_id="user_456",
    metadata={"client": "web"}
)

# Crear respuesta del agente
envelope = WebSocketEnvelopeFactory.create_agent_response(
    content="Response from QA Agent",
    tools_used=["web_search", "calculator"],
    execution_time=2.1,
    confidence=0.95,
    correlation_id="original_message_id"
)

# Crear evento de error
envelope = WebSocketEnvelopeFactory.create_error_event(
    error_code="TIMEOUT",
    error_message="Request timed out",
    retry_count=1,
    correlation_id="failed_request_id"
)
```

## 🔍 Type Safety con Pydantic V2

### Validación Automática
- **Campos requeridos**: Validación de presencia
- **Tipos de datos**: Validación de tipos estricta
- **Rangos**: Validación de rangos (ej: confidence 0.0-1.0)
- **Formatos**: Validación de formatos (ej: UUID, timestamp)
- **Enums**: Validación de valores permitidos

### Uniones Discriminadas
```python
# El campo 'message_type' actúa como discriminador
WebSocketPayload = Union[
    ChatMessagePayload,      # message_type: "chat_message"
    AgentResponsePayload,    # message_type: "agent_response"
    SystemEventPayload,      # message_type: "system_event"
    ErrorEventPayload,       # message_type: "error_event"
    ConnectionEventPayload,  # message_type: "connection_event"
    HealthCheckPayload       # message_type: "health_check"
]
```

## 📥 Parsing y Serialización

### Métodos de Parsing
```python
# Desde JSON string
envelope = WebSocketEnvelope.parse_envelope(json_string)

# Desde diccionario
envelope = parse_websocket_envelope(data_dict)

# Con manejo de errores
try:
    envelope = WebSocketEnvelope.model_validate_json(json_data)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Serialización
```python
# A JSON string
json_data = envelope.to_json()

# A diccionario
dict_data = envelope.model_dump()
```

## 🚀 Integración con Middleware

### Nuevo Método de Procesamiento
```python
# Parsing y procesamiento de envelope
processed_envelope = await middleware.parse_and_process_envelope(
    websocket=websocket,
    raw_message=json_message,
    session_id="session_123", 
    user_id="user_456"
)

# Procesamiento directo de envelope
result = await middleware.process_envelope(
    websocket=websocket,
    envelope=parsed_envelope,
    session_id="session_123",
    user_id="user_456"
)
```

### Validaciones del Middleware
- **Validación de contexto**: session_id y user_id matching
- **Versión del protocolo**: Compatibilidad multi-versión
- **Estructura del envelope**: Validación de payload presente
- **Logging estructurado**: Trazabilidad completa
- **Manejo de errores**: Logging detallado de fallos

## 🔄 Compatibilidad hacia Atrás

### Aliases para Código Existente
```python
# Aliases para compatibilidad
WebSocketEvent = WebSocketEnvelope
parse_websocket_event = parse_websocket_envelope

# Factory methods de compatibilidad
create_chat_message() -> WebSocketEnvelope
create_agent_response() -> WebSocketEnvelope  
create_error_event() -> WebSocketEnvelope
```

### Conversión desde Formato Legacy
```python
# Converter eventos legacy a envelope
envelope = create_envelope_from_legacy_event(
    event_type="chat_message",
    event_data=legacy_data
)
```

## 📊 Ejemplo de Uso Completo

```python
# 1. Crear envelope de chat
chat_envelope = WebSocketEnvelopeFactory.create_chat_message(
    content="¿Cuál es el weather today?",
    session_id="sess_abc123",
    user_id="user_xyz789",
    metadata={"source": "web_client"}
)

# 2. Serializar para envío
message_json = chat_envelope.to_json()

# 3. En el receptor, parsing
received_envelope = WebSocketEnvelope.parse_envelope(message_json)

# 4. Type-safe access
if received_envelope.is_chat_message():
    chat_payload = received_envelope.payload
    print(f"User message: {chat_payload.content}")

# 5. Crear respuesta correlacionada
response_envelope = WebSocketEnvelopeFactory.create_agent_response(
    content="Today's weather is sunny, 25°C",
    tools_used=["weather_api"],
    execution_time=1.2,
    confidence=0.98,
    correlation_id=received_envelope.id,  # Correlación
    session_id=received_envelope.session_id,
    user_id=received_envelope.user_id
)
```

## ✅ Beneficios del Sistema

### 1. **Type Safety Completa**
- Validación en tiempo de compilación y ejecución
- IntelliSense y autocompletado mejorado
- Detección temprana de errores

### 2. **Protocolo Estándar**
- Campos comunes bien definidos (type, version, id, ts)
- Estructura predecible para todos los mensajes
- Trazabilidad completa con correlation_id

### 3. **Extensibilidad**
- Fácil adición de nuevos tipos de payload
- Versionado del protocolo
- Compatibilidad hacia atrás

### 4. **Robustez**
- Validación automática de datos
- Manejo de errores estructurado
- Logging detallado para debugging

### 5. **Performance**
- Parsing eficiente con Pydantic V2
- Serialización optimizada
- Type hints para optimizaciones del runtime

## 🎯 Estado de Implementación

✅ **COMPLETADO:**
- Envelope común con campos estándares (type, version, id, ts)
- Payloads tipados con uniones discriminadas
- Factory pattern para creación
- Parsing y validación automática
- Integración con middleware
- Compatibilidad hacia atrás
- Pydantic V2 con field_validator
- Documentación completa

🚀 **SISTEMA PRODUCTION-READY**

El nuevo sistema de envelope está completamente implementado y listo para uso en producción, proporcionando un protocolo WebSocket robusto, type-safe y extensible para QA Intelligence.
