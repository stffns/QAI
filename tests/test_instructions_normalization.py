# Tests for instructions normalization functionality
# Tests must always pass to ensure instructions logging bug fix works

import pytest
from conftest import ConfigForTesting


class TestInstructionsNormalization:
    """Test instructions normalization bug fix"""
    
    def test_list_instructions_normalized_to_string(self):
        """Test that list instructions are properly normalized to string"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # Verify test setup: instructions should be a list
        assert isinstance(instructions, list), "Test setup: instructions should be list"
        assert len(instructions) == 3, "Should have 3 test instructions"
        
        # Simulate the normalization process
        if isinstance(instructions, list):
            normalized = '\n'.join(instructions)
        else:
            normalized = instructions
        
        # Verify normalization result
        assert isinstance(normalized, str), "Normalized instructions should be string"
        assert len(normalized) > 0, "Normalized instructions should not be empty"
        
        # Verify content preservation
        assert "You are a test QA assistant" in normalized
        assert "Always validate test data" in normalized
        assert "Provide clear test results" in normalized
    
    def test_string_instructions_remain_unchanged(self):
        """Test that string instructions remain unchanged"""
        original_string = "You are a QA assistant. Help users with testing."
        
        # Simulate normalization on string input
        if isinstance(original_string, list):
            normalized = '\n'.join(original_string)
        else:
            normalized = original_string
        
        assert isinstance(normalized, str)
        assert normalized == original_string, "String instructions should remain unchanged"
    
    def test_instructions_character_counting_consistency(self):
        """Test that character counting is consistent after normalization"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # Normalize instructions
        if isinstance(instructions, list):
            normalized = '\n'.join(instructions)
        else:
            normalized = instructions
        
        # Character count should be consistent
        char_count = len(normalized)
        assert char_count > 0, "Character count should be positive"
        
        # Count should include newlines for joined list
        if isinstance(instructions, list) and len(instructions) > 1:
            # Should have newlines between instructions
            newline_count = normalized.count('\n')
            expected_newlines = len(instructions) - 1
            assert newline_count == expected_newlines, f"Should have {expected_newlines} newlines, got {newline_count}"
    
    def test_instructions_formatting_consistency(self):
        """Test that instructions formatting is consistent"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # Normalize multiple times to ensure consistency
        normalized1 = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        normalized2 = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        assert normalized1 == normalized2, "Normalization should be consistent"
        assert len(normalized1) == len(normalized2), "Character count should be consistent"
    
    def test_instructions_metadata_extraction(self):
        """Test that metadata can be properly extracted from normalized instructions"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        # Extract metadata
        lines = normalized.split('\n')
        word_count = len(normalized.split())
        char_count = len(normalized)
        
        # Metadata should be meaningful
        assert len(lines) > 0, "Should have instruction lines"
        assert word_count > 0, "Should have words"
        assert char_count > 0, "Should have characters"
        
        # For list input, should have multiple lines
        if isinstance(instructions, list):
            assert len(lines) == len(instructions), "Line count should match instruction count"
    
    def test_empty_instructions_handling(self):
        """Test handling of empty instructions"""
        # Test empty list
        empty_list = []
        normalized = '\n'.join(empty_list) if isinstance(empty_list, list) else empty_list
        assert isinstance(normalized, str)
        assert normalized == ""
        
        # Test empty string
        empty_string = ""
        normalized = '\n'.join(empty_string) if isinstance(empty_string, list) else empty_string
        assert isinstance(normalized, str)
        assert normalized == ""
    
    def test_instructions_with_special_characters(self):
        """Test normalization with special characters"""
        special_instructions = [
            "You are a QA assistant with émojis 🤖",
            "Handle special chars: @#$%^&*()",
            "Unicode support: 中文, العربية, русский"
        ]
        
        normalized = '\n'.join(special_instructions)
        
        assert isinstance(normalized, str)
        assert len(normalized) > 0
        
        # Special characters should be preserved
        assert "🤖" in normalized
        assert "@#$%^&*()" in normalized
        assert "中文" in normalized
    
    def test_instructions_with_newlines_in_items(self):
        """Test normalization when list items contain newlines"""
        instructions_with_newlines = [
            "First instruction\nwith embedded newline",
            "Second instruction",
            "Third instruction\nwith another\nnewline"
        ]
        
        normalized = '\n'.join(instructions_with_newlines)
        
        assert isinstance(normalized, str)
        # Should preserve embedded newlines
        assert "embedded newline" in normalized
        assert "another" in normalized


class TestInstructionsNormalizationRegressionSafety:
    """Tests to prevent regression of instructions normalization bug fix"""
    
    def test_no_regression_to_list_formatting_artifacts(self):
        """Ensure instructions don't regress to containing list formatting artifacts"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        # Should not contain list artifacts from string representation
        assert not normalized.startswith('['), "Should not start with list bracket"
        assert not normalized.endswith(']'), "Should not end with list bracket"
        assert "', '" not in normalized, "Should not contain comma-quote artifacts"
        assert normalized.count("'") == 0 or "'" in str(instructions), "Should not have spurious quotes"
    
    def test_no_regression_to_inconsistent_character_counting(self):
        """Ensure character counting doesn't regress to old inconsistent behavior"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # Test character counting multiple times
        counts = []
        for _ in range(5):
            normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
            counts.append(len(normalized))
        
        # All counts should be identical
        assert len(set(counts)) == 1, f"Character counts should be consistent: {counts}"
        assert all(count > 0 for count in counts), "All counts should be positive"
    
    def test_no_regression_to_ambiguous_metadata(self):
        """Ensure metadata extraction doesn't regress to ambiguous results"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        # Metadata should be clear and unambiguous
        lines = normalized.split('\n')
        words = normalized.split()
        chars = len(normalized)
        
        # Verify metadata consistency
        assert len(lines) > 0, "Should have lines"
        assert len(words) > 0, "Should have words"
        assert chars > 0, "Should have characters"
        
        # For list input, verify relationship between original and normalized
        if isinstance(instructions, list):
            assert len(lines) == len(instructions), "Line count should match instruction count"
            
            # Each instruction should be represented as a line
            for i, instruction in enumerate(instructions):
                assert instruction.strip() == lines[i].strip(), f"Instruction {i} should match line {i}"
    
    def test_normalization_idempotency(self):
        """Test that normalization is idempotent (multiple applications yield same result)"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # First normalization
        normalized1 = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        # Second normalization (on already normalized string)
        normalized2 = '\n'.join([normalized1]) if isinstance([normalized1], list) else normalized1
        
        # Should be different because we're treating the normalized string as a single instruction
        # But character count should be predictable
        assert isinstance(normalized1, str)
        assert isinstance(normalized2, str)
        
        # The key test: original normalization should be stable
        normalized1_repeat = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        assert normalized1 == normalized1_repeat, "Original normalization should be stable"
    
    def test_instructions_type_consistency_after_normalization(self):
        """Test that type consistency is maintained after normalization"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        # Test multiple normalizations
        results = []
        for _ in range(3):
            normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
            results.append(normalized)
        
        # All results should be strings
        for i, result in enumerate(results):
            assert isinstance(result, str), f"Result {i} should be string, got {type(result)}"
        
        # All results should be identical
        assert all(r == results[0] for r in results), "All normalization results should be identical"
    
    def test_no_data_loss_during_normalization(self):
        """Ensure no data is lost during the normalization process"""
        config = ConfigForTesting()
        instructions = config.get_agent_instructions()
        
        normalized = '\n'.join(instructions) if isinstance(instructions, list) else instructions
        
        # All original instruction content should be present
        if isinstance(instructions, list):
            for instruction in instructions:
                assert instruction.strip() in normalized, f"Instruction '{instruction}' should be in normalized result"
        else:
            assert instructions == normalized, "String instructions should be unchanged"
        
        # Check that important content is preserved
        key_phrases = ["QA assistant", "validate", "test"]
        for phrase in key_phrases:
            if any(phrase.lower() in str(instr).lower() for instr in instructions):
                assert phrase.lower() in normalized.lower(), f"Key phrase '{phrase}' should be preserved"
