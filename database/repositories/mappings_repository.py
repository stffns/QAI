"""
Mappings Repository - Repository implementation for ApplicationCountryMapping model
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select, text
from sqlalchemy import func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.mappings import ApplicationCountryMapping

class MappingsRepository(BaseRepository[ApplicationCountryMapping]):
    """
    Repository for ApplicationCountryMapping operations
    
    Provides specialized queries for managing app-country relationships including:
    - Finding mappings by app or country
    - Launch date tracking
    - Deployment status management
    """
    
    def __init__(self, session: Session):
        super().__init__(session, ApplicationCountryMapping)
    
    def get_by_app_and_country(self, application_id: int, country_id: int) -> Optional[ApplicationCountryMapping]:
        """Find mapping by application and country IDs"""
        statement = select(ApplicationCountryMapping).where(
            ApplicationCountryMapping.application_id == application_id,
            ApplicationCountryMapping.country_id == country_id
        )
        return self.session.exec(statement).first()
    
    def get_mappings_by_app(self, application_id: int) -> List[ApplicationCountryMapping]:
        """Get all country mappings for a specific app"""
        statement = select(ApplicationCountryMapping).where(ApplicationCountryMapping.application_id == application_id)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_mappings_by_country(self, country_id: int) -> List[ApplicationCountryMapping]:
        """Get all app mappings for a specific country"""
        statement = select(ApplicationCountryMapping).where(ApplicationCountryMapping.country_id == country_id)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_active_mappings(self) -> List[ApplicationCountryMapping]:
        """Get all active app-country mappings"""
        statement = select(ApplicationCountryMapping).where(ApplicationCountryMapping.is_active == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_mappings_with_launch_date(self) -> List[ApplicationCountryMapping]:
        """Get mappings that have a launch date set"""
        statement = select(ApplicationCountryMapping).where(ApplicationCountryMapping.launched_date != None)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_mappings_with_deprecation_date(self) -> List[ApplicationCountryMapping]:
        """Get mappings that have a deprecation date set"""
        statement = select(ApplicationCountryMapping).where(ApplicationCountryMapping.deprecated_date != None)
        result = self.session.exec(statement).all()
        return list(result)
    
    def exists_mapping(self, application_id: int, country_id: int) -> bool:
        """Check if a mapping exists between app and country"""
        statement = select(ApplicationCountryMapping.mapping_id).where(
            ApplicationCountryMapping.application_id == application_id,
            ApplicationCountryMapping.country_id == country_id
        )
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_mapping(self, application_id: int, country_id: int, 
                      launched_date: Optional[datetime] = None) -> ApplicationCountryMapping:
        """Create a new app-country mapping with validation"""
        if self.exists_mapping(application_id, country_id):
            raise DuplicateEntityError("ApplicationCountryMapping", "application_id+country_id", f"{application_id}+{country_id}")
        
        mapping = ApplicationCountryMapping(
            application_id=application_id,
            country_id=country_id,
            launched_date=launched_date
        )
        
        return self.save(mapping)
    
    def activate_mapping(self, application_id: int, country_id: int) -> bool:
        """Activate an app-country mapping"""
        mapping = self.get_by_app_and_country(application_id, country_id)
        if not mapping:
            return False
        
        mapping.is_active = True
        self.save(mapping)
        return True
    
    def deactivate_mapping(self, application_id: int, country_id: int) -> bool:
        """Deactivate an app-country mapping"""
        mapping = self.get_by_app_and_country(application_id, country_id)
        if not mapping:
            return False
        
        mapping.is_active = False
        self.save(mapping)
        return True
    
    def deprecate_mapping(self, application_id: int, country_id: int, deprecation_date: Optional[datetime] = None) -> bool:
        """Set deprecation date for an app-country mapping"""
        mapping = self.get_by_app_and_country(application_id, country_id)
        if not mapping:
            return False
        
        mapping.deprecated_date = deprecation_date or datetime.now(timezone.utc)
        self.save(mapping)
        return True
    
    def get_mappings_summary(self) -> dict:
        """Get summary statistics for mappings"""
        total_statement = select(func.count(text("1"))).select_from(ApplicationCountryMapping)
        active_statement = select(func.count(text("1"))).select_from(ApplicationCountryMapping).where(
            ApplicationCountryMapping.is_active == True
        )
        with_launch_statement = select(func.count(text("1"))).select_from(ApplicationCountryMapping).where(
            ApplicationCountryMapping.launched_date != None
        )
        with_deprecation_statement = select(func.count(text("1"))).select_from(ApplicationCountryMapping).where(
            ApplicationCountryMapping.deprecated_date != None
        )
        unique_apps_statement = select(func.count(func.distinct(ApplicationCountryMapping.application_id)))
        unique_countries_statement = select(func.count(func.distinct(ApplicationCountryMapping.country_id)))
        
        total = self.session.exec(total_statement).one()
        active = self.session.exec(active_statement).one()
        with_launch = self.session.exec(with_launch_statement).one()
        with_deprecation = self.session.exec(with_deprecation_statement).one()
        unique_apps = self.session.exec(unique_apps_statement).one()
        unique_countries = self.session.exec(unique_countries_statement).one()
        
        return {
            "total_mappings": total,
            "active_mappings": active,
            "inactive_mappings": total - active,
            "mappings_with_launch_date": with_launch,
            "mappings_with_deprecation_date": with_deprecation,
            "unique_apps": unique_apps,
            "unique_countries": unique_countries,
            "avg_countries_per_app": round(total / unique_apps, 2) if unique_apps > 0 else 0,
            "avg_apps_per_country": round(total / unique_countries, 2) if unique_countries > 0 else 0
        }
