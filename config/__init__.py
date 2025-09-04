"""
Unified Configuration Package for QA Intelligence

This package provides a comprehensive configuration management system built on
Pydantic with support for YAML files and environment variables.

## Architecture Overview

The configuration system follows a modular approach with specialized managers:

### Core Components:
- **models/core.py**: Primary configuration models (ModelConfig, DatabaseConfig, ToolsConfig)
- **models/interface.py**: Interface and environment configurations
- **models/logging.py**: Logging system configuration
- **models/websocket.py**: WebSocket server configuration (optional)
- **settings.py**: Main Pydantic Settings implementation with YAML integration
- **legacy.py**: Backward compatibility layer for migration

### Configuration Priority:
1. Environment variables (highest priority)
2. YAML configuration file 
3. Default values (lowest priority)

## Usage Examples

### Modern Approach (Recommended):
```python
from config import get_settings
settings = get_settings()

# Access configuration sections
model_config = settings.model
db_config = settings.database
tools_config = settings.tools
```

### Legacy Compatibility:
```python
from config import get_config  
config = get_config()

# Legacy access patterns still work
model_id = config.model.id
db_url = config.database.url
```

### Environment Variable Examples:
```bash
# Model configuration
export MODEL_PROVIDER=openai
export MODEL_ID=gpt-4
export MODEL_API_KEY=sk-...
export MODEL_TEMPERATURE=0.7

# Database configuration  
export DB_URL=postgresql://user:pass@localhost:5432/qadb
export DB_POOL_SIZE=20

# Tool configuration
export TOOLS_ENABLED=true
export TOOLS_SAFETY_MODE=true
```

### YAML Configuration:
```yaml
# agent_config.yaml
model:
  provider: "openai"
  id: "gpt-4"
  temperature: 0.7

database:
  url: "sqlite:///./data/qa_intelligence.db"
  pool_size: 20

tools:
  enabled: true
  safety_mode: true
```

## Migration Guide

For projects migrating from the old configuration system:

1. **Import Changes**: Update imports to use the new structure
2. **Environment Variables**: Rename env vars to follow new naming conventions
3. **YAML Structure**: Update YAML files to match new schema
4. **Validation**: New system provides automatic validation and better error messages

## Error Handling

The configuration system provides comprehensive validation:
- **Type validation**: Automatic type checking via Pydantic
- **Range validation**: Min/max constraints on numeric values
- **Format validation**: URL, email, and other format checks
- **Provider validation**: Ensures supported AI providers are used
- **Cross-field validation**: Validates related configuration options

Common validation errors and solutions are documented in the individual model classes.
"""

# ============================================================================
# Main Configuration Interfaces
# ============================================================================

# Primary interfaces for modern usage
from .settings import Settings, get_settings, reset_settings

# Legacy compatibility layer for gradual migration
from .legacy import ConfigManager, get_config

# ============================================================================
# Core Configuration Models
# ============================================================================

# Import all configuration models for direct usage
from .models.core import (
    # Core configuration models
    ModelConfig,
    DatabaseConfig, 
    ToolConfig,
    ToolsConfig,
    
    # Enums for validation
    ModelProvider,
    DatabaseType,
)

from .models.interface import (
    # Interface configuration models
    InterfaceConfig,
    AppEnvironmentConfig,
)

from .models.logging import (
    # Logging system configuration
    LoggingConfig,
)

# ============================================================================
# Optional WebSocket Configuration
# ============================================================================

# WebSocket models are imported conditionally since they're optional
try:
    from .models.websocket import (
        WebSocketConfig,
        ServerConfig,
        SecurityConfig,
        AuthenticationConfig,
        CorsConfig,
        RateLimitConfig,
        SSLConfig,
        WebSocketLoggingConfig
    )
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    # WebSocket dependencies not available
    _WEBSOCKET_AVAILABLE = False

# ============================================================================
# Package Metadata
# ============================================================================

__version__ = "2.0.0"
__author__ = "QA Intelligence Team"
__description__ = "Comprehensive configuration management for QA Intelligence"

# ============================================================================
# Configuration Validation Utilities
# ============================================================================

def validate_current_config() -> bool:
    """
    Validate the current configuration setup.
    
    Returns:
        True if configuration is valid, False otherwise
        
    Raises:
        ValidationError: If configuration has validation errors
    """
    try:
        settings = get_settings()
        # The settings instantiation will trigger all validators
        return True
    except Exception as e:
        import warnings
        warnings.warn(f"Configuration validation failed: {e}", UserWarning)
        return False


def get_config_summary() -> dict:
    """
    Get a summary of the current configuration.
    
    Returns:
        Dictionary with configuration summary
    """
    try:
        settings = get_settings()
        return {
            "model": {
                "provider": settings.model.provider,
                "id": settings.model.id,
                "has_api_key": bool(settings.model.api_key),
            },
            "database": {
                "type": "sqlite" if "sqlite" in settings.database.url else "other",
                "url_set": bool(settings.database.url),
            },
            "tools": {
                "enabled": settings.tools.enabled,
                "count": len(settings.tools.tools),
                "enabled_tools": [t.name for t in settings.tools.get_enabled_tools()],
            },
            "interface": {
                "playground_enabled": settings.interface.playground.get("enabled", False),
                "api_enabled": True,  # Always available
            }
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# Development and Debugging Utilities  
# ============================================================================

def debug_config():
    """Print detailed configuration information for debugging."""
    try:
        settings = get_settings()
        summary = get_config_summary()
        
        print("=" * 60)
        print("QA Intelligence Configuration Debug")
        print("=" * 60)
        print(f"Config Version: {__version__}")
        print(f"Settings Type: {type(settings).__name__}")
        print(f"Config File: {settings.config_file}")
        print()
        
        print("Configuration Summary:")
        for section, data in summary.items():
            print(f"  {section}:")
            for key, value in data.items():
                print(f"    {key}: {value}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error debugging configuration: {e}")

# ============================================================================
# Public API Definition
# ============================================================================

__all__ = [
    # Main interfaces
    "Settings",
    "get_settings", 
    "reset_settings",
    
    # Legacy compatibility
    "ConfigManager",
    "get_config",
    
    # Core models
    "ModelConfig",
    "DatabaseConfig",
    "ToolConfig", 
    "ToolsConfig",
    
    # Interface models
    "InterfaceConfig",
    "AppEnvironmentConfig",
    
    # Infrastructure models
    "LoggingConfig",
    
    # Enums
    "ModelProvider",
    "DatabaseType",
    
    # Utilities
    "validate_current_config",
    "get_config_summary",
    "debug_config",
    
    # Package info
    "__version__",
    "__author__",
    "__description__",
]

# Add WebSocket models to public API if available
if _WEBSOCKET_AVAILABLE:
    __all__.extend([
        "WebSocketConfig",
        "ServerConfig", 
        "SecurityConfig",
        "AuthenticationConfig",
        "CorsConfig",
        "RateLimitConfig",
        "SSLConfig",
        "WebSocketLoggingConfig"
    ])

# ============================================================================
# Initialization and Validation
# ============================================================================

# Validate configuration on import if not in test environment
import os
if os.getenv("ENVIRONMENT") != "test" and os.getenv("SKIP_CONFIG_VALIDATION") != "true":
    try:
        # Quick validation check
        validate_current_config()
    except Exception:
        # Don't fail import, just warn
        import warnings
        warnings.warn(
            "Configuration validation failed during import. "
            "Run 'python config.py' for detailed validation.",
            UserWarning
        )
