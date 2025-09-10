"""
QA Agent Adapter for WebSocket Integration

Adapts the QA Intelligence Agent for use with WebSocket connections following exactly the same
pattern as run_qa_agent.py with full feature support including reasoning, memory, and tools.
"""

import sys
import os
import importlib.util
import traceback
import asyncio
from typing import Optional, Dict, Any, Union, AsyncGenerator
from pathlib import Path

# Configure logging for detailed debugging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAAgentAdapter:
    """
    Adapter to integrate the real QA Intelligence Agent with WebSocket
    
    This adapter replicates EXACTLY the initialization logic from run_qa_agent.py
    maintaining ALL features:
    - Model configuration with Pydantic validation
    - Tools manager with web search, Python execution, calculator
    - Storage manager with Memory v2 and SQLite backend  
    - Reasoning capabilities (agent, model, tools)
    - Advanced memory features (user memories, agentic memory)
    - Full configuration validation and error handling
    - Response optimization for concise vs detailed answers
    """
    
    def __init__(self, user_id: str = "websocket_user@qai.com", enable_reasoning: bool = False, enable_memory: bool = True):
        """
        Initialize the QA Agent using EXACTLY the same logic as run_qa_agent.py
        
        Args:
            user_id: User context identifier for the agent
            enable_reasoning: Whether to enable reasoning capabilities  
            enable_memory: Whether to enable persistent memory
        """
        self.user_id = user_id
        self.enable_reasoning = enable_reasoning
        self.enable_memory = enable_memory
        self.agent = None
        self.config = None
        self.response_manager = None
        self.is_initialized = False
        self.initialization_error = None
        
        # Track all components for debugging
        self.components = {
            'model_manager': None,
            'tools_manager': None, 
            'storage_manager': None,
            'model': None,
            'tools': None,
            'storage': None
        }
        
        logger.info(f"🔧 Initializing QA Agent Adapter for user: {user_id}")
        logger.info(f"🧠 Reasoning enabled: {enable_reasoning}")
        logger.info(f"💾 Memory enabled: {enable_memory}")
        
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the QA Agent using EXACTLY the same logic as run_qa_agent.py"""
        try:
            # Step 1: Setup paths exactly like run_qa_agent.py
            project_root = self._setup_project_paths()
            logger.info(f"📁 Project root: {project_root}")
            
            # Step 2: Import core dependencies 
            agno_agent, openai_chat = self._import_core_dependencies()
            logger.info("✅ Core dependencies imported")
            
            # Step 3: Import and validate configuration
            config = self._import_and_validate_config(project_root)
            self.config = config
            logger.info("✅ Configuration loaded and validated")
            
            # Step 4: Import modular components
            managers = self._import_agent_components(project_root)
            logger.info("✅ Agent components imported")
            
            # Step 5: Create component managers
            model_manager, tools_manager, storage_manager = self._create_component_managers(config, managers)
            self.components['model_manager'] = model_manager
            self.components['tools_manager'] = tools_manager
            self.components['storage_manager'] = storage_manager
            logger.info("✅ Component managers created")
            
            # Step 6: Create agent components (model, tools, storage)
            model, tools, storage = self._create_agent_components(
                model_manager, tools_manager, storage_manager
            )
            self.components['model'] = model
            self.components['tools'] = tools  
            self.components['storage'] = storage
            logger.info("✅ Agent components created")
            
            # Step 7: Get all configuration sections
            interface_config, instructions, reasoning_config = self._get_configuration_sections(config)
            logger.info("✅ Configuration sections loaded")
            
            # Step 8: Prepare base agent arguments
            agent_args = self._prepare_base_agent_args(
                model, instructions, tools, storage, interface_config
            )
            logger.info("✅ Base agent arguments prepared")
            
            # Step 9: Add advanced memory capabilities
            if storage is not None and self.enable_memory:
                self._add_advanced_memory_capabilities(agent_args)
                logger.info("✅ Advanced memory capabilities added")
            
            # Step 10: Add reasoning capabilities
            if self.enable_reasoning and reasoning_config.get("enabled", False):
                self._add_reasoning_capabilities(agent_args, reasoning_config, openai_chat)
                logger.info("✅ Reasoning capabilities added")
            
            # Step 11: Create the agent
            self.agent = agno_agent(**agent_args)
            
            # ✅ Force WebSocket-specific configuration 
            # Override show_tool_calls for chat experience
            if hasattr(self.agent, 'show_tool_calls'):
                self.agent.show_tool_calls = False
                logger.info("🔧 WebSocket override: show_tool_calls = False")
            
            self.is_initialized = True
            
            logger.info("🎉 QA Agent successfully initialized for WebSocket!")
            self._log_agent_summary()
            
        except Exception as e:
            self.initialization_error = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"❌ QA Agent initialization failed: {e}")
            logger.error(f"📍 Error trace:\n{error_trace}")
            
            self.agent = None
            self.is_initialized = False
    
    def _setup_project_paths(self) -> str:
        """Setup project paths exactly like run_qa_agent.py"""
        # Get current file directory and navigate to project root
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up 3 levels: websocket -> src -> QAI
        project_root_str = str(project_root)
        
        # Change working directory to project root (same as run_qa_agent.py)
        os.chdir(project_root_str)
        
        # Add project root to Python path (same as run_qa_agent.py)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        return project_root_str
    
    def _import_core_dependencies(self):
        """Import core Agno dependencies"""
        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
            return Agent, OpenAIChat
        except ImportError as e:
            raise ImportError(f"Failed to import Agno core dependencies: {e}")
    
    def _import_and_validate_config(self, project_root: str):
        """Import and validate configuration exactly like run_qa_agent.py"""
        original_dir = os.getcwd()  # Store current directory to restore later
        try:
            # Change working directory to project root (like run_qa_agent.py)
            os.chdir(project_root)
            
            # Add project root to Python path (like run_qa_agent.py)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # Clear any conflicting config modules from cache (including websocket config)
            modules_to_clear = ['config', 'src.websocket.config', 'config.models']
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.info(f"🗑️  Cleared module from cache: {module_name}")
            
            # Import config exactly like run_qa_agent.py does
            # We need to ensure it imports from project root, not websocket config
            import config
            logger.info(f"📦 Config module imported from: {config.__file__}")
            
            from config import get_settings
            config = get_settings()
            
            # Validate configuration using modern Pydantic validation
            try:
                # Modern settings object is self-validating via Pydantic
                # Just verify it's accessible
                _ = config.model
                _ = config.tools
                _ = config.database
                logger.info("✅ Configuration validation successful")
            except Exception as e:
                raise ValueError(f"Configuration validation error: {e}")
            
            # Restore original directory
            os.chdir(original_dir)
            
            logger.info(f"📋 Configuration loaded from: {project_root}/config.py")
            return config
            
        except ImportError as e:
            # Restore original directory in case of error
            try:
                os.chdir(original_dir)
            except:
                pass
            raise ImportError(f"Failed to import configuration: {e}")
        except Exception as e:
            # Restore original directory in case of error
            try:
                os.chdir(original_dir)
            except:
                pass
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _import_agent_components(self, project_root: str):
        """Import modular agent components exactly like run_qa_agent.py"""
        original_dir = os.getcwd()  # Store current directory to restore later
        try:
            # Change working directory to project root (like run_qa_agent.py)
            os.chdir(project_root)
            
            # Add project root to Python path (like run_qa_agent.py)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
                
            # Add agent directory to path (like run_qa_agent.py)
            agent_dir = os.path.join(project_root, 'src', 'agent')
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            
            logger.info(f"📂 Project root: {project_root}")
            logger.info(f"📂 Agent directory: {agent_dir}")
            logger.info(f"� Changed working directory to: {project_root}")
            
            # Clear any existing manager modules from cache to avoid conflicts
            manager_modules = [
                'model_manager', 'tools_manager', 'storage_manager',
                'config.models', 'config'  # Clear config modules too
            ]
            for module_name in manager_modules:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.info(f"🗑️  Cleared module from cache: {module_name}")
            
            # Import manager classes directly (like run_qa_agent.py does)
            from src.agent.model_manager import ModelManager
            from src.agent.tools_manager import ToolsManager
            from src.agent.storage_manager import StorageManager
            from src.agent.response_manager import ResponseManager
            
            logger.info("✅ All manager classes imported successfully")
            
            # Restore original directory
            os.chdir(original_dir)
            
            return {
                'ModelManager': ModelManager,
                'ToolsManager': ToolsManager,
                'StorageManager': StorageManager,
                'ResponseManager': ResponseManager
            }
            
        except Exception as e:
            # Restore original directory in case of error
            try:
                os.chdir(original_dir)
            except:
                pass
            raise ImportError(f"Failed to import agent components: {e}")
    
    def _create_component_managers(self, config, managers):
        """Create component managers exactly like run_qa_agent.py"""
        try:
            model_manager = managers['ModelManager'](config)
            tools_manager = managers['ToolsManager'](config)
            storage_manager = managers['StorageManager'](config)
            response_manager = managers['ResponseManager'](config)
            
            # Store response manager for later use
            self.response_manager = response_manager
            
            return model_manager, tools_manager, storage_manager
            
        except Exception as e:
            raise RuntimeError(f"Failed to create component managers: {e}")
    
    def _create_agent_components(self, model_manager, tools_manager, storage_manager):
        """Create agent components exactly like run_qa_agent.py"""
        try:
            # Create model
            model = model_manager.create_model()
            logger.info(f"📱 Model created: {type(model).__name__}")
            
            # Load tools
            tools = tools_manager.load_tools()
            logger.info(f"🔧 Tools loaded: {len(tools)} tools")
            
            # Setup storage (only if memory is enabled)
            storage = None
            if self.enable_memory:
                storage = storage_manager.setup_storage()
                if storage:
                    logger.info("💾 Storage setup: Memory v2 with SQLite backend")
                else:
                    logger.warning("⚠️ Storage setup failed, continuing without memory")
            else:
                logger.info("🚫 Memory disabled by configuration")
            
            return model, tools, storage
            
        except Exception as e:
            raise RuntimeError(f"Failed to create agent components: {e}")
    
    def _get_configuration_sections(self, config):
        """Get all configuration sections exactly like run_qa_agent.py"""
        try:
            interface_config = config.get_interface_config()
            instructions = config.get_agent_instructions()
            
            # Build reasoning config manually like run_qa_agent.py does
            reasoning_config = {"enabled": False, "type": "agent"}  # Default reasoning config
            if self.enable_reasoning:
                reasoning_config["enabled"] = True
                reasoning_config["type"] = "agent"  # Default to agent reasoning
            
            return interface_config, instructions, reasoning_config
            
        except Exception as e:
            raise RuntimeError(f"Failed to get configuration sections: {e}")
    
    def _get_config_value(self, websocket_config: dict, interface_config: dict, 
                         websocket_key: str, interface_key: str, default_value):
        """
        Helper method to get configuration values with fallback chain.
        
        Args:
            websocket_config: WebSocket specific configuration
            interface_config: Interface configuration
            websocket_key: Key to look for in websocket_config
            interface_key: Key to look for in interface_config
            default_value: Default value if not found in either config
            
        Returns:
            Configuration value with proper fallback
        """
        return websocket_config.get(websocket_key, 
                                  interface_config.get(interface_key, default_value))

    def _prepare_base_agent_args(self, model, instructions, tools, storage, interface_config):
        """Prepare base agent arguments exactly like run_qa_agent.py"""
        # Get WebSocket specific configuration from agent_config.yaml
        import yaml
        try:
            with open("agent_config.yaml", "r") as f:
                raw_config = yaml.safe_load(f)
            websocket_config = raw_config.get("websocket", {})
            logger.info(f"🔧 WebSocket config loaded: {websocket_config}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load WebSocket config: {e}")
            websocket_config = {}
        
        logger.info(f"🔧 Interface config show_tool_calls: {interface_config.get('show_tool_calls', 'NOT_FOUND')}")
        
        # Get streaming configuration from model config
        model_config = self.config.get_model_config()
        stream_enabled = model_config.get("stream", False)
        logger.info(f"🔧 Model config: {model_config}")
        logger.info(f"🔧 Stream value from config: {stream_enabled}")
        
        agent_args = {
            "model": model,
            "instructions": instructions,
            "tools": tools,
            "memory": storage,
            "show_tool_calls": self._get_config_value(websocket_config, interface_config, 
                                                   "show_tool_calls", "show_tool_calls", False),
            "markdown": self._get_config_value(websocket_config, interface_config,
                                             "markdown", "enable_markdown", True),
            "add_history_to_messages": storage is not None,
            "user_id": self.user_id,  # ⭐ Contexto de usuario QA
            "stream": stream_enabled,  # ⭐ Use configuration value
        }
        
        logger.info(f"👤 User ID: {self.user_id}")
        logger.info(f"🔧 Show tool calls: {agent_args['show_tool_calls']}")
        logger.info(f"📝 Markdown enabled: {agent_args['markdown']}")
        logger.info(f"📚 History in messages: {agent_args['add_history_to_messages']}")
        logger.info(f"📡 Streaming enabled: {agent_args['stream']}")
        
        return agent_args
    
    def _add_advanced_memory_capabilities(self, agent_args):
        """Add advanced memory capabilities exactly like run_qa_agent.py"""
        agent_args.update({
            "enable_user_memories": True,    # ⭐ Memoria automática de usuario  
            "enable_agentic_memory": True,   # ⭐ Gestión inteligente de memoria
            "num_history_runs": 5,           # Más contexto histórico
        })
        
        logger.info("🧠 User memories enabled")
        logger.info("🤖 Agentic memory management enabled") 
        logger.info("📖 History runs: 5")
    
    def _add_reasoning_capabilities(self, agent_args, reasoning_config, openai_chat):
        """Add reasoning capabilities exactly like run_qa_agent.py"""
        reasoning_type = reasoning_config.get("type", "agent")
        
        if reasoning_type == "agent":
            # Simple reasoning agent - just set reasoning=True
            agent_args["reasoning"] = True
            logger.info("🧠 Reasoning Agent enabled (chain-of-thought)")
            
        elif reasoning_type == "model":
            # Reasoning model approach
            model_id = reasoning_config.get("model_id", "o3-mini")
            try:
                if "o3" in model_id or "o1" in model_id:
                    reasoning_model = openai_chat(id=model_id)
                    agent_args["reasoning_model"] = reasoning_model
                    logger.info(f"🧠 Reasoning Model enabled: {model_id}")
                else:
                    logger.warning(f"⚠️ Unsupported reasoning model: {model_id}")
            except Exception as e:
                logger.warning(f"⚠️ Reasoning model setup failed: {e}")
                
        elif reasoning_type == "tools":
            # Reasoning tools approach
            try:
                from agno.tools.thinking import ThinkingTools
                thinking_tool = ThinkingTools(
                    add_instructions=reasoning_config.get("add_instructions", True)
                )
                agent_args["tools"].append(thinking_tool)
                logger.info("🧠 Reasoning Tools enabled (ThinkingTools)")
            except ImportError as e:
                logger.warning(f"⚠️ Reasoning tools not available: {e}")
    
    def _log_agent_summary(self):
        """Log agent initialization summary"""
        logger.info("=" * 60)
        logger.info("🎯 QA AGENT WEBSOCKET INTEGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"👤 User ID: {self.user_id}")
        logger.info(f"🧠 Reasoning: {self.enable_reasoning}")
        logger.info(f"💾 Memory: {self.enable_memory}")
        
        if self.components['model']:
            logger.info(f"📱 Model: {type(self.components['model']).__name__}")
        if self.components['tools']:
            logger.info(f"🔧 Tools: {len(self.components['tools'])} loaded")
        if self.components['storage']:
            logger.info(f"💾 Storage: Memory v2 active")
            
        logger.info("✅ Agent ready for WebSocket integration")
        logger.info("=" * 60)
    
    async def chat(self, message: str) -> str:
        """
        Chat method required by QAAgentProtocol
        
        Args:
            message: User message to process
            
        Returns:
            Agent response as string
        """
        if not self.is_initialized or self.agent is None:
            error_msg = f"❌ QA Agent not available"
            if self.initialization_error:
                error_msg += f": {self.initialization_error}"
            return error_msg
        
        try:
            logger.info(f"💬 Processing chat message: {message[:100]}...")
            
            # Use Response Manager to analyze the message and determine optimal model
            if self.response_manager:
                context = self.response_manager.analyze_message(message)
                strategy = self.response_manager.get_strategy(context)
                
                logger.info(f"🎯 Response strategy: {strategy.name} (model: {context.model}, max_tokens: {context.max_tokens})")
                
                # Apply dynamic model configuration if recommended model differs
                self._apply_dynamic_model_config(context)
            else:
                logger.warning("⚠️ Response Manager not available, using default model")
            
            # Use the agent's run method (same as chat_interface.py)
            response = self.agent.run(message)
            
            # Extract response content with detailed handling
            if hasattr(response, 'content') and response.content:
                result = str(response.content)
                logger.info(f"✅ Chat response generated: {len(result)} characters")
                return result
            elif hasattr(response, 'text') and response.text:
                result = str(response.text)
                logger.info(f"✅ Chat response generated: {len(result)} characters")
                return result
            else:
                result = str(response) if response else "No response generated"
                logger.warning(f"⚠️ Unexpected response format: {type(response)}")
                return result
                
        except Exception as e:
            error_msg = f"❌ Error processing chat message: {e}"
            logger.error(error_msg)
            logger.error(f"📍 Error trace:\n{traceback.format_exc()}")
            return error_msg
    
    async def _is_technical_event(self, chunk_str: str) -> bool:
        """Check if a chunk contains technical events that should be filtered out."""
        technical_terms = [
            'RunResponseContentEvent', 'created_at=', 'agent_id=', 'run_id=', 
            'session_id=', 'team_session_id=', 'content_type=', 'thinking=',
            'reasoning_content=', 'citations=', 'response_audio=', 'image=', 'extra_data='
        ]
        return any(tech_term in chunk_str for tech_term in technical_terms)

    async def _extract_chunk_content(self, chunk) -> str:
        """Extract clean content from a response chunk."""
        if hasattr(chunk, 'content') and chunk.content:
            content = str(chunk.content).strip()
            return content if content else ""
        elif chunk and isinstance(chunk, str):
            chunk_str = chunk.strip()
            if chunk_str and not self._is_technical_event(chunk_str):
                return chunk_str
        else:
            chunk_str = str(chunk).strip()
            if chunk_str and not chunk_str.startswith('RunResponseContentEvent'):
                return chunk_str
        return ""

    async def _process_generator_response(self, response) -> str:
        """Process generator response and convert to single response."""
        try:
            logger.info("🔧 Converting generator response to single response")
            response_parts = []
            
            for chunk in response:
                content = self._extract_chunk_content(chunk)
                if content:
                    response_parts.append(content)
            
            if response_parts:
                result = ''.join(response_parts).strip()
                logger.info(f"✅ Generator processed: {len(result)} characters")
                return result
            else:
                logger.warning("⚠️ Generator was empty or contained only technical events")
                return "No response generated"
                
        except Exception as e:
            logger.error(f"❌ Error processing generator response: {e}")
            return f"Error processing response: {e}"

    async def _extract_response_content(self, response) -> str:
        """Extract response content with detailed handling."""
        if hasattr(response, 'content') and response.content:
            return str(response.content)
        elif hasattr(response, 'text') and response.text:
            return str(response.text)
        else:
            logger.warning(f"⚠️ Unexpected response format: {type(response)}")
            return str(response) if response else "No response generated"

    async def process_message(
        self, 
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a single message and return complete response
        
        Args:
            message: User message to process
            session_id: Session identifier
            user_id: User identifier (overrides adapter user_id if provided)
            metadata: Additional message metadata
            
        Returns:
            Agent response as string
        """
        if not self.is_initialized or self.agent is None:
            error_msg = f"❌ QA Agent not available"
            if self.initialization_error:
                error_msg += f": {self.initialization_error}"
            return error_msg

        try:
            # Log context information
            context_info = []
            if session_id:
                context_info.append(f"session:{session_id}")
            if user_id:
                context_info.append(f"user:{user_id}")
            if metadata:
                context_info.append(f"metadata:{len(metadata)} fields")
                
            logger.info(f"🔄 Processing message with context: {', '.join(context_info)}")
            logger.info(f"💬 Message: {message[:100]}...")
            
            # Use the agent's run method (same as chat_interface.py)
            response = self.agent.run(message)
            
            # Handle generator response (convert to single response)
            if hasattr(response, '__iter__') and not isinstance(response, (str, bytes)):
                result = self._process_generator_response(response)
            else:
                result = self._extract_response_content(response)
            
            logger.info(f"✅ Message processed successfully: {len(result)} characters")
            return result
                
        except Exception as e:
            error_msg = f"❌ Error processing message: {e}"
            logger.error(error_msg)
            logger.error(f"📍 Error trace:\n{traceback.format_exc()}")
            return error_msg
    
    async def process_message_stream(
        self, 
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process message with streaming support - yields chunks as they arrive
        
        Args:
            message: User message to process
            session_id: Session identifier
            user_id: User identifier (overrides adapter user_id if provided)
            metadata: Additional message metadata
            
        Yields:
            Response chunks as they are generated
        """
        if not self.is_initialized or self.agent is None:
            error_msg = f"❌ QA Agent not available"
            if self.initialization_error:
                error_msg += f": {self.initialization_error}"
            yield error_msg
            return
        
        try:
            # Log context information
            context_info = []
            if session_id:
                context_info.append(f"session:{session_id}")
            if user_id:
                context_info.append(f"user:{user_id}")
            if metadata:
                context_info.append(f"metadata:{len(metadata)} fields")
                
            logger.info(f"🔄 Processing STREAMING message with context: {', '.join(context_info)}")
            logger.info(f"💬 Message: {message[:100]}...")
            
            # Try native Agno streaming based on configuration
            model_config = self.config.get_model_config()
            stream_enabled = model_config.get("stream", False)
            logger.info(f"🔧 Stream config for run: {stream_enabled}")
            
            try:
                logger.info(f"📡 Attempting Agno agent with streaming={stream_enabled}")
                response = self.agent.run(message, stream=stream_enabled)
                
                # Check if response is iterable (streaming)
                try:
                    response_iter = iter(response)
                    logger.info("✅ Native streaming confirmed")
                    
                    # Buffer for accumulating chunks to preserve Markdown formatting
                    content_buffer = ""
                    
                    def is_markdown_block_complete(text: str) -> bool:
                        """Check if the text contains complete Markdown structures"""
                        # Check for complete sentences (ending with punctuation)
                        if text.strip().endswith(('.', '!', '?', ':', ';')):
                            return True
                        # Check for complete code blocks
                        if '```' in text:
                            code_blocks = text.count('```')
                            return code_blocks % 2 == 0  # Even number means closed blocks
                        # Check for complete list items
                        if text.strip().endswith(('\n-', '\n*', '\n+')):
                            return True
                        # Check for complete headers or bold/italic text
                        if any(text.strip().endswith(marker) for marker in ['#', '**', '*', '__', '_']):
                            return False
                        # If buffer is getting too long, send anyway
                        if len(text) > 100:
                            return True
                        return False
                    
                    # Handle streaming response from Agno
                    for chunk in response_iter:
                        chunk_content = ""
                        
                        # Extract content based on chunk type
                        if hasattr(chunk, 'event') and chunk.event == "RunResponseContent":
                            if hasattr(chunk, 'content') and chunk.content:
                                chunk_content = str(chunk.content)
                        elif hasattr(chunk, 'content') and chunk.content and not hasattr(chunk, 'event'):
                            chunk_content = str(chunk.content)
                        elif isinstance(chunk, str):
                            chunk_content = chunk
                        
                        if chunk_content:
                            content_buffer += chunk_content
                            
                            # Check if we have a complete Markdown block
                            if is_markdown_block_complete(content_buffer):
                                yield content_buffer
                                content_buffer = ""
                                await asyncio.sleep(0.05)  # Slightly longer delay for better formatting
                    
                    # Send any remaining content in buffer
                    if content_buffer.strip():
                        yield content_buffer
                    
                    return
                    
                except TypeError:
                    # Not iterable, handle as single response
                    logger.info("📡 Single response received, converting to streaming")
                    content = getattr(response, 'content', str(response)) if response else "No response generated"
                    
            except Exception as e:
                # Fallback to regular run without streaming
                logger.info(f"📡 Fallback to simulated streaming due to: {e}")
                response = self.agent.run(message)
                content = getattr(response, 'content', str(response)) if response else "No response generated"
            
            # Convert single response to streaming chunks
            chunk_size = 50  # Characters per chunk
            content_str = str(content)
            for i in range(0, len(content_str), chunk_size):
                chunk = content_str[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.05)  # Delay between chunks for streaming effect
                    
            logger.info("✅ Streaming message processed successfully")
                
        except Exception as e:
            error_msg = f"❌ Error processing streaming message: {e}"
            logger.error(error_msg)
            logger.error(f"📍 Error trace:\n{traceback.format_exc()}")
            yield error_msg
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the adapter"""
        return {
            "initialized": self.is_initialized,
            "user_id": self.user_id,
            "reasoning_enabled": self.enable_reasoning,
            "memory_enabled": self.enable_memory,
            "initialization_error": self.initialization_error,
            "components": {
                name: component is not None 
                for name, component in self.components.items()
            }
        }
    
    def _apply_dynamic_model_config(self, context: Dict[str, Any]):
        """
        Apply dynamic model configuration based on Response Manager analysis
        
        Args:
            context: Analysis context from Response Manager containing model recommendation
        """
        try:
            recommended_model = context.get('model')
            current_model = getattr(self.agent.model, 'id', None) if (self.agent and hasattr(self.agent, 'model') and self.agent.model) else None
            
            if recommended_model and current_model != recommended_model:
                logger.info(f"🔄 Switching model: {current_model} → {recommended_model}")
                
                # Update agent's model configuration
                if (self.agent and hasattr(self.agent, 'model') and self.agent.model and 
                    hasattr(self.agent.model, 'id')):
                    self.agent.model.id = recommended_model
                    logger.info(f"✅ Model switched to: {recommended_model}")
                else:
                    logger.warning(f"⚠️ Cannot switch model - agent.model not accessible")
            else:
                logger.debug(f"🔧 Using current model: {current_model}")
                
        except Exception as e:
            logger.error(f"❌ Error applying dynamic model config: {e}")
            # Don't fail the chat - continue with current model
