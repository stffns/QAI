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
        default=os.getenv("MODEL_PROVIDER", "openai"),
        description="AI model provider (openai, azure, deepseek, etc.)"
    )
    id: str = Field(
        default=os.getenv("MODEL_ID", os.getenv("AGENT_DEFAULT_MODEL", "gpt-5-mini")), 
        description="Model identifier/name"
    )
    api_key: Optional[str] = Field(
        default=os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY"),
        description="API key for the model provider"
    )
    
    # Response configuration
    temperature: float = Field(
        default=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
        ge=0.0,
        le=2.0,
        description="Model temperature for response randomness (0.0 = deterministic, 2.0 = very creative)"
    )
    max_tokens: Optional[int] = Field(
        default=int(os.getenv("MODEL_MAX_TOKENS", "0")) if os.getenv("MODEL_MAX_TOKENS") else None,
        gt=0,
        description="Maximum tokens in model response (null = no limit)"
    )
    
    # Connection settings
    timeout: int = Field(
        default=int(os.getenv("MODEL_TIMEOUT", "30")),
        gt=0,
        description="Request timeout in seconds"
    )
    base_url: Optional[str] = Field(
        default=os.getenv("MODEL_BASE_URL"),
        description="Custom base URL for API endpoints"
    )
    
    # Provider-specific settings
    organization: Optional[str] = Field(
        default=os.getenv("OPENAI_ORGANIZATION"),
        description="Organization ID for OpenAI API requests"
    )
    project: Optional[str] = Field(
        default=os.getenv("OPENAI_PROJECT"),
        description="Project ID for OpenAI API requests"
    )
    
    # Advanced settings
    top_p: Optional[float] = Field(
        default=float(os.getenv("MODEL_TOP_P", "1.0")),
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: float = Field(
        default=float(os.getenv("MODEL_FREQUENCY_PENALTY", "0.0")),
        ge=-2.0,
        le=2.0,
        description="Frequency penalty for token repetition"
    )
    presence_penalty: float = Field(
        default=float(os.getenv("MODEL_PRESENCE_PENALTY", "0.0")),
        ge=-2.0,
        le=2.0,
        description="Presence penalty for new topics"
    )
    seed: Optional[int] = Field(
        default=int(os.getenv("MODEL_SEED", "0")) if os.getenv("MODEL_SEED") else None,
        description="Random seed for reproducible outputs"
    )
    response_format: Optional[str] = Field(
        default=os.getenv("MODEL_RESPONSE_FORMAT"),
        description="Response format (json, text, etc.)"
    )
    
    # Streaming configuration
    stream: bool = Field(
        default=os.getenv("MODEL_STREAM", "true").lower() == "true",
        description="Enable streaming responses for real-time output"
    )
    stream_config: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "enabled": True,
            "chunk_delay": 0.01,
            "show_thinking": True,
            "buffer_size": 1024
        },
        description="Advanced streaming configuration options"
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
            if len(v) < 10:  # Basic length check
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
    url: str = Field(
        default=os.getenv("DB_URL", "sqlite:///./data/qa_intelligence.db"),
        description="Complete database URL"
    )
    
    # Individual connection components (used if url not provided)
    host: Optional[str] = Field(
        default=os.getenv("DB_HOST"),
        description="Database host"
    )
    port: Optional[int] = Field(
        default=int(os.getenv("DB_PORT", "5432")) if os.getenv("DB_PORT") else None,
        description="Database port"
    )
    name: Optional[str] = Field(
        default=os.getenv("DB_NAME"),
        description="Database name"
    )
    user: Optional[str] = Field(
        default=os.getenv("DB_USER"),
        description="Database username"
    )
    password: Optional[str] = Field(
        default=os.getenv("DB_PASSWORD"),
        description="Database password"
    )
    
    # Connection pool settings
    pool_size: int = Field(
        default=int(os.getenv("DB_POOL_SIZE", "20")),
        ge=1,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=int(os.getenv("DB_MAX_OVERFLOW", "30")),
        ge=0,
        description="Maximum pool overflow connections"
    )
    pool_timeout: int = Field(
        default=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        ge=1,
        description="Pool connection timeout in seconds"
    )
    
    # Additional database settings
    echo: bool = Field(
        default=os.getenv("DB_ECHO", "false").lower() == "true",
        description="Enable SQL query logging"
    )
    enable_migrations: bool = Field(
        default=os.getenv("DB_ENABLE_MIGRATIONS", "true").lower() == "true",
        description="Enable automatic database migrations"
    )
    backup_enabled: bool = Field(
        default=os.getenv("DB_BACKUP_ENABLED", "false").lower() == "true",
        description="Enable automatic database backups"
    )
    backup_interval: int = Field(
        default=int(os.getenv("DB_BACKUP_INTERVAL", "24")),
        ge=1,
        description="Backup interval in hours"
    )

    @field_validator('url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        
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

    @model_validator(mode='after')
    def ensure_database_directory(self):
        """Ensure database directory exists for SQLite databases."""
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
        default=os.getenv("TOOLS_ENABLED", "true").lower() == "true",
        description="Whether tools are enabled globally"
    )
    
    # Tool collection
    tools: List[ToolConfig] = Field(
        default_factory=lambda: [
            ToolConfig(name="web_search", enabled=True, timeout=30),
            ToolConfig(name="python_execution", enabled=True, timeout=60),
            ToolConfig(name="file_operations", enabled=False, timeout=15),
            ToolConfig(name="calculator", enabled=True, timeout=5)
        ],
        description="List of available tools with their configurations"
    )
    
    # Execution settings
    default_timeout: int = Field(
        default=int(os.getenv("TOOLS_TIMEOUT", "30")),
        gt=0,
        description="Default timeout for tool execution in seconds"
    )
    max_concurrent_tools: int = Field(
        default=int(os.getenv("TOOLS_MAX_CONCURRENT", "5")),
        gt=0,
        description="Maximum number of tools that can run concurrently"
    )
    
    # Safety and security
    safety_mode: bool = Field(
        default=os.getenv("TOOLS_SAFETY_MODE", "true").lower() == "true",
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
