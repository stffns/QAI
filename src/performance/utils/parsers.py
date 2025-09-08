"""
Performance Command Parser
Parser de comandos en lenguaje natural para pruebas de rendimiento

Responsabilidades:
- Parsing de comandos en español/inglés
- Extracción de parámetros (app, env, country, users, duration, RPS)
- Normalización de valores
- Validación básica de parámetros

Extraído de performance_tool_v2.py
"""

import re
from typing import Dict, Any


class PerformanceCommandParser:
    """Parser para comandos de performance en lenguaje natural"""
    
    def __init__(self):
        """Initialize parser with patterns and mappings"""
        # Application mappings - más específicos primero
        self.app_patterns = [
            (r"eva[-_]?ro|eva ro|eva romania", "EVA_RO"),
            (r"eva", "EVA_RO"),  # Default EVA to EVA_RO
            (r"payroll", "PAYROLL"),
            (r"oneapp", "ONEAPP")
        ]
        
        # Environment mappings
        self.env_patterns = [
            (r"sta|staging", "STA"),
            (r"test", "TEST"),
            (r"prod|production", "PROD")
        ]
        
        # Country mappings
        self.country_patterns = [
            (r"ro|romania", "RO"),
            (r"fr|france", "FR"),
            (r"be|belgium", "BE")
        ]
    
    def parse_natural_language_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Parse natural language command to extract parameters
        
        Args:
            command: Natural language command in Spanish/English
            **kwargs: Additional parameters to merge
            
        Returns:
            Dict with success flag and extracted parameters
        """
        try:
            command_lower = command.lower()
            params = {}
            
            # Extract application
            for pattern, app_code in self.app_patterns:
                if re.search(pattern, command_lower):
                    params["app_code"] = app_code
                    break
            
            # Extract environment
            for pattern, env_code in self.env_patterns:
                if re.search(pattern, command_lower):
                    params["env_code"] = env_code
                    break
            
            # Extract country
            for pattern, country_code in self.country_patterns:
                if re.search(pattern, command_lower):
                    params["country_code"] = country_code
                    break
            
            # Extract numeric parameters
            params.update(self._extract_numeric_parameters(command_lower))
            
            # Merge with provided kwargs
            params.update(kwargs)
            
            # Apply defaults
            self._apply_defaults(params)
            
            return {
                "success": True,
                "parameters": params
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Command parsing error: {str(e)}"
            }
    
    def _extract_numeric_parameters(self, command_lower: str) -> Dict[str, Any]:
        """Extract numeric parameters from command"""
        params = {}
        
        # Extract users (supports singular/plural and English)
        if "usuario" in command_lower or "usuarios" in command_lower or "user" in command_lower or "users" in command_lower:
            users_match = re.search(r'(\d+)\s*(usuario|usuarios|user|users)', command_lower)
            if users_match:
                params["virtual_users"] = int(users_match.group(1))
            else:
                # Fallback to first number if "usuario/user" mentioned
                numbers = re.findall(r'\d+', command_lower)
                if numbers:
                    params["virtual_users"] = int(numbers[0])
        
        # Extract RPS
        if "rps" in command_lower:
            rps_match = re.search(r'(\d+\.?\d*)\s*rps', command_lower)
            if rps_match:
                params["agent_rps"] = float(rps_match.group(1))
        
        # Extract duration (supports plural and English)
        if "minuto" in command_lower or "minutos" in command_lower or "minute" in command_lower or "minutes" in command_lower:
            duration_match = re.search(r'(\d+)\s*(minuto|minutos|minute|minutes)', command_lower)
            if duration_match:
                params["duration_minutes"] = int(duration_match.group(1))
        
        return params
    
    def _apply_defaults(self, params: Dict[str, Any]) -> None:
        """Apply default values for missing parameters"""
        params.setdefault("virtual_users", 3)
        params.setdefault("duration_minutes", 1)
        params.setdefault("env_code", "STA")  # Default environment is always STA
    
    def validate_extracted_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted parameters
        
        Returns:
            Dict with validation result and errors if any
        """
        errors = []
        
        # Check required parameters
        required_params = ["app_code", "env_code"]
        for param in required_params:
            if not params.get(param):
                errors.append(f"Missing required parameter: {param}")
        
        # Validate ranges
        if "virtual_users" in params:
            users = params["virtual_users"]
            if not isinstance(users, int) or users < 1 or users > 1000:
                errors.append("virtual_users must be between 1 and 1000")
        
        if "duration_minutes" in params:
            duration = params["duration_minutes"]
            if not isinstance(duration, int) or duration < 1 or duration > 120:
                errors.append("duration_minutes must be between 1 and 120")
        
        if "agent_rps" in params:
            rps = params["agent_rps"]
            if not isinstance(rps, (int, float)) or rps < 0.1 or rps > 100:
                errors.append("agent_rps must be between 0.1 and 100")
        
        return {
            "success": len(errors) == 0,
            "errors": errors
        }
    
    def get_supported_patterns(self) -> Dict[str, Any]:
        """Get documentation of supported parsing patterns"""
        return {
            "applications": {
                "EVA_RO": ["eva", "eva-ro", "eva_ro", "eva ro", "eva romania"],
                "PAYROLL": ["payroll"],
                "ONEAPP": ["oneapp"]
            },
            "environments": {
                "STA": ["sta", "staging"],
                "TEST": ["test"],
                "PROD": ["prod", "production"]
            },
            "countries": {
                "RO": ["ro", "romania"],
                "FR": ["fr", "france"],
                "BE": ["be", "belgium"]
            },
            "examples": [
                "Probar EVA en STA con 2 usuarios durante 1 minuto para RO",
                "Test PAYROLL in TEST with 5 users for 3 minutes",
                "Run ONEAPP staging 10 users 2 minutes BE"
            ]
        }


# Factory function for convenience
def create_parser() -> PerformanceCommandParser:
    """Create a new parser instance"""
    return PerformanceCommandParser()


# Legacy function name for compatibility
def parse_natural_language_command(command: str, **kwargs) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    parser = create_parser()
    return parser.parse_natural_language_command(command, **kwargs)
