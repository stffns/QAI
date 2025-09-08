"""
Engine Models - Data structures for performance engine

Contains all data classes and enums used by the performance engine:
- Execution status definitions
- Progress tracking models
- Result data structures
- Response models

Extracted from performance_engine_v2_enhanced.py
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class ExecutionStatus(str, Enum):
    """Estado de ejecuciones batch"""
    SUBMITTED = "submitted"      # Enviado al engine
    PREPARING = "preparing"      # Generando archivos
    RUNNING = "running"          # Ejecutando Gatling
    PARSING = "parsing"          # Procesando resultados
    GENERATING_REPORTS = "generating_reports"  # Generando reportes
    COMPLETED = "completed"      # Finalizado exitosamente
    FAILED = "failed"           # Error en ejecución
    CANCELLED = "cancelled"     # Cancelado por usuario


@dataclass
class ProgressInfo:
    """Información de progreso en tiempo real"""
    phase: ExecutionStatus
    percentage: float
    waiting: int
    active: int
    done: int
    total: int
    current_rps: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    mean_response_time: float
    message: str
    error_message: Optional[str] = None
    report_path: Optional[str] = None


@dataclass
class BatchExecutionResult:
    """Resultado de envío de simulación batch"""
    execution_id: str
    submitted_at: str
    estimated_duration_minutes: int
    status: ExecutionStatus
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionStatusResponse:
    """Respuesta completa de estado de ejecución"""
    execution_id: str
    status: ExecutionStatus
    submitted_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    progress_percentage: float
    current_phase: str
    message: str
    
    # Real-time user statistics
    waiting_users: int
    active_users: int
    completed_users: int
    
    # Real-time performance metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    mean_response_time: float
    p95_response_time: Optional[float]
    current_rps: float
    
    # Results
    report_path: Optional[str]
    error_details: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceEngineException(Exception):
    """Exception específica del engine de performance"""
    pass
