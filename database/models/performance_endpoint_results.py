"""
Performance Endpoint Results Model - SQLModel with comprehensive performance metrics

Modelo para resultados de endpoints de performance testing con:
- Métricas completas de tiempo de respuesta (incluyendo p75)
- Contadores de requests y errores
- Métricas de throughput (RPS)
- Campos de control y auditoría
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field
from pydantic import field_validator, computed_field
from decimal import Decimal

class PerformanceEndpointResults(SQLModel, table=True):
    """
    Performance Endpoint Results model
    
    Almacena métricas detalladas de performance por endpoint durante la ejecución
    de tests de carga. Incluye percentiles completos y campos de auditoría.
    """
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # Conexión con execution (NOT NULL obligatorio)
    execution_id: str = Field(
        max_length=100,
        description="ID of the performance test execution",
        index=True
    )
    
    # Endpoint information (NOT NULL obligatorio)
    endpoint_name: str = Field(
        max_length=500,
        description="Endpoint path or name being tested",
        index=True
    )
    
    http_method: str = Field(
        max_length=10,
        description="HTTP method (GET, POST, PUT, DELETE, etc.)",
        index=True
    )
    
    endpoint_url: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Full endpoint URL"
    )
    
    # Request counts (NOT NULL fields)
    total_requests: int = Field(
        ge=0,
        description="Total number of requests made to this endpoint"
    )
    
    successful_requests: int = Field(
        ge=0,
        description="Number of successful requests (status 200-299)"
    )
    
    failed_requests: int = Field(
        ge=0,
        description="Number of failed requests (status >= 400 or network errors)"
    )
    
    # Response time percentiles (Optional pero recomendado)
    p50_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="50th percentile response time in milliseconds"
    )
    
    p75_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="75th percentile response time in milliseconds (NUEVA MÉTRICA)"
    )
    
    p95_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="95th percentile response time in milliseconds"
    )
    
    p99_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="99th percentile response time in milliseconds"
    )
    
    avg_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average response time in milliseconds"
    )
    
    max_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum response time in milliseconds"
    )
    
    min_response_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum response time in milliseconds"
    )
    
    # Throughput metrics (Optional)
    requests_per_second: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average requests per second during test"
    )
    
    max_rps: Optional[float] = Field(
        default=None,
        ge=0,
        description="Peak requests per second achieved"
    )
    
    # Status code breakdown (Optional JSON)
    status_code_distribution: Optional[str] = Field(
        default=None,
        description="JSON string with status code distribution {200: 150, 404: 5, etc.}"
    )
    
    # Error information (Optional)
    error_messages: Optional[str] = Field(
        default=None,
        description="Sample error messages encountered (JSON or text)"
    )
    
    # Test configuration context (Optional)
    concurrent_users: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of concurrent users/threads during test"
    )
    
    test_duration_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Duration of the test in seconds"
    )
    
    # Additional metrics (Optional)
    bytes_received: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total bytes received from this endpoint"
    )
    
    bytes_sent: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total bytes sent to this endpoint"
    )
    
    # Control and audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when record was created"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when record was last updated"
    )
    
    created_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User or system that created this record"
    )
    
    # Validation methods
    @field_validator('total_requests')
    @classmethod
    def validate_total_requests(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Total requests cannot be negative')
        return v
    
    @field_validator('successful_requests', 'failed_requests')
    @classmethod
    def validate_request_counts(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Request counts cannot be negative')
        return v
    
    @field_validator('p50_response_time', 'p75_response_time', 'p95_response_time', 'p99_response_time')
    @classmethod
    def validate_percentiles(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Response times cannot be negative')
        return v
    
    @field_validator('execution_id')
    @classmethod
    def validate_execution_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Execution ID cannot be empty')
        return v.strip()
    
    @field_validator('endpoint_name')
    @classmethod
    def validate_endpoint_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Endpoint name cannot be empty')
        return v.strip()
    
    @field_validator('http_method')
    @classmethod
    def validate_http_method(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('HTTP method cannot be empty')
        v = v.strip().upper()
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if v not in valid_methods:
            raise ValueError(f'HTTP method must be one of: {valid_methods}')
        return v
    
    # Business logic properties
    @computed_field
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @computed_field
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        return 100.0 - self.error_rate
    
    @computed_field
    @property
    def performance_grade(self) -> str:
        """
        Calculate performance grade based on error rate and p95 response time
        A: < 1% errors and < 500ms p95
        B: < 2% errors and < 1000ms p95
        C: < 5% errors and < 2000ms p95
        D: < 10% errors and < 5000ms p95
        F: >= 10% errors or >= 5000ms p95
        """
        error_rate = self.error_rate
        p95 = self.p95_response_time or 0
        
        if error_rate < 1 and p95 < 500:
            return 'A'
        elif error_rate < 2 and p95 < 1000:
            return 'B'
        elif error_rate < 5 and p95 < 2000:
            return 'C'
        elif error_rate < 10 and p95 < 5000:
            return 'D'
        else:
            return 'F'
    
    @computed_field
    @property
    def has_performance_issues(self) -> bool:
        """Check if endpoint has performance issues"""
        return self.performance_grade in ['D', 'F']
    
    @computed_field
    @property
    def is_percentiles_consistent(self) -> bool:
        """Verify that percentiles are in ascending order"""
        percentiles = [
            self.p50_response_time,
            self.p75_response_time,
            self.p95_response_time,
            self.p99_response_time
        ]
        
        # Filter out None values
        valid_percentiles = [p for p in percentiles if p is not None]
        
        if len(valid_percentiles) < 2:
            return True  # Can't check consistency with < 2 values
        
        # Check if sorted in ascending order
        return valid_percentiles == sorted(valid_percentiles)
    
    # Utility methods
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    def get_summary(self) -> dict:
        """Get a summary of key metrics"""
        return {
            "endpoint": f"{self.http_method} {self.endpoint_name}",
            "total_requests": self.total_requests,
            "error_rate": round(self.error_rate, 2),
            "p95_response_time": self.p95_response_time,
            "requests_per_second": self.requests_per_second,
            "performance_grade": self.performance_grade
        }
    
    @classmethod
    def create_sample_data(cls, execution_id: str) -> List['PerformanceEndpointResults']:
        """Create sample endpoint results for testing"""
        return [
            cls(
                execution_id=execution_id,
                endpoint_name="/api/users",
                http_method="GET",
                endpoint_url="https://api.example.com/api/users",
                total_requests=1000,
                successful_requests=995,
                failed_requests=5,
                p50_response_time=120.5,
                p75_response_time=180.2,
                p95_response_time=350.8,
                p99_response_time=650.1,
                avg_response_time=145.6,
                max_response_time=850.0,
                min_response_time=45.2,
                requests_per_second=25.5,
                max_rps=45.0,
                concurrent_users=10,
                test_duration_seconds=40.0,
                created_by="system"
            ),
            cls(
                execution_id=execution_id,
                endpoint_name="/api/users",
                http_method="POST",
                endpoint_url="https://api.example.com/api/users",
                total_requests=500,
                successful_requests=490,
                failed_requests=10,
                p50_response_time=250.8,
                p75_response_time=320.4,
                p95_response_time=580.2,
                p99_response_time=950.5,
                avg_response_time=295.1,
                max_response_time=1200.0,
                min_response_time=89.3,
                requests_per_second=12.5,
                max_rps=22.0,
                concurrent_users=10,
                test_duration_seconds=40.0,
                created_by="system"
            ),
            cls(
                execution_id=execution_id,
                endpoint_name="/api/products",
                http_method="GET",
                endpoint_url="https://api.example.com/api/products",
                total_requests=750,
                successful_requests=745,
                failed_requests=5,
                p50_response_time=95.3,
                p75_response_time=140.7,
                p95_response_time=280.9,
                p99_response_time=450.2,
                avg_response_time=125.8,
                max_response_time=600.0,
                min_response_time=32.1,
                requests_per_second=18.8,
                max_rps=35.0,
                concurrent_users=10,
                test_duration_seconds=40.0,
                created_by="system"
            )
        ]
