# Tests for configuration validation contract
# Tests must always pass to ensure exception-based validation works

import pytest
from conftest import ConfigForTesting


class TestConfigValidationContract:
    """Test the improved exception-based configuration validation contract"""
    
    def test_valid_config_passes_validation(self):
        """Test that valid configuration passes validation without exceptions"""
        config = ConfigForTesting(should_fail=False)
        
        # Should complete without raising any exception
        try:
            config.validate_config()
            validation_passed = True
        except Exception as e:
            validation_passed = False
            pytest.fail(f"Valid config should not raise exception: {e}")
        
        assert validation_passed is True
    
    def test_invalid_config_raises_value_error(self):
        """Test that invalid config raises ValueError"""
        config = ConfigForTesting(should_fail=True, fail_type="value")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate_config()
        
        assert "Test configuration value error" in str(exc_info.value)
    
    def test_missing_key_config_raises_key_error(self):
        """Test that missing key config raises KeyError"""
        config = ConfigForTesting(should_fail=True, fail_type="key")
        
        with pytest.raises(KeyError) as exc_info:
            config.validate_config()
        
        assert "Missing test configuration key" in str(exc_info.value)
    
    def test_generic_config_error_raises_exception(self):
        """Test that generic config error raises Exception"""
        config = ConfigForTesting(should_fail=True, fail_type="generic")
        
        with pytest.raises(Exception) as exc_info:
            config.validate_config()
        
        assert "Generic test error" in str(exc_info.value)
    
    def test_validation_contract_consistency(self):
        """Test that validation contract is consistent across calls"""
        config = ConfigForTesting(should_fail=False)
        
        # Should consistently not raise exceptions
        for _ in range(5):
            try:
                config.validate_config()
            except Exception as e:
                pytest.fail(f"Validation should be consistent: {e}")
    
    def test_config_provides_all_required_methods(self):
        """Test that configuration provides all required methods"""
        config = ConfigForTesting()
        
        # All these methods should exist and be callable
        assert hasattr(config, 'validate_config')
        assert callable(config.validate_config)
        
        assert hasattr(config, 'get_interface_config')
        assert callable(config.get_interface_config)
        
        assert hasattr(config, 'get_agent_instructions')
        assert callable(config.get_agent_instructions)
        
        assert hasattr(config, 'get_model_config')
        assert callable(config.get_model_config)
        
        assert hasattr(config, 'get_tools_config')
        assert callable(config.get_tools_config)
        
        assert hasattr(config, 'get_storage_config')
        assert callable(config.get_storage_config)
    
    def test_config_methods_return_expected_types(self):
        """Test that config methods return expected data types"""
        config = ConfigForTesting()
        
        # Validate config should not return anything (void)
        result = config.validate_config()
        assert result is None
        
        # Interface config should return dict
        interface_config = config.get_interface_config()
        assert isinstance(interface_config, dict)
        assert 'show_tool_calls' in interface_config
        assert 'enable_markdown' in interface_config
        
        # Agent instructions can be string or list
        instructions = config.get_agent_instructions()
        assert isinstance(instructions, (str, list))
        
        # Model config should return dict
        model_config = config.get_model_config()
        assert isinstance(model_config, dict)
        assert 'id' in model_config  # Updated: use 'id' instead of 'name' for Pydantic models
        
        # Tools config should return dict
        tools_config = config.get_tools_config()
        assert isinstance(tools_config, dict)
        assert 'enabled' in tools_config
        
        # Storage config should return dict
        storage_config = config.get_storage_config()
        assert isinstance(storage_config, dict)
    
    def test_validation_exception_details(self):
        """Test that validation exceptions provide meaningful details"""
        test_cases = [
            ("value", ValueError, "value error"),
            ("key", KeyError, "configuration key"),
            ("generic", Exception, "test error")
        ]
        
        for fail_type, expected_exception, expected_message_part in test_cases:
            config = ConfigForTesting(should_fail=True, fail_type=fail_type)
            
            with pytest.raises(expected_exception) as exc_info:
                config.validate_config()
            
            error_message = str(exc_info.value).lower()
            assert expected_message_part in error_message
    
    def test_config_validation_contract_regression_safety(self):
        """Ensure the validation contract doesn't regress to boolean returns"""
        config = ConfigForTesting(should_fail=True, fail_type="value")
        
        # The old contract might have returned False for invalid config
        # The new contract should raise exceptions, never return boolean
        try:
            result = config.validate_config()
            # If we get here without exception, check that it's not boolean
            if isinstance(result, bool):
                pytest.fail("validate_config() should not return boolean (old contract)")
            if result is not None:
                pytest.fail(f"validate_config() should raise exception, not return: {result}")
        except Exception:
            # This is the expected behavior for the new contract
            pass


class TestConfigDataIntegrity:
    """Test that configuration data integrity is maintained"""
    
    def test_config_data_consistency(self):
        """Test that config data remains consistent"""
        config = ConfigForTesting()
        
        # Get data multiple times and ensure consistency
        interface1 = config.get_interface_config()
        interface2 = config.get_interface_config()
        assert interface1 == interface2
        
        model1 = config.get_model_config()
        model2 = config.get_model_config()
        assert model1 == model2
        
        tools1 = config.get_tools_config()
        tools2 = config.get_tools_config()
        assert tools1 == tools2
    
    def test_config_instruction_format(self):
        """Test that instructions are properly formatted"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        if isinstance(instructions, list):
            # List should contain valid strings
            assert len(instructions) > 0
            for instruction in instructions:
                assert isinstance(instruction, str)
                assert len(instruction.strip()) > 0
        else:
            # String should be non-empty
            assert isinstance(instructions, str)
            assert len(instructions.strip()) > 0
    
    def test_config_model_settings(self):
        """Test that model configuration contains required settings"""
        config = ConfigForTesting()
        model_config = config.get_model_config()
        
        # Essential model settings should be present
        assert 'id' in model_config  # Updated: use 'id' instead of 'name' for Pydantic models
        assert isinstance(model_config['id'], str)
        assert len(model_config['id']) > 0
        
        # Optional but common settings
        if 'temperature' in model_config:
            assert isinstance(model_config['temperature'], (int, float))
            assert 0 <= model_config['temperature'] <= 2
        
        if 'max_tokens' in model_config:
            if model_config['max_tokens'] is not None:  # Only validate if not None
                assert isinstance(model_config['max_tokens'], int)
                assert model_config['max_tokens'] > 0
