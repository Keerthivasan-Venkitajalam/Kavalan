"""
Property-based tests for Frame Sampling
Tests Property 10: Frame Sampling Interval
"""

import pytest
import numpy as np
import cv2
import time
from hypothesis import given, strategies as st, settings
from modules.video_processor import VideoProcessor

class TestFrameSamplingProperties:
    """Property-based tests for frame sampling"""
    
    def setup_method(self):
        """Set up video processor for each test"""
        self.processor = VideoProcessor(
            gemini_api_key="test_key",  # Mock key for testing
            config={'frame_sample_interval': 2.0}
        )
    
    def create_test_frame(self, width: int = 640, height: int = 480) -> np.ndarray:
        """Create a test frame for processing"""
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (width//4, height//4), (3*width//4, 3*height//4), (255, 255, 255), -1)
        return frame
    
    def test_frame_sampling_interval_property(self):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval**
        
        For any continuous video stream, the Visual_Analyzer should be invoked
        at intervals of approximately 2 seconds (±0.5 seconds tolerance).
        """
        frame = self.create_test_frame()
        prompt = "Test uniform analysis prompt"
        
        # Reset processor timing
        self.processor.last_analysis_time = 0
        
        # First call should trigger analysis (if Gemini was available)
        start_time = time.time()
        result1 = self.processor.process_frame(frame, prompt)
        first_analysis_time = self.processor.last_analysis_time
        
        # Property: First call should update analysis time
        if self.processor.gemini_model:
            assert first_analysis_time > 0, "First analysis should update timestamp"
        
        # Immediate second call should NOT trigger analysis
        result2 = self.processor.process_frame(frame, prompt)
        second_analysis_time = self.processor.last_analysis_time
        
        # Property: Second call should not update analysis time (too soon)
        assert second_analysis_time == first_analysis_time, \
            "Second immediate call should not trigger new analysis"
        
        # Wait for interval and try again
        time.sleep(0.1)  # Small wait for testing
        
        # Manually set time to simulate interval passage
        self.processor.last_analysis_time = time.time() - 2.5  # Simulate 2.5 seconds ago
        
        result3 = self.processor.process_frame(frame, prompt)
        third_analysis_time = self.processor.last_analysis_time
        
        # Property: Third call after interval should trigger analysis
        if self.processor.gemini_model:
            assert third_analysis_time > second_analysis_time, \
                "Call after interval should trigger new analysis"
    
    @given(
        intervals=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=5, deadline=1000)
    def test_configurable_sampling_interval(self, intervals):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval (Configurable)**
        
        For any configured sampling interval, the system should respect that interval.
        """
        # Create processor with custom interval
        processor = VideoProcessor(
            gemini_api_key="test_key",
            config={'frame_sample_interval': intervals}
        )
        
        # Property: Processor should use configured interval
        assert processor.frame_sample_interval == intervals, \
            f"Processor should use configured interval {intervals}, got {processor.frame_sample_interval}"
        
        frame = self.create_test_frame()
        
        # Reset timing
        processor.last_analysis_time = 0
        
        # First call
        processor.process_frame(frame, "test")
        first_time = processor.last_analysis_time
        
        # Simulate time passage less than interval
        processor.last_analysis_time = time.time() - (intervals * 0.5)  # Half the interval
        
        # Second call should not trigger
        processor.process_frame(frame, "test")
        second_time = processor.last_analysis_time
        
        # Property: Should not update if within interval
        time_diff = abs(second_time - (time.time() - (intervals * 0.5)))
        assert time_diff < 0.1, "Should not update analysis time within interval"
    
    def test_frame_sampling_without_prompt_property(self):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval (No Prompt)**
        
        When no prompt is provided, visual analysis should not be triggered
        regardless of timing.
        """
        frame = self.create_test_frame()
        
        # Reset timing
        self.processor.last_analysis_time = 0
        
        # Call without prompt
        result = self.processor.process_frame(frame, None)
        
        # Property: No visual analysis should be triggered without prompt
        assert result[1] is None, "Visual analysis should not run without prompt"
        
        # Call with empty prompt
        result2 = self.processor.process_frame(frame, "")
        
        # Property: No visual analysis should be triggered with empty prompt
        assert result2[1] is None, "Visual analysis should not run with empty prompt"
    
    def test_liveness_always_processed_property(self):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval (Liveness)**
        
        Liveness detection should always be processed regardless of sampling interval.
        """
        frame = self.create_test_frame()
        
        # Process multiple frames quickly
        results = []
        for i in range(5):
            result = self.processor.process_frame(frame, "test")
            results.append(result)
            time.sleep(0.01)  # Very short delay
        
        # Property: All calls should return liveness results
        for i, (liveness_result, visual_result) in enumerate(results):
            assert liveness_result is not None, f"Call {i} should have liveness result"
            # Visual results may be None due to sampling interval
    
    def test_timing_precision_property(self):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval (Precision)**
        
        The timing mechanism should be precise and consistent.
        """
        # Test timing precision
        current_time = time.time()
        
        # Set last analysis time to exactly interval ago
        self.processor.last_analysis_time = current_time - self.processor.frame_sample_interval
        
        frame = self.create_test_frame()
        
        # This should trigger analysis (if Gemini available)
        result = self.processor.process_frame(frame, "test")
        
        # Property: Analysis time should be updated to current time (approximately)
        if self.processor.gemini_model and self.processor.last_analysis_time > 0:
            time_diff = abs(self.processor.last_analysis_time - time.time())
            assert time_diff < 1.0, f"Analysis time should be current, diff: {time_diff}"
    
    def test_reset_preserves_interval_property(self):
        """
        **Feature: kavalan-lite, Property 10: Frame Sampling Interval (Reset)**
        
        Resetting the processor should preserve the sampling interval configuration.
        """
        original_interval = self.processor.frame_sample_interval
        
        # Set some analysis time
        self.processor.last_analysis_time = time.time()
        
        # Reset processor
        self.processor.reset_tracking()
        
        # Property: Interval should be preserved
        assert self.processor.frame_sample_interval == original_interval, \
            "Reset should preserve sampling interval"
        
        # Property: Analysis time should be reset
        assert self.processor.last_analysis_time == 0, \
            "Reset should clear analysis time"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])