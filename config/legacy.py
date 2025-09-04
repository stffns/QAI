"""
Legacy compatibility layer for configuration
Provides backward compatibility with the old config.py pattern
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path

from .settings import get_settings, Settings
from .models import *


class ConfigManager:
    """
    Legacy ConfigManager for backward compatibility
    Wraps the new Pydantic-based Settings
    """
    
    def __init__(self, config_file: str = "agent_config.yaml"):
        self.config_file = config_file
        self._settings = None
        
    def get_config(self) -> Settings:
        """Get configuration instance (backward compatibility)"""
        if self._settings is None:
            # Use the new settings system with YAML config file
            self._settings = get_settings(config_file=self.config_file)
            
            # Add additional legacy methods
            self._add_legacy_methods()
        
        return self._settings
    
    def _add_legacy_methods(self):
        """Add legacy methods for backward compatibility"""
        if self._settings is None:
            return
            
        settings: Settings = self._settings
        
        # Add get_reasoning_config method (not in main Settings)
        def get_reasoning_config() -> Dict[str, Any]:
            """Get reasoning configuration from YAML"""
            # Load YAML directly since _load_yaml_config is private
            config_file = settings.config_file or "agent_config.yaml"
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}
                return yaml_config.get('reasoning', {'enabled': False})
            except FileNotFoundError:
                return {'enabled': False}
            except Exception:
                return {'enabled': False}
        
        # Add legacy validate_config that returns boolean
        def validate_config_legacy() -> bool:
            """Legacy validate_config that returns boolean instead of raising"""
            try:
                settings.validate_config()  # This raises on error
                return True
            except Exception as e:
                print(f"❌ Configuration validation failed: {e}")
                return False
        
        # Add methods as attributes (monkey patching for backward compatibility)
        setattr(settings, 'get_reasoning_config', get_reasoning_config)
        setattr(settings, 'validate_config_legacy', validate_config_legacy)


# Global instance for backward compatibility
_config_manager = ConfigManager()


def get_config():
    """
    Global function for backward compatibility
    Returns the same Settings instance that the new system uses
    """
    return _config_manager.get_config()


# Legacy exports for backward compatibility
__all__ = [
    'ConfigManager',
    'get_config',
    # Re-export all models for compatibility
    'ModelConfig',
    'DatabaseConfig',
    'ToolsConfig',
    'InterfaceConfig',
    'AppEnvironmentConfig',
    'LoggingConfig',
    'WebSocketConfig'
]
