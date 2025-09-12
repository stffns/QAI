"""
Application Endpoints Model - Clean Normalized Structure

Modelo limpio con solo mapping_id como FK.
Acceso a app/env/country via JOIN con app_environment_country_mappings.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON as SQLAlchemyJSON, Column
from pydantic import field_validator
import json


class ApplicationEndpoint(SQLModel, table=True):
    """
    Clean normalized Application Endpoints model
    
    Structure:
    - mapping_id: FK to app_environment_country_mappings (contains app+env+country)
    - endpoint info: name, url, method, type, description, body
    - timestamps: created_at, updated_at
    """
    
    __tablename__ = 'application_endpoints'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Single FK to mapping (contains app+env+country+config)
    mapping_id: int = Field(
        foreign_key="app_environment_country_mappings.id",
        description="Reference to mapping containing app+env+country+config"
    )
    
    # Endpoint information
    endpoint_name: str = Field(
        max_length=255,
        min_length=1,
        description="Endpoint name (unique per mapping)"
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
        description="Endpoint type (api, health, auth, etc.)"
    )
    
    # Additional data
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Endpoint description"
    )
    body: Optional[str] = Field(
        default=None,
        sa_column=Column(SQLAlchemyJSON),
        description="Request body template (JSON)"
    )
    
    # State and timestamps
    is_active: bool = Field(default=True, description="Endpoint is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # === VALIDATORS ===
    
    @field_validator('endpoint_url')
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URL format"""
        if not v.startswith('/'):
            raise ValueError("Endpoint URL must start with /")
        if len(v) < 1 or len(v) > 500:
            raise ValueError("Endpoint URL length must be 1-500 characters")
        return v
    
    @field_validator('http_method')
    @classmethod
    def validate_http_method(cls, v: str) -> str:
        """Validate HTTP method"""
        valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
        if v.upper() not in valid_methods:
            raise ValueError(f"HTTP method must be one of: {valid_methods}")
        return v.upper()
    
    @field_validator('endpoint_type')
    @classmethod
    def validate_endpoint_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate endpoint type"""
        if v is None:
            return v
        valid_types = {'api', 'health', 'auth', 'dashboard', 'admin', 'public', 'internal'}
        if v.lower() not in valid_types:
            raise ValueError(f"Endpoint type must be one of: {valid_types}")
        return v.lower()
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v: Optional[str]) -> Optional[str]:
        """Validate JSON body format"""
        if v is None:
            return v
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f"Body must be valid JSON: {e}")
    
    # === BUSINESS LOGIC METHODS ===
    
    @property
    def endpoint_config(self) -> Dict[str, Any]:
        """Get endpoint configuration as dictionary"""
        config = {
            'name': self.endpoint_name,
            'url': self.endpoint_url,
            'method': self.http_method,
            'type': self.endpoint_type,
            'active': self.is_active
        }
        
        if self.description:
            config['description'] = self.description
            
        if self.body:
            try:
                config['body'] = json.loads(self.body)
            except json.JSONDecodeError:
                config['body_raw'] = self.body
                
        return config
    
    def get_full_url(self, base_url: str) -> str:
        """Get full URL combining base_url + endpoint_url"""
        # Remove trailing slash from base_url if present
        base_clean = base_url.rstrip('/')
        # endpoint_url already starts with /
        return f"{base_clean}{self.endpoint_url}"
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if endpoint matches a search pattern"""
        pattern_lower = pattern.lower()
        return (
            pattern_lower in self.endpoint_name.lower() or
            pattern_lower in self.endpoint_url.lower() or
            pattern_lower in self.http_method.lower() or
            (self.description and pattern_lower in self.description.lower())
        )
    
    def is_method(self, method: str) -> bool:
        """Check if endpoint uses specific HTTP method"""
        return self.http_method.upper() == method.upper()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'mapping_id': self.mapping_id,
            'endpoint_name': self.endpoint_name,
            'endpoint_url': self.endpoint_url,
            'http_method': self.http_method,
            'endpoint_type': self.endpoint_type,
            'description': self.description,
            'body': self.body,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<ApplicationEndpoint(id={self.id}, mapping={self.mapping_id}, {self.http_method} {self.endpoint_name})>"