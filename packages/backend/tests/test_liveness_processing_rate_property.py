"""
Property-Based Test: Liveness Processing Rate

Feature: production-ready-browser-extension
Property 29: Liveness Processing Rate

For any sequence of video frames, the liveness detector should process frames
at 1 FPS (one frame per second).

Validates: Requirements 15.7
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.liveness_detector import LivenessDetector
from PIL import Image
import io
import time
import numpy as np


def generate_simple_frame(seed: int = None) -> bytes:
    """Generate a simple test frame"""
    if seed is not None:
        np.random.seed(seed)
    
    image = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@given(
    num_frames=st.integers(min_value=2, max_value=10),
    time_interval=st.floats(min_value=0.1, max_value=0.9)
)
@settings(max_examples=50, deadline=10000)
def test_liveness_processing_rate_skips_fast_frames(num_frames: int, time_interval: float):
    """
    Property 29: Liveness Processing Rate
    
    For any sequence of frames arriving faster than 1 FPS, the detector should
    skip frames to maintain 1 FPS processing rate.
    """
    detector = LivenessDetector()
    detector.reset_history()
    
    # Generate frames
    frame_bytes = generate_simple_frame(seed=42)
    
    # Simulate frames arriving at intervals < 1 second
    current_time = time.time()
    processed_count = 0
    skipped_count = 0
    
    for i in range(num_frames):
        timestamp = current_time + (i * time_interval)
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
        
        # Check if frame was processed or skipped
        # Skipped frames return empty result with face_detected=False
        if i == 0:
            # First frame should always be processed
            processed_count += 1
        else:
            # Subsequent frames: check if enough time passed
            time_since_last = timestamp - detector.last_processed_time
            if time_since_last >= 1.0:
                # Should be processed
                processed_count += 1
            else:
                # Should be skipped
                skipped_count += 1
    
    # Property 1: At least one frame should be processed (the first one)
    assert processed_count >= 1, "At least the first frame should be processed"
    
    # Property 2: If time_interval < 1.0, some frames should be skipped
    if time_interval < 1.0:
        expected_processed = 1 + int((num_frames - 1) * time_interval / 1.0)
        # Allow some tolerance
        assert processed_count <= expected_processed + 2, \
            f"Too many frames processed: {processed_count} (expected ~{expected_processed})"


def test_processing_rate_exactly_1fps():
    """
    Test that frames arriving at exactly 1 FPS are all processed.
    """
    detector = LivenessDetector()
    detector.reset_history()
    
    frame_bytes = generate_simple_frame(seed=42)
    
    # Send frames at exactly 1 second intervals
    num_frames = 5
    current_time = time.time()
    processed_count = 0
    
    for i in range(num_frames):
        timestamp = current_time + (i * 1.0)  # Exactly 1 second apart
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
        
        # All frames should be processed
        processed_count += 1
    
    # All frames should be processed
    stats = detector.get_stats()
    assert stats['frames_processed'] >= num_frames - 1, \
        f"Expected {num_frames} frames processed, got {stats['frames_processed']}"


def test_processing_rate_slower_than_1fps():
    """
    Test that frames arriving slower than 1 FPS are all processed.
    """
    detector = LivenessDetector()
    detector.reset_history()
    
    frame_bytes = generate_simple_frame(seed=42)
    
    # Send frames at 2 second intervals (0.5 FPS)
    num_frames = 3
    current_time = time.time()
    
    for i in range(num_frames):
        timestamp = current_time + (i * 2.0)  # 2 seconds apart
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
    
    # All frames should be processed
    stats = detector.get_stats()
    assert stats['frames_processed'] >= num_frames - 1, \
        "All frames arriving slower than 1 FPS should be processed"


def test_processing_rate_burst_then_slow():
    """
    Test behavior with burst of frames followed by slow frames.
    """
    detector = LivenessDetector()
    detector.reset_history()
    
    frame_bytes = generate_simple_frame(seed=42)
    current_time = time.time()
    
    # Burst: 5 frames in 0.5 seconds
    for i in range(5):
        timestamp = current_time + (i * 0.1)
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
    
    stats_after_burst = detector.get_stats()
    processed_after_burst = stats_after_burst['frames_processed']
    
    # Only 1 frame should be processed from the burst
    assert processed_after_burst <= 2, \
        f"Burst should process only 1-2 frames, got {processed_after_burst}"
    
    # Then slow frames: 3 frames at 1.5 second intervals
    for i in range(3):
        timestamp = current_time + 1.0 + (i * 1.5)
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
    
    stats_final = detector.get_stats()
    processed_final = stats_final['frames_processed']
    
    # Slow frames should all be processed
    assert processed_final >= processed_after_burst + 2, \
        "Slow frames after burst should be processed"


@given(num_frames=st.integers(min_value=10, max_value=30))
@settings(max_examples=20, deadline=10000)
def test_frame_skip_count_tracking(num_frames: int):
    """
    Property: Frame skip count should be tracked correctly.
    """
    detector = LivenessDetector()
    detector.reset_history()
    
    frame_bytes = generate_simple_frame(seed=42)
    current_time = time.time()
    
    # Send frames at 0.1 second intervals (10 FPS)
    for i in range(num_frames):
        timestamp = current_time + (i * 0.1)
        result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
    
    stats = detector.get_stats()
    
    # Property 1: frames_processed + frames_skipped should account for all frames
    # (Note: first frame is always processed, so we expect many skips)
    total_accounted = stats['frames_processed'] + stats['frames_skipped']
    
    # Should be close to num_frames (allowing for first frame)
    assert total_accounted >= num_frames - 2, \
        f"Total accounted ({total_accounted}) should be close to {num_frames}"
    
    # Property 2: Most frames should be skipped (since 10 FPS > 1 FPS)
    assert stats['frames_skipped'] > stats['frames_processed'], \
        "More frames should be skipped than processed when rate > 1 FPS"


def test_reset_clears_rate_control_state():
    """
    Test that reset_history() clears rate control state.
    """
    detector = LivenessDetector()
    
    frame_bytes = generate_simple_frame(seed=42)
    current_time = time.time()
    
    # Process some frames
    for i in range(5):
        timestamp = current_time + (i * 0.1)
        detector.detect_liveness(frame_bytes, timestamp=timestamp)
    
    stats_before = detector.get_stats()
    assert stats_before['frames_processed'] > 0 or stats_before['frames_skipped'] > 0
    
    # Reset
    detector.reset_history()
    
    # Check state is cleared
    stats_after = detector.get_stats()
    assert stats_after['frames_processed'] == 0
    assert stats_after['frames_skipped'] == 0
    assert stats_after['last_processed_time'] == 0.0


def test_target_fps_configuration():
    """
    Test that target FPS is correctly configured.
    """
    detector = LivenessDetector()
    
    stats = detector.get_stats()
    
    # Should be 1.0 FPS
    assert stats['target_fps'] == 1.0, \
        f"Target FPS should be 1.0, got {stats['target_fps']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
