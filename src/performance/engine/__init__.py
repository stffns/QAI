"""
Performance Engine Module
Módulo independiente para ejecutar pruebas de rendimiento con Gatling

Componentes:
- models: Estructuras de datos (ExecutionStatus, ProgressInfo, etc.)
- monitoring: Monitor de salida en tiempo real con callbacks
- batch_engine: Engine principal para ejecuciones batch

Uso:
    from src.performance.engine import PerformanceEngineV2, ExecutionStatus
    
    engine = PerformanceEngineV2()
    result = engine.submit_simulation(config_json)
    status = engine.get_execution_status(result.execution_id)
"""

from typing import Optional

# Interfaces principales del engine
from .batch_engine import PerformanceEngineV2
from .models import (
    ExecutionStatus,
    ProgressInfo,
    BatchExecutionResult,
    ExecutionStatusResponse,
    PerformanceEngineException
)
from .monitoring import GatlingOutputMonitor

# Interface unificada del engine
__all__ = [
    "PerformanceEngineV2",
    "ExecutionStatus", 
    "ProgressInfo",
    "BatchExecutionResult",
    "ExecutionStatusResponse",
    "PerformanceEngineException",
    "GatlingOutputMonitor"
]

# Función de conveniencia para crear engine
def create_engine(gatling_path: Optional[str] = None) -> PerformanceEngineV2:
    """
    Factory para crear instancia del engine
    """
    return PerformanceEngineV2(gatling_path)
