"""
WebSocket Server Implementation for QA Intelligence

This module implements the main WebSocket server following SOLID principles:
- Single Responsibility: Server handles only WebSocket connections
- Open/Closed: Extensible via dependency injection  
- Liskov Substitution: Protocol-based design
- Interface Segregation: Separate protocols for different responsibilities
- Dependency Inversion: Depends on abstractions (QAAgentProtocol)

Architecture:
- Uses FastAPI + websockets for modern async WebSocket support
- Integrates with existing QAAgent via dependency injection
- Follows project's Pydantic v2 configuration pattern
- Uses Loguru logging consistent with project standards
- Implements structured exception handling
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Set, Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

import websockets
from websockets import (
    ServerConnection,
    ConnectionClosed,
    WebSocketException,
    serve
)
from pydantic import ValidationError

try:
    from src.logging_config import get_logger, LogExecutionTime, LogStep
    from src.websocket.events import WebSocketEnvelope, WebSocketEnvelopeFactory, parse_websocket_envelope
    from config.models import WebSocketConfig, ServerConfig, SecurityConfig, AuthenticationConfig, CorsConfig  # Use unified config
    from src.websocket.manager import WebSocketManager, QAAgentProtocol
    from src.websocket.security import SecurityManager
    from src.websocket.middleware import WebSocketMiddleware
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.logging_config import get_logger, LogExecutionTime, LogStep
    from src.websocket.events import WebSocketEnvelope, WebSocketEnvelopeFactory, parse_websocket_envelope
    from config.models import WebSocketConfig, ServerConfig, SecurityConfig, AuthenticationConfig, CorsConfig  # Use unified config
    from src.websocket.manager import WebSocketManager, QAAgentProtocol
    from src.websocket.security import SecurityManager
    from src.websocket.middleware import WebSocketMiddleware


class WebSocketServerError(Exception):
    """Base exception for WebSocket server errors"""
    pass


class ConnectionError(WebSocketServerError):
    """Connection-related errors"""
    pass


class AuthenticationError(WebSocketServerError):
    """Authentication-related errors"""
    pass


class RateLimitError(WebSocketServerError):
    """Rate limiting errors"""
    pass


class WebSocketServer:
    """
    Main WebSocket server implementing QA Intelligence real-time communication.
    
    Follows SOLID principles:
    - Single Responsibility: Manages WebSocket connections and message routing
    - Dependency Inversion: Depends on QAAgentProtocol abstraction
    - Open/Closed: Extensible via middleware and event system
    
    Architecture:
    - Protocol-based design for loose coupling with QAAgent
    - Event-driven message handling
    - Comprehensive security and rate limiting
    - Performance monitoring and logging
    """
    
    def __init__(
        self,
        config: WebSocketConfig,
        qa_agent: QAAgentProtocol,
        security_manager: Optional[SecurityManager] = None,
        middleware: Optional[WebSocketMiddleware] = None
    ):
        self.config = config
        self.qa_agent = qa_agent
        self.manager = WebSocketManager(qa_agent)
        self.security_manager = security_manager or SecurityManager(config.security)
        self.middleware = middleware or WebSocketMiddleware(config)
        
        # Server state
        # WebSocket server instance from websockets.serve()
        self.server: Optional[Any] = None  # WebSocket server from serve()
        self.is_running = False
        self.connections: Set[ServerConnection] = set()
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.metrics = {
            'connections_total': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors_total': 0,
            'start_time': None
        }
        
        self.logger = get_logger("WebSocketServer")
        
        # Suppress routine websockets library errors to reduce noise
        logging.getLogger("websockets.server").setLevel(logging.WARNING)
        logging.getLogger("websockets.protocol").setLevel(logging.WARNING)
        self.logger.info("WebSocket server initialized with configuration")
    
    async def start(self) -> None:
        """
        Start the WebSocket server.
        
        Implements graceful startup with proper error handling
        and resource initialization.
        """
        if self.is_running:
            self.logger.warning("Server is already running")
            return
            
        try:
            with LogExecutionTime("WebSocket server startup", "WebSocketServer"):
                # Initialize security components
                await self.security_manager.initialize()
                
                # Start the server
                self.server = await websockets.serve(
                    self._handle_connection,
                    self.config.server.host,
                    self.config.server.port,
                    max_size=self.config.server.max_message_size,
                    ping_interval=self.config.server.ping_interval,
                    ping_timeout=self.config.server.ping_timeout,
                    close_timeout=self.config.server.close_timeout,
                    compression=None if not self.config.enable_compression else "deflate"
                )
                
                self.is_running = True
                self.metrics['start_time'] = datetime.now()
                
                self.logger.info(
                    f"WebSocket server started on {self.config.server.host}:{self.config.server.port}"
                )
                
                # Start metrics collection if enabled
                if self.config.enable_metrics:
                    asyncio.create_task(self._metrics_collector())
                
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise WebSocketServerError(f"Server startup failed: {e}")
    
    async def stop(self) -> None:
        """
        Stop the WebSocket server gracefully.
        
        Closes all connections and cleans up resources.
        """
        if not self.is_running:
            self.logger.warning("Server is not running")
            return
            
        try:
            with LogExecutionTime("WebSocket server shutdown", "WebSocketServer"):
                self.is_running = False
                
                # Close all active connections
                if self.connections:
                    self.logger.info(f"Closing {len(self.connections)} active connections")
                    await asyncio.gather(
                        *[self._close_connection(conn, "Server shutdown") for conn in self.connections.copy()],
                        return_exceptions=True
                    )
                
                # Stop the server
                if self.server:
                    self.server.close()
                    await self.server.wait_closed()
                    self.server = None
                
                # Clean up resources
                await self.security_manager.cleanup()
                self.connections.clear()
                self.user_sessions.clear()
                
                self.logger.info("WebSocket server stopped successfully")
                
        except Exception as e:
            self.logger.error(f"Error during server shutdown: {e}")
            raise WebSocketServerError(f"Server shutdown failed: {e}")
    
    def _manager_supports_streaming(self) -> bool:
        """
        Check if the agent manager supports streaming responses.
        
        Returns:
            bool: True if streaming is supported and enabled, False otherwise
        """
        return hasattr(self.manager, 'process_chat_message_stream')
    
    async def _handle_connection(self, websocket: ServerConnection, path: str = "/") -> None:
        """
        Handle new WebSocket connection.
        
        Implements full connection lifecycle:
        - Authentication and security checks
        - Connection registration
        - Message processing loop
        - Graceful disconnection
        """
        connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"New connection attempt from {connection_id}")
        
        try:
            # Check connection limits
            if len(self.connections) >= self.config.server.max_connections:
                await self._send_error(websocket, "max_connections", "Server at capacity")
                await websocket.close(code=1013, reason="Server at capacity")
                return
            
            # Apply middleware (CORS, rate limiting, etc.)
            # Note: Temporary type casting until websockets types are unified
            if not await self.middleware.process_connection(websocket, path):  # type: ignore
                await websocket.close(code=1008, reason="Middleware rejected connection")
                return
            
            # Add to active connections
            self.connections.add(websocket)
            self.metrics['connections_total'] += 1
            
            # Register with manager
            user_id = await self._authenticate_connection(websocket)
            session_id = await self.manager.add_connection(websocket, user_id)
            
            # Store session info
            self.user_sessions[session_id] = {
                'user_id': user_id,
                'websocket': websocket,
                'connected_at': datetime.now(),
                'last_activity': datetime.now()
            }
            
            # Send welcome message
            welcome_event = WebSocketEnvelopeFactory.create_system_event(
                event_name="connection_established",
                description="Connected to QA Intelligence WebSocket",
                session_id=session_id,
                user_id=user_id
            )
            await self._send_event(websocket, welcome_event)
            
            self.logger.info(f"Connection established for user {user_id}, session {session_id}")
            
            # Message processing loop
            await self._message_loop(websocket, session_id, user_id)
            
        except AuthenticationError as e:
            self.logger.warning(f"Authentication failed for {connection_id}: {e}")
            await self._send_error(websocket, "authentication_failed", str(e))
            await websocket.close(code=1008, reason="Authentication failed")
            
        except RateLimitError as e:
            self.logger.warning(f"Rate limit exceeded for {connection_id}: {e}")
            await self._send_error(websocket, "rate_limit_exceeded", str(e))
            await websocket.close(code=1008, reason="Rate limit exceeded")
            
        except ConnectionClosed:
            # This is normal - don't log as an error
            self.logger.debug(f"Connection closed normally for {connection_id}")
            
        except WebSocketException as e:
            # Check if this is a routine handshake failure (common with health checks)
            error_message = str(e).lower()
            if any(phrase in error_message for phrase in [
                "no close frame", "connection closed", "handshake failed", 
                "invalid", "timeout", "refused"
            ]):
                self.logger.debug(f"Routine WebSocket handshake issue for {connection_id}: {e}")
            else:
                self.logger.error(f"WebSocket error for {connection_id}: {e}")
                self.metrics['errors_total'] += 1
            
        except Exception as e:
            self.logger.error(f"Unexpected error handling connection {connection_id}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.metrics['errors_total'] += 1
            
        finally:
            # Clean up connection
            await self._cleanup_connection(websocket)
    
    async def _authenticate_connection(self, websocket: ServerConnection) -> str:
        """
        Authenticate WebSocket connection.
        
        Returns:
            str: User ID if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.config.security.authentication.enabled:
            return "anonymous_user"
        
        # Wait for authentication message
        try:
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_message)
            
            # Validate authentication token
            user_id = await self.security_manager.authenticate_token(auth_data.get('token'))
            
            if not user_id:
                raise AuthenticationError("Invalid authentication token")
                
            return user_id
            
        except asyncio.TimeoutError:
            raise AuthenticationError("Authentication timeout")
        except json.JSONDecodeError:
            raise AuthenticationError("Invalid authentication message format")
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {e}")
    
    async def _message_loop(self, websocket: ServerConnection, session_id: str, user_id: str) -> None:
        """
        Main message processing loop for a connection.
        
        Handles incoming messages and routes them appropriately.
        """
        from websockets import State
        
        while self.is_running and websocket.state == State.OPEN:
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.recv(), 
                    timeout=self.config.server.ping_timeout
                )
                
                # Convert bytes-like data to string if necessary
                if isinstance(raw_message, (bytes, bytearray, memoryview)):
                    message_data = bytes(raw_message).decode('utf-8')
                else:
                    message_data = str(raw_message)
                
                self.metrics['messages_received'] += 1
                self.user_sessions[session_id]['last_activity'] = datetime.now()
                
                # Apply rate limiting
                if not await self.security_manager.check_rate_limit(user_id):
                    await self._send_error(websocket, "rate_limit", "Rate limit exceeded")
                    continue
                
                # Parse and process message
                await self._process_message(websocket, message_data, session_id, user_id)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.ping()
                except ConnectionClosed:
                    break
                    
            except ConnectionClosed:
                self.logger.info(f"Connection closed for session {session_id}")
                break
                
            except Exception as e:
                self.logger.error(f"Error processing message for session {session_id}: {e}")
                await self._send_error(websocket, "processing_error", "Message processing failed")
    
    async def _process_message(
        self, 
        websocket: ServerConnection, 
        message_data: str, 
        session_id: str, 
        user_id: str
    ) -> None:
        """
        Process incoming WebSocket message.
        
        Parses the message, validates it, and routes it to the appropriate handler.
        """
        try:
            # Parse message as WebSocket envelope
            envelope = parse_websocket_envelope(message_data)
            
            with LogStep(f"Processing {envelope.type} envelope", "WebSocketServer"):
                
                if envelope.is_chat_message():
                    await self._handle_chat_message(websocket, envelope, session_id, user_id)
                    
                elif envelope.type == "system_event":
                    await self._handle_system_event(websocket, envelope, session_id, user_id)
                    
                else:
                    self.logger.warning(f"Unknown envelope type: {envelope.type}")
                    await self._send_error(websocket, "unknown_event", f"Unknown envelope type: {envelope.type}")
                    
        except ValidationError as e:
            self.logger.error(f"Message validation error: {e}")
            await self._send_error(websocket, "validation_error", "Invalid message format")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            await self._send_error(websocket, "json_error", "Invalid JSON format")
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await self._send_error(websocket, "processing_error", "Message processing failed")
    
    async def _handle_chat_message(
        self, 
        websocket: ServerConnection, 
        chat_envelope: WebSocketEnvelope, 
        session_id: str, 
        user_id: str
    ) -> None:
        """
        Handle chat message from client with streaming support.
        
        Processes the message through QAAgent and sends response back in chunks.
        """
        try:
            with LogExecutionTime(f"Chat message processing", "WebSocketServer"):
                
                # Extract chat payload (type-safe access)
                if not chat_envelope.is_chat_message():
                    raise ValueError("Expected chat message envelope")
                
                # Type-safe access to chat payload
                from src.websocket.events import ChatMessagePayload
                chat_payload = chat_envelope.payload
                if not isinstance(chat_payload, ChatMessagePayload):
                    raise ValueError("Expected ChatMessagePayload")
                
                # Check if streaming is available and process accordingly
                if self._manager_supports_streaming():
                    # Use streaming version
                    self.logger.info(f"📡 Processing chat message with streaming for session {session_id}")
                    
                    # Send stream start
                    start_envelope = WebSocketEnvelopeFactory.create_agent_response_stream_start(
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=chat_envelope.id,
                        response_type="text"
                    )
                    await self._send_event(websocket, start_envelope)
                    
                    # Process and send chunks
                    full_response = ""
                    chunk_index = 0
                    chunk_count = 0
                    
                    async for chunk in self.manager.process_chat_message_stream(
                        message=chat_payload.content,
                        session_id=session_id,
                        user_id=user_id,
                        metadata=chat_payload.metadata
                    ):
                        if chunk.strip():  # Only send non-empty chunks
                            chunk_envelope = WebSocketEnvelopeFactory.create_agent_response_stream_chunk(
                                chunk=chunk,
                                chunk_index=chunk_index,
                                session_id=session_id,
                                user_id=user_id,
                                correlation_id=chat_envelope.id,
                                is_complete=False
                            )
                            await self._send_event(websocket, chunk_envelope)
                            full_response += chunk
                            chunk_index += 1
                            chunk_count += 1
                    
                    # Send stream end
                    end_envelope = WebSocketEnvelopeFactory.create_agent_response_stream_end(
                        total_chunks=chunk_count,
                        full_content=full_response,
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=chat_envelope.id
                    )
                    await self._send_event(websocket, end_envelope)
                    
                    self.logger.info(f"✅ Streaming chat message completed for session {session_id} ({chunk_count} chunks)")
                else:
                    # Fallback to non-streaming version
                    self.logger.info(f"📝 Processing chat message (non-streaming) for session {session_id}")
                    
                    # Process message through QA Agent
                    response = await self.manager.process_chat_message(
                        message=chat_payload.content,
                        session_id=session_id,
                        user_id=user_id,
                        metadata=chat_payload.metadata
                    )
                    
                    # Create and send response envelope
                    response_envelope = WebSocketEnvelopeFactory.create_agent_response(
                        content=response,
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=chat_envelope.id
                    )
                    
                    await self._send_event(websocket, response_envelope)
                    
                    self.logger.info(f"Processed chat message for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Error handling chat message: {e}")
            
            # Enhanced error handling with OpenAI health information
            try:
                from src.websocket.health_middleware import enhance_websocket_error, should_check_openai_health
                
                error_message = f"Failed to process chat message: {str(e)}"
                
                # Check if we should include OpenAI health info
                if should_check_openai_health(error_message):
                    enhanced_error = await enhance_websocket_error(error_message, {
                        "original_exception": str(e),
                        "session_id": session_id,
                        "user_id": user_id
                    })
                    
                    # Create enhanced error response with health context
                    details_dict = {
                        "original_envelope_id": chat_envelope.id,
                        "openai_health": {
                            "status": enhanced_error.get("openai_status"),
                            "message": enhanced_error.get("openai_message"),
                            "likely_cause": enhanced_error.get("likely_cause"),
                            "can_make_requests": enhanced_error.get("can_make_requests", True)
                        } if enhanced_error.get("openai_health_checked") else None,
                        "suggestion": enhanced_error.get("service_suggestion")
                    }
                    
                    error_envelope = WebSocketEnvelopeFactory.create_error_event(
                        error_code="chat_processing_error_with_health",
                        error_message=enhanced_error.get("user_message", error_message),
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=chat_envelope.id,
                        details=json.dumps(details_dict)
                    )
                else:
                    # Standard error response
                    error_envelope = WebSocketEnvelopeFactory.create_error_event(
                        error_code="chat_processing_error",
                        error_message="Failed to process chat message",
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=chat_envelope.id,
                        details=f"original_envelope_id: {chat_envelope.id}"
                    )
                    
            except Exception as health_error:
                self.logger.error(f"Error enhancing error with health info: {health_error}")
                
                # Fallback to basic error response
                error_envelope = WebSocketEnvelopeFactory.create_error_event(
                    error_code="chat_processing_error",
                    error_message="Failed to process chat message",
                    session_id=session_id,
                    user_id=user_id,
                    correlation_id=chat_envelope.id,
                    details=f"original_envelope_id: {chat_envelope.id}"
                )
            
            await self._send_event(websocket, error_envelope)
    
    async def _handle_system_event(
        self, 
        websocket: ServerConnection, 
        envelope: WebSocketEnvelope, 
        session_id: str, 
        user_id: str
    ) -> None:
        """Handle system events (ping, status, etc.)"""
        
        if envelope.is_system_event():
            from src.websocket.events import SystemEventPayload
            system_payload = envelope.payload
            if isinstance(system_payload, SystemEventPayload):
                
                if system_payload.event_name == "ping":
                    # Respond with pong
                    pong_envelope = WebSocketEnvelopeFactory.create_health_check(
                        status="pong",
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=envelope.id
                    )
                    await self._send_event(websocket, pong_envelope)
                
                elif system_payload.event_name == "status":
                    # Send server status
                    status_envelope = WebSocketEnvelopeFactory.create_system_event(
                        event_name="server_status",
                        description="Current server status",
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=envelope.id,
                        data={
                            'connections': len(self.connections) if hasattr(self, 'connections') else 0,
                            'uptime': 0,  # Simplified for now
                            'messages_processed': self.metrics['messages_received']
                        }
                    )
                    await self._send_event(websocket, status_envelope)
                
                elif system_payload.event_name == "openai_health":
                    # Check OpenAI service health
                    try:
                        from src.websocket.health_middleware import get_service_status_for_websocket
                        health_status = await get_service_status_for_websocket()
                        
                        health_envelope = WebSocketEnvelopeFactory.create_system_event(
                            event_name="openai_health_status",
                            description="OpenAI service health status",
                            session_id=session_id,
                            user_id=user_id,
                            correlation_id=envelope.id,
                            data=health_status
                        )
                        await self._send_event(websocket, health_envelope)
                        
                    except Exception as e:
                        self.logger.error(f"Error checking OpenAI health: {e}")
                        
                        error_envelope = WebSocketEnvelopeFactory.create_error_event(
                            error_code="health_check_failed",
                            error_message="Failed to check OpenAI service health",
                            session_id=session_id,
                            user_id=user_id,
                            correlation_id=envelope.id,
                            details=str(e)
                        )
                        await self._send_event(websocket, error_envelope)
    
    async def _send_event(self, websocket: ServerConnection, event: WebSocketEnvelope) -> None:
        """Send WebSocket envelope to client"""
        try:
            message = event.model_dump_json()
            await websocket.send(message)
            self.metrics['messages_sent'] += 1
            
        except ConnectionClosed:
            self.logger.debug("Connection closed while sending event")
        except Exception as e:
            self.logger.error(f"Error sending event: {e}")
    
    async def _send_error(self, websocket: ServerConnection, error_type: str, message: str) -> None:
        """Send error event to client"""
        error_envelope = WebSocketEnvelopeFactory.create_error_event(
            error_code=error_type,
            error_message=message,
            session_id="unknown",
            user_id="unknown"
        )
        await self._send_event(websocket, error_envelope)
    
    async def _close_connection(self, websocket: ServerConnection, reason: str) -> None:
        """Close WebSocket connection gracefully"""
        try:
            await websocket.close(code=1000, reason=reason)
        except Exception as e:
            self.logger.debug(f"Error closing connection: {e}")
    
    async def _cleanup_connection(self, websocket: ServerConnection) -> None:
        """Clean up connection resources"""
        try:
            # Remove from active connections
            self.connections.discard(websocket)
            
            # Remove from manager
            await self.manager.remove_connection(websocket)
            
            # Clean up session data
            session_to_remove = None
            for session_id, session_data in self.user_sessions.items():
                if session_data['websocket'] == websocket:
                    session_to_remove = session_id
                    break
            
            if session_to_remove:
                del self.user_sessions[session_to_remove]
                self.logger.debug(f"Cleaned up session {session_to_remove}")
                
        except Exception as e:
            self.logger.error(f"Error during connection cleanup: {e}")
    
    async def _metrics_collector(self) -> None:
        """Collect and log performance metrics periodically"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.metrics_interval)
                
                uptime = (datetime.now() - self.metrics['start_time']).total_seconds() if self.metrics['start_time'] else 0
                
                metrics_data = {
                    'active_connections': len(self.connections),
                    'total_connections': self.metrics['connections_total'],
                    'messages_sent': self.metrics['messages_sent'],
                    'messages_received': self.metrics['messages_received'],
                    'errors_total': self.metrics['errors_total'],
                    'uptime_seconds': uptime
                }
                
                self.logger.info(f"WebSocket metrics: {metrics_data}")
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get current server status"""
        return {
            'running': self.is_running,
            'host': self.config.server.host,
            'port': self.config.server.port,
            'active_connections': len(self.connections),
            'metrics': self.metrics.copy()
        }


@asynccontextmanager
async def create_websocket_server(
    config: WebSocketConfig,
    qa_agent: QAAgentProtocol
) -> AsyncGenerator[WebSocketServer, None]:
    """
    Context manager for creating and managing WebSocket server lifecycle.
    
    Usage:
        async with create_websocket_server(config, qa_agent) as server:
            # Server is running
            await server.wait_closed()
    """
    server = WebSocketServer(config, qa_agent)
    
    try:
        await server.start()
        yield server
    finally:
        await server.stop()


# Example usage and integration point
if __name__ == "__main__":
    async def main():
        """Example server startup"""
        try:
            # Import from project root config module 
            import sys, os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from config import get_settings
        except ImportError:
            # Fallback configuration if project config not available
            print("Warning: Could not import project config, using default WebSocket config")
            get_settings = None
        
        # Load configuration
        if get_settings:
            settings = get_settings()
            # Extract WebSocket config if available, otherwise use defaults
            ws_config = WebSocketConfig(
                server=ServerConfig(host='127.0.0.1', port=8765),
                security=SecurityConfig(
                    authentication=AuthenticationConfig(enabled=False),
                    cors=CorsConfig(
                        enabled=True,
                        origins=["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]
                    )
                )
            )
        else:
            # Use default configuration
            ws_config = WebSocketConfig(
                server=ServerConfig(host='127.0.0.1', port=8765),
                security=SecurityConfig(
                    authentication=AuthenticationConfig(enabled=False),
                    cors=CorsConfig(
                        enabled=True,
                        origins=["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]
                    )
                )
            )
        
        # QA Intelligence Agent Integration
        print("🔧 Initializing QA Intelligence Agent...")
        
        try:
            from src.websocket.qa_agent_adapter import QAAgentAdapter
            
            # Initialize QA Agent with optimal performance (no reasoning for fast responses)
            qa_agent = QAAgentAdapter(
                user_id="websocket_qa_agent@qai.com",
                enable_reasoning=False,  # Disabled for fast responses (no 100+ second delays)
                enable_memory=True       # Keep persistent memory
            )
            
            # Validate initialization
            if qa_agent.is_initialized:
                print("✅ QA Intelligence Agent successfully integrated!")
                
                # Log detailed status
                status = qa_agent.get_status()
                print(f"👤 Agent User ID: {status['user_id']}")
                print(f"🧠 Reasoning Enabled: {status['reasoning_enabled']}")
                print(f"💾 Memory Enabled: {status['memory_enabled']}")
                
                # Log component status
                components = status['components']
                print("📋 Component Status:")
                for component, active in components.items():
                    status_emoji = "✅" if active else "❌"
                    print(f"  {status_emoji} {component}")
                    
            else:
                error_msg = qa_agent.initialization_error or "Unknown initialization error"
                print(f"❌ QA Agent failed to initialize: {error_msg}")
                raise Exception(f"QA Agent initialization failed: {error_msg}")
                
        except ImportError as e:
            print(f"❌ Could not import QA Agent Adapter: {e}")
            print("🔄 Falling back to Mock QA Agent for testing")
            raise e
        except Exception as e:
            print(f"❌ QA Agent initialization error: {e}")
            print("🔄 Falling back to Mock QA Agent for testing")
            raise e
            
            # Fallback Mock QA Agent for testing
            class MockQAAgent:
                async def chat(self, message: str, session_id: Optional[str] = None, 
                              user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
                    return f"Echo: {message}"
                
                async def process_message(self, message: str, session_id: Optional[str] = None,
                                        user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
                    return f"Processed: {message}"
            
            qa_agent = MockQAAgent()
        
        # Start server
        async with create_websocket_server(ws_config, qa_agent) as server:
            print(f"WebSocket server running on {ws_config.server.host}:{ws_config.server.port}")
            print("Press Ctrl+C to stop")
            
            try:
                # Keep server running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")

    asyncio.run(main())
