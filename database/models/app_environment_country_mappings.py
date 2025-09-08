"""
App Environment Country Mappings Model - SQLModel model for unified mappings

Tabla unificada que maneja la tríada App-Environment-Country
con configuración técnica centralizada para testing.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import JSON as SQLAlchemyJSON
from decimal import Decimal
from pydantic import field_validator, model_validator
import re

if TYPE_CHECKING:
    from .apps import Apps
    from .countries import Countries
    from .environments import Environments

class AppEnvironmentCountryMapping(SQLModel, table=True):
    """
    App Environment Country Mappings table model
    
    Tabla unificada que representa la combinación válida de:
    - Aplicación + Ambiente + País
    - Configuración técnica (URL, headers, auth)
    - Configuración de testing (SLAs, performance)
    
    Reemplaza las tablas fragmentadas application_country_mapping
    y application_environment_configs con una sola fuente de verdad.
    """
    __tablename__ = 'app_environment_country_mappings'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # La tríada sagrada: APP + ENVIRONMENT + COUNTRY (NOT NULL obligatorio)
    application_id: int = Field(foreign_key="apps_master.id", description="Reference to application")
    environment_id: int = Field(foreign_key="environments_master.id", description="Reference to environment")
    country_id: int = Field(foreign_key="countries_master.id", description="Reference to country")
    
    # Configuración técnica (NOT NULL + validaciones)
    base_url: str = Field(
        max_length=500, 
        min_length=10,
        description="Complete base URL for this combination (must start with http:// or https://)"
    )
    protocol: str = Field(
        max_length=10, 
        default="https",
        description="Protocol (http/https only)"
    )
    default_headers: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Default headers for this combination"
    )
    auth_config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Authentication configuration"
    )
    
    # Configuración de testing (CHECK constraints reflejados)
    performance_config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Performance testing configuration"
    )
    max_response_time_ms: int = Field(
        default=2000, 
        ge=1,  # >= 1
        le=60000,  # <= 60000 (1 minuto máximo)
        description="Maximum acceptable response time in milliseconds (1-60000)"
    )
    max_error_rate_percent: Decimal = Field(
        default=Decimal("5.0"), 
        max_digits=5, 
        decimal_places=2,
        ge=0.0,  # >= 0.0
        le=100.0,  # <= 100.0
        description="Maximum acceptable error rate percentage (0.0-100.0)"
    )
    
    # Estado y metadata (NOT NULL + validaciones)
    is_active: bool = Field(default=True, description="Whether this mapping is active")
    launched_date: Optional[datetime] = Field(default=None, description="When the app was launched in this environment/country")
    deprecated_date: Optional[datetime] = Field(default=None, description="When the app was deprecated in this environment/country")
    priority: int = Field(
        default=1,
        ge=1,  # >= 1
        le=10,  # <= 10
        description="Priority for cases with multiple configurations (1-10)"
    )
    
    # Timestamps (NOT NULL en created_at)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # === VALIDACIONES PYDANTIC (MATCHING DATABASE CONSTRAINTS) ===
    
    @model_validator(mode='after')
    def validate_all_constraints(self):
        """Validate all fields match database CHECK constraints"""
        
        # Validate base_url
        if hasattr(self, 'base_url') and self.base_url:
            if not re.match(r'^https?://.+', self.base_url):
                raise ValueError('base_url must start with http:// or https://')
            if len(self.base_url) < 10:
                raise ValueError('base_url must be at least 10 characters long')
        
        # Validate protocol
        if hasattr(self, 'protocol') and self.protocol:
            if self.protocol not in ('http', 'https'):
                raise ValueError('protocol must be either "http" or "https"')
        
        # Validate max_response_time_ms
        if hasattr(self, 'max_response_time_ms') and self.max_response_time_ms is not None:
            if not (1 <= self.max_response_time_ms <= 60000):
                raise ValueError('max_response_time_ms must be between 1 and 60000')
        
        # Validate max_error_rate_percent
        if hasattr(self, 'max_error_rate_percent') and self.max_error_rate_percent is not None:
            if not (Decimal('0.0') <= self.max_error_rate_percent <= Decimal('100.0')):
                raise ValueError('max_error_rate_percent must be between 0.0 and 100.0')
        
        # Validate priority
        if hasattr(self, 'priority') and self.priority is not None:
            if not (1 <= self.priority <= 10):
                raise ValueError('priority must be between 1 and 10')
        
        return self
    
    # Relationships
    application: "Apps" = Relationship(back_populates="country_mappings")
    country: "Countries" = Relationship(back_populates="app_mappings")
    environment: "Environments" = Relationship(back_populates="app_mappings")
    
    def __repr__(self) -> str:
        """String representation of the mapping record"""
        return f"<AppEnvironmentCountryMapping(id={self.id}, app_id={self.application_id}, env_id={self.environment_id}, country_id={self.country_id}, active={self.is_active})>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        app_name = self.application.app_code if self.application else f"App#{self.application_id}"
        country_name = self.country.country_code if self.country else f"Country#{self.country_id}"
        env_name = self.environment.env_code if self.environment else f"Env#{self.environment_id}"
        status = "Active" if self.is_active else "Inactive"
        return f"{app_name} → {env_name} → {country_name} ({status})"
    
    @property
    def is_currently_active(self) -> bool:
        """
        Check if mapping is currently active (considering deprecation date)
        
        Returns:
            True if mapping is active and not deprecated
        """
        if not self.is_active:
            return False
        
        if self.deprecated_date:
            # Ensure both dates are timezone-aware for proper comparison
            deprecated_date = self.deprecated_date
            if deprecated_date.tzinfo is None:
                deprecated_date = deprecated_date.replace(tzinfo=timezone.utc)
            
            if deprecated_date <= datetime.now(timezone.utc):
                return False
        
        return True
    
    @property
    def deployment_duration_days(self) -> Optional[int]:
        """
        Calculate how long the app has been deployed in this environment/country
        
        Returns:
            Number of days since launch, None if not launched
        """
        if not self.launched_date:
            return None
        
        # Ensure both dates are timezone-aware for proper comparison
        launch_date = self.launched_date
        if launch_date.tzinfo is None:
            launch_date = launch_date.replace(tzinfo=timezone.utc)
        
        end_date = self.deprecated_date
        if end_date:
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = datetime.now(timezone.utc)
        
        return (end_date - launch_date).days
    
    @property
    def full_configuration(self) -> Dict[str, Any]:
        """
        Get complete configuration for this mapping
        
        Returns:
            Dictionary with all configuration settings
        """
        return {
            "base_url": self.base_url,
            "protocol": self.protocol,
            "headers": self.default_headers or {},
            "auth": self.auth_config or {},
            "performance": self.performance_config or {},
            "sla": {
                "max_response_time_ms": self.max_response_time_ms,
                "max_error_rate_percent": float(self.max_error_rate_percent)
            },
            "deployment": {
                "launched_date": self.launched_date.isoformat() if self.launched_date else None,
                "deprecated_date": self.deprecated_date.isoformat() if self.deprecated_date else None,
                "days_active": self.deployment_duration_days
            }
        }
    
    def deprecate(self, deprecation_date: Optional[datetime] = None) -> None:
        """
        Mark this mapping as deprecated
        
        Args:
            deprecation_date: When to deprecate (defaults to now)
        """
        self.deprecated_date = deprecation_date or datetime.now(timezone.utc)
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """
        Reactivate this mapping (remove deprecation)
        """
        self.deprecated_date = None
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    @classmethod
    def create_sample_data(cls) -> list['AppEnvironmentCountryMapping']:
        """
        Create sample data for testing and development
        
        Returns:
            List of sample mapping instances
        """
        return [
            cls(
                application_id=1,  # EVA
                environment_id=1,  # STA
                country_id=1,      # Romania
                base_url="https://api.sta.pluxee.app/gl/eva/bff-sta/ro",
                protocol="https",
                default_headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Country": "RO",
                    "X-Environment": "STA"
                },
                max_response_time_ms=3000,
                max_error_rate_percent=Decimal("5.0"),
                launched_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            )
        ]
