"""
Agent Factory - Handles agent creation and configuration
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence, Union

from agno.agent import Agent
from agno.memory.v2.memory import Memory
from agno.models.base import Model

from .model_manager import ModelManager
from .storage_manager import StorageManager
from .tools_manager import ToolsManager


class AgentFactoryError(Exception):
    """Base error for AgentFactory."""


class AgentFactoryConfigError(AgentFactoryError):
    """Raised when configuration is invalid."""


class AgentFactoryBuildError(AgentFactoryError):
    """Raised when building components or Agent fails."""


class AgentFactory:
    """Factory for creating configured agents (SRP: construir y configurar Agent)."""

    def __init__(self, config: Any) -> None:
        """
        Initialize factory with configuration.

        Args:
            config: System configuration object with:
                - validate_config() -> None (lanza si inválida)
                - get_interface_config() -> dict
                - get_agent_instructions() -> str | list[str]
        """
        self.config = config

    def _normalize_instructions(
        self, instructions: Union[str, list[str]]
    ) -> Union[str, list[str]]:
        """Ensure instructions are a non-empty string or a non-empty list of non-empty strings."""
        if isinstance(instructions, list):
            if not instructions or any(
                not isinstance(x, str) or not x.strip() for x in instructions
            ):
                raise AgentFactoryConfigError(
                    "Agent instructions list is empty or contains blank/non-string items"
                )
            return instructions
        if not isinstance(instructions, str) or not instructions.strip():
            raise AgentFactoryConfigError("Agent instructions string is empty")
        return instructions

    def _as_list(self, maybe_seq: Iterable[Any]) -> list[Any]:
        try:
            lst = list(maybe_seq)
        except Exception as e:
            raise AgentFactoryBuildError(f"Tools must be iterable: {e}") from e
        return lst

    def create_agent(self) -> Agent:
        """
        Create and configure the Agent instance.

        Returns:
            Agent: Configured Agent instance.

        Raises:
            AgentFactoryConfigError: invalid or incomplete configuration.
            AgentFactoryBuildError: components or Agent could not be created.
        """
        # 1) Validate configuration (sin booleanos; debe lanzar si algo falta)
        if not hasattr(self.config, "validate_config"):
            raise AgentFactoryConfigError("Config object missing validate_config()")
        try:
            self.config.validate_config()
        except Exception as e:
            # Propaga detalle; no ocultes el error
            raise AgentFactoryConfigError(f"Configuration invalid: {e}") from e

        # 2) Build managers
        try:
            model_manager = ModelManager(self.config)
            tools_manager = ToolsManager(self.config)
            storage_manager = StorageManager(self.config)
        except Exception as e:
            raise AgentFactoryBuildError(f"Failed creating managers: {e}") from e

        # 3) Create components
        try:
            model: Model = model_manager.create_model()
            if model is None:
                raise AgentFactoryBuildError(
                    "ModelManager.create_model() returned None"
                )

            tools_seq: Sequence[Any] | Iterable[Any] = tools_manager.load_tools()
            tools: list[Any] = self._as_list(tools_seq)

            storage: Memory | None = storage_manager.setup_storage()
        except AgentFactoryBuildError:
            raise
        except Exception as e:
            raise AgentFactoryBuildError(f"Failed creating components: {e}") from e

        # 4) Config details
        try:
            interface_config: dict[str, Any] = self.config.get_interface_config()
        except Exception as e:
            raise AgentFactoryConfigError(f"get_interface_config() failed: {e}") from e

        try:
            raw_instructions = self.config.get_agent_instructions()
            instructions = self._normalize_instructions(raw_instructions)
        except Exception as e:
            raise AgentFactoryConfigError(f"Invalid agent instructions: {e}") from e

        # 5) Create Agent (usa memory=..., no storage=...)
        try:
            agent = Agent(
                model=model,
                instructions=instructions,
                tools=tools,
                memory=storage,  # <- agno v2 usa 'memory'
                show_tool_calls=bool(interface_config.get("show_tool_calls", True)),
                markdown=bool(interface_config.get("enable_markdown", True)),
                add_history_to_messages=storage is not None,
            )
        except Exception as e:
            raise AgentFactoryBuildError(f"Failed to create Agent: {e}") from e

        return agent
