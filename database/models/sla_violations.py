"""
SLA Violations Model - SQLModel para violaciones de SLA
======================================================

SQLModel para registrar y auditar violaciones autorizadas de reglas SLA:
- Control de excepciones de performance
- Flujo de aprobación con justificación
- Auditoría completa de violaciones
- Trazabilidad temporal del proceso
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from pydantic import validator

class ViolationType(str, Enum):
    """Tipos de violación de SLA"""
    CONCURRENCY = "concurrency"      # Exceso de usuarios concurrentes
    DURATION = "duration"            # Duración excesiva de prueba
    RPS = "rps"                      # Requests por segundo excesivo
    EXECUTION_WINDOW = "execution_window"  # Fuera de ventana permitida
    APPROVAL_BYPASS = "approval_bypass"    # Saltarse aprobación requerida
    RESOURCE_LIMIT = "resource_limit"      # Límites de recursos
    CUSTOM = "custom"                # Violación personalizada

class ExecutionStatus(str, Enum):
    """Estados de ejecución de la violación"""
    PENDING = "pending"      # Pendiente de aprobación
    APPROVED = "approved"    # Aprobada, lista para ejecutar
    DENIED = "denied"        # Denegada por administrador
    EXECUTED = "executed"    # Ejecutada exitosamente
    RESOLVED = "resolved"    # Resuelta/cerrada
    CANCELLED = "cancelled"  # Cancelada por usuario

class RiskLevel(str, Enum):
    """Niveles de riesgo de la violación"""
    LOW = "LOW"          # Riesgo bajo (1-25)
    MEDIUM = "MEDIUM"    # Riesgo medio (26-50)
    HIGH = "HIGH"        # Riesgo alto (51-75)
    CRITICAL = "CRITICAL"  # Riesgo crítico (76-100)

class SlaViolations(SQLModel, table=True):
    """
    Violaciones de SLA - Registro y Control de Excepciones
    
    Esta tabla registra todas las violaciones autorizadas de reglas SLA,
    proporcionando control, auditoría y trazabilidad completa del proceso
    de aprobación y ejecución de excepciones.
    """
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="ID único de la violación")
    
    # Relación con SLA violado
    sla_id: int = Field(foreign_key="performance_slas.id", description="ID del SLA violado")
    
    # Detalles de la violación
    command_text: str = Field(max_length=1000, description="Comando o acción que causó la violación")
    violation_type: ViolationType = Field(description="Tipo de violación")
    requested_value: Optional[str] = Field(default=None, max_length=100, description="Valor solicitado que excede el límite")
    sla_limit: Optional[str] = Field(default=None, max_length=100, description="Límite SLA que se está violando")
    
    # Evaluación de riesgo
    risk_score: Optional[int] = Field(default=None, ge=1, le=100, description="Puntuación de riesgo (1-100)")
    risk_level: Optional[RiskLevel] = Field(default=None, description="Nivel de riesgo categorizado")
    
    # Estado y flujo de aprobación
    execution_status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Estado actual de la violación")
    approved_by: Optional[str] = Field(default=None, max_length=100, description="Usuario que aprobó/denegó la violación")
    approval_reason: Optional[str] = Field(default=None, description="Justificación de la aprobación/denegación")
    
    # Control temporal
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Momento de detección de la violación")
    approved_at: Optional[datetime] = Field(default=None, description="Momento de aprobación/denegación")
    executed_at: Optional[datetime] = Field(default=None, description="Momento de ejecución")
    resolved_at: Optional[datetime] = Field(default=None, description="Momento de resolución/cierre")
    
    # Metadatos adicionales
    severity_notes: Optional[str] = Field(default=None, description="Notas adicionales sobre la severidad")
    execution_notes: Optional[str] = Field(default=None, description="Notas de ejecución")
    resolution_notes: Optional[str] = Field(default=None, description="Notas de resolución")
    
    # Auditoría
    created_by: Optional[str] = Field(default=None, max_length=100, description="Usuario que registró la violación")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(default=None, description="Fecha de última actualización")
    
    # Relación con el SLA (para consultas JOINed)
    # sla: Optional["PerformanceSLAs"] = Relationship(back_populates="violations")
    
    @validator('risk_score')
    def validate_risk_score(cls, v):
        """Valida que el risk_score esté en rango válido"""
        if v is not None and (v < 1 or v > 100):
            raise ValueError("risk_score debe estar entre 1 y 100")
        return v
    
    @validator('risk_level', pre=False, always=True)
    def set_risk_level_from_score(cls, v, values):
        """Establece risk_level automáticamente basado en risk_score"""
        risk_score = values.get('risk_score')
        
        # Si ya se especificó risk_level, mantenerlo
        if v is not None:
            return v
        
        # Auto-asignar basado en risk_score
        if risk_score is not None:
            if risk_score <= 25:
                return RiskLevel.LOW
            elif risk_score <= 50:
                return RiskLevel.MEDIUM
            elif risk_score <= 75:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL
        
        return None
    
    @validator('approved_by')
    def validate_approval_consistency(cls, v, values):
        """Valida consistencia en datos de aprobación"""
        status = values.get('execution_status')
        
        # Si está aprobado o denegado, debe tener approved_by
        if status in [ExecutionStatus.APPROVED, ExecutionStatus.DENIED] and not v:
            raise ValueError(f"approved_by es requerido cuando execution_status es {status}")
        
        return v
    
    @validator('approval_reason')
    def validate_approval_reason(cls, v, values):
        """Valida que haya justificación para aprobaciones/denegaciones"""
        status = values.get('execution_status')
        approved_by = values.get('approved_by')
        
        # Si hay approved_by, debe haber approval_reason
        if approved_by and not v:
            raise ValueError("approval_reason es requerido cuando hay approved_by")
        
        # Para estados aprobado/denegado, approval_reason es obligatorio
        if status in [ExecutionStatus.APPROVED, ExecutionStatus.DENIED] and not v:
            raise ValueError(f"approval_reason es requerido para status {status}")
        
        return v
    
    @validator('executed_at')
    def validate_execution_timing(cls, v, values):
        """Valida que executed_at sea consistente con el estado"""
        status = values.get('execution_status')
        
        # executed_at solo debe existir si status es EXECUTED o RESOLVED
        if v and status not in [ExecutionStatus.EXECUTED, ExecutionStatus.RESOLVED]:
            raise ValueError(f"executed_at no debe existir cuando status es {status}")
        
        # Si status es EXECUTED, debe tener executed_at
        if status == ExecutionStatus.EXECUTED and not v:
            return datetime.utcnow()  # Auto-asignar si no se especificó
        
        return v
    
    @validator('resolved_at')
    def validate_resolution_timing(cls, v, values):
        """Valida que resolved_at sea consistente con el estado"""
        status = values.get('execution_status')
        
        # resolved_at solo debe existir si status es RESOLVED
        if v and status != ExecutionStatus.RESOLVED:
            raise ValueError(f"resolved_at no debe existir cuando status es {status}")
        
        # Si status es RESOLVED, debe tener resolved_at
        if status == ExecutionStatus.RESOLVED and not v:
            return datetime.utcnow()  # Auto-asignar si no se especificó
        
        return v
    
    def get_duration_minutes(self) -> Optional[float]:
        """Calcular duración total del proceso en minutos"""
        if not self.resolved_at:
            return None
        
        duration = self.resolved_at - self.detected_at
        return duration.total_seconds() / 60
    
    def get_approval_duration_minutes(self) -> Optional[float]:
        """Calcular tiempo de aprobación en minutos"""
        if not self.approved_at:
            return None
        
        duration = self.approved_at - self.detected_at
        return duration.total_seconds() / 60
    
    def is_overdue(self, max_pending_hours: int = 24) -> bool:
        """Verificar si la violación está vencida sin aprobación"""
        if self.execution_status != ExecutionStatus.PENDING:
            return False
        
        hours_pending = (datetime.utcnow() - self.detected_at).total_seconds() / 3600
        return hours_pending > max_pending_hours
    
    def can_be_approved(self) -> bool:
        """Verificar si la violación puede ser aprobada"""
        return self.execution_status == ExecutionStatus.PENDING
    
    def can_be_executed(self) -> bool:
        """Verificar si la violación puede ser ejecutada"""
        return self.execution_status == ExecutionStatus.APPROVED
    
    def can_be_resolved(self) -> bool:
        """Verificar si la violación puede ser resuelta"""
        return self.execution_status in [ExecutionStatus.EXECUTED, ExecutionStatus.DENIED]
    
    def get_status_summary(self) -> dict:
        """Obtener resumen del estado actual"""
        return {
            "id": self.id,
            "violation_type": self.violation_type,
            "risk_level": self.risk_level,
            "execution_status": self.execution_status,
            "pending_hours": (datetime.utcnow() - self.detected_at).total_seconds() / 3600,
            "is_overdue": self.is_overdue(),
            "can_be_approved": self.can_be_approved(),
            "can_be_executed": self.can_be_executed(),
            "can_be_resolved": self.can_be_resolved()
        }

# Clase de tabla para compatibilidad con esquemas existentes
class sla_violations(SlaViolations, table=True):
    """Alias para mantener compatibilidad con nombre de tabla en minúsculas"""
    pass
