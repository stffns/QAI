"""
Database Tools for QA Intelligence Agent

This module provides database query tools using both raw functions and Agno @tool decorators.
Raw functions can be called directly, while @tool decorated versions are for the Agno agent.
"""
import json
from typing import Optional
from agno.tools import tool
from sqlmodel import Session, select

# Import our database validator functions
try:
    from .database_validator import (
        get_database_stats,
        get_all_apps,
        get_all_countries,
        get_all_mappings,
    get_all_environments,
    search_database,
    get_app_countries as _validator_get_app_countries,
    get_country_apps as _validator_get_country_apps,
    )
    # Ensure ApplicationEndpoint model is registered with SQLAlchemy before queries run
    # to avoid mapper relationship resolution errors during tool execution.
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.environments import Environments  # noqa: F401
    # Reuse PerformanceService for endpoint discovery to avoid duplicating repo logic
    from src.application.performance.factory import build_default_service
    # Direct DB access for full mapping details
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.environments import Environments as EnvModel
    from database.models.performance_test_executions import PerformanceTestExecution, ExecutionStatus as ExecStatus
    from database.models.performance_endpoint_results import PerformanceEndpointResults
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.agent.tools.database_validator import (
        get_database_stats,
        get_all_apps,
        get_all_countries,
        get_all_mappings,
    get_all_environments,
    search_database,
    get_app_countries as _validator_get_app_countries,
    get_country_apps as _validator_get_country_apps,
    )
    from database.models.application_endpoints import ApplicationEndpoint  # noqa: F401
    from database.models.environments import Environments  # noqa: F401
    from src.application.performance.factory import build_default_service
    from database.connection import db_manager
    from database.models.app_environment_country_mappings import AppEnvironmentCountryMapping
    from database.models.apps import Apps
    from database.models.countries import Countries
    from database.models.environments import Environments as EnvModel
    from database.models.performance_test_executions import PerformanceTestExecution, ExecutionStatus as ExecStatus
    from database.models.performance_endpoint_results import PerformanceEndpointResults


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

def list_environments_raw() -> str:
    """List all environments - raw function for direct calling"""
    return get_all_environments()

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
    name="get_qa_environments",
    description="Get all environments from the QA Intelligence database (e.g., STA, UAT, PRD)",
    show_result=False
)
def list_environments() -> str:
    """
    Get all environments from the QA Intelligence database.
    
    Returns:
        str: JSON string with all environments information
    """
    return get_all_environments()


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


# --- Performance Executions: DB exposure ---

def _exec_to_dict(ex: PerformanceTestExecution) -> dict:
    def iso(dt):
        try:
            return dt.isoformat() if dt else None
        except Exception:
            return None
    def enum_name(v):
        try:
            return v.name if hasattr(v, "name") else (str(v) if v is not None else None)
        except Exception:
            return str(v) if v is not None else None
    return {
        "id": getattr(ex, "id", None),
        "execution_id": getattr(ex, "execution_id", None),
        "execution_name": getattr(ex, "execution_name", None),
        "status": enum_name(getattr(ex, "status", None)),
        "validation_status": enum_name(getattr(ex, "validation_status", None)),
        "sla_compliance": enum_name(getattr(ex, "sla_compliance", None)),
        "execution_scope": enum_name(getattr(ex, "execution_scope", None)),
        "execution_environment": getattr(ex, "execution_environment", None),
        "test_purpose": getattr(ex, "test_purpose", None),
        "start_time": iso(getattr(ex, "start_time", None)),
        "end_time": iso(getattr(ex, "end_time", None)),
        "duration_seconds": getattr(ex, "duration_seconds", None),
        "total_requests": getattr(ex, "total_requests", None),
        "successful_requests": getattr(ex, "successful_requests", None),
        "failed_requests": getattr(ex, "failed_requests", None),
        "avg_rps": getattr(ex, "avg_rps", None),
        "avg_response_time": getattr(ex, "avg_response_time", None),
        "p95_response_time": getattr(ex, "p95_response_time", None),
        "p99_response_time": getattr(ex, "p99_response_time", None),
        "min_response_time": getattr(ex, "min_response_time", None),
        "max_response_time": getattr(ex, "max_response_time", None),
        "error_rate": getattr(ex, "error_rate", None),
        "gatling_report_path": getattr(ex, "gatling_report_path", None),
        "created_at": iso(getattr(ex, "created_at", None)),
        "updated_at": iso(getattr(ex, "updated_at", None)),
    }


def list_perf_executions_raw(status: Optional[str] = None, environment: Optional[str] = None, limit: int = 20) -> str:
    """Raw: list recent performance executions with optional filters."""
    try:
        engine = db_manager.engine
        with Session(engine) as session:
            stmt = select(PerformanceTestExecution)
            if status:
                try:
                    enum_status = ExecStatus[status.upper()]
                    stmt = stmt.where(PerformanceTestExecution.status == enum_status)
                except Exception:
                    return json.dumps({"status": "error", "message": f"Invalid status: {status}"})
            if environment:
                stmt = stmt.where(PerformanceTestExecution.execution_environment == environment)
            # Order by created_at desc when available
            try:
                from sqlmodel import desc
                stmt = stmt.order_by(desc(PerformanceTestExecution.created_at))
            except Exception:
                pass
            rows = session.exec(stmt).all()
            data = [_exec_to_dict(ex) for ex in rows[: max(1, int(limit))]]
            return json.dumps({"status": "success", "count": len(data), "executions": data})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to list executions: {str(e)}"})


def get_perf_execution_raw(execution_id: str) -> str:
    """Raw: get a single performance execution by execution_id."""
    try:
        engine = db_manager.engine
        with Session(engine) as session:
            stmt = select(PerformanceTestExecution).where(PerformanceTestExecution.execution_id == execution_id)
            ex = session.exec(stmt).first()
            if not ex:
                return json.dumps({"status": "success", "found": False, "execution": None})
            return json.dumps({"status": "success", "found": True, "execution": _exec_to_dict(ex)})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to get execution: {str(e)}"})


def get_perf_endpoint_results_raw(execution_id: str) -> str:
    """Raw: list endpoint-level results for a given execution_id."""
    try:
        engine = db_manager.engine
        with Session(engine) as session:
            stmt = select(PerformanceEndpointResults).where(PerformanceEndpointResults.execution_id == execution_id)
            rows = session.exec(stmt).all()
            def dto(r: PerformanceEndpointResults) -> dict:
                return {
                    "id": r.id,
                    "execution_id": r.execution_id,
                    "endpoint_name": r.endpoint_name,
                    "http_method": r.http_method,
                    "endpoint_url": r.endpoint_url,
                    "total_requests": r.total_requests,
                    "successful_requests": r.successful_requests,
                    "failed_requests": r.failed_requests,
                    "p50_response_time": r.p50_response_time,
                    "p75_response_time": r.p75_response_time,
                    "p95_response_time": r.p95_response_time,
                    "p99_response_time": r.p99_response_time,
                    "avg_response_time": r.avg_response_time,
                    "max_response_time": r.max_response_time,
                    "min_response_time": r.min_response_time,
                    "requests_per_second": r.requests_per_second,
                    "max_rps": r.max_rps,
                    "error_rate": r.error_rate,
                    "performance_grade": r.performance_grade,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
            data = [dto(r) for r in rows]
            return json.dumps({"status": "success", "count": len(data), "endpoints": data})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to get endpoint results: {str(e)}"})


@tool(
    name="get_qa_perf_executions",
    description="List performance test executions with optional filters: status (PENDING/RUNNING/COMPLETED/FAILED), environment, limit",
    show_result=False,
)
def get_perf_executions(status: Optional[str] = None, environment: Optional[str] = None, limit: int = 20) -> str:
    try:
        return list_perf_executions_raw(status=status, environment=environment, limit=limit)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool(
    name="get_qa_perf_execution",
    description="Get a single performance execution by execution_id (DB-backed)",
    show_result=False,
)
def get_perf_execution(execution_id: str) -> str:
    try:
        return get_perf_execution_raw(execution_id)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool(
    name="get_qa_perf_endpoint_results",
    description="List endpoint-level performance results for a given execution_id",
    show_result=False,
)
def get_perf_endpoint_results(execution_id: str) -> str:
    try:
        return get_perf_endpoint_results_raw(execution_id)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool(
    name="get_qa_mappings_full",
    description="Get App-Environment-Country mappings with all model fields. Optional filters by app_code, env_code, country_code.",
    show_result=False,
)
def list_mappings_full(app_code: Optional[str] = None, env_code: Optional[str] = None, country_code: Optional[str] = None) -> str:
    """Return detailed mapping records exposing all AppEnvironmentCountryMapping fields.

    Args:
        app_code: Optional application code to filter (e.g., "EVA").
        env_code: Optional environment code to filter (e.g., "STA", "UAT", "PRD").
        country_code: Optional country code to filter (e.g., "RO").

    Returns:
        JSON string containing a list of mappings with full fields.
    """
    try:
        return _list_mappings_full_impl(app_code=app_code, env_code=env_code, country_code=country_code)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to fetch mappings: {str(e)}"})


def list_mappings_full_raw(app_code: Optional[str] = None, env_code: Optional[str] = None, country_code: Optional[str] = None) -> str:
    """Raw function variant of get_qa_mappings_full for direct imports/tests."""
    return _list_mappings_full_impl(app_code=app_code, env_code=env_code, country_code=country_code)


def _list_mappings_full_impl(app_code: Optional[str], env_code: Optional[str], country_code: Optional[str]) -> str:
    engine = db_manager.engine
    with Session(engine) as session:
        # Resolve codes to IDs when provided
        app_id = None
        env_id = None
        ctry_id = None
        if app_code:
            app_id = session.exec(select(Apps.id).where(Apps.app_code == app_code)).first()
            if app_id is None:
                return json.dumps({"status": "success", "count": 0, "mappings": []})
        if env_code:
            env_id = session.exec(select(EnvModel.id).where(EnvModel.env_code == env_code)).first()
            if env_id is None:
                return json.dumps({"status": "success", "count": 0, "mappings": []})
        if country_code:
            ctry_id = session.exec(select(Countries.id).where(Countries.country_code == country_code)).first()
            if ctry_id is None:
                return json.dumps({"status": "success", "count": 0, "mappings": []})

        q = select(AppEnvironmentCountryMapping)
        if app_id is not None:
            q = q.where(AppEnvironmentCountryMapping.application_id == app_id)
        if env_id is not None:
            q = q.where(AppEnvironmentCountryMapping.environment_id == env_id)
        if ctry_id is not None:
            q = q.where(AppEnvironmentCountryMapping.country_id == ctry_id)

        rows = session.exec(q).all()

        def dto(m: AppEnvironmentCountryMapping) -> dict:
            # Access relationships while session is open
            app = m.application
            env = m.environment
            c = m.country
            return {
                "id": m.id,
                "application_id": m.application_id,
                "environment_id": m.environment_id,
                "country_id": m.country_id,
                "app_code": getattr(app, "app_code", None),
                "app_name": getattr(app, "app_name", None),
                "env_code": getattr(env, "env_code", None),
                "env_name": getattr(env, "env_name", None),
                "country_code": getattr(c, "country_code", None),
                "country_name": getattr(c, "country_name", None),
                "base_url": m.base_url,
                "protocol": m.protocol,
                "default_headers": m.default_headers or {},
                "auth_config": m.auth_config or {},
                "performance_config": m.performance_config or {},
                "max_response_time_ms": m.max_response_time_ms,
                "max_error_rate_percent": float(m.max_error_rate_percent) if m.max_error_rate_percent is not None else None,
                "is_active": m.is_active,
                "launched_date": m.launched_date.isoformat() if m.launched_date else None,
                "deprecated_date": m.deprecated_date.isoformat() if m.deprecated_date else None,
                "priority": m.priority,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                "is_currently_active": m.is_currently_active,
                "deployment_duration_days": m.deployment_duration_days,
                "full_configuration": m.full_configuration,
            }

        data = [dto(m) for m in rows]
        return json.dumps({"status": "success", "count": len(data), "mappings": data})


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


@tool(
    name="qa_endpoints",
    description="List available application endpoints for a given app, environment, and country (includes global and country-specific).",
    show_result=False,
)
def list_endpoints(app_code: str, environment_code: str, country_code: str) -> str:
    """
    List endpoints discovered for the given app/environment/country using the unified application_endpoints model.

    Args:
        app_code: Application code (e.g., "EVA")
        environment_code: Environment code (e.g., "STA", "UAT", "PRD")
        country_code: Country code (e.g., "RO")

    Returns:
        str: JSON string with a list of endpoints (name, url, method, scope)
    """
    try:
        svc = build_default_service()
        eps = svc.discover_endpoints(app_code, environment_code, country_code)
        return json.dumps({
            "status": "success",
            "count": len(eps),
            "endpoints": eps,
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to list endpoints: {str(e)}",
        })
