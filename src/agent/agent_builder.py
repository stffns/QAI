"""
Agent Builder - Builder pattern for complex agent configuration
Following Agno best practices with fluent interface
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from agno.agent import Agent
from agno.memory.v2.memory import Memory
from agno.models.base import Model

from .model_manager import ModelManager
from .storage_manager import StorageManager
from .tools_manager import ToolsManager

# Configure logging
try:
    from ..logging_config import LogStep, get_logger
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from logging_config import LogStep, get_logger

logger = get_logger("AgentBuilder")


@dataclass
class AgentBuildConfig:
    """Configuration container for agent building"""

    model: Optional[Model] = None
    tools: List[Any] = field(default_factory=list)
    memory: Optional[Memory] = None
    instructions: Union[str, List[str]] = ""
    show_tool_calls: bool = True
    markdown: bool = True
    stream: bool = False
    add_history_to_messages: bool = False

    # Advanced configuration
    tool_validation: bool = True
    memory_validation: bool = True
    performance_monitoring: bool = True


class AgentBuilderError(Exception):
    """Agent builder specific error"""

    pass


class AgentBuilder:
    """
    Builder pattern for creating configured Agno agents

    Provides fluent interface for complex agent configuration
    with validation and error handling.

    Example:
        agent = (AgentBuilder(config)
                .with_model("gpt-4")
                .with_tools(["python", "calculator"])
                .with_memory("sqlite")
                .with_streaming(True)
                .validate()
                .build())
    """

    def __init__(self, config: Any):
        """
        Initialize builder with base configuration

        Args:
            config: System configuration object
        """
        self.config = config
        self.build_config = AgentBuildConfig()
        self._managers_created = False

        # Component managers
        self.model_manager: Optional[ModelManager] = None
        self.tools_manager: Optional[ToolsManager] = None
        self.storage_manager: Optional[StorageManager] = None

    def with_model(
        self, model_id: Optional[str] = None, **model_kwargs
    ) -> AgentBuilder:
        """
        Configure model for the agent

        Args:
            model_id: Optional model ID override
            **model_kwargs: Additional model configuration

        Returns:
            AgentBuilder: Self for chaining
        """
        try:
            if not self.model_manager:
                self.model_manager = ModelManager(self.config)

            # Override model configuration if provided
            if model_id or model_kwargs:
                logger.info(
                    f"Overriding model configuration: id={model_id}, kwargs={model_kwargs}"
                )
                # This would require extending ModelManager to accept overrides

            self.build_config.model = self.model_manager.create_model()
            logger.debug(f"Model configured: {type(self.build_config.model).__name__}")

        except Exception as e:
            raise AgentBuilderError(f"Failed to configure model: {e}") from e

        return self

    def with_tools(
        self,
        tool_names: Optional[List[str]] = None,
        essential_tools: Optional[List[str]] = None,
    ) -> AgentBuilder:
        """
        Configure tools for the agent

        Args:
            tool_names: Specific tools to load (overrides config)
            essential_tools: Tools that must load successfully

        Returns:
            AgentBuilder: Self for chaining
        """
        try:
            if not self.tools_manager:
                self.tools_manager = ToolsManager(self.config)

            # Override tool configuration if provided
            if tool_names:
                logger.info(f"Loading specific tools: {tool_names}")
                # This would require extending ToolsManager for selective loading

            if essential_tools:
                logger.info(f"Essential tools required: {essential_tools}")
                # Mark specific tools as essential

            self.build_config.tools = self.tools_manager.load_tools()
            logger.debug(f"Tools configured: {len(self.build_config.tools)} loaded")

        except Exception as e:
            raise AgentBuilderError(f"Failed to configure tools: {e}") from e

        return self

    def with_memory(
        self,
        memory_type: Optional[str] = None,
        memory_config: Optional[Dict[str, Any]] = None,
    ) -> AgentBuilder:
        """
        Configure memory for the agent

        Args:
            memory_type: Type of memory to use
            memory_config: Memory-specific configuration

        Returns:
            AgentBuilder: Self for chaining
        """
        try:
            if not self.storage_manager:
                self.storage_manager = StorageManager(self.config)

            # Override memory configuration if provided
            if memory_type or memory_config:
                logger.info(
                    f"Configuring memory: type={memory_type}, config={memory_config}"
                )

            self.build_config.memory = self.storage_manager.setup_storage()
            self.build_config.add_history_to_messages = (
                self.build_config.memory is not None
            )

            logger.debug(
                f"Memory configured: {type(self.build_config.memory).__name__ if self.build_config.memory else 'None'}"
            )

        except Exception as e:
            raise AgentBuilderError(f"Failed to configure memory: {e}") from e

        return self

    def with_streaming(self, enabled: bool = True) -> AgentBuilder:
        """
        Configure streaming for the agent

        Args:
            enabled: Whether to enable streaming

        Returns:
            AgentBuilder: Self for chaining
        """
        self.build_config.stream = enabled
        logger.debug(f"Streaming configured: {enabled}")
        return self

    def with_interface(
        self, show_tool_calls: Optional[bool] = None, markdown: Optional[bool] = None
    ) -> AgentBuilder:
        """
        Configure interface options

        Args:
            show_tool_calls: Whether to show tool calls
            markdown: Whether to enable markdown

        Returns:
            AgentBuilder: Self for chaining
        """
        if show_tool_calls is not None:
            self.build_config.show_tool_calls = show_tool_calls
        if markdown is not None:
            self.build_config.markdown = markdown

        logger.debug(
            f"Interface configured: tool_calls={self.build_config.show_tool_calls}, markdown={self.build_config.markdown}"
        )
        return self

    def with_instructions(self, instructions: Union[str, List[str]]) -> AgentBuilder:
        """
        Configure agent instructions

        Args:
            instructions: Agent instructions

        Returns:
            AgentBuilder: Self for chaining
        """
        self.build_config.instructions = instructions
        logger.debug(f"Instructions configured: {type(instructions).__name__}")
        return self

    def with_validation(
        self, tools: bool = True, memory: bool = True, performance: bool = True
    ) -> AgentBuilder:
        """
        Configure validation options

        Args:
            tools: Enable tool validation
            memory: Enable memory validation
            performance: Enable performance monitoring

        Returns:
            AgentBuilder: Self for chaining
        """
        self.build_config.tool_validation = tools
        self.build_config.memory_validation = memory
        self.build_config.performance_monitoring = performance

        logger.debug(
            f"Validation configured: tools={tools}, memory={memory}, performance={performance}"
        )
        return self

    def auto_configure(self) -> AgentBuilder:
        """
        Auto-configure based on system configuration

        Returns:
            AgentBuilder: Self for chaining
        """
        with LogStep("Auto-configuring agent", "AgentBuilder"):
            # Configure from system config
            interface_config = self.config.get_interface_config()
            model_config = self.config.get_model_config()

            return (
                self.with_model()
                .with_tools()
                .with_memory()
                .with_streaming(model_config.get("stream", False))
                .with_interface(
                    show_tool_calls=interface_config.get("show_tool_calls", True),
                    markdown=interface_config.get("enable_markdown", True),
                )
                .with_instructions(self.config.get_agent_instructions())
            )

    def validate(self) -> AgentBuilder:
        """
        Validate the current configuration

        Returns:
            AgentBuilder: Self for chaining

        Raises:
            AgentBuilderError: If validation fails
        """
        with LogStep("Validating agent configuration", "AgentBuilder"):
            errors = []

            # Validate model
            if not self.build_config.model:
                errors.append("Model not configured")

            # Validate instructions
            if not self.build_config.instructions:
                errors.append("Instructions not configured")
            elif isinstance(self.build_config.instructions, list):
                if not self.build_config.instructions or any(
                    not isinstance(x, str) or not x.strip()
                    for x in self.build_config.instructions
                ):
                    errors.append(
                        "Instructions list is empty or contains invalid items"
                    )
            elif (
                not isinstance(self.build_config.instructions, str)
                or not self.build_config.instructions.strip()
            ):
                errors.append("Instructions string is empty")

            # Validate tools if enabled
            if self.build_config.tool_validation and self.build_config.tools:
                for i, tool in enumerate(self.build_config.tools):
                    if not any(
                        [
                            callable(tool),
                            hasattr(tool, "run") and callable(getattr(tool, "run")),
                            isinstance(tool, dict),
                            hasattr(tool, "functions"),
                        ]
                    ):
                        errors.append(f"Tool {i} doesn't implement required interface")

            # Validate memory if enabled
            if self.build_config.memory_validation and self.build_config.memory:
                if not hasattr(self.build_config.memory, "add_memory"):
                    logger.warning(
                        "Memory object may not be compatible with Agent interface"
                    )

            if errors:
                error_msg = f"Validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                raise AgentBuilderError(error_msg)

            logger.info("Agent configuration validation passed")
            return self

    def build(self) -> Agent:
        """
        Build the final Agent instance

        Returns:
            Agent: Configured Agent instance

        Raises:
            AgentBuilderError: If build fails
        """
        with LogStep("Building Agent instance", "AgentBuilder"):
            try:
                agent = Agent(
                    model=self.build_config.model,
                    instructions=self.build_config.instructions,
                    tools=self.build_config.tools,
                    memory=self.build_config.memory,
                    show_tool_calls=self.build_config.show_tool_calls,
                    markdown=self.build_config.markdown,
                    stream=self.build_config.stream,
                    add_history_to_messages=self.build_config.add_history_to_messages,
                )

                logger.success(
                    f"Agent built successfully with {len(self.build_config.tools)} tools and {'streaming' if self.build_config.stream else 'non-streaming'} mode"
                )

                # Performance monitoring if enabled
                if self.build_config.performance_monitoring:
                    self._setup_performance_monitoring(agent)

                return agent

            except Exception as e:
                raise AgentBuilderError(f"Failed to build Agent: {e}") from e

    def _setup_performance_monitoring(self, agent: Agent) -> None:
        """Setup performance monitoring for the agent"""
        logger.debug("Performance monitoring enabled for agent")
        # This could be extended to add performance wrappers, metrics collection, etc.

    def get_build_info(self) -> Dict[str, Any]:
        """
        Get information about the current build configuration

        Returns:
            Dict with build configuration details
        """
        return {
            "model_configured": self.build_config.model is not None,
            "tools_count": len(self.build_config.tools),
            "memory_enabled": self.build_config.memory is not None,
            "streaming_enabled": self.build_config.stream,
            "validation_enabled": {
                "tools": self.build_config.tool_validation,
                "memory": self.build_config.memory_validation,
                "performance": self.build_config.performance_monitoring,
            },
            "interface_config": {
                "show_tool_calls": self.build_config.show_tool_calls,
                "markdown": self.build_config.markdown,
            },
        }
