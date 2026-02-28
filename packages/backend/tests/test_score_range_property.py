"""
Property-based test for unified score range constraint

Feature: production-ready-browser-extension
Property 32: Unified Score Range Constraint

For any fused threat assessment, the final unified threat score must be in the range [0.0, 10.0].

Validates: Requirements 16.3
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.threat_analyzer import ThreatAnalyzer


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_unified_score_always_in_range(audio: float, visual: float, liveness: float):
    """
    Property: For any valid modality scores, the unified score must be in [0.0, 10.0].
    
    This is a critical safety property - the final score must never exceed bounds.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    assert 0.0 <= result.final_score <= 10.0, \
        f"Final score {result.final_score} is out of range [0.0, 10.0]"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    audio_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    visual_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    liveness_conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_unified_score_with_confidence_in_range(
    audio: float,
    visual: float,
    liveness: float,
    audio_conf: float,
    visual_conf: float,
    liveness_conf: float
):
    """
    Property: Even with varying confidence scores, final score must be in [0.0, 10.0].
    
    Confidence values should not cause the final score to exceed bounds.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(
        audio, visual, liveness,
        audio_conf, visual_conf, liveness_conf
    )
    
    assert 0.0 <= result.final_score <= 10.0, \
        f"Final score {result.final_score} is out of range [0.0, 10.0]"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_confidence_score_always_in_range(audio: float, visual: float, liveness: float):
    """
    Property: The confidence score must always be in [0.0, 1.0].
    
    Confidence is a probability-like value and must be bounded.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    assert 0.0 <= result.confidence <= 1.0, \
        f"Confidence {result.confidence} is out of range [0.0, 1.0]"


@given(
    audio_weight=st.floats(min_value=0.1, max_value=0.8, allow_nan=False, allow_infinity=False),
    visual_weight=st.floats(min_value=0.1, max_value=0.8, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_score_range_with_custom_weights(audio_weight: float, visual_weight: float):
    """
    Property: Custom weights should not cause scores to exceed [0.0, 10.0].
    
    Even with different weight configurations, bounds must be maintained.
    """
    liveness_weight = 1.0 - audio_weight - visual_weight
    
    # Skip if liveness weight would be invalid
    if liveness_weight < 0.0 or liveness_weight > 1.0:
        return
    
    analyzer = ThreatAnalyzer(
        audio_weight=audio_weight,
        visual_weight=visual_weight,
        liveness_weight=liveness_weight
    )
    
    # Test with extreme scores
    result1 = analyzer.fuse_scores(10.0, 10.0, 10.0)
    assert 0.0 <= result1.final_score <= 10.0
    
    result2 = analyzer.fuse_scores(0.0, 0.0, 0.0)
    assert 0.0 <= result2.final_score <= 10.0
    
    result3 = analyzer.fuse_scores(10.0, 0.0, 5.0)
    assert 0.0 <= result3.final_score <= 10.0


def test_score_range_boundary_values():
    """
    Edge case: Test exact boundary values.
    """
    analyzer = ThreatAnalyzer()
    
    # Minimum boundary
    result_min = analyzer.fuse_scores(0.0, 0.0, 0.0)
    assert result_min.final_score == 0.0
    
    # Maximum boundary
    result_max = analyzer.fuse_scores(10.0, 10.0, 10.0)
    assert result_max.final_score == 10.0
    
    # Mixed boundaries
    result_mixed = analyzer.fuse_scores(10.0, 0.0, 10.0)
    assert 0.0 <= result_mixed.final_score <= 10.0


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_threat_level_consistency_with_score(audio: float, visual: float, liveness: float):
    """
    Property: Threat level should be consistent with final score.
    
    The threat level categorization should match the score thresholds.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Verify threat level matches score
    if result.final_score >= 8.5:
        assert result.threat_level == 'critical'
    elif result.final_score >= 7.0:
        assert result.threat_level == 'high'
    elif result.final_score >= 5.0:
        assert result.threat_level == 'moderate'
    else:
        assert result.threat_level == 'low'


def test_invalid_score_raises_error():
    """
    Edge case: Invalid input scores should raise ValueError.
    """
    analyzer = ThreatAnalyzer()
    
    # Score below minimum
    with pytest.raises(ValueError, match="audio score must be in"):
        analyzer.fuse_scores(-1.0, 5.0, 5.0)
    
    # Score above maximum
    with pytest.raises(ValueError, match="visual score must be in"):
        analyzer.fuse_scores(5.0, 11.0, 5.0)
    
    # Invalid confidence
    with pytest.raises(ValueError, match="audio_confidence must be in"):
        analyzer.fuse_scores(5.0, 5.0, 5.0, audio_confidence=1.5)
