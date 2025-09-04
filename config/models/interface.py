"""
Interface and application environment configuration models
Contains InterfaceConfig and AppEnvironmentConfig
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class InterfaceConfig(BaseModel):
    """Configuration for user interfaces"""
    
    terminal: Dict[str, Any] = Field(
        default_factory=lambda: {
            "show_tool_calls": True,
            "enable_markdown": True,
            "max_history": 100,
            "color_scheme": "dark",
            "streaming": {
                "enabled": True,
                "show_cursor": True,
                "cursor_style": "⚡",
                "typing_delay": 0.02,
                "chunk_buffer_size": 1024,
                "show_thinking_indicator": True
            }
        },
        description="Terminal interface settings with streaming support"
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

    model_config = ConfigDict(extra='allow')


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

    model_config = ConfigDict(extra='allow')
