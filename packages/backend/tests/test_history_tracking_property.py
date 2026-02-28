"""
Property-based test for threat score history tracking

Feature: production-ready-browser-extension
Property 34: Threat Score History Tracking

For any threat analysis performed, the score should be appended to the session's 
historical threat score timeline with timestamp.

Validates: Requirements 16.5
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from app.services.threat_analyzer import ThreatAnalyzer


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=50
    )
)
@settings(max_examples=100, deadline=None)
def test_history_preserves_all_scores(scores):
    """
    Property: All threat analyses should be preserved in history.
    
    For any sequence of threat analyses, history should contain all results.
    """
    analyzer = ThreatAnalyzer()
    
    # Perform multiple analyses
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
    
    # Verify all scores are in history
    history = analyzer.get_history()
    assert len(history) == len(scores)


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=2,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_history_maintains_chronological_order(scores):
    """
    Property: History should maintain chronological order (most recent first).
    
    When retrieving history, entries should be ordered by timestamp.
    """
    analyzer = ThreatAnalyzer()
    
    # Perform analyses
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
    
    # Get history
    history = analyzer.get_history()
    
    # Verify chronological order (most recent first)
    for i in range(len(history) - 1):
        assert history[i].timestamp >= history[i + 1].timestamp, \
            "History should be ordered by timestamp (most recent first)"


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=10,
        max_size=50
    ),
    limit=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_history_limit_respected(scores, limit):
    """
    Property: History retrieval should respect limit parameter.
    
    When requesting limited history, should return at most limit entries.
    """
    analyzer = ThreatAnalyzer()
    
    # Perform analyses
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
    
    # Get limited history
    history = analyzer.get_history(limit=limit)
    
    # Verify limit is respected
    assert len(history) <= limit
    assert len(history) == min(limit, len(scores))


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_max_threat_score_tracking(scores):
    """
    Property: Maximum threat score should be tracked correctly.
    
    The max score should equal the highest final score in history.
    """
    analyzer = ThreatAnalyzer()
    
    final_scores = []
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
        final_scores.append(result.final_score)
    
    # Get max threat score
    max_score = analyzer.get_max_threat_score()
    
    # Verify it matches the actual maximum
    assert max_score == max(final_scores)


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_alert_count_tracking(scores):
    """
    Property: Alert count should match number of high-threat scores.
    
    Count of alerts should equal number of entries with is_alert=True.
    """
    analyzer = ThreatAnalyzer()
    
    expected_alert_count = 0
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
        if result.is_alert:
            expected_alert_count += 1
    
    # Get alert count
    alert_count = analyzer.get_alert_count()
    
    # Verify it matches expected count
    assert alert_count == expected_alert_count


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_history_entries_have_timestamps(scores):
    """
    Property: All history entries should have valid timestamps.
    
    Every entry should have a timestamp that is a datetime object.
    """
    analyzer = ThreatAnalyzer()
    
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
    
    history = analyzer.get_history()
    
    for entry in history:
        assert isinstance(entry.timestamp, datetime)
        # Timestamp should be recent (within last hour)
        assert entry.timestamp <= datetime.utcnow()
        assert entry.timestamp >= datetime.utcnow() - timedelta(hours=1)


@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_history_preserves_modality_scores(scores):
    """
    Property: History should preserve individual modality scores.
    
    Each history entry should contain audio, visual, and liveness scores.
    """
    analyzer = ThreatAnalyzer()
    
    for audio, visual, liveness in scores:
        result = analyzer.fuse_scores(audio, visual, liveness)
        analyzer.add_to_history(result)
    
    history = analyzer.get_history()
    
    # Verify each entry has all modality scores
    for i, entry in enumerate(reversed(history)):  # Reverse to match insertion order
        audio, visual, liveness = scores[i]
        assert entry.audio_score == audio
        assert entry.visual_score == visual
        assert entry.liveness_score == liveness


def test_empty_history():
    """
    Edge case: Empty history should return None for max score.
    """
    analyzer = ThreatAnalyzer()
    
    assert analyzer.get_max_threat_score() is None
    assert analyzer.get_alert_count() == 0
    assert len(analyzer.get_history()) == 0


def test_clear_history():
    """
    Unit test: Clearing history should remove all entries.
    """
    analyzer = ThreatAnalyzer()
    
    # Add some entries
    for i in range(5):
        result = analyzer.fuse_scores(5.0, 5.0, 5.0)
        analyzer.add_to_history(result)
    
    assert len(analyzer.get_history()) == 5
    
    # Clear history
    analyzer.clear_history()
    
    assert len(analyzer.get_history()) == 0
    assert analyzer.get_max_threat_score() is None
    assert analyzer.get_alert_count() == 0


def test_history_since_filter():
    """
    Unit test: History filtering by timestamp should work correctly.
    """
    analyzer = ThreatAnalyzer()
    
    # Add entries
    for i in range(5):
        result = analyzer.fuse_scores(float(i), float(i), float(i))
        analyzer.add_to_history(result)
    
    # Get recent history (last 1 second)
    since = datetime.utcnow() - timedelta(seconds=1)
    recent_history = analyzer.get_history(since=since)
    
    # All entries should be recent
    assert len(recent_history) == 5
    
    # Get very old history (should be empty)
    old_since = datetime.utcnow() + timedelta(hours=1)
    old_history = analyzer.get_history(since=old_since)
    assert len(old_history) == 0
