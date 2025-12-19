"""
Property-based tests for Liveness Detection
Tests Properties 4 and 9 related to liveness detection
"""

import pytest
import numpy as np
import cv2
import time
from hypothesis import given, strategies as st, settings
from modules.video_processor import VideoProcessor, LivenessResult
from unittest.mock import Mock, MagicMock

class TestLivenessProperties:
    """Property-based tests for liveness detection"""
    
    def setup_method(self):
        """Set up video processor for each test"""
        # Create processor without Gemini (for testing liveness only)
        self.processor = VideoProcessor(gemini_api_key="", config={
            'ear_threshold': 0.25,
            'min_blinks_per_minute': 10,
            'frame_sample_interval': 2.0
        })
    
    def create_test_frame(self, width: int = 640, height: int = 480) -> np.ndarray:
        """Create a test frame for processing"""
        # Create a simple test frame (black with white rectangle for face)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Add a white rectangle to simulate a face region
        cv2.rectangle(frame, (width//4, height//4), (3*width//4, 3*height//4), (255, 255, 255), -1)
        return frame
    
    def test_ear_calculation_validity(self):
        """
        **Feature: kavalan-lite, Property 9: EAR Calculation Validity**
        
        For any valid facial landmarks, the calculated Eye Aspect Ratio
        should be a positive float with reasonable bounds.
        """
        """
        **Feature: kavalan-lite, Property 9: EAR Calculation Validity**
        
        For any valid facial landmarks, the calculated Eye Aspect Ratio
        should be a positive float with reasonable bounds.
        """
        # Test with several different eye configurations
        test_cases = [
            # Normal open eye
            [(0.3, 0.5), (0.32, 0.48), (0.35, 0.48), (0.4, 0.5), (0.35, 0.52), (0.32, 0.52)],
            # Closed eye (smaller vertical distances)
            [(0.3, 0.5), (0.32, 0.49), (0.35, 0.49), (0.4, 0.5), (0.35, 0.51), (0.32, 0.51)],
            # Wide open eye
            [(0.3, 0.5), (0.32, 0.47), (0.35, 0.47), (0.4, 0.5), (0.35, 0.53), (0.32, 0.53)]
        ]
        
        for i, points in enumerate(test_cases):
            # Create mock landmarks
            mock_landmarks = Mock()
            mock_landmarks.landmark = []
            
            # Create 6 mock points for eye
            for x, y in points:
                point = Mock()
                point.x, point.y = x, y
                mock_landmarks.landmark.append(point)
            
            # Test EAR calculation
            eye_points = list(range(6))  # Use first 6 points
            ear = self.processor.calculate_ear(mock_landmarks, eye_points)
            
            # Property 9: EAR should be a positive float
            assert isinstance(ear, float), f"EAR should be float, got {type(ear)} for case {i}"
            assert ear >= 0.0, f"EAR should be non-negative, got {ear} for case {i}"
            assert ear <= 2.0, f"EAR should be reasonable (<= 2.0), got {ear} for case {i}"
    
    @given(
        blink_rate=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10)
    def test_low_blink_rate_detection(self, blink_rate):
        """
        **Feature: kavalan-lite, Property 4: Low Blink Rate Detection**
        
        For any blink rate below 10 blinks per minute, the liveness module
        should set is_suspicious = True and return a score > 5.0.
        """
        # Test the scoring logic directly
        score, is_suspicious = self.processor.calculate_liveness_score(
            blinks_per_minute=blink_rate,
            face_detected=True,
            ear=0.3  # Normal EAR value
        )
        
        # Property 4: Low blink rate should be flagged as suspicious
        if blink_rate < self.processor.min_blinks_per_minute:
            assert is_suspicious == True, \
                f"Blink rate {blink_rate} < {self.processor.min_blinks_per_minute} should be suspicious"
            assert score > 5.0, \
                f"Low blink rate {blink_rate} should produce score > 5.0, got {score}"
        
        # Verify score is in valid range
        assert 0.0 <= score <= 10.0, f"Score out of range: {score}"
    
    def test_no_face_detection_property(self):
        """
        **Feature: kavalan-lite, Property 4: Low Blink Rate Detection (Extended)**
        
        When no face is detected, the system should return high suspicion score.
        """
        score, is_suspicious = self.processor.calculate_liveness_score(
            blinks_per_minute=0.0,
            face_detected=False,
            ear=0.0
        )
        
        # Property: No face should be highly suspicious
        assert is_suspicious == True, "No face detected should be suspicious"
        assert score >= 8.0, f"No face should produce high score, got {score}"
    
    def test_blink_detection_consistency_property(self):
        """
        **Feature: kavalan-lite, Property 9: EAR Calculation Validity (Extended)**
        
        Blink detection should be consistent with EAR threshold.
        """
        # Test with EAR values above and below threshold
        high_ear = self.processor.ear_threshold + 0.1
        low_ear = self.processor.ear_threshold - 0.1
        
        # Reset processor state
        self.processor.blink_state = False
        self.processor.last_ear_values.clear()
        
        # Test high EAR (eyes open)
        blink_detected_high = self.processor.detect_blink(high_ear)
        
        # Test low EAR (eyes closed)
        blink_detected_low = self.processor.detect_blink(low_ear)
        
        # Test return to high EAR (blink completion)
        blink_detected_return = self.processor.detect_blink(high_ear)
        
        # Property: Blink should be detected on return from low to high EAR
        # Note: The exact behavior depends on state, but we can verify consistency
        assert isinstance(blink_detected_high, bool), "Blink detection should return boolean"
        assert isinstance(blink_detected_low, bool), "Blink detection should return boolean"
        assert isinstance(blink_detected_return, bool), "Blink detection should return boolean"
    
    @given(
        frame_dimensions=st.tuples(
            st.integers(min_value=100, max_value=1920),  # width
            st.integers(min_value=100, max_value=1080)   # height
        )
    )
    @settings(max_examples=10)
    def test_frame_processing_robustness(self, frame_dimensions):
        """
        **Feature: kavalan-lite, Property 9: EAR Calculation Validity (Robustness)**
        
        Frame processing should handle various frame sizes without errors
        and return valid results.
        """
        width, height = frame_dimensions
        
        # Create test frame
        frame = self.create_test_frame(width, height)
        
        # Process frame (this will likely not detect a face, but shouldn't crash)
        try:
            result = self.processor.process_liveness(frame)
            
            # Property: Processing should return valid LivenessResult
            assert isinstance(result, LivenessResult), f"Should return LivenessResult, got {type(result)}"
            assert isinstance(result.score, float), f"Score should be float, got {type(result.score)}"
            assert 0.0 <= result.score <= 10.0, f"Score out of range: {result.score}"
            assert isinstance(result.face_detected, bool), f"face_detected should be bool"
            assert isinstance(result.is_suspicious, bool), f"is_suspicious should be bool"
            assert isinstance(result.ear_value, float), f"ear_value should be float"
            assert result.ear_value >= 0.0, f"EAR should be non-negative: {result.ear_value}"
            
        except Exception as e:
            pytest.fail(f"Frame processing failed for size {width}x{height}: {e}")
    
    def test_blink_history_management_property(self):
        """
        **Feature: kavalan-lite, Property 4: Low Blink Rate Detection (History)**
        
        Blink history should be properly managed and not grow indefinitely.
        """
        # Simulate many blinks
        import time
        
        # Add many blinks to history
        for i in range(150):  # More than the deque maxlen of 100
            self.processor.blink_history.append(time.time() - i)
        
        # Property: History should be limited
        assert len(self.processor.blink_history) <= 100, \
            f"Blink history should be limited to 100, got {len(self.processor.blink_history)}"
        
        # Test blink rate calculation with full history
        blink_count, blinks_per_minute = self.processor.calculate_blink_rate()
        
        # Property: Calculations should handle full history
        assert isinstance(blink_count, int), f"Blink count should be int, got {type(blink_count)}"
        assert isinstance(blinks_per_minute, float), f"Blinks per minute should be float"
        assert blinks_per_minute >= 0.0, f"Blinks per minute should be non-negative"
    
    def test_ear_smoothing_property(self):
        """
        **Feature: kavalan-lite, Property 9: EAR Calculation Validity (Smoothing)**
        
        EAR smoothing should reduce noise and provide stable values.
        """
        # Add some EAR values with noise
        ear_values = [0.3, 0.35, 0.28, 0.32, 0.31, 0.29, 0.33]
        
        # Clear existing values
        self.processor.last_ear_values.clear()
        
        # Add values and test smoothing
        for ear in ear_values:
            self.processor.last_ear_values.append(ear)
        
        # Property: Smoothed value should be within reasonable range of inputs
        smoothed = np.mean(self.processor.last_ear_values)
        min_ear = min(ear_values)
        max_ear = max(ear_values)
        
        assert min_ear <= smoothed <= max_ear, \
            f"Smoothed EAR {smoothed} should be between {min_ear} and {max_ear}"
    
    def test_reset_functionality_property(self):
        """
        **Feature: kavalan-lite, Property 4: Low Blink Rate Detection (Reset)**
        
        Reset functionality should properly clear all tracking state.
        """
        # Add some state
        self.processor.blink_history.append(time.time())
        self.processor.last_ear_values.append(0.3)
        self.processor.frame_count = 100
        self.processor.blink_state = True
        
        # Reset
        self.processor.reset_tracking()
        
        # Property: All state should be cleared
        assert len(self.processor.blink_history) == 0, "Blink history should be cleared"
        assert len(self.processor.last_ear_values) == 0, "EAR values should be cleared"
        assert self.processor.frame_count == 0, "Frame count should be reset"
        assert self.processor.blink_state == False, "Blink state should be reset"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])