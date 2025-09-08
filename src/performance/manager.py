"""
Performance Manager - Facade Principal
Manager principal que orquesta todos los servicios de performance

Responsabilidades:
- Facade unificado para todos los servicios
- Dependency injection de componentes
- Interface pública estable
- Coordinación de workflows completos

Patrón: Facade + Dependency Injection

NOTA: Esta es una implementación híbrida que demuestra el patrón Manager/Facade
mientras mantiene compatibilidad con los servicios existentes.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Utils imports (estos están completamente extraídos en Fase 5)
from .utils.parsers import PerformanceCommandParser
from .utils.validators import PerformanceParameterValidator, PerformanceSLAValidator


@dataclass
class PerformanceManagerConfig:
    """Configuration for PerformanceManager"""
    default_timeout: int = 300
    enable_monitoring: bool = True
    enable_sla_validation: bool = True
    max_concurrent_tests: int = 3


class PerformanceManager:
    """
    Main Performance Manager - Facade for all performance testing operations
    
    This class provides a unified interface to all performance testing functionality,
    implementing dependency injection and coordinating between utilities and services.
    
    This is a demonstration of the Manager/Facade pattern that integrates the
    extracted utilities (parsers, validators) with the performance system.
    """
    
    def __init__(self, config: Optional[PerformanceManagerConfig] = None):
        """
        Initialize Performance Manager with all dependencies
        
        Args:
            config: Manager configuration (optional)
        """
        self.config = config or PerformanceManagerConfig()
        
        # Initialize utilities (from Phase 5 extraction)
        self._initialize_utilities()
        
        # Initialize services (these would be injected in full implementation)
        self._initialize_services()
    
    def _initialize_utilities(self):
        """Initialize parsers and validators (Phase 5 extractions)"""
        self.command_parser = PerformanceCommandParser()
        self.parameter_validator = PerformanceParameterValidator()
        
        if self.config.enable_sla_validation:
            self.sla_validator = PerformanceSLAValidator()
        else:
            self.sla_validator = None
    
    def _initialize_services(self):
        """Initialize services including database service for persistence"""
        try:
            # Import database service for persistence operations
            from .services.database_service import DatabaseService
            from database.connection import db_manager
            
            # Initialize database service with connection manager
            self.database_service = DatabaseService(db_manager)
            self.services_initialized = True
            
        except Exception as e:
            # Log error but continue with placeholder implementation
            print(f"⚠️  Warning: Could not initialize database service: {e}")
            print("📄 Falling back to placeholder implementation")
            self.database_service = None
            self.services_initialized = True
    
    # ==================== PUBLIC API - MAIN ENTRY POINT ====================
    
    def execute_performance_test_from_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a complete performance test from natural language command
        
        This demonstrates the Manager/Facade pattern coordinating the full workflow:
        1. Parse natural language command (using Phase 5 parser)
        2. Validate parameters (using Phase 5 validator)
        3. Validate against SLAs (using Phase 5 SLA validator)
        4. Build configuration
        5. Execute test
        
        Args:
            command: Natural language command
            **kwargs: Additional parameters
            
        Returns:
            Complete test execution result
        """
        try:
            # 1. Parse command using extracted parser
            parse_result = self.parse_command(command, **kwargs)
            if not parse_result["success"]:
                return self._error_response(f"Command parsing failed: {parse_result['error']}")
            
            params = parse_result["parameters"]
            
            # 2. Validate parameters using extracted validator
            validation_result = self.validate_parameters(params)
            if not validation_result["success"]:
                return self._error_response(f"Parameter validation failed: {validation_result['errors']}")
            
            # 3. Validate against SLAs if enabled
            calculated_rps = params.get("agent_rps", 1.0) * params.get("virtual_users", 1)
            
            if self.sla_validator:
                sla_result = self.validate_sla(params, calculated_rps)
                if not sla_result["success"]:
                    return self._error_response(f"SLA validation failed: {sla_result['error']}")
            
            # 4. Build configuration
            config = self._build_test_configuration(params, calculated_rps)
            
            # 5. Execute test (simplified for demonstration)
            execution_result = self._execute_test_workflow(config)
            
            # 6. Return complete result
            return {
                "success": True,
                "test_id": execution_result["test_id"],
                "parameters": params,
                "parsed_command": command,
                "validated_parameters": validation_result["validated_params"],
                "rps": calculated_rps,
                "configuration": config,
                "execution": execution_result,
                "sla_validated": self.sla_validator is not None,
                "manager_version": "Phase6_Facade_Demo"
            }
            
        except Exception as e:
            return self._error_response(f"Performance test execution error: {str(e)}")
    
    # ==================== UTILITIES API (Phase 5 integrations) ====================
    
    def parse_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Parse natural language command using extracted parser"""
        return self.command_parser.parse_natural_language_command(command, **kwargs)
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance test parameters using extracted validator"""
        return self.parameter_validator.validate_parameters(params)
    
    def validate_sla(self, params: Dict[str, Any], rps: float, db_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate against SLA constraints using extracted SLA validator"""
        if not self.sla_validator:
            return {"success": True, "message": "SLA validation disabled"}
        return self.sla_validator.validate_against_slas(params, rps, db_data)
    
    # ==================== FACADE API METHODS ====================
    
    def get_supported_patterns(self) -> Dict[str, Any]:
        """Get supported command patterns from parser"""
        return self.command_parser.get_supported_patterns()
    
    def parse_and_validate(self, command: str, **kwargs) -> Dict[str, Any]:
        """Parse command and validate parameters in one step"""
        parse_result = self.parse_command(command, **kwargs)
        if not parse_result["success"]:
            return parse_result
        
        validation_result = self.validate_parameters(parse_result["parameters"])
        
        return {
            "success": validation_result["success"],
            "parsed_parameters": parse_result["parameters"],
            "validation_errors": validation_result.get("errors", []),
            "validated_parameters": validation_result.get("validated_params")
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate test configuration using configuration validator"""
        from .utils.validators import create_configuration_validator
        
        config_validator = create_configuration_validator()
        return config_validator.validate_configuration(config)
    
    # ==================== BATCH OPERATIONS ====================
    
    def process_multiple_commands(self, commands: List[str]) -> Dict[str, Any]:
        """Process multiple commands in batch"""
        results = []
        
        for i, command in enumerate(commands):
            if i >= self.config.max_concurrent_tests:
                break
                
            result = self.parse_and_validate(command)
            results.append({
                "command": command,
                "index": i,
                "result": result
            })
        
        return {
            "success": True,
            "batch_results": results,
            "total_processed": len(results)
        }
    
    # ==================== HEALTH AND STATUS ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all components"""
        health_status = {
            "manager": "healthy",
            "services": {"placeholder": "healthy"},
            "utilities": {},
            "config": self.config.__dict__
        }
        
        # Check utilities (Phase 5 extractions)
        health_status["utilities"] = {
            "parser": "healthy" if self.command_parser else "error",
            "parameter_validator": "healthy" if self.parameter_validator else "error",
            "sla_validator": "healthy" if self.sla_validator else "disabled"
        }
        
        return {
            "success": True,
            "health": health_status,
            "phase": "Phase 6 - Manager/Facade Pattern Demonstration"
        }
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a performance test execution
        
        Args:
            execution_id: Execution ID to check
            
        Returns:
            Dictionary with execution status and results
        """
        try:
            # In a real implementation, this would query the database or engine
            # For now, return a placeholder response
            
            # TODO: Implement actual execution status checking
            # This should integrate with the database service to get real status
            
            return {
                "success": True,
                "execution_id": execution_id,
                "status": "completed",  # placeholder
                "progress": 100,
                "results": {
                    "response_time_avg": 250,
                    "response_time_p95": 450,
                    "requests_total": 1000,
                    "requests_ok": 995,
                    "requests_ko": 5,
                    "success_rate": 99.5
                },
                "message": "Execution status retrieved (placeholder implementation)"
            }
            
        except Exception as e:
            return self._error_response(f"Error getting execution status: {str(e)}")
    
    def list_recent_executions(self, limit: int = 10) -> Dict[str, Any]:
        """
        List recent performance test executions
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            Dictionary with list of recent executions
        """
        try:
            # Use real database service if available
            if self.database_service:
                try:
                    # Get performance tests from database (now returns dictionaries)
                    executions = self.database_service.get_performance_tests(limit=limit)
                    
                    # Convert to API format (executions are now dictionaries)
                    execution_list = []
                    for execution in executions:
                        execution_list.append({
                            "execution_id": execution.get('execution_id', 'unknown'),
                            "timestamp": execution.get('created_at', self._get_timestamp()),
                            "status": execution.get('status', 'unknown'),
                            "application": execution.get('app_name', 'unknown'),
                            "environment": execution.get('country_name', 'unknown'),
                            "virtual_users": execution.get('execution_details', {}).get('users', 0),
                            "duration": execution.get('execution_time', 'unknown'),
                            "success_rate": execution.get('execution_details', {}).get('success_rate', 0)
                        })
                    
                    if len(execution_list) == 0:
                        return {
                            "success": True,
                            "executions": [],
                            "total": 0,
                            "limit": limit,
                            "message": "No executions found in database. This could mean:\n"
                                     "• No tests have been executed yet\n"
                                     "• Database connection issues\n"
                                     "• Tests are not being persisted properly\n"
                                     "Run a new test and check if it gets saved.",
                            "debug_info": "Real database query executed successfully"
                        }
                    
                    return {
                        "success": True,
                        "executions": execution_list,
                        "total": len(execution_list),
                        "limit": limit,
                        "message": f"Found {len(execution_list)} recent executions from database",
                        "debug_info": "Real database query executed successfully"
                    }
                    
                except Exception as db_error:
                    # Database service failed - provide clear error
                    return {
                        "success": False,
                        "executions": [],
                        "total": 0,
                        "limit": limit,
                        "error": f"Database query failed: {str(db_error)}",
                        "message": "Could not retrieve executions from database. Check:\n"
                                 "• Database connection\n"
                                 "• Table structure\n"
                                 "• Permissions",
                        "debug_info": f"Database service error: {str(db_error)}"
                    }
            
            else:
                # Fallback to placeholder with clear warning
                placeholder_executions = []
                for i in range(min(limit, 3)):  # Return up to 3 placeholder executions
                    placeholder_executions.append({
                        "execution_id": f"demo_exec_{1000 + i}",
                        "timestamp": self._get_timestamp(),
                        "status": "completed",
                        "application": "DEMO_APP",
                        "environment": "TEST",
                        "virtual_users": 5,
                        "duration": "2.0 minutes",
                        "success_rate": 98.5 - i
                    })
                
                return {
                    "success": True,
                    "executions": placeholder_executions,
                    "total": len(placeholder_executions),
                    "limit": limit,
                    "message": "⚠️  PLACEHOLDER DATA - Database service not available",
                    "warning": "These are demo executions. Real database integration failed.",
                    "debug_info": "Database service not initialized - using fallback data"
                }
                
        except Exception as e:
            return self._error_response(f"Error listing recent executions: {str(e)}")
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _build_test_configuration(self, params: Dict[str, Any], rps: float) -> Dict[str, Any]:
        """Build test configuration from validated parameters"""
        return {
            "application": params.get("app_code"),
            "environment": params.get("env_code"),
            "country": params.get("country_code", "RO"),
            "virtualUsers": params.get("virtual_users", 1),
            "duration": f"{params.get('duration_minutes', 1)}m",
            "rps": rps,
            "scenarios": [
                {
                    "name": f"Performance Test {params.get('app_code')}",
                    "users": params.get("virtual_users", 1),
                    "duration": params.get("duration_minutes", 1)
                }
            ],
            "built_by": "PerformanceManager"
        }
    
    def _execute_test_workflow(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test workflow with REAL Gatling engine"""
        from datetime import datetime
        from .engine import create_engine
        
        timestamp = datetime.now().isoformat()
        
        try:
            # Initialize REAL performance engine
            engine = create_engine()
            
            # Convert config to Gatling format
            gatling_config = self._convert_to_gatling_config(config)
            
            # Execute REAL test with Gatling (convert to JSON string)
            import json
            result = engine.submit_simulation(json.dumps(gatling_config))
            
            execution_result = {
                "test_id": result.execution_id,
                "status": result.status.value,
                "execution_id": result.execution_id,
                "started_at": timestamp,
                "duration": config.get("duration", "1m"),
                "virtual_users": config.get("virtualUsers", 1),
                "application": config.get("application", "unknown"),
                "environment": config.get("environment", "unknown"),
                "country": config.get("country", "RO"),
                "rps": config.get("rps", 1.0),
                "message": f"REAL Gatling test executing with {config['virtualUsers']} users for {config['duration']}",
                "workflow": "real_gatling_execution",
                "submitted_at": result.submitted_at
            }
            
        except Exception as engine_error:
            # Fallback to error response
            execution_result = {
                "test_id": f"failed_{int(datetime.now().timestamp())}",
                "status": "failed",
                "error": f"Gatling engine error: {str(engine_error)}",
                "started_at": timestamp,
                "duration": config.get("duration", "1m"),
                "virtual_users": config.get("virtualUsers", 1),
                "application": config.get("application", "unknown"),
                "environment": config.get("environment", "unknown"),
                "country": config.get("country", "RO"),
                "rps": config.get("rps", 1.0),
                "message": f"Failed to execute real test: {str(engine_error)}",
                "workflow": "real_gatling_execution_failed"
            }
        
        # Persist to database if service is available
        if self.database_service:
            try:
                # Prepare data for database persistence
                test_data = {
                    "execution_id": execution_result["execution_id"],
                    "app_name": config.get("application", "unknown"),
                    "country_name": config.get("country", "RO"), 
                    "status": execution_result["status"],
                    "execution_time": str(config.get("duration", "1m")),
                    "started_at": timestamp,
                    "created_at": timestamp,
                    "execution_details": {
                        "users": config.get("virtualUsers", 1),
                        "rps": config.get("rps", 1.0),
                        "workflow": execution_result["workflow"]
                    }
                }
                
                # Save to database
                self.database_service.save_performance_test(test_data)
                execution_result["persisted"] = True
                execution_result["message"] += " (saved to database)"
                
            except Exception as db_error:
                # Log database error but don't fail the execution
                execution_result["persisted"] = False
                execution_result["persistence_error"] = str(db_error)
                execution_result["message"] += f" (⚠️  database save failed: {str(db_error)})"
        else:
            execution_result["persisted"] = False
            execution_result["message"] += " (⚠️  no database service available)"
        
        return execution_result
    
    def _convert_to_gatling_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal config to Gatling engine format"""
        # Extract duration in seconds
        duration_str = config.get("duration", "1m")
        if duration_str.endswith("m"):
            duration_seconds = int(float(duration_str[:-1]) * 60)
        else:
            duration_seconds = int(duration_str.replace("s", ""))
        
        # Build Gatling configuration
        gatling_config = {
            "simulation_config": {
                "base_url": f"https://{config.get('environment', 'api.example.com')}",
                "test_parameters": {
                    "virtual_users": config.get("virtualUsers", 1),
                    "duration_seconds": duration_seconds,
                    "rps": config.get("rps", 1.0)
                }
            },
            "endpoints": [
                {
                    "name": f"Test {config.get('application', 'API')}",
                    "url": "/",
                    "method": "GET",
                    "headers": {}
                }
            ],
            "headers": {
                "User-Agent": f"QA-Intelligence-{config.get('application', 'Test')}"
            }
        }
        
        return gatling_config
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": message,
            "timestamp": self._get_timestamp(),
            "manager": "PerformanceManager"
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


# Factory functions for convenience
def create_performance_manager(config: Optional[PerformanceManagerConfig] = None) -> PerformanceManager:
    """Create a new Performance Manager instance"""
    return PerformanceManager(config)


def create_performance_manager_with_config(**kwargs) -> PerformanceManager:
    """Create Performance Manager with configuration from kwargs"""
    config = PerformanceManagerConfig(**kwargs)
    return PerformanceManager(config)
