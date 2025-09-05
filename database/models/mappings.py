"""
Application Country Mapping Model - SQLModel model for app-country relationships
"""
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .apps import Apps
    from .countries import Countries

class ApplicationCountryMapping(SQLModel, table=True):
    """
    Application Country Mapping table model
    
    Represents the many-to-many relationship between applications and countries.
    Tracks which applications are available in which countries, including
    launch dates and deployment status.
    """
    __tablename__ = 'application_country_mapping'
    
    # Primary key
    mapping_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign keys
    application_id: int = Field(foreign_key="apps_master.id", description="Reference to application")
    country_id: int = Field(foreign_key="countries_master.id", description="Reference to country")
    
    # Deployment status
    is_active: bool = Field(default=True, description="Whether this mapping is active")
    launched_date: Optional[datetime] = Field(default=None, description="When the app was launched in this country")
    deprecated_date: Optional[datetime] = Field(default=None, description="When the app was deprecated in this country")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    application: "Apps" = Relationship(back_populates="country_mappings")
    country: "Countries" = Relationship(back_populates="app_mappings")
    
    def __repr__(self) -> str:
        """String representation of the mapping record"""
        return f"<ApplicationCountryMapping(id={self.mapping_id}, app_id={self.application_id}, country_id={self.country_id}, active={self.is_active})>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        app_name = self.application.app_code if self.application else f"App#{self.application_id}"
        country_name = self.country.country_code if self.country else f"Country#{self.country_id}"
        status = "Active" if self.is_active else "Inactive"
        return f"{app_name} → {country_name} ({status})"
    
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
        Calculate how long the app has been deployed in this country
        
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
    
    def deprecate(self, deprecation_date: Optional[datetime] = None) -> None:
        """
        Mark this mapping as deprecated
        
        Args:
            deprecation_date: When to deprecate (default: now)
        """
        self.deprecated_date = deprecation_date or datetime.now(timezone.utc)
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def reactivate(self) -> None:
        """
        Reactivate this mapping (remove deprecation)
        """
        self.deprecated_date = None
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    @classmethod
    def create_sample_data(cls, apps: list, countries: list) -> list:
        """
        Create sample mapping data for testing and development
        
        Args:
            apps: List of AppsMaster instances
            countries: List of CountriesMaster instances
            
        Returns:
            List of sample ApplicationCountryMapping instances
        """
        mappings = []
        
        # EVA in multiple European countries
        eva_app = next((app for app in apps if app.app_code == "EVA"), None)
        if eva_app:
            for country in countries:
                if country.region == "Europe":
                    mappings.append(cls(
                        application_id=eva_app.id,
                        country_id=country.id,
                        launched_date=datetime(2024, 1, 15),
                        is_active=True
                    ))
        
        # ONEAPP in all countries
        oneapp = next((app for app in apps if app.app_code == "ONEAPP"), None)
        if oneapp:
            for country in countries:
                launch_dates = {
                    "RO": datetime(2023, 6, 1),
                    "FR": datetime(2023, 8, 15), 
                    "BE": datetime(2023, 9, 1),
                    "US": datetime(2024, 2, 1),
                    "SG": datetime(2024, 3, 15)
                }
                mappings.append(cls(
                    application_id=oneapp.id,
                    country_id=country.id,
                    launched_date=launch_dates.get(country.country_code, datetime(2024, 1, 1)),
                    is_active=True
                ))
        
        # MOBILE only in some countries
        mobile_app = next((app for app in apps if app.app_code == "MOBILE"), None)
        if mobile_app:
            mobile_countries = ["RO", "FR", "US"]
            for country in countries:
                if country.country_code in mobile_countries:
                    mappings.append(cls(
                        application_id=mobile_app.id,
                        country_id=country.id,
                        launched_date=datetime(2023, 12, 1),
                        is_active=True
                    ))
        
        return mappings
