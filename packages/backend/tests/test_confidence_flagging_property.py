"""
Property-Based Test: Low-Confidence Flagging

Feature: production-ready-browser-extension
Property 13: Low-Confidence Flagging

For any transcription or analysis result with confidence score below 0.6,
the system should flag the result as uncertain and mark it for review.

Validates: Requirements 6.6, 13.6
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.audio_transcriber import AudioTranscriber, TranscriptSegment
import logging

logger = logging.getLogger(__name__)


def test_low_confidence_threshold():
    """
    Property 13: Low-Confidence Flagging
    
    For any segment with confidence < 0.6, it should be flagged as low confidence.
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with varying confidence levels
    segments = [
        TranscriptSegment(text="High confidence", start=0.0, end=2.0, confidence=0.95),
        TranscriptSegment(text="Medium confidence", start=2.0, end=4.0, confidence=0.75),
        TranscriptSegment(text="At threshold", start=4.0, end=6.0, confidence=0.6),
        TranscriptSegment(text="Below threshold", start=6.0, end=8.0, confidence=0.59),
        TranscriptSegment(text="Low confidence", start=8.0, end=10.0, confidence=0.3),
        TranscriptSegment(text="Very low", start=10.0, end=12.0, confidence=0.1),
    ]
    
    # Flag low-confidence segments
    low_confidence_indices = transcriber.flag_low_confidence(segments)
    
    # Property: Segments with confidence < 0.6 should be flagged
    expected_flagged = [3, 4, 5]  # Indices of segments with confidence < 0.6
    
    assert low_confidence_indices == expected_flagged, \
        f"Expected indices {expected_flagged}, got {low_confidence_indices}"
    
    # Property: Segments with confidence >= 0.6 should NOT be flagged
    for i in [0, 1, 2]:
        assert i not in low_confidence_indices, \
            f"Segment {i} with confidence >= 0.6 should not be flagged"
    
    logger.info(f"✓ Low-confidence flagging validated: {len(low_confidence_indices)} segments flagged")


@settings(max_examples=50)
@given(
    confidence=st.floats(min_value=0.0, max_value=1.0)
)
def test_confidence_threshold_property(confidence):
    """
    Property: Any segment with confidence < 0.6 should be flagged
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create a single segment with the given confidence
    segment = TranscriptSegment(
        text="Test segment",
        start=0.0,
        end=2.0,
        confidence=confidence
    )
    
    # Flag low-confidence segments
    low_confidence_indices = transcriber.flag_low_confidence([segment])
    
    # Property: Segment should be flagged if and only if confidence < 0.6
    if confidence < 0.6:
        assert 0 in low_confidence_indices, \
            f"Segment with confidence {confidence:.2f} should be flagged"
    else:
        assert 0 not in low_confidence_indices, \
            f"Segment with confidence {confidence:.2f} should NOT be flagged"
    
    logger.info(f"✓ Confidence {confidence:.2f}: {'flagged' if 0 in low_confidence_indices else 'not flagged'}")


def test_empty_segments_no_flags():
    """
    Test that empty segment list returns no flags
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    low_confidence_indices = transcriber.flag_low_confidence([])
    
    assert low_confidence_indices == [], \
        "Empty segment list should return no flags"
    
    logger.info("✓ Empty segments return no flags")


def test_all_high_confidence_no_flags():
    """
    Test that all high-confidence segments return no flags
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with high confidence
    segments = [
        TranscriptSegment(text=f"Segment {i}", start=i*2.0, end=(i+1)*2.0, confidence=0.9)
        for i in range(5)
    ]
    
    low_confidence_indices = transcriber.flag_low_confidence(segments)
    
    assert low_confidence_indices == [], \
        "All high-confidence segments should return no flags"
    
    logger.info("✓ All high-confidence segments return no flags")


def test_all_low_confidence_all_flagged():
    """
    Test that all low-confidence segments are flagged
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with low confidence
    num_segments = 5
    segments = [
        TranscriptSegment(text=f"Segment {i}", start=i*2.0, end=(i+1)*2.0, confidence=0.3)
        for i in range(num_segments)
    ]
    
    low_confidence_indices = transcriber.flag_low_confidence(segments)
    
    assert len(low_confidence_indices) == num_segments, \
        "All low-confidence segments should be flagged"
    
    assert low_confidence_indices == list(range(num_segments)), \
        "Flagged indices should match all segment indices"
    
    logger.info(f"✓ All {num_segments} low-confidence segments flagged")


def test_boundary_confidence_values():
    """
    Test boundary values around the 0.6 threshold
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Test values around the threshold
    test_values = [0.59, 0.599, 0.6, 0.600, 0.601]
    
    for conf in test_values:
        segment = TranscriptSegment(
            text="Test",
            start=0.0,
            end=2.0,
            confidence=conf
        )
        
        flags = transcriber.flag_low_confidence([segment])
        
        if conf < 0.6:
            assert 0 in flags, f"Confidence {conf} should be flagged"
        else:
            assert 0 not in flags, f"Confidence {conf} should NOT be flagged"
    
    logger.info("✓ Boundary confidence values validated")


def test_mixed_confidence_segments():
    """
    Test a mix of high and low confidence segments
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create mixed confidence segments
    segments = [
        TranscriptSegment(text="High 1", start=0.0, end=2.0, confidence=0.95),
        TranscriptSegment(text="Low 1", start=2.0, end=4.0, confidence=0.4),
        TranscriptSegment(text="High 2", start=4.0, end=6.0, confidence=0.85),
        TranscriptSegment(text="Low 2", start=6.0, end=8.0, confidence=0.2),
        TranscriptSegment(text="High 3", start=8.0, end=10.0, confidence=0.7),
    ]
    
    low_confidence_indices = transcriber.flag_low_confidence(segments)
    
    # Only indices 1 and 3 should be flagged
    assert low_confidence_indices == [1, 3], \
        f"Expected [1, 3], got {low_confidence_indices}"
    
    logger.info("✓ Mixed confidence segments correctly flagged")


def test_confidence_flagging_preserves_order():
    """
    Test that flagged indices are in ascending order
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with random confidence values
    segments = [
        TranscriptSegment(text=f"Seg {i}", start=i*2.0, end=(i+1)*2.0, confidence=0.3 if i % 2 == 0 else 0.9)
        for i in range(10)
    ]
    
    low_confidence_indices = transcriber.flag_low_confidence(segments)
    
    # Property: Indices should be in ascending order
    assert low_confidence_indices == sorted(low_confidence_indices), \
        "Flagged indices should be in ascending order"
    
    logger.info(f"✓ Flagged indices in order: {low_confidence_indices}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
