"""
Tests básicos para validar el sistema de WebSocket Envelope con Uniones Discriminadas

Este módulo contiene tests fundamentales para validar:
- Creación de envelopes con campos estándares
- Serialización/deserialización JSON básica
- Factory pattern básico
- Type safety fundamental
"""

import pytest
import json
import uuid
from datetime import datetime

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


class TestBasicEnvelopeSystem:
    """Tests básicos del sistema de envelope"""
    
    def test_chat_message_creation(self):
        """Test creación básica de mensaje de chat"""
        payload = ChatMessagePayload(
            message_type="chat_message",
            content="Hello World"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.CHAT_MESSAGE,
            payload=payload
        )
        
        # Verificar campos estándares
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.version == ProtocolVersion.V2_0
        assert isinstance(envelope.id, str)
        assert len(envelope.id) > 0
        assert isinstance(envelope.ts, int)
        assert envelope.ts > 0
        assert envelope.payload.content == "Hello World"
    
    def test_agent_response_creation(self):
        """Test creación de respuesta del agente"""
        payload = AgentResponsePayload(
            message_type="agent_response",
            content="Agent response here",
            tools_used=["web_search"],
            execution_time=1.5,
            confidence=0.95
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.AGENT_RESPONSE,
            payload=payload
        )
        
        assert envelope.type == MessageType.AGENT_RESPONSE
        assert envelope.payload.content == "Agent response here"
        assert envelope.payload.tools_used == ["web_search"]
        assert envelope.payload.execution_time == 1.5
        assert envelope.payload.confidence == 0.95
    
    def test_system_event_creation(self):
        """Test creación de evento del sistema"""
        payload = SystemEventPayload(
            message_type="system_event",
            event_name="user_connected",
            description="User has connected",
            severity="info",
            data={"ip": "192.168.1.1"}
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.SYSTEM_EVENT,
            payload=payload
        )
        
        assert envelope.type == MessageType.SYSTEM_EVENT
        assert envelope.payload.event_name == "user_connected"
        assert envelope.payload.description == "User has connected"
        assert envelope.payload.severity == "info"
        assert envelope.payload.data == {"ip": "192.168.1.1"}
    
    def test_error_event_creation(self):
        """Test creación de evento de error"""
        payload = ErrorEventPayload(
            message_type="error_event",
            error_code="AUTH_FAILED",
            error_message="Authentication failed",
            details="User credentials invalid"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.ERROR_EVENT,
            payload=payload
        )
        
        assert envelope.type == MessageType.ERROR_EVENT
        assert envelope.payload.error_code == "AUTH_FAILED"
        assert envelope.payload.error_message == "Authentication failed"
        assert envelope.payload.details == "User credentials invalid"
    
    def test_connection_event_creation(self):
        """Test creación de evento de conexión"""
        payload = ConnectionEventPayload(
            message_type="connection_event",
            event_type="connected",
            client_info={"browser": "Chrome"},
            session_data={"start_time": "2025-09-03T18:00:00Z"}
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.CONNECTION_EVENT,
            payload=payload
        )
        
        assert envelope.type == MessageType.CONNECTION_EVENT
        assert envelope.payload.event_type == "connected"
        assert envelope.payload.client_info == {"browser": "Chrome"}
    
    def test_health_check_creation(self):
        """Test creación de health check"""
        payload = HealthCheckPayload(
            message_type="health_check",
            status="ping"
        )
        
        envelope = WebSocketEnvelope(
            type=MessageType.HEALTH_CHECK,
            payload=payload
        )
        
        assert envelope.type == MessageType.HEALTH_CHECK
        assert envelope.payload.status == "ping"


class TestEnvelopeFactory:
    """Tests básicos para el factory pattern"""
    
    def test_create_chat_message(self):
        """Test factory para mensaje de chat"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Hello from factory",
            session_id="sess_123",
            user_id="user_456"
        )
        
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.session_id == "sess_123"
        assert envelope.user_id == "user_456"
        assert envelope.payload.content == "Hello from factory"
    
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
        assert envelope.payload.content == "Agent response from factory"
        assert envelope.payload.tools_used == ["web_search"]
        assert envelope.payload.execution_time == 2.3
        assert envelope.payload.confidence == 0.89
    
    def test_create_system_event(self):
        """Test factory para evento del sistema"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="server_restart",
            description="Server is restarting",
            severity="warning"
        )
        
        assert envelope.type == MessageType.SYSTEM_EVENT
        assert envelope.payload.event_name == "server_restart"
        assert envelope.payload.description == "Server is restarting"
        assert envelope.payload.severity == "warning"
    
    def test_create_error_event(self):
        """Test factory para evento de error"""
        envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input provided",
            details="Field validation failed"
        )
        
        assert envelope.type == MessageType.ERROR_EVENT
        assert envelope.payload.error_code == "VALIDATION_ERROR"
        assert envelope.payload.error_message == "Invalid input provided"
        assert envelope.payload.details == "Field validation failed"
    
    def test_create_health_check(self):
        """Test factory para health check"""
        envelope = WebSocketEnvelopeFactory.create_health_check(
            status="ping"
        )
        
        assert envelope.type == MessageType.HEALTH_CHECK
        assert envelope.payload.status == "ping"


class TestJSONSerialization:
    """Tests para serialización/deserialización JSON"""
    
    def test_chat_message_json_roundtrip(self):
        """Test serialización completa de mensaje de chat"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Test message",
            session_id="sess_123",
            user_id="user_456"
        )
        
        # Serializar a JSON
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
        
        # Deserializar de vuelta
        restored = WebSocketEnvelope.model_validate_json(json_str)
        assert restored.type == envelope.type
        assert restored.id == envelope.id
        assert restored.payload.content == "Test message"
    
    def test_agent_response_json_roundtrip(self):
        """Test serialización de respuesta del agente"""
        original = WebSocketEnvelopeFactory.create_agent_response(
            content="Original response",
            tools_used=["calculator"],
            execution_time=1.2,
            confidence=0.95
        )
        
        # Roundtrip JSON
        json_str = original.model_dump_json()
        restored = WebSocketEnvelope.model_validate_json(json_str)
        
        # Verificar que son equivalentes
        assert restored.type == original.type
        assert restored.id == original.id
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
    """Tests para type safety y discriminated unions"""
    
    def test_discriminated_union_validation(self):
        """Test que las uniones discriminadas funcionan correctamente"""
        # Crear envelope con cada tipo de payload
        chat_envelope = WebSocketEnvelopeFactory.create_chat_message(content="Hi")
        agent_envelope = WebSocketEnvelopeFactory.create_agent_response(content="Response")
        system_envelope = WebSocketEnvelopeFactory.create_system_event(event_name="event")
        
        # Verificar type safety methods
        assert chat_envelope.is_chat_message()
        assert not chat_envelope.is_agent_response()
        assert not chat_envelope.is_system_event()
        
        assert agent_envelope.is_agent_response()
        assert not agent_envelope.is_chat_message()
        
        assert system_envelope.is_system_event()
        assert not system_envelope.is_chat_message()
    
    def test_payload_type_identification(self):
        """Test identificación de tipo de payload"""
        chat_envelope = WebSocketEnvelopeFactory.create_chat_message(content="Hi")
        agent_envelope = WebSocketEnvelopeFactory.create_agent_response(content="Response")
        system_envelope = WebSocketEnvelopeFactory.create_system_event(event_name="event")
        error_envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="TEST", error_message="Test error"
        )
        
        assert chat_envelope.get_payload_type() == "chat_message"
        assert agent_envelope.get_payload_type() == "agent_response"
        assert system_envelope.get_payload_type() == "system_event"
        assert error_envelope.get_payload_type() == "error_event"


class TestCorrelationAndSessionTracking:
    """Tests para correlación y seguimiento de sesión"""
    
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


class TestErrorHandling:
    """Tests para manejo de errores"""
    
    def test_invalid_json_parsing(self):
        """Test manejo de JSON inválido"""
        with pytest.raises(Exception):
            parse_websocket_envelope("invalid json")
    
    def test_missing_payload(self):
        """Test manejo de envelope sin payload"""
        with pytest.raises(Exception):
            invalid_json = '{"type": "chat_message", "version": "2.0", "id": "test", "ts": 123}'
            parse_websocket_envelope(invalid_json)


# Test de integración básica
def test_complete_envelope_workflow():
    """Test de flujo completo del sistema de envelope"""
    # 1. Crear mensaje de chat
    chat_msg = WebSocketEnvelopeFactory.create_chat_message(
        content="Hello, I need help with Python",
        session_id="session_123",
        user_id="user_456"
    )
    
    # 2. Serializar para transmisión
    chat_json = chat_msg.model_dump_json()
    
    # 3. Deserializar en el receptor
    received_chat = parse_websocket_envelope(chat_json)
    
    # 4. Crear respuesta correlacionada
    agent_response = WebSocketEnvelopeFactory.create_agent_response(
        content="I can help you with Python! What specific question do you have?",
        session_id=received_chat.session_id,
        user_id=received_chat.user_id,
        correlation_id=received_chat.id,
        tools_used=["python_assistant"],
        confidence=0.95
    )
    
    # 5. Verificar flujo completo
    assert received_chat.type == MessageType.CHAT_MESSAGE
    assert received_chat.payload.content == "Hello, I need help with Python"
    
    assert agent_response.type == MessageType.AGENT_RESPONSE
    assert agent_response.correlation_id == chat_msg.id
    assert agent_response.session_id == chat_msg.session_id
    assert agent_response.user_id == chat_msg.user_id
    
    # 6. Serializar respuesta
    response_json = agent_response.model_dump_json()
    final_response = parse_websocket_envelope(response_json)
    
    assert final_response.payload.content.startswith("I can help you with Python!")
    assert final_response.correlation_id == chat_msg.id


if __name__ == "__main__":
    # Ejecutar tests si se ejecuta directamente
    pytest.main([__file__, "-v"])
