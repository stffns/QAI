"""
Logging configuration models
Contains LoggingConfig for centralized logging configuration
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, ConfigDict


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
