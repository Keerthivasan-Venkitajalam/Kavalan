"""
Property-based test for confidence-weighted conflict resolution

Feature: production-ready-browser-extension
Property 31: Confidence-Weighted Conflict Resolution

For any set of conflicting modality scores (variance > 4.0), the threat analyzer 
should apply confidence-weighted averaging where higher-confidence scores have greater influence.

Validates: Requirements 16.2
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
import numpy as np
from app.services.threat_analyzer import ThreatAnalyzer


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    audio_conf=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
    visual_conf=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
    liveness_conf=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_high_confidence_score_has_more_influence(
    audio: float,
    visual: float,
    liveness: float,
    audio_conf: float,
    visual_conf: float,
    liveness_conf: float
):
    """
    Property: When scores conflict, higher confidence scores should have more influence.
    
    If we have conflicting scores and one has much higher confidence,
    the final score should be closer to the high-confidence score.
    """
    # Ensure we have conflicting scores (variance > 4.0)
    scores = [audio, visual, liveness]
    variance = float(np.var(scores))
    assume(variance > 4.0)
    
    analyzer = ThreatAnalyzer()
    
    # Test with equal confidences first
    result_equal = analyzer.fuse_scores(
        audio, visual, liveness,
        0.5, 0.5, 0.5
    )
    
    # Now boost audio confidence significantly
    result_audio_high = analyzer.fuse_scores(
        audio, visual, liveness,
        1.0, 0.1, 0.1
    )
    
    # The result with high audio confidence should be closer to audio score
    # than the result with equal confidences
    distance_equal = abs(result_equal.final_score - audio)
    distance_high = abs(result_audio_high.final_score - audio)
    
    # High confidence should pull result closer to that modality's score
    assert distance_high <= distance_equal + 0.5, \
        f"High confidence audio should pull score closer to audio value"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_conflict_detection_threshold(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Conflict resolution should only activate when variance > 4.0.
    
    Below the threshold, standard weighted fusion should be used.
    """
    analyzer = ThreatAnalyzer()
    
    scores = [audio, visual, liveness]
    variance = float(np.var(scores))
    
    # Test with equal confidences
    result = analyzer.fuse_scores(audio, visual, liveness, 1.0, 1.0, 1.0)
    
    # Calculate expected score with standard weights
    expected_standard = (
        audio * analyzer.weights['audio'] +
        visual * analyzer.weights['visual'] +
        liveness * analyzer.weights['liveness']
    )
    
    if variance <= 4.0:
        # Should use standard weighted fusion
        assert abs(result.final_score - expected_standard) < 0.01, \
            f"Low variance ({variance}) should use standard fusion"


@given(
    high_score=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    low_score=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    high_conf=st.floats(min_value=0.8, max_value=1.0, allow_nan=False, allow_infinity=False),
    low_conf=st.floats(min_value=0.0, max_value=0.2, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_confidence_weighted_with_extreme_conflict(
    high_score: float,
    low_score: float,
    high_conf: float,
    low_conf: float
):
    """
    Property: With extreme conflicts, high confidence should dominate.
    
    When one score is high with high confidence and others are low with low confidence,
    the final score should be closer to the high-confidence score.
    """
    # Ensure we have a real conflict (variance > 4.0)
    scores = [high_score, low_score, low_score]
    variance = float(np.var(scores))
    assume(variance > 4.0)
    
    analyzer = ThreatAnalyzer()
    
    # Create extreme conflict: one high, two low
    result = analyzer.fuse_scores(
        high_score, low_score, low_score,
        high_conf, low_conf, low_conf
    )
    
    # Final score should be closer to high_score than to low_score
    distance_to_high = abs(result.final_score - high_score)
    distance_to_low = abs(result.final_score - low_score)
    
    assert distance_to_high < distance_to_low, \
        f"High confidence score should dominate in extreme conflict"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_zero_confidence_fallback(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: When all confidences are zero, should fall back to equal weighting.
    
    This is an edge case that should be handled gracefully.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(
        audio, visual, liveness,
        0.0, 0.0, 0.0
    )
    
    # Should still produce a valid score
    assert 0.0 <= result.final_score <= 10.0
    
    # With zero confidences and conflict, should approximate equal weighting
    scores = [audio, visual, liveness]
    variance = float(np.var(scores))
    
    if variance > 4.0:
        expected_equal = (audio + visual + liveness) / 3.0
        assert abs(result.final_score - expected_equal) < 0.5


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    audio_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    visual_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    liveness_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_conflict_resolution_preserves_bounds(
    audio: float,
    visual: float,
    liveness: float,
    audio_conf: float,
    visual_conf: float,
    liveness_conf: float
):
    """
    Property: Conflict resolution should never produce out-of-bounds scores.
    
    Even with confidence weighting, final score must be in [0.0, 10.0].
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(
        audio, visual, liveness,
        audio_conf, visual_conf, liveness_conf
    )
    
    assert 0.0 <= result.final_score <= 10.0, \
        f"Conflict resolution produced out-of-bounds score: {result.final_score}"


def test_conflict_resolution_with_known_values():
    """
    Unit test: Verify conflict resolution with known values.
    """
    analyzer = ThreatAnalyzer()
    
    # Create conflicting scores: audio=9.0, visual=1.0, liveness=1.0
    # Variance = 21.33 > 4.0, so conflict resolution should activate
    
    # With equal confidences, should still use base weights
    result_equal = analyzer.fuse_scores(9.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    
    # With high audio confidence, should be closer to 9.0
    result_audio_high = analyzer.fuse_scores(9.0, 1.0, 1.0, 1.0, 0.1, 0.1)
    
    # High audio confidence should pull score higher
    assert result_audio_high.final_score > result_equal.final_score


def test_no_conflict_uses_standard_fusion():
    """
    Unit test: When variance is low, standard fusion should be used.
    """
    analyzer = ThreatAnalyzer()
    
    # Similar scores: variance = 0.22 < 4.0
    result = analyzer.fuse_scores(5.0, 5.5, 4.5, 0.8, 0.9, 0.7)
    
    # Should use standard weighted fusion
    expected = (
        5.0 * analyzer.weights['audio'] +
        5.5 * analyzer.weights['visual'] +
        4.5 * analyzer.weights['liveness']
    )
    
    assert abs(result.final_score - expected) < 0.01
