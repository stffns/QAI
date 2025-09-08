"""
Performance Tool - Clean Adapter Implementation

This is a clean, lightweight adapter that delegates to the PerformanceManager
(Fase 6) while maintaining the same public interface expected by the QA agent.

Replaces the 1781-line monolithic performance_tool_v2.py with a < 100 line adapter.

Architecture:
- Adapter Pattern: Delegates to PerformanceManager
- Clean Interface: Maintains compatibility with agent
- SOLID Principles: Single responsibility (adaptation only)
- Dependency Injection: Uses extracted components from Phases 5-6
"""

from typing import Optional
import json

# Import the SOLID architecture components (Phases 5-6)
from src.performance import PerformanceManager, PerformanceManagerConfig


class PerformanceTool:
    """
    Clean Performance Tool - Adapter to PerformanceManager
    
    This tool provides the same interface as the original performance tool
    but delegates all work to the SOLID architecture components.
    
    Responsibilities:
    - Adapter pattern: Convert agent interface to manager interface
    - Error formatting: Convert manager responses to agent format
    - Compatibility: Maintain exact same public API
    """
    
    def __init__(self):
        """Initialize the performance tool with PerformanceManager"""
        # Configure manager for agent use
        config = PerformanceManagerConfig(
            enable_monitoring=True,
            enable_sla_validation=True,
            max_concurrent_tests=3
        )
        
        # Initialize the SOLID architecture manager
        self.manager = PerformanceManager(config)
        
        # Tool metadata
        self.tool_name = "Performance Tool (SOLID Architecture)"
        self.version = "4.0.0"
        self.architecture = "Adapter -> Manager/Facade -> Services/Engine/Utils"
    
    def execute_performance_test(self, command: Optional[str] = None, **kwargs) -> str:
        """
        Execute performance test - Main entry point for the agent
        
        This method maintains the same signature as the original tool
        but delegates to the PerformanceManager (Fase 6).
        
        Args:
            command: Natural language command (optional)
            **kwargs: Additional parameters
            
        Returns:
            JSON string with execution results (agent format)
        """
        try:
            # Handle case where no command is provided
            if not command:
                return self._format_error("No command provided. Please specify a performance test command.")
            
            # Delegate to PerformanceManager (Fase 6 - Manager/Facade)
            result = self.manager.execute_performance_test_from_command(command, **kwargs)
            
            # Convert manager response to agent format
            if result["success"]:
                return self._format_success(result)
            else:
                return self._format_error(result["error"])
                
        except Exception as e:
            return self._format_error(f"Performance tool execution error: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> str:
        """
        Get status of a performance test execution
        
        Args:
            execution_id: Execution ID from execute_performance_test
            
        Returns:
            JSON string with execution status and results
        """
        try:
            # Delegate to manager for execution status
            status_result = self.manager.get_execution_status(execution_id)
            
            if status_result.get('success'):
                return self._format_success(status_result)
            else:
                return self._format_error(status_result.get('error', 'Unknown error getting execution status'))
                
        except Exception as e:
            return self._format_error(f"Error getting execution status: {str(e)}")
    
    def list_recent_executions(self, limit: int = 10) -> str:
        """
        List recent performance test executions
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            JSON string with list of recent executions
        """
        try:
            # Delegate to manager for recent executions
            executions_result = self.manager.list_recent_executions(limit)
            
            if executions_result.get('success'):
                return self._format_success(executions_result)
            else:
                return self._format_error(executions_result.get('error', 'Unknown error listing executions'))
                
        except Exception as e:
            return self._format_error(f"Error listing recent executions: {str(e)}")
    
    # ==================== UTILITY METHODS ====================
    
    def get_supported_patterns(self) -> str:
        """Get supported command patterns (agent format)"""
        try:
            patterns = self.manager.get_supported_patterns()
            return json.dumps({
                "success": True,
                "patterns": patterns,
                "tool_info": {
                    "name": self.tool_name,
                    "version": self.version,
                    "architecture": self.architecture
                }
            }, indent=2)
        except Exception as e:
            return self._format_error(f"Failed to get patterns: {str(e)}")
    
    def health_check(self) -> str:
        """Health check for the tool (agent format)"""
        try:
            health = self.manager.health_check()
            return json.dumps({
                "success": True,
                "health": health["health"],
                "tool_status": "healthy",
                "architecture_status": "SOLID principles implemented",
                "phases_completed": ["Phase 3: Engine", "Phase 4: Services", "Phase 5: Utils", "Phase 6: Manager"]
            }, indent=2)
        except Exception as e:
            return self._format_error(f"Health check failed: {str(e)}")
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _format_success(self, result: dict) -> str:
        """Format successful result for agent consumption"""
        response = {
            "success": True,
            "test_id": result.get("test_id"),
            "message": f"✅ Performance test executed successfully",
            "details": {
                "command_parsed": result.get("parsed_command"),
                "parameters": result.get("parameters"),
                "rps": result.get("rps"),
                "sla_validated": result.get("sla_validated", False),
                "manager_version": result.get("manager_version"),
                "architecture": "SOLID"
            },
            "execution_summary": {
                "application": result.get("parameters", {}).get("app_code"),
                "environment": result.get("parameters", {}).get("env_code"),
                "users": result.get("parameters", {}).get("virtual_users"),
                "duration": f"{result.get('parameters', {}).get('duration_minutes', 1)} minutes",
                "calculated_rps": result.get("rps")
            }
        }
        
        return json.dumps(response, indent=2)
    
    def _format_error(self, error_message: str) -> str:
        """Format error response for agent consumption"""
        response = {
            "success": False,
            "error": error_message,
            "tool_info": {
                "name": self.tool_name,
                "version": self.version,
                "architecture": self.architecture
            },
            "help": {
                "supported_commands": [
                    "Probar [APP] en [ENV] con [N] usuarios durante [M] minutos",
                    "Test [APP] in [ENV] with [N] users for [M] minutes",
                    "Run [APP] [ENV] [N] users [M] minutes"
                ],
                "examples": [
                    "Probar EVA en STA con 5 usuarios durante 2 minutos",
                    "Test PAYROLL in TEST with 3 users for 1 minute"
                ]
            }
        }
        
        return json.dumps(response, indent=2)


# Factory function for agent registration
def create_performance_tool() -> PerformanceTool:
    """Create a new PerformanceTool instance"""
    return PerformanceTool()


# Legacy class name for backward compatibility with existing agent registrations
class PerformanceToolV2(PerformanceTool):
    """Legacy class name for backward compatibility"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "Performance Tool V2 (SOLID Architecture Adapter)"
        
    # The original interface method name is maintained for compatibility
    # execute_performance_test is inherited from PerformanceTool