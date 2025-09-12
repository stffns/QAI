"""
Tests corregidos para el sistema de WebSocket Envelope con Uniones Discriminadas

Este módulo contiene tests exhaustivos para validar:
- Sistema de envelope común con campos estándares (type, version, id, ts)
- Uniones discriminadas para payloads
- Serialización/deserialización JSON
- Factory pattern para creación de envelopes
- Type safety y validación
"""

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
    HealthCheckPayload
)


class TestWebSocketEnvelopeBasics:
    """Tests básicos del sistema de envelope"""

    def test_envelope_creation_with_required_fields(self):
        """Test creación de envelope con campos requeridos"""
        payload = ChatMessagePayload(content="Test message")
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        
        # Verificar campos requeridos
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.version == ProtocolVersion.V2_0  # Valor por defecto
        assert isinstance(envelope.id, str)
        assert len(envelope.id) > 0
        assert isinstance(envelope.ts, int)
        assert envelope.ts > 0
        assert envelope.payload == payload

    def test_envelope_optional_fields(self):
        """Test campos opcionales del envelope"""
        payload = ChatMessagePayload(content="Test message")
        session_id = "test_session_123"
        user_id = "test_user_456"
        correlation_id = "test_correlation_789"
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        assert envelope.session_id == session_id
        assert envelope.user_id == user_id
        assert envelope.correlation_id == correlation_id

    def test_envelope_auto_generated_fields(self):
        """Test campos generados automáticamente"""
        payload = ChatMessagePayload(content="Test message")
        
        envelope1 = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        envelope2 = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        
        # Los IDs deben ser únicos
        assert envelope1.id != envelope2.id
        
        # Los timestamps deben ser diferentes (aunque sea por milisegundos)
        assert envelope1.ts <= envelope2.ts


class TestDiscriminatedUnions:
    """Tests de uniones discriminadas para payloads"""

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
        assert len(payload.attachments) == 2
        assert payload.attachments[0]["name"] == "file1.pdf"
        assert payload.metadata["priority"] == "high"

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
        assert payload.response_type == "text"
        assert payload.tools_used == ["web_search", "calculator"]
        assert payload.execution_time == 1.5
        assert payload.confidence == 0.95
        assert payload.metadata["source"] == "qa_agent"

    def test_system_event_payload(self):
        """Test SystemEventPayload"""
        payload = SystemEventPayload(
            message_type="system_event",
            event_name="user_connected",
            description="User has connected to the system",
            severity="info",
            data={"ip": "192.168.1.1", "user_agent": "Chrome"}
        )
        
        assert payload.message_type == "system_event"
        assert payload.event_name == "user_connected"
        assert payload.description == "User has connected to the system"
        assert payload.severity == "info"
        assert payload.data == {"ip": "192.168.1.1", "user_agent": "Chrome"}

    def test_error_event_payload(self):
        """Test ErrorEventPayload"""
        payload = ErrorEventPayload(
            message_type="error_event",
            error_code="AUTH_FAILED",
            error_message="Authentication failed",
            details="User provided invalid credentials",
            stack_trace="Traceback (most recent call last)...",
            retry_count=2
        )
        
        assert payload.message_type == "error_event"
        assert payload.error_code == "AUTH_FAILED"
        assert payload.error_message == "Authentication failed"
        assert payload.details == "User provided invalid credentials"
        assert payload.stack_trace is not None
        assert payload.retry_count == 2

    def test_connection_event_payload(self):
        """Test ConnectionEventPayload"""
        payload = ConnectionEventPayload(
            message_type="connection_event",
            event_type="connected",
            client_info={"browser": "Chrome", "os": "macOS"},
            session_data={"protocol": "websocket", "version": "13"}
        )
        
        assert payload.message_type == "connection_event"
        assert payload.event_type == "connected"
        assert payload.client_info == {"browser": "Chrome", "os": "macOS"}
        assert payload.session_data == {"protocol": "websocket", "version": "13"}

    def test_health_check_payload(self):
        """Test HealthCheckPayload"""
        payload = HealthCheckPayload(
            message_type="health_check",
            status="ping"
        )
        
        assert payload.message_type == "health_check"
        assert payload.status == "ping"
        assert isinstance(payload.timestamp, float)
        assert payload.timestamp > 0


class TestEnvelopeFactory:
    """Tests del factory pattern para envelopes"""

    def test_create_chat_message(self):
        """Test factory para mensaje de chat"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Hello from factory",
            session_id="sess_123",
            user_id="user_456",
            attachments=[{"name": "doc.pdf", "type": "document"}],
            metadata={"urgent": True}
        )
        
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.session_id == "sess_123"
        assert envelope.user_id == "user_456"
        assert envelope.is_chat_message()
        
        payload = envelope.payload
        assert payload.content == "Hello from factory"
        assert len(payload.attachments) == 1
        assert payload.attachments[0]["name"] == "doc.pdf"
        assert payload.metadata["urgent"] == True

    def test_create_agent_response(self):
        """Test factory para respuesta del agente"""
        original_id = str(uuid.uuid4())
        
        envelope = WebSocketEnvelopeFactory.create_agent_response(
            content="Agent response from factory",
            correlation_id=original_id,
            tools_used=["web_search"],
            execution_time=2.3,
            confidence=0.89
        )
        
        assert envelope.type == MessageType.AGENT_RESPONSE
        assert envelope.correlation_id == original_id
        assert envelope.is_agent_response()
        
        payload = envelope.payload
        assert payload.content == "Agent response from factory"
        assert payload.tools_used == ["web_search"]
        assert payload.execution_time == 2.3
        assert payload.confidence == 0.89

    def test_create_system_event(self):
        """Test factory para evento del sistema"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="server_restart",
            description="Server is restarting",
            severity="warning",
            data={"restart_reason": "maintenance"}
        )
        
        assert envelope.type == MessageType.SYSTEM_EVENT
        assert envelope.is_system_event()
        
        payload = envelope.payload
        assert payload.event_name == "server_restart"
        assert payload.description == "Server is restarting"
        assert payload.severity == "warning"
        assert payload.data == {"restart_reason": "maintenance"}

    def test_create_error_event(self):
        """Test factory para evento de error"""
        envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input provided",
            details="Email field contains invalid format"
        )
        
        assert envelope.type == MessageType.ERROR_EVENT
        assert envelope.is_error_event()
        
        payload = envelope.payload
        assert payload.error_code == "VALIDATION_ERROR"
        assert payload.error_message == "Invalid input provided"
        assert payload.details == "Email field contains invalid format"

    def test_create_connection_event(self):
        """Test factory para evento de conexión"""
        envelope = WebSocketEnvelopeFactory.create_connection_event(
            event_type="disconnected",
            client_info={"session_duration": 300},
            session_data={"reason": "timeout"}
        )
        
        assert envelope.type == MessageType.CONNECTION_EVENT
        assert envelope.is_connection_event()
        
        payload = envelope.payload
        assert payload.event_type == "disconnected"
        assert payload.client_info == {"session_duration": 300}
        assert payload.session_data == {"reason": "timeout"}

    def test_create_health_check(self):
        """Test factory para health check"""
        envelope = WebSocketEnvelopeFactory.create_health_check(
            status="pong"
        )
        
        assert envelope.type == MessageType.HEALTH_CHECK
        assert envelope.is_health_check()
        
        payload = envelope.payload
        assert payload.status == "pong"
        assert isinstance(payload.timestamp, float)


class TestJSONSerialization:
    """Tests de serialización/deserialización JSON"""

    def test_envelope_to_json(self):
        """Test serialización de envelope a JSON"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Test message",
            session_id="test_session",
            user_id="test_user"
        )
        
        json_str = envelope.model_dump_json()
        json_data = json.loads(json_str)
        
        # Verificar estructura JSON
        assert "type" in json_data
        assert "version" in json_data
        assert "id" in json_data
        assert "ts" in json_data
        assert "payload" in json_data
        assert "session_id" in json_data
        assert "user_id" in json_data
        
        # Verificar valores
        assert json_data["type"] == "chat_message"
        assert json_data["session_id"] == "test_session"
        assert json_data["user_id"] == "test_user"
        assert json_data["payload"]["message_type"] == "chat_message"
        assert json_data["payload"]["content"] == "Test message"

    def test_envelope_from_json(self):
        """Test deserialización de JSON a envelope"""
        # Crear envelope original
        original = WebSocketEnvelopeFactory.create_agent_response(
            content="Original response",
            tools_used=["tool1", "tool2"],
            execution_time=1.5,
            confidence=0.95
        )
        
        # Serializar a JSON
        json_str = original.model_dump_json()
        
        # Deserializar
        deserialized = WebSocketEnvelope.model_validate_json(json_str)
        
        # Verificar que se preserva correctamente
        assert deserialized.type == original.type
        assert deserialized.id == original.id
        assert deserialized.ts == original.ts
        assert type(deserialized.payload) == type(original.payload)
        assert deserialized.payload.content == original.payload.content

    def test_parse_websocket_envelope_function(self):
        """Test función parse_websocket_envelope"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="test_event",
            severity="info"
        )
        
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.type == envelope.type
        assert parsed.id == envelope.id
        assert parsed.is_system_event()
        assert parsed.payload.event_name == "test_event"
        assert parsed.payload.severity == "info"


class TestTypeSafety:
    """Tests de seguridad de tipos y validación"""

    def test_envelope_type_validation(self):
        """Test validación de tipos de envelope"""
        chat_envelope = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        agent_envelope = WebSocketEnvelopeFactory.create_agent_response(content="Response")
        
        # Test métodos de identificación
        assert chat_envelope.is_chat_message()
        assert not chat_envelope.is_agent_response()
        
        assert agent_envelope.is_agent_response()
        assert not agent_envelope.is_chat_message()

    def test_payload_type_access(self):
        """Test acceso a tipos de payload"""
        envelopes = [
            WebSocketEnvelopeFactory.create_chat_message(content="Test"),
            WebSocketEnvelopeFactory.create_agent_response(content="Response"),
            WebSocketEnvelopeFactory.create_system_event(event_name="test"),
            WebSocketEnvelopeFactory.create_error_event(error_code="TEST", error_message="Test"),
            WebSocketEnvelopeFactory.create_connection_event(event_type="connected"),
            WebSocketEnvelopeFactory.create_health_check(status="ping")
        ]
        
        expected_types = [
            ChatMessagePayload,
            AgentResponsePayload,
            SystemEventPayload,
            ErrorEventPayload,
            ConnectionEventPayload,
            HealthCheckPayload
        ]
        
        for envelope, expected_type in zip(envelopes, expected_types):
            assert isinstance(envelope.payload, expected_type)

    def test_get_payload_type_method(self):
        """Test método get_payload_type"""
        test_cases = [
            (WebSocketEnvelopeFactory.create_chat_message(content="Test"), "chat_message"),
            (WebSocketEnvelopeFactory.create_agent_response(content="Response"), "agent_response"),
            (WebSocketEnvelopeFactory.create_system_event(event_name="test"), "system_event"),
            (WebSocketEnvelopeFactory.create_error_event(error_code="TEST", error_message="Test"), "error_event"),
            (WebSocketEnvelopeFactory.create_connection_event(event_type="connected"), "connection_event"),
            (WebSocketEnvelopeFactory.create_health_check(status="ping"), "health_check")
        ]
        
        for envelope, expected_type in test_cases:
            assert envelope.get_payload_type() == expected_type

    def test_invalid_discriminator(self):
        """Test validación de discriminador inválido"""
        with pytest.raises(ValueError):
            # Intentar crear payload con message_type incorrecto no debería ser posible
            # debido a Literal types, pero podemos testearlo con JSON inválido
            invalid_json = '{"type": "chat_message", "payload": {"message_type": "wrong_type", "content": "test"}}'
            parse_websocket_envelope(invalid_json)


class TestErrorHandling:
    """Tests de manejo de errores"""

    def test_invalid_json_parsing(self):
        """Test parsing de JSON inválido"""
        invalid_cases = [
            "not json at all",
            '{"type": "chat_message"}',  # Falta payload
            '{"payload": {"content": "test"}}',  # Falta type
        ]
        
        for invalid_json in invalid_cases:
            with pytest.raises(Exception):
                parse_websocket_envelope(invalid_json)

    def test_missing_required_fields(self):
        """Test campos requeridos faltantes"""
        with pytest.raises(Exception):
            ChatMessagePayload(message_type="chat_message")  # Falta content

    def test_invalid_message_type_in_payload(self):
        """Test message_type inválido en payload"""
        # Los Literal types de Pydantic previenen esto en tiempo de creación
        with pytest.raises(Exception):
            # Esto fallará porque message_type debe ser exactamente "chat_message"
            invalid_json = '''
            {
                "type": "chat_message",
                "payload": {
                    "message_type": "invalid_type",
                    "content": "test"
                }
            }
            '''
            parse_websocket_envelope(invalid_json)


class TestCorrelationAndTracing:
    """Tests de correlación y trazabilidad"""

    def test_correlation_ids(self):
        """Test IDs de correlación"""
        # Usuario hace pregunta
        question = WebSocketEnvelopeFactory.create_chat_message(
            content="What is Python?",
            session_id="session_123",
            user_id="user_456"
        )
        
        # Agente responde
        answer = WebSocketEnvelopeFactory.create_agent_response(
            content="Python is a programming language",
            correlation_id=question.id,
            session_id="session_123",
            user_id="user_456"
        )
        
        # Verificar correlación
        assert answer.correlation_id == question.id
        assert answer.session_id == question.session_id
        assert answer.user_id == question.user_id

    def test_session_tracking(self):
        """Test seguimiento de sesión"""
        session_id = "test_session_789"
        user_id = "test_user_123"
        
        messages = [
            WebSocketEnvelopeFactory.create_chat_message(
                content="Message 1", session_id=session_id, user_id=user_id
            ),
            WebSocketEnvelopeFactory.create_agent_response(
                content="Response 1", session_id=session_id, user_id=user_id
            ),
            WebSocketEnvelopeFactory.create_system_event(
                event_name="event_1", session_id=session_id, user_id=user_id
            )
        ]
        
        # Todos deben pertenecer a la misma sesión
        for msg in messages:
            assert msg.session_id == session_id
            assert msg.user_id == user_id


class TestProtocolVersions:
    """Tests de versiones del protocolo"""

    def test_default_version(self):
        """Test versión por defecto"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        assert envelope.version == ProtocolVersion.V2_0

    def test_explicit_version(self):
        """Test versión explícita"""
        payload = ChatMessagePayload(content="Test message")
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            version=ProtocolVersion.V1_0,
            payload=payload
        )
        assert envelope.version == ProtocolVersion.V1_0

    def test_version_serialization(self):
        """Test serialización de versión"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        json_str = envelope.model_dump_json()
        json_data = json.loads(json_str)
        
        assert "version" in json_data
        # La versión se serializa como string
        assert isinstance(json_data["version"], str)


# Tests de integración y casos complejos
def test_complete_conversation_flow():
    """Test flujo completo de conversación"""
    session_id = "integration_test_session"
    user_id = "integration_test_user"
    
    # 1. Usuario se conecta
    connection = WebSocketEnvelopeFactory.create_connection_event(
        event_type="connected",
        client_info={"browser": "Test"},
        session_data={"test": True}
    )
    connection.session_id = session_id
    connection.user_id = user_id
    
    # 2. Usuario hace pregunta
    question = WebSocketEnvelopeFactory.create_chat_message(
        content="How do I use Python?",
        session_id=session_id,
        user_id=user_id
    )
    
    # 3. Agente responde
    answer = WebSocketEnvelopeFactory.create_agent_response(
        content="Python is easy to learn...",
        correlation_id=question.id,
        session_id=session_id,
        user_id=user_id,
        tools_used=["documentation"],
        execution_time=2.1,
        confidence=0.95
    )
    
    # 4. Health check
    health = WebSocketEnvelopeFactory.create_health_check(status="ping")
    
    # Test serialización de toda la conversación
    conversation = [connection, question, answer, health]
    serialized = []
    
    for envelope in conversation:
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        serialized.append(parsed)
    
    # Verificar correlación y flujo
    assert serialized[0].is_connection_event()
    assert serialized[1].is_chat_message()
    assert serialized[2].is_agent_response()
    assert serialized[2].correlation_id == serialized[1].id
    assert serialized[3].is_health_check()
    
    # Verificar sesión
    for msg in serialized[:3]:  # Excluyendo health check
        if hasattr(msg, 'session_id') and msg.session_id:
            assert msg.session_id == session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
