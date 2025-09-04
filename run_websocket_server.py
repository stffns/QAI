#!/usr/bin/env python3
"""
WebSocket Server Launcher for QA Intelligence
Simplified startup script for the WebSocket server
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

async def start_websocket_server():
    """Start the WebSocket server"""
    try:
        # Import WebSocket server components
        from src.websocket.server import create_websocket_server
        from config.models import WebSocketConfig, ServerConfig, SecurityConfig, AuthenticationConfig, CorsConfig
        
        print("🔧 Loading WebSocket configuration...")
        
        # Load configuration
        try:
            from config import get_settings
            settings = get_settings()
            print("✅ Project configuration loaded")
        except ImportError:
            print("⚠️ Could not import project config, using defaults")
            settings = None
        
        # Create WebSocket configuration
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
        
        print(f"🔧 Server configuration: {ws_config.server.host}:{ws_config.server.port}")
        
        # Initialize QA Agent
        print("🤖 Initializing QA Intelligence Agent...")
        
        try:
            from src.websocket.qa_agent_adapter import QAAgentAdapter
            
            qa_agent = QAAgentAdapter(
                user_id="websocket_qa_agent@qai.com",
                enable_reasoning=False,  # Fast responses
                enable_memory=True       # Persistent memory
            )
            
            if qa_agent.is_initialized:
                print("✅ QA Agent successfully integrated!")
                status = qa_agent.get_status()
                print(f"👤 Agent User ID: {status['user_id']}")
                print(f"🧠 Reasoning: {status['reasoning_enabled']}")
                print(f"💾 Memory: {status['memory_enabled']}")
            else:
                error_msg = qa_agent.initialization_error or "Unknown initialization error"
                print(f"❌ QA Agent failed to initialize: {error_msg}")
                raise Exception(f"QA Agent initialization failed: {error_msg}")
                
        except Exception as e:
            print(f"❌ QA Agent error: {e}")
            print("🔄 Using fallback mock agent")
            
            class MockQAAgent:
                async def chat(self, message: str) -> str:
                    return f"WebSocket Echo: {message}"
                
                async def process_message(self, message: str, session_id: Optional[str] = None, 
                                        user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
                    return f"Processed via WebSocket: {message}"
            
            qa_agent = MockQAAgent()
            print("✅ Mock QA Agent ready")
        
        # Start the WebSocket server
        print("🚀 Starting WebSocket server...")
        
        async with create_websocket_server(ws_config, qa_agent) as server:
            print("=" * 60)
            print(f"🌐 WebSocket Server ACTIVE")
            print(f"📡 URL: ws://{ws_config.server.host}:{ws_config.server.port}")
            print(f"🔗 HTTP: http://{ws_config.server.host}:{ws_config.server.port}")
            print("=" * 60)
            print("Press Ctrl+C to stop the server")
            
            try:
                # Keep server running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Shutting down WebSocket server...")
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📝 Dependencies needed:")
        print("   pip install websockets fastapi uvicorn")
        raise
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        raise

def main():
    """Main entry point for WebSocket server"""
    print("🌐 QA Intelligence WebSocket Server")
    print("=" * 60)
    
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        print("\n👋 WebSocket server stopped by user")
    except Exception as e:
        print(f"❌ Error starting WebSocket server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
