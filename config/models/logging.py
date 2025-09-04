"""
Logging configuration models for QA Intelligence

This module provides comprehensive logging configuration for the QA Intelligence
system with support for multiple output formats, file rotation, and structured logging.

The LoggingConfig model supports:
- Multiple log levels with validation
- File and console logging with separate configurations
- Log rotation with size limits and backup management
- Structured JSON logging for production environments
- Custom log formatting with rich text support
- Performance logging and audit trails

Environment Variables:
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_FILE: Main log file path
    LOG_MAX_SIZE: Maximum log file size (e.g., "10 MB", "50 KB")
    LOG_BACKUP_COUNT: Number of backup files to retain
    LOG_ENABLE_FILE: Enable/disable file logging (true/false)
    LOG_ENABLE_CONSOLE: Enable/disable console logging (true/false)
    LOG_ENABLE_JSON: Enable/disable JSON structured logging (true/false)
    LOG_FORMAT: Custom log format string

Example:
    # Basic usage
    logging_config = LoggingConfig()
    
    # Production setup with JSON logging
    logging_config = LoggingConfig(
        level="INFO",
        enable_json_logs=True,
        max_file_size="50 MB",
        backup_count=10
    )
"""

from __future__ import annotations

import os
import re
from typing import Optional, Dict, Any, Literal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()


class LogLevel:
    """
    Standard logging levels with descriptions.
    
    Provides both the level names and their intended usage patterns.
    """
    TRACE = "TRACE"      # Very detailed debugging information
    DEBUG = "DEBUG"      # Detailed debugging information
    INFO = "INFO"        # General information messages
    SUCCESS = "SUCCESS"  # Success operation messages
    WARNING = "WARNING"  # Warning messages
    ERROR = "ERROR"      # Error messages
    CRITICAL = "CRITICAL" # Critical error messages
    
    @classmethod
    def all_levels(cls) -> set[str]:
        """Get all valid log levels."""
        return {cls.TRACE, cls.DEBUG, cls.INFO, cls.SUCCESS, 
                cls.WARNING, cls.ERROR, cls.CRITICAL}


class LoggingConfig(BaseModel):
    """
    Comprehensive logging configuration for QA Intelligence.
    
    This model provides full control over the logging system including:
    - Log levels and formatting
    - File and console output configuration
    - Log rotation and backup management
    - Structured logging support
    - Performance and audit logging
    
    Environment Variables:
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        LOG_FILE: Main log file path
        LOG_MAX_SIZE: Maximum log file size (e.g., "10 MB", "50 KB")
        LOG_BACKUP_COUNT: Number of backup files to retain
        LOG_ENABLE_FILE: Enable/disable file logging (true/false)
        LOG_ENABLE_CONSOLE: Enable/disable console logging (true/false)
        LOG_ENABLE_JSON: Enable/disable JSON structured logging (true/false)
        LOG_FORMAT: Custom log format string
        
    Example:
        # Environment variables
        export LOG_LEVEL=INFO
        export LOG_FILE=logs/qa_intelligence.log
        export LOG_MAX_SIZE="25 MB"
        export LOG_BACKUP_COUNT=7
        
        # Programmatic usage
        config = LoggingConfig(
            level="DEBUG",
            enable_file_logging=True,
            enable_json_logs=True
        )
    """
    
    # ========================================================================
    # Core Logging Settings
    # ========================================================================
    
    level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)"
    )
    
    # ========================================================================
    # Log Format Configuration
    # ========================================================================
    
    format: str = Field(
        default=os.getenv(
            "LOG_FORMAT",
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        description="Log message format string (supports rich text markup)"
    )
    
    json_format: Dict[str, str] = Field(
        default_factory=lambda: {
            "timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}",
            "level": "{level}",
            "logger": "{name}",
            "function": "{function}",
            "line": "{line}",
            "message": "{message}",
            "process": "{process}",
            "thread": "{thread}"
        },
        description="JSON log format field mapping"
    )
    
    # ========================================================================
    # File Logging Configuration
    # ========================================================================
    
    enable_file_logging: bool = Field(
        default=os.getenv("LOG_ENABLE_FILE", "true").lower() == "true",
        description="Enable logging to files"
    )
    
    log_file: str = Field(
        default=os.getenv("LOG_FILE", "logs/qa_intelligence.log"),
        description="Main log file path"
    )
    
    max_file_size: str = Field(
        default=os.getenv("LOG_MAX_SIZE", "10 MB"),
        description="Maximum log file size (e.g., '10 MB', '500 KB', '1 GB')"
    )
    
    backup_count: int = Field(
        default=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        ge=0,
        le=100,
        description="Number of backup log files to keep (0-100)"
    )
    
    # ========================================================================
    # Console Logging Configuration
    # ========================================================================
    
    enable_console_logging: bool = Field(
        default=os.getenv("LOG_ENABLE_CONSOLE", "true").lower() == "true",
        description="Enable console logging output"
    )
    
    console_level: Optional[str] = Field(
        default=os.getenv("LOG_CONSOLE_LEVEL"),
        description="Separate log level for console output (optional)"
    )
    
    # ========================================================================
    # Structured Logging Configuration
    # ========================================================================
    
    enable_json_logs: bool = Field(
        default=os.getenv("LOG_ENABLE_JSON", "false").lower() == "true",
        description="Enable structured JSON logging for production"
    )
    
    json_log_file: Optional[str] = Field(
        default=os.getenv("LOG_JSON_FILE"),
        description="Separate file for JSON logs (optional)"
    )
    
    # ========================================================================
    # Specialized Logging Features
    # ========================================================================
    
    enable_performance_logging: bool = Field(
        default=os.getenv("LOG_ENABLE_PERFORMANCE", "false").lower() == "true",
        description="Enable performance timing logs"
    )
    
    performance_log_file: str = Field(
        default=os.getenv("LOG_PERFORMANCE_FILE", "logs/performance.log"),
        description="Performance log file path"
    )
    
    enable_audit_logging: bool = Field(
        default=os.getenv("LOG_ENABLE_AUDIT", "false").lower() == "true",
        description="Enable audit trail logging"
    )
    
    audit_log_file: str = Field(
        default=os.getenv("LOG_AUDIT_FILE", "logs/audit.log"),
        description="Audit log file path"
    )
    
    # ========================================================================
    # Error and Exception Handling
    # ========================================================================
    
    error_log_file: str = Field(
        default=os.getenv("LOG_ERROR_FILE", "logs/errors.log"),
        description="Dedicated error log file path"
    )
    
    capture_exceptions: bool = Field(
        default=os.getenv("LOG_CAPTURE_EXCEPTIONS", "true").lower() == "true",
        description="Automatically capture and log unhandled exceptions"
    )
    
    include_traceback: bool = Field(
        default=os.getenv("LOG_INCLUDE_TRACEBACK", "true").lower() == "true",
        description="Include full traceback in error logs"
    )

    # ========================================================================
    # Validation Methods
    # ========================================================================

    @field_validator('level', 'console_level')
    @classmethod
    def validate_log_level(cls, v: Optional[str]) -> Optional[str]:
        """Validate that log level is supported."""
        if v is None:
            return v
            
        v_upper = v.upper()
        if v_upper not in LogLevel.all_levels():
            valid_levels = ", ".join(sorted(LogLevel.all_levels()))
            raise ValueError(
                f"Invalid log level: {v}. "
                f"Must be one of: {valid_levels}"
            )
        return v_upper

    @field_validator('max_file_size')
    @classmethod
    def validate_file_size(cls, v: str) -> str:
        """Validate file size format."""
        # Pattern to match sizes like "10 MB", "500 KB", "1 GB"
        pattern = r'^\d+(\.\d+)?\s*(B|KB|MB|GB)$'
        if not re.match(pattern, v.upper()):
            raise ValueError(
                f"Invalid file size format: {v}. "
                "Use format like '10 MB', '500 KB', '1 GB'"
            )
        return v

    @field_validator('log_file', 'json_log_file', 'performance_log_file', 
                    'audit_log_file', 'error_log_file')
    @classmethod
    def validate_log_file_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate log file paths and ensure directories exist."""
        if v is None:
            return v
            
        log_path = Path(v)
        
        # Ensure parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate path is writable (create empty file if doesn't exist)
        try:
            log_path.touch(exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot write to log file {v}: {e}")
        
        return str(log_path)

    @model_validator(mode='after')
    def validate_logging_configuration(self):
        """Validate the overall logging configuration."""
        # At least one output method must be enabled
        if not self.enable_file_logging and not self.enable_console_logging:
            raise ValueError(
                "At least one logging output (file or console) must be enabled"
            )
        
        # If JSON logging is enabled but no separate file is specified,
        # use the main log file location with .json extension
        if self.enable_json_logs and not self.json_log_file:
            log_path = Path(self.log_file)
            self.json_log_file = str(log_path.with_suffix('.json'))
        
        # Validate console level is not more restrictive than main level
        if self.console_level:
            level_order = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
            if (level_order.index(self.console_level) < 
                level_order.index(self.level)):
                import warnings
                warnings.warn(
                    f"Console log level ({self.console_level}) is less restrictive "
                    f"than main level ({self.level}). This may cause confusion.",
                    UserWarning
                )
        
        return self

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_loguru_config(self) -> Dict[str, Any]:
        """
        Get configuration dictionary for Loguru logger setup.
        
        Returns:
            Dictionary with Loguru-compatible configuration
        """
        config = {
            "handlers": []
        }
        
        # Console handler
        if self.enable_console_logging:
            console_handler = {
                "sink": "sys.stdout",
                "level": self.console_level or self.level,
                "format": self.format,
                "colorize": True,
                "backtrace": self.include_traceback,
                "diagnose": True
            }
            config["handlers"].append(console_handler)
        
        # File handler
        if self.enable_file_logging:
            file_handler = {
                "sink": self.log_file,
                "level": self.level,
                "format": self.format,
                "rotation": self.max_file_size,
                "retention": self.backup_count,
                "compression": "zip",
                "backtrace": self.include_traceback,
                "diagnose": True
            }
            config["handlers"].append(file_handler)
        
        # JSON handler
        if self.enable_json_logs and self.json_log_file:
            json_handler = {
                "sink": self.json_log_file,
                "level": self.level,
                "format": self.json_format,
                "serialize": True,
                "rotation": self.max_file_size,
                "retention": self.backup_count,
                "compression": "zip"
            }
            config["handlers"].append(json_handler)
        
        # Error handler
        error_handler = {
            "sink": self.error_log_file,
            "level": "ERROR",
            "format": self.format,
            "rotation": self.max_file_size,
            "retention": self.backup_count,
            "filter": lambda record: record["level"].no >= 40  # ERROR and above
        }
        config["handlers"].append(error_handler)
        
        return config

    def get_file_size_bytes(self) -> int:
        """
        Convert file size string to bytes.
        
        Returns:
            File size in bytes
        """
        size_str = self.max_file_size.upper()
        
        # Extract number and unit
        import re
        match = re.match(r'(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)', size_str)
        if not match:
            return 10 * 1024 * 1024  # Default 10MB
        
        size_num = float(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3
        }
        
        return int(size_num * multipliers[unit])

    def get_log_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the logging configuration.
        
        Returns:
            Dictionary with logging configuration summary
        """
        return {
            "level": self.level,
            "file_logging": self.enable_file_logging,
            "console_logging": self.enable_console_logging,
            "json_logging": self.enable_json_logs,
            "performance_logging": self.enable_performance_logging,
            "audit_logging": self.enable_audit_logging,
            "log_file": self.log_file if self.enable_file_logging else None,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count,
            "capture_exceptions": self.capture_exceptions
        }

    model_config = ConfigDict(
        str_to_lower=True,
        extra='allow',
        validate_assignment=True
    )
