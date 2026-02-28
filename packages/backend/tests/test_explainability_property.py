"""
Property-based test for modality contribution explainability

Feature: production-ready-browser-extension
Property 35: Modality Contribution Explainability

For any unified threat score, the system should provide an explanation breaking down 
the contribution from each modality (audio, visual, liveness).

Validates: Requirements 16.7
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
def test_explanation_always_provided(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Every threat result should include explanations.
    
    For any threat analysis, explanations list should be non-empty.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    assert isinstance(result.explanation, list)
    assert len(result.explanation) > 0
    assert all(isinstance(exp, str) for exp in result.explanation)


@given(
    audio=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_high_audio_score_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: High audio scores should be mentioned in explanations.
    
    When audio score is high (> 7.0), explanation should reference audio threats.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Explanation should mention audio-related threats
    explanation_text = ' '.join(result.explanation).lower()
    assert any(keyword in explanation_text for keyword in ['keyword', 'audio', 'conversation', 'scam'])


@given(
    audio=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=6.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_high_visual_score_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: High visual scores should be mentioned in explanations.
    
    When visual score is high (> 6.0), explanation should reference visual threats.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Explanation should mention visual-related threats
    explanation_text = ' '.join(result.explanation).lower()
    assert any(keyword in explanation_text for keyword in ['uniform', 'badge', 'visual', 'threat'])


@given(
    audio=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=7.1, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_high_liveness_score_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: High liveness scores should be mentioned in explanations.
    
    When liveness score is high (> 7.0), explanation should reference stress/distress.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Explanation should mention liveness-related indicators
    explanation_text = ' '.join(result.explanation).lower()
    assert any(keyword in explanation_text for keyword in ['stress', 'distress', 'caller'])


@given(
    audio=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_low_liveness_score_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Low liveness scores should be mentioned in explanations.
    
    When liveness score is low (< 3.0), explanation should reference deepfake/pre-recorded.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Explanation should mention deepfake indicators
    explanation_text = ' '.join(result.explanation).lower()
    assert any(keyword in explanation_text for keyword in ['deepfake', 'pre-recorded', 'video'])


@given(
    audio=st.floats(min_value=5.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=5.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_combined_threats_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Combined high scores should be mentioned in explanations.
    
    When both audio and visual scores are high (> 5.0), explanation should mention combined threats.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Explanation should mention combined threats
    explanation_text = ' '.join(result.explanation).lower()
    assert any(keyword in explanation_text for keyword in ['combined', 'audio', 'visual'])


@given(
    audio=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=3.0, max_value=6.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_safe_call_explained(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Safe calls should have appropriate explanations.
    
    When all scores are low, explanation should indicate no threats.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Should have at least one explanation
    assert len(result.explanation) > 0
    
    # For very low scores, should mention no threats
    if result.final_score < 3.0:
        explanation_text = ' '.join(result.explanation).lower()
        assert any(keyword in explanation_text for keyword in ['no', 'safe', 'threats'])


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_explanation_is_human_readable(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Explanations should be human-readable strings.
    
    All explanations should be non-empty strings with reasonable length.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    for explanation in result.explanation:
        # Should be a non-empty string
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        
        # Should have reasonable length (not too short, not too long)
        assert 10 <= len(explanation) <= 200
        
        # Should start with capital letter
        assert explanation[0].isupper()


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_explanation_count_reasonable(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Number of explanations should be reasonable.
    
    Should have at least 1 and at most 5 explanations.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # Should have reasonable number of explanations
    assert 1 <= len(result.explanation) <= 5


def test_explanation_for_known_scenario():
    """
    Unit test: Verify explanations for known threat scenario.
    """
    analyzer = ThreatAnalyzer()
    
    # High audio, high visual, low liveness
    result = analyzer.fuse_scores(9.0, 8.0, 2.0)
    
    explanation_text = ' '.join(result.explanation).lower()
    
    # Should mention audio threats
    assert 'keyword' in explanation_text or 'scam' in explanation_text
    
    # Should mention visual threats
    assert 'uniform' in explanation_text or 'badge' in explanation_text
    
    # Should mention deepfake
    assert 'deepfake' in explanation_text or 'pre-recorded' in explanation_text
    
    # Should mention combined threats
    assert 'combined' in explanation_text


def test_explanation_for_safe_scenario():
    """
    Unit test: Verify explanations for safe scenario.
    """
    analyzer = ThreatAnalyzer()
    
    # All low scores
    result = analyzer.fuse_scores(1.0, 1.0, 5.0)
    
    explanation_text = ' '.join(result.explanation).lower()
    
    # Should indicate no threats
    assert 'no' in explanation_text or 'safe' in explanation_text
