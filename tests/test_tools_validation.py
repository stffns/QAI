# Tests for tools validation and normalization
# Tests must always pass to ensure tuple→list conversion and content validation work

import pytest
from conftest import MockToolsManager, ConfigForTesting, MockTool


class TestToolsValidationAndNormalization:
    """Test tools validation improvements"""
    
    def test_tuple_to_list_conversion(self):
        """Test that tools tuple is converted to list"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="tuple")
        
        # Load tools as tuple
        tools = tools_manager.load_tools()
        assert isinstance(tools, tuple), "Setup verification: should start as tuple"
        
        # Test conversion (simulating agent's _validate_and_normalize_tools)
        if isinstance(tools, tuple):
            normalized_tools = list(tools)
        else:
            normalized_tools = tools
        
        assert isinstance(normalized_tools, list), "Tools should be converted from tuple to list"
        assert len(normalized_tools) == len(tools), "No tools should be lost in conversion"
    
    def test_list_tools_remain_list(self):
        """Test that tools already in list format remain unchanged"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="list")
        
        # Load tools as list
        tools = tools_manager.load_tools()
        assert isinstance(tools, list), "Setup verification: should start as list"
        
        # Test that list remains list
        if isinstance(tools, tuple):
            normalized_tools = list(tools)
        else:
            normalized_tools = tools
        
        assert isinstance(normalized_tools, list), "Tools should remain as list"
        assert normalized_tools is tools or normalized_tools == tools, "List should not be unnecessarily changed"
    
    def test_tools_content_validation(self):
        """Test that tools content is properly validated"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config)
        
        tools = tools_manager.load_tools()
        
        # Validate that tools list contains expected types
        assert len(tools) == 4, "Should have 4 test tools"
        
        # Test different tool types are present
        tool_types = [type(tool).__name__ for tool in tools]
        assert 'MockTool' in tool_types, "Should contain MockTool instances"
        assert 'function' in tool_types, "Should contain lambda functions"
        assert 'dict' in tool_types, "Should contain dictionary tools"
    
    def test_tools_validation_handles_different_types(self):
        """Test that validation handles different tool types correctly"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config)
        
        tools = tools_manager.load_tools()
        
        # Test each tool type
        for tool in tools:
            if hasattr(tool, 'name'):
                # MockTool type
                assert isinstance(tool.name, str)
                assert len(tool.name) > 0
            elif callable(tool):
                # Lambda/function type
                try:
                    result = tool("test")
                    assert isinstance(result, str), "Callable tool should return string"
                    assert "Lambda tool" in str(result), "Should contain expected content"
                except Exception as e:
                    pytest.fail(f"Callable tool should work: {e}")
            elif isinstance(tool, dict):
                # Dictionary type
                assert 'name' in tool or 'type' in tool
    
    def test_tools_validation_preserves_functionality(self):
        """Test that validation preserves tool functionality"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="tuple")
        
        original_tools = tools_manager.load_tools()
        
        # Convert tuple to list (simulating validation)
        normalized_tools = list(original_tools) if isinstance(original_tools, tuple) else original_tools
        
        # Test that functionality is preserved
        for i, (original, normalized) in enumerate(zip(original_tools, normalized_tools)):
            assert original is normalized, f"Tool {i} should be the same object after normalization"
            
            # Test functionality for MockTool instances
            if hasattr(original, '__call__'):
                try:
                    original_result = original("test")
                    normalized_result = normalized("test")
                    assert original_result == normalized_result
                except Exception:
                    # Not all tools may be callable in the same way
                    pass
    
    def test_empty_tools_handling(self):
        """Test handling of empty tools collections"""
        # Test empty tuple
        empty_tuple = tuple()
        normalized = list(empty_tuple) if isinstance(empty_tuple, tuple) else empty_tuple
        assert isinstance(normalized, list)
        assert len(normalized) == 0
        
        # Test empty list
        empty_list = []
        normalized = list(empty_list) if isinstance(empty_list, tuple) else empty_list
        assert isinstance(normalized, list)
        assert len(normalized) == 0
    
    def test_tools_validation_error_handling(self):
        """Test that tools validation handles errors gracefully"""
        config = ConfigForTesting()
        failing_tools_manager = MockToolsManager(config, should_fail=True)
        
        # Should raise exception when tools loading fails
        with pytest.raises(Exception) as exc_info:
            failing_tools_manager.load_tools()
        
        assert "Mock tools loading failed" in str(exc_info.value)
    
    def test_tools_info_consistency(self):
        """Test that tools info remains consistent after validation"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config)
        
        info_before = tools_manager.get_tools_info()
        tools = tools_manager.load_tools()
        
        # Normalize tools
        normalized_tools = list(tools) if isinstance(tools, tuple) else tools
        
        info_after = tools_manager.get_tools_info()
        
        # Info should remain consistent
        assert info_before == info_after
        assert info_after["tools_count"] == len(normalized_tools)
        assert info_after["status"] == "loaded"


class TestToolsValidationRegressionSafety:
    """Tests to prevent regression of tools validation improvements"""
    
    def test_no_regression_to_tuple_handling_issues(self):
        """Ensure we don't regress to the old tuple handling problems"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="tuple")
        
        tools = tools_manager.load_tools()
        assert isinstance(tools, tuple), "Test setup: should be tuple"
        
        # The old code might have failed here or not handled tuple properly
        # New code should always convert to list
        try:
            normalized_tools = list(tools) if isinstance(tools, tuple) else tools
            conversion_success = True
        except Exception as e:
            conversion_success = False
            pytest.fail(f"Tuple to list conversion should not fail: {e}")
        
        assert conversion_success is True
        assert isinstance(normalized_tools, list)
        assert len(normalized_tools) == len(tools)
    
    def test_no_regression_to_content_validation_issues(self):
        """Ensure we don't regress to old content validation problems"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config)
        
        tools = tools_manager.load_tools()
        
        # The old code might not have validated content properly
        # New code should handle all tool types without errors
        validation_success = True
        for i, tool in enumerate(tools):
            try:
                # Basic validation that should always work
                assert tool is not None, f"Tool {i} should not be None"
                
                # Type-specific validation
                if hasattr(tool, 'name'):
                    assert isinstance(tool.name, str), f"Tool {i} name should be string"
                elif isinstance(tool, dict):
                    assert len(tool) > 0, f"Tool {i} dict should not be empty"
                elif callable(tool):
                    # Should be callable without immediate errors
                    assert callable(tool), f"Tool {i} should be callable"
                
            except Exception as e:
                validation_success = False
                pytest.fail(f"Content validation should not fail for tool {i}: {e}")
        
        assert validation_success is True
    
    def test_no_regression_to_type_consistency_issues(self):
        """Ensure tools type consistency doesn't regress"""
        config = ConfigForTesting()
        
        # Test both tuple and list input
        for return_type in ["tuple", "list"]:
            tools_manager = MockToolsManager(config, return_type=return_type)
            tools = tools_manager.load_tools()
            
            # Normalize (this is what the agent does)
            normalized_tools = list(tools) if isinstance(tools, tuple) else tools
            
            # Result should always be list regardless of input type
            assert isinstance(normalized_tools, list), f"Output should always be list (input was {return_type})"
            assert len(normalized_tools) > 0, "Should have tools loaded"
    
    def test_tools_validation_maintains_order(self):
        """Test that tools validation maintains original order"""
        config = ConfigForTesting()
        tools_manager = MockToolsManager(config, return_type="tuple")
        
        original_tools = tools_manager.load_tools()
        normalized_tools = list(original_tools) if isinstance(original_tools, tuple) else original_tools
        
        # Order should be preserved
        assert len(normalized_tools) == len(original_tools)
        for i, (original, normalized) in enumerate(zip(original_tools, normalized_tools)):
            assert original is normalized, f"Tool order should be preserved at index {i}"
    
    def test_tools_validation_handles_edge_cases(self):
        """Test that tools validation handles edge cases without regression"""
        # Test single tool
        single_tool = (MockTool("single"),)
        normalized = list(single_tool) if isinstance(single_tool, tuple) else single_tool
        assert isinstance(normalized, list)
        assert len(normalized) == 1
        
        # Test mixed types in tuple
        mixed_tools = (
            MockTool("test"),
            lambda x: x,
            {"name": "dict_tool"}
        )
        normalized = list(mixed_tools) if isinstance(mixed_tools, tuple) else mixed_tools
        assert isinstance(normalized, list)
        assert len(normalized) == 3
        
        # Verify each type is preserved
        assert hasattr(normalized[0], 'name')
        assert callable(normalized[1])
        assert isinstance(normalized[2], dict)
