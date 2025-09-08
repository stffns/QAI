"""
Monitoring Service - Real-time monitoring and status

Handles monitoring operations:
- Real-time execution monitoring
- Status tracking
- Performance metrics

Single responsibility: monitoring and observability.
"""
import json
from typing import Optional


class MonitoringService:
    """Service for monitoring operations."""
    
    def __init__(self, database_service):
        """Initialize with injected dependencies."""
        self.database_service = database_service
    
    def start_enhanced_monitoring(self, execution_id: str) -> str:
        """Start enhanced monitoring for execution."""
        try:
            # TODO: Implement from performance_tool_v2.py
            return json.dumps({
                "success": True,
                "message": f"Enhanced monitoring started for {execution_id}",
                "execution_id": execution_id,
                "monitoring_active": True
            }, indent=2)
        except Exception as e:
            return self._error_response(f"Failed to start monitoring: {str(e)}")
    
    def stop_enhanced_monitoring(self, execution_id: str) -> str:
        """Stop enhanced monitoring for execution."""
        try:
            # TODO: Implement from performance_tool_v2.py
            return json.dumps({
                "success": True,
                "message": f"Enhanced monitoring stopped for {execution_id}",
                "execution_id": execution_id,
                "monitoring_active": False
            }, indent=2)
        except Exception as e:
            return self._error_response(f"Failed to stop monitoring: {str(e)}")
    
    def get_execution_status(self, execution_id: str, engine) -> str:
        """Get status of a batch execution with enhanced real-time monitoring"""
        if not engine:
            return self._error_response("Performance engine not initialized")

        try:
            # Always try to get status from engine first
            try:
                status = engine.get_execution_status(execution_id)
                
                # Check if we got real-time monitoring data or execution info
                from ..engine.models import ExecutionStatus
                if hasattr(status, 'progress_percentage') and status.status in {
                    ExecutionStatus.RUNNING,
                    ExecutionStatus.PREPARING,
                    ExecutionStatus.SUBMITTED,
                    ExecutionStatus.PARSING,
                    ExecutionStatus.GENERATING_REPORTS,
                    ExecutionStatus.FAILED,
                    ExecutionStatus.COMPLETED,
                }:
                    print(f"🔴 Real-time data found for {execution_id}: {status.status.value} - {status.progress_percentage}%")
                    # Real-time or recent execution found - return enhanced status
                    response = {
                        "success": True,
                        "execution_id": execution_id,
                        "status": status.status.value,
                        "submitted_at": status.submitted_at,
                        "started_at": status.started_at,
                        "completed_at": status.completed_at,
                        "progress": status.progress_percentage,
                        "current_phase": status.current_phase,
                        "message": status.message,
                        "source": "engine_data",
                        
                        # Enhanced: Real-time user statistics
                        "user_statistics": {
                            "waiting": status.waiting_users,
                            "active": status.active_users,
                            "completed": status.completed_users
                        } if hasattr(status, 'waiting_users') else None,
                        
                        # Enhanced: Real-time performance metrics  
                        "performance_metrics": {
                            "total_requests": status.total_requests,
                            "successful_requests": status.successful_requests,
                            "failed_requests": status.failed_requests,
                            "mean_response_time": status.mean_response_time,
                            "p95_response_time": getattr(status, 'p95_response_time', None),
                            "current_rps": status.current_rps,
                            "success_rate": round((status.successful_requests / status.total_requests * 100), 2) if status.total_requests and status.total_requests > 0 and status.successful_requests is not None else None
                        } if status.total_requests and status.total_requests > 0 else None,
                        
                        # Report path (when completed)
                        "report_path": status.report_path,
                        "error_details": status.error_details
                    }
                    
                    return json.dumps(response, indent=2)
                
            except Exception as engine_error:
                print(f"🔴 Engine query failed for {execution_id}: {engine_error}")
                # Fallback to database query
                
            # Fallback: Query database for historical data
            db_data = self.database_service.get_execution_from_db(execution_id)
            if db_data:
                print(f"🔴 Database data found for {execution_id}")
                response = {
                    "success": True,
                    "execution_id": execution_id,
                    "status": db_data.get("batch_status", "unknown"),
                    "submitted_at": db_data.get("created_at"),
                    "started_at": db_data.get("started_at"),
                    "completed_at": db_data.get("updated_at"),
                    "progress": 100 if db_data.get("batch_status") == "completed" else 0,
                    "message": f"Batch execution {db_data.get('batch_status', 'unknown')}",
                    "source": "database",
                    "batch_name": db_data.get("batch_name"),
                    "app_name": db_data.get("app_name"),
                    "country_name": db_data.get("country_name"),
                    "test_type": db_data.get("test_type_name"),
                    "execution_details": db_data.get("execution_details")
                }
                return json.dumps(response, indent=2)
                
            # Not found anywhere
            return self._error_response(f"Execution {execution_id} not found in engine or database")
            
        except Exception as e:
            return self._error_response(f"Failed to get execution status: {str(e)}")

    def get_engine_status(self, engine) -> str:
        """Get performance engine status."""
        if not engine:
            return json.dumps({
                "success": False,
                "engine_available": False,
                "error": "Performance engine not initialized"
            }, indent=2)
        
        try:
            engine_status = engine.get_engine_status()
            
            response = {
                "success": True,
                "engine_available": True,
                "engine_status": engine_status,
                "system_info": {
                    "engine_type": "PerformanceEngineV2",
                    "monitoring_enabled": True,
                    "real_time_stats": True
                }
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "engine_available": True,
                "error": f"Failed to get engine status: {str(e)}"
            }, indent=2)
    
    def get_execution_metrics(self, execution_id: str) -> str:
        """Get real-time metrics for execution."""
        try:
            # TODO: Implement metrics collection
            return json.dumps({
                "success": True,
                "execution_id": execution_id,
                "metrics": {
                    "current_users": 0,
                    "requests_per_second": 0,
                    "response_time_avg": 0,
                    "error_rate": 0
                }
            }, indent=2)
        except Exception as e:
            return self._error_response(f"Failed to get metrics: {str(e)}")
    
    def _error_response(self, message: str) -> str:
        """Create standardized error response."""
        return json.dumps({
            "success": False,
            "error": message
        }, indent=2)
