"""
Error Recovery System - Enhanced error handling with recovery patterns
Following Agno best practices for resilient agent operations
"""

import functools
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

# Configure logging
try:
    from ..logging_config import LogStep, get_logger
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from logging_config import LogStep, get_logger

logger = get_logger("ErrorRecovery")

T = TypeVar("T")


class RecoveryStrategy(Enum):
    """Recovery strategies for different types of errors"""

    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery"""

    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    circuit_timeout: float = 30.0
    fallback_fn: Optional[Callable] = None
    essential: bool = False


@dataclass
class ErrorInfo:
    """Information about an error occurrence"""

    error: Exception
    error_type: str
    component: str
    timestamp: float
    retry_count: int = 0
    recovery_attempted: bool = False


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, timeout: float = 30.0, failure_threshold: int = 5):
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker moving to half-open state")
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)

            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful call")

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise e


class ErrorRecoveryManager:
    """
    Manages error recovery strategies for agent components

    Provides resilient operation patterns including:
    - Retry with exponential backoff
    - Circuit breaker pattern
    - Graceful degradation
    - Fallback mechanisms
    """

    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_configs: Dict[str, RecoveryConfig] = {}

    def register_component(
        self, component_name: str, recovery_config: RecoveryConfig
    ) -> None:
        """
        Register a component with recovery configuration

        Args:
            component_name: Name of the component
            recovery_config: Recovery configuration
        """
        self.recovery_configs[component_name] = recovery_config

        if recovery_config.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            self.circuit_breakers[component_name] = CircuitBreaker(
                timeout=recovery_config.circuit_timeout
            )

        logger.debug(
            f"Registered component {component_name} with {recovery_config.strategy.value} recovery"
        )

    def execute_with_recovery(
        self, component_name: str, operation: Callable[..., T], *args, **kwargs
    ) -> T:
        """
        Execute operation with configured recovery strategy

        Args:
            component_name: Name of the component
            operation: Operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            Exception: If all recovery attempts fail
        """
        config = self.recovery_configs.get(component_name)
        if not config:
            # No recovery configured, execute directly
            return operation(*args, **kwargs)

        if config.strategy == RecoveryStrategy.RETRY:
            return self._execute_with_retry(
                component_name, operation, config, *args, **kwargs
            )
        elif config.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            return self._execute_with_circuit_breaker(
                component_name, operation, config, *args, **kwargs
            )
        elif config.strategy == RecoveryStrategy.FALLBACK:
            return self._execute_with_fallback(
                component_name, operation, config, *args, **kwargs
            )
        elif config.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._execute_with_degradation(
                component_name, operation, config, *args, **kwargs
            )
        elif config.strategy == RecoveryStrategy.FAIL_FAST:
            return self._execute_fail_fast(
                component_name, operation, config, *args, **kwargs
            )
        else:
            return operation(*args, **kwargs)

    def _execute_with_retry(
        self,
        component_name: str,
        operation: Callable[..., T],
        config: RecoveryConfig,
        *args,
        **kwargs,
    ) -> T:
        """Execute with retry and exponential backoff"""
        last_error: Optional[Exception] = None
        delay = config.retry_delay

        for attempt in range(config.max_retries + 1):
            try:
                result = operation(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"Operation {component_name} succeeded on attempt {attempt + 1}"
                    )

                return result

            except Exception as e:
                last_error = e
                self._record_error(component_name, e, attempt)

                if attempt < config.max_retries:
                    logger.warning(
                        f"Operation {component_name} failed on attempt {attempt + 1}, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    delay *= config.backoff_multiplier
                else:
                    logger.error(
                        f"Operation {component_name} failed after {config.max_retries + 1} attempts"
                    )

        if last_error:
            raise last_error
        else:
            raise Exception(f"Operation {component_name} failed with unknown error")

    def _execute_with_circuit_breaker(
        self,
        component_name: str,
        operation: Callable[..., T],
        config: RecoveryConfig,
        *args,
        **kwargs,
    ) -> T:
        """Execute with circuit breaker protection"""
        circuit_breaker = self.circuit_breakers[component_name]

        try:
            return circuit_breaker.call(operation, *args, **kwargs)
        except Exception as e:
            self._record_error(component_name, e, 0)
            raise

    def _execute_with_fallback(
        self,
        component_name: str,
        operation: Callable[..., T],
        config: RecoveryConfig,
        *args,
        **kwargs,
    ) -> T:
        """Execute with fallback mechanism"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            self._record_error(component_name, e, 0)

            if config.fallback_fn:
                logger.warning(
                    f"Operation {component_name} failed, using fallback: {e}"
                )
                try:
                    return config.fallback_fn(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback for {component_name} also failed: {fallback_error}"
                    )
                    raise e
            else:
                raise

    def _execute_with_degradation(
        self,
        component_name: str,
        operation: Callable[..., T],
        config: RecoveryConfig,
        *args,
        **kwargs,
    ) -> T:
        """Execute with graceful degradation"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            self._record_error(component_name, e, 0)

            if config.essential:
                logger.error(f"Essential component {component_name} failed: {e}")
                raise
            else:
                logger.warning(
                    f"Non-essential component {component_name} failed, continuing: {e}"
                )
                # For non-essential components, we need to raise since we can't return None for type T
                raise

    def _execute_fail_fast(
        self,
        component_name: str,
        operation: Callable[..., T],
        config: RecoveryConfig,
        *args,
        **kwargs,
    ) -> T:
        """Execute with fail-fast strategy"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            self._record_error(component_name, e, 0)
            logger.error(f"Fail-fast component {component_name} failed: {e}")
            raise

    def _record_error(self, component: str, error: Exception, retry_count: int) -> None:
        """Record error information for analysis"""
        error_info = ErrorInfo(
            error=error,
            error_type=type(error).__name__,
            component=component,
            timestamp=time.time(),
            retry_count=retry_count,
        )
        self.error_history.append(error_info)

        # Keep only recent errors to prevent memory growth
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        if not self.error_history:
            return {"total_errors": 0}

        recent_errors = [
            e for e in self.error_history if time.time() - e.timestamp < 3600
        ]  # Last hour

        error_by_component = {}
        error_by_type = {}

        for error in recent_errors:
            error_by_component[error.component] = (
                error_by_component.get(error.component, 0) + 1
            )
            error_by_type[error.error_type] = error_by_type.get(error.error_type, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "errors_by_component": error_by_component,
            "errors_by_type": error_by_type,
            "circuit_breaker_states": {
                name: cb.state for name, cb in self.circuit_breakers.items()
            },
        }


def with_recovery(
    component_name: str,
    recovery_manager: ErrorRecoveryManager,
    recovery_config: Optional[RecoveryConfig] = None,
):
    """
    Decorator for adding error recovery to functions

    Args:
        component_name: Name of the component
        recovery_manager: Error recovery manager instance
        recovery_config: Recovery configuration (optional)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if recovery_config:
            recovery_manager.register_component(component_name, recovery_config)

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return recovery_manager.execute_with_recovery(
                component_name, func, *args, **kwargs
            )

        return wrapper

    return decorator


# Global recovery manager for the application
global_recovery_manager = ErrorRecoveryManager()

# Pre-configured recovery strategies for common components
COMPONENT_RECOVERY_CONFIGS = {
    "model_manager": RecoveryConfig(
        strategy=RecoveryStrategy.RETRY, max_retries=2, retry_delay=1.0, essential=True
    ),
    "tools_manager": RecoveryConfig(
        strategy=RecoveryStrategy.GRACEFUL_DEGRADATION, essential=False
    ),
    "storage_manager": RecoveryConfig(
        strategy=RecoveryStrategy.FALLBACK, essential=False
    ),
    "web_search": RecoveryConfig(
        strategy=RecoveryStrategy.CIRCUIT_BREAKER, circuit_timeout=60.0, essential=False
    ),
    "python_tools": RecoveryConfig(
        strategy=RecoveryStrategy.RETRY, max_retries=1, essential=False
    ),
}

# Register default configurations
for component, config in COMPONENT_RECOVERY_CONFIGS.items():
    global_recovery_manager.register_component(component, config)
