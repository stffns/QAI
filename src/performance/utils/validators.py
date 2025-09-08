"""
Performance Validators
Validadores para parámetros y configuraciones de pruebas de rendimiento

Responsabilidades:
- Validación de parámetros de entrada
- Validación contra SLAs 
- Validación de configuraciones
- Validación de RPS y thresholds

Extraído de performance_tool_v2.py
"""

from typing import Dict, Any, Optional


class PerformanceParameterValidator:
    """Validator for performance test parameters"""
    
    def __init__(self):
        """Initialize validator with limits and constraints"""
        self.limits = {
            "max_virtual_users": 1000,
            "min_virtual_users": 1,
            "max_duration_minutes": 120,
            "min_duration_minutes": 0.5,  # Allow tests as short as 30 seconds
            "max_agent_rps": 100.0,
            "min_agent_rps": 0.1,
            "max_allowed_rps": 100.0  # SLA limit
        }
        
        self.required_params = [
            "app_code",
            "env_code"
        ]
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all performance test parameters
        
        Args:
            params: Dictionary with test parameters
            
        Returns:
            Dict with validation result and errors
        """
        errors = []
        
        # Check required parameters
        for param in self.required_params:
            if not params.get(param):
                errors.append(f"Missing required parameter: {param}")
        
        # Validate numeric ranges
        errors.extend(self._validate_numeric_ranges(params))
        
        # Validate business rules
        errors.extend(self._validate_business_rules(params))
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "validated_params": params if len(errors) == 0 else None
        }
    
    def _validate_numeric_ranges(self, params: Dict[str, Any]) -> list:
        """Validate numeric parameter ranges"""
        errors = []
        
        # Virtual users validation
        if "virtual_users" in params:
            users = params["virtual_users"]
            if not isinstance(users, int):
                errors.append("virtual_users must be an integer")
            elif users < self.limits["min_virtual_users"] or users > self.limits["max_virtual_users"]:
                errors.append(f"virtual_users must be between {self.limits['min_virtual_users']} and {self.limits['max_virtual_users']}")
        
        # Duration validation
        if "duration_minutes" in params:
            duration = params["duration_minutes"]
            if not isinstance(duration, (int, float)):
                errors.append("duration_minutes must be a number")
            elif duration < self.limits["min_duration_minutes"] or duration > self.limits["max_duration_minutes"]:
                errors.append(f"duration_minutes must be between {self.limits['min_duration_minutes']} and {self.limits['max_duration_minutes']}")
        
        # RPS validation
        if "agent_rps" in params:
            rps = params["agent_rps"]
            if not isinstance(rps, (int, float)):
                errors.append("agent_rps must be a number")
            elif rps < self.limits["min_agent_rps"] or rps > self.limits["max_agent_rps"]:
                errors.append(f"agent_rps must be between {self.limits['min_agent_rps']} and {self.limits['max_agent_rps']}")
        
        return errors
    
    def _validate_business_rules(self, params: Dict[str, Any]) -> list:
        """Validate business-specific rules"""
        errors = []
        
        # Environment-specific rules
        env_code = params.get("env_code", "").upper()
        if env_code == "PROD":
            # Production environment restrictions
            if params.get("virtual_users", 0) > 10:
                errors.append("Production environment limited to maximum 10 virtual users")
            if params.get("duration_minutes", 0) > 5:
                errors.append("Production environment limited to maximum 5 minutes duration")
        
        # Application-specific rules
        app_code = params.get("app_code", "")
        if app_code == "PAYROLL" and params.get("virtual_users", 0) > 5:
            errors.append("PAYROLL application limited to maximum 5 virtual users")
        
        return errors


class PerformanceSLAValidator:
    """Validator for SLA compliance"""
    
    def __init__(self):
        """Initialize SLA validator"""
        self.default_limits = {
            "max_allowed_rps": 100.0,
            "max_response_time_ms": 2000,
            "min_success_rate": 95.0
        }
    
    def validate_against_slas(self, params: Dict[str, Any], rps: float, db_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate RPS against performance SLAs
        
        Args:
            params: Test parameters
            rps: Calculated RPS value
            db_data: Database configuration data (optional)
            
        Returns:
            Dict with validation result
        """
        try:
            # Use database SLA if available, otherwise use defaults
            max_allowed_rps = self._get_sla_limit(params, db_data)
            
            if rps > max_allowed_rps:
                return {
                    "success": False,
                    "error": f"RPS {rps} exceeds maximum allowed {max_allowed_rps}",
                    "sla_limit": max_allowed_rps
                }
            
            return {
                "success": True,
                "validated_rps": rps,
                "sla_limit": max_allowed_rps
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"SLA validation error: {str(e)}"
            }
    
    def _get_sla_limit(self, params: Dict[str, Any], db_data: Optional[Dict[str, Any]] = None) -> float:
        """Get SLA limit from database or defaults"""
        if db_data and "sla_limit" in db_data:
            return float(db_data["sla_limit"])
        
        # Environment-specific defaults
        env_code = params.get("env_code", "").upper()
        if env_code == "PROD":
            return 50.0  # Stricter limit for production
        elif env_code == "TEST":
            return 75.0  # Medium limit for test
        else:
            return self.default_limits["max_allowed_rps"]  # Default for STA
    
    def validate_performance_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate performance test results against SLAs
        
        Args:
            results: Performance test results
            
        Returns:
            Dict with validation result
        """
        try:
            violations = []
            
            # Check response time
            avg_response_time = results.get("avg_response_time_ms", 0)
            if avg_response_time > self.default_limits["max_response_time_ms"]:
                violations.append(f"Average response time {avg_response_time}ms exceeds limit {self.default_limits['max_response_time_ms']}ms")
            
            # Check success rate
            success_rate = results.get("success_rate", 0)
            if success_rate < self.default_limits["min_success_rate"]:
                violations.append(f"Success rate {success_rate}% below minimum {self.default_limits['min_success_rate']}%")
            
            return {
                "success": len(violations) == 0,
                "violations": violations,
                "results_validated": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Results validation error: {str(e)}"
            }


class PerformanceConfigurationValidator:
    """Validator for performance test configurations"""
    
    def __init__(self):
        """Initialize configuration validator"""
        self.required_config_fields = [
            "application",
            "environment", 
            "country",
            "virtualUsers",
            "duration"
        ]
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate performance test configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dict with validation result
        """
        try:
            errors = []
            
            # Check required fields
            for field in self.required_config_fields:
                if field not in config:
                    errors.append(f"Missing required configuration field: {field}")
            
            # Validate configuration structure
            if "scenarios" not in config:
                errors.append("Missing scenarios configuration")
            elif not isinstance(config["scenarios"], list):
                errors.append("Scenarios must be a list")
            
            # Validate Gatling-specific configuration
            if "gatling" in config:
                errors.extend(self._validate_gatling_config(config["gatling"]))
            
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "validated_config": config if len(errors) == 0 else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Configuration validation error: {str(e)}"
            }
    
    def _validate_gatling_config(self, gatling_config: Dict[str, Any]) -> list:
        """Validate Gatling-specific configuration"""
        errors = []
        
        # Check required Gatling fields
        required_gatling_fields = ["simulation", "resultsFolder"]
        for field in required_gatling_fields:
            if field not in gatling_config:
                errors.append(f"Missing required Gatling field: {field}")
        
        return errors


# Factory functions for convenience
def create_parameter_validator() -> PerformanceParameterValidator:
    """Create a new parameter validator instance"""
    return PerformanceParameterValidator()


def create_sla_validator() -> PerformanceSLAValidator:
    """Create a new SLA validator instance"""
    return PerformanceSLAValidator()


def create_configuration_validator() -> PerformanceConfigurationValidator:
    """Create a new configuration validator instance"""
    return PerformanceConfigurationValidator()


# Legacy function for backward compatibility
def validate_against_slas(params: Dict[str, Any], rps: float, db_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    validator = create_sla_validator()
    return validator.validate_against_slas(params, rps, db_data)
