"""
Tests funcionales para el sistema de WebSocket Envelope

Tests que validan la funcionalidad real del sistema implementado,
enfocándose en casos de uso prácticos y flujos completos.
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


class TestWebSocketEnvelopeSystem:
    """Tests del sistema de envelope con uniones discriminadas"""
    
    def test_chat_message_workflow(self):
        """Test flujo completo de mensaje de chat"""
        # Crear mensaje usando factory
        envelope = WebSocketEnvelopeFactory.create_chat_message(
            content="Hello, I need help with Python programming",
            session_id="session_123",
            user_id="user_456"
        )
        
        # Verificar campos estándares del envelope
        assert envelope.type == MessageType.CHAT_MESSAGE
        assert envelope.version == ProtocolVersion.V2_0
        assert isinstance(envelope.id, str)
        assert len(envelope.id) > 0
        assert isinstance(envelope.ts, int)
        assert envelope.ts > 0
        assert envelope.session_id == "session_123"
        assert envelope.user_id == "user_456"
        
        # Verificar que es identificado correctamente
        assert envelope.is_chat_message()
        assert not envelope.is_agent_response()
        assert envelope.get_payload_type() == "chat_message"
        
        # Serializar a JSON
        json_str = envelope.model_dump_json()
        json_data = json.loads(json_str)
        
        # Verificar estructura JSON
        assert json_data["type"] == "chat_message"
        assert json_data["version"] == "2.0"
        assert json_data["session_id"] == "session_123"
        assert json_data["user_id"] == "user_456"
        assert json_data["payload"]["message_type"] == "chat_message"
        assert json_data["payload"]["content"] == "Hello, I need help with Python programming"
        
        # Deserializar y verificar
        parsed = parse_websocket_envelope(json_str)
        assert parsed.type == envelope.type
        assert parsed.id == envelope.id
        assert parsed.is_chat_message()
        assert parsed.payload.content == "Hello, I need help with Python programming"
    
    def test_agent_response_workflow(self):
        """Test flujo completo de respuesta del agente"""
        # Crear respuesta usando factory
        original_msg_id = str(uuid.uuid4())
        envelope = WebSocketEnvelopeFactory.create_agent_response(
            content="I can help you with Python! Here's a simple example...",
            session_id="session_123",
            user_id="user_456",
            correlation_id=original_msg_id,
            tools_used=["python_interpreter", "documentation_search"],
            execution_time=2.5,
            confidence=0.92
        )
        
        # Verificar campos del envelope
        assert envelope.type == MessageType.AGENT_RESPONSE
        assert envelope.session_id == "session_123"
        assert envelope.user_id == "user_456"
        assert envelope.correlation_id == original_msg_id
        
        # Verificar identificación de tipo
        assert envelope.is_agent_response()
        assert not envelope.is_chat_message()
        assert envelope.get_payload_type() == "agent_response"
        
        # Test JSON roundtrip
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.type == MessageType.AGENT_RESPONSE
        assert parsed.correlation_id == original_msg_id
        assert parsed.is_agent_response()
        assert parsed.payload.content.startswith("I can help you with Python!")
        assert parsed.payload.tools_used == ["python_interpreter", "documentation_search"]
        assert parsed.payload.execution_time == 2.5
        assert parsed.payload.confidence == 0.92
    
    def test_system_event_workflow(self):
        """Test flujo completo de evento del sistema"""
        envelope = WebSocketEnvelopeFactory.create_system_event(
            event_name="user_connected",
            description="New user has connected to the system",
            severity="info",
            data={"ip_address": "192.168.1.100", "timestamp": "2025-09-03T18:00:00Z"}
        )
        
        # Verificar tipo
        assert envelope.type == MessageType.SYSTEM_EVENT
        assert envelope.is_system_event()
        assert envelope.get_payload_type() == "system_event"
        
        # Test serialización
        json_str = envelope.model_dump_json()
        json_data = json.loads(json_str)
        
        assert json_data["type"] == "system_event"
        assert json_data["payload"]["event_name"] == "user_connected"
        assert json_data["payload"]["severity"] == "info"
        assert json_data["payload"]["data"]["ip_address"] == "192.168.1.100"
        
        # Test deserialización
        parsed = parse_websocket_envelope(json_str)
        assert parsed.is_system_event()
        assert parsed.payload.event_name == "user_connected"
        assert parsed.payload.severity == "info"
        assert parsed.payload.data["ip_address"] == "192.168.1.100"
    
    def test_error_event_workflow(self):
        """Test flujo completo de evento de error"""
        envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code="VALIDATION_FAILED",
            error_message="Input validation failed for user query",
            details="Query length exceeds maximum allowed characters",
            user_id="user_456"
        )
        
        # Verificar tipo
        assert envelope.type == MessageType.ERROR_EVENT
        assert envelope.is_error_event()
        assert envelope.get_payload_type() == "error_event"
        assert envelope.user_id == "user_456"
        
        # Test JSON roundtrip
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.is_error_event()
        assert parsed.payload.error_code == "VALIDATION_FAILED"
        assert parsed.payload.error_message == "Input validation failed for user query"
        assert parsed.payload.details == "Query length exceeds maximum allowed characters"
    
    def test_connection_event_workflow(self):
        """Test flujo completo de evento de conexión"""
        envelope = WebSocketEnvelopeFactory.create_connection_event(
            event_type="connected",
            client_info={"browser": "Chrome", "version": "91.0", "os": "macOS"},
            session_data={"connection_time": "2025-09-03T18:00:00Z", "protocol": "websocket"}
        )
        
        # Verificar tipo
        assert envelope.type == MessageType.CONNECTION_EVENT
        assert envelope.is_connection_event()
        assert envelope.get_payload_type() == "connection_event"
        
        # Test serialización
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.is_connection_event()
        assert parsed.payload.event_type == "connected"
        assert parsed.payload.client_info["browser"] == "Chrome"
        assert parsed.payload.session_data["protocol"] == "websocket"
    
    def test_health_check_workflow(self):
        """Test flujo completo de health check"""
        envelope = WebSocketEnvelopeFactory.create_health_check(
            status="ping"
        )
        
        # Verificar tipo
        assert envelope.type == MessageType.HEALTH_CHECK
        assert envelope.is_health_check()
        assert envelope.get_payload_type() == "health_check"
        
        # Test JSON roundtrip
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        
        assert parsed.is_health_check()
        assert parsed.payload.status == "ping"
        assert isinstance(parsed.payload.timestamp, float)


class TestCorrelationWorkflow:
    """Tests del sistema de correlación entre mensajes"""
    
    def test_complete_conversation_flow(self):
        """Test flujo completo de conversación con correlación"""
        session_id = "session_conversation_123"
        user_id = "user_alice"
        
        # 1. Usuario envía mensaje inicial
        user_message = WebSocketEnvelopeFactory.create_chat_message(
            content="What is the difference between lists and tuples in Python?",
            session_id=session_id,
            user_id=user_id
        )
        
        # 2. Agente procesa y responde
        agent_response = WebSocketEnvelopeFactory.create_agent_response(
            content="Great question! Lists and tuples are both sequence types in Python, but they have key differences...",
            session_id=session_id,
            user_id=user_id,
            correlation_id=user_message.id,
            tools_used=["python_docs", "code_examples"],
            execution_time=1.8,
            confidence=0.95
        )
        
        # 3. Usuario hace pregunta de seguimiento
        followup_message = WebSocketEnvelopeFactory.create_chat_message(
            content="Can you show me a code example?",
            session_id=session_id,
            user_id=user_id
        )
        
        # 4. Agente responde con ejemplo
        code_response = WebSocketEnvelopeFactory.create_agent_response(
            content="Certainly! Here's a practical example:\n\n```python\n# List (mutable)\nmy_list = [1, 2, 3]\nmy_list.append(4)  # This works\n\n# Tuple (immutable)\nmy_tuple = (1, 2, 3)\n# my_tuple.append(4)  # This would raise an error\n```",
            session_id=session_id,
            user_id=user_id,
            correlation_id=followup_message.id,
            tools_used=["code_generator"],
            execution_time=0.9,
            confidence=0.98
        )
        
        # Verificar correlaciones
        assert agent_response.correlation_id == user_message.id
        assert code_response.correlation_id == followup_message.id
        
        # Verificar que todos pertenecen a la misma sesión
        messages = [user_message, agent_response, followup_message, code_response]
        for msg in messages:
            assert msg.session_id == session_id
            assert msg.user_id == user_id
        
        # Verificar que los IDs son únicos
        ids = [msg.id for msg in messages]
        assert len(set(ids)) == 4  # Todos únicos
        
        # Test serialización de toda la conversación
        conversation_json = []
        for msg in messages:
            json_str = msg.model_dump_json()
            parsed = parse_websocket_envelope(json_str)
            conversation_json.append(parsed)
        
        # Verificar que la conversación se preserva
        assert conversation_json[0].is_chat_message()
        assert conversation_json[1].is_agent_response()
        assert conversation_json[1].correlation_id == conversation_json[0].id
        assert conversation_json[2].is_chat_message()
        assert conversation_json[3].is_agent_response()
        assert conversation_json[3].correlation_id == conversation_json[2].id


class TestErrorScenariosAndEdgeCases:
    """Tests de escenarios de error y casos límite"""
    
    def test_invalid_json_handling(self):
        """Test manejo de JSON inválido"""
        invalid_cases = [
            "not json at all",
            '{"type": "chat_message"}',  # Falta payload
            '{"payload": {"content": "test"}}',  # Falta type
            '{"type": "invalid_type", "payload": {"message_type": "chat_message", "content": "test"}}'  # Tipo inválido
        ]
        
        for invalid_json in invalid_cases:
            with pytest.raises(Exception):
                parse_websocket_envelope(invalid_json)
    
    def test_empty_content_handling(self):
        """Test manejo de contenido vacío"""
        with pytest.raises(ValueError):
            # Content no puede estar vacío
            WebSocketEnvelopeFactory.create_chat_message(content="")
    
    def test_long_content_handling(self):
        """Test manejo de contenido muy largo"""
        # Content muy largo (más de 10000 caracteres)
        long_content = "x" * 10001
        
        with pytest.raises(ValueError):
            WebSocketEnvelopeFactory.create_chat_message(content=long_content)
    
    def test_confidence_validation(self):
        """Test validación de confidence fuera de rango"""
        with pytest.raises(ValueError):
            WebSocketEnvelopeFactory.create_agent_response(
                content="Test",
                confidence=1.5  # Fuera del rango 0.0-1.0
            )
        
        with pytest.raises(ValueError):
            WebSocketEnvelopeFactory.create_agent_response(
                content="Test", 
                confidence=-0.1  # Fuera del rango 0.0-1.0
            )


class TestPerformanceAndOptimization:
    """Tests de rendimiento y optimización"""
    
    def test_large_batch_serialization(self):
        """Test serialización de lote grande de mensajes"""
        # Crear 100 mensajes
        messages = []
        for i in range(100):
            msg = WebSocketEnvelopeFactory.create_chat_message(
                content=f"Test message number {i}",
                session_id=f"session_{i % 10}",
                user_id=f"user_{i % 5}"
            )
            messages.append(msg)
        
        # Serializar todos
        serialized = []
        for msg in messages:
            json_str = msg.model_dump_json()
            serialized.append(json_str)
        
        # Deserializar todos
        deserialized = []
        for json_str in serialized:
            parsed = parse_websocket_envelope(json_str)
            deserialized.append(parsed)
        
        # Verificar que todos se procesaron correctamente
        assert len(deserialized) == 100
        for i, msg in enumerate(deserialized):
            assert msg.is_chat_message()
            assert msg.payload.content == f"Test message number {i}"
    
    def test_unique_id_generation(self):
        """Test que los IDs generados son únicos"""
        # Crear 1000 mensajes y verificar que todos tienen IDs únicos
        messages = []
        for i in range(1000):
            msg = WebSocketEnvelopeFactory.create_chat_message(content=f"Test {i}")
            messages.append(msg)
        
        # Extraer todos los IDs
        ids = [msg.id for msg in messages]
        
        # Verificar que son únicos
        assert len(set(ids)) == 1000
        
        # Verificar que todos son strings válidos
        for msg_id in ids:
            assert isinstance(msg_id, str)
            assert len(msg_id) > 0


def test_system_integration():
    """Test de integración del sistema completo"""
    print("\n🧪 Testing complete WebSocket Envelope System...")
    
    # Simular flujo completo de QA
    session_id = "integration_test_session"
    user_id = "test_user_qa"
    
    # 1. Usuario se conecta
    connection_event = WebSocketEnvelopeFactory.create_connection_event(
        event_type="connected",
        client_info={"browser": "Test Browser"},
        session_data={"test": True}
    )
    connection_event.session_id = session_id
    connection_event.user_id = user_id
    
    # 2. Usuario hace pregunta
    question = WebSocketEnvelopeFactory.create_chat_message(
        content="How do I implement a binary search algorithm in Python?",
        session_id=session_id,
        user_id=user_id
    )
    
    # 3. Sistema procesa y responde
    answer = WebSocketEnvelopeFactory.create_agent_response(
        content="Here's a clean implementation of binary search in Python...",
        session_id=session_id,
        user_id=user_id,
        correlation_id=question.id,
        tools_used=["algorithm_library", "code_generator"],
        execution_time=3.2,
        confidence=0.97
    )
    
    # 4. Health check
    health = WebSocketEnvelopeFactory.create_health_check(status="ping")
    
    # 5. Error handling (simulado)
    error = WebSocketEnvelopeFactory.create_error_event(
        error_code="RATE_LIMIT",
        error_message="Too many requests",
        user_id=user_id
    )
    
    # Serializar todo el flujo
    flow = [connection_event, question, answer, health, error]
    serialized_flow = []
    
    for envelope in flow:
        json_str = envelope.model_dump_json()
        parsed = parse_websocket_envelope(json_str)
        serialized_flow.append(parsed)
    
    # Verificar el flujo completo
    assert serialized_flow[0].is_connection_event()
    assert serialized_flow[1].is_chat_message()
    assert serialized_flow[2].is_agent_response()
    assert serialized_flow[2].correlation_id == serialized_flow[1].id
    assert serialized_flow[3].is_health_check()
    assert serialized_flow[4].is_error_event()
    
    print("✅ Complete WebSocket Envelope System Integration Test PASSED")
    print(f"✅ Processed {len(flow)} different envelope types successfully")
    print("✅ JSON serialization/deserialization working perfectly")
    print("✅ Correlation system working correctly")
    print("✅ Type safety validated")
    print("🎉 WebSocket Envelope System with Discriminated Unions is FULLY FUNCTIONAL!")


if __name__ == "__main__":
    # Ejecutar test de integración
    test_system_integration()
    
    # Ejecutar todos los tests
    pytest.main([__file__, "-v"])
