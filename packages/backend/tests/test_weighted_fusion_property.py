"""
Property-based test for weighted score fusion

Feature: production-ready-browser-extension
Property 30: Weighted Score Fusion

For any set of modality scores (audio, visual, liveness), the threat analyzer 
should combine them using the configured weights (default: audio=0.45, visual=0.35, liveness=0.20).

Validates: Requirements 16.1
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
def test_weighted_fusion_formula(audio: float, visual: float, liveness: float):
    """
    Property: For any modality scores, fusion should use configured weights.
    
    The final score should equal:
    audio * 0.45 + visual * 0.35 + liveness * 0.20
    """
    analyzer = ThreatAnalyzer()
    weights = analyzer.weights
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Calculate expected score using weights
    expected = (
        audio * weights['audio'] +
        visual * weights['visual'] +
        liveness * weights['liveness']
    )
    
    # Allow small floating point tolerance
    assert abs(result.final_score - expected) < 0.01, \
        f"Expected {expected}, got {result.final_score}"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_weighted_fusion_preserves_input_scores(audio: float, visual: float, liveness: float):
    """
    Property: Fusion should preserve original modality scores in result.
    
    The result should contain the exact input scores for traceability.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Verify input scores are preserved
    assert result.audio_score == audio
    assert result.visual_score == visual
    assert result.liveness_score == liveness


@given(
    audio_weight=st.floats(min_value=0.1, max_value=0.8, allow_nan=False, allow_infinity=False),
    visual_weight=st.floats(min_value=0.1, max_value=0.8, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_custom_weights_applied_correctly(audio_weight: float, visual_weight: float):
    """
    Property: Custom weights should be applied correctly.
    
    When custom weights are provided, they should be used in fusion calculation.
    """
    # Calculate liveness weight to make sum = 1.0
    liveness_weight = 1.0 - audio_weight - visual_weight
    
    # Skip if liveness weight would be invalid
    if liveness_weight < 0.0 or liveness_weight > 1.0:
        return
    
    analyzer = ThreatAnalyzer(
        audio_weight=audio_weight,
        visual_weight=visual_weight,
        liveness_weight=liveness_weight
    )
    
    # Test with known scores
    audio, visual, liveness = 8.0, 6.0, 4.0
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    expected = (
        audio * audio_weight +
        visual * visual_weight +
        liveness * liveness_weight
    )
    
    assert abs(result.final_score - expected) < 0.01


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_weighted_fusion_monotonicity(audio: float, visual: float, liveness: float):
    """
    Property: Increasing any modality score should not decrease final score.
    
    If we increase one modality score while keeping others constant,
    the final score should increase (or stay the same if at max).
    """
    analyzer = ThreatAnalyzer()
    
    result1 = analyzer.fuse_scores(audio, visual, liveness)
    
    # Increase audio score by 1.0 (if possible)
    if audio < 10.0:
        audio_increased = min(audio + 1.0, 10.0)
        result2 = analyzer.fuse_scores(audio_increased, visual, liveness)
        assert result2.final_score >= result1.final_score, \
            "Increasing audio score should not decrease final score"
    
    # Increase visual score by 1.0 (if possible)
    if visual < 10.0:
        visual_increased = min(visual + 1.0, 10.0)
        result3 = analyzer.fuse_scores(audio, visual_increased, liveness)
        assert result3.final_score >= result1.final_score, \
            "Increasing visual score should not decrease final score"
    
    # Increase liveness score by 1.0 (if possible)
    if liveness < 10.0:
        liveness_increased = min(liveness + 1.0, 10.0)
        result4 = analyzer.fuse_scores(audio, visual, liveness_increased)
        assert result4.final_score >= result1.final_score, \
            "Increasing liveness score should not decrease final score"


def test_weighted_fusion_with_zero_scores():
    """
    Edge case: All zero scores should produce zero final score.
    """
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(0.0, 0.0, 0.0)
    
    assert result.final_score == 0.0
    assert result.threat_level == 'low'
    assert result.is_alert is False


def test_weighted_fusion_with_max_scores():
    """
    Edge case: All maximum scores should produce maximum final score.
    """
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(10.0, 10.0, 10.0)
    
    assert result.final_score == 10.0
    assert result.threat_level == 'critical'
    assert result.is_alert is True
