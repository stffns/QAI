"""
Tests simples y funcionales para el sistema de WebSocket Envelope
Diseñados para ejecutarse con pytest sin problemas de tipo
"""

import pytest
import json
from src.websocket.events import (
    WebSocketEnvelopeFactory,
    parse_websocket_envelope,
    MessageType,
    ProtocolVersion
)


class TestBasicEnvelopeSystem:
    """Tests básicos del sistema de envelope implementado"""

    def test_chat_message_creation(self):
        """Test creación de mensaje de chat"""
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Hello, this is a test message",
            session_id="test_session_123",
            user_id="test_user_456"
        )
        
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.version == ProtocolVersion.V2_0
        assert envelope.session_id == "test_session_123"
        assert envelope.user_id == "test_user_456"
        assert envelope.is_chat_message()
        assert envelope.get_payload_type() == "chat_message"

    def test_agent_response_creation(self):
        """Test creación de respuesta del agente"""
        envelope = WebSocketEnvelopeFactory.create_agent_response(
            content="This is an agent response",
            tools_used=["web_search", "calculator"],
            execution_time=2.5,
            confidence=0.95
        )
        
        assert envelope.type == MessageType.AGENT_RESPONSE
        assert envelope.is_agent_response()
        assert envelope.get_payload_type() == "agent_response"

    def test_system_event_creation(self):
        """Test creación de evento del sistema"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="user_connected",
            description="A new user has connected",
            severity="info",
            data={"ip": "192.168.1.100", "browser": "Chrome"}
        )
        
        assert envelope.type == MessageType.SYSTEM_EVENT
        assert envelope.is_system_event()
        assert envelope.get_payload_type() == "system_event"

    def test_error_event_creation(self):
        """Test creación de evento de error"""
        envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="VALIDATION_FAILED",
            error_message="Input validation failed",
            details="The provided email format is invalid"
        )
        
        assert envelope.type == MessageType.ERROR_EVENT
        assert envelope.is_error_event()
        assert envelope.get_payload_type() == "error_event"

    def test_connection_event_creation(self):
        """Test creación de evento de conexión"""
        envelope = WebSocketEnvelopeFactory.create_connection_event(
            event_type="connected",
            client_info={"browser": "Chrome", "version": "91.0"},
            session_data={"protocol": "websocket"}
        )
        
        assert envelope.type == MessageType.CONNECTION_EVENT
        assert envelope.is_connection_event()
        assert envelope.get_payload_type() == "connection_event"

    def test_health_check_creation(self):
        """Test creación de health check"""
        envelope = WebSocketEnvelopeFactory.create_health_check(status="ping")
        
        assert envelope.type == MessageType.HEALTH_CHECK
        assert envelope.is_health_check()
        assert envelope.get_payload_type() == "health_check"


class TestJSONOperations:
    """Tests de operaciones JSON"""

    def test_json_serialization_roundtrip(self):
        """Test serialización y deserialización JSON"""
        # Crear envelope original
        original = WebSocketEnvelopeFactory.create_chat_message(
            content="Test message for JSON roundtrip",
            session_id="json_test_session",
            user_id="json_test_user"
        )
        
        # Serializar a JSON
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        
        # Verificar estructura JSON
        assert "type" in json_data
        assert "version" in json_data
        assert "id" in json_data
        assert "ts" in json_data
        assert "payload" in json_data
        assert "session_id" in json_data
        assert "user_id" in json_data
        
        # Deserializar
        parsed = parse_websocket_envelope(json_str)
        
        # Verificar que se preserva correctamente
        assert parsed.type == original.type
        assert parsed.id == original.id
        assert parsed.session_id == original.session_id
        assert parsed.user_id == original.user_id
        assert parsed.is_chat_message()

    def test_all_envelope_types_json_serialization(self):
        """Test serialización JSON de todos los tipos de envelope"""
        envelopes = [
            WebSocketEnvelopeFactory.create_chat_message(content="Test chat"),
            WebSocketEnvelopeFactory.create_agent_response(content="Test response"),
            WebSocketEnvelopeFactory.create_system_event(event_name="test_event"),
            WebSocketEnvelopeFactory.create_error_event(error_code="TEST", error_message="Test error"),
            WebSocketEnvelopeFactory.create_connection_event(event_type="connected"),
            WebSocketEnvelopeFactory.create_health_check(status="ping")
        ]
        
        for envelope in envelopes:
            # Serializar
            json_str = envelope.model_dump_json()
            
            # Deserializar
            parsed = parse_websocket_envelope(json_str)
            
            # Verificar tipo se preserva
            assert parsed.type == envelope.type
            assert parsed.get_payload_type() == envelope.get_payload_type()


class TestCorrelationSystem:
    """Tests del sistema de correlación"""

    def test_question_answer_correlation(self):
        """Test correlación pregunta-respuesta"""
        # Usuario hace pregunta
        question = WebSocketEnvelopeFactory.create_chat_message(
            content="What is machine learning?",
            session_id="correlation_test_session",
            user_id="correlation_test_user"
        )
        
        # Agente responde correlacionando con la pregunta
        answer = WebSocketEnvelopeFactory.create_agent_response(
            content="Machine learning is a subset of artificial intelligence...",
            correlation_id=question.id,
            session_id="correlation_test_session",
            user_id="correlation_test_user"
        )
        
        # Verificar correlación
        assert answer.correlation_id == question.id
        assert answer.session_id == question.session_id
        assert answer.user_id == question.user_id

    def test_session_tracking(self):
        """Test seguimiento de sesión"""
        session_id = "session_tracking_test"
        user_id = "user_tracking_test"
        
        messages = []
        
        # Crear varios mensajes en la misma sesión
        for i in range(3):
            msg = WebSocketEnvelopeFactory.create_chat_message(
                content=f"Message {i+1}",
                session_id=session_id,
                user_id=user_id
            )
            messages.append(msg)
        
        # Verificar que todos pertenecen a la misma sesión
        for msg in messages:
            assert msg.session_id == session_id
            assert msg.user_id == user_id
        
        # Verificar que tienen IDs únicos
        ids = [msg.id for msg in messages]
        assert len(set(ids)) == len(ids)  # Todos únicos


class TestTypeIdentification:
    """Tests de identificación de tipos"""

    def test_type_identification_methods(self):
        """Test métodos de identificación de tipos"""
        # Crear uno de cada tipo
        chat = WebSocketEnvelopeFactory.create_chat_message(content="Test")
        agent = WebSocketEnvelopeFactory.create_agent_response(content="Response")
        system = WebSocketEnvelopeFactory.create_system_event(event_name="test")
        error = WebSocketEnvelopeFactory.create_error_event(error_code="TEST", error_message="Test")
        connection = WebSocketEnvelopeFactory.create_connection_event(event_type="connected")
        health = WebSocketEnvelopeFactory.create_health_check(status="ping")
        
        # Test identificación correcta
        assert chat.is_chat_message() and not chat.is_agent_response()
        assert agent.is_agent_response() and not agent.is_chat_message()
        assert system.is_system_event() and not system.is_error_event()
        assert error.is_error_event() and not error.is_system_event()
        assert connection.is_connection_event() and not connection.is_health_check()
        assert health.is_health_check() and not health.is_connection_event()

    def test_get_payload_type_consistency(self):
        """Test consistencia del método get_payload_type"""
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


class TestErrorScenarios:
    """Tests de escenarios de error"""

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

    def test_content_validation(self):
        """Test validación de contenido"""
        # Contenido vacío no debe ser válido
        with pytest.raises(Exception):
            WebSocketEnvelopeFactory.create_chat_message(content="")

    def test_confidence_validation(self):
        """Test validación de confidence"""
        # Confidence fuera de rango [0.0, 1.0]
        with pytest.raises(Exception):
            WebSocketEnvelopeFactory.create_agent_response(
                content="Test", confidence=1.5
            )
        
        with pytest.raises(Exception):
            WebSocketEnvelopeFactory.create_agent_response(
                content="Test", confidence=-0.1
            )


def test_complete_conversation_flow():
    """Test de integración: flujo completo de conversación"""
    session_id = "integration_conversation_test"
    user_id = "integration_user_test"
    
    # 1. Usuario se conecta
    connection = WebSocketEnvelopeFactory.create_connection_event(
        event_type="connected",
        client_info={"browser": "Test Browser"},
        session_data={"test_mode": True}
    )
    connection.session_id = session_id
    connection.user_id = user_id
    
    # 2. Usuario hace pregunta
    question = WebSocketEnvelopeFactory.create_chat_message(
        content="How do I implement a binary search in Python?",
        session_id=session_id,
        user_id=user_id
    )
    
    # 3. Agente procesa y responde
    answer = WebSocketEnvelopeFactory.create_agent_response(
        content="Here's how to implement binary search in Python...",
        correlation_id=question.id,
        session_id=session_id,
        user_id=user_id,
        tools_used=["algorithm_docs", "code_generator"],
        execution_time=1.8,
        confidence=0.97
    )
    
    # 4. Health check
    health = WebSocketEnvelopeFactory.create_health_check(status="ping")
    
    # 5. Sistema registra actividad
    activity = WebSocketEnvelopeFactory.create_system_event(
        event_name="successful_qa_interaction",
        description="User successfully received help with algorithm implementation",
        severity="info",
        data={"topic": "algorithms", "satisfaction": "high"}
    )
    
    # Test serialización de todo el flujo
    conversation = [connection, question, answer, health, activity]
    
    for envelope in conversation:
        # Serializar a JSON
        json_str = envelope.model_dump_json()
        
        # Deserializar
        parsed = parse_websocket_envelope(json_str)
        
        # Verificar que el tipo se preserva
        assert parsed.type == envelope.type
        assert parsed.get_payload_type() == envelope.get_payload_type()
    
    # Verificar correlación
    assert answer.correlation_id == question.id
    
    # Verificar sesión
    session_messages = [connection, question, answer]
    for msg in session_messages:
        assert msg.session_id == session_id
        assert msg.user_id == user_id
    
    print("✅ Complete conversation flow test passed!")
    print(f"✅ Processed {len(conversation)} envelopes successfully")
    print("✅ All envelope types working correctly")
    print("✅ JSON serialization/deserialization working")
    print("✅ Correlation system working")
    print("✅ Session tracking working")


if __name__ == "__main__":
    # Ejecutar test de integración si se ejecuta directamente
    test_complete_conversation_flow()
    
    # Ejecutar todos los tests con pytest
    pytest.main([__file__, "-v"])
