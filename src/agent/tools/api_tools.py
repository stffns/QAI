"""
API Tools for QA Intelligence Agent - SIMPLIFIED & CONCISE VERSION

This module provides concise API testing tools using Agno's CustomApiTools
for quick quality assurance workflows.
"""
import json
from typing import Optional, Dict, Any, Literal, cast
from agno.tools import tool
from agno.tools.api import CustomApiTools

# Import logging
try:
    from ...logging_config import get_logger, LogStep
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger, LogStep

logger = get_logger("APITools")


class QAAPITools:
    """Simplified QA API Tools wrapper for concise results"""
    
    def __init__(self):
        """Initialize API Tools for QA Intelligence"""
        self.api_tools = CustomApiTools()
        logger.info("QA API Tools initialized")
    
    def test_endpoint(self, url: str, method: str = "GET", headers: Optional[Dict] = None, 
                     data: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Test API endpoint with concise results"""
        try:
            # Validate method
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
            method_upper = method.upper()
            if method_upper not in valid_methods:
                method_upper = "GET"
            
            method_literal = cast(Literal["GET", "POST", "PUT", "DELETE", "PATCH"], method_upper)
            
            # Make request
            if data:
                response = self.api_tools.make_request(
                    endpoint=url,
                    method=method_literal,
                    headers=headers,
                    json_data=data
                )
            else:
                response = self.api_tools.make_request(
                    endpoint=url,
                    method=method_literal,
                    headers=headers
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
                
            response_time = response_data.get("response_time", 0) * 1000 if response_data.get("response_time") else 0
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
                "success": 200 <= status_code < 300
            }
            
        except Exception as e:
            return {
                "status": "❌ ERROR",
                "code": 0,
                "time": "0ms",
                "performance": "🚫 FAILED",
                "success": False,
                "error": str(e)
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
            "healthy": is_healthy
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
            "failed": iterations - success_count
        }


# Initialize global instance
qa_api_tools = QAAPITools()


# Agno tool functions - CONCISE VERSIONS
@tool
def api_test_endpoint(url: str, method: str = "GET", headers: Optional[str] = None, 
                     data: Optional[str] = None) -> str:
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
        status_emoji = "✅" if result['success'] else "❌"
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
        status_emoji = "🟢" if result['healthy'] else "🔴"
        return f"{status_emoji} {url} → {result['status']} (Code: {result['code']}, Time: {result['time']})"
        
    except Exception as e:
        return f"❌ {url} → Health check failed: {str(e)}"


@tool
def api_performance_test(
    command: str = "Test endpoint", 
    url: Optional[str] = None,
    app_code: Optional[str] = None,
    env_code: Optional[str] = None,
    country_code: Optional[str] = None,
    virtual_users: int = 3,
    duration_minutes: float = 1.0,
    agent_rps: Optional[float] = None
) -> str:
    """
    Advanced API performance test using QA Intelligence Performance Engine V2.
    
    Supports both simple URL testing and advanced database-driven testing.
    
    Args:
        command: Natural language command (e.g., "Probar EVA_RO en STA con 5 usuarios")
        url: Direct URL to test (optional, overrides database lookup)
        app_code: Application code (e.g., "EVA_RO", "PAYROLL")
        env_code: Environment code (e.g., "STA", "TEST", "PROD")
        country_code: Country code (e.g., "RO", "FR", "BE")
        virtual_users: Number of virtual users (default: 3)
        duration_minutes: Test duration in minutes, supports decimals (default: 1.0)
        agent_rps: Custom RPS override (optional)
    
    Returns:
        Performance test execution status and results summary
    """
    try:
        # Import Performance Tool (SOLID Architecture - Phase 7)
        from .performance_tool import PerformanceToolV2
        
        # Initialize tool
        perf_tool = PerformanceToolV2()
        
        # If direct URL provided, create simple command
        if url:
            simple_command = f"Test {url} with {virtual_users} users for {duration_minutes} minutes"
            if agent_rps:
                simple_command += f" at {agent_rps} RPS"
            
            # Execute simple performance test
            result_json = perf_tool.execute_performance_test(
                command=simple_command,
                virtual_users=virtual_users,
                duration_minutes=duration_minutes,
                agent_rps=agent_rps
            )
            
        else:
            # Build advanced command with database lookup
            params = {}
            if app_code:
                params["app_code"] = app_code
            if env_code:
                params["env_code"] = env_code  
            if country_code:
                params["country_code"] = country_code
            if agent_rps:
                params["agent_rps"] = agent_rps
                
            result_json = perf_tool.execute_performance_test(
                command=command,
                virtual_users=virtual_users,
                duration_minutes=duration_minutes,
                **params
            )
        
        # Parse result
        import json
        try:
            result = json.loads(result_json)
        except json.JSONDecodeError:
            return f"❌ Performance test failed: Invalid response format"
        
        if result.get("success"):
            execution_id = result.get("execution_id", "unknown")
            status = result.get("status", "unknown")
            estimated_duration = result.get("estimated_duration_minutes", "unknown")
            rps_used = result.get("rps_resolved", "unknown")
            
            # Return execution summary
            return (f"⚡ Performance test started successfully!\n"
                   f"🆔 Execution ID: {execution_id}\n"
                   f"📊 Status: {status}\n"
                   f"⏱️ Estimated duration: {estimated_duration} minutes\n"
                   f"🔥 RPS: {rps_used}\n"
                   f"💡 Use get_execution_status({execution_id}) to check progress")
        else:
            error = result.get("error", "Unknown error")
            return f"❌ Performance test failed: {error}"
            
    except ImportError:
        # Fallback to simple test
        return f"⚠️ Advanced performance testing not available. Using basic test for: {url or command}"
        
    except Exception as e:
        return f"❌ Performance test failed: {str(e)}"


@tool
def get_execution_status(execution_id: str) -> str:
    """
    Get status of a performance test execution.
    
    Args:
        execution_id: Execution ID returned from api_performance_test
    
    Returns:
        Current execution status and results (if completed)
    """
    try:
        from .performance_tool import PerformanceToolV2
        
        perf_tool = PerformanceToolV2()
        result_json = perf_tool.get_execution_status(execution_id)
        
        import json
        try:
            result = json.loads(result_json)
        except json.JSONDecodeError:
            return f"❌ Failed to get status: Invalid response format"
        
        if result.get("success"):
            status = result.get("status", "unknown")
            progress = result.get("progress_percentage", 0)
            phase = result.get("current_phase", "unknown")
            
            # If completed, show results
            if status in ["COMPLETED", "SUCCESS"]:
                total_requests = result.get("total_requests", 0)
                successful_requests = result.get("successful_requests", 0)
                failed_requests = result.get("failed_requests", 0)
                mean_time = result.get("mean_response_time", 0)
                p95_time = result.get("p95_response_time", 0)
                
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
                
                return (f"✅ Performance test completed!\n"
                       f"📊 Results: {total_requests} total requests\n"
                       f"✅ Success rate: {success_rate:.1f}% ({successful_requests}/{total_requests})\n" 
                       f"❌ Failed requests: {failed_requests}\n"
                       f"⏱️ Mean response time: {mean_time}ms\n"
                       f"📈 95th percentile: {p95_time}ms")
            
            elif status in ["FAILED", "ERROR"]:
                error_details = result.get("error_details", "Unknown error")
                return f"❌ Performance test failed: {error_details}"
            
            else:
                return (f"🔄 Test in progress: {status}\n"
                       f"📊 Progress: {progress}%\n"
                       f"📍 Current phase: {phase}")
        else:
            error = result.get("error", "Unknown error")
            return f"❌ Failed to get status: {error}"
            
    except ImportError:
        return f"⚠️ Advanced performance monitoring not available for execution {execution_id}"
        
    except Exception as e:
        return f"❌ Failed to get execution status: {str(e)}"


@tool  
def list_recent_performance_tests(limit: int = 5) -> str:
    """
    List recent performance test executions.
    
    Args:
        limit: Maximum number of executions to show (default: 5)
    
    Returns:
        List of recent performance test executions
    """
    try:
        from .performance_tool import PerformanceToolV2
        
        perf_tool = PerformanceToolV2()
        result_json = perf_tool.list_recent_executions(limit)
        
        import json
        try:
            result = json.loads(result_json)
        except json.JSONDecodeError:
            return f"❌ Failed to list executions: Invalid response format"
        
        if result.get("success"):
            executions = result.get("executions", [])
            
            if not executions:
                return "📝 No recent performance test executions found"
            
            output = f"📋 Recent performance test executions ({len(executions)}):\n\n"
            
            for i, execution in enumerate(executions, 1):
                execution_id = execution.get("execution_id", "unknown")[:8]  # Short ID
                status = execution.get("status", "unknown") 
                command = execution.get("original_command", "Unknown command")
                submitted_at = execution.get("submitted_at", "unknown")
                
                status_emoji = {
                    "COMPLETED": "✅",
                    "SUCCESS": "✅", 
                    "FAILED": "❌",
                    "ERROR": "❌",
                    "RUNNING": "🔄",
                    "PENDING": "⏳"
                }.get(status, "❓")
                
                output += f"{i}. {status_emoji} {execution_id}... - {status}\n"
                output += f"   Command: {command}\n"
                output += f"   Started: {submitted_at}\n\n"
            
            return output.strip()
        else:
            error = result.get("error", "Unknown error")
            return f"❌ Failed to list executions: {error}"
            
    except ImportError:
        return "⚠️ Advanced performance monitoring not available"
        
    except Exception as e:
        return f"❌ Failed to list executions: {str(e)}"


# Export for toolchain discovery
__all__ = [
    'api_test_endpoint', 
    'api_health_check', 
    'api_performance_test',
    'get_execution_status',
    'list_recent_performance_tests'
]
