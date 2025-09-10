"""
Application Endpoints Model - SQLModel with robust validation

Modelo para endpoints de aplicaciones con soporte para:
- Endpoints globales (country_id = NULL)
- Endpoints específicos por país (country_id = NOT NULL)
- Validaciones robustas que coinciden con constraints de DB
- Campo body JSON para configuraciones adicionales
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON as SQLAlchemyJSON, UniqueConstraint
from pydantic import field_validator, model_validator
import json
import re

if TYPE_CHECKING:
    from .apps import Apps
    from .countries import Countries


class ApplicationEndpoint(SQLModel, table=True):
    """
    Application Endpoints model with country-specific support
    
    Soporta tanto endpoints globales como específicos por país:
    - country_id = NULL: Endpoint global (aplica a todos los países)
    - country_id = NOT NULL: Endpoint específico de un país
    
    Validaciones sincronizadas con constraints de base de datos.
    """
    
    __tablename__ = 'application_endpoints'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # La tríada de identificación: APP + ENVIRONMENT + COUNTRY (opcional)
    application_id: int = Field(foreign_key="apps_master.id", description="Reference to application")
    environment_id: int = Field(foreign_key="environments_master.id", description="Reference to environment")
    country_id: Optional[int] = Field(
        default=None, 
        foreign_key="countries_master.id", 
        description="Reference to country (NULL = global endpoint)"
    )
    
    # Información del endpoint (NOT NULL + validaciones)
    endpoint_name: str = Field(
        max_length=255,
        min_length=1,
        description="Endpoint name (must be unique per app+env+country combination)"
    )
    endpoint_url: str = Field(
        max_length=500,
        min_length=1,
        description="Endpoint URL path (must start with /)"
    )
    http_method: str = Field(
        max_length=10,
        description="HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)"
    )
    endpoint_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Endpoint type (api, health, auth, dashboard, admin, public, internal)"
    )
    
    # Datos adicionales y metadata
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Endpoint description"
    )
    body: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Additional JSON data (headers, payloads, config)"
    )
    
    # Estado y timestamps (NOT NULL obligatorio)
    is_active: bool = Field(default=True, description="Whether this endpoint is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    application: Optional["Apps"] = Relationship(back_populates="endpoints")
    country: Optional["Countries"] = Relationship(back_populates="endpoints")
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            'application_id', 'environment_id', 'country_id', 'endpoint_name',
            name='uq_app_env_country_endpoint'
        ),
    )
    
    # === VALIDACIONES PYDANTIC (MATCHING DATABASE CONSTRAINTS) ===
    
    @model_validator(mode='after')
    def validate_all_constraints(self):
        """Validate all fields match database CHECK constraints"""
        
        # Validate endpoint_name
        if hasattr(self, 'endpoint_name') and self.endpoint_name:
            if len(self.endpoint_name) < 1:
                raise ValueError('endpoint_name must be at least 1 character long')
        
        # Validate endpoint_url (must start with /)
        if hasattr(self, 'endpoint_url') and self.endpoint_url:
            if not self.endpoint_url.startswith('/'):
                raise ValueError('endpoint_url must start with /')
            if not (1 <= len(self.endpoint_url) <= 500):
                raise ValueError('endpoint_url must be between 1 and 500 characters')
        
        # Validate http_method
        if hasattr(self, 'http_method') and self.http_method:
            valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
            if self.http_method not in valid_methods:
                raise ValueError(f'http_method must be one of: {", ".join(valid_methods)}')
        
        # Validate endpoint_type
        if hasattr(self, 'endpoint_type') and self.endpoint_type is not None:
            valid_types = {'api', 'health', 'auth', 'dashboard', 'admin', 'public', 'internal'}
            if self.endpoint_type not in valid_types:
                raise ValueError(f'endpoint_type must be one of: {", ".join(valid_types)} or None')
        
        # Validate description length
        if hasattr(self, 'description') and self.description is not None:
            if len(self.description) > 1000:
                raise ValueError('description must be 1000 characters or less')
        
        # Validate is_active (boolean values)
        if hasattr(self, 'is_active') and self.is_active is not None:
            if not isinstance(self.is_active, bool):
                raise ValueError('is_active must be a boolean')
        
        return self
    
    # === BUSINESS LOGIC METHODS ===
    
    @property
    def is_global_endpoint(self) -> bool:
        """Check if this is a global endpoint (applies to all countries)"""
        return self.country_id is None
    
    @property
    def is_country_specific(self) -> bool:
        """Check if this is a country-specific endpoint"""
        return self.country_id is not None
    
    @property
    def full_identifier(self) -> str:
        """Get full identifier for this endpoint"""
        country_part = f"country_{self.country_id}" if self.country_id else "global"
        return f"app_{self.application_id}_env_{self.environment_id}_{country_part}_{self.endpoint_name}"
    
    @property
    def endpoint_config(self) -> Dict[str, Any]:
        """Get endpoint configuration as dictionary"""
        config = {
            "name": self.endpoint_name,
            "url": self.endpoint_url,
            "method": self.http_method,
            "type": self.endpoint_type,
            "is_global": self.is_global_endpoint,
            "is_active": self.is_active
        }
        
        if self.body:
            config["additional_config"] = self.body
            
        if self.description:
            config["description"] = self.description
            
        return config
    
    def get_effective_url(self, base_url: Optional[str] = None) -> str:
        """Get the complete URL by combining base_url + endpoint_url"""
        if base_url:
            # Remove trailing slash from base_url and leading slash from endpoint_url if needed
            clean_base = base_url.rstrip('/')
            clean_endpoint = self.endpoint_url.lstrip('/')
            return f"{clean_base}/{clean_endpoint}"
        return self.endpoint_url
    
    def is_compatible_with_country(self, country_id: Optional[int]) -> bool:
        """Check if this endpoint is compatible with the given country"""
        # Global endpoints are compatible with any country
        if self.is_global_endpoint:
            return True
        # Country-specific endpoints only match their specific country
        return self.country_id == country_id
    
    def to_test_config(self) -> Dict[str, Any]:
        """Convert to configuration suitable for API testing"""
        config = {
            "endpoint_name": self.endpoint_name,
            "url": self.endpoint_url,
            "method": self.http_method,
            "endpoint_type": self.endpoint_type or "api",
            "is_active": self.is_active,
            "is_global": self.is_global_endpoint
        }
        
        # Add body configuration if present
        if self.body:
            if "headers" in self.body:
                config["headers"] = self.body["headers"]
            if "payload" in self.body:
                config["payload"] = self.body["payload"]
            if "test_config" in self.body:
                config.update(self.body["test_config"])
        
        return config
    
    def mark_as_deprecated(self) -> None:
        """Mark endpoint as deprecated (inactive)"""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        country_info = f" (country: {self.country_id})" if self.country_id else " (global)"
        return f"<ApplicationEndpoint {self.endpoint_name}: {self.http_method} {self.endpoint_url}{country_info}>"
