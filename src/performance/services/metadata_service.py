"""
Metadata Service - System metadata queries

Handles metadata queries:
- Available applications
- Available environments  
- Available countries
- System configuration

Single responsibility: metadata retrieval.
"""
import json
from typing import Optional


class MetadataService:
    """Service for metadata operations."""
    
    def __init__(self, database_service):
        """Initialize with injected dependencies."""
        self.database_service = database_service
    
    def get_available_applications(self) -> str:
        """Get available applications from database."""
        try:
            apps = self.database_service.get_all_applications()
            
            apps_data = []
            for app in apps:
                apps_data.append({
                    "app_code": app.app_code,
                    "app_name": app.app_name,
                    "description": app.description,
                    "base_url_template": app.base_url_template,
                    "is_active": app.is_active
                })
            
            return json.dumps({
                "success": True,
                "applications": apps_data,
                "total": len(apps_data)
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to get applications: {str(e)}")
    
    def get_available_environments(self) -> str:
        """Get available environments from database."""
        try:
            environments = self.database_service.get_all_environments()
            
            env_data = []
            for env in environments:
                env_data.append({
                    "env_code": env.env_code,
                    "env_name": env.env_name,
                    "url_pattern": env.url_pattern,
                    "description": env.description,
                    "is_active": env.is_active
                })
            
            return json.dumps({
                "success": True,
                "environments": env_data,
                "total": len(env_data)
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to get environments: {str(e)}")
    
    def get_available_countries(self) -> str:
        """Get available countries from database."""
        try:
            countries = self.database_service.get_all_countries()
            
            countries_data = []
            for country in countries:
                countries_data.append({
                    "country_code": country.country_code,
                    "country_name": country.country_name,
                    "is_active": country.is_active
                })
            
            return json.dumps({
                "success": True,
                "countries": countries_data,
                "total": len(countries_data)
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to get countries: {str(e)}")
    
    def get_enhanced_configurations(self, app_code: Optional[str] = None, 
                                  env_code: Optional[str] = None, 
                                  country_code: Optional[str] = None) -> str:
        """Get enhanced App-Environment-Country configurations."""
        try:
            configurations = self.database_service.get_enhanced_configurations(
                app_code=app_code,
                env_code=env_code,
                country_code=country_code
            )
            
            return json.dumps({
                "success": True,
                "configurations": configurations,
                "total": len(configurations),
                "filters_applied": {
                    "app_code": app_code,
                    "env_code": env_code,
                    "country_code": country_code
                }
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to get enhanced configurations: {str(e)}")
    
    def _error_response(self, message: str) -> str:
        """Create standardized error response."""
        return json.dumps({
            "success": False,
            "error": message
        }, indent=2)
