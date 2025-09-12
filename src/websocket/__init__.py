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

from config.models import WebSocketConfig  # Use unified config system

from .events import (  # Compatibility aliases
    AgentResponsePayload,
    ChatMessagePayload,
    ConnectionEventPayload,
    ErrorEventPayload,
    HealthCheckPayload,
    SystemEventPayload,
    WebSocketEnvelope,
    WebSocketEnvelopeFactory,
    WebSocketEvent,
    create_agent_response,
    create_chat_message,
    create_error_event,
    parse_websocket_envelope,
)
from .manager import WebSocketManager
from .middleware import WebSocketMiddleware
from .server import WebSocketServer

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
    "create_error_event",
]

__version__ = "1.0.0"
__author__ = "QA Intelligence Team"
