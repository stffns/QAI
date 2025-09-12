"""
API Tools for QA Intelligence Agent - SIMPLIFIED & CONCISE VERSION

This module provides concise API testing tools using Agno's CustomApiTools
for quick quality assurance workflows.
"""

import json
from typing import Any, Dict, Literal, Optional, cast, List
import time

from agno.tools import tool
from agno.tools.api import CustomApiTools

# Import logging
try:
    from ...logging_config import LogStep, get_logger
    from .test_scenarios_manager import TestScenarioManager
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import LogStep, get_logger
    from src.agent.tools.test_scenarios_manager import TestScenarioManager

logger = get_logger("APITools")


class QAAPITools:
    """Simplified QA API Tools wrapper for concise results"""

    def __init__(self):
        """Initialize API Tools for QA Intelligence"""
        self.api_tools = CustomApiTools()
        self.scenario_manager = TestScenarioManager()
        logger.info("QA API Tools initialized with scenario support")

    def test_endpoint(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Test API endpoint with concise results"""
        try:
            # Validate method
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
            method_upper = method.upper()
            if method_upper not in valid_methods:
                method_upper = "GET"

            method_literal = cast(
                Literal["GET", "POST", "PUT", "DELETE", "PATCH"], method_upper
            )

            # Make request
            if data:
                response = self.api_tools.make_request(
                    endpoint=url, method=method_literal, headers=headers, json_data=data
                )
            else:
                response = self.api_tools.make_request(
                    endpoint=url, method=method_literal, headers=headers
                )

            # Parse response
            if isinstance(response, str):
                try:
                    response_data = json.loads(response)
                except json.JSONDecodeError:
                    response_data = {"raw_response": response}
            else:
                response_data = response

            # Extract key info with type validation
            status_code = response_data.get("status_code", 0)
            if not isinstance(status_code, int):
                status_code = int(status_code) if str(status_code).isdigit() else 0

            response_time = (
                response_data.get("response_time", 0) * 1000
                if response_data.get("response_time")
                else 0
            )
            if not isinstance(response_time, (int, float)):
                response_time = 0

            # Simple status assessment
            if 200 <= status_code < 300:
                status = "✅ SUCCESS"
            elif 300 <= status_code < 400:
                status = "⚠️ REDIRECT"
            elif 400 <= status_code < 500:
                status = "❌ CLIENT ERROR"
            elif status_code >= 500:
                status = "🚨 SERVER ERROR"
            else:
                status = "❓ UNKNOWN"

            # Performance assessment
            if response_time < 500:
                perf = "🚀 FAST"
            elif response_time < 1000:
                perf = "⚡ GOOD"
            elif response_time < 2000:
                perf = "⏱️ SLOW"
            else:
                perf = "🐌 VERY SLOW"

            return {
                "status": status,
                "code": status_code,
                "time": f"{response_time:.0f}ms",
                "performance": perf,
                "success": 200 <= status_code < 300,
            }

        except Exception as e:
            return {
                "status": "❌ ERROR",
                "code": 0,
                "time": "0ms",
                "performance": "🚫 FAILED",
                "success": False,
                "error": str(e),
            }

    def health_check(self, url: str, expected_status: int = 200) -> Dict[str, Any]:
        """Quick health check"""
        result = self.test_endpoint(url, "GET")
        is_healthy = result.get("success") and result.get("code") == expected_status

        return {
            "url": url,
            "status": "🟢 HEALTHY" if is_healthy else "🔴 UNHEALTHY",
            "code": result.get("code", 0),
            "time": result.get("time", "0ms"),
            "healthy": is_healthy,
        }

    def performance_test(self, url: str, iterations: int = 5) -> Dict[str, Any]:
        """Quick performance test"""
        success_count = 0
        times = []

        for _ in range(iterations):
            result = self.test_endpoint(url)
            if result.get("success"):
                success_count += 1
                time_str = result.get("time", "0ms")
                time_val = float(time_str.replace("ms", ""))
                times.append(time_val)

        success_rate = (success_count / iterations) * 100
        avg_time = sum(times) / len(times) if times else 0

        # Simple performance rating
        if success_rate >= 95 and avg_time < 1000:
            rating = "🚀 EXCELLENT"
        elif success_rate >= 90 and avg_time < 2000:
            rating = "✅ GOOD"
        elif success_rate >= 75:
            rating = "⚠️ FAIR"
        else:
            rating = "❌ POOR"

        return {
            "url": url,
            "tests": iterations,
            "success_rate": f"{success_rate:.0f}%",
            "avg_time": f"{avg_time:.0f}ms",
            "rating": rating,
            "passed": success_count,
            "failed": iterations - success_count,
        }
    
    def execute_test_scenario(self, scenario_id: int, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Ejecutar un escenario completo de testing
        
        Args:
            scenario_id: ID del escenario a ejecutar
            base_url: URL base opcional (override de la configuración del mapping)
            
        Returns:
            Dict con resultados del escenario
        """
        try:
            # Obtener el escenario con sus endpoints
            scenario = self.scenario_manager.get_scenario_with_endpoints(scenario_id)
            
            if not scenario:
                return {
                    "success": False,
                    "error": f"Scenario {scenario_id} not found"
                }
            
            scenario_start = time.time()
            results = {
                "scenario_id": scenario_id,
                "scenario_name": scenario["name"],
                "scenario_type": scenario["type"],
                "total_endpoints": scenario["total_endpoints"],
                "base_url": base_url,
                "endpoints_results": [],
                "summary": {
                    "success_count": 0,
                    "failed_count": 0,
                    "error_count": 0,
                    "total_time_ms": 0
                },
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"🎭 Starting scenario: {scenario['name']} ({scenario['type']}) with {scenario['total_endpoints']} endpoints")
            
            # Ejecutar endpoints en orden
            for endpoint in scenario["endpoints"]:
                endpoint_start = time.time()
                
                # Construir URL completa
                endpoint_url = endpoint["endpoint_url"]
                if base_url:
                    # Si se proporciona base_url, reemplazar
                    if endpoint_url.startswith('/'):
                        full_url = base_url.rstrip('/') + endpoint_url
                    else:
                        full_url = base_url.rstrip('/') + '/' + endpoint_url
                else:
                    # Usar URL completa desde la configuración
                    full_url = endpoint_url
                
                # Ejecutar endpoint
                try:
                    endpoint_result = self.test_endpoint(
                        url=full_url,
                        method=endpoint["http_method"],
                        timeout=endpoint.get("custom_timeout_ms", 5000) // 1000
                    )
                    
                    endpoint_time = (time.time() - endpoint_start) * 1000
                    
                    # Determinar si es crítico y afecta el escenario
                    is_critical = endpoint.get("is_critical", False)
                    endpoint_success = endpoint_result.get("success", False)
                    
                    if endpoint_success:
                        results["summary"]["success_count"] += 1
                        status = "✅ SUCCESS"
                    elif is_critical:
                        results["summary"]["error_count"] += 1
                        status = "🚨 CRITICAL FAILURE"
                    else:
                        results["summary"]["failed_count"] += 1
                        status = "⚠️ FAILURE"
                    
                    # Agregar resultado del endpoint
                    results["endpoints_results"].append({
                        "endpoint_id": endpoint["endpoint_id"],
                        "name": endpoint["endpoint_name"],
                        "url": full_url,
                        "method": endpoint["http_method"],
                        "execution_order": endpoint["execution_order"],
                        "is_critical": is_critical,
                        "status": status,
                        "success": endpoint_success,
                        "response_code": endpoint_result.get("code", 0),
                        "response_time_ms": endpoint_time,
                        "performance": endpoint_result.get("performance", "Unknown")
                    })
                    
                    # Si es crítico y falla, verificar si debe parar
                    if is_critical and not endpoint_success and scenario.get("stop_on_critical_failure", False):
                        logger.warning(f"🛑 Stopping scenario due to critical failure: {endpoint['endpoint_name']}")
                        break
                        
                except Exception as e:
                    results["summary"]["error_count"] += 1
                    results["endpoints_results"].append({
                        "endpoint_id": endpoint["endpoint_id"],
                        "name": endpoint["endpoint_name"],
                        "url": full_url,
                        "method": endpoint["http_method"],
                        "status": "❌ ERROR",
                        "success": False,
                        "error": str(e)
                    })
            
            # Calcular métricas finales
            total_time = (time.time() - scenario_start) * 1000
            total_executed = len(results["endpoints_results"])
            success_rate = (results["summary"]["success_count"] / total_executed * 100) if total_executed > 0 else 0
            
            results["summary"]["total_time_ms"] = total_time
            results["summary"]["total_executed"] = total_executed
            results["summary"]["success_rate_percent"] = success_rate
            results["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Determinar estado general del escenario
            if results["summary"]["error_count"] > 0:
                results["overall_status"] = "❌ FAILED"
                results["success"] = False
            elif success_rate >= 90:
                results["overall_status"] = "✅ PASSED"
                results["success"] = True
            else:
                results["overall_status"] = "⚠️ PARTIAL"
                results["success"] = False
            
            logger.info(f"🎭 Scenario completed: {results['overall_status']} ({success_rate:.1f}% success)")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error executing scenario {scenario_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "scenario_id": scenario_id
            }
    
    def list_available_scenarios(self, mapping_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Listar escenarios disponibles
        
        Args:
            mapping_id: ID opcional del mapping para filtrar
            
        Returns:
            Lista de escenarios disponibles
        """
        if mapping_id:
            return self.scenario_manager.list_scenarios_by_mapping(mapping_id)
        else:
            # Si no se especifica mapping, mostrar todos (limitado)
            scenarios = []
            # Esta implementación podría expandirse para buscar en múltiples mappings
            return scenarios


# Initialize global instance
qa_api_tools = QAAPITools()


# Agno tool functions - CONCISE VERSIONS
@tool
def api_test_endpoint(
    url: str,
    method: str = "GET",
    headers: Optional[str] = None,
    data: Optional[str] = None,
) -> str:
    """
    Test API endpoint - Returns ONLY the test result, no additional analysis needed.

    Args:
        url: API endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: JSON string of headers (optional)
        data: JSON string of data (optional)

    Returns:
        FINAL result - no further analysis required
    """
    try:
        # Parse headers and data if provided
        headers_dict = json.loads(headers) if headers else None
        data_dict = json.loads(data) if data else None

        result = qa_api_tools.test_endpoint(url, method, headers_dict, data_dict)

        # Return ONLY the essential info
        status_emoji = "✅" if result["success"] else "❌"
        return f"{status_emoji} {url} → {result['status']} ({result['code']}) in {result['time']}"

    except Exception as e:
        return f"❌ {url} → ERROR: {str(e)}"


@tool
def api_health_check(url: str, expected_status: int = 200) -> str:
    """
    Quick API health check - Returns ONLY the health status, no analysis needed.

    Args:
        url: Health check endpoint URL
        expected_status: Expected HTTP status code (default: 200)

    Returns:
        FINAL health status - no further interpretation required
    """
    try:
        result = qa_api_tools.health_check(url, expected_status)

        # Return ONLY the essential health info
        status_emoji = "🟢" if result["healthy"] else "🔴"
        return f"{status_emoji} {url} → {result['status']} (Code: {result['code']}, Time: {result['time']})"

    except Exception as e:
        return f"❌ {url} → Health check failed: {str(e)}"


@tool
def execute_test_scenario(scenario_id: int, base_url: str = "") -> str:
    """
    Execute a complete test scenario with all its configured endpoints.
    
    Args:
        scenario_id: ID of the scenario to execute
        base_url: Optional base URL to override the mapping configuration
        
    Returns:
        FINAL scenario execution summary - no further analysis needed
    """
    try:
        result = qa_api_tools.execute_test_scenario(
            scenario_id=scenario_id,
            base_url=base_url if base_url else None
        )
        
        if not result.get("success"):
            return f"❌ Scenario {scenario_id} failed: {result.get('error', 'Unknown error')}"
        
        # Create concise summary
        summary = result["summary"]
        scenario_name = result["scenario_name"]
        scenario_type = result["scenario_type"]
        
        status_emoji = "✅" if result["overall_status"].startswith("✅") else "⚠️" if result["overall_status"].startswith("⚠️") else "❌"
        
        success_rate = summary["success_rate_percent"]
        total_time = summary["total_time_ms"]
        
        # Show top 3 results for quick overview
        endpoint_summary = []
        for i, ep in enumerate(result["endpoints_results"][:3]):
            status = "✅" if ep["success"] else "❌"
            endpoint_summary.append(f"{status} {ep['name']} ({ep.get('response_code', 0)})")
        
        endpoint_text = " | ".join(endpoint_summary)
        if len(result["endpoints_results"]) > 3:
            endpoint_text += f" + {len(result['endpoints_results']) - 3} more"
        
        return f"{status_emoji} SCENARIO '{scenario_name}' ({scenario_type}): {success_rate:.0f}% success in {total_time:.0f}ms\n{endpoint_text}"
        
    except Exception as e:
        return f"❌ Error executing scenario {scenario_id}: {str(e)}"


@tool  
def list_test_scenarios(mapping_id: int) -> str:
    """
    List all available test scenarios for a specific mapping.
    
    Args:
        mapping_id: ID of the app/env/country mapping
        
    Returns:
        FINAL list of scenarios - no further processing needed
    """
    try:
        scenarios = qa_api_tools.list_available_scenarios(mapping_id)
        
        if not scenarios:
            return f"📭 No scenarios found for mapping {mapping_id}"
        
        scenario_list = []
        for scenario in scenarios:
            type_emoji = {
                "SMOKE": "💨",
                "FUNCTIONAL": "🧪", 
                "PERFORMANCE": "🚀",
                "REGRESSION": "🔄",
                "SECURITY": "🔒"
            }.get(scenario["type"], "🎭")
            
            scenario_list.append(
                f"{type_emoji} ID:{scenario['id']} - {scenario['name']} ({scenario['endpoints_count']} endpoints)"
            )
        
        return f"🎭 Available scenarios for mapping {mapping_id}:\n" + "\n".join(scenario_list)
        
    except Exception as e:
        return f"❌ Error listing scenarios: {str(e)}"


# Export for toolchain discovery
__all__ = ["api_test_endpoint", "api_health_check"]
