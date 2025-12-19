"""
Property-based tests for configuration loading
Tests Property 8: Configuration Loading Round-Trip
"""

import pytest
import json
import os
import tempfile
import shutil
from hypothesis import given, strategies as st, settings, HealthCheck
from modules.config import ConfigLoader, Config

class TestConfigurationProperties:
    """Property-based tests for configuration loading"""
    
    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_loader = ConfigLoader(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    @given(
        keywords=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.lists(st.text(min_size=1, max_size=15), min_size=1, max_size=3),
            min_size=1, max_size=2
        )
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10)
    def test_keywords_round_trip(self, keywords):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any valid keywords dictionary, saving to JSON and loading back
        should preserve all key-value pairs exactly.
        """
        # Save keywords to file
        keywords_file = os.path.join(self.temp_dir, "scam_keywords.json")
        with open(keywords_file, 'w') as f:
            json.dump(keywords, f)
        
        # Load back using ConfigLoader
        loaded_keywords = self.config_loader.load_json_file("scam_keywords.json", {})
        
        # Property: Round-trip preservation
        assert loaded_keywords == keywords, f"Keywords not preserved: {loaded_keywords} != {keywords}"
    
    @given(
        thresholds=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            min_size=1, max_size=3
        )
    )
    @settings(max_examples=10)
    def test_thresholds_round_trip(self, thresholds):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any valid thresholds dictionary, saving to JSON and loading back
        should preserve all numeric values exactly.
        """
        # Save thresholds to file
        thresholds_file = os.path.join(self.temp_dir, "thresholds.json")
        with open(thresholds_file, 'w') as f:
            json.dump(thresholds, f)
        
        # Load back using ConfigLoader
        loaded_thresholds = self.config_loader.load_json_file("thresholds.json", {})
        
        # Property: Round-trip preservation with float tolerance
        assert loaded_thresholds == thresholds, f"Thresholds not preserved: {loaded_thresholds} != {thresholds}"
    
    @given(
        prompts=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.text(min_size=1, max_size=50),
            min_size=1, max_size=2
        )
    )
    @settings(max_examples=10)
    def test_prompts_round_trip(self, prompts):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any valid prompts dictionary, saving to JSON and loading back
        should preserve all string values exactly.
        """
        # Save prompts to file
        prompts_file = os.path.join(self.temp_dir, "gemini_prompts.json")
        with open(prompts_file, 'w') as f:
            json.dump(prompts, f)
        
        # Load back using ConfigLoader
        loaded_prompts = self.config_loader.load_json_file("gemini_prompts.json", {})
        
        # Property: Round-trip preservation
        assert loaded_prompts == prompts, f"Prompts not preserved: {loaded_prompts} != {prompts}"
    
    def test_missing_file_fallback_property(self):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any missing configuration file, the loader should return
        the provided default value exactly.
        """
        default_value = {"test": "default"}
        
        # Try to load non-existent file
        loaded_value = self.config_loader.load_json_file("nonexistent.json", default_value)
        
        # Property: Default fallback preservation
        assert loaded_value == default_value, f"Default not preserved: {loaded_value} != {default_value}"
    
    def test_invalid_json_fallback_property(self):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any file with invalid JSON, the loader should return
        the provided default value exactly.
        """
        default_value = {"test": "default"}
        
        # Create file with invalid JSON
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Try to load invalid file
        loaded_value = self.config_loader.load_json_file("invalid.json", default_value)
        
        # Property: Default fallback preservation
        assert loaded_value == default_value, f"Default not preserved: {loaded_value} != {default_value}"
    
    def test_config_object_consistency_property(self):
        """
        **Feature: kavalan-lite, Property 8: Configuration Loading Round-Trip**
        
        For any Config object created by ConfigLoader, all required
        attributes should be present and of correct types.
        """
        # Load config (will use defaults since no files exist)
        config = self.config_loader.load_config()
        
        # Property: Config object structure consistency
        assert isinstance(config, Config), f"Config is not Config instance: {type(config)}"
        assert isinstance(config.keywords, dict), f"Keywords not dict: {type(config.keywords)}"
        assert isinstance(config.thresholds, dict), f"Thresholds not dict: {type(config.thresholds)}"
        assert isinstance(config.prompts, dict), f"Prompts not dict: {type(config.prompts)}"
        
        # Property: Required keys present
        assert len(config.keywords) > 0, "Keywords dictionary is empty"
        assert len(config.thresholds) > 0, "Thresholds dictionary is empty"
        assert len(config.prompts) > 0, "Prompts dictionary is empty"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])