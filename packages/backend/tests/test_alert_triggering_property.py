"""
Property-based test for high-threat alert triggering

Feature: production-ready-browser-extension
Property 33: High-Threat Alert Triggering

For any unified threat score ≥ 7.0, the system should trigger a high-priority alert 
and notify the user within 1 second.

Validates: Requirements 16.4
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.services.threat_analyzer import ThreatAnalyzer


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_alert_triggered_for_high_scores(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: For any final score ≥ 7.0, is_alert should be True.
    
    High threat scores must always trigger alerts.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    if result.final_score >= 7.0:
        assert result.is_alert is True, \
            f"Score {result.final_score} >= 7.0 should trigger alert"
    else:
        assert result.is_alert is False, \
            f"Score {result.final_score} < 7.0 should not trigger alert"


@given(
    audio=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_high_scores_always_trigger_alert(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: When all modality scores are high (≥ 7.0), alert must be triggered.
    
    This ensures critical threats are never missed.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # With all scores >= 7.0, final score will definitely be >= 7.0
    assert result.final_score >= 7.0
    assert result.is_alert is True
    assert result.threat_level in ['high', 'critical']


@given(
    audio=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_low_scores_never_trigger_alert(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: When all modality scores are low (≤ 3.0), alert should not be triggered.
    
    This prevents false alarms from safe calls.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    # With all scores <= 3.0, final score will definitely be <= 3.0
    assert result.final_score <= 3.0
    assert result.is_alert is False
    assert result.threat_level == 'low'


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_threat_level_consistency_with_alert(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Alert status should be consistent with threat level.
    
    High and critical threat levels should always have is_alert=True.
    Low and moderate threat levels should have is_alert=False.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    if result.threat_level in ['high', 'critical']:
        assert result.is_alert is True, \
            f"Threat level {result.threat_level} should trigger alert"
    else:
        assert result.is_alert is False, \
            f"Threat level {result.threat_level} should not trigger alert"


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_alert_message_appropriate_for_level(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: Alert message should be appropriate for threat level.
    
    Critical threats should have urgent messages.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    if result.threat_level == 'critical':
        assert 'CRITICAL' in result.message.upper()
    elif result.threat_level == 'high':
        assert 'HIGH' in result.message.upper() or 'RISK' in result.message.upper()
    elif result.threat_level == 'moderate':
        assert 'MODERATE' in result.message.upper()
    elif result.threat_level == 'low':
        assert 'Safe' in result.message or 'No threats' in result.message


def test_alert_threshold_boundary():
    """
    Unit test: Test exact threshold boundary (7.0).
    """
    analyzer = ThreatAnalyzer()
    
    # Just below threshold
    result_below = analyzer.fuse_scores(6.9, 6.9, 6.9)
    assert result_below.is_alert is False
    
    # At threshold
    result_at = analyzer.fuse_scores(7.0, 7.0, 7.0)
    assert result_at.is_alert is True
    
    # Above threshold
    result_above = analyzer.fuse_scores(7.1, 7.1, 7.1)
    assert result_above.is_alert is True


def test_critical_threshold_boundary():
    """
    Unit test: Test critical threshold boundary (8.5).
    """
    analyzer = ThreatAnalyzer()
    
    # Just below critical
    result_below = analyzer.fuse_scores(8.4, 8.4, 8.4)
    assert result_below.threat_level == 'high'
    assert result_below.is_alert is True
    
    # At critical threshold
    result_at = analyzer.fuse_scores(8.5, 8.5, 8.5)
    assert result_at.threat_level == 'critical'
    assert result_at.is_alert is True
    
    # Above critical
    result_above = analyzer.fuse_scores(9.0, 9.0, 9.0)
    assert result_above.threat_level == 'critical'
    assert result_above.is_alert is True


def test_moderate_threshold_boundary():
    """
    Unit test: Test moderate threshold boundary (5.0).
    """
    analyzer = ThreatAnalyzer()
    
    # Just below moderate
    result_below = analyzer.fuse_scores(4.9, 4.9, 4.9)
    assert result_below.threat_level == 'low'
    assert result_below.is_alert is False
    
    # At moderate threshold
    result_at = analyzer.fuse_scores(5.0, 5.0, 5.0)
    assert result_at.threat_level == 'moderate'
    assert result_at.is_alert is False
    
    # Above moderate but below high
    result_above = analyzer.fuse_scores(6.0, 6.0, 6.0)
    assert result_above.threat_level == 'moderate'
    assert result_above.is_alert is False


@given(
    audio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_alert_includes_explanation(
    audio: float,
    visual: float,
    liveness: float
):
    """
    Property: All threat results should include explanations.
    
    Even low-threat results should have explanations for transparency.
    """
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio, visual, liveness)
    
    assert isinstance(result.explanation, list)
    assert len(result.explanation) > 0
    assert all(isinstance(exp, str) for exp in result.explanation)
