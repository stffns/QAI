"""
Apps Model - SQLModel model for applications
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .countries import Countries
    from .mappings import ApplicationCountryMapping

class Apps(SQLModel, table=True):
    """
    Applications Master table model
    
    Represents the main catalog of applications in the QA Intelligence system.
    Each application can be deployed across multiple countries.
    """
    __tablename__ = 'apps_master'
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Core application data
    app_code: str = Field(max_length=50, unique=True, description="Unique application code")
    app_name: str = Field(max_length=255, description="Display name of the application")
    description: Optional[str] = Field(default=None, description="Detailed description of the application")
    base_url_template: Optional[str] = Field(default=None, max_length=500, description="URL template for the application")
    
    # Status and metadata
    is_active: bool = Field(default=True, description="Whether the application is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    country_mappings: List["ApplicationCountryMapping"] = Relationship(back_populates="application")
    
    def __repr__(self) -> str:
        """String representation of the Apps record"""
        return f"<Apps(id={self.id}, code='{self.app_code}', name='{self.app_name}', active={self.is_active})>"
    
    def __str__(self) -> str:
        """User-friendly string representation"""
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
                base_url_template="https://eva.{country}.company.com"
            ),
            cls(
                app_code="ONEAPP", 
                app_name="OneApp Platform",
                description="Unified platform for all company services",
                base_url_template="https://oneapp.{country}.company.com"
            ),
            cls(
                app_code="MOBILE",
                app_name="Mobile Banking",
                description="Mobile banking application for customers",
                base_url_template="https://mobile.{country}.company.com"
            )
        ]
