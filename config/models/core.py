"""
Core configuration models for QA Intelligence
Contains ModelConfig, DatabaseConfig, and ToolsConfig with .env support
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import SettingsConfigDict

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()


def _get_env_int(key: str, default: int) -> int:
    """Safely get integer from environment variable with guaranteed default"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_int_optional(key: str, default: Optional[int] = None) -> Optional[int]:
    """Safely get optional integer from environment variable"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(key: str, default: float = 0.0) -> float:
    """Safely get float from environment variable"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class ModelConfig(BaseModel):
    """Configuration for AI model settings with environment variable support"""
    
    provider: str = Field(
        default_factory=lambda: os.getenv("MODEL_PROVIDER", "openai"),
        description="AI model provider (openai, azure, deepseek, etc.)"
    )
    id: str = Field(
        default_factory=lambda: os.getenv("MODEL_ID", os.getenv("AGENT_DEFAULT_MODEL", "gpt-5-mini")),
        description="Model identifier/name"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the model provider (auto-detected from env)"
    )
    temperature: float = Field(
        default_factory=lambda: _get_env_float("MODEL_TEMPERATURE", 0.7),
        ge=0.0,
        le=2.0,
        description="Model temperature for response randomness"
    )
    max_tokens: Optional[int] = Field(
        default_factory=lambda: _get_env_int_optional("MODEL_MAX_TOKENS"),
        description="Maximum tokens in model response"
    )
    timeout: Optional[int] = Field(
        default_factory=lambda: _get_env_int("MODEL_TIMEOUT", 30),
        gt=0,
        description="Request timeout in seconds"
    )
    base_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("MODEL_BASE_URL"),
        description="Custom base URL for API endpoints"
    )
    organization: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_ORGANIZATION"),
        description="Organization ID for API requests"
    )
    project: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_PROJECT"),
        description="Project ID for API requests"
    )
    seed: Optional[int] = Field(
        default_factory=lambda: _get_env_int_optional("MODEL_SEED"),
        description="Seed for deterministic responses"
    )
    response_format: Optional[str] = Field(
        default_factory=lambda: os.getenv("MODEL_RESPONSE_FORMAT"),
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
            
            # Try multiple environment variable patterns
            env_keys = [
                f"{provider.upper()}_API_KEY",
                "OPENAI_API_KEY",  # fallback for openai
                "API_KEY"  # generic fallback
            ]
            
            for env_key in env_keys:
                v = os.getenv(env_key)
                if v:
                    break
            
            # Only raise error if we're in validation mode and no key found
            if v is None and os.getenv('SKIP_API_KEY_VALIDATION') != 'true':
                print(f"⚠️  Warning: API key not found for provider {provider}. Set {env_keys[0]} environment variable.")
                # Don't raise error here, let the Settings class handle it
                pass
        
        return v

    model_config = ConfigDict(extra='allow')


class DatabaseConfig(BaseModel):
    """Configuration for database connections with environment variable support"""
    
    url: str = Field(
        default_factory=lambda: os.getenv("DB_URL", "sqlite:///./data/qa_intelligence.db"),
        description="Main database URL"
    )
    conversations_path: str = Field(
        default_factory=lambda: os.getenv("QA_AGENT_DB_PATH", "data/qa_conversations.db"),
        description="Path to conversations database"
    )
    knowledge_path: str = Field(
        default_factory=lambda: os.getenv("QA_KNOWLEDGE_DB_PATH", "data/qa_knowledge.db"),
        description="Path to knowledge base database"
    )
    rag_path: str = Field(
        default_factory=lambda: os.getenv("QA_RAG_DB_PATH", "data/qa_intelligence_rag.db"),
        description="Path to RAG database"
    )
    echo: bool = Field(
        default_factory=lambda: os.getenv("DB_ECHO", "false").lower() == "true",
        description="Enable SQL query logging"
    )
    pool_size: int = Field(
        default_factory=lambda: _get_env_int("DB_POOL_SIZE", 20),
        gt=0,
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default_factory=lambda: _get_env_int("DB_MAX_OVERFLOW", 30),
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

    model_config = ConfigDict(str_to_lower=True, extra='allow')


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

    model_config = ConfigDict(str_to_lower=True, extra='allow')
