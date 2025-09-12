"""
Apps Master Model - SQLModel with enterprise-grade validation

Modelo mejorado para aplicaciones con:
- Campos de control y gestión empresarial
- Validaciones robustas de dominio
- Ciclo de vida y auditoría
- Eliminación del campo base_url_template redundante
"""
from datetime import datetime, timezone, date
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index
from pydantic import field_validator, model_validator
import re

if TYPE_CHECKING:
    from .countries import Countries
    from .app_environment_country_mappings import AppEnvironmentCountryMapping
    from .application_endpoints import ApplicationEndpoint
else:  # Runtime safe import to ensure mapper sees dependent model
    try:  # pragma: no cover
        from .application_endpoints import ApplicationEndpoint  # noqa: F401
    except Exception:  # pragma: no cover
        ApplicationEndpoint = None  # type: ignore


class Apps(SQLModel, table=True):
    """
    Applications Master table with enterprise controls
    
    Gestiona aplicaciones con controles empresariales:
    - Identificación única y validada
    - Campos de ownership y contacto
    - Configuración técnica por defecto
    - Ciclo de vida completo (launch → deprecation → EOL)
    - Auditoría y metadatos
    """
    
    __tablename__ = 'apps_master'  # type: ignore[assignment]
    # DB-level constraints & indexes
    __table_args__ = (
        UniqueConstraint('app_code', name='uq_apps_master_app_code'),
        Index('ix_apps_master_app_code', 'app_code'),
    )
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # Identificación única de la aplicación (NOT NULL + validaciones)
    app_code: str = Field(
        max_length=50,
        min_length=2,
        description="Unique application code (uppercase, no spaces)"
    )
    app_name: str = Field(
        max_length=255,
        min_length=2,
        description="Human-readable application name"
    )
    
    # Metadata descriptiva
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Application description"
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Application category (web, mobile, api, service, microservice, legacy, integration)"
    )
    
    # Campos de control y gestión
    owner_team: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Team responsible for this application"
    )
    technical_contact: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Technical contact (email or name)"
    )
    business_contact: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Business contact (email or name)"
    )
    
    # Configuración técnica por defecto
    default_timeout_ms: int = Field(
        default=5000,
        ge=1000,  # >= 1 segundo
        le=300000,  # <= 5 minutos
        description="Default timeout in milliseconds (1s-5min)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,  # >= 0
        le=10,  # <= 10
        description="Maximum number of retries (0-10)"
    )
    
    # Estado y ciclo de vida
    is_active: bool = Field(default=True, description="Whether this application is active")
    is_production_ready: bool = Field(
        default=False, 
        description="Whether this application is ready for production"
    )
    launch_date: Optional[date] = Field(default=None, description="Application launch date")
    deprecation_date: Optional[date] = Field(default=None, description="Application deprecation date")
    end_of_life_date: Optional[date] = Field(default=None, description="Application end-of-life date")
    
    # Metadatos de auditoría
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, max_length=100, description="User who created this record")
    updated_by: Optional[str] = Field(default=None, max_length=100, description="User who last updated this record")
    
    # Relationships
    country_mappings: List["AppEnvironmentCountryMapping"] = Relationship(back_populates="application")
    # endpoints: List["ApplicationEndpoint"] = Relationship(back_populates="application")  # Disabled - now uses mapping_id
    
    # === VALIDACIONES PYDANTIC (MATCHING DATABASE CONSTRAINTS) ===
    
    @model_validator(mode='after')
    def validate_all_constraints(self):
        """Validate all fields match database CHECK constraints"""
        
        # Validate app_code (uppercase, no spaces, length)
        if hasattr(self, 'app_code') and self.app_code:
            if not (2 <= len(self.app_code) <= 50):
                raise ValueError('app_code must be between 2 and 50 characters')
            if self.app_code != self.app_code.upper():
                raise ValueError('app_code must be uppercase')
            if ' ' in self.app_code:
                raise ValueError('app_code cannot contain spaces')
        
        # Validate app_name length
        if hasattr(self, 'app_name') and self.app_name:
            if not (2 <= len(self.app_name) <= 255):
                raise ValueError('app_name must be between 2 and 255 characters')
        
        # Validate description length
        if hasattr(self, 'description') and self.description is not None:
            if len(self.description) > 1000:
                raise ValueError('description must be 1000 characters or less')
        
        # Validate category
        if hasattr(self, 'category') and self.category is not None:
            valid_categories = {
                'web', 'mobile', 'api', 'service', 'microservice', 'legacy', 'integration'
            }
            if self.category not in valid_categories:
                raise ValueError(f'category must be one of: {", ".join(valid_categories)}')
        
        # Validate contact fields length
        for field_name in ['owner_team', 'technical_contact', 'business_contact']:
            field_value = getattr(self, field_name, None)
            if field_value is not None:
                max_length = 100 if field_name == 'owner_team' else 255
                if len(field_value) > max_length:
                    raise ValueError(f'{field_name} must be {max_length} characters or less')
        
        # Validate date sequence (launch <= deprecation <= EOL)
        if hasattr(self, 'launch_date') and hasattr(self, 'deprecation_date'):
            if (self.launch_date and self.deprecation_date and 
                self.launch_date > self.deprecation_date):
                raise ValueError('launch_date must be before or equal to deprecation_date')
        
        if hasattr(self, 'deprecation_date') and hasattr(self, 'end_of_life_date'):
            if (self.deprecation_date and self.end_of_life_date and 
                self.deprecation_date > self.end_of_life_date):
                raise ValueError('deprecation_date must be before or equal to end_of_life_date')
        
        return self
    
    # === BUSINESS LOGIC METHODS ===
    
    @property
    def is_deprecated(self) -> bool:
        """Check if application is deprecated"""
        if not self.deprecation_date:
            return False
        return date.today() >= self.deprecation_date
    
    @property
    def is_end_of_life(self) -> bool:
        """Check if application has reached end of life"""
        if not self.end_of_life_date:
            return False
        return date.today() >= self.end_of_life_date
    
    @property
    def lifecycle_status(self) -> str:
        """Get current lifecycle status"""
        if self.is_end_of_life:
            return "end_of_life"
        elif self.is_deprecated:
            return "deprecated"
        elif not self.is_production_ready:
            return "development"
        elif self.launch_date and date.today() >= self.launch_date:
            return "production"
        else:
            return "pre_launch"
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return f"{self.app_name} ({self.app_code})"
    
    @property
    def active_countries(self) -> List['Countries']:
        """
        Get list of countries where this application is actively deployed
        
        Returns:
            List of Countries objects where this app is active
        """
        return [
            mapping.country for mapping in self.country_mappings 
            if mapping.is_active and mapping.country.is_active
        ]
    
    @property
    def country_count(self) -> int:
        """
        Get count of active countries for this application
        
        Returns:
            Number of countries where this app is actively deployed
        """
        return len([
            mapping for mapping in self.country_mappings 
            if mapping.is_active and mapping.country.is_active
        ])
    
    def get_default_config(self) -> dict:
        """Get default configuration for this application"""
        return {
            "app_code": self.app_code,
            "app_name": self.app_name,
            "timeout_ms": self.default_timeout_ms,
            "max_retries": self.max_retries,
            "category": self.category,
            "is_production_ready": self.is_production_ready,
            "lifecycle_status": self.lifecycle_status
        }
    
    def is_available_in_country(self, country_code: str) -> bool:
        """
        Check if application is available in a specific country
        
        Args:
            country_code: ISO country code to check
            
        Returns:
            True if application is available in the country
        """
        return any(
            mapping.is_active and 
            mapping.country.is_active and 
            mapping.country.country_code == country_code
            for mapping in self.country_mappings
        )
    
    def get_launch_date_for_country(self, country_code: str) -> Optional[datetime]:
        """
        Get launch date for application in a specific country
        
        Args:
            country_code: ISO country code
            
        Returns:
            Launch date if available, None otherwise
        """
        for mapping in self.country_mappings:
            if (mapping.country.country_code == country_code and 
                mapping.is_active):
                return mapping.launched_date
        return None
    
    def mark_as_deprecated(self, deprecation_date: Optional[date] = None) -> None:
        """Mark application as deprecated"""
        self.deprecation_date = deprecation_date or date.today()
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_end_of_life(self, eol_date: Optional[date] = None) -> None:
        """Mark application as end of life"""
        self.end_of_life_date = eol_date or date.today()
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def promote_to_production(self, launch_date: Optional[date] = None) -> None:
        """Promote application to production"""
        self.is_production_ready = True
        self.launch_date = launch_date or date.today()
        self.updated_at = datetime.now(timezone.utc)
    
    def update_contacts(
        self, 
        owner_team: Optional[str] = None,
        technical_contact: Optional[str] = None,
        business_contact: Optional[str] = None
    ) -> None:
        """Update contact information"""
        if owner_team is not None:
            self.owner_team = owner_team
        if technical_contact is not None:
            self.technical_contact = technical_contact
        if business_contact is not None:
            self.business_contact = business_contact
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        status = f" [{self.lifecycle_status}]" if self.lifecycle_status != "production" else ""
        return f"<App {self.app_code}: {self.app_name}{status}>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.display_name
    
    @classmethod
    def create_sample_data(cls) -> List['Apps']:
        """
        Create sample data for testing and development
        
        Returns:
            List of sample Apps instances
        """
        return [
            cls(
                app_code="EVA",
                app_name="EVA Application",
                description="Enterprise Virtual Assistant for customer service",
                category="web",
                owner_team="AI Platform Team",
                technical_contact="eva-team@company.com",
                default_timeout_ms=10000,
                is_production_ready=True,
                launch_date=date(2023, 1, 15)
            ),
            cls(
                app_code="ONEAPP", 
                app_name="OneApp Platform",
                description="Unified platform for all company services",
                category="mobile",
                owner_team="Mobile Team",
                technical_contact="oneapp-team@company.com",
                default_timeout_ms=8000,
                is_production_ready=True,
                launch_date=date(2022, 6, 1)
            ),
            cls(
                app_code="MOBILE",
                app_name="Mobile Banking",
                description="Mobile banking application for customers",
                category="mobile",
                owner_team="Banking Team",
                technical_contact="mobile-banking@company.com",
                default_timeout_ms=15000,
                is_production_ready=True,
                launch_date=date(2021, 3, 10)
            )
        ]
