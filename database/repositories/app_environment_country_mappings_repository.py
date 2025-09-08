"""
App Environment Country Mappings Repository - Simplified implementation
"""
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_
from sqlalchemy import func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.app_environment_country_mappings import AppEnvironmentCountryMapping


class AppEnvironmentCountryMappingRepository(BaseRepository[AppEnvironmentCountryMapping]):
    """
    Repository for App Environment Country Mappings operations
    
    Provides basic CRUD and specialized queries for unified app-environment-country management
    """
    
    def __init__(self, session: Session):
        super().__init__(session, AppEnvironmentCountryMapping)
    
    def get_by_combination(self, app_id: int, env_id: int, country_id: int) -> Optional[AppEnvironmentCountryMapping]:
        """
        Find mapping by the combination of app-environment-country IDs
        
        Args:
            app_id: Application ID
            env_id: Environment ID 
            country_id: Country ID
            
        Returns:
            Mapping if found, None otherwise
        """
        statement = select(AppEnvironmentCountryMapping).where(
            and_(
                AppEnvironmentCountryMapping.application_id == app_id,
                AppEnvironmentCountryMapping.environment_id == env_id,
                AppEnvironmentCountryMapping.country_id == country_id,
                AppEnvironmentCountryMapping.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_active_mappings(self) -> List[AppEnvironmentCountryMapping]:
        """Get all currently active mappings"""
        statement = select(AppEnvironmentCountryMapping).where(
            AppEnvironmentCountryMapping.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_by_application_id(self, app_id: int) -> List[AppEnvironmentCountryMapping]:
        """
        Get all mappings for a specific application ID
        
        Args:
            app_id: Application ID
            
        Returns:
            List of mappings for the application
        """
        statement = select(AppEnvironmentCountryMapping).where(
            and_(
                AppEnvironmentCountryMapping.application_id == app_id,
                AppEnvironmentCountryMapping.is_active == True
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_configuration(self, app_id: int, env_id: int, country_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete configuration for testing a specific combination
        
        Args:
            app_id: Application ID
            env_id: Environment ID
            country_id: Country ID
            
        Returns:
            Configuration dictionary if mapping exists, None otherwise
        """
        mapping = self.get_by_combination(app_id, env_id, country_id)
        return mapping.full_configuration if mapping else None
    
    def get_base_url(self, app_id: int, env_id: int, country_id: int) -> Optional[str]:
        """
        Get base URL for a specific combination (convenience method for testing tools)
        
        Args:
            app_id: Application ID
            env_id: Environment ID
            country_id: Country ID
            
        Returns:
            Base URL if mapping exists, None otherwise
        """
        mapping = self.get_by_combination(app_id, env_id, country_id)
        return mapping.base_url if mapping else None
    
    def exists_combination(self, app_id: int, env_id: int, country_id: int) -> bool:
        """Check if a combination exists"""
        statement = select(AppEnvironmentCountryMapping.id).where(
            and_(
                AppEnvironmentCountryMapping.application_id == app_id,
                AppEnvironmentCountryMapping.environment_id == env_id,
                AppEnvironmentCountryMapping.country_id == country_id
            )
        )
        result = self.session.exec(statement).first()
        return result is not None
    
    def create_mapping(self, app_id: int, env_id: int, country_id: int, 
                      base_url: str, **kwargs) -> AppEnvironmentCountryMapping:
        """
        Create a new mapping with validation for unique combinations
        
        Args:
            app_id: Application ID
            env_id: Environment ID
            country_id: Country ID
            base_url: Base URL for the combination
            **kwargs: Additional mapping parameters
            
        Returns:
            Created mapping
            
        Raises:
            DuplicateEntityError: If combination already exists
        """
        if self.exists_combination(app_id, env_id, country_id):
            raise DuplicateEntityError(
                "AppEnvironmentCountryMapping",
                "combination",
                f"app_id={app_id}, env_id={env_id}, country_id={country_id}"
            )
        
        mapping = AppEnvironmentCountryMapping(
            application_id=app_id,
            environment_id=env_id,
            country_id=country_id,
            base_url=base_url,
            **kwargs
        )
        
        return self.save(mapping)
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_
from sqlalchemy import func

from .base import BaseRepository
from .exceptions import EntityNotFoundError, DuplicateEntityError
from ..models.app_environment_country_mappings import AppEnvironmentCountryMapping


class AppEnvironmentCountryMappingRepository(BaseRepository[AppEnvironmentCountryMapping]):
    """
    Repository for App Environment Country Mappings operations
    
    Provides specialized queries for unified app-environment-country management:
    - Finding valid combinations by app/environment/country codes
    - Configuration retrieval for testing
    - Active deployment queries
    - Performance SLA validation
    """
    
    def __init__(self, session: Session):
        super().__init__(session, AppEnvironmentCountryMapping)
    
    def get_by_combination(self, app_id: int, env_id: int, country_id: int) -> Optional[AppEnvironmentCountryMapping]:
        """
        Find mapping by the combination of app-environment-country IDs
        
        Args:
            app_id: Application ID
            env_id: Environment ID 
            country_id: Country ID
            
        Returns:
            Mapping if found, None otherwise
        """
        statement = select(AppEnvironmentCountryMapping).where(
            and_(
                AppEnvironmentCountryMapping.application_id == app_id,
                AppEnvironmentCountryMapping.environment_id == env_id,
                AppEnvironmentCountryMapping.country_id == country_id,
                AppEnvironmentCountryMapping.is_active == True
            )
        )
        return self.session.exec(statement).first()
    
    def get_by_combination_codes(self, app_code: str, env_code: str, country_code: str) -> Optional[AppEnvironmentCountryMapping]:
        """
        Find mapping by app-environment-country codes (convenience method)
        
        Args:
            app_code: Application code (e.g., "EVA")
            env_code: Environment code (e.g., "STA") 
            country_code: Country code (e.g., "RO")
            
        Returns:
            Mapping if found, None otherwise
        """
        # First get the IDs from the codes
        from .apps_repository import AppsRepository
        from .countries_repository import CountriesRepository
        
        apps_repo = AppsRepository(self.session)
        countries_repo = CountriesRepository(self.session)
        
        app = apps_repo.get_by_code(app_code)
        country = countries_repo.get_by_code(country_code)
        env_id = self._get_environment_id_by_code(env_code)
        
        if not app or not country or not env_id:
            return None
            
        return self.get_by_combination(app.id, env_id, country.id)
    
    def get_active_mappings(self) -> List[AppEnvironmentCountryMapping]:
        """Get all currently active mappings"""
        statement = select(AppEnvironmentCountryMapping).where(
            AppEnvironmentCountryMapping.is_active == True
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_by_application(self, app_code: str) -> List[AppEnvironmentCountryMapping]:
        """
        Get all mappings for a specific application
        
        Args:
            app_code: Application code
            
        Returns:
            List of mappings for the application
        """
        statement = (
            select(AppEnvironmentCountryMapping)
            .join(AppEnvironmentCountryMapping.application)
            .where(
                and_(
                    AppEnvironmentCountryMapping.application.has(app_code=app_code),
                    AppEnvironmentCountryMapping.is_active == True
                )
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_by_country(self, country_code: str) -> List[AppEnvironmentCountryMapping]:
        """
        Get all mappings for a specific country
        
        Args:
            country_code: Country code
            
        Returns:
            List of mappings for the country
        """
        statement = (
            select(AppEnvironmentCountryMapping)
            .join(AppEnvironmentCountryMapping.country)
            .where(
                and_(
                    AppEnvironmentCountryMapping.country.has(country_code=country_code),
                    AppEnvironmentCountryMapping.is_active == True
                )
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_by_environment(self, env_code: str) -> List[AppEnvironmentCountryMapping]:
        """
        Get all mappings for a specific environment
        
        Args:
            env_code: Environment code
            
        Returns:
            List of mappings for the environment
        """
        env_id = self._get_environment_id_by_code(env_code)
        if not env_id:
            return []
            
        statement = select(AppEnvironmentCountryMapping).where(
            and_(
                AppEnvironmentCountryMapping.environment_id == env_id,
                AppEnvironmentCountryMapping.is_active == True
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    def get_configuration(self, app_code: str, env_code: str, country_code: str) -> Optional[Dict[str, Any]]:
        """
        Get complete configuration for testing a specific combination
        
        Args:
            app_code: Application code
            env_code: Environment code
            country_code: Country code
            
        Returns:
            Configuration dictionary if mapping exists, None otherwise
        """
        mapping = self.get_by_combination(app_code, env_code, country_code)
        return mapping.full_configuration if mapping else None
    
    def validate_combination(self, app_code: str, env_code: str, country_code: str) -> bool:
        """
        Validate if a specific app-environment-country combination is valid and active
        
        Args:
            app_code: Application code
            env_code: Environment code
            country_code: Country code
            
        Returns:
            True if combination is valid and active
        """
        mapping = self.get_by_combination(app_code, env_code, country_code)
        return mapping is not None and mapping.is_currently_active
    
    def get_base_url(self, app_code: str, env_code: str, country_code: str) -> Optional[str]:
        """
        Get base URL for a specific combination (convenience method for testing tools)
        
        Args:
            app_code: Application code
            env_code: Environment code
            country_code: Country code
            
        Returns:
            Base URL if mapping exists, None otherwise
        """
        mapping = self.get_by_combination(app_code, env_code, country_code)
        return mapping.base_url if mapping else None
    
    def get_headers(self, app_code: str, env_code: str, country_code: str) -> Dict[str, Any]:
        """
        Get default headers for a specific combination (convenience method for testing tools)
        
        Args:
            app_code: Application code
            env_code: Environment code
            country_code: Country code
            
        Returns:
            Headers dictionary (empty if no mapping found)
        """
        mapping = self.get_by_combination(app_code, env_code, country_code)
        return mapping.default_headers or {} if mapping else {}
    
    def get_sla_limits(self, app_code: str, env_code: str, country_code: str) -> Optional[Dict[str, Any]]:
        """
        Get SLA limits for performance testing
        
        Args:
            app_code: Application code
            env_code: Environment code
            country_code: Country code
            
        Returns:
            SLA limits if mapping exists, None otherwise
        """
        mapping = self.get_by_combination(app_code, env_code, country_code)
        if not mapping:
            return None
            
        return {
            "max_response_time_ms": mapping.max_response_time_ms,
            "max_error_rate_percent": float(mapping.max_error_rate_percent)
        }
    
    def search_combinations(self, pattern: str) -> List[AppEnvironmentCountryMapping]:
        """
        Search mappings by app name, country name, or other text patterns
        
        Args:
            pattern: Search pattern
            
        Returns:
            List of matching mappings
        """
        statement = (
            select(AppEnvironmentCountryMapping)
            .join(AppEnvironmentCountryMapping.application)
            .join(AppEnvironmentCountryMapping.country)
            .where(
                and_(
                    AppEnvironmentCountryMapping.is_active == True,
                    # Search in app name, app code, country name, or country code
                    func.lower(
                        func.concat(
                            AppEnvironmentCountryMapping.application.app_name, " ",
                            AppEnvironmentCountryMapping.application.app_code, " ",
                            AppEnvironmentCountryMapping.country.country_name, " ",
                            AppEnvironmentCountryMapping.country.country_code
                        )
                    ).like(func.lower(f"%{pattern}%"))
                )
            )
        )
        result = self.session.exec(statement).all()
        return list(result)
    
    # Private helper methods
    
    def _get_environment_id_by_code(self, env_code: str) -> Optional[int]:
        """
        Helper method to get environment ID by code
        TODO: This should be moved to EnvironmentRepository when available
        
        Args:
            env_code: Environment code
            
        Returns:
            Environment ID if found, None otherwise
        """
        # For now, hardcode the known environment mappings
        # This should be replaced with proper EnvironmentRepository lookup
        env_mapping = {
            "DEV": 1,
            "STA": 1,  # Using 1 as we know STA has id=1 from the database
            "PROD": 3
        }
        return env_mapping.get(env_code.upper())
    
    # Override base methods for specific validation
    
    def create(self, entity: AppEnvironmentCountryMapping) -> AppEnvironmentCountryMapping:
        """
        Create new mapping with validation for unique combinations
        
        Args:
            entity: Mapping to create
            
        Returns:
            Created mapping
            
        Raises:
            DuplicateEntityError: If combination already exists
        """
        # Check for existing combination
        existing = self.session.exec(
            select(AppEnvironmentCountryMapping).where(
                and_(
                    AppEnvironmentCountryMapping.application_id == entity.application_id,
                    AppEnvironmentCountryMapping.environment_id == entity.environment_id,
                    AppEnvironmentCountryMapping.country_id == entity.country_id,
                    AppEnvironmentCountryMapping.priority == entity.priority
                )
            )
        ).first()
        
        if existing:
            raise DuplicateEntityError(
                f"Mapping already exists for app_id={entity.application_id}, "
                f"env_id={entity.environment_id}, country_id={entity.country_id}, "
                f"priority={entity.priority}"
            )
        
        return super().create(entity)
