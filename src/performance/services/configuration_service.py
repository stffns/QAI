"""
Configuration Service - Configuration management and validation

Handles configuration operations:
- Database configuration queries
- RPS cascade resolution
- SLA validation
- Configuration building

Single responsibility: configuration management.
"""
import json
from typing import Dict, Any, Optional


class ConfigurationService:
    """Service for configuration operations."""
    
    def __init__(self, database_service):
        """Initialize with injected dependencies."""
        self.database_service = database_service
    
    def query_database_configuration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query database for complete configuration INCLUDING enhanced App-Env-Country configs."""
        try:
            # Check if repository classes are available
            from database.repositories.apps_repository import AppsRepository
            from database.repositories.performance import EnvironmentsRepository, ApplicationEndpointsRepository
            from database.repositories.countries_repository import CountriesRepository
            from database.repositories.app_environment_country_mappings_repository import AppEnvironmentCountryMappingRepository
            
            data = {}
            
            with self.database_service.get_session() as session:
                # Get repositories
                apps_repo = AppsRepository(session)
                env_repo = EnvironmentsRepository(session)
                countries_repo = CountriesRepository(session)
                endpoints_repo = ApplicationEndpointsRepository(session)
                mappings_repo = AppEnvironmentCountryMappingRepository(session)
                
                # Get application
                if "app_code" in params:
                    app = apps_repo.get_by_code(params["app_code"])
                    if not app:
                        return {"success": False, "error": f"Application {params['app_code']} not found"}
                    
                    # Convert to dict to avoid session issues
                    data["application"] = {
                        "id": app.id,
                        "app_code": app.app_code,
                        "app_name": app.app_name,
                        "description": app.description,
                        "base_url_template": app.base_url_template,
                        "is_active": app.is_active
                    }
                
                # Get environment
                if "env_code" in params:
                    env = env_repo.get_by_code(params["env_code"])
                    if not env:
                        return {"success": False, "error": f"Environment {params['env_code']} not found"}
                    
                    # Convert to dict to avoid session issues
                    data["environment"] = {
                        "id": env.id,
                        "env_code": env.env_code,
                        "env_name": env.env_name,
                        "url_pattern": env.url_pattern,
                        "description": env.description,
                        "is_active": env.is_active
                    }
                
                # Get country
                if "country_code" in params:
                    country = countries_repo.get_by_code(params["country_code"])
                    if not country:
                        return {"success": False, "error": f"Country {params['country_code']} not found"}
                    
                    # Convert to dict to avoid session issues
                    data["country"] = {
                        "id": country.id,
                        "country_code": country.country_code,
                        "country_name": country.country_name,
                        "is_active": country.is_active
                    }
                
                # Get endpoints
                if "app_code" in params and "env_code" in params:
                    # Need to get IDs from the app and env objects
                    app_id = data["application"]["id"] if "application" in data else None
                    env_id = data["environment"]["id"] if "environment" in data else None
                    
                    if app_id and env_id:
                        endpoints = endpoints_repo.get_active_endpoints(app_id, env_id)
                        
                        data["endpoints"] = []
                        for endpoint in endpoints:
                            data["endpoints"].append({
                                "id": endpoint.id,
                                "application_id": endpoint.application_id,
                                "environment_id": endpoint.environment_id,
                                "endpoint_name": endpoint.endpoint_name,
                                "endpoint_url": endpoint.endpoint_url,
                                "http_method": endpoint.http_method,
                                "endpoint_type": endpoint.endpoint_type,
                                "description": endpoint.description,
                                "is_active": endpoint.is_active
                            })
                
                # TODO: Update to use new unified mapping repository
                # mapping_config = mappings_repo.get_by_combination(
                #     app_id=..., env_id=..., country_id=...
                # )
                
                return {"success": True, "data": data}
                
        except Exception as e:
            return {"success": False, "error": f"Database query failed: {str(e)}"}
    
    def resolve_rps_cascade(self, params: Dict[str, Any], db_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve RPS using cascade logic."""
        try:
            # Default RPS if nothing found
            default_rps = 1.0
            
            # Check direct parameter first
            if "agent_rps" in params and params["agent_rps"]:
                return {"success": True, "rps": float(params["agent_rps"]), "source": "direct_parameter"}
            
            # Check enhanced configuration
            if "enhanced_config" in db_data and db_data["enhanced_config"]:
                enhanced_config = db_data["enhanced_config"]
                if enhanced_config.get("performance_config", {}).get("default_rps"):
                    rps = float(enhanced_config["performance_config"]["default_rps"])
                    return {"success": True, "rps": rps, "source": "enhanced_config"}
            
            # Fallback to default
            return {"success": True, "rps": default_rps, "source": "default"}
            
        except Exception as e:
            return {"success": False, "error": f"RPS resolution failed: {str(e)}"}
    
    def validate_against_slas(self, params: Dict[str, Any], rps: float, db_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against SLA limits."""
        try:
            # For now, basic validation - can be enhanced later
            virtual_users = int(params.get("virtual_users", 1))
            duration_minutes = int(params.get("duration_minutes", 1))
            
            # Basic limits
            if virtual_users > 1000:
                return {"success": False, "error": f"Virtual users {virtual_users} exceeds limit of 1000"}
            
            if duration_minutes > 60:
                return {"success": False, "error": f"Duration {duration_minutes} minutes exceeds limit of 60"}
            
            if rps > 100:
                return {"success": False, "error": f"RPS {rps} exceeds limit of 100"}
            
            return {"success": True, "validation": "passed"}
            
        except Exception as e:
            return {"success": False, "error": f"SLA validation failed: {str(e)}"}
    
    def build_complete_configuration(self, params: Dict[str, Any], db_data: Dict[str, Any], rps: float) -> str:
        """Build complete configuration JSON for engine."""
        try:
            config = {
                "simulation": {
                    "app_code": params.get("app_code"),
                    "env_code": params.get("env_code"),
                    "country_code": params.get("country_code"),
                    "virtual_users": int(params.get("virtual_users", 1)),
                    "duration_seconds": int(params.get("duration_minutes", 1)) * 60,
                    "agent_rps": rps
                },
                "application": db_data.get("application", {}),
                "environment": db_data.get("environment", {}),
                "country": db_data.get("country", {}),
                "endpoints": db_data.get("endpoints", []),
                "enhanced_config": db_data.get("enhanced_config", {})
            }
            
            return json.dumps(config, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Configuration build failed: {str(e)}"})
    
    def _error_response(self, message: str) -> str:
        """Create standardized error response."""
        return json.dumps({
            "success": False,
            "error": message
        }, indent=2)
