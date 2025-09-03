"""
Tools Manager - Handles tool configuration and loading
"""


# SRP: This class has a single responsibility - managing agent tools.
# It handles tool loading, configuration, and provides a unified interface
# for all tool-related operations without mixing concerns with models or storage.
class ToolsManager:
    """Manages agent tools configuration and loading"""

    def __init__(self, config):
        """
        Initialize the tools manager with configuration

        Args:
            config: System configuration object
        """
        self.config = config
        self.tools = []

    def load_tools(self):
        """
        Load tools according to configuration

        Returns:
            list: List of loaded tools
        """
        tools_config = self.config.get_enabled_tools()
        self.tools = []

        # Web search tool
        if tools_config.get("web_search", False):
            self._load_web_search()

        # Python execution tool
        if tools_config.get("python_execution", False):
            self._load_python_tools()

        # Calculator tool
        if tools_config.get("calculator", False):
            self._load_calculator()

        # File operations tool
        if tools_config.get("file_operations", False):
            self._load_file_tools()

        return self.tools

    def _load_web_search(self):
        """Load web search tool"""
        try:
            from agno.tools.duckduckgo import DuckDuckGo

            self.tools.append(DuckDuckGo())
            print("✅ Web search tool (DuckDuckGo) enabled")
        except ImportError as e:
            print(f"⚠️  Web search tool not available: {e}")

    def _load_python_tools(self):
        """Load Python execution tools"""
        try:
            from agno.tools.python import PythonTools

            self.tools.append(PythonTools())
            print("✅ Python execution tool enabled")
        except ImportError as e:
            print(f"⚠️  Python execution tool not available: {e}")

    def _load_calculator(self):
        """Load calculator tool"""
        try:
            from agno.tools.calculator import CalculatorTools

            self.tools.append(CalculatorTools())
            print("✅ Calculator tool enabled")
        except ImportError as e:
            print(f"⚠️  Calculator tool not available: {e}")

    def _load_file_tools(self):
        """Load file operations tools"""
        try:
            from agno.tools.file import FileTools

            self.tools.append(FileTools())
            print("✅ File operations tools enabled")
        except ImportError as e:
            print(f"⚠️  File operations tools not available: {e}")

    def get_tools_info(self):
        """
        Get information about loaded tools

        Returns:
            dict: Tools information
        """
        return {
            "total_tools": len(self.tools),
            "tools_names": [tool.__class__.__name__ for tool in self.tools],
        }
