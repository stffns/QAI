"""
Performance Test Executions Models
==================================

SQLModel definitions for performance test executions with enhanced tracking capabilities.
"""

from datetime import datetime
from typing import Optional, Any, List, Dict
from sqlmodel import SQLModel, Field, JSON, Column
from pydantic import field_validator
from enum import Enum

class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

class ValidationStatus(str, Enum):
    """Validation status enumeration."""
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

class SLACompliance(str, Enum):
    """SLA compliance enumeration."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

class ExecutionScope(str, Enum):
    """Execution scope enumeration."""
    FUNCTIONAL = "FUNCTIONAL"
    LOAD = "LOAD"
    STRESS = "STRESS"
    SPIKE = "SPIKE"
    VOLUME = "VOLUME"
    ENDURANCE = "ENDURANCE"
    BASELINE = "BASELINE"
    REGRESSION = "REGRESSION"

class ExecutionPriority(str, Enum):
    """Execution priority enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExecutionTrigger(str, Enum):
    """Execution trigger enumeration."""
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    CI_CD = "CI_CD"
    API = "API"
    WEBHOOK = "WEBHOOK"

class PerformanceGrade(str, Enum):
    """Performance grade enumeration."""
    A = "A"  # Excellent
    B = "B"  # Good
    C = "C"  # Average
    D = "D"  # Poor
    F = "F"  # Failed

class PerformanceTestExecutionBase(SQLModel):
    """Base model for performance test executions."""
    
    # Core execution info
    test_config_id: Optional[int] = Field(default=None, foreign_key="performance_test_configs.id", description="Test configuration ID")
    execution_id: str = Field(max_length=100, description="Unique execution identifier")
    execution_name: str = Field(max_length=255, description="Execution name")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Execution status")
    
    # Timing
    start_time: Optional[datetime] = Field(default=None, description="Execution start time")
    end_time: Optional[datetime] = Field(default=None, description="Execution end time")
    duration_seconds: Optional[float] = Field(default=None, ge=0, description="Total execution duration in seconds")
    
    # Request metrics
    total_requests: int = Field(default=0, ge=0, description="Total number of requests")
    successful_requests: int = Field(default=0, ge=0, description="Number of successful requests")
    failed_requests: int = Field(default=0, ge=0, description="Number of failed requests")
    
    # Response time metrics
    avg_response_time: Optional[float] = Field(default=None, ge=0, description="Average response time in ms")
    p95_response_time: Optional[float] = Field(default=None, ge=0, description="95th percentile response time in ms")
    p99_response_time: Optional[float] = Field(default=None, ge=0, description="99th percentile response time in ms")
    max_response_time: Optional[float] = Field(default=None, ge=0, description="Maximum response time in ms")
    min_response_time: Optional[float] = Field(default=None, ge=0, description="Minimum response time in ms")
    
    # Throughput metrics
    avg_rps: Optional[float] = Field(default=None, ge=0, description="Average requests per second")
    max_rps: Optional[float] = Field(default=None, ge=0, description="Maximum requests per second")
    error_rate: Optional[float] = Field(default=0.0, ge=0, le=1, description="Error rate (0.0 to 1.0)")
    
    # File paths
    simulation_file_path: Optional[str] = Field(default=None, max_length=500, description="Path to simulation file")
    gatling_report_path: Optional[str] = Field(default=None, max_length=500, description="Path to Gatling report")
    
    # Execution metadata
    executed_by: Optional[str] = Field(default=None, max_length=100, description="User who executed the test")
    
    # Enhanced control fields
    validation_status: ValidationStatus = Field(default=ValidationStatus.PENDING, description="Validation status of results")
    sla_compliance: Optional[SLACompliance] = Field(default=None, description="SLA compliance status")
    is_baseline: bool = Field(default=False, description="Whether this is a baseline execution")
    
    # Execution context
    execution_environment: Optional[str] = Field(default=None, max_length=100, description="Environment where test was executed")
    test_purpose: Optional[str] = Field(default=None, max_length=100, description="Purpose of the test execution")
    execution_scope: ExecutionScope = Field(default=ExecutionScope.FUNCTIONAL, description="Scope of execution")
    execution_priority: ExecutionPriority = Field(default=ExecutionPriority.MEDIUM, description="Priority level")
    
    # Comparison and analysis
    baseline_execution_id: Optional[int] = Field(default=None, foreign_key="performance_test_executions.id", description="Reference to baseline execution")
    comparison_group: Optional[str] = Field(default=None, max_length=100, description="Group for related executions")
    configuration_snapshot: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Snapshot of configuration used")
    
    # Additional metadata
    execution_notes: Optional[str] = Field(default=None, description="Notes about the execution")
    tags: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Tags for categorization")
    execution_trigger: ExecutionTrigger = Field(default=ExecutionTrigger.MANUAL, description="What triggered the execution")
    
    # Resource metrics
    memory_usage_peak: Optional[float] = Field(default=None, ge=0, description="Peak memory usage in MB")
    cpu_usage_avg: Optional[float] = Field(default=None, ge=0, le=100, description="Average CPU usage percentage")
    network_io: Optional[float] = Field(default=None, ge=0, description="Network I/O in MB")
    
    # Error tracking
    error_details: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Detailed error information")
    performance_grade: Optional[PerformanceGrade] = Field(default=None, description="Performance grade (A, B, C, D, F)")
    
    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    updated_by: Optional[str] = Field(default=None, max_length=100, description="Updated by user")

    @field_validator('error_rate')
    @classmethod
    def validate_error_rate(cls, v: Optional[float]) -> Optional[float]:
        """Validate error rate is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("error_rate must be between 0.0 and 1.0")
        return v

    @field_validator('successful_requests')
    @classmethod
    def validate_successful_requests(cls, v: int, info) -> int:
        """Validate successful requests don't exceed total."""
        if 'total_requests' in info.data and v > info.data['total_requests']:
            raise ValueError("successful_requests cannot exceed total_requests")
        return v

    @field_validator('failed_requests')
    @classmethod
    def validate_failed_requests(cls, v: int, info) -> int:
        """Validate failed requests don't exceed total."""
        if 'total_requests' in info.data and v > info.data['total_requests']:
            raise ValueError("failed_requests cannot exceed total_requests")
        return v

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate end_time is after start_time."""
        if v is not None and 'start_time' in info.data and info.data['start_time'] is not None:
            if v < info.data['start_time']:
                raise ValueError("end_time cannot be before start_time")
        return v

    def calculate_error_rate(self) -> float:
        """Calculate error rate from request counts."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def calculate_success_rate(self) -> float:
        """Calculate success rate from request counts."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.COMPLETED and (self.error_rate or 0) <= 0.05

    def get_duration_minutes(self) -> Optional[float]:
        """Get duration in minutes."""
        return self.duration_seconds / 60 if self.duration_seconds else None


class PerformanceTestExecution(PerformanceTestExecutionBase, table=True):
    """Performance test execution table model."""
    __tablename__ = "performance_test_executions"
    
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")


class PerformanceTestExecutionCreate(PerformanceTestExecutionBase):
    """Model for creating performance test executions."""
    pass


class PerformanceTestExecutionUpdate(SQLModel):
    """Model for updating performance test executions."""
    
    test_config_id: Optional[int] = None
    execution_name: Optional[str] = None
    status: Optional[ExecutionStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_requests: Optional[int] = None
    successful_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    avg_response_time: Optional[float] = None
    p95_response_time: Optional[float] = None
    p99_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    avg_rps: Optional[float] = None
    max_rps: Optional[float] = None
    error_rate: Optional[float] = None
    simulation_file_path: Optional[str] = None
    gatling_report_path: Optional[str] = None
    executed_by: Optional[str] = None
    validation_status: Optional[ValidationStatus] = None
    sla_compliance: Optional[SLACompliance] = None
    is_baseline: Optional[bool] = None
    execution_environment: Optional[str] = None
    test_purpose: Optional[str] = None
    execution_scope: Optional[ExecutionScope] = None
    execution_priority: Optional[ExecutionPriority] = None
    baseline_execution_id: Optional[int] = None
    comparison_group: Optional[str] = None
    configuration_snapshot: Optional[Dict[str, Any]] = None
    execution_notes: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    execution_trigger: Optional[ExecutionTrigger] = None
    memory_usage_peak: Optional[float] = None
    cpu_usage_avg: Optional[float] = None
    network_io: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_grade: Optional[PerformanceGrade] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class PerformanceTestExecutionRead(PerformanceTestExecutionBase):
    """Model for reading performance test executions with computed fields."""
    
    id: int
    
    # Computed fields
    calculated_error_rate: Optional[float] = Field(default=None, description="Calculated error rate")
    calculated_success_rate: Optional[float] = Field(default=None, description="Calculated success rate")
    duration_minutes: Optional[float] = Field(default=None, description="Duration in minutes")
    is_execution_successful: Optional[bool] = Field(default=None, description="Whether execution was successful")


class PerformanceTestExecutionSummary(SQLModel):
    """Summary model for execution listings."""
    
    id: int
    execution_id: str
    execution_name: str
    status: ExecutionStatus
    validation_status: ValidationStatus
    sla_compliance: Optional[SLACompliance]
    execution_scope: ExecutionScope
    performance_grade: Optional[PerformanceGrade]
    is_baseline: bool
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    error_rate: Optional[float]
    total_requests: int
    test_config_name: Optional[str] = None
    created_at: datetime


class PerformanceTestExecutionComparison(SQLModel):
    """Model for comparing executions."""
    
    execution_id: str
    execution_name: str
    performance_grade: Optional[PerformanceGrade]
    error_rate: Optional[float]
    avg_response_time: Optional[float]
    avg_rps: Optional[float]
    total_requests: int
    duration_seconds: Optional[float]
    sla_compliance: Optional[SLACompliance]
    created_at: datetime


class PerformanceTestExecutionQuery(SQLModel):
    """Model for execution queries with filters."""
    
    test_config_id: Optional[int] = None
    status: Optional[ExecutionStatus] = None
    validation_status: Optional[ValidationStatus] = None
    sla_compliance: Optional[SLACompliance] = None
    execution_scope: Optional[ExecutionScope] = None
    is_baseline: Optional[bool] = None
    comparison_group: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_failed: bool = Field(default=True, description="Include failed executions")
    min_requests: Optional[int] = Field(default=None, description="Minimum number of requests")
    max_error_rate: Optional[float] = Field(default=None, description="Maximum error rate")


class BaselineComparisonResult(SQLModel):
    """Model for baseline comparison results."""
    
    current_execution_id: str
    baseline_execution_id: str
    performance_delta: float  # Percentage change
    response_time_delta: float  # Percentage change
    throughput_delta: float  # Percentage change
    error_rate_delta: float  # Percentage change
    overall_grade: PerformanceGrade
    recommendation: str
