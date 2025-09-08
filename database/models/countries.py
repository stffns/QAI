"""
Countries Model - SQLModel with enterprise-grade validation

Modelo mejorado para países con:
- Campos de control empresarial y gestión global
- Información geográfica y monetaria completa
- Validaciones robustas de dominios ISO
- Localización y configuración regional
- Auditoría y metadatos empresariales
"""
from datetime import datetime, timezone, date
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator, model_validator
import re

if TYPE_CHECKING:
    from .apps import Apps
    from .app_environment_country_mappings import AppEnvironmentCountryMapping
    from .application_endpoints import ApplicationEndpoint


class Countries(SQLModel, table=True):
    """
    Countries Master table with enterprise controls
    
    Gestiona países con información completa:
    - Identificación ISO estándar (alpha-2, alpha-3, numeric)
    - Información geográfica detallada (región, continente, capital)
    - Datos monetarios completos (moneda, símbolo, nombre)
    - Localización cultural (idiomas, formatos, timezone)
    - Campos de control empresarial (prioridad, unidad de negocio)
    - Estado de producción y capacidades
    - Auditoría completa
    """
    
    __tablename__ = 'countries_master'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True, description="Primary key")
    
    # Identificación del país (ISO standards)
    country_name: str = Field(
        max_length=255,
        min_length=2,
        description="Full country name"
    )
    country_code: str = Field(
        max_length=3,
        min_length=2,
        description="ISO 3166-1 alpha-2 country code (2 chars UPPERCASE)"
    )
    iso_alpha3_code: Optional[str] = Field(
        default=None,
        max_length=3,
        description="ISO 3166-1 alpha-3 country code"
    )
    iso_numeric_code: Optional[str] = Field(
        default=None,
        max_length=3,
        description="ISO 3166-1 numeric country code"
    )
    
    # Información geográfica y cultural
    region: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Geographic region"
    )
    subregion: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Geographic subregion"
    )
    continent: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Continent"
    )
    
    # Información monetaria
    currency_code: Optional[str] = Field(
        default=None,
        max_length=3,
        description="ISO 4217 currency code"
    )
    currency_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Full currency name"
    )
    currency_symbol: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Currency symbol"
    )
    
    # Información temporal y localización
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary timezone"
    )
    capital_city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Capital city"
    )
    language_codes: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Language codes (comma separated)"
    )
    
    # Campos de control empresarial
    business_unit: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Business unit responsible"
    )
    regional_manager: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Regional manager contact"
    )
    technical_contact: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Technical contact"
    )
    launch_date: Optional[date] = Field(
        default=None,
        description="Market launch date"
    )
    market_priority: str = Field(
        default="MEDIUM",
        max_length=20,
        description="Market priority level"
    )
    
    # Estado y configuración
    is_active: bool = Field(default=True, description="Whether country is active")
    is_production_ready: bool = Field(
        default=False,
        description="Whether country is production ready"
    )
    supports_mobile_app: bool = Field(
        default=True,
        description="Whether country supports mobile app"
    )
    supports_web_app: bool = Field(
        default=True,
        description="Whether country supports web app"
    )
    
    # Configuración técnica
    default_locale: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Default locale (e.g., en-US, es-ES)"
    )
    date_format: str = Field(
        default="DD/MM/YYYY",
        max_length=20,
        description="Default date format"
    )
    number_format: str = Field(
        default="EUROPEAN",
        max_length=20,
        description="Number format preference"
    )
    
    # Metadatos de auditoría
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )
    created_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User who created this record"
    )
    updated_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User who last updated this record"
    )
    
    # Relationships
    app_mappings: List["AppEnvironmentCountryMapping"] = Relationship(back_populates="country")
    endpoints: List["ApplicationEndpoint"] = Relationship(back_populates="country")
    
    # === VALIDACIONES PYDANTIC (MATCHING DATABASE CONSTRAINTS) ===
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate country_code format"""
        if not v:
            raise ValueError('country_code is required')
        v = v.strip()
        if len(v) != 2:
            raise ValueError('country_code must be exactly 2 characters')
        if v != v.upper():
            raise ValueError('country_code must be UPPERCASE')
        if ' ' in v:
            raise ValueError('country_code cannot contain spaces')
        return v
    
    @field_validator('country_name')
    @classmethod
    def validate_country_name(cls, v: str) -> str:
        """Validate country_name"""
        if not v:
            raise ValueError('country_name is required')
        v = v.strip()
        if not (2 <= len(v) <= 255):
            raise ValueError('country_name must be between 2 and 255 characters')
        return v
    
    @field_validator('iso_alpha3_code')
    @classmethod
    def validate_iso_alpha3_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO alpha-3 code format"""
        if v is None:
            return v
        v = v.strip()
        if len(v) != 3:
            raise ValueError('iso_alpha3_code must be exactly 3 characters')
        if v != v.upper():
            raise ValueError('iso_alpha3_code must be UPPERCASE')
        return v
    
    @field_validator('currency_code')
    @classmethod
    def validate_currency_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate currency_code (ISO 4217)"""
        if v is None:
            return v
        v = v.strip()
        if len(v) != 3:
            raise ValueError('currency_code must be exactly 3 characters')
        if v != v.upper():
            raise ValueError('currency_code must be UPPERCASE')
        return v
    
    @field_validator('region')
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        """Validate region"""
        if v is None:
            return v
        valid_regions = {
            'Europe', 'North America', 'South America', 'Central America',
            'Asia', 'Africa', 'Oceania', 'Middle East'
        }
        if v not in valid_regions:
            raise ValueError(f'region must be one of: {", ".join(valid_regions)}')
        return v
    
    @field_validator('continent')
    @classmethod
    def validate_continent(cls, v: Optional[str]) -> Optional[str]:
        """Validate continent"""
        if v is None:
            return v
        valid_continents = {
            'Europe', 'North America', 'South America', 'Asia', 
            'Africa', 'Oceania', 'Antarctica'
        }
        if v not in valid_continents:
            raise ValueError(f'continent must be one of: {", ".join(valid_continents)}')
        return v
    
    @field_validator('market_priority')
    @classmethod
    def validate_market_priority(cls, v: str) -> str:
        """Validate market_priority"""
        if not v:
            v = "MEDIUM"  # Default value
        valid_priorities = {'LOW', 'MEDIUM', 'HIGH', 'STRATEGIC'}
        if v not in valid_priorities:
            raise ValueError(f'market_priority must be one of: {", ".join(valid_priorities)}')
        return v
    
    @field_validator('number_format')
    @classmethod
    def validate_number_format(cls, v: str) -> str:
        """Validate number_format"""
        if not v:
            v = "EUROPEAN"  # Default value
        valid_formats = {'EUROPEAN', 'AMERICAN', 'INDIAN', 'CUSTOM'}
        if v not in valid_formats:
            raise ValueError(f'number_format must be one of: {", ".join(valid_formats)}')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone format"""
        if v is None:
            return v
        if '/' not in v:
            raise ValueError('timezone must be in Continent/City format')
        return v
    
    @field_validator('default_locale')
    @classmethod
    def validate_default_locale(cls, v: Optional[str]) -> Optional[str]:
        """Validate locale format"""
        if v is None:
            return v
        if len(v) != 5 or v[2] != '-':
            raise ValueError('default_locale must be in xx-XX format (e.g., en-US)')
        return v
    
    @field_validator('regional_manager', 'technical_contact')
    @classmethod
    def validate_contact_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact field length"""
        if v is not None and len(v) > 255:
            raise ValueError('Contact field must be 255 characters or less')
        return v
    
    @field_validator('business_unit')
    @classmethod
    def validate_business_unit(cls, v: Optional[str]) -> Optional[str]:
        """Validate business_unit length"""
        if v is not None and len(v) > 100:
            raise ValueError('business_unit must be 100 characters or less')
        return v
    
    # === BUSINESS LOGIC METHODS ===
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return f"{self.country_name} ({self.country_code})"
    
    @property
    def is_strategic_market(self) -> bool:
        """Check if this is a strategic market"""
        return self.market_priority == 'STRATEGIC'
    
    @property
    def supports_apps(self) -> bool:
        """Check if country supports any app type"""
        return self.supports_mobile_app or self.supports_web_app
    
    @property
    def active_apps(self) -> List['Apps']:
        """
        Get list of applications actively deployed in this country
        
        Returns:
            List of Apps objects active in this country
        """
        return [
            mapping.application for mapping in self.app_mappings 
            if mapping.is_active and mapping.application.is_active
        ]
    
    @property
    def app_count(self) -> int:
        """
        Get count of active applications for this country
        
        Returns:
            Number of applications actively deployed in this country
        """
        return len([
            mapping for mapping in self.app_mappings 
            if mapping.is_active and mapping.application.is_active
        ])
    
    def get_full_locale_info(self) -> dict:
        """Get complete localization information"""
        return {
            "country_code": self.country_code,
            "locale": self.default_locale,
            "timezone": self.timezone,
            "currency_code": self.currency_code,
            "currency_symbol": self.currency_symbol,
            "date_format": self.date_format,
            "number_format": self.number_format,
            "language_codes": self.language_codes.split(',') if self.language_codes else []
        }
    
    def get_business_info(self) -> dict:
        """Get business and operational information"""
        return {
            "market_priority": self.market_priority,
            "business_unit": self.business_unit,
            "regional_manager": self.regional_manager,
            "technical_contact": self.technical_contact,
            "launch_date": self.launch_date,
            "is_production_ready": self.is_production_ready,
            "supports_mobile": self.supports_mobile_app,
            "supports_web": self.supports_web_app
        }
    
    def has_application(self, app_code: str) -> bool:
        """
        Check if a specific application is available in this country
        
        Args:
            app_code: Application code to check
            
        Returns:
            True if application is available in this country
        """
        return any(
            mapping.is_active and 
            mapping.application.is_active and 
            mapping.application.app_code == app_code
            for mapping in self.app_mappings
        )
    
    def get_launch_date_for_app(self, app_code: str) -> Optional[datetime]:
        """
        Get launch date for a specific application in this country
        
        Args:
            app_code: Application code
            
        Returns:
            Launch date if available, None otherwise
        """
        for mapping in self.app_mappings:
            if (mapping.application.app_code == app_code and 
                mapping.is_active):
                return mapping.launched_date
        return None
    
    def update_contacts(
        self, 
        regional_manager: Optional[str] = None,
        technical_contact: Optional[str] = None
    ) -> None:
        """Update contact information"""
        if regional_manager is not None:
            self.regional_manager = regional_manager
        if technical_contact is not None:
            self.technical_contact = technical_contact
        self.updated_at = datetime.now(timezone.utc)
    
    def promote_to_production(self, launch_date: Optional[date] = None) -> None:
        """Promote country to production ready"""
        self.is_production_ready = True
        if launch_date:
            self.launch_date = launch_date
        self.updated_at = datetime.now(timezone.utc)
    
    def set_market_priority(self, priority: str) -> None:
        """Set market priority with validation"""
        valid_priorities = {'LOW', 'MEDIUM', 'HIGH', 'STRATEGIC'}
        if priority not in valid_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(valid_priorities)}')
        self.market_priority = priority
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        priority_indicator = f" [{self.market_priority}]" if self.market_priority != "MEDIUM" else ""
        return f"<Country {self.country_code}: {self.country_name}{priority_indicator}>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.display_name
    
    @classmethod
    def create_sample_data(cls) -> List['Countries']:
        """
        Create sample data for testing and development
        
        Returns:
            List of sample Countries instances
        """
        return [
            cls(
                country_name="Romania",
                country_code="RO",
                iso_alpha3_code="ROU",
                region="Europe",
                continent="Europe",
                currency_code="RON",
                currency_name="Romanian Leu",
                timezone="Europe/Bucharest",
                capital_city="Bucharest",
                business_unit="Europe Operations",
                market_priority="HIGH",
                default_locale="ro-RO",
                is_production_ready=True
            ),
            cls(
                country_name="France",
                country_code="FR",
                iso_alpha3_code="FRA", 
                region="Europe",
                continent="Europe",
                currency_code="EUR",
                currency_name="Euro",
                currency_symbol="€",
                timezone="Europe/Paris",
                capital_city="Paris",
                business_unit="Europe Operations",
                market_priority="STRATEGIC",
                default_locale="fr-FR",
                is_production_ready=True
            ),
            cls(
                country_name="Colombia",
                country_code="CO",
                iso_alpha3_code="COL",
                region="South America",
                continent="South America",
                currency_code="COP",
                currency_name="Colombian Peso",
                timezone="America/Bogota",
                capital_city="Bogotá",
                business_unit="LATAM Operations",
                market_priority="STRATEGIC",
                default_locale="es-CO",
                is_production_ready=True
            ),
            cls(
                country_name="Mexico",
                country_code="MX",
                iso_alpha3_code="MEX",
                region="North America", 
                continent="North America",
                currency_code="MXN",
                currency_name="Mexican Peso",
                timezone="America/Mexico_City",
                capital_city="Mexico City",
                business_unit="LATAM Operations",
                market_priority="STRATEGIC",
                default_locale="es-MX",
                is_production_ready=True
            )
        ]
