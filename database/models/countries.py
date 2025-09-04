"""
Countries Master Model - SQLModel model for countries
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .apps_master import AppsMaster
    from .mappings import ApplicationCountryMapping

class CountriesMaster(SQLModel, table=True):
    """
    Countries Master table model
    
    Represents the catalog of countries and regions where applications can be deployed.
    Each country can have multiple applications available.
    """
    __tablename__ = 'countries_master'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Core country data
    country_name: str = Field(max_length=255, description="Full country name")
    country_code: str = Field(max_length=10, unique=True, description="ISO country code")
    region: Optional[str] = Field(default=None, max_length=100, description="Geographic region")
    currency_code: Optional[str] = Field(default=None, max_length=10, description="Currency code")
    timezone: Optional[str] = Field(default=None, max_length=50, description="Primary timezone")
    
    # Status and metadata
    is_active: bool = Field(default=True, description="Whether the country is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    app_mappings: List["ApplicationCountryMapping"] = Relationship(back_populates="country")
    
    def __repr__(self) -> str:
        """String representation of the Countries Master record"""
        return f"<CountriesMaster(id={self.id}, code='{self.country_code}', name='{self.country_name}', active={self.is_active})>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
        return f"{self.country_name} ({self.country_code})"
    
    @property
    def active_apps(self) -> List['AppsMaster']:
        """
        Get list of applications actively deployed in this country
        
        Returns:
            List of AppsMaster objects active in this country
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
    
    def get_apps_by_region(self) -> List['AppsMaster']:
        """
        Get applications available in the same region as this country
        
        Returns:
            List of applications available in the same region
        """
        if not self.region:
            return self.active_apps
        
        # This would require a more complex query in practice
        # For now, return active apps for this country
        return self.active_apps
    
    @classmethod
    def create_sample_data(cls) -> List['CountriesMaster']:
        """
        Create sample data for testing and development
        
        Returns:
            List of sample CountriesMaster instances
        """
        return [
            cls(
                country_name="Romania",
                country_code="RO",
                region="Europe",
                currency_code="RON",
                timezone="Europe/Bucharest"
            ),
            cls(
                country_name="France",
                country_code="FR", 
                region="Europe",
                currency_code="EUR",
                timezone="Europe/Paris"
            ),
            cls(
                country_name="Belgium",
                country_code="BE",
                region="Europe", 
                currency_code="EUR",
                timezone="Europe/Brussels"
            ),
            cls(
                country_name="United States",
                country_code="US",
                region="North America",
                currency_code="USD",
                timezone="America/New_York"
            ),
            cls(
                country_name="Singapore",
                country_code="SG",
                region="Asia",
                currency_code="SGD", 
                timezone="Asia/Singapore"
            )
        ]
