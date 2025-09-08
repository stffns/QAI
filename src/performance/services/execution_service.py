"""
Execution Service - Performance test execution

Handles test execution lifecycle:
- Test configuration and validation
- Engine orchestration
- Process management

Single responsibility: test execution.
"""
import json
from typing import Optional, Dict, Any


class ExecutionService:
    """Service for test execution operations."""
    
    def __init__(self, database_service):
        """Initialize with injected dependencies."""
        self.database_service = database_service
    
    def execute_performance_test(self, app_code: str, env_code: str, 
                               users: int, duration_minutes: int,
                               country_code: Optional[str] = None) -> str:
        """Execute performance test with direct parameters."""
        try:
            # Initialize engine if not available
            if not hasattr(self, 'engine') or not self.engine:
                self._initialize_engine()
            
            if not self.engine:
                return self._error_response("Performance engine not initialized")
            
            # Prepare parameters
            params = {
                'app_code': app_code,
                'env_code': env_code,
                'country_code': country_code,
                'virtual_users': users,
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_minutes * 60,
                'agent_rps': 1.0  # Default RPS
            }
            
            # Validate required parameters
            required_params = ['app_code', 'env_code']
            missing_params = [p for p in required_params if not params.get(p)]
            if missing_params:
                return self._error_response(f"Missing required parameters: {missing_params}")
            
            # Query database for configuration
            db_config = self._get_configuration_service().query_database_configuration(params)
            if not db_config["success"]:
                return self._error_response(f"Database query failed: {db_config['error']}")
            
            # Extract endpoints data for later use
            endpoints_data = db_config["data"].get("endpoints", [])
            
            # Apply RPS cascade logic
            rps_result = self._get_configuration_service().resolve_rps_cascade(params, db_config["data"])
            if not rps_result["success"]:
                return self._error_response(f"RPS resolution failed: {rps_result['error']}")
            
            # Validate against SLAs
            sla_validation = self._get_configuration_service().validate_against_slas(params, rps_result["rps"], db_config["data"])
            if not sla_validation["success"]:
                return self._error_response(f"SLA validation failed: {sla_validation['error']}")
            
            # Build complete configuration JSON
            config_json = self._get_configuration_service().build_complete_configuration(params, db_config["data"], rps_result["rps"])
            
            # Submit to Performance Engine V2 (batch)
            execution_result = self.engine.submit_simulation(config_json)
            
            # Track execution in memory for quick access
            if not hasattr(self, 'agent_executions'):
                self.agent_executions = {}
            
            self.agent_executions[execution_result.execution_id] = {
                "app_code": app_code,
                "env_code": env_code,
                "country_code": country_code,
                "parameters": params,
                "submitted_at": execution_result.submitted_at,
                "config_json": config_json,
                "estimated_duration": execution_result.estimated_duration_minutes
            }
            
            # Persist execution in database for cross-instance tracking
            self._persist_execution_to_db(execution_result, params, config_json)
            
            # Save endpoints data to database for visibility
            if endpoints_data:
                self._save_endpoints_data_to_db(execution_result.execution_id, endpoints_data)
            
            # Return success response
            return json.dumps({
                "success": True,
                "message": "Performance test submitted successfully",
                "execution_id": execution_result.execution_id,
                "estimated_duration_minutes": execution_result.estimated_duration_minutes,
                "submitted_at": execution_result.submitted_at,
                "status": "submitted",
                "parameters": {
                    "app_code": app_code,
                    "env_code": env_code,
                    "country_code": country_code,
                    "virtual_users": users,
                    "duration_minutes": duration_minutes,
                    "agent_rps": rps_result["rps"]
                }
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to execute test: {str(e)}")
    
    def _initialize_engine(self):
        """Initialize the performance engine."""
        try:
            # Import the new modular engine
            from ..engine import PerformanceEngineV2
            
            # Initialize engine with default gatling path
            from pathlib import Path
            gatling_path = str(Path(__file__).parent.parent.parent.parent / "tools" / "gatling")
            self.engine = PerformanceEngineV2(gatling_path)
            
        except Exception as e:
            self.engine = None
            self.initialization_error = f"Engine init failed: {str(e)}"
    
    def _get_configuration_service(self):
        """Get configuration service instance."""
        if not hasattr(self, '_config_service'):
            from .configuration_service import ConfigurationService
            self._config_service = ConfigurationService(self.database_service)
        return self._config_service
    
    def _persist_execution_to_db(self, execution_result, params: Dict[str, Any], config_json: str):
        """Persist execution to database."""
        try:
            test_data = {
                "execution_id": execution_result.execution_id,
                "app_code": params.get("app_code"),
                "env_code": params.get("env_code"),
                "country_code": params.get("country_code"),
                "virtual_users": params.get("virtual_users"),
                "duration_minutes": params.get("duration_minutes"),
                "agent_rps": params.get("agent_rps"),
                "status": "submitted",
                "config_json": config_json,
                "submitted_at": execution_result.submitted_at,
                "estimated_duration_minutes": execution_result.estimated_duration_minutes
            }
            
            self.database_service.save_performance_test(test_data)
            
        except Exception as e:
            # Log error but don't fail the execution
            print(f"Warning: Failed to persist execution to DB: {str(e)}")
    
    def _save_endpoints_data_to_db(self, execution_id: str, endpoints_data: list):
        """Save endpoints data to database."""
        try:
            if not endpoints_data:
                return
            # Delegate to database service helper for persistence
            self.database_service.save_endpoints_data_to_db(execution_id, endpoints_data)
        except Exception as e:
            print(f"Warning: Failed to save endpoints data: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> str:
        """Get execution status by ID with enhanced real-time monitoring."""
        try:
            # Initialize engine if not available
            if not hasattr(self, 'engine') or not self.engine:
                self._initialize_engine()
            
            if not self.engine:
                return self._error_response("Performance engine not initialized")
            
            # Priority: Always try to get status from engine first
            try:
                status = self.engine.get_execution_status(execution_id)
                
                # Check if we got real-time monitoring data
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
                    # Real-time or recent execution found - return enhanced status
                    agent_info = getattr(self, 'agent_executions', {}).get(execution_id, {})
                    
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
                        "error_details": status.error_details,
                        
                        # Agent tracking
                        "original_command": agent_info.get("app_code", "") + "-" + agent_info.get("env_code", ""),
                        "estimated_duration_minutes": agent_info.get("estimated_duration"),
                        
                        # Enhanced: Progress visualization
                        "progress_visualization": f"[{'█' * int(status.progress_percentage / 5)}{'░' * (20 - int(status.progress_percentage / 5))}] {status.progress_percentage:.1f}%",
                        "real_time_monitoring": True
                    }
                    return json.dumps(response, indent=2)
                
            except Exception as engine_error:
                # Continue to try database fallback
                pass
            
            # Fallback: Try to get from database
            test = self.database_service.get_test_by_execution_id(execution_id)
            if not test:
                return self._error_response(f"Execution {execution_id} not found")
            
            # Return database status (less detailed)
            return json.dumps({
                "success": True,
                "execution_id": execution_id,
                "status": getattr(test, 'status', 'unknown'),
                "source": "database",
                "submitted_at": str(getattr(test, 'submitted_at', '')),
                "app_code": getattr(test, 'app_code', ''),
                "env_code": getattr(test, 'env_code', ''),
                "country_code": getattr(test, 'country_code', ''),
                "virtual_users": getattr(test, 'virtual_users', 0),
                "duration_minutes": getattr(test, 'duration_minutes', 0),
                "message": "Status retrieved from database (limited details)"
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to get status: {str(e)}")
    
    def list_recent_executions(self, limit: int = 5) -> str:
        """List recent test executions with enhanced details."""
        try:
            enhanced_executions = []
            
            # Try to get from engine first
            if hasattr(self, 'engine') and self.engine:
                try:
                    engine_executions = self.engine.list_executions(limit)
                    
                    for execution in engine_executions:
                        agent_info = getattr(self, 'agent_executions', {}).get(execution.execution_id, {})
                        enhanced_executions.append({
                            "execution_id": execution.execution_id,
                            "status": execution.status.value,
                            "submitted_at": execution.submitted_at,
                            "completed_at": execution.completed_at,
                            "message": execution.message,
                            "app_code": agent_info.get("app_code", "Unknown"),
                            "env_code": agent_info.get("env_code", "Unknown"),
                            "country_code": agent_info.get("country_code"),
                            "estimated_duration": agent_info.get("estimated_duration"),
                            "source": "engine"
                        })
                except Exception as e:
                    print(f"Warning: Engine list failed: {e}")
            
            # Add/supplement with executions from database
            try:
                db_tests = self.database_service.get_performance_tests(limit=limit)
                
                for test in db_tests:
                    execution_id = getattr(test, 'execution_id', None)
                    
                    # Skip if already in engine results
                    if any(exec['execution_id'] == execution_id for exec in enhanced_executions):
                        continue
                    
                    enhanced_executions.append({
                        "execution_id": execution_id,
                        "status": getattr(test, 'status', 'unknown'),
                        "submitted_at": str(getattr(test, 'submitted_at', '')),
                        "completed_at": str(getattr(test, 'completed_at', '')),
                        "app_code": getattr(test, 'app_code', 'Unknown'),
                        "env_code": getattr(test, 'env_code', 'Unknown'),
                        "country_code": getattr(test, 'country_code', None),
                        "virtual_users": getattr(test, 'virtual_users', 0),
                        "duration_minutes": getattr(test, 'duration_minutes', 0),
                        "source": "database"
                    })
                    
            except Exception as e:
                print(f"Warning: Database query failed: {e}")
            
            # Sort by submitted_at and limit
            enhanced_executions.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
            enhanced_executions = enhanced_executions[:limit]
            
            return json.dumps({
                "success": True,
                "executions": enhanced_executions,
                "total": len(enhanced_executions),
                "limit": limit,
                "sources": list(set(exec['source'] for exec in enhanced_executions))
            }, indent=2)
            
        except Exception as e:
            return self._error_response(f"Failed to list executions: {str(e)}")
    
    def cancel_execution(self, execution_id: str) -> str:
        """Cancel execution by ID."""
        try:
            # TODO: Implement cancellation logic
            return json.dumps({
                "success": True,
                "message": f"Execution {execution_id} cancelled",
                "execution_id": execution_id
            }, indent=2)
        except Exception as e:
            return self._error_response(f"Failed to cancel execution: {str(e)}")
    
    def _error_response(self, message: str) -> str:
        """Create standardized error response."""
        return json.dumps({
            "success": False,
            "error": message
        }, indent=2)
