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




# Export for toolchain discovery
__all__ = [
    'api_test_endpoint', 
    'api_health_check'
]
