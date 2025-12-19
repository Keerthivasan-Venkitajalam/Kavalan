"""
Test Visual Analyzer functionality
"""

import pytest
import numpy as np
import cv2
from modules.video_processor import VideoProcessor
from modules.config import get_config
import os

def test_visual_analyzer_initialization():
    """Test that visual analyzer initializes correctly"""
    # Test without API key
    processor = VideoProcessor(gemini_api_key="")
    assert processor.gemini_model is None
    
    # Test with mock API key
    processor_with_key = VideoProcessor(gemini_api_key="test_key")
    # Should not crash, but may not have working model due to invalid key
    assert processor_with_key is not None

def test_frame_to_base64():
    """Test frame conversion to base64"""
    processor = VideoProcessor(gemini_api_key="")
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (500, 400), (255, 255, 255), -1)
    
    # Convert to base64
    base64_str = processor.frame_to_base64(frame)
    
    # Should return a non-empty string
    assert isinstance(base64_str, str)
    assert len(base64_str) > 0

def test_analyze_uniform_without_gemini():
    """Test uniform analysis without Gemini (should return default result)"""
    processor = VideoProcessor(gemini_api_key="")
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Analyze without Gemini
    result = processor.analyze_uniform(frame, "test prompt")
    
    # Should return default VisualResult
    assert result.score == 0.0
    assert result.uniform_detected == False
    assert result.confidence == 0.0
    assert "not available" in result.raw_analysis.lower()

def test_frame_sampling_interval():
    """Test that visual analysis respects frame sampling interval"""
    processor = VideoProcessor(gemini_api_key="", config={'frame_sample_interval': 1.0})
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Process frame multiple times quickly
    result1 = processor.process_frame(frame, "test prompt")
    result2 = processor.process_frame(frame, "test prompt")
    
    # First call should have liveness result
    assert result1[0] is not None  # LivenessResult
    
    # Second call should not trigger visual analysis (too soon)
    assert result2[1] is None  # No VisualResult due to interval

if __name__ == "__main__":
    pytest.main([__file__, "-v"])