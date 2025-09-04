#!/usr/bin/env python3
"""
QA Agent - Specialized agent for QA Testing and Intelligence
Modular version with specialized classes and improved architecture
"""

import sys
from abc import ABC, abstractmethod
from typing import Any, Protocol, Union, Callable, Sequence

from agno.agent import Agent
from agno.memory.v2.memory import Memory
from agno.models.base import Model

# Use absolute imports - avoid sys.path manipulation
try:
    from config import get_settings
except ImportError:
    # Fallback for development
    import os

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from config import get_settings

from .chat_interface import ChatInterface
from .model_manager import ModelManager
from .storage_manager import StorageManager
from .tools_manager import ToolsManager

# Configure Loguru logging
try:
    from ..logging_config import (
        get_logger,
        get_performance_logger,
        LogExecutionTime,
        LogStep,
        log_agent_event,
        setup_qa_logging,
    )
except ImportError:
    # Fallback for relative imports
    import sys
    import os

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from logging_config import (
        get_logger,
        get_performance_logger,
        LogExecutionTime,
        LogStep,
        log_agent_event,
        setup_qa_logging,
    )

# Initialize QA Agent logger
logger = get_logger("QAAgent")
perf_logger = get_performance_logger()


class ConfigValidator(Protocol):
    """Protocol for configuration validation"""

    def validate_config(self) -> None:
        """
        Validate configuration

        Raises:
            ConfigurationError: If any configuration is invalid, with specific details
            ValueError: If configuration values are invalid
            KeyError: If required configuration keys are missing
        """
        ...

    def get_interface_config(self) -> dict[str, Any]:
        """Get interface configuration"""
        ...

    def get_agent_instructions(self) -> Union[str, list[str]]:
        """Get agent instructions"""
        ...

    def get_model_config(self) -> dict[str, Any]:
        """Get model configuration"""
        ...

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration"""
        ...

    def get_tools_config(self) -> dict[str, Any]:
        """Get tools configuration"""
        ...


class ToolLike(Protocol):
    """Protocol for tool-like objects that can be used by the Agent"""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Tools should be callable"""
        ...

    # Optional: tools might have these attributes
    # name: str
    # description: str


class ComponentManager(ABC):
    """Abstract base class for component managers"""

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """Get component information"""
        pass


class QAAgentError(Exception):
    """Base exception for QA Agent errors"""

    pass


class ConfigurationError(QAAgentError):
    """Configuration validation error"""

    pass


class AgentCreationError(QAAgentError):
    """Agent creation error"""

    pass


# SRP: This class has a single responsibility - coordinating the QA agent components.
# It orchestrates the model, tools, storage, and interface managers without implementing
# their specific logic, following the Composition over Inheritance principle.
class QAAgent:
    """
    Specialized agent for QA Testing and Intelligence with modular architecture

    Supports dependency injection and provides structured logging and error handling.
    """

    def __init__(
        self,
        config: ConfigValidator | None = None,
        model_manager: ModelManager | None = None,
        tools_manager: ToolsManager | None = None,
        storage_manager: StorageManager | None = None,
    ):
        """
        Initialize QA agent with modular components

        Args:
            config: Configuration object (optional, will use default if not provided)
            model_manager: Model manager instance (optional)
            tools_manager: Tools manager instance (optional)
            storage_manager: Storage manager instance (optional)
        """
        with LogStep("QA Agent initialization", "QAAgent"):
            self.config = config or get_settings()
            self.agent: Agent | None = None

            # Initialize component managers with dependency injection support
            with LogStep("Component managers setup", "QAAgent"):
                self.model_manager = model_manager or ModelManager(self.config)
                self.tools_manager = tools_manager or ToolsManager(self.config)
                self.storage_manager = storage_manager or StorageManager(self.config)

            logger.info(
                "QA Agent initialized with modular components",
                component="QAAgent",
                managers=["ModelManager", "ToolsManager", "StorageManager"],
            )

            # Setup agent
            self.setup_agent()

    def _validate_configuration(self) -> None:
        """
        Validate configuration with detailed error reporting

        Raises:
            ConfigurationError: If configuration is invalid with specific details
        """
        logger.debug("Validating configuration...", component="QAAgent")

        if not hasattr(self.config, "validate_config"):
            raise ConfigurationError(
                "Configuration object missing validate_config method"
            )

        try:
            # This now expects validate_config to raise specific exceptions
            self.config.validate_config()
            logger.success("Configuration validation successful", component="QAAgent")

        except ConfigurationError:
            # Re-raise ConfigurationError as-is to preserve specific details
            raise
        except (ValueError, KeyError) as e:
            # Wrap other validation errors in ConfigurationError
            logger.error(
                "Configuration validation failed",
                component="QAAgent",
                error_type=type(e).__name__,
                error_details=str(e),
            )
            raise ConfigurationError(
                f"Configuration validation failed: {str(e)}"
            ) from e
        except Exception as e:
            # Handle unexpected validation errors
            logger.error(
                "Unexpected error during configuration validation",
                component="QAAgent",
                error_type=type(e).__name__,
                error_details=str(e),
            )
            raise ConfigurationError(f"Unexpected validation error: {str(e)}") from e

    def _normalize_instructions(
        self, instructions: Union[str, list[str]]
    ) -> tuple[str, dict[str, Any]]:
        """
        Normalize instructions and create logging metadata

        Args:
            instructions: Agent instructions as string or list of strings

        Returns:
            Tuple of (normalized_string, logging_metadata)
        """
        if isinstance(instructions, str):
            return instructions, {
                "instructions_type": "string",
                "instructions_length": len(instructions),
                "instructions_items": 1,
            }
        elif isinstance(instructions, list):
            normalized = "\n".join(instructions)
            return normalized, {
                "instructions_type": "list",
                "instructions_length": len(normalized),
                "instructions_items": len(instructions),
                "instructions_list_lengths": [len(item) for item in instructions],
            }
        else:
            # Fallback for unexpected types
            normalized = str(instructions)
            return normalized, {
                "instructions_type": type(instructions).__name__,
                "instructions_length": len(normalized),
                "instructions_items": 1,
                "instructions_original_type": type(instructions).__name__,
            }

    def _validate_and_normalize_tools(self, tools: Union[list, tuple]) -> list[Any]:
        """
        Validate and normalize tools to a consistent list format

        Args:
            tools: Tools as list or tuple from tools manager

        Returns:
            List of validated tools (keeping original types for Agent compatibility)

        Raises:
            AgentCreationError: If tools are invalid
        """
        if not isinstance(tools, (list, tuple)):
            raise AgentCreationError(
                f"Tools must be list or tuple, got {type(tools).__name__}"
            )

        # Convert to list for consistency
        tools_list = list(tools)

        # Validate each tool
        invalid_tools = []
        for i, tool in enumerate(tools_list):
            # Basic validation: check if tool has expected characteristics
            tool_info = {"index": i, "type": type(tool).__name__}

            # Most tools should be callable OR have a 'run' method OR be dict-like OR have 'functions' attribute (agno tools)
            is_callable = callable(tool)
            has_run_method = hasattr(tool, "run") and callable(getattr(tool, "run"))
            is_dict_like = isinstance(tool, dict)
            has_functions = hasattr(tool, "functions")  # agno tools have this

            if not (is_callable or has_run_method or is_dict_like or has_functions):
                invalid_tools.append(
                    f"Tool {i}: not callable, no 'run' method, not dict-like, and no 'functions' attribute ({type(tool).__name__})"
                )
                continue

            # Gather tool info for logging
            if hasattr(tool, "name"):
                tool_info["name"] = getattr(tool, "name")

            if hasattr(tool, "description"):
                desc = getattr(tool, "description", "")
                tool_info["description"] = desc[:50] + "..." if len(desc) > 50 else desc

            if is_dict_like:
                tool_info["dict_keys"] = (
                    list(tool.keys()) if hasattr(tool, "keys") else "unknown"
                )

            if has_functions:
                # For agno tools, get function count
                functions = getattr(tool, "functions", [])
                tool_info["functions_count"] = len(functions) if functions else 0

            tool_info["validation"] = {
                "callable": is_callable,
                "has_run": has_run_method,
                "is_dict": is_dict_like,
                "has_functions": has_functions,
            }

            logger.debug(
                "Tool validation passed", component="QAAgent", tool_info=tool_info
            )

        # Raise if any tools are invalid
        if invalid_tools:
            raise AgentCreationError(f"Invalid tools found: {'; '.join(invalid_tools)}")

        logger.info(
            "All tools validated successfully",
            component="QAAgent",
            tools_count=len(tools_list),
            original_type=type(tools).__name__,
            normalized_type="list",
        )

        return tools_list

    def _create_agent_components(self) -> tuple[Model, list[Any], Memory | None]:
        """
        Create and validate agent components

        Returns:
            Tuple of (model, tools, storage)

        Raises:
            AgentCreationError: If component creation fails
        """
        logger.debug("Creating agent components...", component="QAAgent")

        try:
            # Create model
            with LogStep("Model creation", "QAAgent"):
                model = self.model_manager.create_model()
                if model is None:
                    raise AgentCreationError("Model manager returned None")
                logger.info(
                    "Model created successfully",
                    component="QAAgent",
                    model_type=type(model).__name__,
                )

            # Create tools
            with LogStep("Tools loading", "QAAgent"):
                raw_tools = self.tools_manager.load_tools()

                # Validate and normalize tools to consistent list format
                tools = self._validate_and_normalize_tools(raw_tools)

                logger.info(
                    "Tools loaded and validated successfully",
                    component="QAAgent",
                    tools_count=len(tools),
                    tool_types=[type(tool).__name__ for tool in tools] if tools else [],
                    tool_names=[
                        getattr(tool, "name", f"Tool_{i}")
                        for i, tool in enumerate(tools)
                    ],
                )

            # Create storage
            storage = self.storage_manager.setup_storage()
            if storage is not None and not hasattr(storage, "add_memory"):
                logger.warning(
                    "Storage object may not be compatible with Agent memory interface"
                )
            logger.info(
                f"Storage configured: {type(storage).__name__ if storage else 'None'}"
            )

            return model, tools, storage

        except Exception as e:
            raise AgentCreationError(
                f"Failed to create agent components: {str(e)}"
            ) from e

    def _create_agent_instance(
        self,
        model: Model,
        tools: list[Any],
        storage: Memory | None,
        instructions: Union[str, list[str]],
        interface_config: dict[str, Any],
    ) -> Agent:
        """
        Create Agent instance with proper error handling

        Args:
            model: AI model instance
            tools: List of tools
            storage: Memory storage instance
            instructions: Agent instructions
            interface_config: Interface configuration

        Returns:
            Configured Agent instance

        Raises:
            AgentCreationError: If agent creation fails
        """
        try:
            agent = Agent(
                model=model,
                instructions=instructions,
                tools=tools,
                memory=storage,  # Using memory parameter for v2
                show_tool_calls=interface_config.get("show_tool_calls", True),
                markdown=interface_config.get("enable_markdown", True),
                add_history_to_messages=storage is not None,
            )

            logger.info("Agent instance created successfully")
            logger.debug(
                f"Agent configuration: show_tool_calls={agent.show_tool_calls}, "
                f"markdown={agent.markdown}, memory_enabled={storage is not None}"
            )

            return agent

        except Exception as e:
            raise AgentCreationError(
                f"Failed to create Agent instance: {str(e)}"
            ) from e

    def setup_agent(self) -> None:
        """
        Configure agent with all components using managers

        Raises:
            ConfigurationError: If configuration is invalid
            AgentCreationError: If agent creation fails
        """
        with LogExecutionTime("QA Agent setup", "QAAgent"):
            logger.info("Setting up QA Agent...", component="QAAgent")

            # Validate configuration
            with LogStep("Configuration validation", "QAAgent"):
                self._validate_configuration()

            # Create components using managers
            with LogStep("Component creation", "QAAgent"):
                model, tools, storage = self._create_agent_components()

            # Get additional configuration
            with LogStep("Configuration retrieval", "QAAgent"):
                interface_config = self.config.get_interface_config()
                instructions = self.config.get_agent_instructions()

                # Normalize instructions for consistent logging and usage
                normalized_instructions, instruction_metadata = (
                    self._normalize_instructions(instructions)
                )

                logger.debug(
                    "Agent configuration details",
                    component="QAAgent",
                    interface_config=interface_config,
                    **instruction_metadata,
                )

            # Create agent with isolated method for better maintainability
            with LogStep("Agent instance creation", "QAAgent"):
                self.agent = self._create_agent_instance(
                    model=model,
                    tools=tools,
                    storage=storage,
                    instructions=normalized_instructions,  # Use normalized instructions
                    interface_config=interface_config,
                )

            logger.success("QA Agent setup completed successfully", component="QAAgent")

            # Log completion event
            log_agent_event(
                "setup_completed",
                {
                    "model_type": type(model).__name__,
                    "tools_count": len(tools),
                    "memory_enabled": storage is not None,
                    "interface_config": interface_config,
                },
            )

    async def run_async(self) -> None:
        """
        Execute QA agent using chat interface (async version)

        Raises:
            RuntimeError: If agent not configured correctly
        """
        if not self.agent:
            raise RuntimeError(
                "Agent not configured correctly - call setup_agent() first"
            )

        logger.info("Starting QA Agent in async mode...")

        try:
            # Create and execute chat interface
            chat_interface = ChatInterface(self.agent, self.config)

            # For now, just use sync version since async isn't implemented
            logger.info("Using synchronous chat interface")
            chat_interface.start_chat()

        except KeyboardInterrupt:
            logger.info("QA Agent interrupted by user")
        except Exception as e:
            logger.error(f"Error during chat execution: {str(e)}")
            raise

    def run(self) -> None:
        """
        Execute QA agent using chat interface (sync version)

        Raises:
            RuntimeError: If agent not configured correctly
        """
        if not self.agent:
            raise RuntimeError(
                "Agent not configured correctly - call setup_agent() first"
            )

        logger.info("Starting QA Agent...")

        try:
            # Create and execute chat interface
            chat_interface = ChatInterface(self.agent, self.config)
            chat_interface.start_chat()

        except KeyboardInterrupt:
            logger.info("QA Agent interrupted by user")
        except Exception as e:
            logger.error(f"Error during chat execution: {str(e)}")
            raise
        finally:
            logger.info("QA Agent session ended")

    def get_info(self) -> dict[str, Any]:
        """
        Get complete agent information with enhanced details

        Returns:
            dict: Information from all components plus agent status
        """
        info = {
            "agent_configured": self.agent is not None,
            "model": self.model_manager.get_model_info(),
            "tools": self.tools_manager.get_tools_info(),
            "storage": self.storage_manager.get_storage_info(),
        }

        if self.agent:
            info["agent_details"] = {
                "model_type": type(self.agent.model).__name__,
                "tools_count": len(self.agent.tools) if self.agent.tools else 0,
                "memory_enabled": self.agent.memory is not None,
                "show_tool_calls": getattr(self.agent, "show_tool_calls", None),
                "markdown": getattr(self.agent, "markdown", None),
            }

        return info

    def health_check(self) -> dict[str, Union[bool, str]]:
        """
        Perform health check on all components

        Returns:
            dict: Health status of each component
        """
        health = {
            "overall": True,
            "config": False,
            "model": False,
            "tools": False,
            "storage": False,
            "agent": False,
            "errors": [],
        }

        try:
            # Check config
            self._validate_configuration()
            health["config"] = True
        except ConfigurationError as e:
            health["errors"].append(f"Config: {str(e)}")
            health["overall"] = False
        except Exception as e:
            health["errors"].append(f"Config (unexpected): {str(e)}")
            health["overall"] = False

        try:
            # Check components
            if self.model_manager.create_model():
                health["model"] = True
        except Exception as e:
            health["errors"].append(f"Model: {str(e)}")
            health["overall"] = False

        try:
            tools = self.tools_manager.load_tools()
            if isinstance(tools, (list, tuple)):
                health["tools"] = True
        except Exception as e:
            health["errors"].append(f"Tools: {str(e)}")
            health["overall"] = False

        try:
            self.storage_manager.setup_storage()
            health["storage"] = True
        except Exception as e:
            health["errors"].append(f"Storage: {str(e)}")
            health["overall"] = False

        # Check agent
        health["agent"] = self.agent is not None
        if not health["agent"]:
            health["errors"].append("Agent: Not initialized")
            health["overall"] = False

        return health


def main() -> int:
    """
    Main function to execute QA agent with proper error handling and logging

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Setup Loguru logging for QA Agent
    setup_qa_logging(
        level="INFO",
        enable_file_logging=True,
        enable_debug_logging=False,
        component="QAAgent",
        development_mode=True,
    )

    try:
        with LogExecutionTime("QA Agent initialization", "QAAgent"):
            logger.info("Initializing QA Agent with Loguru logging...")
            qa_agent = QAAgent()

            # Perform health check
            with LogStep("Health check", "QAAgent"):
                health = qa_agent.health_check()
                if not health["overall"]:
                    logger.error(
                        "Health check failed",
                        errors=health["errors"],
                        component="QAAgent",
                    )
                    return 1

            logger.success("QA Agent health check passed, starting...")

            # Log agent details
            log_agent_event(
                "startup",
                {
                    "health_status": "healthy",
                    "components": list(qa_agent.get_info().keys()),
                },
            )

            qa_agent.run()

        return 0

    except ConfigurationError as e:
        logger.error(
            "Configuration error occurred",
            error=str(e),
            component="QAAgent",
            error_type="ConfigurationError",
        )
        logger.info("💡 Check your configuration by running: python config.py")
        return 2

    except AgentCreationError as e:
        logger.error(
            "Agent creation failed",
            error=str(e),
            component="QAAgent",
            error_type="AgentCreationError",
        )
        return 3

    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted by user", component="QAAgent")
        return 0

    except Exception as e:
        logger.error(
            "Unexpected error occurred",
            error=str(e),
            component="QAAgent",
            error_type=type(e).__name__,
        )
        logger.exception("Full exception details:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
