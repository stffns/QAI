"""
WebSocket Manager - Coordinador principal del sistema WebSocket

Gestiona conexiones, sesiones y la integración con QAAgent como servicio externo.
Mantiene separación total del framework Agno siguiendo principios SOLID.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Protocol, Set

try:
    from src.logging_config import LogExecutionTime, LogStep, get_logger
    from src.websocket.events import (
        SystemEventPayload,
        WebSocketEnvelope,
        WebSocketEnvelopeFactory,
    )
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.logging_config import LogExecutionTime, LogStep, get_logger
    from src.websocket.events import (
        SystemEventPayload,
        WebSocketEnvelope,
        WebSocketEnvelopeFactory,
    )


class QAAgentProtocol(Protocol):
    """
    Protocol que define la interfaz que debe implementar QAAgent
    para ser usado por el sistema WebSocket
    """

    async def chat(self, message: str) -> str:
        """
        Procesar mensaje de chat y retornar respuesta

        Args:
            message: Mensaje del usuario

        Returns:
            Respuesta del agente
        """
        ...

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process message with additional context.

        Args:
            message: User message
            session_id: Session identifier
            user_id: User identifier
            metadata: Additional message metadata

        Returns:
            Agent response
        """
        ...


class ConnectionInfo:
    """Información de una conexión WebSocket activa"""

    def __init__(self, connection_id: str, websocket, user_id: str, session_id: str):
        self.connection_id = connection_id
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.message_count = 0

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        self.message_count += 1


class WebSocketManager:
    """
    Manager principal del sistema WebSocket para QA Intelligence

    Responsabilidades:
    - Gestión de conexiones WebSocket activas
    - Coordinación con QAAgent como servicio externo
    - Manejo de sesiones y usuarios
    - Broadcasting de eventos del sistema
    - Monitoreo y estadísticas de uso

    Arquitectura:
    - Protocol-based design para QAAgent integration
    - Event-driven messaging system
    - Async/await para performance
    - Comprehensive logging and metrics
    """

    def __init__(self, qa_agent: QAAgentProtocol):
        """
        Initialize WebSocket manager with QA Agent.

        Args:
            qa_agent: QA Agent instance implementing the protocol
        """
        # External service integration
        self.qa_agent = qa_agent

        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> user_id mapping
        self.user_connections: Dict[str, Set[str]] = (
            {}
        )  # user_id -> set of connection_ids

        # Server state
        self.is_running = False
        self.connection_counter = 0

        # Performance tracking
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "start_time": None,
        }

        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()

        # Logging
        self.logger = get_logger("WebSocketManager")

        self.logger.info(
            "WebSocketManager initialized",
            extra={"qa_agent_type": type(qa_agent).__name__},
        )

    async def start(self) -> None:
        """Start the WebSocket manager"""
        if self.is_running:
            return

        self.is_running = True
        self.stats["start_time"] = datetime.now()

        # Start background tasks
        cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        stats_task = asyncio.create_task(self._periodic_stats())

        self._background_tasks.add(cleanup_task)
        self._background_tasks.add(stats_task)

        self.logger.info("WebSocketManager started")

    async def stop(self) -> None:
        """Stop the manager and clean up all connections"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        self.logger.info("WebSocketManager stopped")

    async def add_connection(
        self, websocket, user_id: str, session_id: Optional[str] = None
    ) -> str:
        """
        Add new WebSocket connection.

        Args:
            websocket: WebSocket connection object
            user_id: User identifier
            session_id: Optional session identifier

        Returns:
            str: Generated session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        connection_id = str(uuid.uuid4())

        # Create connection info
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Store connection
        self.connections[connection_id] = connection_info
        self.sessions[session_id] = user_id

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        # Update stats
        self.connection_counter += 1
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connections)

        self.logger.info(
            "WebSocket connection added",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "session_id": session_id,
                "total_connections": self.stats["active_connections"],
            },
        )

        return session_id

    async def remove_connection(self, websocket) -> None:
        """
        Remove WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        # Find connection by websocket object
        connection_to_remove = None
        for conn_id, conn_info in self.connections.items():
            if conn_info.websocket == websocket:
                connection_to_remove = (conn_id, conn_info)
                break

        if not connection_to_remove:
            self.logger.warning("Attempted to remove non-existent connection")
            return

        connection_id, connection_info = connection_to_remove
        user_id = connection_info.user_id
        session_id = connection_info.session_id

        # Clean up references
        del self.connections[connection_id]
        self.sessions.pop(session_id, None)

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Update stats
        self.stats["active_connections"] = len(self.connections)

        self.logger.info(
            "WebSocket connection removed",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "session_id": session_id,
                "remaining_connections": self.stats["active_connections"],
            },
        )

    async def process_chat_message(
        self,
        message: str,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process chat message through QA Agent.

        Args:
            message: User message content
            session_id: Session identifier
            user_id: User identifier
            metadata: Optional message metadata

        Returns:
            str: Agent response

        Raises:
            Exception: If processing fails
        """
        try:
            with LogExecutionTime("Chat message processing", "WebSocketManager"):

                # Check if QA Agent supports enhanced processing
                if hasattr(self.qa_agent, "process_message"):
                    response = await self.qa_agent.process_message(
                        message=message,
                        session_id=session_id,
                        user_id=user_id,
                        metadata=metadata,
                    )
                else:
                    # Fallback to basic chat method
                    response = await self.qa_agent.chat(message)

                # Update stats
                self.stats["messages_processed"] += 1

                # Update connection activity
                for conn_info in self.connections.values():
                    if conn_info.session_id == session_id:
                        conn_info.update_activity()
                        break

                self.logger.info(
                    "Chat message processed successfully",
                    extra={
                        "session_id": session_id,
                        "user_id": user_id,
                        "message_length": len(message),
                        "response_length": len(response),
                    },
                )

                return response

        except Exception as e:
            self.stats["messages_failed"] += 1

            self.logger.error(
                "Error processing chat message",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                    "message_preview": message[:100],
                },
            )

            # Re-raise to be handled by caller
            raise

    async def process_chat_message_stream(
        self,
        message: str,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Process chat message through QA Agent with streaming support.

        Args:
            message: User message content
            session_id: Session identifier
            user_id: User identifier
            metadata: Optional message metadata

        Yields:
            str: Response chunks as they are generated

        Raises:
            Exception: If processing fails
        """
        try:
            with LogExecutionTime(
                "Chat message streaming processing", "WebSocketManager"
            ):

                # Check if QA Agent supports streaming processing
                if hasattr(self.qa_agent, "process_message_stream") and callable(
                    getattr(self.qa_agent, "process_message_stream")
                ):
                    async for chunk in self.qa_agent.process_message_stream(  # type: ignore
                        message=message,
                        session_id=session_id,
                        user_id=user_id,
                        metadata=metadata,
                    ):
                        yield chunk
                else:
                    # Fallback to non-streaming method
                    response = await self.process_chat_message(
                        message, session_id, user_id, metadata
                    )
                    # Simulate streaming by chunking the response
                    chunk_size = 30
                    for i in range(0, len(response), chunk_size):
                        chunk = response[i : i + chunk_size]
                        yield chunk
                        await asyncio.sleep(0.03)  # Small delay for streaming effect

                # Update stats
                self.stats["messages_processed"] += 1

                # Update connection activity
                for conn_info in self.connections.values():
                    if conn_info.session_id == session_id:
                        conn_info.update_activity()
                        break

                self.logger.info(
                    "Chat message processed successfully (streaming)",
                    extra={
                        "session_id": session_id,
                        "user_id": user_id,
                        "message_length": len(message),
                    },
                )

        except Exception as e:
            self.stats["messages_failed"] += 1

            self.logger.error(
                "Error processing chat message (streaming)",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                    "message_preview": message[:100],
                },
            )

            # Re-raise to be handled by caller
            raise

    async def broadcast_system_event(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        severity: Literal["info", "warning", "error", "critical"] = "info",
    ) -> None:
        """
        Broadcast system event to all active connections.

        Args:
            event_name: Name of the system event
            data: Optional event data
            severity: Event severity level
        """
        if not self.connections:
            self.logger.debug("No active connections for system event broadcast")
            return

        # Create system event
        system_event = WebSocketEnvelopeFactory.create_system_event(
            event_name=event_name, data=data, severity=severity
        )

        # Send to all connections
        sent_count = 0
        for connection_info in self.connections.values():
            try:
                await connection_info.websocket.send(system_event.to_json())
                sent_count += 1
            except Exception as e:
                self.logger.warning(
                    f"Failed to send system event to {connection_info.user_id}: {e}"
                )

        self.logger.info(
            "System event broadcasted",
            extra={
                "event_name": event_name,
                "recipients": sent_count,
                "severity": severity,
            },
        )

    async def send_to_user(self, user_id: str, event: WebSocketEnvelope) -> bool:
        """
        Send event to specific user (all their connections).

        Args:
            user_id: Target user ID
            event: Event to send

        Returns:
            bool: True if sent successfully to at least one connection
        """
        if user_id not in self.user_connections:
            return False

        connection_ids = self.user_connections[user_id].copy()
        sent_count = 0

        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    connection_info = self.connections[connection_id]
                    await connection_info.websocket.send(event.to_json())
                    sent_count += 1

                    self.logger.debug(
                        "Event sent to user",
                        extra={
                            "user_id": user_id,
                            "connection_id": connection_id,
                            "event_type": event.type,
                        },
                    )
                except Exception as e:
                    self.logger.error(f"Failed to send event to user {user_id}: {e}")

        return sent_count > 0

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all active session IDs for a user.

        Args:
            user_id: User identifier

        Returns:
            List[str]: List of active session IDs
        """
        sessions = []

        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.connections:
                    session_id = self.connections[connection_id].session_id
                    if session_id:
                        sessions.append(session_id)

        return sessions

    async def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection info by ID"""
        return self.connections.get(connection_id)

    async def _cleanup_inactive_connections(self) -> None:
        """Background task to clean up inactive connections"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                current_time = datetime.now()
                inactive_connections = []

                for connection_id, connection_info in self.connections.items():
                    # Check if connection has been inactive for more than 1 hour
                    if (current_time - connection_info.last_activity).seconds > 3600:
                        inactive_connections.append(connection_id)

                # Remove inactive connections
                for connection_id in inactive_connections:
                    if connection_id in self.connections:
                        connection_info = self.connections[connection_id]
                        self.logger.info(
                            f"Removing inactive connection: {connection_info.user_id}"
                        )
                        await self.remove_connection(connection_info.websocket)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")

    async def _periodic_stats(self) -> None:
        """Background task for periodic statistics logging"""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Every hour

                stats = await self.get_stats()
                self.logger.info("Periodic WebSocket stats", extra=stats)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in stats task: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get current manager statistics"""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        stats = {
            **self.stats,
            "uptime_seconds": uptime,
            "unique_users": len(self.user_connections),
            "total_sessions": len(self.sessions),
        }

        return stats

    @property
    def is_active(self) -> bool:
        """Check if manager is running"""
        return self.is_running

    async def shutdown(self) -> None:
        """Gracefully shutdown the manager"""
        if not self.is_running:
            return

        self.logger.info(f"Closing {len(self.connections)} active connections")

        # Send shutdown notification
        shutdown_event = WebSocketEnvelopeFactory.create_system_event(
            event_name="server_shutdown",
            data={"reason": "Server maintenance"},
            severity="warning",
        )

        # Close all connections
        for connection_info in list(self.connections.values()):
            try:
                await connection_info.websocket.send(shutdown_event.to_json())
                await connection_info.websocket.close()
            except Exception:
                pass  # Connection might already be closed

        # Clear all data
        self.connections.clear()
        self.sessions.clear()
        self.user_connections.clear()
        self.is_running = False

        await self.stop()

        self.logger.info("WebSocket manager shutdown complete")


# Example usage for testing
if __name__ == "__main__":

    async def main():
        """Test WebSocket manager"""

        # Mock QA Agent for testing
        class MockQAAgent:
            async def chat(self, message: str) -> str:
                return f"Echo: {message}"

            async def process_message(
                self,
                message: str,
                session_id: Optional[str] = None,
                user_id: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
            ) -> str:
                return f"Processed for {user_id}: {message}"

        # Create manager
        qa_agent = MockQAAgent()
        manager = WebSocketManager(qa_agent)

        # Start manager
        await manager.start()
        print("Manager started")

        # Test basic functionality
        stats = await manager.get_stats()
        print(f"Stats: {stats}")

        # Cleanup
        await manager.shutdown()
        print("Manager shutdown")

    import asyncio

    asyncio.run(main())
