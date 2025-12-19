"""
Property-based tests for Fusion Engine
Tests Properties 1, 2, and 3 related to score fusion
"""

import pytest
from hypothesis import given, strategies as st, settings
from modules.fusion import FusionEngine, FusionResult

class TestFusionProperties:
    """Property-based tests for fusion engine"""
    
    def setup_method(self):
        """Set up fusion engine for each test"""
        self.fusion_engine = FusionEngine()
    
    @given(
        visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_score_range_invariant(self, visual, liveness, audio):
        """
        **Feature: kavalan-lite, Property 1: Score Range Invariant**
        
        For any input scores in range [0, 10], the fusion engine SHALL
        return a final score in range [0, 10].
        """
        result = self.fusion_engine.fuse_scores(visual, liveness, audio)
        
        # Property 1: Final score must be in valid range
        assert 0.0 <= result.final_score <= 10.0, \
            f"Final score out of range: {result.final_score}"
        
        # Also verify individual scores are preserved in valid range
        assert 0.0 <= result.visual_score <= 10.0, \
            f"Visual score out of range: {result.visual_score}"
        assert 0.0 <= result.liveness_score <= 10.0, \
            f"Liveness score out of range: {result.liveness_score}"
        assert 0.0 <= result.audio_score <= 10.0, \
            f"Audio score out of range: {result.audio_score}"
    
    @given(
        visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_fusion_calculation_correctness(self, visual, liveness, audio):
        """
        **Feature: kavalan-lite, Property 2: Fusion Calculation Correctness**
        
        For any three valid scores, the fusion engine SHALL compute the final
        score as: final = visual * 0.4 + liveness * 0.3 + audio * 0.3
        """
        result = self.fusion_engine.fuse_scores(visual, liveness, audio)
        
        # Calculate expected score manually
        expected_score = (
            visual * self.fusion_engine.visual_weight +
            liveness * self.fusion_engine.liveness_weight +
            audio * self.fusion_engine.audio_weight
        )
        
        # Clamp expected score to valid range (same as fusion engine does)
        expected_score = max(0.0, min(10.0, expected_score))
        
        # Property 2: Fusion calculation must be correct (within floating point tolerance)
        assert abs(result.final_score - expected_score) < 1e-10, \
            f"Fusion calculation incorrect: got {result.final_score}, expected {expected_score}"
    
    @given(
        score=st.floats(min_value=0.0, max_value=15.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=30)
    def test_alert_threshold_consistency(self, score):
        """
        **Feature: kavalan-lite, Property 3: Alert Threshold Consistency**
        
        For any score > 8.0, is_alert SHALL be True.
        For any score <= 8.0, is_alert SHALL be False.
        """
        # Create a dummy result to test alert logic
        # We'll use the check_alert method directly
        is_alert, message = self.fusion_engine.check_alert(score)
        
        # Property 3: Alert threshold consistency
        if score > self.fusion_engine.alert_threshold:
            assert is_alert == True, \
                f"Score {score} > {self.fusion_engine.alert_threshold} should trigger alert"
            assert "ALERT" in message.upper(), \
                f"Alert message should contain 'ALERT': {message}"
        else:
            assert is_alert == False, \
                f"Score {score} <= {self.fusion_engine.alert_threshold} should not trigger alert"
    
    @given(
        visual=st.floats(min_value=-5.0, max_value=15.0, allow_nan=False, allow_infinity=False),
        liveness=st.floats(min_value=-5.0, max_value=15.0, allow_nan=False, allow_infinity=False),
        audio=st.floats(min_value=-5.0, max_value=15.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=30)
    def test_score_clamping_property(self, visual, liveness, audio):
        """
        **Feature: kavalan-lite, Property 1: Score Range Invariant (Extended)**
        
        For any input scores (even outside [0, 10]), the fusion engine SHALL
        clamp them to [0, 10] and return a valid final score.
        """
        result = self.fusion_engine.fuse_scores(visual, liveness, audio)
        
        # Property: All scores should be clamped to valid range
        assert 0.0 <= result.final_score <= 10.0, \
            f"Final score not clamped: {result.final_score}"
        assert 0.0 <= result.visual_score <= 10.0, \
            f"Visual score not clamped: {result.visual_score}"
        assert 0.0 <= result.liveness_score <= 10.0, \
            f"Liveness score not clamped: {result.liveness_score}"
        assert 0.0 <= result.audio_score <= 10.0, \
            f"Audio score not clamped: {result.audio_score}"
    
    def test_weights_sum_to_one_property(self):
        """
        **Feature: kavalan-lite, Property 2: Fusion Calculation Correctness (Extended)**
        
        The fusion weights should sum to approximately 1.0 for proper averaging.
        """
        total_weight = (
            self.fusion_engine.visual_weight +
            self.fusion_engine.liveness_weight +
            self.fusion_engine.audio_weight
        )
        
        # Property: Weights should sum to 1.0 (within tolerance)
        assert abs(total_weight - 1.0) < 1e-10, \
            f"Weights don't sum to 1.0: {total_weight}"
    
    def test_boundary_values_property(self):
        """
        **Feature: kavalan-lite, Property 1, 2, 3: Boundary Value Testing**
        
        Test specific boundary values that are critical for the system.
        """
        # Test minimum values
        result_min = self.fusion_engine.fuse_scores(0.0, 0.0, 0.0)
        assert result_min.final_score == 0.0, f"Min fusion should be 0.0: {result_min.final_score}"
        assert result_min.is_alert == False, "Min score should not trigger alert"
        
        # Test maximum values
        result_max = self.fusion_engine.fuse_scores(10.0, 10.0, 10.0)
        assert result_max.final_score == 10.0, f"Max fusion should be 10.0: {result_max.final_score}"
        assert result_max.is_alert == True, "Max score should trigger alert"
        
        # Test threshold boundary
        threshold = self.fusion_engine.alert_threshold
        
        # Just below threshold
        is_alert_below, _ = self.fusion_engine.check_alert(threshold - 0.01)
        assert is_alert_below == False, f"Score {threshold - 0.01} should not trigger alert"
        
        # Just above threshold
        is_alert_above, _ = self.fusion_engine.check_alert(threshold + 0.01)
        assert is_alert_above == True, f"Score {threshold + 0.01} should trigger alert"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])