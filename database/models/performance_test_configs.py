"""
Performance Test Configs Models
===============================

SQLModel definitions for performance test configurations with hierarchy support.
"""

from datetime import datetime
from typing import Optional, Any, List, Dict
from sqlmodel import SQLModel, Field, JSON, Column
from pydantic import field_validator

class PerformanceTestConfigBase(SQLModel):
    """Base model for performance test configurations."""
    
    application_id: int = Field(foreign_key="apps_master.id", description="Application ID")
    country_id: Optional[int] = Field(default=None, foreign_key="countries_master.id", description="Country ID (optional)")
    environment_id: int = Field(foreign_key="environments_master.id", description="Environment ID")
    
    config_name: str = Field(max_length=255, description="Configuration name")
    test_type: str = Field(description="Type of test (load, stress, spike, etc.)")
    load_pattern: str = Field(description="Load pattern (ramp_users, constant_users, spike)")
    
    # Test execution parameters
    base_users: int = Field(ge=1, description="Base number of users")
    peak_users: int = Field(ge=1, description="Peak number of users")
    target_rps: Optional[float] = Field(default=None, ge=0, description="Target requests per second")
    
    # Duration parameters
    ramp_duration_seconds: int = Field(ge=0, description="Ramp up duration in seconds")
    hold_duration_seconds: int = Field(ge=0, description="Hold duration in seconds")
    total_duration_seconds: int = Field(ge=1, description="Total test duration in seconds")
    
    # Think time parameters
    think_time_min_seconds: float = Field(ge=0, description="Minimum think time in seconds")
    think_time_max_seconds: float = Field(ge=0, description="Maximum think time in seconds")
    
    # Template and metadata
    is_active: bool = Field(default=True, description="Whether config is active")
    is_template: bool = Field(default=False, description="Whether this is a template config")
    description: Optional[str] = Field(default=None, description="Configuration description")
    
    # Hierarchy fields
    specificity_level: int = Field(default=4, ge=1, le=4, description="Hierarchy specificity level (1=highest, 4=lowest)")
    hierarchy_priority: int = Field(default=1000, ge=1, description="Priority within hierarchy level")
    config_scope: str = Field(default="APP_GENERAL", max_length=50, description="Configuration scope")
    endpoint_pattern: Optional[str] = Field(default=None, max_length=200, description="Endpoint pattern for matching")
    
    # Validation and control
    allows_cascade: bool = Field(default=True, description="Whether to allow cascading to lower specificity")
    validation_status: str = Field(default="PENDING", max_length=20, description="Validation status")
    last_validated_at: Optional[datetime] = Field(default=None, description="Last validation timestamp")
    
    # Advanced configuration
    priority_level: str = Field(default="MEDIUM", max_length=20, description="Priority level (LOW, MEDIUM, HIGH)")
    execution_prompts: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Execution prompts and instructions")
    advanced_config: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Advanced configuration parameters")
    resource_requirements: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Resource requirements")
    execution_frequency: Optional[str] = Field(default=None, max_length=50, description="Execution frequency")
    
    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, max_length=100, description="Created by user")
    updated_by: Optional[str] = Field(default=None, max_length=100, description="Updated by user")

    @field_validator('test_type')
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        """Validate test type values."""
        valid_types = {'load', 'stress', 'spike', 'volume', 'endurance', 'baseline'}
        if v.lower() not in valid_types:
            raise ValueError(f"test_type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator('load_pattern')
    @classmethod
    def validate_load_pattern(cls, v: str) -> str:
        """Validate load pattern values."""
        valid_patterns = {'ramp_users', 'constant_users', 'spike', 'step', 'gradual'}
        if v.lower() not in valid_patterns:
            raise ValueError(f"load_pattern must be one of: {', '.join(valid_patterns)}")
        return v.lower()

    @field_validator('priority_level')
    @classmethod
    def validate_priority_level(cls, v: str) -> str:
        """Validate priority level values."""
        valid_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"priority_level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator('validation_status')
    @classmethod
    def validate_validation_status(cls, v: str) -> str:
        """Validate validation status values."""
        valid_statuses = {'PENDING', 'VALIDATED', 'FAILED', 'EXPIRED'}
        if v.upper() not in valid_statuses:
            raise ValueError(f"validation_status must be one of: {', '.join(valid_statuses)}")
        return v.upper()

    @field_validator('config_scope')
    @classmethod
    def validate_config_scope(cls, v: str) -> str:
        """Validate configuration scope values."""
        valid_scopes = {'ENDPOINT', 'COUNTRY_ENV_APP', 'ENV_APP', 'APP_GENERAL'}
        if v.upper() not in valid_scopes:
            raise ValueError(f"config_scope must be one of: {', '.join(valid_scopes)}")
        return v.upper()

    @field_validator('peak_users')
    @classmethod
    def validate_peak_users(cls, v: int, info) -> int:
        """Validate that peak_users >= base_users."""
        if 'base_users' in info.data and v < info.data['base_users']:
            raise ValueError("peak_users must be greater than or equal to base_users")
        return v

    @field_validator('think_time_max_seconds')
    @classmethod
    def validate_think_time_max(cls, v: float, info) -> float:
        """Validate that think_time_max >= think_time_min."""
        if 'think_time_min_seconds' in info.data and v < info.data['think_time_min_seconds']:
            raise ValueError("think_time_max_seconds must be greater than or equal to think_time_min_seconds")
        return v


class PerformanceTestConfig(PerformanceTestConfigBase, table=True):
    """Performance test configuration table model."""
    
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")


class PerformanceTestConfigCreate(PerformanceTestConfigBase):
    """Model for creating performance test configurations."""
    pass


class PerformanceTestConfigUpdate(SQLModel):
    """Model for updating performance test configurations."""
    
    application_id: Optional[int] = None
    country_id: Optional[int] = None
    environment_id: Optional[int] = None
    config_name: Optional[str] = None
    test_type: Optional[str] = None
    load_pattern: Optional[str] = None
    base_users: Optional[int] = None
    peak_users: Optional[int] = None
    target_rps: Optional[float] = None
    ramp_duration_seconds: Optional[int] = None
    hold_duration_seconds: Optional[int] = None
    total_duration_seconds: Optional[int] = None
    think_time_min_seconds: Optional[float] = None
    think_time_max_seconds: Optional[float] = None
    is_active: Optional[bool] = None
    is_template: Optional[bool] = None
    description: Optional[str] = None
    specificity_level: Optional[int] = None
    hierarchy_priority: Optional[int] = None
    config_scope: Optional[str] = None
    endpoint_pattern: Optional[str] = None
    allows_cascade: Optional[bool] = None
    validation_status: Optional[str] = None
    priority_level: Optional[str] = None
    execution_prompts: Optional[Dict[str, Any]] = None
    advanced_config: Optional[Dict[str, Any]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    execution_frequency: Optional[str] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class PerformanceTestConfigRead(PerformanceTestConfigBase):
    """Model for reading performance test configurations with computed fields."""
    
    id: int
    
    # Computed fields for hierarchy resolution
    effective_priority: Optional[int] = Field(default=None, description="Computed effective priority")
    hierarchy_path: Optional[str] = Field(default=None, description="Hierarchy resolution path")
    template_source: Optional[str] = Field(default=None, description="Source template if applicable")


class PerformanceTestConfigHierarchyQuery(SQLModel):
    """Model for hierarchical configuration queries."""
    
    application_id: int
    environment_id: int
    country_id: Optional[int] = None
    endpoint_pattern: Optional[str] = None
    test_type: Optional[str] = None
    include_templates: bool = Field(default=False, description="Include template configurations")
    allow_cascade: bool = Field(default=True, description="Allow cascading to lower specificity")


class PerformanceTestConfigSummary(SQLModel):
    """Summary model for configuration listings."""
    
    id: int
    config_name: str
    test_type: str
    config_scope: str
    hierarchy_priority: int
    is_active: bool
    is_template: bool
    validation_status: str
    application_name: Optional[str] = None
    environment_name: Optional[str] = None
    country_name: Optional[str] = None
    created_at: datetime
