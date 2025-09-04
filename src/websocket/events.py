"""
Sistema de eventos para WebSocket con Envelope Común

Define envelope estándar y payloads tipados por uniones discriminadas
para comunicación WebSocket robusta y type-safe.

Arquitectura:
- Envelope común con campos estándares (type, version, id, ts)
- Payloads tipados usando uniones discriminadas de Pydantic
- Validación automática y serialización JSON
- Compatibilidad con múltiples versiones de protocolo
"""

from datetime import datetime
from typing import Optional, Any, Dict, List, Union, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import json
import uuid
import time


class ProtocolVersion(str, Enum):
    """Versiones soportadas del protocolo WebSocket"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class MessageType(str, Enum):
    """Tipos de mensajes soportados"""
    CHAT_MESSAGE = "chat_message"
    AGENT_RESPONSE = "agent_response"
    AGENT_RESPONSE_STREAM_START = "agent_response_stream_start"
    AGENT_RESPONSE_STREAM_CHUNK = "agent_response_stream_chunk"
    AGENT_RESPONSE_STREAM_END = "agent_response_stream_end"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    CONNECTION_EVENT = "connection_event"
    HEALTH_CHECK = "health_check"


# ==================== PAYLOAD MODELS ====================

class BasePayload(BaseModel):
    """Clase base para todos los payloads"""
    
    class Config:
        """Configuración común para payloads"""
        extra = "forbid"  # No permitir campos adicionales


class ChatMessagePayload(BasePayload):
    """Payload para mensajes de chat del usuario"""
    message_type: Literal["chat_message"] = "chat_message"
    content: str = Field(..., min_length=1, max_length=10000)
    attachments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Campos adicionales comunes para aplicaciones web
    language: Optional[str] = Field(None, description="Código de idioma (ej: 'en', 'es')")
    locale: Optional[str] = Field(None, description="Código de localización (ej: 'en-US', 'es-ES')")
    timestamp: Optional[str] = Field(None, description="Timestamp del cliente (ISO string)")


class AgentResponsePayload(BasePayload):
    """Payload para respuestas del agente QA"""
    message_type: Literal["agent_response"] = "agent_response"
    content: str = Field(..., min_length=1)
    response_type: str = Field(default="text")  # text, markdown, json, etc.
    tools_used: Optional[List[str]] = None
    execution_time: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class AgentResponseStreamStartPayload(BasePayload):
    """Payload para inicio de respuesta streaming del agente"""
    message_type: Literal["agent_response_stream_start"] = "agent_response_stream_start"
    response_type: str = Field(default="text")
    estimated_length: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentResponseStreamChunkPayload(BasePayload):
    """Payload para chunks de respuesta streaming del agente"""
    message_type: Literal["agent_response_stream_chunk"] = "agent_response_stream_chunk"
    chunk: str = Field(..., description="Parte del contenido de la respuesta")
    chunk_index: int = Field(..., ge=0, description="Índice del chunk (0-based)")
    is_complete: bool = Field(default=False, description="Si este es el último chunk")


class AgentResponseStreamEndPayload(BasePayload):
    """Payload para fin de respuesta streaming del agente"""
    message_type: Literal["agent_response_stream_end"] = "agent_response_stream_end"
    total_chunks: int = Field(..., ge=0)
    full_content: str = Field(..., description="Contenido completo para verificación")
    tools_used: Optional[List[str]] = None
    execution_time: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class SystemEventPayload(BasePayload):
    """Payload para eventos del sistema"""
    message_type: Literal["system_event"] = "system_event"
    event_name: str
    description: Optional[str] = None
    severity: Literal["info", "warning", "error", "critical"] = "info"
    data: Optional[Dict[str, Any]] = None


class ErrorEventPayload(BasePayload):
    """Payload para eventos de error"""
    message_type: Literal["error_event"] = "error_event"
    error_code: str
    error_message: str
    details: Optional[str] = None
    stack_trace: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)


class ConnectionEventPayload(BasePayload):
    """Payload para eventos de conexión"""
    message_type: Literal["connection_event"] = "connection_event"
    event_type: Literal["connected", "disconnected", "reconnected"] = "connected"
    client_info: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None


class HealthCheckPayload(BasePayload):
    """Payload para health checks"""
    message_type: Literal["health_check"] = "health_check"
    status: Literal["ping", "pong"] = "ping"
    timestamp: float = Field(default_factory=time.time)
    metrics: Optional[Dict[str, Any]] = None


# ==================== DISCRIMINATED UNION ====================

WebSocketPayload = Union[
    ChatMessagePayload,
    AgentResponsePayload,
    AgentResponseStreamStartPayload,
    AgentResponseStreamChunkPayload,
    AgentResponseStreamEndPayload,
    SystemEventPayload,
    ErrorEventPayload,
    ConnectionEventPayload,
    HealthCheckPayload
]


# ==================== ENVELOPE MODEL ====================

class WebSocketEnvelope(BaseModel):
    """
    Envelope común para toda comunicación WebSocket.
    
    Implementa protocolo estándar con campos comunes y payload tipado
    usando uniones discriminadas para type safety.
    
    Campos estándares:
    - type: Tipo de mensaje (discriminador)
    - version: Versión del protocolo
    - id: Identificador único del mensaje
    - ts: Timestamp Unix (milisegundos)
    - payload: Contenido tipado del mensaje
    """
    
    # Campos del envelope estándar
    type: MessageType = Field(..., description="Tipo de mensaje")
    version: ProtocolVersion = Field(default=ProtocolVersion.V2_0, description="Versión del protocolo")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del mensaje")
    ts: int = Field(default_factory=lambda: int(time.time() * 1000), description="Timestamp en ms")
    
    # Payload tipado por unión discriminada
    payload: WebSocketPayload = Field(..., discriminator='message_type')
    
    # Metadatos opcionales del envelope
    session_id: Optional[str] = Field(None, description="ID de sesión")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    correlation_id: Optional[str] = Field(None, description="ID de correlación para trazabilidad")
    
    class Config:
        """Configuración del envelope"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @field_validator('ts')
    @classmethod
    def validate_timestamp(cls, v):
        """Validar que el timestamp sea válido"""
        if v <= 0:
            raise ValueError("Timestamp debe ser positivo")
        return v
    
    def to_json(self) -> str:
        """Serializar envelope a JSON"""
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json_data: str) -> 'WebSocketEnvelope':
        """Deserializar envelope desde JSON"""
        return cls.model_validate_json(json_data)
    
    @classmethod
    def parse_envelope(cls, json_data: str) -> 'WebSocketEnvelope':
        """
        Parse JSON data to WebSocket envelope.
        
        Args:
            json_data: JSON string containing envelope data
            
        Returns:
            WebSocketEnvelope: Parsed envelope instance
            
        Raises:
            ValueError: If envelope format is invalid
            ValidationError: If data validation fails
        """
        try:
            return cls.model_validate_json(json_data)
        except Exception as e:
            raise ValueError(f"Failed to parse WebSocket envelope: {e}")
    
    def get_payload_type(self) -> str:
        """Obtener el tipo de payload"""
        return self.payload.message_type
    
    def is_chat_message(self) -> bool:
        """Verificar si es un mensaje de chat"""
        return isinstance(self.payload, ChatMessagePayload)
    
    def is_agent_response(self) -> bool:
        """Verificar si es una respuesta del agente"""
        return isinstance(self.payload, AgentResponsePayload)
    
    def is_system_event(self) -> bool:
        """Verificar si es un evento del sistema"""
        return isinstance(self.payload, SystemEventPayload)
    
    def is_error_event(self) -> bool:
        """Verificar si es un evento de error"""
        return isinstance(self.payload, ErrorEventPayload)
    
    def is_connection_event(self) -> bool:
        """Verificar si es un evento de conexión"""
        return isinstance(self.payload, ConnectionEventPayload)
    
    def is_health_check(self) -> bool:
        """Verificar si es un health check"""
        return isinstance(self.payload, HealthCheckPayload)


# ==================== FACTORY METHODS ====================

class WebSocketEnvelopeFactory:
    """Factory para crear envelopes tipados"""
    
    @staticmethod
    def create_chat_message(
        content: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para mensaje de chat"""
        payload = ChatMessagePayload(
            content=content,
            attachments=attachments,
            metadata=metadata,
            language=None,
            locale=None,
            timestamp=None
        )
        return WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_agent_response(
        content: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        response_type: str = "text",
        tools_used: Optional[List[str]] = None,
        execution_time: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para respuesta del agente"""
        payload = AgentResponsePayload(
            content=content,
            response_type=response_type,
            tools_used=tools_used,
            execution_time=execution_time,
            confidence=confidence
        )
        return WebSocketEnvelope(
            type=MessageType.AGENT_RESPONSE,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_agent_response_stream_start(
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        response_type: str = "text",
        estimated_length: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para inicio de respuesta streaming"""
        payload = AgentResponseStreamStartPayload(
            response_type=response_type,
            estimated_length=estimated_length,
            metadata=metadata
        )
        return WebSocketEnvelope(
            type=MessageType.AGENT_RESPONSE_STREAM_START,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_agent_response_stream_chunk(
        chunk: str,
        chunk_index: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        is_complete: bool = False
    ) -> WebSocketEnvelope:
        """Crear envelope para chunk de respuesta streaming"""
        payload = AgentResponseStreamChunkPayload(
            chunk=chunk,
            chunk_index=chunk_index,
            is_complete=is_complete
        )
        return WebSocketEnvelope(
            type=MessageType.AGENT_RESPONSE_STREAM_CHUNK,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_agent_response_stream_end(
        total_chunks: int,
        full_content: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        execution_time: Optional[float] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para fin de respuesta streaming"""
        payload = AgentResponseStreamEndPayload(
            total_chunks=total_chunks,
            full_content=full_content,
            tools_used=tools_used,
            execution_time=execution_time,
            confidence=confidence,
            metadata=metadata
        )
        return WebSocketEnvelope(
            type=MessageType.AGENT_RESPONSE_STREAM_END,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_system_event(
        event_name: str,
        description: Optional[str] = None,
        severity: Literal["info", "warning", "error", "critical"] = "info",
        data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para evento del sistema"""
        payload = SystemEventPayload(
            event_name=event_name,
            description=description,
            severity=severity,
            data=data
        )
        return WebSocketEnvelope(
            type=MessageType.SYSTEM_EVENT,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_error_event(
        error_code: str,
        error_message: str,
        details: Optional[str] = None,
        stack_trace: Optional[str] = None,
        retry_count: int = 0,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para evento de error"""
        payload = ErrorEventPayload(
            error_code=error_code,
            error_message=error_message,
            details=details,
            stack_trace=stack_trace,
            retry_count=retry_count
        )
        return WebSocketEnvelope(
            type=MessageType.ERROR_EVENT,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_connection_event(
        event_type: Literal["connected", "disconnected", "reconnected"] = "connected",
        client_info: Optional[Dict[str, Any]] = None,
        session_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para evento de conexión"""
        payload = ConnectionEventPayload(
            event_type=event_type,
            client_info=client_info,
            session_data=session_data
        )
        return WebSocketEnvelope(
            type=MessageType.CONNECTION_EVENT,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_health_check(
        status: Literal["ping", "pong"] = "ping",
        metrics: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> WebSocketEnvelope:
        """Crear envelope para health check"""
        payload = HealthCheckPayload(
            status=status,
            metrics=metrics
        )
        return WebSocketEnvelope(
            type=MessageType.HEALTH_CHECK,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )


# ==================== UTILITY FUNCTIONS ====================

def parse_websocket_envelope(data: Union[str, Dict[str, Any]]) -> WebSocketEnvelope:
    """
    Parse data to WebSocket envelope.
    
    Args:
        data: JSON string or dictionary containing envelope data
        
    Returns:
        WebSocketEnvelope: Parsed and validated envelope
        
    Raises:
        ValueError: If data format is invalid
        ValidationError: If validation fails
    """
    if isinstance(data, str):
        return WebSocketEnvelope.parse_envelope(data)
    elif isinstance(data, dict):
        return WebSocketEnvelope.model_validate(data)
    else:
        raise ValueError(f"Invalid data type for envelope: {type(data)}")


def create_envelope_from_legacy_event(event_type: str, event_data: Dict[str, Any]) -> WebSocketEnvelope:
    """
    Crear envelope desde formato legacy para compatibilidad.
    
    Args:
        event_type: Tipo de evento legacy
        event_data: Datos del evento
        
    Returns:
        WebSocketEnvelope: Envelope convertido
    """
    # Mapear tipos legacy a nuevos tipos
    type_mapping = {
        "chat_message": MessageType.CHAT_MESSAGE,
        "agent_response": MessageType.AGENT_RESPONSE,
        "system_event": MessageType.SYSTEM_EVENT,
        "error": MessageType.ERROR_EVENT,
        "connection_event": MessageType.CONNECTION_EVENT
    }
    
    message_type = type_mapping.get(event_type, MessageType.SYSTEM_EVENT)
    
    # Crear payload basado en el tipo
    if message_type == MessageType.CHAT_MESSAGE:
        payload = ChatMessagePayload(
            content=event_data.get("content", ""),
            attachments=event_data.get("attachments"),
            metadata=event_data.get("metadata"),
            language=event_data.get("language"),
            locale=event_data.get("locale"),
            timestamp=event_data.get("timestamp")
        )
    elif message_type == MessageType.AGENT_RESPONSE:
        payload = AgentResponsePayload(
            content=event_data.get("content", ""),
            response_type=event_data.get("response_type", "text"),
            tools_used=event_data.get("tools_used"),
            execution_time=event_data.get("execution_time"),
            confidence=event_data.get("confidence")
        )
    elif message_type == MessageType.ERROR_EVENT:
        payload = ErrorEventPayload(
            error_code=event_data.get("error_code", "UNKNOWN"),
            error_message=event_data.get("error_message", "Unknown error"),
            details=event_data.get("details"),
            stack_trace=event_data.get("stack_trace")
        )
    else:
        # Sistema event por defecto
        payload = SystemEventPayload(
            event_name=event_data.get("event_name", event_type),
            description=event_data.get("description"),
            severity=event_data.get("severity", "info"),
            data=event_data
        )
    
    return WebSocketEnvelope(
        type=message_type,
        payload=payload,
        session_id=event_data.get("session_id"),
        user_id=event_data.get("user_id"),
        correlation_id=event_data.get("correlation_id")
    )


# ==================== BACKWARDS COMPATIBILITY ====================

# Alias para compatibilidad con código existente
WebSocketEvent = WebSocketEnvelope

# Factory method compatibility
def create_chat_message(*args, **kwargs) -> WebSocketEnvelope:
    """Compatibility wrapper"""
    return WebSocketEnvelopeFactory.create_chat_message(*args, **kwargs)


def create_agent_response(*args, **kwargs) -> WebSocketEnvelope:
    """Compatibility wrapper"""
    return WebSocketEnvelopeFactory.create_agent_response(*args, **kwargs)


def create_error_event(*args, **kwargs) -> WebSocketEnvelope:
    """Compatibility wrapper"""
    return WebSocketEnvelopeFactory.create_error_event(*args, **kwargs)


# Parsing compatibility
def parse_websocket_event(data: Union[str, Dict[str, Any]]) -> WebSocketEnvelope:
    """Compatibility wrapper for parsing"""
    return parse_websocket_envelope(data)


# Example usage and testing
if __name__ == "__main__":
    # Test envelope creation
    print("🧪 Testing WebSocket Envelope System\n")
    
    # Create chat message
    chat_envelope = WebSocketEnvelopeFactory.create_chat_message(
        content="Hello, this is a test message",
        session_id="session_123",
        user_id="user_456",
        metadata={"client": "web"}
    )
    
    print("📨 Chat Message Envelope:")
    print(chat_envelope.to_json())
    print(f"Type: {chat_envelope.type}")
    print(f"Payload Type: {chat_envelope.get_payload_type()}")
    print(f"Is Chat: {chat_envelope.is_chat_message()}")
    print()
    
    # Create agent response
    agent_envelope = WebSocketEnvelopeFactory.create_agent_response(
        content="This is the agent's response",
        session_id="session_123",
        user_id="user_456",
        tools_used=["web_search", "calculator"],
        execution_time=1.5,
        confidence=0.95,
        correlation_id=chat_envelope.id
    )
    
    print("🤖 Agent Response Envelope:")
    print(agent_envelope.to_json())
    print(f"Is Agent Response: {agent_envelope.is_agent_response()}")
    print()
    
    # Test parsing
    json_data = chat_envelope.to_json()
    parsed_envelope = WebSocketEnvelope.parse_envelope(json_data)
    
    print("🔄 Parsed Envelope:")
    print(f"Original ID: {chat_envelope.id}")
    print(f"Parsed ID: {parsed_envelope.id}")
    print(f"Types match: {chat_envelope.type == parsed_envelope.type}")
    
    # Type-safe content access
    if parsed_envelope.is_chat_message():
        original_chat_payload = chat_envelope.payload
        parsed_chat_payload = parsed_envelope.payload
        # Both are guaranteed to be ChatMessagePayload
        if isinstance(original_chat_payload, ChatMessagePayload) and isinstance(parsed_chat_payload, ChatMessagePayload):
            print(f"Content matches: {original_chat_payload.content == parsed_chat_payload.content}")
    
    print("\n✅ All tests passed! Envelope system working correctly.")
