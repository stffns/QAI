"""
Main settings configuration using Pydantic BaseSettings
Centralizes all configuration management with environment variable support
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

import yaml
from pydantic import Field, SkipValidation, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Detect pytest early to avoid loading .env during tests
_RUNNING_TESTS = (
    bool(os.getenv("PYTEST_CURRENT_TEST"))
    or os.getenv("ENVIRONMENT", "").lower() == "test"
    or ("pytest" in sys.modules)
)

# Load .env if available (opt-out with DISABLE_DOTENV=true) and not during tests
try:
    from dotenv import load_dotenv  # type: ignore

    if os.getenv("DISABLE_DOTENV", "false").lower() != "true" and not _RUNNING_TESTS:
        repo_root = Path(__file__).resolve().parent.parent
        candidates = [repo_root / ".env", Path.cwd() / ".env"]
        for p in candidates:
            if p.exists():
                load_dotenv(p, override=False)
                break
except Exception:
    # Non-fatal if dotenv is unavailable
    pass

from .models import (
    AppEnvironmentConfig,
    DatabaseConfig,
    InterfaceConfig,
    LoggingConfig,
    ModelConfig,
    ToolsConfig,
)


# Build ModelConfig from environment without running validators.
def _build_model_from_env_for_settings() -> ModelConfig:
    def _get(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(name, default)

    def _get_float(name: str, default: float) -> float:
        raw = os.environ.get(name)
        try:
            return float(raw) if raw is not None else default
        except Exception:
            return default

    def _get_int(name: str, default: Optional[int]) -> Optional[int]:
        raw = os.environ.get(name)
        if raw is None or str(raw).strip() == "":
            return default
        try:
            return int(raw)
        except Exception:
            return default

    provider = _get("MODEL_PROVIDER", "openai")
    model_id = _get("MODEL_ID", _get("AGENT_DEFAULT_MODEL", "gpt-5-mini"))
    stream_raw = os.environ.get("MODEL_STREAM")
    stream_val = True if stream_raw is None else str(stream_raw).lower() == "true"

    data = {
        "provider": provider,
        "id": model_id,
        "api_key": _get("MODEL_API_KEY"),
        "temperature": _get_float("MODEL_TEMPERATURE", 0.7),
        "max_tokens": _get_int("MODEL_MAX_TOKENS", None),
        "timeout": _get_int("MODEL_TIMEOUT", 30) or 30,
        "base_url": _get("MODEL_BASE_URL"),
        "organization": _get("OPENAI_ORGANIZATION"),
        "project": _get("OPENAI_PROJECT"),
        "stream": stream_val,
        "stream_config": {
            "enabled": True,
            "chunk_delay": 0.01,
            "show_thinking": False,
            "buffer_size": 1024,
        },
    }
    # Test-friendly Azure defaults: avoid hard failure in Settings when provider=azure without base_url
    try:
        import sys as _sys  # local import to avoid shadowing

        _running_tests = (
            bool(os.getenv("PYTEST_CURRENT_TEST"))
            or os.getenv("ENVIRONMENT", "").lower() == "test"
            or ("pytest" in _sys.modules)
        )
    except Exception:
        _running_tests = False
    if data.get("provider") == "azure" and not data.get("base_url"):
        # Prefer common Azure env var names if present
        azure_env = _get("AZURE_OPENAI_ENDPOINT") or _get("AZURE_BASE_URL")
        if azure_env:
            data["base_url"] = azure_env
        elif _running_tests:
            # Safe placeholder during tests
            data["base_url"] = "http://localhost"
    return ModelConfig.model_construct(**data)


class Settings(BaseSettings):
    """
    Main application settings using Pydantic BaseSettings

    Supports configuration from:
    1. Environment variables
    2. YAML configuration files
    3. Default values

    Priority order: ENV vars > YAML file > defaults
    """

    # Set env_file to project .env unless explicitly disabled
    _ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="allow",
        env_file=(
            str(_ENV_FILE)
            if os.getenv("DISABLE_DOTENV", "false").lower() != "true"
            and not _RUNNING_TESTS
            and _ENV_FILE.exists()
            else None
        ),
        env_file_encoding="utf-8",
    )

    # Prevent dotenv autoload during tests by customizing settings sources
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings=None,
        env_settings=None,
        dotenv_settings=None,
        file_secret_settings=None,
        **kwargs,
    ):
        """Customize settings sources to avoid reading .env during tests.

        Supports both pydantic-settings signatures:
        - (settings_cls, init_settings, env_settings, file_secret_settings)
        - (settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings)
        """
        disable_dotenv = (
            os.getenv("DISABLE_DOTENV", "false").lower() == "true" or _RUNNING_TESTS
        )
        # Some versions pass 4 sources (no dotenv), others pass 5 (with dotenv)
        if dotenv_settings is None or disable_dotenv:
            return (env_settings, init_settings, file_secret_settings)
        return (env_settings, dotenv_settings, init_settings, file_secret_settings)

    # Core configuration sections (use factories so env vars are read at instantiation time)
    model: Annotated[ModelConfig, SkipValidation] = Field(
        default_factory=_build_model_from_env_for_settings
    )
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)
    app_environment: AppEnvironmentConfig = Field(default_factory=AppEnvironmentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Global settings
    config_file: Optional[str] = "agent_config.yaml"
    version: str = "1.0.0"
    app_name: str = "QA Intelligence"

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook to load YAML and ensure directories"""
        # Some environments may not trigger model_post_init reliably; an
        # explicit after-validator is also added below for robustness.
        yaml_config = self._load_yaml_config()
        if yaml_config:
            self._update_from_yaml(yaml_config)
        # Validate model to surface env/YAML errors (e.g., temperature out of range)
        # Keep test-friendly Azure base_url from _build_model_from_env_for_settings
        self.model = ModelConfig(**self.model.model_dump())
        self._ensure_directories()

    @model_validator(mode="after")
    def _apply_yaml_after(self) -> "Settings":
        """Ensure YAML merge runs even if model_post_init isn't triggered."""
        yaml_config = self._load_yaml_config()
        if yaml_config:
            self._update_from_yaml(yaml_config)
        # Re-validate after potential YAML merge
        self.model = ModelConfig(**self.model.model_dump())
        self._ensure_directories()
        return self

    def _update_from_yaml(self, yaml_config: Dict[str, Any]) -> None:
        """Update configuration from YAML data - Environment variables have priority.

        Performs a deep merge: for nested dicts, merge recursively. For scalars,
        keep current (ENV) value when it differs from the default; otherwise take YAML.
        Lists are replaced by YAML entirely if provided.
        """
        section_mappings = {
            "model": "model",
            "database": "database",
            "tools": "tools",
            "interface": "interface",
            "environment": "app_environment",  # Map YAML 'environment' to 'app_environment'
            "logging": "logging",
        }

        for yaml_section, attr_name in section_mappings.items():
            if yaml_section in yaml_config:
                section_data = yaml_config[yaml_section]
                if isinstance(section_data, dict):
                    current_section = getattr(self, attr_name)
                    section_class = type(current_section)
                    if attr_name == "model":
                        # Special handling: YAML should override defaults unless an explicit ENV var exists
                        merged = self._merge_model_section(
                            current_section.model_dump(), section_data
                        )
                        # Run validators here so YAML-only Azure without base_url raises as expected in tests
                        new_section = section_class(**merged)
                    elif attr_name == "database":
                        # Build new config from current, then apply YAML, then apply explicit ENV overrides
                        base = current_section.model_dump()
                        base.update(section_data)
                        new_section = section_class(**base)
                        # ENV overrides
                        if os.environ.get("DB_URL"):
                            new_section.url = os.environ["DB_URL"]
                        if os.environ.get("DB_POOL_SIZE"):
                            new_section.pool_size = int(os.environ["DB_POOL_SIZE"])
                    elif attr_name == "tools":
                        base = current_section.model_dump()
                        base.update(section_data)
                        new_section = section_class(**base)
                        # ENV overrides for common fields
                        if os.environ.get("TOOLS_ENABLED"):
                            new_section.enabled = (
                                os.environ["TOOLS_ENABLED"].lower() == "true"
                            )
                        if os.environ.get("TOOLS_TIMEOUT"):
                            new_section.default_timeout = int(
                                os.environ["TOOLS_TIMEOUT"]
                            )
                        if os.environ.get("TOOLS_MAX_CONCURRENT"):
                            new_section.max_concurrent_tools = int(
                                os.environ["TOOLS_MAX_CONCURRENT"]
                            )
                    else:
                        merged = self._merge_with_env_priority(
                            current_section.model_dump(),
                            section_data,
                            self._get_effective_defaults(section_class),
                        )
                        new_section = section_class(**merged)
                    setattr(self, attr_name, new_section)

    def _merge_model_section(
        self, current: Dict[str, Any], yaml_vals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge model section giving priority to explicit ENV vars per-field.

        - If an env var for the field exists (non-empty), keep current value.
        - Otherwise, take YAML value.
        - For nested dicts like stream_config, replace with YAML when provided.
        """
        env_map = {
            "provider": "MODEL_PROVIDER",
            "id": "MODEL_ID",
            "api_key": "MODEL_API_KEY",
            "temperature": "MODEL_TEMPERATURE",
            "max_tokens": "MODEL_MAX_TOKENS",
            "timeout": "MODEL_TIMEOUT",
            "base_url": "MODEL_BASE_URL",
            "organization": "OPENAI_ORGANIZATION",
            "project": "OPENAI_PROJECT",
            "stream": "MODEL_STREAM",
            "response_format": "MODEL_RESPONSE_FORMAT",
        }

        # Defaults used to detect non-explicit env overrides (env set to default shouldn't block YAML)
        default_like = {
            "provider": "openai",
            "id": "gpt-5-mini",
            "api_key": None,
            "temperature": 0.7,
            "max_tokens": None,
            "timeout": 30,
            "base_url": None,
            "organization": None,
            "project": None,
            "stream": True,
            "response_format": None,
        }

        result: Dict[str, Any] = dict(current)
        for key, yaml_value in yaml_vals.items():
            # Replace nested config blocks outright
            if isinstance(yaml_value, dict) and key == "stream_config":
                result[key] = yaml_value
                continue

            env_key = env_map.get(key)
            env_set = None
            try:
                env_set = os.environ.get(env_key) if env_key else None
            except Exception:
                env_set = None

            # Treat env equal to default as not an explicit override
            is_default_like = False
            if env_set is not None:
                try:
                    if key in ("temperature", "timeout"):
                        cast_env = (
                            float(env_set) if key == "temperature" else int(env_set)
                        )
                        is_default_like = cast_env == default_like[key]
                    elif key == "stream":
                        cast_env = str(env_set).lower() == "true"
                        is_default_like = cast_env == default_like[key]
                    else:
                        if default_like[key] is None:
                            is_default_like = str(env_set).strip() == ""
                        else:
                            is_default_like = env_set == str(default_like[key])
                except Exception:
                    is_default_like = False

            if not env_set or str(env_set).strip() == "" or is_default_like:
                result[key] = yaml_value

        # If YAML switches provider to azure and no base_url provided anywhere, keep base_url None
        # so that ModelConfig validators can raise as expected by tests.
        if yaml_vals.get("provider") == "azure" and not yaml_vals.get("base_url"):
            result["base_url"] = None

        return result

    def _get_effective_defaults(self, model_class) -> Dict[str, Any]:
        """Get static field defaults without constructing the model.

        Avoids environment-influenced instantiation so ENV values are treated
        as overrides vs defaults when merging with YAML.
        """
        defaults: Dict[str, Any] = {}
        for field_name, field_info in model_class.model_fields.items():
            if field_info.default is not None and field_info.default != Ellipsis:
                defaults[field_name] = field_info.default
            elif hasattr(field_info, "default_factory") and field_info.default_factory:
                try:
                    defaults[field_name] = field_info.default_factory()
                except Exception:
                    defaults[field_name] = None
            else:
                defaults[field_name] = None
        return defaults

    def _merge_with_env_priority(
        self,
        current: Dict[str, Any],
        yaml_vals: Dict[str, Any],
        defaults: Dict[str, Any],
    ) -> Dict[str, Any]:
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

            # Process each key using helper methods
            if self._should_keep_current_value(cur_value, def_value):
                result[key] = cur_value
            elif self._should_merge_nested_dict(yaml_value, cur_value):
                result[key] = self._merge_nested_dict(cur_value, yaml_value, def_value)
            else:
                result[key] = yaml_value

        return result

    def _merge_with_env_map(
        self,
        current: Dict[str, Any],
        yaml_vals: Dict[str, Any],
        env_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Merge section values using explicit env var mapping per-field.

        If the env var for a field is set (non-empty), keep current value; otherwise use YAML.
        Dict values are replaced by YAML when provided.
        """
        result: Dict[str, Any] = dict(current)
        for key, yaml_value in yaml_vals.items():
            if isinstance(yaml_value, dict):
                result[key] = yaml_value
                continue
            env_key = env_map.get(key)
            env_set = os.environ.get(env_key) if env_key else None
            if env_set is not None and str(env_set).strip() != "":
                # Explicit ENV override present; keep current
                result[key] = current.get(key)
            else:
                result[key] = yaml_value
        return result

    def _should_keep_current_value(
        self, current_value: Any, default_value: Any
    ) -> bool:
        """Check if current value should be kept (ENV override)"""
        return (
            current_value != default_value
            and current_value is not None
            and not isinstance(current_value, dict)
        )

    def _should_merge_nested_dict(self, yaml_value: Any, current_value: Any) -> bool:
        """Check if values should be merged as nested dictionaries"""
        return isinstance(yaml_value, dict) and isinstance(current_value, dict)

    def _merge_nested_dict(
        self, current_value: Any, yaml_value: Dict[str, Any], default_value: Any
    ) -> Dict[str, Any]:
        """Merge nested dictionary values recursively"""
        nested_defaults = default_value if isinstance(default_value, dict) else {}
        return self._merge_with_env_priority(current_value, yaml_value, nested_defaults)

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = self.config_file or "agent_config.yaml"
        config_path = Path(config_file)

        if not config_path.exists():
            # Create default config file if it doesn't exist
            self._create_default_config_file(config_path)
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
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
            "model": {"provider": "openai", "id": "gpt-5-mini", "temperature": 1.0},
            "database": {
                "url": "sqlite:///./data/qa_intelligence.db",
                "conversations_path": "data/qa_conversations.db",
                "knowledge_path": "data/qa_knowledge.db",
                "rag_path": "data/qa_intelligence_rag.db",
            },
            "tools": {
                "enabled": True,
                "tools": [
                    {"name": "web_search", "enabled": True},
                    {"name": "python_execution", "enabled": True},
                    {"name": "file_operations", "enabled": False},
                ],
            },
            "interface": {
                "terminal": {"show_tool_calls": True, "enable_markdown": True},
                "playground": {"enabled": True, "port": 7777},
            },
            "environment": {
                "data_directory": "data",
                "logs_directory": "logs",
                "environment": "development",
            },
            "logging": {
                "level": "INFO",
                "enable_file_logging": True,
                "log_file": "logs/qa_intelligence.log",
            },
        }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
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
            self.app_environment.temp_directory,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def save_config(self, config_path: Optional[str] = None) -> None:
        """Save current configuration to YAML file"""
        if config_path is None:
            config_path = self.config_file or "agent_config.yaml"

        config_dict = {
            "model": self.model.model_dump(exclude={"api_key"}),  # Don't save API key
            "database": self.database.model_dump(),
            "tools": self.tools.model_dump(),
            "interface": self.interface.model_dump(),
            "environment": self.app_environment.model_dump(),
            "logging": self.logging.model_dump(),
        }

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            print(f"✅ Configuration saved to: {config_path}")
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")

    def get_api_key(self) -> str:
        """Get API key for the configured model provider"""
        api_key = self.model.api_key
        if api_key is None:
            raise ValueError(
                f"API key not configured for provider: {self.model.provider}"
            )
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
        """Get agent instructions - optimized for concise responses"""
        return """You are QA Intelligence, a direct and efficient AI assistant for quality assurance.

Core behavior:
- Provide concise, actionable responses
- Use tools to answer questions directly
- Only give detailed analysis when explicitly requested
- Focus on immediate, practical solutions

Response style:
- Brief and to the point
- Use tool results as-is without extensive interpretation
- Save long explanations for when users ask "why" or "explain more"
- Prioritize efficiency over exhaustive analysis

When using tools: Present results clearly and ask if more detail is needed."""

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
                    "API_KEY",  # generic fallback
                ]

                found_key = None
                for env_key in env_keys:
                    found_key = os.getenv(env_key)
                    if found_key:
                        # Update the model with the found key
                        self.model.api_key = found_key
                        break

                if not found_key:
                    raise ValueError(
                        f"API key is required but not configured. Set {env_keys[0]} environment variable."
                    )
        except Exception as e:
            raise ValueError(f"Model configuration error: {e}")

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration for backwards compatibility"""
        return {"enabled": True, "type": "sqlite", "path": self.database.url}

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
            "data_directory": self.app_environment.data_directory,
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


def get_settings(
    config_file: Optional[str] = None, force_reload: bool = False
) -> Settings:
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
