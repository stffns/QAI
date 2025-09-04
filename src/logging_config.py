#!/usr/bin/env python3
"""
Centralized logging configuration using Loguru
Provides consistent logging setup across the entire QA Intelligence system
"""

import sys
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# Configuration constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

DETAILED_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<blue>{extra[component]}</blue> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{extra[component]} | "
    "{message}"
)


class LoggingConfig:
    """
    Centralized logging configuration manager

    Provides consistent logging setup with:
    - Multiple output handlers (console, file, debug)
    - Contextual component tagging
    - Performance monitoring
    - Error tracking
    - Development vs production modes
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Track if already configured
        self._configured = False

    def setup_logging(
        self,
        level: str = DEFAULT_LOG_LEVEL,
        enable_file_logging: bool = True,
        enable_debug_logging: bool = False,
        component: str = "QAI",
        development_mode: bool = True,
    ) -> None:
        """
        Configure Loguru with comprehensive logging strategy

        Args:
            level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_file_logging: Enable logging to files
            enable_debug_logging: Enable debug file with verbose output
            component: Main component name for context
            development_mode: Enable development features
        """

        if self._configured:
            logger.warning("Logging already configured, skipping setup")
            return

        # Remove default handler
        logger.remove()

        # Bind default context
        logger.configure(extra={"component": component})

        # 1. CONSOLE HANDLER - Always enabled
        console_format = DETAILED_FORMAT if development_mode else DEFAULT_LOG_FORMAT
        logger.add(
            sys.stdout,
            format=console_format,
            level=level,
            colorize=True,
            backtrace=development_mode,
            diagnose=development_mode,
            filter=self._console_filter,
        )

        if enable_file_logging:
            # 2. MAIN LOG FILE - All logs
            logger.add(
                self.logs_dir / "qa_intelligence.log",
                format=FILE_FORMAT,
                level="DEBUG",
                rotation="100 MB",
                retention="30 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                enqueue=True,  # Thread-safe
            )

            # 3. ERROR LOG FILE - Errors and above
            logger.add(
                self.logs_dir / "errors.log",
                format=FILE_FORMAT,
                level="ERROR",
                rotation="50 MB",
                retention="90 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                enqueue=True,
            )

        if enable_debug_logging:
            # 4. DEBUG LOG FILE - Very verbose
            logger.add(
                self.logs_dir / "debug.log",
                format=FILE_FORMAT,
                level="TRACE",
                rotation="200 MB",
                retention="7 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                enqueue=True,
            )

        # 5. PERFORMANCE LOG - For timing and metrics
        logger.add(
            self.logs_dir / "performance.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {extra[component]} | {message}",
            level="INFO",
            rotation="50 MB",
            retention="14 days",
            filter=lambda record: record["extra"].get("log_type") == "performance",
        )

        self._configured = True
        logger.info(
            "Logging system initialized",
            component=component,
            level=level,
            file_logging=enable_file_logging,
            debug_logging=enable_debug_logging,
            development_mode=development_mode,
        )

    def _console_filter(self, record) -> bool:
        """Filter for console output to reduce noise"""
        # Skip some verbose debug messages in production
        if record["level"].name == "DEBUG":
            # Only show debug for specific components
            component = record["extra"].get("component", "")
            return component in ["QAAgent", "Teams", "Memory"]
        return True

    def get_component_logger(self, component: str) -> Any:
        """
        Get a logger bound to a specific component

        Args:
            component: Component name for context

        Returns:
            Logger instance with component context
        """
        return logger.bind(component=component)

    def get_performance_logger(self) -> Any:
        """Get logger for performance metrics"""
        return logger.bind(component="PERF", log_type="performance")

    def get_error_logger(self) -> Any:
        """Get logger specifically for error tracking"""
        return logger.bind(component="ERROR", log_type="error")


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def setup_qa_logging(
    level: str = "INFO",
    enable_file_logging: bool = True,
    enable_debug_logging: bool = False,
    component: str = "QAI",
    development_mode: bool = True,
    base_dir: Optional[Path] = None,
) -> LoggingConfig:
    """
    Setup logging for QA Intelligence system

    Args:
        level: Log level
        enable_file_logging: Enable file output
        enable_debug_logging: Enable debug files
        component: Main component name
        development_mode: Development features
        base_dir: Base directory for logs

    Returns:
        LoggingConfig instance
    """
    global _logging_config

    if _logging_config is None:
        _logging_config = LoggingConfig(base_dir)

    _logging_config.setup_logging(
        level=level,
        enable_file_logging=enable_file_logging,
        enable_debug_logging=enable_debug_logging,
        component=component,
        development_mode=development_mode,
    )

    return _logging_config


def get_logger(component: str = "QAI") -> Any:
    """
    Get a logger for a specific component

    Args:
        component: Component name

    Returns:
        Logger instance
    """
    if _logging_config is None:
        # Auto-setup with defaults if not configured
        setup_qa_logging()

    return _logging_config.get_component_logger(component)


def get_performance_logger() -> Any:
    """Get performance logger"""
    if _logging_config is None:
        setup_qa_logging()
    return _logging_config.get_performance_logger()


def get_error_logger() -> Any:
    """Get error logger"""
    if _logging_config is None:
        setup_qa_logging()
    return _logging_config.get_error_logger()


# Context managers for logging
class LogExecutionTime:
    """Context manager to log execution time"""

    def __init__(self, operation: str, component: str = "QAI"):
        self.operation = operation
        self.logger = get_performance_logger()
        self.component = component
        self.start_time: float | None = None

    def __enter__(self):
        import time

        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}", component=self.component)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time

        if self.start_time is not None:
            duration = time.time() - self.start_time
        else:
            duration = 0.0

        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                component=self.component,
                operation=self.operation,
                duration=duration,
                status="success",
            )
        else:
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                component=self.component,
                operation=self.operation,
                duration=duration,
                status="error",
                error=str(exc_val),
            )


class LogStep:
    """Context manager for logging operation steps"""

    def __init__(self, step: str, component: str = "QAI"):
        self.step = step
        self.logger = get_logger(component)
        self.component = component

    def __enter__(self):
        self.logger.debug(f"→ {self.step}", component=self.component)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.debug(f"✓ {self.step}", component=self.component)
        else:
            self.logger.error(
                f"✗ {self.step}: {exc_val}",
                component=self.component,
                error=str(exc_val),
            )


# Utility functions
def log_agent_event(event: str, details: dict[str, Any], component: str = "Agent"):
    """Log agent-specific events with structured data"""
    log = get_logger(component)
    log.info(f"Agent Event: {event}", component=component, event=event, **details)


def log_memory_operation(operation: str, details: dict[str, Any]):
    """Log memory operations"""
    log = get_logger("Memory")
    log.debug(
        f"Memory: {operation}", component="Memory", operation=operation, **details
    )


def log_model_interaction(model_type: str, tokens: int, response_time: float):
    """Log model interactions with metrics"""
    perf_log = get_performance_logger()
    perf_log.info(
        f"Model interaction completed",
        component="Model",
        model_type=model_type,
        tokens=tokens,
        response_time=response_time,
        tokens_per_second=tokens / response_time if response_time > 0 else 0,
    )


def log_tool_usage(tool_name: str, success: bool, execution_time: float):
    """Log tool usage with metrics"""
    log = get_logger("Tools")
    status = "success" if success else "failed"
    log.info(
        f"Tool {tool_name} {status}",
        component="Tools",
        tool=tool_name,
        success=success,
        execution_time=execution_time,
    )


if __name__ == "__main__":
    # Demo/test the logging system
    setup_qa_logging(level="DEBUG", development_mode=True)

    # Test different loggers
    main_log = get_logger("QAAgent")
    perf_log = get_performance_logger()
    error_log = get_error_logger()

    main_log.info("Testing QA Intelligence logging system")
    main_log.debug("Debug message with component context")
    main_log.warning("Warning message")

    # Test context managers
    with LogExecutionTime("test operation", "TEST"):
        import time

        time.sleep(0.1)

    with LogStep("test step", "TEST"):
        main_log.info("Inside step context")

    # Test utility functions
    log_agent_event("initialization", {"model": "gpt-4", "tools": 3})
    log_memory_operation("store", {"conversations": 5, "tokens": 1500})
    log_model_interaction("gpt-4", 150, 2.5)
    log_tool_usage("calculator", True, 0.05)

    main_log.success("Logging system test completed")
