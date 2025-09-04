"""
QA Agent Adapter for WebSocket Integration

Adapts the QA Intelligence Agent for use with WebSocket connections following exactly the same
pattern as run_qa_agent.py with full feature support including reasoning, memory, and tools.
"""

import sys
import os
import importlib.util
import traceback
from typing import Optional, Dict, Any, Union
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
    """
    
    def __init__(self, user_id: str = "websocket_user@qai.com", enable_reasoning: bool = True, enable_memory: bool = True):
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
            
            from config import get_config
            config = get_config()
            
            # Validate configuration (same as run_qa_agent.py)
            if hasattr(config, 'validate_config_legacy'):
                # Use legacy method that returns boolean
                if not config.validate_config_legacy():
                    raise ValueError("Invalid configuration - validation failed")
            elif hasattr(config, 'validate_config'):
                # Try modern method (may raise exception)
                try:
                    config.validate_config()
                except Exception as e:
                    raise ValueError(f"Configuration validation error: {e}")
            else:
                raise ValueError("Configuration object has no validation method")
            
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
            from model_manager import ModelManager
            from tools_manager import ToolsManager
            from storage_manager import StorageManager
            
            logger.info("✅ All manager classes imported successfully")
            
            # Restore original directory
            os.chdir(original_dir)
            
            return {
                'ModelManager': ModelManager,
                'ToolsManager': ToolsManager,
                'StorageManager': StorageManager
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
            reasoning_config = config.get_reasoning_config()
            
            return interface_config, instructions, reasoning_config
            
        except Exception as e:
            raise RuntimeError(f"Failed to get configuration sections: {e}")
    
    def _prepare_base_agent_args(self, model, instructions, tools, storage, interface_config):
        """Prepare base agent arguments exactly like run_qa_agent.py"""
        agent_args = {
            "model": model,
            "instructions": instructions,
            "tools": tools,
            "memory": storage,
            "show_tool_calls": interface_config.get("show_tool_calls", True),
            "markdown": interface_config.get("enable_markdown", True),
            "add_history_to_messages": storage is not None,
            "user_id": self.user_id,  # ⭐ Contexto de usuario QA
        }
        
        logger.info(f"👤 User ID: {self.user_id}")
        logger.info(f"🔧 Show tool calls: {agent_args['show_tool_calls']}")
        logger.info(f"📝 Markdown enabled: {agent_args['markdown']}")
        logger.info(f"📚 History in messages: {agent_args['add_history_to_messages']}")
        
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
    
    async def process_message(
        self, 
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process message with additional context - required by QAAgentProtocol
        
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
            
            # Extract response content with detailed handling
            if hasattr(response, 'content') and response.content:
                result = str(response.content)
                logger.info(f"✅ Message processed successfully: {len(result)} characters")
                return result
            elif hasattr(response, 'text') and response.text:
                result = str(response.text)
                logger.info(f"✅ Message processed successfully: {len(result)} characters")
                return result
            else:
                result = str(response) if response else "No response generated"
                logger.warning(f"⚠️ Unexpected response format: {type(response)}")
                return result
                
        except Exception as e:
            error_msg = f"❌ Error processing message: {e}"
            logger.error(error_msg)
            logger.error(f"📍 Error trace:\n{traceback.format_exc()}")
            return error_msg
    
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
