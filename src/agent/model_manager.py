"""
Model Manager - Handles AI model configuration and creation
Updated to use Pydantic configuration models for type safety and validation
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from agno.models.openai import OpenAIChat
from pydantic import ValidationError

# Import our Pydantic configuration models
from config.models.core import ModelConfig
# Remove legacy imports - we'll use the modern configuration directly


class ModelManagerError(Exception):
    """Raised when model configuration or creation fails."""


class ConfigProtocol(Protocol):
    """Protocol for configuration objects that provide model configuration"""

    def get_model_config(self) -> Dict[str, Any]:
        """Return model configuration as dictionary"""
        ...


class ModelManager:
    """
    Manages AI model configuration and creation using Pydantic models

    Now uses type-safe Pydantic models for configuration validation
    and supports multiple model providers through the factory pattern.
    """

    def __init__(self, config: ConfigProtocol) -> None:
        """
        Initialize ModelManager with configuration

        Args:
            config: Configuration object with get_model_config() method
        """
        self.config = config
        self._model: Optional[Any] = None
        self._model_config: Optional[ModelConfig] = None

    def _get_validated_config(self) -> ModelConfig:
        """
        Get and validate model configuration using Pydantic

        Returns:
            Validated ModelConfig instance

        Raises:
            ModelManagerError: If configuration is invalid
        """
        if self._model_config is not None:
            return self._model_config

        try:
            # Get raw config from config object
            raw_config = self.config.get_model_config()

            if not isinstance(raw_config, dict):
                raise ModelManagerError("get_model_config() must return a dict")

            # Create ModelConfig directly using Pydantic
            self._model_config = ModelConfig(**raw_config)

            # Basic validation - ensure provider is supported
            supported_providers = ["openai", "azure", "deepseek"]
            if self._model_config.provider not in supported_providers:
                raise ModelManagerError(
                    f"Unsupported provider: {self._model_config.provider}. "
                    f"Supported: {supported_providers}"
                )

            return self._model_config

        except ValidationError as e:
            raise ModelManagerError(f"Invalid model configuration: {e}")
        except Exception as e:
            raise ModelManagerError(f"Configuration error: {e}") from e

    def _build_openai_chat(self, config: ModelConfig) -> Any:
        """
        Build OpenAIChat instance from Pydantic configuration

        Args:
            config: Validated ModelConfig instance

        Returns:
            Configured OpenAIChat instance
        """
        # Get only the fields supported by OpenAIChat
        allowed_fields = {
            "id",
            "api_key",
            "base_url",
            "organization",
            "project",
            "temperature",
            "max_tokens",
            "timeout",
            "seed",
            "response_format",
        }

        # Convert to dict and filter allowed fields
        config_dict = config.model_dump()
        kwargs = {
            k: v
            for k, v in config_dict.items()
            if k in allowed_fields and v is not None
        }

        try:
            return OpenAIChat(**kwargs)
        except TypeError as e:
            raise ModelManagerError(f"Invalid parameter for OpenAIChat: {e}") from e
        except Exception as e:
            raise ModelManagerError(f"Failed to instantiate OpenAIChat: {e}") from e

    def create_model(self) -> Any:
        """
        Create (or return cached) model instance according to configuration

        Returns:
            Configured model instance

        Raises:
            ModelManagerError: If model creation fails
        """
        if self._model is not None:
            return self._model

        config = self._get_validated_config()
        provider = config.provider

        if provider in ("openai", "openai-chat", "oai"):
            self._model = self._build_openai_chat(config)
        # elif provider in ("azure-openai", "azure"):
        #     self._model = self._build_azure_openai_chat(config)
        else:
            raise ModelManagerError(f"Unsupported provider: {provider}")

        return self._model

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get non-sensitive model information

        Returns:
            Dictionary with model information (excluding sensitive data like API keys)
        """
        config = self._get_validated_config()

        # Convert to dict and exclude sensitive information
        info = config.model_dump(exclude={"api_key"})

        # Add additional metadata
        info.update(
            {
                "compatible": True,  # We use Pydantic validation directly now
                "provider_type": type(config).__name__,
            }
        )

        return info
