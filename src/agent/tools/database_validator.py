"""
Database Validator Tool for QA Intelligence Agent

This tool provides comprehensive validation and querying capabilities for the QA Intelligence database,
specifically for Apps, Countries, and Application-Country Mappings.
"""
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, select

# Import the models
try:
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.mappings import ApplicationCountryMapping
    from database.connection import db_manager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.mappings import ApplicationCountryMapping
    from database.connection import db_manager

class DatabaseValidatorTool:
    """
    Comprehensive database validation and query tool for QA Intelligence.
    
    Provides methods to validate, query, and analyze the relationships between
    Apps, Countries, and their mappings.
    """
    
    def __init__(self):
        """Initialize the database validator tool"""
        self.engine = db_manager.engine
        self.session_factory = sessionmaker(bind=self.engine)
    
    def validate_apps(self, app_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate apps in the database
        
        Args:
            app_codes: Optional list of app codes to validate. If None, validates all apps.
            
        Returns:
            Dictionary with validation results
        """
        with Session(self.engine) as session:
            try:
                if app_codes:
                    # Validate specific apps
                    query = select(Apps).where(Apps.app_code.in_(app_codes))
                else:
                    # Validate all apps
                    query = select(Apps)
                
                apps = session.exec(query).all()
                
                result = {
                    "status": "success",
                    "total_apps": len(apps),
                    "active_apps": len([app for app in apps if app.is_active]),
                    "inactive_apps": len([app for app in apps if not app.is_active]),
                    "apps": []
                }
                
                for app in apps:
                    app_data = {
                        "id": app.id,
                        "app_code": app.app_code,
                        "app_name": app.app_name,
                        "description": app.description,
                        "is_active": app.is_active,
                        "created_at": app.created_at.isoformat() if app.created_at else None,
                        "country_count": len(app.country_mappings) if app.country_mappings else 0
                    }
                    result["apps"].append(app_data)
                
                if app_codes:
                    # Check for missing apps
                    found_codes = [app.app_code for app in apps]
                    missing_codes = [code for code in app_codes if code not in found_codes]
                    if missing_codes:
                        result["missing_apps"] = missing_codes
                        result["status"] = "partial"
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating apps: {str(e)}"
                }
    
    def validate_countries(self, country_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate countries in the database
        
        Args:
            country_codes: Optional list of country codes to validate. If None, validates all countries.
            
        Returns:
            Dictionary with validation results
        """
        with Session(self.engine) as session:
            try:
                if country_codes:
                    # Validate specific countries
                    query = select(Countries).where(Countries.country_code.in_(country_codes))
                else:
                    # Validate all countries
                    query = select(Countries)
                
                countries = session.exec(query).all()
                
                result = {
                    "status": "success",
                    "total_countries": len(countries),
                    "active_countries": len([country for country in countries if country.is_active]),
                    "inactive_countries": len([country for country in countries if not country.is_active]),
                    "countries": []
                }
                
                for country in countries:
                    country_data = {
                        "id": country.id,
                        "country_code": country.country_code,
                        "country_name": country.country_name,
                        "region": country.region,
                        "currency_code": country.currency_code,
                        "timezone": country.timezone,
                        "is_active": country.is_active,
                        "created_at": country.created_at.isoformat() if country.created_at else None,
                        "app_count": len(country.app_mappings) if country.app_mappings else 0
                    }
                    result["countries"].append(country_data)
                
                if country_codes:
                    # Check for missing countries
                    found_codes = [country.country_code for country in countries]
                    missing_codes = [code for code in country_codes if code not in found_codes]
                    if missing_codes:
                        result["missing_countries"] = missing_codes
                        result["status"] = "partial"
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating countries: {str(e)}"
                }
    
    def validate_mappings(self, app_code: Optional[str] = None, country_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate application-country mappings
        
        Args:
            app_code: Optional app code to filter mappings
            country_code: Optional country code to filter mappings
            
        Returns:
            Dictionary with mapping validation results
        """
        with Session(self.engine) as session:
            try:
                # Build the query
                query = select(ApplicationCountryMapping)
                
                # Add joins to get app and country data
                query = query.join(Apps).join(Countries)
                
                # Apply filters if provided
                if app_code:
                    query = query.where(Apps.app_code == app_code)
                if country_code:
                    query = query.where(Countries.country_code == country_code)
                
                mappings = session.exec(query).all()
                
                result = {
                    "status": "success",
                    "total_mappings": len(mappings),
                    "active_mappings": len([m for m in mappings if m.is_currently_active]),
                    "inactive_mappings": len([m for m in mappings if not m.is_currently_active]),
                    "mappings": []
                }
                
                for mapping in mappings:
                    mapping_data = {
                        "mapping_id": mapping.mapping_id,
                        "app_code": mapping.application.app_code,
                        "app_name": mapping.application.app_name,
                        "country_code": mapping.country.country_code,
                        "country_name": mapping.country.country_name,
                        "is_active": mapping.is_active,
                        "is_currently_active": mapping.is_currently_active,
                        "launched_date": mapping.launched_date.isoformat() if mapping.launched_date else None,
                        "deprecated_date": mapping.deprecated_date.isoformat() if mapping.deprecated_date else None,
                        "deployment_duration_days": mapping.deployment_duration_days,
                        "created_at": mapping.created_at.isoformat() if mapping.created_at else None
                    }
                    result["mappings"].append(mapping_data)
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating mappings: {str(e)}"
                }
    
    def get_app_countries(self, app_code: str) -> Dict[str, Any]:
        """
        Get all countries where a specific app is deployed
        
        Args:
            app_code: The application code
            
        Returns:
            Dictionary with app's countries information
        """
        with Session(self.engine) as session:
            try:
                # Get the app
                app = session.exec(select(Apps).where(Apps.app_code == app_code)).first()
                
                if not app:
                    return {
                        "status": "error",
                        "message": f"App '{app_code}' not found"
                    }
                
                # Get mappings for this app
                mappings = session.exec(
                    select(ApplicationCountryMapping)
                    .join(Countries)
                    .where(ApplicationCountryMapping.application_id == app.id)
                ).all()
                
                result = {
                    "status": "success",
                    "app_code": app.app_code,
                    "app_name": app.app_name,
                    "total_countries": len(mappings),
                    "active_countries": len([m for m in mappings if m.is_currently_active]),
                    "countries": []
                }
                
                for mapping in mappings:
                    country_data = {
                        "country_code": mapping.country.country_code,
                        "country_name": mapping.country.country_name,
                        "region": mapping.country.region,
                        "is_active": mapping.is_currently_active,
                        "launched_date": mapping.launched_date.isoformat() if mapping.launched_date else None,
                        "deprecated_date": mapping.deprecated_date.isoformat() if mapping.deprecated_date else None,
                        "deployment_duration_days": mapping.deployment_duration_days
                    }
                    result["countries"].append(country_data)
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting countries for app '{app_code}': {str(e)}"
                }
    
    def get_country_apps(self, country_code: str) -> Dict[str, Any]:
        """
        Get all apps deployed in a specific country
        
        Args:
            country_code: The country code
            
        Returns:
            Dictionary with country's apps information
        """
        with Session(self.engine) as session:
            try:
                # Get the country
                country = session.exec(select(Countries).where(Countries.country_code == country_code)).first()
                
                if not country:
                    return {
                        "status": "error",
                        "message": f"Country '{country_code}' not found"
                    }
                
                # Get mappings for this country
                mappings = session.exec(
                    select(ApplicationCountryMapping)
                    .join(Apps)
                    .where(ApplicationCountryMapping.country_id == country.id)
                ).all()
                
                result = {
                    "status": "success",
                    "country_code": country.country_code,
                    "country_name": country.country_name,
                    "region": country.region,
                    "total_apps": len(mappings),
                    "active_apps": len([m for m in mappings if m.is_currently_active]),
                    "apps": []
                }
                
                for mapping in mappings:
                    app_data = {
                        "app_code": mapping.application.app_code,
                        "app_name": mapping.application.app_name,
                        "description": mapping.application.description,
                        "is_active": mapping.is_currently_active,
                        "launched_date": mapping.launched_date.isoformat() if mapping.launched_date else None,
                        "deprecated_date": mapping.deprecated_date.isoformat() if mapping.deprecated_date else None,
                        "deployment_duration_days": mapping.deployment_duration_days
                    }
                    result["apps"].append(app_data)
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting apps for country '{country_code}': {str(e)}"
                }
    
    def search_database(self, search_term: str, search_type: str = "all") -> Dict[str, Any]:
        """
        Search across apps, countries, and mappings
        
        Args:
            search_term: Term to search for
            search_type: Type of search ("apps", "countries", "mappings", or "all")
            
        Returns:
            Dictionary with search results
        """
        with Session(self.engine) as session:
            try:
                result = {
                    "status": "success",
                    "search_term": search_term,
                    "search_type": search_type,
                    "results": {}
                }
                
                if search_type in ["apps", "all"]:
                    # Search apps
                    apps = session.exec(
                        select(Apps).where(
                            (Apps.app_code.ilike(f"%{search_term}%")) |
                            (Apps.app_name.ilike(f"%{search_term}%")) |
                            (Apps.description.ilike(f"%{search_term}%"))
                        )
                    ).all()
                    
                    result["results"]["apps"] = [
                        {
                            "app_code": app.app_code,
                            "app_name": app.app_name,
                            "description": app.description,
                            "is_active": app.is_active
                        }
                        for app in apps
                    ]
                
                if search_type in ["countries", "all"]:
                    # Search countries
                    countries = session.exec(
                        select(Countries).where(
                            (Countries.country_code.ilike(f"%{search_term}%")) |
                            (Countries.country_name.ilike(f"%{search_term}%")) |
                            (Countries.region.ilike(f"%{search_term}%"))
                        )
                    ).all()
                    
                    result["results"]["countries"] = [
                        {
                            "country_code": country.country_code,
                            "country_name": country.country_name,
                            "region": country.region,
                            "is_active": country.is_active
                        }
                        for country in countries
                    ]
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error searching database: {str(e)}"
                }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics
        
        Returns:
            Dictionary with database statistics
        """
        with Session(self.engine) as session:
            try:
                # Get counts
                total_apps = session.exec(select(Apps)).all()
                total_countries = session.exec(select(Countries)).all()
                total_mappings = session.exec(select(ApplicationCountryMapping)).all()
                
                active_apps = [app for app in total_apps if app.is_active]
                active_countries = [country for country in total_countries if country.is_active]
                active_mappings = [mapping for mapping in total_mappings if mapping.is_currently_active]
                
                # Calculate deployment statistics
                now_utc = datetime.now(timezone.utc)
                recent_deployments = [
                    mapping for mapping in total_mappings 
                    if mapping.launched_date and 
                    (now_utc - (mapping.launched_date.replace(tzinfo=timezone.utc) if mapping.launched_date.tzinfo is None else mapping.launched_date)).days <= 30
                ]
                
                deprecated_mappings = [
                    mapping for mapping in total_mappings 
                    if mapping.deprecated_date is not None
                ]
                
                result = {
                    "status": "success",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "apps": {
                        "total": len(total_apps),
                        "active": len(active_apps),
                        "inactive": len(total_apps) - len(active_apps)
                    },
                    "countries": {
                        "total": len(total_countries),
                        "active": len(active_countries),
                        "inactive": len(total_countries) - len(active_countries)
                    },
                    "mappings": {
                        "total": len(total_mappings),
                        "active": len(active_mappings),
                        "inactive": len(total_mappings) - len(active_mappings),
                        "recent_deployments": len(recent_deployments),
                        "deprecated": len(deprecated_mappings)
                    },
                    "average_countries_per_app": len(total_mappings) / len(total_apps) if total_apps else 0,
                    "average_apps_per_country": len(total_mappings) / len(total_countries) if total_countries else 0
                }
                
                return result
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting database stats: {str(e)}"
                }

# Main tool functions that will be exposed to the agent
def validate_apps(app_codes: Optional[str] = None) -> str:
    """
    Validate apps in the QA Intelligence database.
    
    Args:
        app_codes: Comma-separated list of app codes to validate (optional)
    
    Returns:
        JSON string with validation results
    """
    validator = DatabaseValidatorTool()
    codes_list = [code.strip() for code in app_codes.split(",")] if app_codes else None
    result = validator.validate_apps(codes_list)
    return json.dumps(result, indent=2)

def validate_countries(country_codes: Optional[str] = None) -> str:
    """
    Validate countries in the QA Intelligence database.
    
    Args:
        country_codes: Comma-separated list of country codes to validate (optional)
    
    Returns:
        JSON string with validation results
    """
    validator = DatabaseValidatorTool()
    codes_list = [code.strip() for code in country_codes.split(",")] if country_codes else None
    result = validator.validate_countries(codes_list)
    return json.dumps(result, indent=2)

def validate_mappings(app_code: Optional[str] = None, country_code: Optional[str] = None) -> str:
    """
    Validate application-country mappings in the QA Intelligence database.
    
    Args:
        app_code: App code to filter mappings (optional)
        country_code: Country code to filter mappings (optional)
    
    Returns:
        JSON string with mapping validation results
    """
    validator = DatabaseValidatorTool()
    result = validator.validate_mappings(app_code, country_code)
    return json.dumps(result, indent=2)

def get_app_countries(app_code: str) -> str:
    """
    Get all countries where a specific app is deployed.
    
    Args:
        app_code: The application code
    
    Returns:
        JSON string with app's countries information
    """
    validator = DatabaseValidatorTool()
    result = validator.get_app_countries(app_code)
    return json.dumps(result, indent=2)

def get_country_apps(country_code: str) -> str:
    """
    Get all apps deployed in a specific country.
    
    Args:
        country_code: The country code
    
    Returns:
        JSON string with country's apps information
    """
    validator = DatabaseValidatorTool()
    result = validator.get_country_apps(country_code)
    return json.dumps(result, indent=2)

def search_database(search_term: str, search_type: str = "all") -> str:
    """
    Search across apps, countries, and mappings in the QA Intelligence database.
    
    Args:
        search_term: Term to search for
        search_type: Type of search ("apps", "countries", "mappings", or "all")
    
    Returns:
        JSON string with search results
    """
    validator = DatabaseValidatorTool()
    result = validator.search_database(search_term, search_type)
    return json.dumps(result, indent=2)

def get_database_stats() -> str:
    """
    Get comprehensive statistics about the QA Intelligence database.
    
    Returns:
        JSON string with database statistics
    """
    validator = DatabaseValidatorTool()
    result = validator.get_database_stats()
    return json.dumps(result, indent=2)

def get_all_countries() -> str:
    """
    Get all countries from the QA Intelligence database.
    
    Returns:
        JSON string with all countries information
    """
    validator = DatabaseValidatorTool()
    result = validator.validate_countries()  # No filter means all countries
    return json.dumps(result, indent=2)

def get_all_apps() -> str:
    """
    Get all apps from the QA Intelligence database.
    
    Returns:
        JSON string with all apps information
    """
    validator = DatabaseValidatorTool()
    result = validator.validate_apps()  # No filter means all apps
    return json.dumps(result, indent=2)

def get_all_mappings() -> str:
    """
    Get all app-country mappings from the QA Intelligence database.
    
    Returns:
        JSON string with all mappings information
    """
    validator = DatabaseValidatorTool()
    result = validator.validate_mappings()  # No filter means all mappings
    return json.dumps(result, indent=2)
