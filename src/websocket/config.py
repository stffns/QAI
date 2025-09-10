"""
Compatibility layer for WebSocket configuration.

This module re-exports WebSocketConfig from the unified config system
so existing imports like `from src.websocket.config import WebSocketConfig`
continue to work.
"""

try:
    from config.models import WebSocketConfig
except ImportError:  # Fallback when running in different execution contexts
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from config.models import WebSocketConfig  # type: ignore

__all__ = ["WebSocketConfig"]
