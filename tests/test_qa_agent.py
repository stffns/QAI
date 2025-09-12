# Tests for core QA Agent functionality
# These tests focus on the main functionality and must always pass

import pytest
from unittest.mock import patch, MagicMock
from conftest import ConfigForTesting, MockModelManager, MockToolsManager, MockStorageManager


class TestQAAgentCore:
    """Test core QA Agent functionality that must always work"""
    
    def test_agent_imports_successfully(self):
        """Test that QA Agent can be imported without errors"""
        try:
            from agent.qa_agent import QAAgent
            assert QAAgent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import QAAgent: {e}")
    
    def test_agent_initialization_with_valid_config(self, qa_agent_dependencies):
        """Test QA Agent initialization with valid configuration"""
        from agent.qa_agent import QAAgent
        
        agent = QAAgent(
            config=qa_agent_dependencies["config"],
            model_manager=qa_agent_dependencies["model_manager"],
            tools_manager=qa_agent_dependencies["tools_manager"],
            storage_manager=qa_agent_dependencies["storage_manager"]
        )
        
        assert agent is not None
        assert agent.config is not None
        assert agent.model_manager is not None
        assert agent.tools_manager is not None
        assert agent.storage_manager is not None
    
    @pytest.mark.parametrize("fail_type", ["value", "key", "generic"])
    def test_config_validation_contract(self, fail_type):
        """Test improved config validation contract - exception-based validation"""
        config = ConfigForTesting(should_fail=True, fail_type=fail_type)
        
        # The new contract: validate_config() raises exceptions instead of returning bool
        with pytest.raises(Exception) as exc_info:
            config.validate_config()
        
        # Verify specific exception types
        if fail_type == "value":
            assert isinstance(exc_info.value, ValueError)
        elif fail_type == "key":
            assert isinstance(exc_info.value, KeyError)
        else:
            assert isinstance(exc_info.value, Exception)
    
    def test_config_validation_success(self, test_config):
        """Test that valid config passes validation without raising exceptions"""
        # Should not raise any exception
        test_config.validate_config()
    
    def test_instructions_normalization(self, test_config):
        """Test instructions normalization bug fix"""
        from agent.qa_agent import QAAgent
        
        # Create agent with list-based instructions
        agent = QAAgent(
            config=test_config,
            model_manager=MockModelManager(test_config),
            tools_manager=MockToolsManager(test_config),
            storage_manager=MockStorageManager(test_config)
        )
        
        # Get instructions from config (should be list)
        instructions = test_config.get_agent_instructions()
        
        # Call normalize instructions method with parameter
        normalized, metadata = agent._normalize_instructions(instructions)
        
        # Verify it's now a string
        assert isinstance(normalized, str)
        
        # Verify it contains expected content
        assert "You are a test QA assistant" in normalized
        assert "Always validate test data" in normalized
        assert "Provide clear test results" in normalized
        
        # Verify proper formatting (newlines between instructions)
        lines = normalized.split('\n')
        assert len(lines) >= 3
        
        # Verify metadata
        assert isinstance(metadata, dict)
        assert metadata["instructions_type"] == "list"
        assert metadata["instructions_items"] == 3
    
    def test_tools_validation_and_normalization(self):
        """Test tools validation improvements - tuple to list conversion"""
        from agent.qa_agent import QAAgent
        
        config = ConfigForTesting()
        model_manager = MockModelManager(config)
        tools_manager = MockToolsManager(config, return_type="tuple")
        storage_manager = MockStorageManager(config)
        
        agent = QAAgent(
            config=config,
            model_manager=model_manager,
            tools_manager=tools_manager,
            storage_manager=storage_manager
        )
        
        # Get tools from manager (should be tuple)
        tools = tools_manager.load_tools()
        
        # Call tools validation method with parameter
        validated_tools = agent._validate_and_normalize_tools(tools)
        
        # Verify it's now a list (not tuple)
        assert isinstance(validated_tools, list)
        
        # Verify content is preserved
        assert len(validated_tools) == 4
        
        # Verify different tool types are handled
        tool_names = [getattr(tool, 'name', str(tool)) for tool in validated_tools]
        assert any('calculator' in str(name) for name in tool_names)
        assert any('web_search' in str(name) for name in tool_names)
    
    def test_agent_health_check(self, qa_agent_dependencies):
        """Test agent health check functionality"""
        from agent.qa_agent import QAAgent
        
        agent = QAAgent(**qa_agent_dependencies)
        
        # Test that agent can perform basic health checks
        try:
            # Get test data for method calls
            instructions = qa_agent_dependencies["config"].get_agent_instructions()
            tools = qa_agent_dependencies["tools_manager"].load_tools()
            
            # These should not raise exceptions
            normalized, metadata = agent._normalize_instructions(instructions)
            validated_tools = agent._validate_and_normalize_tools(tools)
            agent.config.validate_config()
            
            health_status = True
        except Exception as e:
            health_status = False
            pytest.fail(f"Agent health check failed: {e}")
        
        assert health_status is True
    
    def test_agent_initialization_failure_handling(self):
        """Test agent handles initialization failures gracefully"""
        from agent.qa_agent import QAAgent
        
        config = ConfigForTesting(should_fail=True)
        
        # Should raise exception during initialization due to config validation
        with pytest.raises(Exception):
            QAAgent(
                config=config,
                model_manager=MockModelManager(config),
                tools_manager=MockToolsManager(config),
                storage_manager=MockStorageManager(config)
            )
    
    def test_manager_integration(self):
        """Test that QA Agent integrates properly with all managers"""
        from agent.qa_agent import QAAgent
        
        config = ConfigForTesting()
        model_manager = MockModelManager(config)
        tools_manager = MockToolsManager(config)
        storage_manager = MockStorageManager(config)
        
        agent = QAAgent(
            config=config,
            model_manager=model_manager,
            tools_manager=tools_manager,
            storage_manager=storage_manager
        )
        
        # Test that managers are properly integrated
        assert agent.model_manager.get_model_info()["status"] == "ready"
        assert agent.tools_manager.get_tools_info()["status"] == "loaded"
        assert agent.storage_manager.get_storage_info()["status"] == "ready"
    
    def test_logging_integration(self, qa_agent_dependencies):
        """Test that logging integration works without errors"""
        from agent.qa_agent import QAAgent
        
        # Should not raise logging-related exceptions
        agent = QAAgent(**qa_agent_dependencies)
        
        # Get test data for method calls
        instructions = qa_agent_dependencies["config"].get_agent_instructions()
        tools = qa_agent_dependencies["tools_manager"].load_tools()
        
        # These operations should be logged without errors
        normalized, metadata = agent._normalize_instructions(instructions)
        validated_tools = agent._validate_and_normalize_tools(tools)
        
        # Test passes if no logging exceptions occur


class TestQAAgentRegressionSafety:
    """Tests that prevent regression of the three main improvements"""
    
    def test_config_validation_regression_safety(self):
        """Ensure config validation doesn't regress to boolean return"""
        config = ConfigForTesting(should_fail=True)
        
        # The old contract returned bool, new contract raises exceptions
        # This test ensures we don't accidentally regress
        try:
            result = config.validate_config()
            # If we get here, it means validate_config returned something instead of raising
            # This would be a regression to the old boolean contract
            pytest.fail(f"validate_config() should raise exception, not return: {result}")
        except Exception:
            # This is expected - the new contract should raise exceptions
            pass
    
    def test_instructions_logging_regression_safety(self, test_config):
        """Ensure instructions logging doesn't regress to the old bug"""
        from agent.qa_agent import QAAgent
        
        agent = QAAgent(
            config=test_config,
            model_manager=MockModelManager(test_config),
            tools_manager=MockToolsManager(test_config),
            storage_manager=MockStorageManager(test_config)
        )
        
        # Get instructions from config
        instructions = test_config.get_agent_instructions()
        
        normalized, metadata = agent._normalize_instructions(instructions)
        
        # Regression safety: ensure it's always string, never list
        assert isinstance(normalized, str), "Instructions should be normalized to string"
        
        # Regression safety: ensure consistent character counting
        assert len(normalized) > 0, "Normalized instructions should not be empty"
        
        # Should not contain list artifacts like brackets or comma separation
        assert not normalized.startswith('['), "Should not contain list formatting artifacts"
        assert not normalized.endswith(']'), "Should not contain list formatting artifacts"
        
        # Test metadata consistency
        assert isinstance(metadata, dict), "Should return metadata"
        assert "instructions_length" in metadata, "Should have length metadata"
        assert metadata["instructions_length"] == len(normalized), "Metadata length should match actual length"
    
    def test_tools_validation_regression_safety(self):
        """Ensure tools validation doesn't regress to the old tuple issue"""
        from agent.qa_agent import QAAgent
        
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="tuple")
        
        agent = QAAgent(
            config=config,
            model_manager=MockModelManager(config),
            tools_manager=tools_manager,
            storage_manager=MockStorageManager(config)
        )
        
        # Get tools as tuple
        tools = tools_manager.load_tools()
        
        validated_tools = agent._validate_and_normalize_tools(tools)
        
        # Regression safety: ensure it's always list, never tuple
        assert isinstance(validated_tools, list), "Tools should always be normalized to list"
        
        # Regression safety: ensure content validation still works
        assert len(validated_tools) > 0, "Should have tools loaded"
        
        # Should handle different types without errors
        for tool in validated_tools:
            # Should not raise exceptions when accessing tool properties
            assert tool is not None
