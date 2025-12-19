"""
Configuration loader module for Kavalan Lite
Handles loading JSON configuration files with fallback defaults
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Main configuration container"""
    keywords: Dict[str, list]
    thresholds: Dict[str, float]
    prompts: Dict[str, str]
    
    # Default values
    DEFAULT_KEYWORDS = {
        "authority": ["CBI", "NCB", "Police"],
        "coercion": ["Do not disconnect", "Stay on call"],
        "financial": ["Transfer money", "Verification account"],
        "crime": ["Money laundering", "Arrest warrant"]
    }
    
    DEFAULT_THRESHOLDS = {
        "alert_threshold": 8.0,
        "visual_weight": 0.4,
        "liveness_weight": 0.3,
        "audio_weight": 0.3,
        "min_blinks_per_minute": 10,
        "ear_threshold": 0.25,
        "frame_sample_interval": 2.0
    }
    
    DEFAULT_PROMPTS = {
        "uniform_analysis": "Analyze this image for fake police uniform indicators. Return JSON with score 0-10.",
        "audio_analysis": "Analyze transcript for scam indicators. Return JSON with score 0-10.",
        "liveness_check": "Check if this is a real person or deepfake. Return score 0-10."
    }

class ConfigLoader:
    """Loads configuration from JSON files with fallback defaults"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        
    def load_json_file(self, filename: str, default_value: Any) -> Any:
        """Load JSON file with fallback to default value"""
        filepath = os.path.join(self.config_dir, filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded configuration from {filepath}")
                    return data
            else:
                logger.warning(f"Configuration file {filepath} not found, using defaults")
                return default_value
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            logger.info("Using default configuration")
            return default_value
            
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            logger.info("Using default configuration")
            return default_value
    
    def load_config(self) -> Config:
        """Load all configuration files and return Config object"""
        
        # Load each configuration file with fallbacks
        keywords = self.load_json_file("scam_keywords.json", Config.DEFAULT_KEYWORDS)
        thresholds = self.load_json_file("thresholds.json", Config.DEFAULT_THRESHOLDS)
        prompts = self.load_json_file("gemini_prompts.json", Config.DEFAULT_PROMPTS)
        
        # Validate and merge with defaults
        keywords = self._merge_with_defaults(keywords, Config.DEFAULT_KEYWORDS)
        thresholds = self._merge_with_defaults(thresholds, Config.DEFAULT_THRESHOLDS)
        prompts = self._merge_with_defaults(prompts, Config.DEFAULT_PROMPTS)
        
        return Config(
            keywords=keywords,
            thresholds=thresholds,
            prompts=prompts
        )
    
    def _merge_with_defaults(self, loaded_config: Dict, defaults: Dict) -> Dict:
        """Merge loaded config with defaults, filling missing keys"""
        result = defaults.copy()
        if isinstance(loaded_config, dict):
            result.update(loaded_config)
        return result

# Global config instance
_config_loader = None
_config_instance = None

def get_config(config_dir: str = "config") -> Config:
    """Get global configuration instance (singleton pattern)"""
    global _config_loader, _config_instance
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
        
    if _config_instance is None:
        _config_instance = _config_loader.load_config()
        
    return _config_instance

def reload_config(config_dir: str = "config") -> Config:
    """Force reload configuration from files"""
    global _config_loader, _config_instance
    
    _config_loader = ConfigLoader(config_dir)
    _config_instance = _config_loader.load_config()
    
    return _config_instance