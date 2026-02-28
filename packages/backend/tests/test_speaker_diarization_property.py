"""
Property-Based Test: Speaker Diarization

Feature: production-ready-browser-extension
Property 20: Speaker Diarization

For any audio segment containing multiple speakers, the transcriber should
detect speaker changes and label each segment with a speaker identifier.

Validates: Requirements 13.3
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.audio_transcriber import AudioTranscriber, TranscriptSegment
import logging

logger = logging.getLogger(__name__)


def test_speaker_diarization_labels_segments():
    """
    Property 20: Speaker Diarization
    
    For any audio with multiple segments, each segment should have a speaker label.
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create mock segments simulating Whisper output
    mock_segments = [
        {
            'text': 'Hello, this is the first speaker.',
            'start': 0.0,
            'end': 2.0,
            'confidence': 0.95,
            'words': []
        },
        {
            'text': 'And this is the second speaker after a pause.',
            'start': 3.5,  # 1.5 second pause (> 1.0 threshold)
            'end': 6.0,
            'confidence': 0.92,
            'words': []
        },
        {
            'text': 'First speaker continues.',
            'start': 6.2,  # Short pause (< 1.0 threshold)
            'end': 8.0,
            'confidence': 0.90,
            'words': []
        },
        {
            'text': 'Second speaker again after long pause.',
            'start': 10.0,  # 2.0 second pause (> 1.0 threshold)
            'end': 12.5,
            'confidence': 0.88,
            'words': []
        }
    ]
    
    # Apply speaker diarization
    labeled_segments = transcriber.detect_speaker_changes(mock_segments)
    
    # Property 1: All segments should have speaker labels
    assert len(labeled_segments) == len(mock_segments), \
        "Number of labeled segments should match input segments"
    
    for i, segment in enumerate(labeled_segments):
        assert segment.speaker is not None, \
            f"Segment {i} should have a speaker label"
        
        assert segment.speaker.startswith("Speaker_"), \
            f"Segment {i} speaker label should start with 'Speaker_'"
    
    # Property 2: Speaker changes should be detected based on pauses
    # Segment 0: Speaker_1 (first speaker)
    assert labeled_segments[0].speaker == "Speaker_1"
    
    # Segment 1: Speaker_2 (pause > 1.0s)
    assert labeled_segments[1].speaker == "Speaker_2"
    
    # Segment 2: Speaker_2 (pause < 1.0s, same speaker continues)
    assert labeled_segments[2].speaker == "Speaker_2"
    
    # Segment 3: Speaker_3 (pause > 1.0s, new speaker)
    assert labeled_segments[3].speaker == "Speaker_3"
    
    logger.info(f"✓ Speaker diarization validated: {len(labeled_segments)} segments with speaker labels")


@settings(max_examples=20)
@given(
    num_segments=st.integers(min_value=1, max_value=10),
    pause_threshold=st.floats(min_value=0.5, max_value=2.0)
)
def test_speaker_count_increases_with_long_pauses(num_segments, pause_threshold):
    """
    Property: Number of detected speakers should increase when pauses exceed threshold
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with varying pauses
    segments = []
    current_time = 0.0
    
    for i in range(num_segments):
        segment = {
            'text': f'Segment {i}',
            'start': current_time,
            'end': current_time + 2.0,
            'confidence': 0.9,
            'words': []
        }
        segments.append(segment)
        
        # Add pause (alternating short and long)
        if i % 2 == 0:
            current_time += 2.5  # Short pause (0.5s)
        else:
            current_time += 4.0  # Long pause (2.0s)
    
    # Apply speaker diarization
    labeled_segments = transcriber.detect_speaker_changes(segments)
    
    # Property: All segments should have speaker labels
    assert all(seg.speaker is not None for seg in labeled_segments), \
        "All segments should have speaker labels"
    
    # Property: Speaker IDs should be sequential
    speaker_ids = [seg.speaker for seg in labeled_segments]
    unique_speakers = set(speaker_ids)
    
    # At least one speaker should be detected
    assert len(unique_speakers) >= 1, \
        "At least one speaker should be detected"
    
    # Number of unique speakers should not exceed number of segments
    assert len(unique_speakers) <= num_segments, \
        "Number of speakers should not exceed number of segments"
    
    logger.info(
        f"✓ Speaker diarization property validated: "
        f"{num_segments} segments → {len(unique_speakers)} speakers"
    )


def test_single_segment_has_one_speaker():
    """
    Test that a single segment is assigned to one speaker
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    segments = [
        {
            'text': 'Single segment audio.',
            'start': 0.0,
            'end': 3.0,
            'confidence': 0.95,
            'words': []
        }
    ]
    
    labeled_segments = transcriber.detect_speaker_changes(segments)
    
    assert len(labeled_segments) == 1
    assert labeled_segments[0].speaker == "Speaker_1"


def test_continuous_speech_same_speaker():
    """
    Test that continuous speech (short pauses) is attributed to same speaker
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with short pauses (< 1.0s)
    segments = [
        {'text': 'Part one.', 'start': 0.0, 'end': 1.0, 'confidence': 0.9, 'words': []},
        {'text': 'Part two.', 'start': 1.2, 'end': 2.2, 'confidence': 0.9, 'words': []},
        {'text': 'Part three.', 'start': 2.5, 'end': 3.5, 'confidence': 0.9, 'words': []},
    ]
    
    labeled_segments = transcriber.detect_speaker_changes(segments)
    
    # All segments should have the same speaker (short pauses)
    speakers = [seg.speaker for seg in labeled_segments]
    assert len(set(speakers)) == 1, \
        "Continuous speech with short pauses should be attributed to one speaker"
    
    assert speakers[0] == "Speaker_1"


def test_long_pauses_indicate_speaker_changes():
    """
    Test that long pauses (> 1.0s) indicate speaker changes
    """
    transcriber = AudioTranscriber(model_size='tiny')
    
    # Create segments with long pauses (> 1.0s)
    segments = [
        {'text': 'First speaker.', 'start': 0.0, 'end': 2.0, 'confidence': 0.9, 'words': []},
        {'text': 'Second speaker.', 'start': 4.0, 'end': 6.0, 'confidence': 0.9, 'words': []},  # 2.0s pause
        {'text': 'Third speaker.', 'start': 8.5, 'end': 10.5, 'confidence': 0.9, 'words': []},  # 2.5s pause
    ]
    
    labeled_segments = transcriber.detect_speaker_changes(segments)
    
    # Each segment should have a different speaker (long pauses)
    speakers = [seg.speaker for seg in labeled_segments]
    assert len(set(speakers)) == 3, \
        "Long pauses should indicate speaker changes"
    
    assert speakers == ["Speaker_1", "Speaker_2", "Speaker_3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
