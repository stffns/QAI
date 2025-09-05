"""
API Tools for QA Intelligence Agent - Agno CustomApiTools Integration

This module provides comprehensive API testing and validation tools using Agno's CustomApiTools
for quality assurance workflows, endpoint testing, and service monitoring.
"""
import json
from typing import Optional, Dict, Any, List, Union, Literal, cast
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
    """
    QA Intelligence API Tools wrapper for Agno CustomApiTools
    
    Provides comprehensive API testing capabilities for:
    - REST API endpoint testing and validation
    - Service health checks and monitoring
    - Authentication and authorization testing
    - Performance and reliability testing
    - Integration testing workflows
    """
    
    def __init__(self):
        """Initialize API Tools for QA Intelligence"""
        self.api_tools = CustomApiTools()
        logger.info("QA API Tools initialized successfully")
    
    def test_endpoint(self, url: str, method: str = "GET", headers: Optional[Dict] = None, 
                     data: Optional[Union[Dict, str]] = None, timeout: int = 30) -> Dict[str, Any]:
        """
        Test API endpoint with comprehensive QA validation
        
        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            headers: Request headers dictionary
            data: Request payload (JSON dict or raw string)
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with detailed test results and QA metrics
        """
        with LogStep(f"Testing API endpoint: {method} {url}", "QAAPITools"):
            try:
                # Validate method
                valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
                method_upper = method.upper()
                if method_upper not in valid_methods:
                    method_upper = "GET"  # Default to GET if invalid
                
                # Cast to the correct literal type
                method_literal = cast(Literal["GET", "POST", "PUT", "DELETE", "PATCH"], method_upper)
                
                # Make API request using direct parameters
                if data and isinstance(data, dict):
                    response = self.api_tools.make_request(
                        endpoint=url,
                        method=method_literal,
                        headers=headers,
                        json_data=data
                    )
                elif data and isinstance(data, str):
                    # For string data, we'll convert to dict or skip
                    try:
                        data_dict = json.loads(data)
                        response = self.api_tools.make_request(
                            endpoint=url,
                            method=method_literal,
                            headers=headers,
                            json_data=data_dict
                        )
                    except:
                        response = self.api_tools.make_request(
                            endpoint=url,
                            method=method_literal,
                            headers=headers
                        )
                else:
                    response = self.api_tools.make_request(
                        endpoint=url,
                        method=method_literal,
                        headers=headers
                    )
                
                # Parse response if it's a JSON string
                if isinstance(response, str):
                    try:
                        response_data = json.loads(response)
                    except json.JSONDecodeError:
                        response_data = {"raw_response": response}
                else:
                    response_data = response
                
                # Enhance with QA metrics
                qa_result = self._analyze_response_for_qa(response_data, url, method)
                
                logger.info(f"API test completed for {url} - Status: {qa_result.get('qa_status', 'unknown')}")
                return qa_result
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e),
                    "url": url,
                    "method": method,
                    "qa_status": "FAILED",
                    "qa_issues": [f"Request failed: {str(e)}"],
                    "recommendations": [
                        "Verify endpoint URL is correct",
                        "Check network connectivity",
                        "Validate authentication if required",
                        "Review request parameters"
                    ]
                }
                logger.error(f"API test failed for {url}: {str(e)}")
                return error_result
    
    def health_check(self, url: str, expected_status: int = 200, 
                    timeout: int = 10) -> Dict[str, Any]:
        """
        Perform health check on API endpoint
        
        Args:
            url: Health check endpoint URL
            expected_status: Expected HTTP status code
            timeout: Request timeout in seconds
            
        Returns:
            Health check results with QA assessment
        """
        with LogStep(f"Health check for {url}", "QAAPITools"):
            result = self.test_endpoint(url, "GET", timeout=timeout)
            
            # Analyze health check specific metrics
            health_result = {
                "endpoint": url,
                "timestamp": self._get_timestamp(),
                "is_healthy": False,
                "response_time_ms": result.get("response_time_ms", 0),
                "status_code": result.get("status_code", 0),
                "expected_status": expected_status,
                "health_score": 0
            }
            
            # Determine health status
            if result.get("success") and result.get("status_code") == expected_status:
                health_result["is_healthy"] = True
                health_result["health_score"] = self._calculate_health_score(result)
                health_result["status"] = "HEALTHY"
            else:
                health_result["status"] = "UNHEALTHY"
                health_result["issues"] = result.get("qa_issues", [])
            
            return health_result
    
    def test_api_performance(self, url: str, iterations: int = 5, 
                           method: str = "GET") -> Dict[str, Any]:
        """
        Test API performance with multiple requests
        
        Args:
            url: API endpoint URL
            iterations: Number of test iterations
            method: HTTP method to test
            
        Returns:
            Performance test results and statistics
        """
        with LogStep(f"Performance testing {url} ({iterations} iterations)", "QAAPITools"):
            results = []
            response_times = []
            success_count = 0
            
            for i in range(iterations):
                result = self.test_endpoint(url, method)
                results.append(result)
                
                if result.get("success"):
                    success_count += 1
                    response_times.append(result.get("response_time_ms", 0))
            
            # Calculate performance metrics
            performance_result = {
                "url": url,
                "method": method,
                "iterations": iterations,
                "success_rate": (success_count / iterations) * 100,
                "successful_requests": success_count,
                "failed_requests": iterations - success_count,
                "response_times": response_times,
                "performance_metrics": self._calculate_performance_metrics(response_times),
                "qa_assessment": self._assess_performance_qa(response_times, success_count, iterations)
            }
            
            return performance_result
    
    def _analyze_response_for_qa(self, response_data: Dict, url: str, method: str) -> Dict[str, Any]:
        """Analyze API response for QA metrics and recommendations"""
        qa_analysis = {
            "url": url,
            "method": method,
            "timestamp": self._get_timestamp(),
            "success": response_data.get("success", False),
            "status_code": response_data.get("status_code", 0),
            "response_time_ms": response_data.get("response_time", 0) * 1000 if response_data.get("response_time") else 0,
            "qa_status": "UNKNOWN",
            "qa_issues": [],
            "qa_score": 0,
            "recommendations": []
        }
        
        # Determine QA status
        status_code = qa_analysis["status_code"]
        response_time = qa_analysis["response_time_ms"]
        
        if 200 <= status_code < 300:
            qa_analysis["qa_status"] = "PASSED"
            qa_analysis["qa_score"] = 100
        elif 300 <= status_code < 400:
            qa_analysis["qa_status"] = "WARNING"
            qa_analysis["qa_score"] = 75
            qa_analysis["qa_issues"].append(f"Redirect response: {status_code}")
        elif 400 <= status_code < 500:
            qa_analysis["qa_status"] = "FAILED"
            qa_analysis["qa_score"] = 25
            qa_analysis["qa_issues"].append(f"Client error: {status_code}")
        elif status_code >= 500:
            qa_analysis["qa_status"] = "FAILED"
            qa_analysis["qa_score"] = 0
            qa_analysis["qa_issues"].append(f"Server error: {status_code}")
        
        # Performance analysis
        if response_time > 5000:
            qa_analysis["qa_issues"].append("Very slow response time (>5s)")
            qa_analysis["qa_score"] = max(0, qa_analysis["qa_score"] - 30)
        elif response_time > 2000:
            qa_analysis["qa_issues"].append("Slow response time (>2s)")
            qa_analysis["qa_score"] = max(0, qa_analysis["qa_score"] - 15)
        
        # Generate recommendations
        qa_analysis["recommendations"] = self._generate_qa_recommendations(qa_analysis)
        
        # Add raw response data
        qa_analysis["response_data"] = response_data
        
        return qa_analysis
    
    def _calculate_health_score(self, result: Dict) -> int:
        """Calculate health score based on response metrics"""
        score = 100
        
        # Response time impact
        response_time = result.get("response_time_ms", 0)
        if response_time > 2000:
            score -= 30
        elif response_time > 1000:
            score -= 15
        
        # Status code impact
        status_code = result.get("status_code", 0)
        if not (200 <= status_code < 300):
            score -= 50
        
        return max(0, score)
    
    def _calculate_performance_metrics(self, response_times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        if not response_times:
            return {}
        
        sorted_times = sorted(response_times)
        length = len(sorted_times)
        
        return {
            "min_ms": min(sorted_times),
            "max_ms": max(sorted_times),
            "avg_ms": sum(sorted_times) / length,
            "median_ms": sorted_times[length // 2],
            "p95_ms": sorted_times[int(length * 0.95)] if length > 1 else sorted_times[0],
            "p99_ms": sorted_times[int(length * 0.99)] if length > 1 else sorted_times[0]
        }
    
    def _assess_performance_qa(self, response_times: List[float], success_count: int, total: int) -> Dict[str, Any]:
        """Assess performance from QA perspective"""
        if not response_times:
            return {"status": "FAILED", "issues": ["No successful responses"]}
        
        avg_time = sum(response_times) / len(response_times)
        success_rate = (success_count / total) * 100
        
        assessment = {
            "status": "PASSED",
            "issues": [],
            "score": 100
        }
        
        # Success rate assessment
        if success_rate < 95:
            assessment["status"] = "FAILED"
            assessment["issues"].append(f"Low success rate: {success_rate:.1f}%")
            assessment["score"] -= 50
        elif success_rate < 99:
            assessment["status"] = "WARNING"
            assessment["issues"].append(f"Moderate success rate: {success_rate:.1f}%")
            assessment["score"] -= 20
        
        # Response time assessment
        if avg_time > 2000:
            assessment["status"] = "FAILED" if assessment["status"] != "FAILED" else "FAILED"
            assessment["issues"].append(f"High average response time: {avg_time:.0f}ms")
            assessment["score"] -= 30
        elif avg_time > 1000:
            assessment["status"] = "WARNING" if assessment["status"] == "PASSED" else assessment["status"]
            assessment["issues"].append(f"Elevated response time: {avg_time:.0f}ms")
            assessment["score"] -= 15
        
        assessment["score"] = max(0, assessment["score"])
        return assessment
    
    def _generate_qa_recommendations(self, analysis: Dict) -> List[str]:
        """Generate QA recommendations based on analysis"""
        recommendations = []
        
        status_code = analysis.get("status_code", 0)
        response_time = analysis.get("response_time_ms", 0)
        
        # Status code recommendations
        if 400 <= status_code < 500:
            recommendations.extend([
                "Review request parameters and authentication",
                "Validate endpoint URL and HTTP method",
                "Check required headers and data format"
            ])
        elif status_code >= 500:
            recommendations.extend([
                "Check server health and logs",
                "Verify database connectivity",
                "Review server capacity and load"
            ])
        
        # Performance recommendations
        if response_time > 2000:
            recommendations.extend([
                "Investigate server performance issues",
                "Consider implementing caching",
                "Review database query optimization",
                "Check network latency"
            ])
        
        # Security recommendations
        if analysis.get("method") in ["POST", "PUT", "DELETE"]:
            recommendations.append("Ensure proper authentication and authorization")
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging"""
        import datetime
        return datetime.datetime.now().isoformat()


# Initialize the QA API Tools instance
qa_api_tools = QAAPITools()


# Tool functions for Agno integration
@tool
def api_test_endpoint(url: str, method: str = "GET", headers: Optional[str] = None, 
                     data: Optional[str] = None, timeout: int = 30) -> str:
    """
    Test API endpoint with comprehensive QA validation and metrics.
    
    Perfect for:
    - Testing REST API endpoints 
    - Validating API responses and status codes
    - Measuring response times and performance
    - Identifying API issues and getting recommendations
    
    Args:
        url: API endpoint URL to test
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: JSON string of request headers (optional)
        data: JSON string of request payload (optional)  
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        JSON string with detailed test results, QA metrics, and recommendations
    """
    try:
        # Parse optional JSON parameters
        parsed_headers = json.loads(headers) if headers else None
        parsed_data = json.loads(data) if data else None
        
        result = qa_api_tools.test_endpoint(
            url=url,
            method=method,
            headers=parsed_headers,
            data=parsed_data,
            timeout=timeout
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"API test failed: {str(e)}",
            "qa_status": "ERROR"
        }
        return json.dumps(error_result, indent=2)


@tool
def api_health_check(url: str, expected_status: int = 200, timeout: int = 10) -> str:
    """
    Perform health check on API endpoint with QA assessment.
    
    Perfect for:
    - Monitoring service availability
    - Automated health checks
    - Uptime monitoring
    - Service reliability testing
    
    Args:
        url: Health check endpoint URL
        expected_status: Expected HTTP status code (default: 200)
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        JSON string with health check results and health score
    """
    try:
        result = qa_api_tools.health_check(
            url=url,
            expected_status=expected_status,
            timeout=timeout
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "is_healthy": False,
            "status": "ERROR",
            "error": f"Health check failed: {str(e)}"
        }
        return json.dumps(error_result, indent=2)


@tool  
def api_performance_test(url: str, iterations: int = 5, method: str = "GET") -> str:
    """
    Test API performance with multiple requests and statistical analysis.
    
    Perfect for:
    - Load testing APIs
    - Performance benchmarking
    - Response time analysis
    - Reliability testing
    
    Args:
        url: API endpoint URL to test
        iterations: Number of test iterations (default: 5)
        method: HTTP method to test (default: GET)
        
    Returns:
        JSON string with performance metrics, statistics, and QA assessment
    """
    try:
        result = qa_api_tools.test_api_performance(
            url=url,
            iterations=iterations,
            method=method
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Performance test failed: {str(e)}",
            "qa_assessment": {"status": "ERROR"}
        }
        return json.dumps(error_result, indent=2)


# Raw function access for direct use
def test_endpoint_raw(url: str, method: str = "GET", headers: Optional[Dict] = None,
                     data: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
    """Raw access to endpoint testing functionality"""
    return qa_api_tools.test_endpoint(url, method, headers, data, timeout)


def health_check_raw(url: str, expected_status: int = 200, timeout: int = 10) -> Dict[str, Any]:
    """Raw access to health check functionality"""
    return qa_api_tools.health_check(url, expected_status, timeout)


def performance_test_raw(url: str, iterations: int = 5, method: str = "GET") -> Dict[str, Any]:
    """Raw access to performance testing functionality"""
    return qa_api_tools.test_api_performance(url, iterations, method)
