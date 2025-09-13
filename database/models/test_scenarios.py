"""
Test Scenarios Model - Sistema de escenarios para testing automatizado

Permite agrupar endpoints en escenarios específicos para diferentes tipos de testing:
- Performance Testing: Solo APIs críticas optimizadas para carga
- Functional Testing: Cobertura completa de funcionalidad
- Smoke Testing: APIs básicas para validación rápida
- Business Flow: Flujos de negocio específicos con orden de ejecución
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON as SQLAlchemyJSON, Column, UniqueConstraint, Index
from enum import Enum
from pydantic import field_validator, model_validator

if TYPE_CHECKING:
    from .app_environment_country_mappings import AppEnvironmentCountryMapping
    from .application_endpoints import ApplicationEndpoint


class TestScenarioType(str, Enum):
    """Tipos de escenarios de testing"""
    PERFORMANCE = "PERFORMANCE"      # Para pruebas de carga/stress
    FUNCTIONAL = "FUNCTIONAL"        # Testing funcional completo  
    SMOKE = "SMOKE"                 # Pruebas básicas de humo
    REGRESSION = "REGRESSION"        # Pruebas de regresión
    BUSINESS_FLOW = "BUSINESS_FLOW" # Flujos de negocio específicos
    INTEGRATION = "INTEGRATION"      # Testing de integración
    SECURITY = "SECURITY"           # Testing de seguridad
    LOAD_BALANCER = "LOAD_BALANCER" # Testing de load balancer


class TestScenario(SQLModel, table=True):
    """
    Test Scenarios - Definición de escenarios de testing
    
    Cada escenario agrupa endpoints para un propósito específico
    vinculado a un mapping (app+env+country)
    """
    __tablename__ = 'test_scenarios'  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint('mapping_id', 'scenario_name', name='uq_mapping_scenario_name'),
        Index('ix_scenario_mapping_type', 'mapping_id', 'scenario_type'),
        Index('ix_scenario_active', 'is_active'),
    )
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # FK to mapping (app+env+country combination)
    mapping_id: int = Field(
        foreign_key="app_environment_country_mappings.id",
        description="Reference to app+env+country mapping"
    )
    
    # Scenario definition
    scenario_name: str = Field(
        max_length=100,
        min_length=1,
        description="Scenario name (unique per mapping)"
    )
    scenario_type: TestScenarioType = Field(
        description="Type of scenario (PERFORMANCE, FUNCTIONAL, etc.)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Detailed description of what this scenario tests"
    )
    
    # Configuration
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Scenario-specific configuration (timeouts, concurrency, etc.)"
    )
    
    # Execution settings
    max_execution_time_minutes: int = Field(
        default=30,
        ge=1,
        le=480,  # 8 horas máximo
        description="Maximum execution time in minutes (1-480)"
    )
    retry_failed_endpoints: bool = Field(
        default=True,
        description="Whether to retry failed endpoints"
    )
    stop_on_critical_failure: bool = Field(
        default=False,
        description="Whether to stop scenario execution on critical failures"
    )
    
    # Performance settings (for PERFORMANCE scenarios)
    target_concurrent_users: Optional[int] = Field(
        default=None,
        ge=1,
        le=10000,
        description="Target concurrent users for performance scenarios"
    )
    ramp_up_time_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=3600,
        description="Ramp-up time in seconds for performance scenarios"
    )
    
    # State and metadata
    is_active: bool = Field(default=True, description="Whether this scenario is active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None, max_length=100, description="User who created the scenario")
    
    # Priority for execution order
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Execution priority (1=highest, 10=lowest)"
    )
    
    # Relationships
    mapping: Optional["AppEnvironmentCountryMapping"] = Relationship()
    scenario_endpoints: List["TestScenarioEndpoint"] = Relationship(back_populates="scenario")
    
    @field_validator('scenario_name')
    @classmethod
    def validate_scenario_name(cls, v: str) -> str:
        """Validate scenario name format"""
        if not v.strip():
            raise ValueError("Scenario name cannot be empty")
        
        # Alphanumeric, spaces, hyphens, underscores only
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v.strip()):
            raise ValueError("Scenario name can only contain alphanumeric characters, spaces, hyphens, and underscores")
        
        return v.strip()
    
    @model_validator(mode='after')
    def validate_performance_settings(self):
        """Validate performance-specific settings"""
        if self.scenario_type == TestScenarioType.PERFORMANCE:
            if self.target_concurrent_users is None:
                raise ValueError("Performance scenarios must specify target_concurrent_users")
            if self.target_concurrent_users > 1000:
                # Warning: High concurrency
                pass
        
        if self.target_concurrent_users is not None and self.scenario_type != TestScenarioType.PERFORMANCE:
            # Allow but warn
            pass
        
        return self


class TestScenarioEndpoint(SQLModel, table=True):
    """
    Test Scenario Endpoints - Endpoints incluidos en cada escenario
    
    Tabla de relación many-to-many entre scenarios y endpoints
    con configuración específica por endpoint en el escenario
    """
    __tablename__ = 'test_scenario_endpoints'  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint('scenario_id', 'endpoint_id', name='uq_scenario_endpoint'),
        Index('ix_scenario_endpoints_order', 'scenario_id', 'execution_order'),
        Index('ix_scenario_endpoints_active', 'is_active'),
    )
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign keys
    scenario_id: int = Field(
        foreign_key="test_scenarios.id",
        description="Reference to test scenario"
    )
    endpoint_id: int = Field(
        foreign_key="application_endpoints.id", 
        description="Reference to application endpoint"
    )
    
    # Execution configuration
    execution_order: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Order of execution within scenario (1=first)"
    )
    is_critical: bool = Field(
        default=False,
        description="Whether this endpoint is critical (failure affects scenario result)"
    )
    is_active: bool = Field(default=True, description="Whether this endpoint is active in scenario")
    
    # Performance-specific settings
    weight: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Weight for performance testing (higher = more frequent execution)"
    )
    custom_timeout_ms: Optional[int] = Field(
        default=None,
        ge=100,
        le=300000,  # 5 minutos máximo
        description="Custom timeout for this endpoint in this scenario (overrides default)"
    )
    
    # Expected behavior
    expected_status_codes: Optional[List[int]] = Field(
        default=[200],
        sa_column=Column(SQLAlchemyJSON),
        description="Expected HTTP status codes for success"
    )
    custom_validation: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Custom validation rules for this endpoint in this scenario"
    )
    
    # Dependencies
    depends_on_endpoint_ids: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="List of endpoint IDs that must succeed before this one"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=500, description="Notes about this endpoint in scenario")
    
    # Relationships
    scenario: Optional["TestScenario"] = Relationship(back_populates="scenario_endpoints")
    endpoint: Optional["ApplicationEndpoint"] = Relationship()
    
    @field_validator('expected_status_codes')
    @classmethod
    def validate_status_codes(cls, v):
        """Validate HTTP status codes"""
        if v is None:
            return [200]
        
        if not isinstance(v, list):
            raise ValueError("Expected status codes must be a list")
        
        for code in v:
            if not isinstance(code, int) or code < 100 or code > 599:
                raise ValueError(f"Invalid HTTP status code: {code}")
        
        return v
    
    @model_validator(mode='after')
    def validate_execution_order(self):
        """Validate execution order logic"""
        if self.execution_order < 1:
            raise ValueError("Execution order must be >= 1")
        
        return self


# Add relationship back to AppEnvironmentCountryMapping
def add_scenario_relationship():
    """Add test_scenarios relationship to AppEnvironmentCountryMapping"""
    # This would be added to the AppEnvironmentCountryMapping model:
    # test_scenarios: List["TestScenario"] = Relationship(back_populates="mapping")
    pass