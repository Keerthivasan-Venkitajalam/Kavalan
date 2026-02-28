"""
Property-based test for graceful degradation with partial modalities

Feature: production-ready-browser-extension
Property 41: Graceful Degradation with Partial Modalities

For any analysis request where one or more modalities fail (e.g., visual analyzer unavailable),
the system should continue processing with available modalities and return a partial threat assessment.

Validates: Requirements 18.7
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.services.threat_analyzer import ThreatAnalyzer


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_partial_modalities_return_valid_assessment(audio, visual, liveness):
    """
    Property: For any combination of available/unavailable modalities (at least one available),
    the system should return a valid threat assessment.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    
    # Should not raise an exception
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    # Verify result is valid
    assert result is not None
    assert 0.0 <= result.final_score <= 10.0
    assert result.threat_level in ['low', 'moderate', 'high', 'critical']
    assert isinstance(result.is_alert, bool)
    assert isinstance(result.message, str)
    assert isinstance(result.explanation, list)
    assert 0.0 <= result.confidence <= 1.0


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_degraded_mode_flag_set_correctly(audio, visual, liveness):
    """
    Property: degraded_mode flag should be True when fewer than 3 modalities are available.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    # Count available modalities
    num_available = sum([audio is not None, visual is not None, liveness is not None])
    
    if num_available < 3:
        assert result.degraded_mode is True, "degraded_mode should be True when < 3 modalities available"
    else:
        assert result.degraded_mode is False, "degraded_mode should be False when all 3 modalities available"


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_available_modalities_list_accurate(audio, visual, liveness):
    """
    Property: available_modalities list should accurately reflect which modalities are available.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    # Verify available_modalities list
    if audio is not None:
        assert 'audio' in result.available_modalities
    else:
        assert 'audio' not in result.available_modalities
    
    if visual is not None:
        assert 'visual' in result.available_modalities
    else:
        assert 'visual' not in result.available_modalities
    
    if liveness is not None:
        assert 'liveness' in result.available_modalities
    else:
        assert 'liveness' not in result.available_modalities


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_degraded_mode_warning_in_message(audio, visual, liveness):
    """
    Property: When in degraded mode, the message should contain a degraded mode warning.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    num_available = sum([audio is not None, visual is not None, liveness is not None])
    
    if num_available < 3:
        assert 'DEGRADED MODE' in result.message, \
            "Message should contain 'DEGRADED MODE' warning when < 3 modalities available"
    else:
        assert 'DEGRADED MODE' not in result.message, \
            "Message should not contain 'DEGRADED MODE' when all modalities available"


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_degraded_mode_warning_in_explanation(audio, visual, liveness):
    """
    Property: When in degraded mode, the explanation should mention unavailable modalities.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    num_available = sum([audio is not None, visual is not None, liveness is not None])
    
    if num_available < 3:
        # Check that explanation mentions unavailable modalities
        explanation_text = ' '.join(result.explanation)
        assert 'unavailable' in explanation_text.lower() or 'WARNING' in explanation_text, \
            "Explanation should mention unavailable modalities in degraded mode"


@given(
    audio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    visual=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
    liveness=st.one_of(st.none(), st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
)
@settings(max_examples=100, deadline=None)
def test_confidence_reduced_in_degraded_mode(audio, visual, liveness):
    """
    Property: Confidence should be reduced when in degraded mode compared to full mode.
    
    With fewer modalities, we have less information, so confidence should be lower.
    """
    # Require at least one modality to be available
    assume(audio is not None or visual is not None or liveness is not None)
    
    analyzer = ThreatAnalyzer()
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=liveness)
    
    num_available = sum([audio is not None, visual is not None, liveness is not None])
    
    if num_available < 3:
        # In degraded mode, confidence should be reduced
        # The reduction factor is num_available / 3.0
        # So confidence should be <= (num_available / 3.0)
        max_expected_confidence = num_available / 3.0
        
        # Allow some tolerance for the agreement component
        assert result.confidence <= max_expected_confidence + 0.5, \
            f"Confidence {result.confidence} should be reduced in degraded mode (max ~{max_expected_confidence})"


@given(
    score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_single_modality_produces_valid_result(score):
    """
    Property: System should work with only a single modality available.
    """
    analyzer = ThreatAnalyzer()
    
    # Test with only audio
    result_audio = analyzer.fuse_scores(audio=score, visual=None, liveness=None)
    assert result_audio.degraded_mode is True
    assert result_audio.available_modalities == ['audio']
    assert 0.0 <= result_audio.final_score <= 10.0
    
    # Test with only visual
    result_visual = analyzer.fuse_scores(audio=None, visual=score, liveness=None)
    assert result_visual.degraded_mode is True
    assert result_visual.available_modalities == ['visual']
    assert 0.0 <= result_visual.final_score <= 10.0
    
    # Test with only liveness
    result_liveness = analyzer.fuse_scores(audio=None, visual=None, liveness=score)
    assert result_liveness.degraded_mode is True
    assert result_liveness.available_modalities == ['liveness']
    assert 0.0 <= result_liveness.final_score <= 10.0


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_two_modalities_produce_valid_result(audio, visual):
    """
    Property: System should work with two modalities available.
    """
    analyzer = ThreatAnalyzer()
    
    # Test with audio + visual
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=None)
    assert result.degraded_mode is True
    assert set(result.available_modalities) == {'audio', 'visual'}
    assert 0.0 <= result.final_score <= 10.0
    
    # Test with audio + liveness
    result2 = analyzer.fuse_scores(audio=audio, visual=None, liveness=visual)
    assert result2.degraded_mode is True
    assert set(result2.available_modalities) == {'audio', 'liveness'}
    assert 0.0 <= result2.final_score <= 10.0
    
    # Test with visual + liveness
    result3 = analyzer.fuse_scores(audio=None, visual=audio, liveness=visual)
    assert result3.degraded_mode is True
    assert set(result3.available_modalities) == {'visual', 'liveness'}
    assert 0.0 <= result3.final_score <= 10.0


def test_all_modalities_unavailable_raises_error():
    """
    Edge case: When all modalities are unavailable, should raise ValueError.
    """
    analyzer = ThreatAnalyzer()
    
    with pytest.raises(ValueError, match="At least one modality must be available"):
        analyzer.fuse_scores(audio=None, visual=None, liveness=None)


def test_partial_scores_preserved_in_result():
    """
    Edge case: Verify that None values are preserved in the result for unavailable modalities.
    """
    analyzer = ThreatAnalyzer()
    
    # Test with only audio available
    result = analyzer.fuse_scores(audio=8.0, visual=None, liveness=None)
    assert result.audio_score == 8.0
    assert result.visual_score is None
    assert result.liveness_score is None
    
    # Test with only visual available
    result2 = analyzer.fuse_scores(audio=None, visual=6.0, liveness=None)
    assert result2.audio_score is None
    assert result2.visual_score == 6.0
    assert result2.liveness_score is None


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_partial_fusion_weights_normalized(audio):
    """
    Property: When using partial modalities, weights should be normalized to sum to 1.0.
    
    For example, if only audio (weight 0.45) and visual (weight 0.35) are available,
    they should be renormalized to 0.45/0.80 = 0.5625 and 0.35/0.80 = 0.4375.
    """
    analyzer = ThreatAnalyzer()
    
    # Test with audio and visual only
    visual = audio  # Use same value for simplicity
    result = analyzer.fuse_scores(audio=audio, visual=visual, liveness=None)
    
    # Calculate expected normalized weights
    total_weight = analyzer.weights['audio'] + analyzer.weights['visual']
    audio_norm = analyzer.weights['audio'] / total_weight
    visual_norm = analyzer.weights['visual'] / total_weight
    
    expected_score = audio * audio_norm + visual * visual_norm
    
    # Allow small floating point tolerance
    assert abs(result.final_score - expected_score) < 0.01, \
        f"Expected {expected_score}, got {result.final_score}"


def test_degraded_mode_with_high_threat():
    """
    Integration test: Verify that high threat alerts still trigger in degraded mode.
    """
    analyzer = ThreatAnalyzer()
    
    # High audio score only
    result = analyzer.fuse_scores(audio=9.0, visual=None, liveness=None)
    
    assert result.degraded_mode is True
    assert result.final_score >= 7.0  # Should still be high
    assert result.is_alert is True
    assert result.threat_level in ['high', 'critical']
    assert 'DEGRADED MODE' in result.message


def test_degraded_mode_with_low_threat():
    """
    Integration test: Verify that low threat assessments work in degraded mode.
    """
    analyzer = ThreatAnalyzer()
    
    # Low audio score only
    result = analyzer.fuse_scores(audio=2.0, visual=None, liveness=None)
    
    assert result.degraded_mode is True
    assert result.final_score < 5.0
    assert result.is_alert is False
    assert result.threat_level in ['low', 'moderate']
    assert 'DEGRADED MODE' in result.message
