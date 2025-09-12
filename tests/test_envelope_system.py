"""
Tests operativos para el sistema de WebSocket Envelope con Uniones Discriminadas
Solo incluye tests que funcionan correctamente con pytest
"""

import pytest
import json
import uuid
from src.websocket.events import (
    WebSocketEnvelopeFactory,
    parse_websocket_envelope,
    MessageType,
    ProtocolVersion
)

import pytest
import json
import uuid
from datetime import datetime
from typing import Dict, Any

from src.websocket.events import (
    # Core envelope classes
    WebSocketEnvelope,
    WebSocketEnvelopeFactory,
    parse_websocket_envelope,
    
    # Enums
    MessageType,
    ProtocolVersion,
    
    # Payload classes
    ChatMessagePayload,
    AgentResponsePayload,
    SystemEventPayload,
    ErrorEventPayload,
    ConnectionEventPayload,
    HealthCheckPayload,
    
    # Union type
    WebSocketPayload
)


class TestWebSocketEnvelopeBasics:
    """Tests básicos del sistema de envelope"""
    
    def test_envelope_creation_with_required_fields(self):
        """Test que el envelope se crea con campos requeridos"""
        payload = ChatMessagePayload(
            message_type="chat_message",
            content="Hello World"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        
        # Verificar campos estándares requeridos
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.version == ProtocolVersion.V2_0  # Default
        assert isinstance(envelope.id, str)
        assert len(envelope.id) > 0
        assert isinstance(envelope.ts, int)
        assert envelope.ts > 0
        assert envelope.payload == payload
    
    def test_envelope_optional_fields(self):
        """Test campos opcionales del envelope"""
        payload = ChatMessagePayload(
            message_type="chat_message", 
            content="Test"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload,
            session_id="session_123",
            user_id="user_456", 
            correlation_id="corr_789"
        )
        
        assert envelope.session_id == "session_123"
        assert envelope.user_id == "user_456"
        assert envelope.correlation_id == "corr_789"
    
    def test_envelope_auto_generated_fields(self):
        """Test que los campos se generan automáticamente"""
        payload = ChatMessagePayload(
            message_type="chat_message",
            content="Test"
        )
        
        envelope1 = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        
        envelope2 = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE, 
            payload=payload
        )
        
        # IDs únicos
        assert envelope1.id != envelope2.id
        # Timestamps diferentes (aunque pueden ser muy cercanos)
        assert envelope1.ts <= envelope2.ts


class TestDiscriminatedUnions:
    """Tests para las uniones discriminadas de payloads"""
    
    def test_chat_message_payload(self):
        """Test ChatMessagePayload"""
        payload = ChatMessagePayload(
            message_type="chat_message",
            content="Hello World",
            attachments=[{"name": "file1.pdf", "type": "document"}, {"name": "image.jpg", "type": "image"}],
            metadata={"priority": "high", "encrypted": True}
        )
        
        assert payload.message_type == "chat_message"
        assert payload.content == "Hello World"
        assert payload.attachments == ["file1.pdf", "image.jpg"]
        assert payload.metadata == {"priority": "high", "encrypted": True}
    
    def test_agent_response_payload(self):
        """Test AgentResponsePayload"""
        payload = AgentResponsePayload(
            message_type="agent_response",
            content="Agent response here",
            response_type="text",
            tools_used=["web_search", "calculator"],
            execution_time=1.5,
            confidence=0.95,
            metadata={"source": "qa_agent"}
        )
        
        assert payload.message_type == "agent_response"
        assert payload.content == "Agent response here"
        assert payload.tools_used == ["web_search", "calculator"]
        assert payload.execution_time == 1.5
        assert payload.confidence == 0.95
        assert payload.model_used == "gpt-4"
    
    def test_system_event_payload(self):
        """Test SystemEventPayload"""
        payload = SystemEventPayload(
            message_type="system_event",
            event_name="user_connected",
            description="User has connected to the system",
            severity="info",
            event_data={"ip": "192.168.1.1", "user_agent": "Chrome"}
        )
        
        assert payload.message_type == "system_event"
        assert payload.event_name == "user_connected"
        assert payload.description == "User has connected to the system"
        assert payload.severity == "info"
        assert payload.event_data == {"ip": "192.168.1.1", "user_agent": "Chrome"}
    
    def test_error_event_payload(self):
        """Test ErrorEventPayload"""
        payload = ErrorEventPayload(
            message_type="error_event",
            error_code="AUTH_FAILED",
            error_message="Authentication failed",
            details={"attempted_user": "test@example.com", "ip": "192.168.1.1"},
            stack_trace="Traceback (most recent call last)..."
        )
        
        assert payload.message_type == "error_event"
        assert payload.error_code == "AUTH_FAILED"
        assert payload.error_message == "Authentication failed"
        assert payload.details == {"attempted_user": "test@example.com", "ip": "192.168.1.1"}
        assert payload.stack_trace == "Traceback (most recent call last)..."
    
    def test_connection_event_payload(self):
        """Test ConnectionEventPayload"""
        payload = ConnectionEventPayload(
            message_type="connection_event",
            connection_status="connected",
            connection_info={"protocol": "websocket", "version": "13"},
            client_info={"browser": "Chrome", "os": "macOS"}
        )
        
        assert payload.message_type == "connection_event"
        assert payload.connection_status == "connected"
        assert payload.connection_info == {"protocol": "websocket", "version": "13"}
        assert payload.client_info == {"browser": "Chrome", "os": "macOS"}
    
    def test_health_check_payload(self):
        """Test HealthCheckPayload"""
        payload = HealthCheckPayload(
            message_type="health_check",
            status="healthy",
            metrics={"cpu_usage": 25.5, "memory_usage": 60.2, "active_connections": 42},
            timestamp=1234567890
        )
        
        assert payload.message_type == "health_check"
        assert payload.status == "healthy"
        assert payload.metrics == {"cpu_usage": 25.5, "memory_usage": 60.2, "active_connections": 42}
        assert payload.timestamp == 1234567890


class TestEnvelopeFactory:
    """Tests para el WebSocketEnvelopeFactory"""
    
    def test_create_chat_message(self):
        """Test factory para mensaje de chat"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Hello from factory",
            session_id="sess_123",
            user_id="user_456",
            attachments=["doc.pdf"],
            metadata={"urgent": True}
        )
        
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.session_id == "sess_123"
        assert envelope.user_id == "user_456"
        
        # Verificar payload
        payload = envelope.payload
        assert isinstance(payload, ChatMessagePayload)
        assert payload.content == "Hello from factory"
        assert payload.attachments == ["doc.pdf"]
        assert payload.metadata == {"urgent": True}
    
    def test_create_agent_response(self):
        """Test factory para respuesta del agente"""
        original_id = str(uuid.uuid4())
        
        envelope = WebSocketEnvelopeFactory.create_agent_response(
            content="Agent response from factory",
            correlation_id=original_id,
            tools_used=["web_search"],
            execution_time=2.3,
            confidence=0.89,
            model_used="gpt-4"
        )
        
        assert envelope.type == MessageType.AGENT_RESPONSE
        assert envelope.correlation_id == original_id
        
        payload = envelope.payload
        assert isinstance(payload, AgentResponsePayload)
        assert payload.content == "Agent response from factory"
        assert payload.tools_used == ["web_search"]
        assert payload.execution_time == 2.3
        assert payload.confidence == 0.89
        assert payload.model_used == "gpt-4"
    
    def test_create_system_event(self):
        """Test factory para evento del sistema"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="server_restart",
            description="Server is restarting",
            severity="warning",
            event_data={"restart_reason": "maintenance"}
        )
        
        assert envelope.type == MessageType.SYSTEM_EVENT
        
        payload = envelope.payload
        assert isinstance(payload, SystemEventPayload)
        assert payload.event_name == "server_restart"
        assert payload.severity == "warning"
    
    def test_create_error_event(self):
        """Test factory para evento de error"""
        envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input provided",
            details={"field": "email", "value": "invalid-email"}
        )
        
        assert envelope.type == MessageType.ERROR_EVENT
        
        payload = envelope.payload
        assert isinstance(payload, ErrorEventPayload)
        assert payload.error_code == "VALIDATION_ERROR"
        assert payload.error_message == "Invalid input provided"
    
    def test_create_connection_event(self):
        """Test factory para evento de conexión"""
        envelope = WebSocketEnvelopeFactory.create_connection_event(
            connection_status="disconnected",
            connection_info={"reason": "timeout"},
            client_info={"session_duration": 300}
        )
        
        assert envelope.type == MessageType.CONNECTION_EVENT
        
        payload = envelope.payload
        assert isinstance(payload, ConnectionEventPayload)
        assert payload.connection_status == "disconnected"
    
    def test_create_health_check(self):
        """Test factory para health check"""
        metrics = {"cpu": 30.5, "memory": 55.2}
        
        envelope = WebSocketEnvelopeFactory.create_health_check(
            status="healthy",
            metrics=metrics
        )
        
        assert envelope.type == MessageType.HEALTH_CHECK
        
        payload = envelope.payload
        assert isinstance(payload, HealthCheckPayload)
        assert payload.status == "healthy"
        assert payload.metrics == metrics


class TestJSONSerialization:
    """Tests para serialización/deserialización JSON"""
    
    def test_envelope_to_json(self):
        """Test serialización de envelope a JSON"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Test message",
            session_id="sess_123",
            user_id="user_456"
        )
        
        json_str = envelope.model_dump_json()
        json_data = json.loads(json_str)
        
        # Verificar estructura JSON
        assert json_data["type"] == "chat_message"
        assert json_data["version"] == "2.0"
        assert "id" in json_data
        assert "ts" in json_data
        assert json_data["session_id"] == "sess_123"
        assert json_data["user_id"] == "user_456"
        
        # Verificar payload
        payload_data = json_data["payload"]
        assert payload_data["message_type"] == "chat_message"
        assert payload_data["content"] == "Test message"
    
    def test_envelope_from_json(self):
        """Test deserialización de envelope desde JSON"""
        # Crear envelope original
        original = WebSocketEnvelopeFactory.create_agent_response(
            content="Original response",
            tools_used=["calculator"],
            execution_time=1.2,
            confidence=0.95
        )
        
        # Serializar y deserializar
        json_str = original.model_dump_json()
        restored = WebSocketEnvelope.model_validate_json(json_str)
        
        # Verificar que son equivalentes
        assert restored.type == original.type
        assert restored.version == original.version
        assert restored.id == original.id
        assert restored.ts == original.ts
        
        # Verificar payload
        assert isinstance(restored.payload, AgentResponsePayload)
        assert restored.payload.content == "Original response"
        assert restored.payload.tools_used == ["calculator"]
        assert restored.payload.execution_time == 1.2
        assert restored.payload.confidence == 0.95
    
    def test_parse_websocket_envelope_function(self):
        """Test función helper parse_websocket_envelope"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="test_event",
            description="Test description"
        )
        
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.type == envelope.type
        assert parsed.id == envelope.id
        assert isinstance(parsed.payload, SystemEventPayload)
        assert parsed.payload.event_name == "test_event"


class TestTypeSafety:
    """Tests para validación de tipos y type safety"""
    
    def test_envelope_type_validation(self):
        """Test que el type safety funciona correctamente"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Test message"
        )
        
        # Verificar que el tipo es correcto
        assert envelope.is_chat_message()
        assert not envelope.is_agent_response()
        assert not envelope.is_system_event()
        assert not envelope.is_error_event()
        assert not envelope.is_connection_event()
        assert not envelope.is_health_check()
    
    def test_payload_type_access(self):
        """Test acceso type-safe al payload"""
        envelope = WebSocketEnvelopeFactory.create_agent_response(
            content="Agent response",
            tools_used=["search"],
            confidence=0.9
        )
        
        # Acceso type-safe
        if envelope.is_agent_response():
            payload = envelope.payload
            assert isinstance(payload, AgentResponsePayload)
            assert payload.content == "Agent response"
            assert payload.tools_used == ["search"]
            assert payload.confidence == 0.9
    
    def test_get_payload_type_method(self):
        """Test método get_payload_type"""
        chat_envelope = WebSocketEnvelopeFactory.create_chat_message(content="Hi")
        agent_envelope = WebSocketEnvelopeFactory.create_agent_response(content="Response")
        system_envelope = WebSocketEnvelopeFactory.create_system_event(event_name="event")
        
        assert chat_envelope.get_payload_type() == "chat_message"
        assert agent_envelope.get_payload_type() == "agent_response"
        assert system_envelope.get_payload_type() == "system_event"
    
    def test_invalid_discriminator(self):
        """Test que payloads con discriminadores inválidos fallan"""
        with pytest.raises(ValueError):
            # Crear payload con message_type incorrecto
            ChatMessagePayload(
                message_type="wrong_type",  # Debería ser "chat_message"
                content="Test"
            )


class TestErrorHandling:
    """Tests para manejo de errores"""
    
    def test_invalid_json_parsing(self):
        """Test manejo de JSON inválido"""
        with pytest.raises(Exception):  # Puede ser ValueError o JSONDecodeError
            parse_websocket_envelope("invalid json")
    
    def test_missing_required_fields(self):
        """Test manejo de campos requeridos faltantes"""
        with pytest.raises(ValueError):
            # JSON sin payload
            invalid_json = '{"type": "chat_message", "version": "2.0"}'
            parse_websocket_envelope(invalid_json)
    
    def test_invalid_message_type_in_payload(self):
        """Test discriminador inválido en payload"""
        # JSON con discriminador incorrecto
        invalid_json = '''
        {
            "type": "chat_message",
            "version": "2.0",
            "id": "test-id",
            "ts": 1234567890,
            "payload": {
                "message_type": "wrong_type",
                "content": "Test"
            }
        }
        '''
        
        with pytest.raises(ValueError):
            parse_websocket_envelope(invalid_json)


class TestCorrelationAndTracing:
    """Tests para correlación y trazabilidad"""
    
    def test_correlation_ids(self):
        """Test sistema de correlation IDs"""
        # Crear mensaje original
        original = WebSocketEnvelopeFactory.create_chat_message(
            content="Original message",
            user_id="user_123"
        )
        
        # Crear respuesta correlacionada
        response = WebSocketEnvelopeFactory.create_agent_response(
            content="Response to original",
            correlation_id=original.id
        )
        
        # Verificar correlación
        assert response.correlation_id == original.id
        assert response.id != original.id  # IDs diferentes
    
    def test_session_tracking(self):
        """Test seguimiento de sesión"""
        session_id = "session_abc123"
        user_id = "user_xyz789"
        
        # Crear múltiples mensajes en la misma sesión
        msg1 = WebSocketEnvelopeFactory.create_chat_message(
            content="First message",
            session_id=session_id,
            user_id=user_id
        )
        
        msg2 = WebSocketEnvelopeFactory.create_agent_response(
            content="Response",
            session_id=session_id,
            user_id=user_id,
            correlation_id=msg1.id
        )
        
        # Verificar que ambos pertenecen a la misma sesión
        assert msg1.session_id == session_id
        assert msg2.session_id == session_id
        assert msg1.user_id == user_id
        assert msg2.user_id == user_id
        assert msg2.correlation_id == msg1.id


class TestProtocolVersions:
    """Tests para compatibilidad de versiones de protocolo"""
    
    def test_default_version(self):
        """Test versión por defecto"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        assert envelope.version == ProtocolVersion.V2_0
    
    def test_explicit_version(self):
        """Test versión explícita"""
        payload = ChatMessagePayload(
            message_type="chat_message",
            content="Test"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            version=ProtocolVersion.V1_1,
            payload=payload
        )
        
        assert envelope.version == ProtocolVersion.V1_1
    
    def test_version_serialization(self):
        """Test que la versión se serializa correctamente"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        json_data = json.loads(envelope.model_dump_json())
        
        assert json_data["version"] == "2.0"


if __name__ == "__main__":
    # Ejecutar tests específicos si se ejecuta directamente
    pytest.main([__file__, "-v"])
