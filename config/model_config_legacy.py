"""
Model-specific configuration management
Provides specialized configuration for AI model providers
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from .models import ModelConfig, ModelProvider


class OpenAIModelConfig(ModelConfig):
    """OpenAI-specific model configuration"""
    
    provider: str = Field(default="openai")
    id: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model identifier"
    )
    organization: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID"
    )
    project: Optional[str] = Field(
        default=None,
        description="OpenAI project ID"
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v != "openai":
            raise ValueError("Provider must be 'openai' for OpenAIModelConfig")
        return v
    
    @classmethod
    def get_available_models(cls) -> list[str]:
        """Get list of available OpenAI models"""
        return [
            # GPT-5 Series (Latest)
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-turbo",
            
            # GPT-4 Series
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            
            # GPT-3.5 Series (Legacy)
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            
            # Reasoning Models
            "o3-mini",
            "o1-preview",
            "o1-mini"
        ]


class AzureModelConfig(ModelConfig):
    """Azure OpenAI-specific model configuration"""
    
    provider: str = Field(default="azure")
    azure_endpoint: str = Field(
        description="Azure OpenAI endpoint URL"
    )
    api_version: str = Field(
        default="2023-12-01-preview",
        description="Azure OpenAI API version"
    )
    deployment_name: str = Field(
        description="Azure deployment name"
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v != "azure":
            raise ValueError("Provider must be 'azure' for AzureModelConfig")
        return v
    
    @classmethod
    def get_available_api_versions(cls) -> list[str]:
        """Get list of available Azure API versions"""
        return [
            "2023-12-01-preview",
            "2023-05-15",
            "2023-03-15-preview"
        ]


class DeepSeekModelConfig(ModelConfig):
    """DeepSeek-specific model configuration"""
    
    provider: str = Field(default="deepseek")
    id: str = Field(
        default="deepseek-chat",
        description="DeepSeek model identifier"
    )
    base_url: Optional[str] = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API base URL"
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v != "deepseek":
            raise ValueError("Provider must be 'deepseek' for DeepSeekModelConfig")
        return v
    
    @classmethod
    def get_available_models(cls) -> list[str]:
        """Get list of available DeepSeek models"""
        return [
            "deepseek-chat",
            "deepseek-coder"
        ]


class ModelConfigFactory:
    """Factory for creating provider-specific model configurations"""
    
    _config_classes = {
        ModelProvider.OPENAI: OpenAIModelConfig,
        ModelProvider.AZURE: AzureModelConfig,
        ModelProvider.DEEPSEEK: DeepSeekModelConfig
    }
    
    @classmethod
    def create_config(
        cls, 
        provider: str, 
        **kwargs
    ) -> ModelConfig:
        """
        Create a provider-specific model configuration
        
        Args:
            provider: Model provider name
            **kwargs: Configuration parameters
            
        Returns:
            Provider-specific model configuration
            
        Raises:
            ValueError: If provider is not supported
        """
        try:
            provider_enum = ModelProvider(provider.lower())
        except ValueError:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config_class = cls._config_classes.get(provider_enum)
        if not config_class:
            raise ValueError(f"No configuration class for provider: {provider}")
        
        return config_class(**kwargs)
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported providers"""
        return [provider.value for provider in ModelProvider]
    
    @classmethod
    def get_provider_requirements(cls, provider: str) -> Dict[str, Any]:
        """
        Get required configuration fields for a provider
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary of required fields and their descriptions
        """
        config_class = cls._config_classes.get(ModelProvider(provider.lower()))
        if not config_class:
            return {}
        
        schema = config_class.model_json_schema()
        required_fields = schema.get('required', [])
        properties = schema.get('properties', {})
        
        return {
            field: properties.get(field, {}).get('description', 'No description')
            for field in required_fields
        }


def validate_model_compatibility(config: ModelConfig) -> bool:
    """
    Validate if model configuration is compatible with current setup
    
    Args:
        config: Model configuration to validate
        
    Returns:
        True if compatible, False otherwise
    """
    try:
        # Basic validation - check if provider is supported
        if config.provider not in ModelConfigFactory.get_supported_providers():
            return False
        
        # Provider-specific validation
        if config.provider == ModelProvider.OPENAI:
            return config.id in OpenAIModelConfig.get_available_models()
        elif config.provider == ModelProvider.DEEPSEEK:
            return config.id in DeepSeekModelConfig.get_available_models()
        elif config.provider == ModelProvider.AZURE:
            # For Azure, check if required fields are present
            azure_config = config
            return (
                hasattr(azure_config, 'azure_endpoint') and
                hasattr(azure_config, 'deployment_name')
            )
        
        return True
    except Exception:
        return False


def get_default_model_config(provider: str) -> ModelConfig:
    """
    Get default configuration for a provider
    
    Args:
        provider: Provider name
        
    Returns:
        Default model configuration for the provider
    """
    return ModelConfigFactory.create_config(provider)
