#!/usr/bin/env python3
"""
API REST simplificada para métricas de Prometheus - Frontend React.

Lee directamente las métricas de Prometheus sin usar la API de queries.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import requests
import re
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="QA Intelligence Metrics API",
    description="API REST para métricas de performance QA",
    version="1.0.0"
)

# CORS para React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URLs de métricas
PROMETHEUS_METRICS_URL = "http://localhost:9400/metrics"
ENDPOINT_METRICS_URL = "http://localhost:9401/metrics"

def parse_prometheus_metrics(metrics_text: str) -> Dict[str, List[Dict]]:
    """Parsea métricas de Prometheus desde texto."""
    metrics = {}
    lines = metrics_text.strip().split('\n')
    
    current_metric_name = None
    current_metric_type = None
    current_metric_help = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            if line.startswith('# HELP'):
                parts = line.split(' ', 3)
                if len(parts) >= 3:
                    current_metric_help = parts[2] if len(parts) == 3 else ' '.join(parts[3:])
                    current_metric_name = parts[2]
            elif line.startswith('# TYPE'):
                parts = line.split(' ', 3)
                if len(parts) >= 3:
                    current_metric_type = parts[3] if len(parts) > 3 else parts[2]
            continue
        
        # Parse metric line: metric_name{labels} value timestamp
        match = re.match(r'([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]*)\}\s+([^\s]+)(?:\s+([^\s]+))?', line)
        if not match:
            # Try simple metric without labels
            match = re.match(r'([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([^\s]+)(?:\s+([^\s]+))?', line)
            if match:
                metric_name = match.group(1)
                value = match.group(2)
                timestamp = match.group(3) if len(match.groups()) > 2 else None
                labels = {}
            else:
                continue
        else:
            metric_name = match.group(1)
            labels_str = match.group(2)
            value = match.group(3)
            timestamp = match.group(4)
            
            # Parse labels
            labels = {}
            if labels_str:
                for label_pair in labels_str.split(','):
                    if '=' in label_pair:
                        key, val = label_pair.split('=', 1)
                        labels[key.strip()] = val.strip('"')
        
        if metric_name not in metrics:
            metrics[metric_name] = []
        
        try:
            metrics[metric_name].append({
                'labels': labels,
                'value': float(value),
                'timestamp': float(timestamp) if timestamp else None
            })
        except ValueError:
            # Skip non-numeric values
            continue
    
    return metrics

@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "QA Intelligence Metrics API - Simplified",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics_sources": [PROMETHEUS_METRICS_URL, ENDPOINT_METRICS_URL]
    }

@app.get("/api/v1/executions/summary")
async def get_executions_summary():
    """Resumen de ejecuciones de performance tests con información de apps y countries."""
    try:
        # Import database components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        from database.connection import db_manager
        from database.models.performance_test_executions import PerformanceTestExecution, ExecutionStatus
        from database.repositories import create_unit_of_work_factory
        from database.repositories.unit_of_work import UnitOfWorkFactory
        from sqlmodel import Session, select, func, desc
        import re
        
        def extract_app_info_with_repos(execution_name: str, execution_environment: str, uow):
            """Extract app and country information using proper repositories."""
            app_info: dict = {"app_name": None, "app_code": None, "country_name": None, "country_code": None}
            
            try:
                # Extract app code from execution name
                if not execution_name:
                    return app_info
                    
                execution_name_lower = execution_name.lower()
                app_code = None
                
                # Check for known apps in execution name
                if "eva" in execution_name_lower:
                    app_code = "EVA"
                elif "oneapp" in execution_name_lower:
                    app_code = "ONEAPP"
                elif "ecommerce" in execution_name_lower:
                    app_code = "EVA"  # Assuming ecommerce is part of EVA
                else:
                    # Try to extract first part of execution name
                    match = re.match(r'^([A-Za-z]+)', execution_name)
                    if match:
                        app_code = match.group(1).upper()
                
                if not app_code:
                    return app_info
                
                # Get app information using repository
                app = uow.apps.get_by_code(app_code)
                if app:
                    app_info["app_name"] = app.app_name
                    app_info["app_code"] = app.app_code
                    
                    # Try to get country from mappings using environment
                    if execution_environment:
                        try:
                            # Get mappings for this app by app code
                            mappings = uow.app_environment_country_mappings.get_by_application(app.app_code)
                            if mappings:
                                # Find mapping that matches environment or use first one
                                selected_mapping = None
                                for mapping in mappings:
                                    env = uow.environments.get_by_id(mapping.environment_id)
                                    if env and env.environment_code == execution_environment:
                                        selected_mapping = mapping
                                        break
                                
                                # If no exact match, use first mapping
                                if not selected_mapping and mappings:
                                    selected_mapping = mappings[0]
                                
                                if selected_mapping:
                                    country = uow.countries.get_by_id(selected_mapping.country_id)
                                    if country:
                                        app_info["country_name"] = country.country_name
                                        app_info["country_code"] = country.country_code
                        except Exception as e:
                            logger.debug(f"Could not find environment mapping: {e}")
                else:
                    # App not found in database, use extracted code
                    app_info["app_name"] = app_code
                    app_info["app_code"] = app_code
                    
            except Exception as e:
                logger.warning(f"Error extracting app info: {e}")
            
            return app_info
        
        # Create Unit of Work for proper transaction management
        uow_factory = UnitOfWorkFactory(db_manager.engine)
        
        with uow_factory.create_scope() as uow:
            # Get status counts using database
            status_counts = {}
            for status in ExecutionStatus:
                count_stmt = select(func.count()).select_from(PerformanceTestExecution).where(
                    PerformanceTestExecution.status == status
                )
                count = uow.session.exec(count_stmt).first() or 0
                status_counts[status.value] = count
            
            # Get recent executions for app/country breakdown
            recent_stmt = select(PerformanceTestExecution).order_by(
                desc(PerformanceTestExecution.created_at)
            ).limit(20)
            recent_executions = uow.session.exec(recent_stmt).all()
            
            # Analyze app and country distribution
            app_breakdown = {}
            country_breakdown = {}
            environment_breakdown = {}
            
            for execution in recent_executions:
                app_info = extract_app_info_with_repos(
                    getattr(execution, "execution_name", ""),
                    getattr(execution, "execution_environment", ""),
                    uow
                )
                
                # App breakdown
                app_key = app_info["app_code"] or "Unknown"
                if app_key not in app_breakdown:
                    app_breakdown[app_key] = {
                        "app_name": app_info["app_name"] or app_key,
                        "app_code": app_key,
                        "total": 0,
                        "completed": 0,
                        "failed": 0,
                        "running": 0,
                        "pending": 0
                    }
                
                app_breakdown[app_key]["total"] += 1
                status = execution.status.value if execution.status else "UNKNOWN"
                if status == "COMPLETED":
                    app_breakdown[app_key]["completed"] += 1
                elif status == "FAILED":
                    app_breakdown[app_key]["failed"] += 1
                elif status == "RUNNING":
                    app_breakdown[app_key]["running"] += 1
                elif status == "PENDING":
                    app_breakdown[app_key]["pending"] += 1
                
                # Country breakdown
                country_key = app_info["country_code"] or "Unknown"
                if country_key not in country_breakdown:
                    country_breakdown[country_key] = {
                        "country_name": app_info["country_name"] or country_key,
                        "country_code": country_key,
                        "total": 0,
                        "completed": 0,
                        "failed": 0
                    }
                
                country_breakdown[country_key]["total"] += 1
                if status == "COMPLETED":
                    country_breakdown[country_key]["completed"] += 1
                elif status == "FAILED":
                    country_breakdown[country_key]["failed"] += 1
                
                # Environment breakdown
                env_key = getattr(execution, "execution_environment", None) or "Unknown"
                if env_key not in environment_breakdown:
                    environment_breakdown[env_key] = {"total": 0, "completed": 0, "failed": 0}
                
                environment_breakdown[env_key]["total"] += 1
                if status == "COMPLETED":
                    environment_breakdown[env_key]["completed"] += 1
                elif status == "FAILED":
                    environment_breakdown[env_key]["failed"] += 1
            
            completed = status_counts.get("COMPLETED", 0)
            failed = status_counts.get("FAILED", 0)
            total_tests = completed + failed
            
            return {
                "summary": {
                    "total_completed": completed,
                    "total_failed": failed,
                    "total_running": status_counts.get("RUNNING", 0),
                    "total_pending": status_counts.get("PENDING", 0),
                    "success_rate": (completed / total_tests * 100) if total_tests > 0 else 0,
                    "total_tests": total_tests
                },
                "breakdown_by_app": list(app_breakdown.values()),
                "breakdown_by_country": list(country_breakdown.values()),
                "breakdown_by_environment": dict(environment_breakdown),
                "current_states": status_counts,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error getting executions summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/summary")
async def get_endpoints_summary():
    """Resumen de métricas por endpoint con información de apps y countries."""
    try:
        # Import database components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        from database.connection import db_manager
        from database.models.performance_endpoint_results import PerformanceEndpointResults
        from database.models.performance_test_executions import PerformanceTestExecution
        from database.repositories import create_unit_of_work_factory
        from database.repositories.unit_of_work import UnitOfWorkFactory
        from sqlmodel import Session, select, desc
        import re
        
        def extract_app_info_with_repos(execution_name: str, execution_environment: str, uow):
            """Extract app and country information using proper repositories."""
            app_info: dict = {"app_name": None, "app_code": None, "country_name": None, "country_code": None}
            
            try:
                # Extract app code from execution name
                if not execution_name:
                    return app_info
                    
                execution_name_lower = execution_name.lower()
                app_code = None
                
                # Check for known apps in execution name
                if "eva" in execution_name_lower:
                    app_code = "EVA"
                elif "oneapp" in execution_name_lower:
                    app_code = "ONEAPP"
                elif "ecommerce" in execution_name_lower:
                    app_code = "EVA"  # Assuming ecommerce is part of EVA
                else:
                    # Try to extract first part of execution name
                    match = re.match(r'^([A-Za-z]+)', execution_name)
                    if match:
                        app_code = match.group(1).upper()
                
                if not app_code:
                    return app_info
                
                # Get app information using repository
                app = uow.apps.get_by_code(app_code)
                if app:
                    app_info["app_name"] = app.app_name
                    app_info["app_code"] = app.app_code
                    
                    # Try to get country from mappings using environment
                    if execution_environment:
                        try:
                            # Get mappings for this app by app code
                            mappings = uow.app_environment_country_mappings.get_by_application(app.app_code)
                            if mappings:
                                # Find mapping that matches environment or use first one
                                selected_mapping = None
                                for mapping in mappings:
                                    env = uow.environments.get_by_id(mapping.environment_id)
                                    if env and env.environment_code == execution_environment:
                                        selected_mapping = mapping
                                        break
                                
                                # If no exact match, use first mapping
                                if not selected_mapping and mappings:
                                    selected_mapping = mappings[0]
                                
                                if selected_mapping:
                                    country = uow.countries.get_by_id(selected_mapping.country_id)
                                    if country:
                                        app_info["country_name"] = country.country_name
                                        app_info["country_code"] = country.country_code
                        except Exception as e:
                            logger.debug(f"Could not find environment mapping: {e}")
                else:
                    # App not found in database, use extracted code
                    app_info["app_name"] = app_code
                    app_info["app_code"] = app_code
                    
            except Exception as e:
                logger.warning(f"Error extracting app info: {e}")
            
            return app_info
        
        # Create Unit of Work for proper transaction management
        uow_factory = UnitOfWorkFactory(db_manager.engine)
        
        with uow_factory.create_scope() as uow:
            # Get recent endpoint results
            endpoint_stmt = select(PerformanceEndpointResults).order_by(
                desc(PerformanceEndpointResults.created_at)
            ).limit(50)
            
            endpoint_results = uow.session.exec(endpoint_stmt).all()
            
            # Get execution information for each endpoint result
            execution_cache = {}
            endpoints = {}
            app_endpoint_breakdown = {}
            country_endpoint_breakdown = {}
            
            for endpoint_result in endpoint_results:
                execution_id = getattr(endpoint_result, "execution_id", None)
                if not execution_id:
                    continue
                
                # Get execution data from cache or database
                if execution_id not in execution_cache:
                    exec_stmt = select(PerformanceTestExecution).where(
                        PerformanceTestExecution.execution_id == execution_id
                    )
                    execution = uow.session.exec(exec_stmt).first()
                    execution_cache[execution_id] = execution
                else:
                    execution = execution_cache[execution_id]
                
                if not execution:
                    continue
                
                endpoint_name = getattr(endpoint_result, "endpoint_name", "unknown")
                method = getattr(endpoint_result, "http_method", "unknown")
                key = f"{method} {endpoint_name}"
                
                # Extract app and country information
                app_info = extract_app_info_with_repos(
                    getattr(execution, "execution_name", ""),
                    getattr(execution, "execution_environment", ""),
                    uow
                )
                endpoint_name = getattr(endpoint_result, "endpoint_name", "unknown")
                method = getattr(endpoint_result, "http_method", "unknown")
                key = f"{method} {endpoint_name}"
                
                # Extract app and country information
                app_info = extract_app_info_with_repos(
                    getattr(execution, "execution_name", ""),
                    getattr(execution, "execution_environment", ""),
                    uow
                )
                
                if key not in endpoints:
                    endpoints[key] = {
                        'endpoint': endpoint_name,
                        'method': method,
                        'metrics': {
                            'total_requests': 0,
                            'successful_requests': 0,
                            'failed_requests': 0,
                            'avg_response_time': 0,
                            'p95_response_time': 0,
                            'error_rate': 0,
                            'rps': 0,
                            'performance_grade': 'A'
                        },
                        'test_count': 0,
                        'apps': set(),
                        'countries': set(),
                        'environments': set()
                    }
                
                # Aggregate metrics
                endpoint_data = endpoints[key]
                endpoint_data['test_count'] += 1
                endpoint_data['metrics']['total_requests'] += getattr(endpoint_result, "total_requests", 0) or 0
                endpoint_data['metrics']['successful_requests'] += getattr(endpoint_result, "successful_requests", 0) or 0
                endpoint_data['metrics']['failed_requests'] += getattr(endpoint_result, "failed_requests", 0) or 0
                
                # Average metrics (simple approach - could be weighted by request count)
                if getattr(endpoint_result, "avg_response_time", None):
                    current_avg = endpoint_data['metrics']['avg_response_time']
                    new_avg = getattr(endpoint_result, "avg_response_time", 0)
                    endpoint_data['metrics']['avg_response_time'] = (current_avg + new_avg) / 2
                
                if getattr(endpoint_result, "p95_response_time", None):
                    current_p95 = endpoint_data['metrics']['p95_response_time']
                    new_p95 = getattr(endpoint_result, "p95_response_time", 0)
                    endpoint_data['metrics']['p95_response_time'] = max(current_p95, new_p95)
                
                if getattr(endpoint_result, "error_rate", None):
                    current_error = endpoint_data['metrics']['error_rate']
                    new_error = getattr(endpoint_result, "error_rate", 0)
                    endpoint_data['metrics']['error_rate'] = max(current_error, new_error)
                
                if getattr(endpoint_result, "requests_per_second", None):
                    current_rps = endpoint_data['metrics']['rps']
                    new_rps = getattr(endpoint_result, "requests_per_second", 0)
                    endpoint_data['metrics']['rps'] = (current_rps + new_rps) / 2
                
                # Track apps, countries, environments
                if app_info["app_code"]:
                    endpoint_data['apps'].add(f"{app_info['app_code']} ({app_info['app_name']})")
                if app_info["country_code"]:
                    endpoint_data['countries'].add(f"{app_info['country_code']} ({app_info['country_name']})")
                if getattr(execution, "execution_environment", None):
                    endpoint_data['environments'].add(getattr(execution, "execution_environment"))
                
                # App breakdown
                app_key = app_info["app_code"] or "Unknown"
                if app_key not in app_endpoint_breakdown:
                    app_endpoint_breakdown[app_key] = {
                        "app_name": app_info["app_name"] or app_key,
                        "app_code": app_key,
                        "endpoints_tested": set(),
                        "total_requests": 0,
                        "avg_response_time": 0
                    }
                
                app_endpoint_breakdown[app_key]["endpoints_tested"].add(endpoint_name)
                app_endpoint_breakdown[app_key]["total_requests"] += getattr(endpoint_result, "total_requests", 0) or 0
                
                # Country breakdown
                country_key = app_info["country_code"] or "Unknown"
                if country_key not in country_endpoint_breakdown:
                    country_endpoint_breakdown[country_key] = {
                        "country_name": app_info["country_name"] or country_key,
                        "country_code": country_key,
                        "endpoints_tested": set(),
                        "total_requests": 0
                    }
                
                country_endpoint_breakdown[country_key]["endpoints_tested"].add(endpoint_name)
                country_endpoint_breakdown[country_key]["total_requests"] += getattr(endpoint_result, "total_requests", 0) or 0
            
            # Convert sets to lists and counts for JSON serialization
            for endpoint_data in endpoints.values():
                endpoint_data['apps'] = list(endpoint_data['apps'])
                endpoint_data['countries'] = list(endpoint_data['countries'])
                endpoint_data['environments'] = list(endpoint_data['environments'])
                
                # Calculate success rate
                total = endpoint_data['metrics']['total_requests']
                successful = endpoint_data['metrics']['successful_requests']
                endpoint_data['metrics']['success_rate'] = (successful / total * 100) if total > 0 else 0
            
            # Convert sets to counts for breakdown data
            for app_data in app_endpoint_breakdown.values():
                app_data["unique_endpoints"] = len(app_data["endpoints_tested"])
                app_data.pop("endpoints_tested")
                
            for country_data in country_endpoint_breakdown.values():
                country_data["unique_endpoints"] = len(country_data["endpoints_tested"])
                country_data.pop("endpoints_tested")
            
            return {
                "endpoints": list(endpoints.values()),
                "total_endpoints": len(endpoints),
                "breakdown_by_app": list(app_endpoint_breakdown.values()),
                "breakdown_by_country": list(country_endpoint_breakdown.values()),
                "summary": {
                    "total_unique_endpoints": len(endpoints),
                    "total_tests_analyzed": len(endpoint_results),
                    "apps_involved": len(app_endpoint_breakdown),
                    "countries_involved": len(country_endpoint_breakdown)
                },
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error getting endpoints summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/problems")
async def get_endpoint_problems():
    """Detecta endpoints con problemas."""
    try:
        response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        problems = []
        
        # High error rate (>5%)
        if 'qa_perf_endpoint_error_rate_percent' in metrics:
            for metric in metrics['qa_perf_endpoint_error_rate_percent']:
                if metric['value'] > 5:
                    problems.append({
                        "type": "high_error_rate",
                        "severity": "critical" if metric['value'] > 50 else "warning",
                        "endpoint": metric['labels'].get('endpoint', 'unknown'),
                        "method": metric['labels'].get('method', 'unknown'),
                        "value": metric['value'],
                        "threshold": 5.0,
                        "message": f"Error rate {metric['value']:.1f}% exceeds threshold"
                    })
        
        # Slow response time (>1000ms)
        if 'qa_perf_endpoint_p95_response_time_ms' in metrics:
            for metric in metrics['qa_perf_endpoint_p95_response_time_ms']:
                if metric['value'] > 1000:
                    problems.append({
                        "type": "slow_response",
                        "severity": "critical" if metric['value'] > 2000 else "warning",
                        "endpoint": metric['labels'].get('endpoint', 'unknown'),
                        "method": metric['labels'].get('method', 'unknown'),
                        "value": metric['value'],
                        "threshold": 1000.0,
                        "message": f"P95 response time {metric['value']:.0f}ms exceeds threshold"
                    })
        
        return {
            "problems": problems,
            "total_problems": len(problems),
            "critical_problems": len([p for p in problems if p['severity'] == 'critical']),
            "warning_problems": len([p for p in problems if p['severity'] == 'warning']),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detecting problems: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/endpoints/{endpoint_name}")
async def get_endpoint_detail(endpoint_name: str, method: Optional[str] = None):
    """Detalles de un endpoint específico."""
    try:
        response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        
        endpoint_data = {
            'endpoint': endpoint_name,
            'method': method,
            'metrics': {}
        }
        
        metric_types = {
            'qa_perf_endpoint_requests_total': 'requests',
            'qa_perf_endpoint_p95_response_time_ms': 'p95_response_time',
            'qa_perf_endpoint_error_rate_percent': 'error_rate',
            'qa_perf_endpoint_rps': 'rps',
            'qa_perf_endpoint_performance_grade': 'performance_grade'
        }
        
        for metric_name, field_name in metric_types.items():
            if metric_name in metrics:
                for metric in metrics[metric_name]:
                    if (metric['labels'].get('endpoint') == endpoint_name and
                        (method is None or metric['labels'].get('method') == method)):
                        endpoint_data['metrics'][field_name] = metric['value']
        
        return endpoint_data
        
    except Exception as e:
        logger.error(f"Error getting endpoint detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/executions/recent")
async def get_recent_executions(
    status: Optional[str] = None,
    environment: Optional[str] = None,
    limit: int = 10
):
    """Obtiene las ejecuciones más recientes de performance tests."""
    try:
        # Import database components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        from database.connection import db_manager
        from database.models.performance_test_executions import PerformanceTestExecution, ExecutionStatus
        from database.repositories import create_unit_of_work_factory
        from database.repositories.unit_of_work import UnitOfWorkFactory
        from sqlmodel import Session, select, desc
        import re
        
        def extract_app_info_with_repos(execution_name: str, execution_environment: str, uow):
            """Extract app and country information using proper repositories."""
            app_info: dict = {"app_name": None, "app_code": None, "country_name": None, "country_code": None}
            
            try:
                # Extract app code from execution name
                if not execution_name:
                    return app_info
                    
                execution_name_lower = execution_name.lower()
                app_code = None
                
                # Check for known apps in execution name
                if "eva" in execution_name_lower:
                    app_code = "EVA"
                elif "oneapp" in execution_name_lower:
                    app_code = "ONEAPP"
                elif "ecommerce" in execution_name_lower:
                    app_code = "EVA"  # Assuming ecommerce is part of EVA
                else:
                    # Try to extract first part of execution name
                    match = re.match(r'^([A-Za-z]+)', execution_name)
                    if match:
                        app_code = match.group(1).upper()
                
                if not app_code:
                    return app_info
                
                # Get app information using repository
                app = uow.apps.get_by_code(app_code)
                if app:
                    app_info["app_name"] = app.app_name
                    app_info["app_code"] = app.app_code
                    
                    # Try to get country from mappings using environment
                    if execution_environment:
                        try:
                            # Get mappings for this app by app code
                            mappings = uow.app_environment_country_mappings.get_by_application(app.app_code)
                            if mappings:
                                # Find mapping that matches environment or use first one
                                selected_mapping = None
                                for mapping in mappings:
                                    env = uow.environments.get_by_id(mapping.environment_id)
                                    if env and env.environment_code == execution_environment:
                                        selected_mapping = mapping
                                        break
                                
                                # If no exact match, use first mapping
                                if not selected_mapping and mappings:
                                    selected_mapping = mappings[0]
                                
                                if selected_mapping:
                                    country = uow.countries.get_by_id(selected_mapping.country_id)
                                    if country:
                                        app_info["country_name"] = country.country_name
                                        app_info["country_code"] = country.country_code
                        except Exception as e:
                            logger.debug(f"Could not find environment mapping: {e}")
                            
                            # Fallback: try to infer from environment name
                            env_lower = execution_environment.lower()
                            if "ro" in env_lower or "romania" in env_lower:
                                app_info["country_name"] = "Romania"
                                app_info["country_code"] = "RO"
                            elif "fr" in env_lower or "france" in env_lower:
                                app_info["country_name"] = "France"
                                app_info["country_code"] = "FR"
                            elif "sta" in env_lower:
                                # STA could be a staging environment, try default
                                app_info["country_name"] = "Romania"  # Default fallback
                                app_info["country_code"] = "RO"
                else:
                    # App not found in database, use extracted code
                    app_info["app_name"] = app_code
                    app_info["app_code"] = app_code
                    
            except Exception as e:
                logger.warning(f"Error extracting app info: {e}")
            
            return app_info
        
        # Create Unit of Work for proper transaction management
        uow_factory = UnitOfWorkFactory(db_manager.engine)
        
        with uow_factory.create_scope() as uow:
            stmt = select(PerformanceTestExecution)
            
            # Apply filters
            if status:
                try:
                    enum_status = ExecutionStatus[status.upper()]
                    stmt = stmt.where(PerformanceTestExecution.status == enum_status)
                except KeyError:
                    raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            
            if environment:
                stmt = stmt.where(PerformanceTestExecution.execution_environment == environment)
            
            # Order by created_at desc to get most recent first
            stmt = stmt.order_by(desc(PerformanceTestExecution.created_at))
            
            # Apply limit
            stmt = stmt.limit(max(1, int(limit)))
            
            executions = uow.session.exec(stmt).all()
            
            # Convert to expected format for frontend
            executions_data = []
            for ex in executions:
                # Calculate success rate
                total_requests = getattr(ex, "total_requests", 0) or 0
                successful_requests = getattr(ex, "successful_requests", 0) or 0
                failed_requests = getattr(ex, "failed_requests", 0) or 0
                
                success_rate = 0
                if total_requests > 0:
                    success_rate = (successful_requests / total_requests) * 100
                
                error_rate = getattr(ex, "error_rate", 0) or 0
                
                # Extract app and country information using repositories
                app_info = extract_app_info_with_repos(
                    getattr(ex, "execution_name", ""),
                    getattr(ex, "execution_environment", ""),
                    uow
                )
                
                exec_dict = {
                    "id": str(ex.id) if ex.id else None,
                    "execution_id": getattr(ex, "execution_id", None),
                    "execution_name": getattr(ex, "execution_name", None) or f"Test-{ex.id}",
                    "status": ex.status.value if ex.status else "UNKNOWN",
                    "metrics": {
                        "total_requests": total_requests,
                        "successful_requests": successful_requests,
                        "failed_requests": failed_requests,
                        "error_rate": error_rate,
                        "avg_response_time": getattr(ex, "avg_response_time", None),
                        "p95_response_time": getattr(ex, "p95_response_time", None),
                        "p99_response_time": getattr(ex, "p99_response_time", None),
                        "min_response_time": getattr(ex, "min_response_time", None),
                        "max_response_time": getattr(ex, "max_response_time", None),
                        "rps": getattr(ex, "avg_rps", None)
                    },
                    "summary": {
                        "success_rate": round(success_rate, 2),
                        "is_successful": success_rate >= 95,  # Consider 95%+ as successful
                        "endpoints_tested": 1,  # Default to 1 if not available
                        "total_response_time": getattr(ex, "avg_response_time", None)
                    },
                    "test_context": {
                        "execution_environment": getattr(ex, "execution_environment", None),
                        "gatling_report_path": getattr(ex, "gatling_report_path", None),
                        "test_type": "performance",
                        "app_name": app_info["app_name"],
                        "app_code": app_info["app_code"],
                        "country_name": app_info["country_name"], 
                        "country_code": app_info["country_code"]
                    },
                    "timestamps": {
                        "created_at": ex.created_at.isoformat() if ex.created_at else None,
                        "updated_at": ex.updated_at.isoformat() if ex.updated_at else None,
                    }
                }
                executions_data.append(exec_dict)
            
            return {
                "status": "success",
                "total": len(executions_data),
                "count": len(executions_data),
                "executions": executions_data,
                "filters": {
                    "status": status,
                    "environment": environment,
                    "limit": limit
                },
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/executions/{execution_id}/details")
async def get_execution_details(execution_id: str):
    """Obtiene los detalles completos de una ejecución específica incluyendo información de endpoints, apps y countries."""
    try:
        # Import database components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        from database.connection import db_manager
        from database.models.performance_test_executions import PerformanceTestExecution
        from database.models.performance_endpoint_results import PerformanceEndpointResults
        from database.repositories import create_unit_of_work_factory
        from database.repositories.unit_of_work import UnitOfWorkFactory
        from sqlmodel import Session, select
        import re
        
        def extract_app_info_with_repos(execution_name: str, execution_environment: str, uow):
            """Extract app and country information using proper repositories."""
            app_info: dict = {"app_name": None, "app_code": None, "country_name": None, "country_code": None}
            
            try:
                # Extract app code from execution name
                if not execution_name:
                    return app_info
                    
                execution_name_lower = execution_name.lower()
                app_code = None
                
                # Check for known apps in execution name
                if "eva" in execution_name_lower:
                    app_code = "EVA"
                elif "oneapp" in execution_name_lower:
                    app_code = "ONEAPP"
                elif "ecommerce" in execution_name_lower:
                    app_code = "EVA"  # Assuming ecommerce is part of EVA
                else:
                    # Try to extract first part of execution name
                    match = re.match(r'^([A-Za-z]+)', execution_name)
                    if match:
                        app_code = match.group(1).upper()
                
                if not app_code:
                    return app_info
                
                # Get app information using repository
                app = uow.apps.get_by_code(app_code)
                if app:
                    app_info["app_name"] = app.app_name
                    app_info["app_code"] = app.app_code
                    
                    # Try to get country from mappings using environment
                    if execution_environment:
                        try:
                            # Get mappings for this app by app code
                            mappings = uow.app_environment_country_mappings.get_by_application(app.app_code)
                            if mappings:
                                # Find mapping that matches environment or use first one
                                selected_mapping = None
                                for mapping in mappings:
                                    env = uow.environments.get_by_id(mapping.environment_id)
                                    if env and env.environment_code == execution_environment:
                                        selected_mapping = mapping
                                        break
                                
                                # If no exact match, use first mapping
                                if not selected_mapping and mappings:
                                    selected_mapping = mappings[0]
                                
                                if selected_mapping:
                                    country = uow.countries.get_by_id(selected_mapping.country_id)
                                    if country:
                                        app_info["country_name"] = country.country_name
                                        app_info["country_code"] = country.country_code
                        except Exception as e:
                            logger.debug(f"Could not find environment mapping: {e}")
                            
                            # Fallback: try to infer from environment name
                            env_lower = execution_environment.lower()
                            if "ro" in env_lower or "romania" in env_lower:
                                app_info["country_name"] = "Romania"
                                app_info["country_code"] = "RO"
                            elif "fr" in env_lower or "france" in env_lower:
                                app_info["country_name"] = "France"
                                app_info["country_code"] = "FR"
                            elif "sta" in env_lower:
                                # STA could be a staging environment, try default
                                app_info["country_name"] = "Romania"  # Default fallback
                                app_info["country_code"] = "RO"
                else:
                    # App not found in database, use extracted code
                    app_info["app_name"] = app_code
                    app_info["app_code"] = app_code
                    
            except Exception as e:
                logger.warning(f"Error extracting app info: {e}")
            
            return app_info
        
        # Create Unit of Work for proper transaction management
        uow_factory = UnitOfWorkFactory(db_manager.engine)
        
        with uow_factory.create_scope() as uow:
            # Get execution
            execution_stmt = select(PerformanceTestExecution).where(
                PerformanceTestExecution.execution_id == execution_id
            )
            execution = uow.session.exec(execution_stmt).first()
            
            if not execution:
                raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
            
            # Get endpoint results for this execution
            endpoints_stmt = select(PerformanceEndpointResults).where(
                PerformanceEndpointResults.execution_id == execution_id
            )
            endpoint_results = uow.session.exec(endpoints_stmt).all()
            
            # Extract app and country information using repositories
            app_info = extract_app_info_with_repos(
                getattr(execution, "execution_name", ""),
                getattr(execution, "execution_environment", ""),
                uow
            )
            
            # Calculate execution-level metrics
            total_requests = getattr(execution, "total_requests", 0) or 0
            successful_requests = getattr(execution, "successful_requests", 0) or 0
            failed_requests = getattr(execution, "failed_requests", 0) or 0
            
            success_rate = 0
            error_rate = 0
            if total_requests > 0:
                success_rate = (successful_requests / total_requests) * 100
                error_rate = (failed_requests / total_requests) * 100
            
            # Process endpoint results
            endpoints_data = []
            total_endpoint_requests = 0
            total_endpoint_successes = 0
            total_endpoint_failures = 0
            
            for endpoint in endpoint_results:
                endpoint_total = getattr(endpoint, "total_requests", 0) or 0
                endpoint_success = getattr(endpoint, "successful_requests", 0) or 0
                endpoint_failed = getattr(endpoint, "failed_requests", 0) or 0
                
                endpoint_success_rate = 0
                endpoint_error_rate = 0
                if endpoint_total > 0:
                    endpoint_success_rate = (endpoint_success / endpoint_total) * 100
                    endpoint_error_rate = (endpoint_failed / endpoint_total) * 100
                
                total_endpoint_requests += endpoint_total
                total_endpoint_successes += endpoint_success
                total_endpoint_failures += endpoint_failed
                
                endpoints_data.append({
                    "endpoint_name": getattr(endpoint, "endpoint_name", ""),
                    "http_method": getattr(endpoint, "http_method", ""),
                    "endpoint_url": getattr(endpoint, "endpoint_url", ""),
                    "requests": {
                        "total": endpoint_total,
                        "successful": endpoint_success,
                        "failed": endpoint_failed,
                        "success_rate": round(endpoint_success_rate, 2),
                        "error_rate": round(endpoint_error_rate, 2)
                    },
                    "response_times": {
                        "avg": getattr(endpoint, "avg_response_time", None),
                        "p50": getattr(endpoint, "p50_response_time", None),
                        "p75": getattr(endpoint, "p75_response_time", None),
                        "p95": getattr(endpoint, "p95_response_time", None),
                        "p99": getattr(endpoint, "p99_response_time", None),
                        "min": getattr(endpoint, "min_response_time", None),
                        "max": getattr(endpoint, "max_response_time", None)
                    },
                    "performance": {
                        "rps": getattr(endpoint, "requests_per_second", None),
                        "max_rps": getattr(endpoint, "max_rps", None),
                        "error_rate": getattr(endpoint, "error_rate", None) or round(endpoint_error_rate, 2),
                        "performance_grade": getattr(endpoint, "performance_grade", None)
                    },
                    "test_context": {
                        "concurrent_users": getattr(endpoint, "concurrent_users", None),
                        "test_duration_seconds": getattr(endpoint, "test_duration_seconds", None)
                    }
                })
            
            # Calculate overall endpoint success rate and error rate
            overall_endpoint_success_rate = 0
            overall_endpoint_error_rate = 0
            if total_endpoint_requests > 0:
                overall_endpoint_success_rate = (total_endpoint_successes / total_endpoint_requests) * 100
                overall_endpoint_error_rate = (total_endpoint_failures / total_endpoint_requests) * 100
            
            return {
                "status": "success",
                "execution": {
                    "id": str(execution.id) if execution.id else None,
                    "execution_id": getattr(execution, "execution_id", None),
                    "execution_name": getattr(execution, "execution_name", None) or f"Test-{execution.id}",
                    "status": execution.status.value if execution.status else "UNKNOWN",
                    "execution_environment": getattr(execution, "execution_environment", None),
                    "gatling_report_path": getattr(execution, "gatling_report_path", None),
                    "app_name": app_info["app_name"],
                    "app_code": app_info["app_code"],
                    "country_name": app_info["country_name"],
                    "country_code": app_info["country_code"],
                    "timestamps": {
                        "created_at": execution.created_at.isoformat() if execution.created_at else None,
                        "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
                        "start_time": execution.start_time.isoformat() if hasattr(execution, 'start_time') and execution.start_time else None,
                        "end_time": execution.end_time.isoformat() if hasattr(execution, 'end_time') and execution.end_time else None
                    }
                },
                "endpoints_summary": {
                    "total_endpoints": len(endpoints_data),
                    "total_requests_all_endpoints": total_endpoint_requests,
                    "total_successful_requests": total_endpoint_successes,
                    "total_failed_requests": total_endpoint_failures,
                    "overall_endpoint_success_rate": round(overall_endpoint_success_rate, 2),
                    "overall_endpoint_error_rate": round(overall_endpoint_error_rate, 2),
                    "execution_level_metrics": {
                        "total_requests": total_requests,
                        "successful_requests": successful_requests,
                        "failed_requests": failed_requests,
                        "success_rate": round(success_rate, 2),
                        "error_rate": getattr(execution, "error_rate", None) or round(error_rate, 2),
                        "avg_response_time": getattr(execution, "avg_response_time", None),
                        "p95_response_time": getattr(execution, "p95_response_time", None),
                        "p99_response_time": getattr(execution, "p99_response_time", None),
                        "avg_rps": getattr(execution, "avg_rps", None)
                    }
                },
                "endpoints": endpoints_data,
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/raw")
async def get_raw_metrics():
    """Métricas raw de Prometheus."""
    try:
        prometheus_response = requests.get(PROMETHEUS_METRICS_URL, timeout=10)
        endpoint_response = requests.get(ENDPOINT_METRICS_URL, timeout=10)
        
        return {
            "prometheus_metrics": parse_prometheus_metrics(prometheus_response.text),
            "endpoint_metrics": parse_prometheus_metrics(endpoint_response.text),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting raw metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting QA Intelligence Metrics API")
    print(f"📊 Prometheus Metrics: {PROMETHEUS_METRICS_URL}")
    print(f"🎯 Endpoint Metrics: {ENDPOINT_METRICS_URL}")
    print("🌐 API will be available at: http://localhost:8003")
    print("📚 API docs at: http://localhost:8003/docs")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003,
        log_level="info"
    )
