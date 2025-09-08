"""
Database Tools for QA Intelligence Agent

This module provides database query tools using both raw functions and Agno @tool decorators.
Raw functions can be called directly, while @tool decorated versions are for the Agno agent.
"""
import json
from typing import Optional
from agno.tools import tool

# Import our database validator functions
try:
    from .database_validator import (
        get_database_stats,
        get_all_apps,
        get_all_countries,
        get_all_mappings,
    search_database,
    get_app_countries as _validator_get_app_countries,
    get_country_apps as _validator_get_country_apps,
    )
    # Ensure ApplicationEndpoint model is registered with SQLAlchemy before queries run
    # to avoid mapper relationship resolution errors during tool execution.
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.environments import Environments  # noqa: F401
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.agent.tools.database_validator import (
        get_database_stats,
        get_all_apps,
        get_all_countries,
        get_all_mappings,
    search_database,
    get_app_countries as _validator_get_app_countries,
    get_country_apps as _validator_get_country_apps,
    )
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.environments import Environments  # noqa: F401


# Raw functions for direct calling (these are just aliases to the originals)
def database_stats_raw() -> str:
    """Get database statistics - raw function for direct calling"""
    return get_database_stats()

def list_apps_raw() -> str:
    """List all apps - raw function for direct calling"""
    return get_all_apps()

def list_countries_raw() -> str:
    """List all countries - raw function for direct calling"""
    return get_all_countries()

def list_mappings_raw() -> str:
    """List all mappings - raw function for direct calling"""
    return get_all_mappings()

def search_qa_data_raw(search_term: str, search_type: str = "all") -> str:
    """Search QA data - raw function for direct calling"""
    return search_database(search_term, search_type)


# Agno @tool decorated functions for the agent
@tool(
    name="get_qa_database_stats",
    description="Get comprehensive statistics about the QA Intelligence database including counts of apps, countries, and mappings",
    show_result=False
)
def database_stats() -> str:
    """
    Get comprehensive statistics about the QA Intelligence database.
    
    Returns information about:
    - Total apps (active/inactive)
    - Total countries (active/inactive)  
    - Total mappings (active/inactive/recent deployments/deprecated)
    - Average countries per app and apps per country
    
    Returns:
        str: JSON string with database statistics
    """
    return get_database_stats()


@tool(
    name="get_qa_apps",
    description="Get all applications from the QA Intelligence database with their details",
    show_result=False
)
def list_apps() -> str:
    """
    Get all applications from the QA Intelligence database.
    
    Returns information about each app including:
    - App code and name
    - Active status
    - Creation date
    - Number of countries where it's deployed
    
    Returns:
        str: JSON string with all apps information
    """
    return get_all_apps()


@tool(
    name="get_qa_countries", 
    description="Get all countries from the QA Intelligence database with their details",
    show_result=False
)
def list_countries() -> str:
    """
    Get all countries from the QA Intelligence database.
    
    Returns information about each country including:
    - Country code and name
    - Region and timezone
    - Currency code
    - Active status
    - Number of apps deployed there
    
    Returns:
        str: JSON string with all countries information
    """
    return get_all_countries()


@tool(
    name="get_qa_mappings",
    description="Get all app-country mappings showing which apps are deployed in which countries",
    show_result=False
)
def list_mappings() -> str:
    """
    Get all application-country mappings from the QA Intelligence database.
    
    Returns information about each mapping including:
    - App code/name and country code/name
    - Active status and current deployment status
    - Launch and deprecation dates
    - Deployment duration in days
    
    Returns:
        str: JSON string with all mappings information
    """
    return get_all_mappings()


@tool(
    name="search_qa_database",
    description="Search for apps, countries, or mappings in the QA Intelligence database by code or name",
    show_result=False
)
def search_qa_data(search_term: str, search_type: str = "all") -> str:
    """
    Search for apps, countries, or mappings in the QA Intelligence database.
    
    Args:
        search_term: The term to search for (app code, country code, or name)
        search_type: Type of search - "apps", "countries", "mappings", or "all" (default: "all")
    
    Returns:
        str: JSON string with search results
    """
    return search_database(search_term, search_type)


@tool(
    name="get_app_deployments",
    description="Get all countries where a specific app is deployed",
    show_result=False
)
def get_app_countries(app_code: str) -> str:
    """
    Get all countries where a specific app is deployed.
    
    Args:
        app_code: The application code (e.g., "EVA", "ONEAPP")
    
    Returns:
        str: JSON string with app's deployment countries
    """
    return _validator_get_app_countries(app_code)


@tool(
    name="get_country_apps", 
    description="Get all apps deployed in a specific country",
    show_result=False
)
def get_country_deployments(country_code: str) -> str:
    """
    Get all apps deployed in a specific country.
    
    Args:
        country_code: The country code (e.g., "RO", "FR", "CO")
    
    Returns:
        str: JSON string with country's deployed apps
    """
    return _validator_get_country_apps(country_code)
