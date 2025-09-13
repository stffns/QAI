"""
Countries Repository - Repository implementation for Countries model

Repositorio empresarial con:
- Búsquedas por prioridad de mercado
- Gestión de unidades de negocio  
- Consultas de capacidades de aplicaciones
- Estadísticas regionales y de negocio
- Validaciones de ISO compliance
"""
from typing import List, Optional, Dict
from sqlmodel import Session, select, text
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone, date

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError, InvalidEntityError
from ..models.countries import Countries

class CountriesRepository(BaseRepository[Countries]):
    """
    Repository for Countries operations with enterprise capabilities
    
    Provides specialized queries for country management including:
    - Market priority filtering
    - Business unit management
    - App capabilities queries
    - Geographic and business statistics
    - ISO compliance validation
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Countries)
    
    # === BÚSQUEDAS BÁSICAS ===
    
    def get_by_code(self, country_code: str) -> Optional[Countries]:
        """Find country by unique country code"""
        statement = select(Countries).where(Countries.country_code == country_code.upper())
        return self.session.exec(statement).first()
    
    def get_by_iso_alpha3(self, iso_alpha3_code: str) -> Optional[Countries]:
        """Find country by ISO 3166-1 alpha-3 code"""
        statement = select(Countries).where(Countries.iso_alpha3_code == iso_alpha3_code.upper())
        return self.session.exec(statement).first()
    
    def get_by_region(self, region: str) -> List[Countries]:
        """Get all countries in a specific region"""
        statement = select(Countries).where(Countries.region == region)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_by_continent(self, continent: str) -> List[Countries]:
        """Get all countries in a specific continent"""
        statement = select(Countries).where(Countries.continent == continent)
        result = self.session.exec(statement).all()
        return list(result)
    
    # === BÚSQUEDAS EMPRESARIALES ===
    
    def get_by_market_priority(self, priority: str) -> List[Countries]:
        """Get countries by market priority"""
        valid_priorities = {'LOW', 'MEDIUM', 'HIGH', 'STRATEGIC'}
        if priority not in valid_priorities:
            raise InvalidEntityError("Invalid priority", [f"Priority must be one of: {', '.join(valid_priorities)}"])
        
        statement = select(Countries).where(Countries.market_priority == priority)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_strategic_markets(self) -> List[Countries]:
        """Get all strategic market countries"""
        return self.get_by_market_priority('STRATEGIC')
    
    def get_by_business_unit(self, business_unit: str) -> List[Countries]:
        """Get countries by business unit"""
        statement = select(Countries).where(Countries.business_unit == business_unit)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_production_ready_countries(self) -> List[Countries]:
        """Get countries that are production ready"""
        statement = select(Countries).where(Countries.is_production_ready == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_with_mobile_support(self) -> List[Countries]:
        """Get countries that support mobile apps"""
        statement = select(Countries).where(Countries.supports_mobile_app == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_with_web_support(self) -> List[Countries]:
        """Get countries that support web apps"""
        statement = select(Countries).where(Countries.supports_web_app == True)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_with_launch_date(self) -> List[Countries]:
        """Get countries that have a launch date set"""
        statement = select(Countries).where(Countries.launch_date != None)
        result = self.session.exec(statement).all()
        return list(result)
    
    # === BÚSQUEDAS POR LOCALIZACIÓN ===
    
    def search_by_name(self, name_pattern: str) -> List[Countries]:
        """Search countries by name pattern (case-insensitive)"""
        statement = select(Countries).where(func.lower(Countries.country_name).contains(func.lower(name_pattern)))
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_by_currency(self, currency_code: str) -> List[Countries]:
        """Find countries using a specific currency"""
        statement = select(Countries).where(Countries.currency_code == currency_code.upper())
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_by_timezone(self, timezone: str) -> List[Countries]:
        """Find countries in a specific timezone"""
        statement = select(Countries).where(Countries.timezone == timezone)
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_countries_by_locale(self, locale: str) -> List[Countries]:
        """Find countries using a specific locale"""
        statement = select(Countries).where(Countries.default_locale == locale)
        result = self.session.exec(statement).all()
        return list(result)
    
    # === MÉTODOS DE LISTADO ===
    
    def get_all_regions(self) -> List[str]:
        """Get list of all unique regions"""
        statement = select(Countries.region).distinct()
        result = self.session.exec(statement).all()
        return [r for r in result if r is not None]
    
    def get_all_continents(self) -> List[str]:
        """Get list of all unique continents"""
        statement = select(Countries.continent).distinct()
        result = self.session.exec(statement).all()
        return [c for c in result if c is not None]
    
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
    
    def get_all_business_units(self) -> List[str]:
        """Get list of all unique business units"""
        statement = select(Countries.business_unit).distinct()
        result = self.session.exec(statement).all()
        return [bu for bu in result if bu is not None]
    
    def get_all_market_priorities(self) -> List[str]:
        """Get list of all market priorities in use"""
        statement = select(Countries.market_priority).distinct()
        result = self.session.exec(statement).all()
        return list(result)
    
    # === VALIDACIONES Y VERIFICACIONES ===
    
    def exists_by_code(self, country_code: str) -> bool:
        """Check if a country exists with the given code"""
        statement = select(Countries.id).where(Countries.country_code == country_code.upper())
        result = self.session.exec(statement).first()
        return result is not None
    
    def exists_by_iso_alpha3(self, iso_alpha3_code: str) -> bool:
        """Check if a country exists with the given ISO alpha-3 code"""
        statement = select(Countries.id).where(Countries.iso_alpha3_code == iso_alpha3_code.upper())
        result = self.session.exec(statement).first()
        return result is not None
    
    def validate_iso_codes(self, country_code: str, iso_alpha3_code: Optional[str] = None) -> bool:
        """Validate ISO code format and uniqueness"""
        if len(country_code) != 2 or not country_code.isupper():
            return False
        
        if iso_alpha3_code and (len(iso_alpha3_code) != 3 or not iso_alpha3_code.isupper()):
            return False
        
        return True
    
    # === OPERACIONES CRUD EMPRESARIALES ===
    
    def create_country(self, 
                      country_code: str, 
                      country_name: str,
                      iso_alpha3_code: Optional[str] = None,
                      region: Optional[str] = None,
                      continent: Optional[str] = None,
                      currency_code: Optional[str] = None,
                      timezone: Optional[str] = None,
                      business_unit: Optional[str] = None,
                      market_priority: str = "MEDIUM",
                      created_by: Optional[str] = None) -> Countries:
        """Create a new country with enterprise validation"""
        
        # Normalize codes
        country_code = country_code.upper()
        if iso_alpha3_code:
            iso_alpha3_code = iso_alpha3_code.upper()
        if currency_code:
            currency_code = currency_code.upper()
        
        # Validation
        if self.exists_by_code(country_code):
            raise DuplicateEntityError("Countries", "country_code", country_code)
        
        if iso_alpha3_code and self.exists_by_iso_alpha3(iso_alpha3_code):
            raise DuplicateEntityError("Countries", "iso_alpha3_code", iso_alpha3_code)
        
        if not self.validate_iso_codes(country_code, iso_alpha3_code):
            raise InvalidEntityError("Invalid ISO code format", ["Country code must be 2 uppercase chars, ISO alpha-3 must be 3 uppercase chars"])
        
        country = Countries(
            country_code=country_code,
            country_name=country_name,
            iso_alpha3_code=iso_alpha3_code,
            region=region,
            continent=continent,
            currency_code=currency_code,
            timezone=timezone,
            business_unit=business_unit,
            market_priority=market_priority,
            created_by=created_by
        )
        
        return self.save(country)
    
    def update_market_priority(self, country_code: str, priority: str, updated_by: Optional[str] = None) -> Optional[Countries]:
        """Update country market priority"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.set_market_priority(priority)
        if updated_by:
            country.updated_by = updated_by
        
        return self.save(country)
    
    def update_business_unit(self, country_code: str, business_unit: str, updated_by: Optional[str] = None) -> Optional[Countries]:
        """Update country business unit"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.business_unit = business_unit
        country.updated_at = datetime.now(timezone.utc)
        if updated_by:
            country.updated_by = updated_by
        
        return self.save(country)
    
    def promote_to_production(self, country_code: str, launch_date: Optional[date] = None, updated_by: Optional[str] = None) -> Optional[Countries]:
        """Promote country to production ready"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.promote_to_production(launch_date)
        if updated_by:
            country.updated_by = updated_by
        
        return self.save(country)
    
    def update_contacts(self, 
                       country_code: str,
                       regional_manager: Optional[str] = None,
                       technical_contact: Optional[str] = None,
                       updated_by: Optional[str] = None) -> Optional[Countries]:
        """Update country contact information"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        country.update_contacts(regional_manager, technical_contact)
        if updated_by:
            country.updated_by = updated_by
        
        return self.save(country)
    
    def update_app_support(self, 
                          country_code: str,
                          supports_mobile: Optional[bool] = None,
                          supports_web: Optional[bool] = None,
                          updated_by: Optional[str] = None) -> Optional[Countries]:
        """Update country application support"""
        country = self.get_by_code(country_code)
        if not country:
            return None
        
        if supports_mobile is not None:
            country.supports_mobile_app = supports_mobile
        if supports_web is not None:
            country.supports_web_app = supports_web
        
        country.updated_at = datetime.now(timezone.utc)
        if updated_by:
            country.updated_by = updated_by
        
        return self.save(country)
    
    # === ESTADÍSTICAS EMPRESARIALES ===
    
    def count_countries_by_region(self) -> Dict[str, int]:
        """Count countries grouped by region"""
        statement = select(
            Countries.region,
            func.count(text("1")).label("count")
        ).group_by(Countries.region)
        
        result = self.session.exec(statement).all()
        return {row[0]: row[1] for row in result if row[0] is not None}
    
    def count_countries_by_market_priority(self) -> Dict[str, int]:
        """Count countries grouped by market priority"""
        statement = select(
            Countries.market_priority,
            func.count(text("1")).label("count")
        ).group_by(Countries.market_priority)
        
        result = self.session.exec(statement).all()
        return {row[0]: row[1] for row in result}
    
    def count_countries_by_business_unit(self) -> Dict[str, int]:
        """Count countries grouped by business unit"""
        statement = select(
            Countries.business_unit,
            func.count(text("1")).label("count")
        ).group_by(Countries.business_unit)
        
        result = self.session.exec(statement).all()
        return {row[0]: row[1] for row in result if row[0] is not None}
    
    def get_countries_summary(self) -> Dict:
        """Get comprehensive summary statistics for countries"""
        total_statement = select(func.count(text("1"))).select_from(Countries)
        active_statement = select(func.count(text("1"))).select_from(Countries).where(Countries.is_active == True)
        production_statement = select(func.count(text("1"))).select_from(Countries).where(Countries.is_production_ready == True)
        
        # Count distinct values
        regions_statement = select(func.count(func.distinct(Countries.region))).where(Countries.region != None)
        currencies_statement = select(func.count(func.distinct(Countries.currency_code))).where(Countries.currency_code != None)
        timezones_statement = select(func.count(func.distinct(Countries.timezone))).where(Countries.timezone != None)
        business_units_statement = select(func.count(func.distinct(Countries.business_unit))).where(Countries.business_unit != None)
        
        # Execute queries
        total = self.session.exec(total_statement).one()
        active = self.session.exec(active_statement).one()
        production = self.session.exec(production_statement).one()
        regions = self.session.exec(regions_statement).one()
        currencies = self.session.exec(currencies_statement).one()
        timezones = self.session.exec(timezones_statement).one()
        business_units = self.session.exec(business_units_statement).one()
        
        return {
            "total_countries": total,
            "active_countries": active,
            "inactive_countries": total - active,
            "production_ready": production,
            "unique_regions": regions,
            "unique_currencies": currencies,
            "unique_timezones": timezones,
            "unique_business_units": business_units,
            "countries_by_region": self.count_countries_by_region(),
            "countries_by_priority": self.count_countries_by_market_priority(),
            "countries_by_business_unit": self.count_countries_by_business_unit()
        }
    
    def get_business_dashboard_data(self) -> Dict:
        """Get business-focused dashboard data"""
        strategic_count = len(self.get_strategic_markets())
        production_ready_count = len(self.get_production_ready_countries())
        mobile_support_count = len(self.get_countries_with_mobile_support())
        web_support_count = len(self.get_countries_with_web_support())
        
        return {
            "strategic_markets": strategic_count,
            "production_ready": production_ready_count,
            "mobile_support": mobile_support_count,
            "web_support": web_support_count,
            "priority_distribution": self.count_countries_by_market_priority(),
            "business_unit_distribution": self.count_countries_by_business_unit(),
            "regional_distribution": self.count_countries_by_region()
        }
    
    def get_active_countries(self) -> List[Countries]:
        """Get all active countries"""
        statement = select(Countries).where(Countries.is_active == True)
        result = self.session.exec(statement).all()
        return list(result)

    def get_inactive_countries(self) -> List[Countries]:
        """Get all inactive countries"""
        statement = select(Countries).where(Countries.is_active == False)
        result = self.session.exec(statement).all()
        return list(result)
