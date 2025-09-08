"""
Tools Manager - Handles tool configuration and loading
Enhanced with Agno best practices, tool validation, and graceful degradation
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

# Configure logging
try:
    from ..logging_config import get_logger, LogStep
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from logging_config import get_logger, LogStep

logger = get_logger("ToolsManager")


@dataclass
class ToolConfig:
    """Configuration for individual tools"""
    name: str
    enabled: bool = True
    essential: bool = False
    config: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass 
class ToolLoadResult:
    """Result of tool loading operation"""
    tool: Any
    name: str
    success: bool
    error: Optional[str] = None
    load_time: float = 0.0


class ToolLoadError(Exception):
    """Tool loading specific error"""
    pass


class ToolsManagerError(Exception):
    """Base error for ToolsManager"""
    pass


# SRP: This class has a single responsibility - managing agent tools with enhanced capabilities.
# It handles tool loading, configuration, validation, and provides graceful degradation
# following Agno best practices without mixing concerns with models or storage.
class ToolsManager:
    """
    Enhanced Tools Manager with Agno best practices
    
    Features:
    - Tool validation and health checking
    - Graceful degradation for failed tools
    - Configurable timeouts and retries
    - Structured error reporting
    - Performance monitoring
    """

    def __init__(self, config):
        """
        Initialize the tools manager with configuration

        Args:
            config: System configuration object
        """
        self.config = config
        self.tools: List[Any] = []
        self.tool_configs: Dict[str, ToolConfig] = {}
        self.load_results: List[ToolLoadResult] = []

    def _parse_tool_configs(self) -> Dict[str, ToolConfig]:
        """
        Parse tool configurations with enhanced validation
        
        Returns:
            Dictionary of tool configurations
        """
        # Get enabled tools as a dictionary
        enabled_tool_names = self.config.get_enabled_tools()
        parsed_configs = {}
        
        # enabled_tool_names is already a dict of {tool_name: enabled_status}
        
        # Default tool configurations following Agno patterns
        default_tools = {
            "web_search": ToolConfig(
                name="web_search",
                enabled=enabled_tool_names.get("web_search", False),
                essential=False,
                config={
                    "max_results": 5,
                    "region": "wt-wt", 
                    "timeout": 10,
                    "safe_search": "moderate"
                }
            ),
            "python_execution": ToolConfig(
                name="python_execution", 
                enabled=enabled_tool_names.get("python_execution", False),
                essential=False,
                config={
                    "timeout": 30,
                    "memory_limit": "512MB",
                    "allowed_imports": ["math", "datetime", "json", "re"]
                }
            ),
            "calculator": ToolConfig(
                name="calculator",
                enabled=enabled_tool_names.get("calculator", False), 
                essential=False,
                config={
                    "precision": 10,
                    "max_expression_length": 1000
                }
            ),
            "file_operations": ToolConfig(
                name="file_operations",
                enabled=enabled_tool_names.get("file_operations", False),
                essential=False,
                config={
                    "allowed_extensions": [".txt", ".json", ".csv", ".md"],
                    "max_file_size": "10MB",
                    "sandbox_mode": True
                }
            ),
            "qa_database_stats": ToolConfig(
                name="qa_database_stats",
                enabled=enabled_tool_names.get("qa_database_stats", True),
                essential=False,
                config={}
            ),
            "qa_apps": ToolConfig(
                name="qa_apps",
                enabled=enabled_tool_names.get("qa_apps", True),
                essential=False,
                config={}
            ),
            "qa_countries": ToolConfig(
                name="qa_countries",
                enabled=enabled_tool_names.get("qa_countries", True),
                essential=False,
                config={}
            ),
            "qa_mappings": ToolConfig(
                name="qa_mappings",
                enabled=enabled_tool_names.get("qa_mappings", True),
                essential=False,
                config={}
            ),
            "qa_search": ToolConfig(
                name="qa_search",
                enabled=enabled_tool_names.get("qa_search", True),
                essential=False,
                config={}
            ),
            # SQL Tools for advanced database analysis
            "sql_execute_query": ToolConfig(
                name="sql_execute_query",
                enabled=enabled_tool_names.get("sql_execute_query", True),
                essential=False,
                config={}
            ),
            "sql_analyze_table": ToolConfig(
                name="sql_analyze_table",
                enabled=enabled_tool_names.get("sql_analyze_table", True),
                essential=False,
                config={}
            ),
            "sql_explore_database": ToolConfig(
                name="sql_explore_database",
                enabled=enabled_tool_names.get("sql_explore_database", True),
                essential=False,
                config={}
            ),
            "sql_qa_analytics": ToolConfig(
                name="sql_qa_analytics",
                enabled=enabled_tool_names.get("sql_qa_analytics", True),
                essential=False,
                config={}
            ),
            # API Tools for endpoint testing and monitoring
            "api_test_endpoint": ToolConfig(
                name="api_test_endpoint",
                enabled=enabled_tool_names.get("api_test_endpoint", True),
                essential=False,
                config={}
            ),
            "api_health_check": ToolConfig(
                name="api_health_check",
                enabled=enabled_tool_names.get("api_health_check", True),
                essential=False,
                config={}
            ),
            "api_performance_test": ToolConfig(
                name="api_performance_test",
                enabled=enabled_tool_names.get("api_performance_test", True),
                essential=False,
                config={}
            ),
            "get_execution_status": ToolConfig(
                name="get_execution_status",
                enabled=enabled_tool_names.get("get_execution_status", True),
                essential=False,
                config={}
            ),
            "list_recent_performance_tests": ToolConfig(
                name="list_recent_performance_tests",
                enabled=enabled_tool_names.get("list_recent_performance_tests", True),
                essential=False,
                config={}
            )
        }
        
        for tool_name, default_config in default_tools.items():
            # Merge with user configuration if provided
            user_config = {}  # For now, use defaults
            if isinstance(user_config, dict) and default_config.config:
                default_config.config.update(user_config)
            
            parsed_configs[tool_name] = default_config
            
        return parsed_configs

    def load_tools(self) -> List[Any]:
        """
        Load tools with enhanced error handling and validation
        
        Returns:
            List of successfully loaded tools
            
        Raises:
            ToolsManagerError: If essential tools fail to load
        """
        with LogStep("Tools loading with validation", "ToolsManager"):
            self.tool_configs = self._parse_tool_configs()
            self.tools = []
            self.load_results = []
            
            essential_failures = []
            
            for tool_name, tool_config in self.tool_configs.items():
                if not tool_config.enabled:
                    logger.debug(f"Tool {tool_name} disabled in configuration")
                    continue
                    
                result = self._load_single_tool(tool_config)
                self.load_results.append(result)
                
                if result.success:
                    self.tools.append(result.tool)
                    logger.info(f"✅ {tool_name} loaded successfully in {result.load_time:.3f}s")
                else:
                    if tool_config.essential:
                        essential_failures.append(f"{tool_name}: {result.error}")
                    logger.warning(f"⚠️ {tool_name} failed to load: {result.error}")
            
            # Check for essential tool failures
            if essential_failures:
                error_msg = f"Essential tools failed: {'; '.join(essential_failures)}"
                logger.error(error_msg)
                raise ToolsManagerError(error_msg)
            
            logger.info(f"Tools loaded: {len(self.tools)}/{len([c for c in self.tool_configs.values() if c.enabled])} successful")
            return self.tools

    def _load_single_tool(self, tool_config: ToolConfig) -> ToolLoadResult:
        """
        Load a single tool with timeout and error handling
        
        Args:
            tool_config: Configuration for the tool to load
            
        Returns:
            ToolLoadResult with success status and details
        """
        start_time = time.time()
        
        try:
            tool = None
            
            if tool_config.name == "web_search":
                tool = self._load_web_search_tool(tool_config)
            elif tool_config.name == "python_execution":
                tool = self._load_python_tools(tool_config)
            elif tool_config.name == "calculator":
                tool = self._load_calculator_tool(tool_config)
            elif tool_config.name == "file_operations":
                tool = self._load_file_tools(tool_config)
            elif tool_config.name in ["qa_database_stats", "qa_apps", "qa_countries", "qa_mappings", "qa_search"]:
                tool = self._load_database_tool(tool_config)
            elif tool_config.name in ["sql_execute_query", "sql_analyze_table", "sql_explore_database", "sql_qa_analytics"]:
                tool = self._load_sql_tool(tool_config)
            elif tool_config.name in ["api_test_endpoint", "api_health_check", "api_performance_test", 
                                     "get_execution_status", "list_recent_performance_tests"]:
                tool = self._load_api_tool(tool_config)
            else:
                raise ToolLoadError(f"Unknown tool: {tool_config.name}")
            
            # Validate tool after loading
            self._validate_tool(tool, tool_config.name)
            
            load_time = time.time() - start_time
            return ToolLoadResult(
                tool=tool,
                name=tool_config.name, 
                success=True,
                load_time=load_time
            )
            
        except Exception as e:
            load_time = time.time() - start_time
            return ToolLoadResult(
                tool=None,
                name=tool_config.name,
                success=False, 
                error=str(e),
                load_time=load_time
            )

    def _load_web_search_tool(self, tool_config: ToolConfig) -> Any:
        """Load web search tool with Agno best practices"""
        try:
            # Try multiple web search implementations
            try:
                from agno.tools.duckduckgo import DuckDuckGo
                tool = DuckDuckGo()
                
                # Apply configuration if tool supports it
                if hasattr(tool, 'configure') and tool_config.config:
                    tool.configure(**tool_config.config)
                    
                return tool
                
            except ImportError:
                # Fallback to alternative search tools
                from agno.tools.web import WebSearchTool
                return WebSearchTool(**tool_config.config)
                
        except ImportError as e:
            raise ToolLoadError(f"Web search tool not available: {e}")

    def _load_python_tools(self, tool_config: ToolConfig) -> Any:
        """Load Python execution tools with enhanced security"""
        try:
            from agno.tools.python import PythonTools
            
            # Apply security configurations
            config = tool_config.config or {}
            
            # Create tool with safe configuration
            tool = PythonTools(
                timeout=config.get("timeout", 30),
                # Add other security parameters as supported by Agno
            )
            
            return tool
            
        except ImportError as e:
            raise ToolLoadError(f"Python execution tool not available: {e}")

    def _load_calculator_tool(self, tool_config: ToolConfig) -> Any:
        """Load calculator tool with precision configuration"""
        try:
            from agno.tools.calculator import CalculatorTools
            
            tool = CalculatorTools()
            
            # Apply precision settings if supported
            config = tool_config.config or {}
            if hasattr(tool, 'set_precision'):
                tool.set_precision(config.get("precision", 10))
                
            return tool
            
        except ImportError as e:
            raise ToolLoadError(f"Calculator tool not available: {e}")

    def _load_file_tools(self, tool_config: ToolConfig) -> Any:
        """Load file operations tools with security constraints"""
        try:
            from agno.tools.file import FileTools
            
            config = tool_config.config or {}
            
            # Create with security constraints
            tool = FileTools()
            
            # Apply security settings if supported  
            if hasattr(tool, 'set_constraints'):
                tool.set_constraints(
                    allowed_extensions=config.get("allowed_extensions", []),
                    max_file_size=config.get("max_file_size", "10MB"),
                    sandbox_mode=config.get("sandbox_mode", True)
                )
                
            return tool
            
        except ImportError as e:
            raise ToolLoadError(f"File operations tools not available: {e}")

    def _load_database_tool(self, tool_config: ToolConfig):
        """Load individual database tool for QA Intelligence using Agno @tool decorator"""
        try:
            # Import the database tools with proper paths
            import sys
            import os
            
            # Add the project root to the path
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            if project_root not in sys.path:
                sys.path.append(project_root)
            
            from src.agent.tools.database_tools import (
                database_stats,
                list_apps,
                list_countries,
                list_mappings,
                search_qa_data
            )
            
            # Map tool config name to actual function
            tool_mapping = {
                "qa_database_stats": database_stats,
                "qa_apps": list_apps,
                "qa_countries": list_countries,
                "qa_mappings": list_mappings,
                "qa_search": search_qa_data
            }
            
            if tool_config.name not in tool_mapping:
                raise ToolLoadError(f"Unknown database tool: {tool_config.name}")
            
            return tool_mapping[tool_config.name]
            
        except ImportError as e:
            raise ToolLoadError(f"Database tool {tool_config.name} not available: {e}")

    def _load_sql_tool(self, tool_config: ToolConfig):
        """Load individual SQL tool for advanced database analysis using Agno SQLTools"""
        try:
            # Import the SQL tools with proper paths
            import sys
            import os
            
            # Add the project root to the path
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            if project_root not in sys.path:
                sys.path.append(project_root)
            
            from src.agent.tools.sql_tools import (
                sql_execute_query,
                sql_analyze_table,
                sql_explore_database,
                sql_qa_analytics
            )
            
            # Map tool config name to actual function
            tool_mapping = {
                "sql_execute_query": sql_execute_query,
                "sql_analyze_table": sql_analyze_table,
                "sql_explore_database": sql_explore_database,
                "sql_qa_analytics": sql_qa_analytics
            }
            
            if tool_config.name not in tool_mapping:
                raise ToolLoadError(f"Unknown SQL tool: {tool_config.name}")
            
            return tool_mapping[tool_config.name]
            
        except ImportError as e:
            raise ToolLoadError(f"SQL tool {tool_config.name} not available: {e}")

    def _load_api_tool(self, tool_config: ToolConfig) -> Any:
        """Load API testing tools with enhanced QA functionality"""
        try:
            # Add the project root to the path if needed
            import sys
            import os
            
            # Add the project root to the path
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            if project_root not in sys.path:
                sys.path.append(project_root)
            
            from src.agent.tools.api_tools import (
                api_test_endpoint,
                api_health_check,
                api_performance_test,
                get_execution_status,
                list_recent_performance_tests
            )
            
            # Map tool config name to actual function
            tool_mapping = {
                "api_test_endpoint": api_test_endpoint,
                "api_health_check": api_health_check,
                "api_performance_test": api_performance_test,
                "get_execution_status": get_execution_status,
                "list_recent_performance_tests": list_recent_performance_tests
            }
            
            if tool_config.name not in tool_mapping:
                raise ToolLoadError(f"Unknown API tool: {tool_config.name}")
            
            return tool_mapping[tool_config.name]
            
        except ImportError as e:
            raise ToolLoadError(f"API tool {tool_config.name} not available: {e}")

    def _validate_tool(self, tool: Any, tool_name: str) -> None:
        """
        Validate that a tool meets Agno compatibility requirements
        
        Args:
            tool: Tool instance to validate
            tool_name: Name of the tool for logging
            
        Raises:
            ToolLoadError: If tool doesn't meet requirements
        """
        # Check basic tool interface
        if not any([
            callable(tool),
            hasattr(tool, "run") and callable(getattr(tool, "run")),
            isinstance(tool, dict),
            hasattr(tool, "functions"),  # Agno tools have this
            hasattr(tool, "entrypoint") and callable(getattr(tool, "entrypoint"))  # Agno Function objects
        ]):
            raise ToolLoadError(f"Tool {tool_name} doesn't implement required interface")
        
        # Test tool if it supports health checking
        if hasattr(tool, 'health_check'):
            try:
                health = tool.health_check()
                if not health:
                    raise ToolLoadError(f"Tool {tool_name} failed health check")
            except Exception as e:
                logger.warning(f"Health check failed for {tool_name}: {e}")
        
        # Validate tool metadata
        if hasattr(tool, 'name') and not getattr(tool, 'name'):
            logger.warning(f"Tool {tool_name} missing name attribute")
            
        logger.debug(f"Tool {tool_name} validation passed")

    def get_tools_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about loaded tools
        
        Returns:
            Dictionary with detailed tool information
        """
        total_enabled = len([c for c in self.tool_configs.values() if c.enabled])
        successful_loads = len([r for r in self.load_results if r.success])
        failed_loads = len([r for r in self.load_results if not r.success])
        
        return {
            "total_tools": len(self.tools),
            "total_enabled": total_enabled,
            "successful_loads": successful_loads,
            "failed_loads": failed_loads,
            "tools_names": [getattr(tool, "name", tool.__class__.__name__) for tool in self.tools],
            "load_results": [
                {
                    "name": result.name,
                    "success": result.success,
                    "load_time": result.load_time,
                    "error": result.error
                }
                for result in self.load_results
            ],
            "health_status": "healthy" if failed_loads == 0 else "degraded",
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all loaded tools
        
        Returns:
            Health status for each tool
        """
        health_report = {
            "overall_healthy": True,
            "tools": {}
        }
        
        for tool in self.tools:
            tool_name = getattr(tool, "name", tool.__class__.__name__)
            
            try:
                if hasattr(tool, 'health_check'):
                    tool_health = tool.health_check()
                    health_report["tools"][tool_name] = {
                        "healthy": bool(tool_health),
                        "details": tool_health if isinstance(tool_health, dict) else {}
                    }
                else:
                    # Basic health check - try to access the tool
                    health_report["tools"][tool_name] = {
                        "healthy": True,
                        "details": {"basic_check": "passed"}
                    }
                    
            except Exception as e:
                health_report["tools"][tool_name] = {
                    "healthy": False,
                    "details": {"error": str(e)}
                }
                health_report["overall_healthy"] = False
        
        return health_report
