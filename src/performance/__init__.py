"""
Performance Module - Independent QA Testing Engine

A comprehensive performance testing module that provides:
- Test execution and monitoring
- Configuration management  
- Database integration
- Real-time monitoring
- Report generation

This module is independent of the QA agent and can be used standalone.

Architecture:
- Phase 3: Modular Engine (engine/)
- Phase 4: SOLID Services (services/)  
- Phase 5: Utilities & Parsers (utils/)
- Phase 6: Manager/Facade Pattern (manager.py)
"""

# Main Manager/Facade (Phase 6)
from .manager import PerformanceManager, PerformanceManagerConfig, create_performance_manager

# Utils exports (Phase 5)
from .utils import (
    PerformanceCommandParser, 
    PerformanceParameterValidator, 
    PerformanceSLAValidator,
    create_parser,
    create_parameter_validator,
    create_sla_validator
)

__version__ = "3.0.0"
__author__ = "QA Intelligence Team"

# Public API - SOLID Architecture with Manager/Facade Pattern
__all__ = [
    # Main Interface (Phase 6 - Manager/Facade)
    "PerformanceManager",
    "PerformanceManagerConfig", 
    "create_performance_manager",
    
    # Utilities (Phase 5 - Extracted parsers and validators)
    "PerformanceCommandParser",
    "PerformanceParameterValidator",
    "PerformanceSLAValidator",
    "create_parser",
    "create_parameter_validator", 
    "create_sla_validator"
]
