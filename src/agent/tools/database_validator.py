"""
Database Validator Tool for QA Intelligence Agent

This tool provides comprehensive validation and querying capabilities for the QA Intelligence database,
specifically for Apps, Countries, and Application-Country Mappings.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from src.logging_config import LogStep, get_logger

# Import the models
try:
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import (
        AppEnvironmentCountryMapping,
    )

    # Import ApplicationEndpoint to ensure relationship resolution at mapper configuration time
    # SQLAlchemy resolves string-based relationships via the class registry; importing the model
    # registers it and prevents "failed to locate a name ('ApplicationEndpoint')" errors.
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.environments import Environments  # noqa: F401
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import (
        AppEnvironmentCountryMapping,
    )
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.environments import Environments  # noqa: F401


class DatabaseValidatorTool:
    """
    Uses the unified mapping table: AppEnvironmentCountryMapping

    Database validation and query tool for the QA Intelligence Agent.

    Provides tools to:
    - Validate app codes and country codes
    - Get database statistics
    - Search apps, countries, and mappings
    """

    def __init__(self):
        """Initialize the database validator tool"""
        self.engine = db_manager.engine
        self.logger = get_logger("DatabaseValidatorTool")

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
                with LogStep("validate_apps", "DatabaseValidatorTool"):
                    query = select(Apps)
                    if app_codes:
                        query = query.where(Apps.app_code.in_(app_codes))  # type: ignore[attr-defined]
                    apps = session.exec(query).all()

                    result = {
                        "status": "success",
                        "total_apps": len(apps),
                        "active_apps": len([app for app in apps if app.is_active]),
                        "inactive_apps": len(
                            [app for app in apps if not app.is_active]
                        ),
                        "apps": [],
                    }

                    for app in apps:
                        app_data = {
                            "id": app.id,
                            "app_code": app.app_code,
                            "app_name": app.app_name,
                            "description": app.description,
                            "is_active": app.is_active,
                            "created_at": (
                                app.created_at.isoformat() if app.created_at else None
                            ),
                            "country_count": (
                                len(app.country_mappings) if app.country_mappings else 0
                            ),
                        }
                        result["apps"].append(app_data)

                    if app_codes:
                        found_codes = [app.app_code for app in apps]
                        missing_codes = [
                            code for code in app_codes if code not in found_codes
                        ]
                        if missing_codes:
                            result["missing_apps"] = missing_codes
                            result["status"] = "partial"

                    return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating apps: {str(e)}",
                }

    def validate_countries(
        self, country_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate countries in the database

        Args:
            country_codes: Optional list of country codes to validate. If None, validates all countries.

        Returns:
            Dictionary with validation results
        """
        with Session(self.engine) as session:
            try:
                with LogStep("validate_countries", "DatabaseValidatorTool"):
                    query = select(Countries)
                    if country_codes:
                        query = query.where(Countries.country_code.in_(country_codes))  # type: ignore[attr-defined]
                    countries = session.exec(query).all()

                    result = {
                        "status": "success",
                        "total_countries": len(countries),
                        "active_countries": len(
                            [country for country in countries if country.is_active]
                        ),
                        "inactive_countries": len(
                            [country for country in countries if not country.is_active]
                        ),
                        "countries": [],
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
                            "created_at": (
                                country.created_at.isoformat()
                                if country.created_at
                                else None
                            ),
                            "app_count": (
                                len(country.app_mappings) if country.app_mappings else 0
                            ),
                        }
                        result["countries"].append(country_data)

                    if country_codes:
                        found_codes = [country.country_code for country in countries]
                        missing_codes = [
                            code for code in country_codes if code not in found_codes
                        ]
                        if missing_codes:
                            result["missing_countries"] = missing_codes
                            result["status"] = "partial"

                    return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating countries: {str(e)}",
                }

    def validate_mappings(
        self, app_code: Optional[str] = None, country_code: Optional[str] = None
    ) -> Dict[str, Any]:
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
                with LogStep("validate_mappings", "DatabaseValidatorTool"):
                    # Resolve optional filters to IDs first
                    app_id: Optional[int] = None
                    country_id: Optional[int] = None
                    if app_code:
                        app_id = session.exec(
                            select(Apps.id).where(Apps.app_code == app_code)
                        ).first()
                        if app_id is None:
                            return {
                                "status": "success",
                                "total_mappings": 0,
                                "active_mappings": 0,
                                "inactive_mappings": 0,
                                "mappings": [],
                            }
                    if country_code:
                        country_id = session.exec(
                            select(Countries.id).where(
                                Countries.country_code == country_code
                            )
                        ).first()
                        if country_id is None:
                            return {
                                "status": "success",
                                "total_mappings": 0,
                                "active_mappings": 0,
                                "inactive_mappings": 0,
                                "mappings": [],
                            }

                    query = select(AppEnvironmentCountryMapping)
                    if app_id is not None:
                        query = query.where(
                            AppEnvironmentCountryMapping.application_id == app_id
                        )
                    if country_id is not None:
                        query = query.where(
                            AppEnvironmentCountryMapping.country_id == country_id
                        )

                    mappings = session.exec(query).all()

                    result = {
                        "status": "success",
                        "total_mappings": len(mappings),
                        "active_mappings": len(
                            [m for m in mappings if m.is_currently_active]
                        ),
                        "inactive_mappings": len(
                            [m for m in mappings if not m.is_currently_active]
                        ),
                        "mappings": [],
                    }

                    for mapping in mappings:
                        mapping_data = {
                            "mapping_id": mapping.id,
                            "app_code": mapping.application.app_code,
                            "app_name": mapping.application.app_name,
                            "country_code": mapping.country.country_code,
                            "country_name": mapping.country.country_name,
                            "is_active": mapping.is_active,
                            "is_currently_active": mapping.is_currently_active,
                            "launched_date": (
                                mapping.launched_date.isoformat()
                                if mapping.launched_date
                                else None
                            ),
                            "deprecated_date": (
                                mapping.deprecated_date.isoformat()
                                if mapping.deprecated_date
                                else None
                            ),
                            "deployment_duration_days": mapping.deployment_duration_days,
                            "created_at": (
                                mapping.created_at.isoformat()
                                if mapping.created_at
                                else None
                            ),
                        }
                        result["mappings"].append(mapping_data)

                    return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating mappings: {str(e)}",
                }

    def validate_environments(
        self, env_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate environments in the database

        Args:
            env_codes: Optional list of environment codes to validate. If None, validates all environments.

        Returns:
            Dictionary with validation results
        """
        from database.models.environments import (
            Environments as EnvModel,  # local import to ensure mapper ready
        )

        with Session(self.engine) as session:
            try:
                with LogStep("validate_environments", "DatabaseValidatorTool"):
                    query = select(EnvModel)
                    if env_codes:
                        query = query.where(EnvModel.env_code.in_(env_codes))  # type: ignore[attr-defined]
                    environments = session.exec(query).all()

                    result = {
                        "status": "success",
                        "total_environments": len(environments),
                        "active_environments": len(
                            [e for e in environments if getattr(e, "is_active", False)]
                        ),
                        "inactive_environments": len(
                            [
                                e
                                for e in environments
                                if not getattr(e, "is_active", False)
                            ]
                        ),
                        "environments": [],
                    }

                    for env in environments:
                        created_at = getattr(env, "created_at", None)
                        env_data = {
                            "id": env.id,
                            "env_code": env.env_code,
                            "env_name": getattr(env, "env_name", None),
                            "is_production": getattr(env, "is_production", False),
                            "is_active": getattr(env, "is_active", False),
                            "created_at": (
                                created_at.isoformat() if created_at else None
                            ),
                        }
                        result["environments"].append(env_data)

                    if env_codes:
                        found_codes = [e.env_code for e in environments]
                        missing_codes = [
                            code for code in env_codes if code not in found_codes
                        ]
                        if missing_codes:
                            result["missing_environments"] = missing_codes
                            result["status"] = "partial"

                    return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error validating environments: {str(e)}",
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
                app = session.exec(
                    select(Apps).where(Apps.app_code == app_code)
                ).first()

                if not app:
                    return {"status": "error", "message": f"App '{app_code}' not found"}

                # Get mappings for this app
                mappings = session.exec(
                    select(AppEnvironmentCountryMapping).where(
                        AppEnvironmentCountryMapping.application_id == app.id
                    )
                ).all()

                result = {
                    "status": "success",
                    "app_code": app.app_code,
                    "app_name": app.app_name,
                    "total_countries": len(mappings),
                    "active_countries": len(
                        [m for m in mappings if m.is_currently_active]
                    ),
                    "countries": [],
                }

                for mapping in mappings:
                    country_data = {
                        "country_code": mapping.country.country_code,
                        "country_name": mapping.country.country_name,
                        "region": mapping.country.region,
                        "is_active": mapping.is_currently_active,
                        "launched_date": (
                            mapping.launched_date.isoformat()
                            if mapping.launched_date
                            else None
                        ),
                        "deprecated_date": (
                            mapping.deprecated_date.isoformat()
                            if mapping.deprecated_date
                            else None
                        ),
                        "deployment_duration_days": mapping.deployment_duration_days,
                    }
                    result["countries"].append(country_data)

                return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting countries for app '{app_code}': {str(e)}",
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
                country = session.exec(
                    select(Countries).where(Countries.country_code == country_code)
                ).first()

                if not country:
                    return {
                        "status": "error",
                        "message": f"Country '{country_code}' not found",
                    }

                # Get mappings for this country
                mappings = session.exec(
                    select(AppEnvironmentCountryMapping).where(
                        AppEnvironmentCountryMapping.country_id == country.id
                    )
                ).all()

                result = {
                    "status": "success",
                    "country_code": country.country_code,
                    "country_name": country.country_name,
                    "region": country.region,
                    "total_apps": len(mappings),
                    "active_apps": len([m for m in mappings if m.is_currently_active]),
                    "apps": [],
                }

                for mapping in mappings:
                    app_data = {
                        "app_code": mapping.application.app_code,
                        "app_name": mapping.application.app_name,
                        "description": mapping.application.description,
                        "is_active": mapping.is_currently_active,
                        "launched_date": (
                            mapping.launched_date.isoformat()
                            if mapping.launched_date
                            else None
                        ),
                        "deprecated_date": (
                            mapping.deprecated_date.isoformat()
                            if mapping.deprecated_date
                            else None
                        ),
                        "deployment_duration_days": mapping.deployment_duration_days,
                    }
                    result["apps"].append(app_data)

                return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting apps for country '{country_code}': {str(e)}",
                }

    def search_database(
        self, search_term: str, search_type: str = "all"
    ) -> Dict[str, Any]:
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
                with LogStep("search_database", "DatabaseValidatorTool"):
                    # Normalize search_type
                    search_type = (search_type or "all").lower().strip()
                    valid_types = {"apps", "countries", "mappings", "all"}
                    if search_type not in valid_types:
                        return {
                            "status": "error",
                            "message": f"Invalid search_type '{search_type}'. Must be one of {sorted(valid_types)}",
                        }
                    result = {
                        "status": "success",
                        "search_term": search_term,
                        "search_type": search_type,
                        "results": {},
                    }

                    if search_type in ["apps", "all"]:
                        apps = session.exec(
                            select(Apps).where(
                                Apps.app_code.ilike(f"%{search_term}%")  # type: ignore[attr-defined]
                                | Apps.app_name.ilike(
                                    f"%{search_term}%"
                                )  # type: ignore[attr-defined]
                                | Apps.description.ilike(
                                    f"%{search_term}%"
                                )  # type: ignore[attr-defined]
                            )
                        ).all()
                        result["results"]["apps"] = [
                            {
                                "app_code": app.app_code,
                                "app_name": app.app_name,
                                "description": app.description,
                                "is_active": app.is_active,
                            }
                            for app in apps
                        ]

                    if search_type in ["countries", "all"]:
                        countries = session.exec(
                            select(Countries).where(
                                Countries.country_code.ilike(f"%{search_term}%")  # type: ignore[attr-defined]
                                | Countries.country_name.ilike(
                                    f"%{search_term}%"
                                )  # type: ignore[attr-defined]
                                | Countries.region.ilike(
                                    f"%{search_term}%"
                                )  # type: ignore[attr-defined]
                            )
                        ).all()
                        result["results"]["countries"] = [
                            {
                                "country_code": country.country_code,
                                "country_name": country.country_name,
                                "region": country.region,
                                "is_active": country.is_active,
                            }
                            for country in countries
                        ]

                    if search_type in ["mappings", "all"]:
                        app_ids = set(
                            session.exec(
                                select(Apps.id).where(
                                    Apps.app_code.ilike(f"%{search_term}%")  # type: ignore[attr-defined]
                                    | Apps.app_name.ilike(
                                        f"%{search_term}%"
                                    )  # type: ignore[attr-defined]
                                )
                            ).all()
                            or []
                        )
                        country_ids = set(
                            session.exec(
                                select(Countries.id).where(
                                    Countries.country_code.ilike(f"%{search_term}%")  # type: ignore[attr-defined]
                                    | Countries.country_name.ilike(
                                        f"%{search_term}%"
                                    )  # type: ignore[attr-defined]
                                )
                            ).all()
                            or []
                        )

                        query = select(AppEnvironmentCountryMapping)
                        if app_ids:
                            query = query.where(AppEnvironmentCountryMapping.application_id.in_(app_ids))  # type: ignore[attr-defined]
                        if country_ids:
                            query = query.where(AppEnvironmentCountryMapping.country_id.in_(country_ids))  # type: ignore[attr-defined]
                        mappings = session.exec(query).all()
                        result["results"]["mappings"] = [
                            {
                                "mapping_id": m.id,
                                "app_code": m.application.app_code,
                                "app_name": m.application.app_name,
                                "country_code": m.country.country_code,
                                "country_name": m.country.country_name,
                                "is_active": m.is_active,
                                "is_currently_active": m.is_currently_active,
                                "launched_date": (
                                    m.launched_date.isoformat()
                                    if m.launched_date
                                    else None
                                ),
                                "deprecated_date": (
                                    m.deprecated_date.isoformat()
                                    if m.deprecated_date
                                    else None
                                ),
                                "deployment_duration_days": m.deployment_duration_days,
                            }
                            for m in mappings
                        ]

                    return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error searching database: {str(e)}",
                }

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics

        Returns:
            Dictionary with database statistics
        """
        with Session(self.engine) as session:
            try:
                with LogStep("get_database_stats", "DatabaseValidatorTool"):
                    # Get counts
                    total_apps = session.exec(select(Apps)).all()
                    total_countries = session.exec(select(Countries)).all()
                    total_mappings = session.exec(
                        select(AppEnvironmentCountryMapping)
                    ).all()

                active_apps = [app for app in total_apps if app.is_active]
                active_countries = [
                    country for country in total_countries if country.is_active
                ]
                active_mappings = [
                    mapping for mapping in total_mappings if mapping.is_currently_active
                ]

                # Calculate deployment statistics
                now_utc = datetime.now(timezone.utc)
                recent_deployments = [
                    mapping
                    for mapping in total_mappings
                    if mapping.launched_date
                    and (
                        now_utc
                        - (
                            mapping.launched_date.replace(tzinfo=timezone.utc)
                            if mapping.launched_date.tzinfo is None
                            else mapping.launched_date
                        )
                    ).days
                    <= 30
                ]

                deprecated_mappings = [
                    mapping
                    for mapping in total_mappings
                    if mapping.deprecated_date is not None
                ]

                result = {
                    "status": "success",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "apps": {
                        "total": len(total_apps),
                        "active": len(active_apps),
                        "inactive": len(total_apps) - len(active_apps),
                    },
                    "countries": {
                        "total": len(total_countries),
                        "active": len(active_countries),
                        "inactive": len(total_countries) - len(active_countries),
                    },
                    "mappings": {
                        "total": len(total_mappings),
                        "active": len(active_mappings),
                        "inactive": len(total_mappings) - len(active_mappings),
                        "recent_deployments": len(recent_deployments),
                        "deprecated": len(deprecated_mappings),
                    },
                    "average_countries_per_app": (
                        len(total_mappings) / len(total_apps) if total_apps else 0
                    ),
                    "average_apps_per_country": (
                        len(total_mappings) / len(total_countries)
                        if total_countries
                        else 0
                    ),
                }

                return result

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error getting database stats: {str(e)}",
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
    codes_list = (
        [code.strip() for code in country_codes.split(",")] if country_codes else None
    )
    result = validator.validate_countries(codes_list)
    return json.dumps(result, indent=2)


def validate_mappings(
    app_code: Optional[str] = None, country_code: Optional[str] = None
) -> str:
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
    app_code = (app_code or "").strip()
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
    country_code = (country_code or "").strip()
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


def get_all_environments() -> str:
    """
    Get all environments from the QA Intelligence database.

    Returns:
        JSON string with all environments information
    """
    validator = DatabaseValidatorTool()
    result = validator.validate_environments()  # No filter means all environments
    return json.dumps(result, indent=2)
