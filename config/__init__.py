"""
Unified Configuration Package for QA Intelligence

This package provides a comprehensive configuration management system built on
Pydantic BaseSettings with support for YAML files and environment variables.

Usage:
    # Modern approach - recommended
    from config import get_settings
    settings = get_settings()
    
    # Legacy compatibility
    from config import get_config  
    config = get_config()

Architecture:
    - models/: Organized configuration models by domain
    - settings.py: Main Pydantic BaseSettings implementation  
    - legacy.py: Backward compatibility layer
    - model_config.py: Legacy model configuration (deprecated)
"""

# Main interfaces
from .settings import Settings, get_settings, reset_settings
from .legacy import ConfigManager, get_config

# Model exports organized by domain
from .models import (
    # Core models
    ModelConfig,
    DatabaseConfig, 
    ToolConfig,
    ToolsConfig,
    
    # Interface models
    InterfaceConfig,
    AppEnvironmentConfig,
    
    # Infrastructure models
    LoggingConfig,
    
    # WebSocket models (optional)
    WebSocketConfig,
    ServerConfig,
    SecurityConfig,
    AuthenticationConfig,
    CorsConfig,
    RateLimitConfig,
    SSLConfig,
    WebSocketLoggingConfig
)

# Legacy compatibility - check if available
try:
    from .model_config import ModelManager
except ImportError:
    # ModelManager not available, create placeholder
    class ModelManager:
        """Placeholder for legacy ModelManager"""
        pass


# Version information
__version__ = "2.0.0"
__description__ = "Unified Configuration Management for QA Intelligence"


def validate_configuration(config_file: str = "agent_config.yaml") -> bool:
    """
    Validate the complete configuration setup
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        settings = get_settings(config_file=config_file)
        settings.validate_config()
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


def get_config_summary(config_file: str = "agent_config.yaml") -> dict:
    """
    Get a summary of the current configuration
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        Dictionary with configuration summary
    """
    try:
        settings = get_settings(config_file=config_file)
        return settings.summary()
    except Exception as e:
        return {"error": f"Failed to load configuration: {e}"}


# Public API
__all__ = [
    # Main interfaces
    "Settings",
    "get_settings", 
    "reset_settings",
    "get_config",          # Legacy compatibility
    "ConfigManager",       # Legacy compatibility
    
    # Core configuration models
    "ModelConfig",
    "DatabaseConfig",
    "ToolConfig", 
    "ToolsConfig",
    
    # Interface configuration models  
    "InterfaceConfig",
    "AppEnvironmentConfig",
    
    # Infrastructure models
    "LoggingConfig",
    
    # WebSocket models (optional - for specialized use)
    "WebSocketConfig",
    "ServerConfig", 
    "SecurityConfig",
    "AuthenticationConfig",
    "CorsConfig",
    "RateLimitConfig",
    "SSLConfig",
    "WebSocketLoggingConfig",
    
    # Legacy compatibility
    "ModelManager",
    
    # Utility functions
    "validate_configuration",
    "get_config_summary",
    
    # Package metadata
    "__version__",
    "__description__"
]
