"""
Pydantic models for configuration validation
All configuration data structures using Pydantic v2 for type safety and validation
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Configuration for AI model settings"""
    
    provider: str = Field(
        default="openai",
        description="AI model provider (openai, azure, deepseek, etc.)"
    )
    id: str = Field(
        default="gpt-3.5-turbo",
        description="Model identifier/name"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the model provider"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Model temperature for response randomness"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens in model response"
    )
    timeout: Optional[int] = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Custom base URL for API endpoints"
    )
    organization: Optional[str] = Field(
        default=None,
        description="Organization ID for API requests"
    )
    project: Optional[str] = Field(
        default=None,
        description="Project ID for API requests"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Seed for deterministic responses"
    )
    response_format: Optional[str] = Field(
        default=None,
        description="Response format (json, text, etc.)"
    )

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        supported_providers = {'openai', 'azure', 'deepseek'}
        if v.lower() not in supported_providers:
            raise ValueError(f"Unsupported provider: {v}. Supported: {supported_providers}")
        return v.lower()

    @field_validator('api_key')
    @classmethod 
    def validate_api_key(cls, v, info):
        if v is None:
            # Try to get from environment based on provider
            data = info.data if hasattr(info, 'data') else {}
            provider = data.get('provider', 'openai')
            env_key = f"{provider.upper()}_API_KEY"
            v = os.getenv(env_key)
            
            if v is None:
                raise ValueError(f"API key not found. Set {env_key} environment variable or provide api_key")
        
        return v

    model_config = ConfigDict(case_sensitive=False)


class DatabaseConfig(BaseModel):
    """Configuration for database connections"""
    
    url: str = Field(
        default="sqlite:///./data/qa_intelligence.db",
        description="Main database URL"
    )
    conversations_path: str = Field(
        default="data/qa_conversations.db",
        description="Path to conversations database"
    )
    knowledge_path: str = Field(
        default="data/qa_knowledge.db", 
        description="Path to knowledge base database"
    )
    rag_path: str = Field(
        default="data/qa_intelligence_rag.db",
        description="Path to RAG database"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging"
    )
    pool_size: int = Field(
        default=20,
        gt=0,
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=30,
        gt=0,
        description="Maximum database connection overflow"
    )

    @field_validator('url', 'conversations_path', 'knowledge_path', 'rag_path')
    @classmethod
    def ensure_database_directories(cls, v):
        if v.startswith('sqlite:///'):
            db_path = v.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        elif '/' in v and not v.startswith('postgresql://') and not v.startswith('mysql://'):
            # Assume it's a file path
            Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v

    model_config = ConfigDict(case_sensitive=False)


class ToolConfig(BaseModel):
    """Configuration for a single tool"""
    
    name: str = Field(description="Tool name")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration")
    timeout: Optional[int] = Field(default=30, gt=0, description="Tool execution timeout")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")


class ToolsConfig(BaseModel):
    """Configuration for tool management"""
    
    enabled: bool = Field(
        default=True,
        description="Whether tools are enabled globally"
    )
    tools: List[ToolConfig] = Field(
        default_factory=lambda: [
            ToolConfig(name="web_search", enabled=True),
            ToolConfig(name="python_execution", enabled=True),
            ToolConfig(name="file_operations", enabled=False)
        ],
        description="List of available tools"
    )
    default_timeout: int = Field(
        default=30,
        gt=0,
        description="Default timeout for tool execution"
    )
    max_concurrent_tools: int = Field(
        default=5,
        gt=0,
        description="Maximum number of tools that can run concurrently"
    )
    safety_mode: bool = Field(
        default=True,
        description="Enable safety restrictions for tools"
    )

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """Get configuration for a specific tool"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled"""
        if not self.enabled:
            return False
        
        tool_config = self.get_tool_config(tool_name)
        return tool_config.enabled if tool_config else False

    model_config = ConfigDict(case_sensitive=False)


class InterfaceConfig(BaseModel):
    """Configuration for user interfaces"""
    
    terminal: Dict[str, Any] = Field(
        default_factory=lambda: {
            "show_tool_calls": True,
            "enable_markdown": True,
            "max_history": 100,
            "color_scheme": "dark"
        },
        description="Terminal interface settings"
    )
    playground: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "port": 7777,
            "host": "localhost",
            "debug": False
        },
        description="Web playground settings"
    )
    api: Dict[str, Any] = Field(
        default_factory=lambda: {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False,
            "cors_enabled": True
        },
        description="API server settings"
    )

    model_config = ConfigDict(case_sensitive=False)


class AppEnvironmentConfig(BaseModel):
    """Configuration for application environment settings"""
    
    data_directory: str = Field(
        default="data",
        description="Directory for data files"
    )
    logs_directory: str = Field(
        default="logs",
        description="Directory for log files"
    )
    cache_directory: str = Field(
        default="cache",
        description="Directory for cache files"
    )
    temp_directory: str = Field(
        default="temp",
        description="Directory for temporary files"
    )
    app_environment: str = Field(
        default="development",
        description="Environment type (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    max_memory_usage: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum memory usage in MB"
    )

    @field_validator('app_environment')
    @classmethod
    def validate_environment(cls, v):
        valid_envs = {'development', 'staging', 'production'}
        if v not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v

    @model_validator(mode='after')
    def ensure_directories(self):
        """Ensure all directories exist"""
        for attr in ['data_directory', 'logs_directory', 'cache_directory', 'temp_directory']:
            if hasattr(self, attr):
                Path(getattr(self, attr)).mkdir(parents=True, exist_ok=True)
        return self

    model_config = ConfigDict(case_sensitive=False)


class LoggingConfig(BaseModel):
    """Configuration for logging system"""
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log message format"
    )
    enable_file_logging: bool = Field(
        default=True,
        description="Enable logging to files"
    )
    log_file: str = Field(
        default="logs/qa_intelligence.log",
        description="Main log file path"
    )
    max_file_size: str = Field(
        default="10 MB",
        description="Maximum log file size"
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of backup log files to keep"
    )
    enable_json_logs: bool = Field(
        default=False,
        description="Enable structured JSON logging"
    )
    enable_console_logging: bool = Field(
        default=True,
        description="Enable console logging"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = {'TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    model_config = ConfigDict(case_sensitive=False)
