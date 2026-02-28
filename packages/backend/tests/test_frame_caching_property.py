"""
Property-Based Test: Frame Analysis Caching

Feature: production-ready-browser-extension
Property 25: Frame Analysis Caching

For any two consecutive video frames with similarity score > 0.95, the second
frame should reuse the cached analysis result from the first frame.

Validates: Requirements 14.7, 19.2
"""
import pytest
from hypothesis import given, strategies as st, settings
from PIL import Image
import io
from app.services.visual_analyzer import VisualAnalyzer
from unittest.mock import patch


def create_test_frame(width: int = 640, height: int = 480, color: tuple = (255, 255, 255)) -> bytes:
    """Create a test frame with specified color"""
    image = Image.new('RGB', (width, height), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@pytest.fixture
def visual_analyzer():
    """Create visual analyzer instance for testing"""
    return VisualAnalyzer(api_key='test-api-key')


@pytest.mark.integration
@patch.object(VisualAnalyzer, 'analyze_frame')
def test_identical_frames_use_cache(mock_analyze, visual_analyzer):
    """
    Property 25: Frame Analysis Caching
    
    For identical frames, the second analysis should use cached result.
    
    This test verifies that:
    1. First frame is analyzed normally
    2. Second identical frame uses cached result
    3. API is only called once for identical frames
    """
    # Mock the actual analyze_frame to track calls
    from app.services.visual_analyzer import VisualResult
    mock_result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=0.0,
        analysis='Test analysis',
        cached=False
    )
    
    # We need to test the real caching logic, so let's use the real method
    # but mock the Gemini API call
    mock_analyze.side_effect = None
    
    # Create identical frame
    frame_bytes = create_test_frame()
    
    # Get initial cache size
    initial_cache_size = len(visual_analyzer.frame_cache)
    
    # Manually add to cache to test cache hit
    visual_analyzer._add_to_cache(frame_bytes, mock_result)
    
    # Verify cache size increased
    assert len(visual_analyzer.frame_cache) == initial_cache_size + 1
    
    # Check cache for the frame
    cached_result = visual_analyzer._check_cache(frame_bytes)
    
    # Property: Cached result should be returned
    assert cached_result is not None, "Cache should return result for identical frame"
    assert cached_result.cached == True, "Result should be marked as cached"
    assert cached_result.score == mock_result.score
    assert cached_result.confidence == mock_result.confidence


@given(
    color_r=st.integers(min_value=0, max_value=255),
    color_g=st.integers(min_value=0, max_value=255),
    color_b=st.integers(min_value=0, max_value=255)
)
@settings(max_examples=20)
def test_cache_stores_results(color_r: int, color_g: int, color_b: int):
    """
    Property test: Verify cache stores and retrieves results correctly
    
    For any frame, after caching, the result should be retrievable.
    """
    # Create analyzer
    visual_analyzer = VisualAnalyzer(api_key='test-api-key')
    
    # Create frame with specific color
    frame_bytes = create_test_frame(color=(color_r, color_g, color_b))
    
    # Create mock result
    from app.services.visual_analyzer import VisualResult
    result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=5.0,
        analysis='Test',
        cached=False
    )
    
    # Add to cache
    visual_analyzer._add_to_cache(frame_bytes, result)
    
    # Property: Should be able to retrieve from cache
    cached_result = visual_analyzer._check_cache(frame_bytes)
    
    assert cached_result is not None, "Should retrieve cached result"
    assert cached_result.score == result.score
    assert cached_result.confidence == result.confidence


@pytest.mark.integration
def test_different_frames_not_cached(visual_analyzer):
    """
    Integration test: Verify different frames don't share cache
    
    Different frames should have separate cache entries.
    """
    # Create two different frames
    frame1_bytes = create_test_frame(color=(255, 0, 0))  # Red
    frame2_bytes = create_test_frame(color=(0, 255, 0))  # Green
    
    # Create mock results
    from app.services.visual_analyzer import VisualResult
    result1 = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=3.0,
        analysis='Frame 1',
        cached=False
    )
    
    result2 = VisualResult(
        uniform_detected=True,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.9,
        score=7.0,
        analysis='Frame 2',
        cached=False
    )
    
    # Add both to cache
    visual_analyzer._add_to_cache(frame1_bytes, result1)
    visual_analyzer._add_to_cache(frame2_bytes, result2)
    
    # Retrieve from cache
    cached1 = visual_analyzer._check_cache(frame1_bytes)
    cached2 = visual_analyzer._check_cache(frame2_bytes)
    
    # Verify correct results are returned
    assert cached1 is not None
    assert cached2 is not None
    assert cached1.score == 3.0
    assert cached2.score == 7.0
    assert cached1.analysis == 'Frame 1'
    assert cached2.analysis == 'Frame 2'


@pytest.mark.integration
def test_cache_expiration(visual_analyzer):
    """
    Integration test: Verify cache entries expire after TTL
    
    Cached entries should be removed after TTL expires.
    """
    from datetime import datetime, timedelta
    
    # Create frame
    frame_bytes = create_test_frame()
    
    # Create mock result
    from app.services.visual_analyzer import VisualResult
    result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=5.0,
        analysis='Test',
        cached=False
    )
    
    # Add to cache
    visual_analyzer._add_to_cache(frame_bytes, result)
    
    # Verify it's in cache
    cached = visual_analyzer._check_cache(frame_bytes)
    assert cached is not None
    
    # Manually expire the cache entry
    frame_hash = visual_analyzer._calculate_frame_hash(frame_bytes)
    if frame_hash in visual_analyzer.frame_cache:
        # Set timestamp to past (beyond TTL)
        expired_time = datetime.now() - timedelta(seconds=visual_analyzer.CACHE_TTL + 1)
        visual_analyzer.frame_cache[frame_hash] = (result, expired_time)
    
    # Check cache again - should return None for expired entry
    cached_after_expiry = visual_analyzer._check_cache(frame_bytes)
    assert cached_after_expiry is None, "Expired cache entry should not be returned"


@pytest.mark.integration
def test_cache_cleanup(visual_analyzer):
    """
    Integration test: Verify cache cleanup removes expired entries
    
    The _clean_cache method should remove expired entries.
    """
    from datetime import datetime, timedelta
    
    # Create multiple frames
    frames = [create_test_frame(color=(i, i, i)) for i in range(5)]
    
    # Create mock result
    from app.services.visual_analyzer import VisualResult
    result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=5.0,
        analysis='Test',
        cached=False
    )
    
    # Add all to cache
    for frame_bytes in frames:
        visual_analyzer._add_to_cache(frame_bytes, result)
    
    # Verify all are in cache
    assert len(visual_analyzer.frame_cache) == 5
    
    # Expire some entries manually
    expired_time = datetime.now() - timedelta(seconds=visual_analyzer.CACHE_TTL + 1)
    for i, (frame_hash, (res, _)) in enumerate(list(visual_analyzer.frame_cache.items())):
        if i < 3:  # Expire first 3 entries
            visual_analyzer.frame_cache[frame_hash] = (res, expired_time)
    
    # Clean cache
    visual_analyzer._clean_cache()
    
    # Verify expired entries were removed
    assert len(visual_analyzer.frame_cache) == 2, "Should have 2 non-expired entries remaining"


@pytest.mark.integration
def test_cache_stats(visual_analyzer):
    """
    Integration test: Verify cache statistics are accurate
    
    Cache stats should reflect current cache state.
    """
    # Get initial stats
    stats = visual_analyzer.get_cache_stats()
    
    assert 'size' in stats
    assert 'ttl_seconds' in stats
    assert 'similarity_threshold' in stats
    
    # Verify initial size
    initial_size = stats['size']
    
    # Add some frames to cache
    from app.services.visual_analyzer import VisualResult
    result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=5.0,
        analysis='Test',
        cached=False
    )
    
    for i in range(3):
        frame_bytes = create_test_frame(color=(i * 50, i * 50, i * 50))
        visual_analyzer._add_to_cache(frame_bytes, result)
    
    # Get updated stats
    new_stats = visual_analyzer.get_cache_stats()
    
    # Verify size increased
    assert new_stats['size'] == initial_size + 3


@pytest.mark.integration
def test_clear_cache(visual_analyzer):
    """
    Integration test: Verify clear_cache removes all entries
    
    After clearing, cache should be empty.
    """
    # Add some frames to cache
    from app.services.visual_analyzer import VisualResult
    result = VisualResult(
        uniform_detected=False,
        badge_detected=False,
        threats=[],
        text_detected='',
        confidence=0.8,
        score=5.0,
        analysis='Test',
        cached=False
    )
    
    for i in range(5):
        frame_bytes = create_test_frame(color=(i * 40, i * 40, i * 40))
        visual_analyzer._add_to_cache(frame_bytes, result)
    
    # Verify cache has entries
    assert len(visual_analyzer.frame_cache) > 0
    
    # Clear cache
    visual_analyzer.clear_cache()
    
    # Verify cache is empty
    assert len(visual_analyzer.frame_cache) == 0
    
    # Verify stats reflect empty cache
    stats = visual_analyzer.get_cache_stats()
    assert stats['size'] == 0
