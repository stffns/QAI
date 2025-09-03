"""
Configuration package for QA Intelligence
Provides Pydantic-based configuration management with environment variable support
"""

from .settings import Settings
from .models import (
    ModelConfig,
    DatabaseConfig,
    ToolsConfig,
    InterfaceConfig,
    AppEnvironmentConfig,
    LoggingConfig
)

# Backwards compatibility functions
def get_config():
    """
    Get configuration instance for backwards compatibility
    
    Returns:
        Settings: Pydantic Settings instance
    """
    return Settings()

__all__ = [
    "Settings",
    "get_config",  # Add backwards compatibility function
    "ModelConfig",
    "DatabaseConfig", 
    "ToolsConfig",
    "InterfaceConfig",
    "AppEnvironmentConfig",
    "LoggingConfig"
]
