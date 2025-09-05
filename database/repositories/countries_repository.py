"""
Countries Repository - Repository implementation for Countries model
"""
from typing import List, Optional
from sqlmodel import Session, select, text
from sqlalchemy import func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.countries import Countries

class CountriesRepository(BaseRepository[Countries]):
    """
    Repository for Countries operations
    
    Provides specialized queries for country management including:
    - Finding countries by code
    - Regional filtering
    - App availability queries
    - Geographic statistics
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Countries)
    
    def get_by_code(self, country_code: str) -> Optional[Countries]:
        """Find country by unique country code"""
        statement = select(Countries).where(Countries.country_code == country_code)
        return self.session.exec(statement).first()
    
    def get_by_region(self, region: str) -> List[Countries]:
        """Get all countries in a specific region"""
        statement = select(Countries).where(Countries.region == region)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_all_regions(self) -> List[str]:
        """Get list of all unique regions"""
        statement = select(Countries.region).distinct()
        result = self.session.exec(statement).all()
        return [r for r in result if r is not None]
    
    def search_by_name(self, name_pattern: str) -> List[Countries]:
        """Search countries by name pattern (case-insensitive)"""
        statement = select(Countries).where(func.lower(Countries.country_name).contains(func.lower(name_pattern)))
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_by_currency(self, currency_code: str) -> List[Countries]:
        """Find countries using a specific currency"""
        statement = select(Countries).where(Countries.currency_code == currency_code)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_by_timezone(self, timezone: str) -> List[Countries]:
        """Find countries in a specific timezone"""
        statement = select(Countries).where(Countries.timezone == timezone)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_all_currencies(self) -> List[str]:
        """Get list of all unique currency codes"""
        statement = select(Countries.currency_code).distinct()
        result = self.session.exec(statement).all()
        return [c for c in result if c is not None]
    
    def get_all_timezones(self) -> List[str]:
        """Get list of all unique timezones"""
        statement = select(Countries.timezone).distinct()
        result = self.session.exec(statement).all()
        return [t for t in result if t is not None]
    
    def count_countries_by_region(self) -> dict:
        """Count countries grouped by region"""
        statement = select(
            Countries.region,
            func.count(text("1")).label("count")
        ).group_by(Countries.region)
        
        result = self.session.exec(statement).all()
        return {row[0]: row[1] for row in result if row[0] is not None}
    
    def exists_by_code(self, country_code: str) -> bool:
        """Check if a country exists with the given code"""
        statement = select(Countries.id).where(Countries.country_code == country_code)
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_country(self, country_code: str, country_name: str, 
                      region: Optional[str] = None,
                      currency_code: Optional[str] = None,
                      timezone: Optional[str] = None) -> Countries:
        """Create a new country with validation"""
        if self.exists_by_code(country_code):
            raise DuplicateEntityError("Countries", "country_code", country_code)
        
        country = Countries(
            country_code=country_code,
            country_name=country_name,
            region=region,
            currency_code=currency_code,
            timezone=timezone
        )
        
        return self.save(country)
    
    def update_country_region(self, country_code: str, region: str) -> Optional[Countries]:
        """Update country region"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.region = region
        return self.save(country)
    
    def update_country_currency(self, country_code: str, currency_code: str) -> Optional[Countries]:
        """Update country currency code"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.currency_code = currency_code
        return self.save(country)
    
    def update_country_timezone(self, country_code: str, timezone: str) -> Optional[Countries]:
        """Update country timezone"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.timezone = timezone
        return self.save(country)
    
    def get_countries_summary(self) -> dict:
        """Get summary statistics for countries"""
        total_statement = select(func.count(text("1"))).select_from(Countries)
        active_statement = select(func.count(text("1"))).select_from(Countries).where(Countries.is_active == True)
        
        # Count distinct regions
        regions_statement = select(func.count(func.distinct(Countries.region))).where(Countries.region != None)
        
        # Count distinct currencies  
        currencies_statement = select(func.count(func.distinct(Countries.currency_code))).where(Countries.currency_code != None)
        
        # Count distinct timezones
        timezones_statement = select(func.count(func.distinct(Countries.timezone))).where(Countries.timezone != None)
        
        total = self.session.exec(total_statement).one()
        active = self.session.exec(active_statement).one()
        regions = self.session.exec(regions_statement).one()
        currencies = self.session.exec(currencies_statement).one()
        timezones = self.session.exec(timezones_statement).one()
        
        return {
            "total_countries": total,
            "active_countries": active,
            "inactive_countries": total - active,
            "unique_regions": regions,
            "unique_currencies": currencies,
            "unique_timezones": timezones,
            "countries_by_region": self.count_countries_by_region()
        }
