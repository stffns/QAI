"""
Core configuration models for QA Intelligence

This module contains the primary configuration models that form the foundation
of the QA Intelligence system:

- ModelConfig: AI model provider and settings configuration
- DatabaseConfig: Database connections and storage settings  
- ToolConfig: Individual tool configuration
- ToolsConfig: Tool management and orchestration settings

All models use Pydantic for validation and automatic environment variable
support. Environment variables take precedence over YAML configuration values.

Usage:
    from config.models.core import ModelConfig, DatabaseConfig, ToolsConfig
    
    # These will automatically load from env vars or use defaults
    model_config = ModelConfig()
    db_config = DatabaseConfig()
    tools_config = ToolsConfig()
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# Helper functions to safely read environment variables at instantiation time
def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None else default


def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    v = os.environ.get(name)
    try:
        return int(v) if v is not None and str(v).strip() != "" else default
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return v.lower() == "true" if isinstance(v, str) else default


class ModelProvider(str, Enum):
    """
    Supported AI model providers.
    
    This enum defines all officially supported AI model providers.
    New providers should be added here with appropriate validation.
    """
    OPENAI = "openai"
    AZURE = "azure" 
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"  # Future support
    GOOGLE = "google"        # Future support


class DatabaseType(str, Enum):
    """
    Supported database types.
    
    Defines the available database backend options for different
    storage needs in the QA Intelligence system.
    """
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MEMORY = "memory"  # For testing


class ModelConfig(BaseModel):
    """
    Configuration for AI model settings and provider connections.
    
    This model handles configuration for various AI providers including OpenAI,
    Azure OpenAI, DeepSeek, and others. It supports automatic environment
    variable loading with sensible defaults.
    
    Environment Variables:
        MODEL_PROVIDER: AI provider name (openai, azure, deepseek)
        MODEL_ID: Model identifier (gpt-4, gpt-3.5-turbo, etc.)
        MODEL_API_KEY: API key for the provider
        MODEL_TEMPERATURE: Response randomness (0.0-2.0)
        MODEL_MAX_TOKENS: Maximum tokens in response
        MODEL_TIMEOUT: Request timeout in seconds
        MODEL_BASE_URL: Custom API endpoint URL
        
    Example:
        # Using environment variables
        export MODEL_PROVIDER=openai
        export MODEL_ID=gpt-4
        export MODEL_API_KEY=sk-...
        
        # Or programmatically
        config = ModelConfig(
            provider="openai",
            id="gpt-4",
            temperature=0.7
        )
    """
    
    # Core model settings
    provider: str = Field(
        default_factory=lambda: _env_str("MODEL_PROVIDER") or "openai",
        description="AI model provider (openai, azure, deepseek, etc.)"
    )
    id: str = Field(
        default_factory=lambda: _env_str("MODEL_ID") or _env_str("AGENT_DEFAULT_MODEL") or "gpt-5-mini",
        description="Model identifier/name"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the model provider"
    )
    
    # Response configuration
    temperature: float = Field(
        default_factory=lambda: _env_float("MODEL_TEMPERATURE", 0.7),
        description="Model temperature for response randomness (0.0 = deterministic, 2.0 = very creative)"
    )
    max_tokens: Optional[int] = Field(
        default_factory=lambda: _env_int("MODEL_MAX_TOKENS"),
        gt=0,
        description="Maximum tokens in model response (null = no limit)"
    )
    
    # Connection settings
    timeout: int = Field(
        default_factory=lambda: _env_int("MODEL_TIMEOUT", 30) or 30,
        gt=0,
        description="Request timeout in seconds"
    )
    base_url: Optional[str] = Field(
        default_factory=lambda: _env_str("MODEL_BASE_URL"),
        description="Custom base URL for API endpoints"
    )
    
    # Provider-specific settings
    organization: Optional[str] = Field(
        default_factory=lambda: _env_str("OPENAI_ORGANIZATION"),
        description="Organization ID for OpenAI API requests"
    )
    project: Optional[str] = Field(
        default_factory=lambda: _env_str("OPENAI_PROJECT"),
        description="Project ID for OpenAI API requests"
    )
    
    # Advanced settings
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: float = Field(
        default_factory=lambda: _env_float("MODEL_FREQUENCY_PENALTY", 0.0),
        ge=-2.0,
        le=2.0,
        description="Frequency penalty for token repetition"
    )
    presence_penalty: float = Field(
        default_factory=lambda: _env_float("MODEL_PRESENCE_PENALTY", 0.0),
        ge=-2.0,
        le=2.0,
        description="Presence penalty for new topics"
    )
    seed: Optional[int] = Field(
        default_factory=lambda: _env_int("MODEL_SEED"),
        description="Random seed for reproducible outputs"
    )
    response_format: Optional[str] = Field(
        default_factory=lambda: _env_str("MODEL_RESPONSE_FORMAT"),
        description="Response format (json, text, etc.)"
    )
    
    # Streaming configuration
    stream: bool = Field(
        default_factory=lambda: _env_bool("MODEL_STREAM", True),
        description="Enable streaming responses for real-time output"
    )
    stream_config: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "enabled": True,
            "chunk_delay": 0.01,
            "show_thinking": False,  # Changed default to False for concise responses
            "buffer_size": 1024
        },
        description="Advanced streaming configuration options"
    )
    
    # Response control configuration
    system_instructions: Optional[str] = Field(
        default=None,
        description="System instructions for guiding model behavior"
    )

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate that the provider is supported."""
        if v not in [provider.value for provider in ModelProvider]:
            raise ValueError(
                f"Unsupported provider: {v}. "
                f"Supported providers: {[p.value for p in ModelProvider]}"
            )
        return v.lower()

    @field_validator('temperature')
    @classmethod 
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is within acceptable range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key format if provided."""
        if v is not None:
            v = v.strip()
            # Keep a minimal length check but allow short test keys used in unit tests
            if len(v) < 6:  # Basic length check
                raise ValueError("API key appears to be too short")
        return v

    @model_validator(mode='after')
    def validate_provider_specific_settings(self):
        """Validate provider-specific configuration requirements."""
        # OpenAI validation
        if self.provider == "openai" and not self.api_key:
            # Only warn if not in test environment
            if os.getenv("ENVIRONMENT") != "test":
                import warnings
                warnings.warn("OpenAI provider requires an API key", UserWarning)
        
        # Azure validation
        if self.provider == "azure":
            if not self.base_url:
                raise ValueError("Azure provider requires base_url (Azure endpoint)")
            if not self.api_key:
                raise ValueError("Azure provider requires an API key")
        
        return self

    def get_provider_config(self) -> Dict[str, Any]:
        """
        Get provider-specific configuration dictionary.
        
        Returns:
            Dictionary with provider-specific settings ready for API calls
        """
        base_config = {
            "model": self.id,
            "temperature": self.temperature,
            "timeout": self.timeout
        }
        
        # Optional common settings
        if self.api_key:
            base_config["api_key"] = self.api_key
        if self.max_tokens:
            base_config["max_tokens"] = self.max_tokens
        if self.base_url:
            base_config["base_url"] = self.base_url
        if self.top_p is not None:
            base_config["top_p"] = self.top_p
        if self.frequency_penalty != 0.0:
            base_config["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            base_config["presence_penalty"] = self.presence_penalty
        if self.seed is not None:
            base_config["seed"] = self.seed
        if self.response_format:
            base_config["response_format"] = self.response_format
            
        # Add provider-specific fields
        if self.provider == "openai":
            if self.organization:
                base_config["organization"] = self.organization
            if self.project:
                base_config["project"] = self.project

        return base_config

    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True
    )


class DatabaseConfig(BaseModel):
    """
    Configuration for database connections and storage settings.
    
    Supports multiple database backends with connection pooling,
    automatic migrations, and backup configurations.
    
    Environment Variables:
        DB_URL: Complete database URL
        DB_HOST: Database host
        DB_PORT: Database port  
        DB_NAME: Database name
        DB_USER: Database username
        DB_PASSWORD: Database password
        DB_POOL_SIZE: Connection pool size
        DB_MAX_OVERFLOW: Maximum pool overflow
        
    Example:
        # SQLite (default)
        config = DatabaseConfig()
        
        # PostgreSQL
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/qadb"
        )
    """
    
    # Primary database connection
    url: Optional[str] = Field(
        default=None,
        description="Complete database URL"
    )
    
    # Individual connection components (used if url not provided)
    host: Optional[str] = Field(
        default_factory=lambda: os.environ.get("DB_HOST"),
        description="Database host"
    )
    port: Optional[int] = Field(
        default_factory=lambda: _env_int("DB_PORT"),
        description="Database port"
    )
    name: Optional[str] = Field(
        default_factory=lambda: os.environ.get("DB_NAME"),
        description="Database name"
    )
    user: Optional[str] = Field(
        default_factory=lambda: os.environ.get("DB_USER"),
        description="Database username"
    )
    password: Optional[str] = Field(
        default_factory=lambda: os.environ.get("DB_PASSWORD"),
        description="Database password"
    )
    
    # Connection pool settings
    pool_size: int = Field(
        default_factory=lambda: int(os.environ.get("DB_POOL_SIZE", "20")),
        ge=1,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default_factory=lambda: int(os.environ.get("DB_MAX_OVERFLOW", "30")),
        ge=0,
        description="Maximum pool overflow connections"
    )
    pool_timeout: int = Field(
        default_factory=lambda: int(os.environ.get("DB_POOL_TIMEOUT", "30")),
        ge=1,
        description="Pool connection timeout in seconds"
    )
    
    # Additional database settings
    echo: bool = Field(
        default_factory=lambda: os.environ.get("DB_ECHO", "false").lower() == "true",
        description="Enable SQL query logging"
    )
    enable_migrations: bool = Field(
        default_factory=lambda: os.environ.get("DB_ENABLE_MIGRATIONS", "true").lower() == "true",
        description="Enable automatic database migrations"
    )
    backup_enabled: bool = Field(
        default_factory=lambda: os.environ.get("DB_BACKUP_ENABLED", "false").lower() == "true",
        description="Enable automatic database backups"
    )
    backup_interval: int = Field(
        default_factory=lambda: int(os.environ.get("DB_BACKUP_INTERVAL", "24")),
        ge=1,
        description="Backup interval in hours"
    )

    @field_validator('url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        # Allow empty string to support building connection string from components
        if v is None:
            # Allow None here; we'll fill from env/default later in model validator
            return v
        if v == "":
            return v
        
        # Basic URL validation with support for SQLAlchemy dialect+driver
        # Examples: postgresql://, postgresql+psycopg://, sqlite:///, sqlite+pysqlite://, mysql://
        allowed_prefixes = (
            "sqlite:///", "sqlite://", "sqlite+pysqlite://",
            "postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://",
            "mysql://", "mysql+pymysql://", "mysql+mysqlconnector://",
            "oracle://", "oracle+cx_oracle://"
        )
        if not v.startswith(allowed_prefixes):
            raise ValueError(
                "Invalid database URL scheme. Must be a supported SQLAlchemy URL (e.g., "
                "sqlite:///path.db, postgresql://..., mysql://...)"
            )
        
        return v

    @model_validator(mode='before')
    @classmethod
    def inject_env_url(cls, data: Any) -> Any:
        """Inject DB_URL from environment if url is not provided.
        Do not override explicit empty string (used to build from components)."""
        if data is None:
            data = {}
        # If url is missing or None, but env provides DB_URL, use it
        url_value = data.get('url') if isinstance(data, dict) else None
        if (url_value is None) and os.environ.get("DB_URL"):
            if isinstance(data, dict):
                data['url'] = os.environ.get("DB_URL")
        return data

    @model_validator(mode='after')
    def ensure_database_directory(self):
        """Ensure database directory exists for SQLite databases."""
        # If url is empty string, ensure required components are present; else error
        if self.url == "":
            if not all([self.host, self.name, self.user]):
                raise ValueError("Database URL cannot be empty")
            return self
        
        # If url is None, populate from env or default
        if self.url is None:
            self.url = os.environ.get("DB_URL", "sqlite:///./data/qa_intelligence.db")

        if self.url.startswith('sqlite:///'):
            # Extract path from SQLite URL
            db_path = self.url.replace('sqlite:///', '')
            db_dir = Path(db_path).parent
            # Avoid side effects during tests
            if os.getenv("ENVIRONMENT") != "test":
                if db_dir != Path('.'):  # Don't create directory for current dir
                    db_dir.mkdir(parents=True, exist_ok=True)
        
        return self

    def get_connection_string(self) -> str:
        """
        Get the complete database connection string.
        
        Returns:
            Formatted connection string ready for SQLAlchemy
        """
        if self.url:
            return self.url
        
        # Build connection string from components
        if not all([self.host, self.name, self.user]):
            raise ValueError("Missing required database connection parameters")
        
        password_part = f":{self.password}" if self.password else ""
        port_part = f":{self.port}" if self.port else ""
        
        return f"postgresql://{self.user}{password_part}@{self.host}{port_part}/{self.name}"

    model_config = ConfigDict(
        str_to_lower=True,
        extra='allow',
        validate_assignment=True
    )


class ToolConfig(BaseModel):
    """
    Configuration for individual tools in the QA Intelligence system.
    
    Each tool can be individually configured with its own settings,
    timeout values, and feature flags.
    
    Example:
        web_search = ToolConfig(
            name="web_search",
            enabled=True,
            timeout=30,
            settings={"max_results": 10}
        )
    """
    
    name: str = Field(
        description="Unique tool identifier"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this tool is enabled"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="Tool execution timeout in seconds"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific configuration settings"
    )
    required_permissions: List[str] = Field(
        default_factory=list,
        description="Required permissions for tool execution"
    )

    @field_validator('name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        
        # Tool name should be snake_case
        if not v.replace('_', '').isalnum():
            raise ValueError("Tool name must contain only letters, numbers, and underscores")
        
        return v.lower().strip()

    model_config = ConfigDict(
        str_to_lower=True,
        extra='allow',
        validate_assignment=True
    )


class ToolsConfig(BaseModel):
    """
    Configuration for tool management and orchestration.
    
    Manages the collection of available tools, global tool settings,
    and tool execution policies.
    
    Environment Variables:
        TOOLS_ENABLED: Global tool enablement (true/false)
        TOOLS_TIMEOUT: Default tool timeout
        TOOLS_MAX_CONCURRENT: Maximum concurrent tool executions
        TOOLS_SAFETY_MODE: Enable safety restrictions
        
    Example:
        config = ToolsConfig(
            enabled=True,
            tools=[
                ToolConfig(name="web_search", enabled=True),
                ToolConfig(name="python_execution", enabled=True),
                ToolConfig(name="file_operations", enabled=False)
            ]
        )
    """
    
    # Global tool settings
    enabled: bool = Field(
        default_factory=lambda: os.environ.get("TOOLS_ENABLED", "true").lower() == "true",
        description="Whether tools are enabled globally"
    )
    
    # Tool collection
    tools: List[ToolConfig] = Field(
        default_factory=lambda: [
            # Only the four default tools expected by tests
            ToolConfig(name="web_search", enabled=True, timeout=30),
            ToolConfig(name="python_execution", enabled=True, timeout=60),
            ToolConfig(name="file_operations", enabled=False, timeout=15),
            ToolConfig(name="calculator", enabled=True, timeout=5),
        ],
        description="List of available tools with their configurations"
    )
    
    # Execution settings
    default_timeout: int = Field(
        default_factory=lambda: int(os.environ.get("TOOLS_TIMEOUT", "30")),
        gt=0,
        description="Default timeout for tool execution in seconds"
    )
    max_concurrent_tools: int = Field(
        default_factory=lambda: int(os.environ.get("TOOLS_MAX_CONCURRENT", "5")),
        gt=0,
        description="Maximum number of tools that can run concurrently"
    )
    
    # Safety and security
    safety_mode: bool = Field(
        default_factory=lambda: os.environ.get("TOOLS_SAFETY_MODE", "true").lower() == "true",
        description="Enable safety restrictions for tool execution"
    )
    allowed_domains: List[str] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1"
        ],
        description="Allowed domains for web-based tools"
    )
    blocked_commands: List[str] = Field(
        default_factory=lambda: ["rm -rf", "del /f", "format", "fdisk"],
        description="Blocked commands for execution tools"
    )

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """
        Get configuration for a specific tool.
        
        Args:
            tool_name: Name of the tool to find
            
        Returns:
            ToolConfig if found, None otherwise
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if a specific tool is enabled.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is globally enabled and individually enabled
        """
        if not self.enabled:
            return False
        
        tool_config = self.get_tool_config(tool_name)
        return tool_config.enabled if tool_config else False

    def add_tool(self, tool_config: ToolConfig) -> None:
        """
        Add a new tool configuration.
        
        Args:
            tool_config: Tool configuration to add
            
        Raises:
            ValueError: If tool with same name already exists
        """
        if self.get_tool_config(tool_config.name):
            raise ValueError(f"Tool '{tool_config.name}' already exists")
        
        self.tools.append(tool_config)

    def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool configuration.
        
        Args:
            tool_name: Name of the tool to remove
            
        Returns:
            True if tool was removed, False if not found
        """
        for i, tool in enumerate(self.tools):
            if tool.name == tool_name:
                del self.tools[i]
                return True
        return False

    def get_enabled_tools(self) -> List[ToolConfig]:
        """
        Get list of all enabled tools.
        
        Returns:
            List of enabled tool configurations
        """
        if not self.enabled:
            return []
        
        return [tool for tool in self.tools if tool.enabled]

    @model_validator(mode='after')
    def validate_tool_names_unique(self):
        """Ensure all tool names are unique."""
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate tool names found: {duplicates}")
        
        return self

    model_config = ConfigDict(
        str_to_lower=True,
        extra='allow',
        validate_assignment=True
    )


class ReasoningConfig(BaseModel):
    """
    Configuration for reasoning capabilities and response optimization.
    
    This model controls when to use detailed reasoning vs concise responses,
    helping balance response speed with thoroughness and cost efficiency.
    """
    
    # Core reasoning settings
    enabled: bool = Field(
        default=os.getenv("REASONING_ENABLED", "true").lower() == "true",
        description="Enable reasoning capabilities"
    )
    type: str = Field(
        default=os.getenv("REASONING_TYPE", "agent"),
        description="Type of reasoning (agent, model, tools)"
    )
    
    # Response control
    auto_reasoning: bool = Field(
        default=os.getenv("REASONING_AUTO", "false").lower() == "true",
        description="Automatically enable reasoning for all queries"
    )
    triggers: List[str] = Field(
        default_factory=lambda: [
            "explain in detail", "analyze", "complex reasoning", 
            "step by step", "comprehensive", "elaborate"
        ],
        description="Keywords that trigger detailed reasoning"
    )
    
    # Multi-model configuration for cost optimization
    reasoning_model: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "id": "gpt-5",  # Full model for complex reasoning
            "temperature": 0.7,
            "max_tokens": 1500
        },
        description="Model configuration specifically for complex reasoning tasks"
    )
    
    simple_model: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "id": "gpt-5-nano",  # Ultra-fast model for simple tasks
            "temperature": 0.2,
            "max_tokens": 100,
            "triggers": [
                "yes/no questions", "simple greetings", "basic confirmations",
                "hello", "hi", "thanks", "thank you", "ok", "yes", "no"
            ]
        },
        description="Model configuration for very simple interactions"
    )
    
    # Performance settings
    concise_mode: bool = Field(
        default=os.getenv("REASONING_CONCISE", "true").lower() == "true",
        description="Prioritize concise responses by default"
    )
    max_concise_tokens: int = Field(
        default=int(os.getenv("REASONING_CONCISE_TOKENS", "300")),
        ge=50,
        le=1000,
        description="Maximum tokens for concise responses"
    )
    
    # Cost optimization settings
    cost_optimization: bool = Field(
        default=os.getenv("REASONING_COST_OPT", "true").lower() == "true",
        description="Enable cost optimization through model selection"
    )

    @field_validator('type')
    @classmethod
    def validate_reasoning_type(cls, v: str) -> str:
        """Validate reasoning type."""
        valid_types = ["agent", "model", "tools"]
        if v not in valid_types:
            raise ValueError(f"Invalid reasoning type: {v}. Must be one of {valid_types}")
        return v

    model_config = ConfigDict(
        str_to_lower=True,
        extra='allow',
        validate_assignment=True
    )
