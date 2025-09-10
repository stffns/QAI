"""
Environments Model - SQLModel for application environments

Modelo para gestión de ambientes empresariales:
- Ambientes de desarrollo, staging, UAT, producción
- Configuración de URLs y patrones
- Control de estado y metadatos
"""
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator

if TYPE_CHECKING:
    from .app_environment_country_mappings import AppEnvironmentCountryMapping
    from .application_endpoints import ApplicationEndpoint


class Environments(SQLModel, table=True):
    """
    Environments Master table
    
    Gestiona los ambientes donde se despliegan las aplicaciones:
    - Ambientes de desarrollo (DEV, STA, UAT)
    - Ambientes de producción (PRD)
    - Configuración de URLs y patrones
    - Estado y metadatos de control
    """
    
    __tablename__ = 'environments_master'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # Identificación del ambiente
    env_name: str = Field(
        max_length=255,
        min_length=2,
        description="Environment name (e.g., Production, Staging, UAT)"
    )
    env_code: str = Field(
        max_length=50,
        min_length=2,
        unique=True,
        description="Environment code (e.g., PRD, STA, UAT, DEV)"
    )
    
    # Configuración del ambiente
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Environment description"
    )
    url_pattern: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL pattern for this environment"
    )
    
    # Estado y control
    is_production: bool = Field(
        default=False,
        description="Whether this is a production environment"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this environment is active"
    )
    
    # Metadatos
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )
    
    # Relationships
    app_mappings: List["AppEnvironmentCountryMapping"] = Relationship(back_populates="environment")
    
    # === VALIDACIONES PYDANTIC ===
    
    @field_validator('env_code')
    @classmethod
    def validate_env_code(cls, v: str) -> str:
        """Validate environment code format"""
        if not v:
            raise ValueError('env_code is required')
        v = v.strip().upper()
        if not (2 <= len(v) <= 50):
            raise ValueError('env_code must be between 2 and 50 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('env_code must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @field_validator('env_name')
    @classmethod
    def validate_env_name(cls, v: str) -> str:
        """Validate environment name"""
        if not v:
            raise ValueError('env_name is required')
        v = v.strip()
        if not (2 <= len(v) <= 255):
            raise ValueError('env_name must be between 2 and 255 characters')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description length"""
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError('description must be 500 characters or less')
            return v if v else None
        return v
    
    @field_validator('url_pattern')
    @classmethod
    def validate_url_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL pattern format"""
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError('url_pattern must be 500 characters or less')
            # Basic URL pattern validation
            if v and not (v.startswith('http://') or v.startswith('https://') or '{' in v):
                raise ValueError('url_pattern must be a valid URL or contain placeholder variables')
            return v if v else None
        return v
    
    # === BUSINESS LOGIC METHODS ===
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return f"{self.env_name} ({self.env_code})"
    
    @property
    def is_production_environment(self) -> bool:
        """Check if this is a production environment"""
        return self.is_production and self.is_active
    
    @property
    def environment_type(self) -> str:
        """Get environment type for categorization"""
        if not self.is_active:
            return "INACTIVE"
        return "PRODUCTION" if self.is_production else "NON_PRODUCTION"
    
    @property
    def active_mappings_count(self) -> int:
        """Get count of active application mappings for this environment"""
        return len([
            mapping for mapping in self.app_mappings 
            if mapping.is_active
        ])
    
    @property
    def applications_count(self) -> int:
        """Get count of unique applications in this environment"""
        return len(set([
            mapping.application_id for mapping in self.app_mappings 
            if mapping.is_active
        ]))
    
    def get_url_for_application(self, app_code: str, country_code: Optional[str] = None) -> Optional[str]:
        """
        Get the specific URL for an application in this environment
        
        Args:
            app_code: Application code
            country_code: Optional country code for country-specific URLs
            
        Returns:
            URL if available, None otherwise
        """
        # Look for specific mapping
        for mapping in self.app_mappings:
            if (mapping.application.app_code == app_code and 
                mapping.is_active and
                (country_code is None or mapping.country.country_code == country_code)):
                return mapping.base_url
        
        # Fallback to URL pattern if available
        if self.url_pattern and '{app_code}' in self.url_pattern:
            url = self.url_pattern.replace('{app_code}', app_code.lower())
            if country_code and '{country}' in url:
                url = url.replace('{country}', country_code.lower())
            return url
        
        return None
    
    def has_application(self, app_code: str) -> bool:
        """
        Check if a specific application is deployed in this environment
        
        Args:
            app_code: Application code to check
            
        Returns:
            True if application is deployed in this environment
        """
        return any(
            mapping.is_active and 
            mapping.application.app_code == app_code
            for mapping in self.app_mappings
        )
    
    def get_countries_for_application(self, app_code: str) -> List[str]:
        """
        Get list of countries where an application is available in this environment
        
        Args:
            app_code: Application code
            
        Returns:
            List of country codes
        """
        return [
            mapping.country.country_code
            for mapping in self.app_mappings
            if (mapping.is_active and 
                mapping.application.app_code == app_code)
        ]
    
    def promote_to_production(self) -> None:
        """Promote environment to production status"""
        self.is_production = True
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate environment"""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate environment"""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def update_url_pattern(self, url_pattern: str) -> None:
        """Update URL pattern"""
        self.url_pattern = url_pattern
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        env_type = "PROD" if self.is_production else "NON-PROD"
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"<Environment {self.env_code}: {self.env_name} [{env_type}] [{status}]>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.display_name
    
    @classmethod
    def create_sample_data(cls) -> List['Environments']:
        """
        Create sample data for testing and development
        
        Returns:
            List of sample Environments instances
        """
        return [
            cls(
                env_name="Development",
                env_code="DEV",
                description="Development environment for testing new features",
                url_pattern="https://dev-{app_code}.example.com",
                is_production=False,
                is_active=True
            ),
            cls(
                env_name="Staging",
                env_code="STA",
                description="Staging environment for pre-production testing",
                url_pattern="https://staging-{app_code}.example.com",
                is_production=False,
                is_active=True
            ),
            cls(
                env_name="User Acceptance Testing",
                env_code="UAT",
                description="User acceptance testing environment",
                url_pattern="https://uat-{app_code}.example.com",
                is_production=False,
                is_active=True
            ),
            cls(
                env_name="Production",
                env_code="PRD",
                description="Production environment for live applications",
                url_pattern="https://{app_code}.example.com",
                is_production=True,
                is_active=True
            )
        ]
