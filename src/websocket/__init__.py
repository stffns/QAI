"""
QA Intelligence WebSocket System

Sistema de comunicación WebSocket independiente para QA Intelligence.
Proporciona comunicación en tiempo real con el agente QA manteniendo
separación total del framework Agno.

Arquitectura:
- src/agent/ = Solo wrappers específicos del framework Agno
- src/websocket/ = Sistema de comunicación independiente
- Comunicación = WebSocket consume QAAgent como servicio externo
"""

from .manager import WebSocketManager
from config.models import WebSocketConfig  # Use unified config system
from .middleware import WebSocketMiddleware
from .server import WebSocketServer
from .events import (
    WebSocketEnvelope,
    WebSocketEnvelopeFactory,
    ChatMessagePayload,
    AgentResponsePayload,
    SystemEventPayload,
    ErrorEventPayload,
    ConnectionEventPayload,
    HealthCheckPayload,
    parse_websocket_envelope,
    # Compatibility aliases
    WebSocketEvent,
    create_chat_message,
    create_agent_response,
    create_error_event
)

__all__ = [
    # Core classes
    "WebSocketServer",
    "WebSocketManager", 
    "WebSocketMiddleware",
    "WebSocketConfig",
    
    # Event system (new envelope-based)
    "WebSocketEnvelope",
    "WebSocketEnvelopeFactory",
    "ChatMessagePayload",
    "AgentResponsePayload", 
    "SystemEventPayload",
    "ErrorEventPayload",
    "ConnectionEventPayload",
    "HealthCheckPayload",
    "parse_websocket_envelope",
    
    # Compatibility aliases
    "WebSocketEvent",
    "create_chat_message",
    "create_agent_response", 
    "create_error_event"
]

__version__ = "1.0.0"
__author__ = "QA Intelligence Team"
