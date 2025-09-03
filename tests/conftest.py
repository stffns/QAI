# Pytest configuration and fixtures for QA Intelligence tests

import sys
import os
import pytest
from typing import Any, Union
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import Pydantic configuration models
try:
    from config.models import ModelConfig, DatabaseConfig, ToolsConfig
    from config.settings import Settings
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("⚠️  Pydantic config models not available, using mock configs")


class MockModel:
    """Mock model for testing"""
    def __init__(self, name: str = "test-model"):
        self.name = name
        self.id = f"mock_{name}"
    
    def __str__(self):
        return f"MockModel({self.name})"


class MockTool:
    """Mock tool for testing"""
    def __init__(self, name: str, description: str = "Test tool"):
        self.name = name
        self.description = description
        self.functions = [f"function_{i}" for i in range(3)]  # Mock functions list
    
    def __call__(self, *args, **kwargs):
        return f"Tool {self.name} executed with {args}, {kwargs}"


class ConfigForTesting:
    """Configuration class for testing that implements improved validation contract"""
    
    def __init__(self, should_fail: bool = False, fail_type: str = "value"):
        self.should_fail = should_fail
        self.fail_type = fail_type
        
        # Initialize with Pydantic models if available
        if PYDANTIC_AVAILABLE:
            self._setup_pydantic_config()
        else:
            self._setup_mock_config()
    
    def _setup_pydantic_config(self):
        """Setup using actual Pydantic configuration models"""
        try:
            self.model_config = ModelConfig(
                provider="openai",
                id="gpt-3.5-turbo",
                api_key="test-api-key",
                temperature=0.7
            )
            self.database_config = DatabaseConfig()
            self.tools_config = ToolsConfig()
        except Exception as e:
            print(f"⚠️  Error setting up Pydantic config: {e}")
            self._setup_mock_config()
    
    def _setup_mock_config(self):
        """Setup using mock configuration for backwards compatibility"""
        self.model_config = None
        self.database_config = None
        self.tools_config = None
    
    def validate_config(self) -> None:
        """Implements improved contract: raises specific exceptions"""
        if self.should_fail:
            if self.fail_type == "value":
                raise ValueError("Test configuration value error")
            elif self.fail_type == "key":
                raise KeyError("Missing test configuration key")
            else:
                raise Exception("Generic test error")
        
        # If using Pydantic models, validate them
        if PYDANTIC_AVAILABLE and self.model_config:
            # This will raise ValidationError if invalid
            self.model_config.model_validate(self.model_config.model_dump())
    
    def get_interface_config(self) -> dict[str, Any]:
        return {
            "show_tool_calls": True,
            "enable_markdown": True
        }
    
    def get_agent_instructions(self) -> Union[str, list[str]]:
        # Return list to test normalization
        return [
            "You are a test QA assistant.",
            "Always validate test data.",
            "Provide clear test results."
        ]
    
    def get_model_config(self) -> dict[str, Any]:
        if PYDANTIC_AVAILABLE and self.model_config:
            return self.model_config.model_dump()
        
        return {
            "provider": "openai",
            "id": "gpt-3.5-turbo",
            "api_key": "test-api-key",
            "temperature": 0.7,
            "max_tokens": 1000
        }
    
    def get_tools_config(self) -> dict[str, Any]:
        if PYDANTIC_AVAILABLE and self.tools_config:
            return self.tools_config.model_dump()
        
        return {
            "enabled": True,
            "tools": [
                {"name": "calculator", "enabled": True},
                {"name": "test_tool", "enabled": True}
            ]
        }
    
    def get_storage_config(self) -> dict[str, Any]:
        return {"enabled": False}


class MockModelManager:
    """Mock model manager for testing"""
    def __init__(self, config, should_fail: bool = False):
        self.config = config
        self.should_fail = should_fail
    
    def create_model(self):
        if self.should_fail:
            raise Exception("Mock model creation failed")
        return MockModel("test-gpt-4")
    
    def get_model_info(self):
        return {"model": "MockModel", "status": "ready"}


class MockToolsManager:
    """Mock tools manager for testing"""
    def __init__(self, config, return_type: str = "list", should_fail: bool = False):
        self.config = config
        self.return_type = return_type
        self.should_fail = should_fail
    
    def load_tools(self):
        if self.should_fail:
            raise Exception("Mock tools loading failed")
        
        tools = [
            MockTool("calculator", "Calculator tool"),
            MockTool("web_search", "Web search tool"),
            lambda x: f"Lambda tool: {x}",  # Test callable
            {"name": "dict_tool", "type": "dictionary"}  # Test dict-like
        ]
        
        if self.return_type == "tuple":
            return tuple(tools)
        return tools
    
    def get_tools_info(self):
        return {"tools_count": 4, "status": "loaded"}


class MockStorageManager:
    """Mock storage manager for testing"""
    def __init__(self, config, should_fail: bool = False):
        self.config = config
        self.should_fail = should_fail
    
    def setup_storage(self):
        if self.should_fail:
            raise Exception("Mock storage setup failed")
        return None  # No storage for testing
    
    def get_storage_info(self):
        return {"storage": "disabled", "status": "ready"}


@pytest.fixture
def test_config():
    """Fixture for valid test configuration"""
    return ConfigForTesting()


@pytest.fixture
def failing_config():
    """Fixture for configuration that should fail validation"""
    return ConfigForTesting(should_fail=True, fail_type="value")


@pytest.fixture
def missing_key_config():
    """Fixture for configuration with missing key error"""
    return ConfigForTesting(should_fail=True, fail_type="key")


@pytest.fixture
def mock_model_manager():
    """Fixture for mock model manager"""
    config = ConfigForTesting()
    return MockModelManager(config)


@pytest.fixture
def mock_tools_manager():
    """Fixture for mock tools manager"""
    config = ConfigForTesting()
    return MockToolsManager(config)


@pytest.fixture
def mock_tools_manager_tuple():
    """Fixture for mock tools manager that returns tuple"""
    config = ConfigForTesting()
    return MockToolsManager(config, return_type="tuple")


@pytest.fixture
def mock_storage_manager():
    """Fixture for mock storage manager"""
    config = ConfigForTesting()
    return MockStorageManager(config)


@pytest.fixture
def qa_agent_dependencies(test_config, mock_model_manager, mock_tools_manager, mock_storage_manager):
    """Fixture providing all QA Agent dependencies"""
    return {
        "config": test_config,
        "model_manager": mock_model_manager,
        "tools_manager": mock_tools_manager,
        "storage_manager": mock_storage_manager
    }


@pytest.fixture(autouse=True)
def setup_logging():
    """Auto-setup logging for all tests"""
    try:
        from logging_config import setup_qa_logging
        setup_qa_logging(level="ERROR", enable_file_logging=False)  # Minimize test noise
    except ImportError:
        pass  # Skip if logging_config not available
