"""
Performance Execution Errors Model - SQLModel for execution startup failures

Modelo para registrar fallos que NO PERMITEN que una simulación inicie, con:
- Información básica del error (tipo, mensaje, detalles)
- Trazabilidad técnica (stack trace)
- Campos de auditoría y control
- Validación de tipos de error específicos para fallas de inicio
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field
from pydantic import field_validator, computed_field
from enum import Enum

class ExecutionErrorType(str, Enum):
    """Tipos de errores que impiden el inicio de simulaciones"""
    SETUP_ERROR = "SETUP_ERROR"              # Fallas en configuración inicial del test
    CONFIG_ERROR = "CONFIG_ERROR"            # Errores de configuración/parámetros
    VALIDATION_ERROR = "VALIDATION_ERROR"    # Fallas en validación de datos maestros
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"  # Problemas de infraestructura

class PerformanceExecutionErrors(SQLModel, table=True):
    """
    Performance Execution Errors model
    
    Registra errores que impiden que una simulación de performance inicie,
    proporcionando trazabilidad y análisis de fallas en el proceso de setup.
    """
    __tablename__ = "performance_execution_errors"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # Core error information (NOT NULL obligatorio)
    execution_id: str = Field(
        max_length=100,
        description="ID of the performance test execution that failed to start",
        index=True
    )
    
    error_type: ExecutionErrorType = Field(
        description="Type of error that prevented execution startup",
        index=True
    )
    
    error_message: str = Field(
        description="Human-readable error message describing the failure"
    )
    
    # Additional error context (Optional)
    error_details: Optional[str] = Field(
        default=None,
        description="Additional technical details about the error"
    )
    
    stack_trace: Optional[str] = Field(
        default=None,
        description="Full stack trace for debugging purposes"
    )
    
    # Timing information
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the error occurred",
        index=True
    )
    
    # Audit fields
    created_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User or system that created this error record"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when record was last updated"
    )
    
    # Validation methods
    @field_validator('execution_id')
    @classmethod
    def validate_execution_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Execution ID cannot be empty')
        return v.strip()
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Error message cannot be empty')
        return v.strip()
    
    @field_validator('error_type')
    @classmethod
    def validate_error_type(cls, v: ExecutionErrorType) -> ExecutionErrorType:
        if v not in ExecutionErrorType:
            raise ValueError(f'Error type must be one of: {[t.value for t in ExecutionErrorType]}')
        return v
    
    # Business logic properties
    @computed_field
    @property
    def is_configuration_related(self) -> bool:
        """Check if error is related to configuration issues"""
        return self.error_type in [ExecutionErrorType.CONFIG_ERROR, ExecutionErrorType.VALIDATION_ERROR]
    
    @computed_field
    @property
    def is_technical_failure(self) -> bool:
        """Check if error is a technical/infrastructure failure"""
        return self.error_type in [ExecutionErrorType.SETUP_ERROR, ExecutionErrorType.INFRASTRUCTURE_ERROR]
    
    @computed_field
    @property
    def severity_level(self) -> str:
        """Determine severity level based on error type"""
        severity_map = {
            ExecutionErrorType.INFRASTRUCTURE_ERROR: "CRITICAL",
            ExecutionErrorType.SETUP_ERROR: "HIGH", 
            ExecutionErrorType.CONFIG_ERROR: "MEDIUM",
            ExecutionErrorType.VALIDATION_ERROR: "MEDIUM"
        }
        return severity_map.get(self.error_type, "UNKNOWN")
    
    @computed_field
    @property
    def error_category(self) -> str:
        """Categorize error for reporting purposes"""
        if self.is_configuration_related:
            return "Configuration"
        elif self.is_technical_failure:
            return "Technical"
        else:
            return "Unknown"
    
    # Utility methods
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    def get_summary(self) -> dict:
        """Get a summary of the error for reporting"""
        return {
            "execution_id": self.execution_id,
            "error_type": self.error_type.value,
            "error_category": self.error_category,
            "severity": self.severity_level,
            "occurred_at": self.occurred_at.isoformat(),
            "message_preview": self.error_message[:100] + "..." if len(self.error_message) > 100 else self.error_message
        }
    
    def is_similar_to(self, other: 'PerformanceExecutionErrors') -> bool:
        """Check if this error is similar to another (same type and similar message)"""
        if self.error_type != other.error_type:
            return False
        
        # Simple similarity check based on first 50 characters
        self_msg = self.error_message[:50].lower()
        other_msg = other.error_message[:50].lower()
        
        return self_msg == other_msg
    
    @classmethod
    def create_sample_data(cls, execution_id: str) -> List['PerformanceExecutionErrors']:
        """Create sample error records for testing"""
        return [
            cls(
                execution_id=execution_id,
                error_type=ExecutionErrorType.SETUP_ERROR,
                error_message="Application detection failed: No SRP detector available",
                error_details="Failed to initialize application detection framework",
                stack_trace="Traceback (most recent call last):\n  File 'detector.py', line 45, in detect_app\n    raise RuntimeError('No SRP detector')",
                created_by="system"
            ),
            cls(
                execution_id=execution_id,
                error_type=ExecutionErrorType.VALIDATION_ERROR,
                error_message="Master data validation failed: Country 'ES' not found in master data",
                error_details="Validation failed during country code verification",
                created_by="system"
            ),
            cls(
                execution_id=execution_id,
                error_type=ExecutionErrorType.CONFIG_ERROR,
                error_message="Invalid configuration: Missing required parameter 'api_endpoint'",
                error_details="Configuration validation failed for test execution setup",
                created_by="user"
            ),
            cls(
                execution_id=execution_id,
                error_type=ExecutionErrorType.INFRASTRUCTURE_ERROR,
                error_message="Database connection failed: Unable to connect to test database",
                error_details="Infrastructure validation failed - database unreachable",
                stack_trace="ConnectionError: [Errno 61] Connection refused",
                created_by="system"
            )
        ]
    
    @classmethod
    def create_from_exception(
        cls, 
        execution_id: str, 
        error_type: ExecutionErrorType,
        exception: Exception,
        created_by: Optional[str] = None
    ) -> 'PerformanceExecutionErrors':
        """Create error record from an exception"""
        import traceback
        
        return cls(
            execution_id=execution_id,
            error_type=error_type,
            error_message=str(exception),
            error_details=f"Exception type: {type(exception).__name__}",
            stack_trace=traceback.format_exc(),
            created_by=created_by or "system"
        )
    
    # String representation
    def __str__(self) -> str:
        return f"ExecutionError({self.error_type.value}: {self.error_message[:50]}...)"
    
    def __repr__(self) -> str:
        return f"PerformanceExecutionErrors(id={self.id}, execution_id='{self.execution_id}', error_type='{self.error_type.value}')"
