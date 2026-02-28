"""
Unit tests for graceful degradation functionality

These tests demonstrate specific examples of graceful degradation behavior
when one or more modalities are unavailable.
"""
import pytest
from app.services.threat_analyzer import ThreatAnalyzer


def test_audio_only_analysis():
    """Test threat analysis with only audio modality available"""
    analyzer = ThreatAnalyzer()
    
    # High audio threat, no visual or liveness
    result = analyzer.fuse_scores(audio=8.5, visual=None, liveness=None)
    
    assert result.degraded_mode is True
    assert result.available_modalities == ['audio']
    assert result.audio_score == 8.5
    assert result.visual_score is None
    assert result.liveness_score is None
    assert result.final_score == 8.5  # Should equal audio score
    assert result.is_alert is True
    assert 'DEGRADED MODE' in result.message
    assert 'audio' in result.message.lower()
    assert any('unavailable' in exp.lower() for exp in result.explanation)


def test_visual_only_analysis():
    """Test threat analysis with only visual modality available"""
    analyzer = ThreatAnalyzer()
    
    # High visual threat, no audio or liveness
    result = analyzer.fuse_scores(audio=None, visual=7.5, liveness=None)
    
    assert result.degraded_mode is True
    assert result.available_modalities == ['visual']
    assert result.audio_score is None
    assert result.visual_score == 7.5
    assert result.liveness_score is None
    assert result.final_score == 7.5  # Should equal visual score
    assert result.is_alert is True
    assert 'DEGRADED MODE' in result.message


def test_liveness_only_analysis():
    """Test threat analysis with only liveness modality available"""
    analyzer = ThreatAnalyzer()
    
    # Low liveness (potential deepfake), no audio or visual
    result = analyzer.fuse_scores(audio=None, visual=None, liveness=2.0)
    
    assert result.degraded_mode is True
    assert result.available_modalities == ['liveness']
    assert result.audio_score is None
    assert result.visual_score is None
    assert result.liveness_score == 2.0
    assert result.final_score == 2.0  # Should equal liveness score
    assert result.is_alert is False
    assert 'DEGRADED MODE' in result.message


def test_audio_visual_analysis():
    """Test threat analysis with audio and visual, no liveness"""
    analyzer = ThreatAnalyzer()
    
    # Both audio and visual available
    result = analyzer.fuse_scores(audio=8.0, visual=6.0, liveness=None)
    
    assert result.degraded_mode is True
    assert set(result.available_modalities) == {'audio', 'visual'}
    assert result.audio_score == 8.0
    assert result.visual_score == 6.0
    assert result.liveness_score is None
    
    # Calculate expected score with renormalized weights
    # Original: audio=0.45, visual=0.35, liveness=0.20
    # Renormalized: audio=0.45/0.80=0.5625, visual=0.35/0.80=0.4375
    expected = 8.0 * (0.45 / 0.80) + 6.0 * (0.35 / 0.80)
    assert abs(result.final_score - expected) < 0.01
    
    assert result.is_alert is True
    assert 'DEGRADED MODE' in result.message
    # Message should mention which modalities ARE available
    assert 'audio' in result.message.lower()
    assert 'visual' in result.message.lower()


def test_audio_liveness_analysis():
    """Test threat analysis with audio and liveness, no visual"""
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio=7.0, visual=None, liveness=8.0)
    
    assert result.degraded_mode is True
    assert set(result.available_modalities) == {'audio', 'liveness'}
    assert result.audio_score == 7.0
    assert result.visual_score is None
    assert result.liveness_score == 8.0
    
    # Calculate expected score with renormalized weights
    # Original: audio=0.45, liveness=0.20
    # Renormalized: audio=0.45/0.65=0.6923, liveness=0.20/0.65=0.3077
    expected = 7.0 * (0.45 / 0.65) + 8.0 * (0.20 / 0.65)
    assert abs(result.final_score - expected) < 0.01
    
    assert result.is_alert is True
    assert 'DEGRADED MODE' in result.message


def test_visual_liveness_analysis():
    """Test threat analysis with visual and liveness, no audio"""
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio=None, visual=5.0, liveness=4.0)
    
    assert result.degraded_mode is True
    assert set(result.available_modalities) == {'visual', 'liveness'}
    assert result.audio_score is None
    assert result.visual_score == 5.0
    assert result.liveness_score == 4.0
    
    # Calculate expected score with renormalized weights
    # Original: visual=0.35, liveness=0.20
    # Renormalized: visual=0.35/0.55=0.6364, liveness=0.20/0.55=0.3636
    expected = 5.0 * (0.35 / 0.55) + 4.0 * (0.20 / 0.55)
    assert abs(result.final_score - expected) < 0.01
    
    assert result.is_alert is False
    assert 'DEGRADED MODE' in result.message


def test_all_modalities_available_no_degradation():
    """Test that degraded mode is NOT active when all modalities are available"""
    analyzer = ThreatAnalyzer()
    
    result = analyzer.fuse_scores(audio=7.0, visual=6.0, liveness=5.0)
    
    assert result.degraded_mode is False
    assert set(result.available_modalities) == {'audio', 'visual', 'liveness'}
    assert result.audio_score == 7.0
    assert result.visual_score == 6.0
    assert result.liveness_score == 5.0
    assert 'DEGRADED MODE' not in result.message


def test_no_modalities_raises_error():
    """Test that providing no modalities raises an error"""
    analyzer = ThreatAnalyzer()
    
    with pytest.raises(ValueError, match="At least one modality must be available"):
        analyzer.fuse_scores(audio=None, visual=None, liveness=None)


def test_degraded_mode_confidence_penalty():
    """Test that confidence is reduced in degraded mode"""
    analyzer = ThreatAnalyzer()
    
    # Full mode
    result_full = analyzer.fuse_scores(audio=7.0, visual=6.0, liveness=5.0)
    
    # Degraded mode with 2 modalities
    result_degraded_2 = analyzer.fuse_scores(audio=7.0, visual=6.0, liveness=None)
    
    # Degraded mode with 1 modality
    result_degraded_1 = analyzer.fuse_scores(audio=7.0, visual=None, liveness=None)
    
    # Confidence should decrease as fewer modalities are available
    assert result_full.confidence > result_degraded_2.confidence
    assert result_degraded_2.confidence > result_degraded_1.confidence


def test_degraded_mode_explanation_mentions_unavailable():
    """Test that explanation mentions which modalities are unavailable"""
    analyzer = ThreatAnalyzer()
    
    # Missing visual and liveness
    result = analyzer.fuse_scores(audio=7.0, visual=None, liveness=None)
    
    explanation_text = ' '.join(result.explanation).lower()
    assert 'visual' in explanation_text
    assert 'liveness' in explanation_text
    assert 'unavailable' in explanation_text or 'warning' in explanation_text


def test_degraded_mode_history_tracking():
    """Test that degraded mode flag is preserved in history"""
    analyzer = ThreatAnalyzer()
    
    # Add degraded mode result
    result_degraded = analyzer.fuse_scores(audio=7.0, visual=None, liveness=None)
    analyzer.add_to_history(result_degraded)
    
    # Add full mode result
    result_full = analyzer.fuse_scores(audio=7.0, visual=6.0, liveness=5.0)
    analyzer.add_to_history(result_full)
    
    history = analyzer.get_history()
    
    # Most recent first
    assert history[0].degraded_mode is False
    assert history[1].degraded_mode is True


def test_partial_modality_alert_still_triggers():
    """Test that high threat alerts still trigger with partial modalities"""
    analyzer = ThreatAnalyzer()
    
    # High audio score only - should still trigger alert
    result = analyzer.fuse_scores(audio=9.5, visual=None, liveness=None)
    
    assert result.degraded_mode is True
    assert result.is_alert is True
    assert result.threat_level in ['high', 'critical']
    assert 'DEGRADED MODE' in result.message
    # Should still have the critical threat message
    assert 'THREAT' in result.message or 'RISK' in result.message


def test_low_threat_in_degraded_mode():
    """Test that low threats are correctly identified in degraded mode"""
    analyzer = ThreatAnalyzer()
    
    # Low audio score only
    result = analyzer.fuse_scores(audio=2.0, visual=None, liveness=None)
    
    assert result.degraded_mode is True
    assert result.is_alert is False
    assert result.threat_level == 'low'
    assert 'DEGRADED MODE' in result.message
    assert 'Safe' in result.message or 'low' in result.threat_level.lower()
