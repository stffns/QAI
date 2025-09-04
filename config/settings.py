"""
Main settings configuration using Pydantic BaseSettings
Centralizes all configuration management with environment variable support
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

from .models import (
    ModelConfig,
    DatabaseConfig,
    ToolsConfig,
    InterfaceConfig,
    AppEnvironmentConfig,
    LoggingConfig
)


class Settings(BaseSettings):
    """
    Main application settings using Pydantic BaseSettings
    
    Supports configuration from:
    1. Environment variables
    2. YAML configuration files
    3. Default values
    
    Priority order: ENV vars > YAML file > defaults
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        env_nested_delimiter='__',
        extra='allow'
    )
    
    # Core configuration sections
    model: ModelConfig = ModelConfig()
    database: DatabaseConfig = DatabaseConfig()
    tools: ToolsConfig = ToolsConfig()
    interface: InterfaceConfig = InterfaceConfig()
    app_environment: AppEnvironmentConfig = AppEnvironmentConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Global settings
    config_file: Optional[str] = "agent_config.yaml"
    version: str = "1.0.0"
    app_name: str = "QA Intelligence"
    
    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook to load YAML and ensure directories"""
        # Load YAML configuration and update fields
        yaml_config = self._load_yaml_config()
        if yaml_config:
            self._update_from_yaml(yaml_config)
        
        # Ensure required directories exist
        self._ensure_directories()
    
    def _update_from_yaml(self, yaml_config: Dict[str, Any]) -> None:
        """Update configuration from YAML data - Environment variables have priority.

        Performs a deep merge: for nested dicts, merge recursively. For scalars,
        keep current (ENV) value when it differs from the default; otherwise take YAML.
        Lists are replaced by YAML entirely if provided.
        """
        section_mappings = {
            'model': 'model',
            'database': 'database', 
            'tools': 'tools',
            'interface': 'interface',
            'environment': 'app_environment',  # Map YAML 'environment' to 'app_environment'
            'logging': 'logging'
        }
        
        for yaml_section, attr_name in section_mappings.items():
            if yaml_section in yaml_config:
                section_data = yaml_config[yaml_section]
                if isinstance(section_data, dict):
                    current_section = getattr(self, attr_name)
                    section_class = type(current_section)
                    try:
                        merged = self._merge_with_env_priority(
                            current_section.model_dump(),
                            section_data,
                            self._get_field_defaults(section_class)
                        )
                        new_section = section_class(**merged)
                        setattr(self, attr_name, new_section)
                    except Exception as e:
                        print(f"⚠️  Error updating {yaml_section} from YAML: {e}")
    
    def _get_field_defaults(self, model_class) -> Dict[str, Any]:
        """Get default values for a Pydantic model class"""
        defaults = {}
        for field_name, field_info in model_class.model_fields.items():
            if field_info.default is not None and field_info.default != Ellipsis:
                defaults[field_name] = field_info.default
            elif hasattr(field_info, 'default_factory') and field_info.default_factory:
                try:
                    defaults[field_name] = field_info.default_factory()
                except:
                    defaults[field_name] = None
            else:
                defaults[field_name] = None
        return defaults

    def _merge_with_env_priority(self, current: Dict[str, Any], yaml_vals: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-merge dicts keeping ENV-overridden values.

        - If current[key] != defaults[key], keep current (assumed ENV override).
        - Else, use yaml value.
        - For nested dicts, recurse with nested defaults.
        - For lists provided in YAML, replace entirely.
        """
        result: Dict[str, Any] = dict(current)
        for key, yaml_value in yaml_vals.items():
            cur_value = current.get(key)
            def_value = defaults.get(key)

            # If ENV override (current != default), keep current
            if cur_value != def_value and cur_value is not None and not isinstance(cur_value, dict):
                result[key] = cur_value
                continue

            # Recurse into dicts
            if isinstance(yaml_value, dict) and isinstance(cur_value, dict):
                nested_defaults = def_value if isinstance(def_value, dict) else {}
                result[key] = self._merge_with_env_priority(cur_value, yaml_value, nested_defaults)
            else:
                # Lists or scalars: prefer YAML when present
                result[key] = yaml_value

        return result
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = self.config_file or "agent_config.yaml"
        config_path = Path(config_file)
        
        if not config_path.exists():
            # Create default config file if it doesn't exist
            self._create_default_config_file(config_path)
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                return config
        except yaml.YAMLError as e:
            print(f"⚠️  Error reading YAML config: {e}")
            return {}
        except Exception as e:
            print(f"⚠️  Unexpected error loading config: {e}")
            return {}
    
    def _create_default_config_file(self, config_path: Path) -> None:
        """Create a default YAML configuration file"""
        default_config = {
            'model': {
                'provider': 'openai',
                'id': 'gpt-5-mini',
                'temperature': 1.0
            },
            'database': {
                'url': 'sqlite:///./data/qa_intelligence.db',
                'conversations_path': 'data/qa_conversations.db',
                'knowledge_path': 'data/qa_knowledge.db',
                'rag_path': 'data/qa_intelligence_rag.db'
            },
            'tools': {
                'enabled': True,
                'tools': [
                    {'name': 'web_search', 'enabled': True},
                    {'name': 'python_execution', 'enabled': True},
                    {'name': 'file_operations', 'enabled': False}
                ]
            },
            'interface': {
                'terminal': {
                    'show_tool_calls': True,
                    'enable_markdown': True
                },
                'playground': {
                    'enabled': True,
                    'port': 7777
                }
            },
            'environment': {
                'data_directory': 'data',
                'logs_directory': 'logs',
                'environment': 'development'
            },
            'logging': {
                'level': 'INFO',
                'enable_file_logging': True,
                'log_file': 'logs/qa_intelligence.log'
            }
        }
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            print(f"✅ Created default configuration file: {config_path}")
        except Exception as e:
            print(f"⚠️  Could not create config file: {e}")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        directories = [
            self.app_environment.data_directory,
            self.app_environment.logs_directory,
            self.app_environment.cache_directory,
            self.app_environment.temp_directory
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """Save current configuration to YAML file"""
        if config_path is None:
            config_path = self.config_file or "agent_config.yaml"
        
        config_dict = {
            'model': self.model.model_dump(exclude={'api_key'}),  # Don't save API key
            'database': self.database.model_dump(),
            'tools': self.tools.model_dump(),
            'interface': self.interface.model_dump(),
            'environment': self.app_environment.model_dump(),
            'logging': self.logging.model_dump()
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            print(f"✅ Configuration saved to: {config_path}")
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
    
    def get_api_key(self) -> str:
        """Get API key for the configured model provider"""
        api_key = self.model.api_key
        if api_key is None:
            raise ValueError(f"API key not configured for provider: {self.model.provider}")
        return api_key
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration as dictionary for backwards compatibility"""
        return self.model.model_dump()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as dictionary for backwards compatibility"""
        return self.database.model_dump()
    
    def get_tools_config(self) -> Dict[str, Any]:
        """Get tools configuration as dictionary for backwards compatibility"""
        return self.tools.model_dump()
    
    def get_interface_config(self) -> Dict[str, Any]:
        """Get interface configuration as dictionary for backwards compatibility"""
        return self.interface.model_dump()
    
    def get_agent_instructions(self) -> str:
        """Get agent instructions - placeholder for backwards compatibility"""
        # This can be enhanced to load from a file or configuration
        return """You are QA Intelligence, an advanced AI assistant specialized in quality assurance and testing.

Your primary responsibilities:
1. Help with test planning, design, and execution
2. Analyze test results and identify patterns
3. Provide guidance on QA best practices
4. Assist with test automation strategies
5. Support debugging and issue investigation

Always provide clear, actionable advice and maintain a focus on quality and reliability."""
    
    def validate_config(self) -> None:
        """
        Validate the complete configuration
        Raises specific exceptions for invalid configurations
        """
        # This method will raise ValidationError if any config is invalid
        # The individual model validators will handle specific validations
        
        # Additional cross-model validations can be added here
        if self.tools.enabled and not self.tools.tools:
            raise ValueError("Tools are enabled but no tools are configured")
        
        # Validate model API key is available
        try:
            api_key = self.get_api_key()
            if not api_key:
                # Try to detect API key from environment again
                provider = self.model.provider
                env_keys = [
                    f"{provider.upper()}_API_KEY",
                    "OPENAI_API_KEY",  # fallback
                    "API_KEY"  # generic fallback
                ]
                
                found_key = None
                for env_key in env_keys:
                    found_key = os.getenv(env_key)
                    if found_key:
                        # Update the model with the found key
                        self.model.api_key = found_key
                        break
                
                if not found_key:
                    raise ValueError(f"API key is required but not configured. Set {env_keys[0]} environment variable.")
        except Exception as e:
            raise ValueError(f"Model configuration error: {e}")
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration for backwards compatibility"""
        return {
            "enabled": True,
            "type": "sqlite",
            "path": self.database.url
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.app_environment.app_environment,
            "model_provider": self.model.provider,
            "model_id": self.model.id,
            "database_url": self.database.url,
            "tools_enabled": self.tools.enabled,
            "tools_count": len(self.tools.tools),
            "log_level": self.logging.level,
            "data_directory": self.app_environment.data_directory
        }
    
    def get_enabled_tools(self) -> Dict[str, bool]:
        """
        Get enabled tools configuration for backwards compatibility
        
        Returns:
            Dict of tool names and their enabled status
        """
        enabled_tools = {}
        for tool in self.tools.tools:
            enabled_tools[tool.name] = tool.enabled
        return enabled_tools



# Global settings instance
_settings: Optional[Settings] = None


def get_settings(config_file: Optional[str] = None, force_reload: bool = False) -> Settings:
    """
    Get the global settings instance
    
    Args:
        config_file: Optional path to configuration file
        force_reload: Force reloading of settings
        
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None or force_reload:
        _settings = Settings(config_file=config_file)
    
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance"""
    global _settings
    _settings = None
