"""
Property-Based Test: Consecutive Frame Deduplication

Feature: production-ready-browser-extension
Property 43: Consecutive Frame Deduplication

**Validates: Requirements 19.2**

For any sequence of consecutive video frames where adjacent frames have
similarity > 0.95, the visual analyzer should skip analysis for the similar
frames and reuse the previous frame's result.

This property ensures:
1. Similar consecutive frames (similarity > 0.95) are deduplicated
2. Different consecutive frames (similarity ≤ 0.95) are analyzed separately
3. Deduplication tracking updates correctly as frames change
4. Deduplicated results preserve all fields from the original analysis
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from PIL import Image
import io
import numpy as np
from app.services.visual_analyzer import VisualAnalyzer, VisualResult
from unittest.mock import patch, MagicMock
from typing import List, Tuple


def create_frame_from_array(arr: np.ndarray) -> bytes:
    """Convert numpy array to JPEG bytes"""
    # Ensure array is in valid range
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    
    # Create image
    if len(arr.shape) == 2:
        # Grayscale
        image = Image.fromarray(arr, mode='L')
    else:
        # RGB
        image = Image.fromarray(arr, mode='RGB')
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def create_test_frame(width: int = 64, height: int = 64, color: Tuple[int, int, int] = (128, 128, 128)) -> bytes:
    """Create a test frame with specified dimensions and color"""
    image = Image.new('RGB', (width, height), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def add_noise_to_frame(frame_bytes: bytes, noise_level: int) -> bytes:
    """Add random noise to a frame"""
    # Load image
    image = Image.open(io.BytesIO(frame_bytes))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to array
    arr = np.array(image)
    
    # Add noise
    noise = np.random.randint(-noise_level, noise_level + 1, arr.shape, dtype=np.int16)
    noisy_arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Convert back to bytes
    return create_frame_from_array(noisy_arr)


@pytest.fixture
def visual_analyzer():
    """Create visual analyzer instance for testing"""
    return VisualAnalyzer(api_key='test-api-key')


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    import json
    return json.dumps({
        'uniform_detected': True,
        'badge_detected': False,
        'threats': ['legal document'],
        'text_detected': 'Police Investigation',
        'confidence': 0.9,
        'analysis': 'Uniform detected in frame'
    })


# Strategy for generating frame colors
frame_color_strategy = st.tuples(
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255)
)


@given(
    color1=frame_color_strategy,
    color2=frame_color_strategy
)
@settings(
    max_examples=50, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_similar_consecutive_frames_deduplicated(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any two consecutive frames with similarity > 0.95, the second frame
    should be deduplicated and reuse the first frame's analysis result.
    
    This property verifies that:
    1. First frame is analyzed normally
    2. Similar second frame (similarity > 0.95) is deduplicated
    3. API is only called once for similar consecutive frames
    4. Deduplicated result preserves all fields from original
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create two frames
    frame1_bytes = create_test_frame(color=color1)
    frame2_bytes = create_test_frame(color=color2)
    
    # Calculate similarity
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    
    # Only test when frames are similar (similarity > 0.95)
    assume(similarity > 0.95)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        initial_call_count = mock_generate.call_count
        
        # Analyze second similar frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Property: API should NOT be called again (deduplication occurred)
        assert mock_generate.call_count == initial_call_count, \
            f"API should not be called for similar frame (similarity={similarity:.3f})"
        
        # Property: Second result should be marked as cached
        assert result2.cached == True, "Deduplicated result should be marked as cached"
        
        # Property: All fields should be preserved
        assert result2.uniform_detected == result1.uniform_detected
        assert result2.badge_detected == result1.badge_detected
        assert result2.threats == result1.threats
        assert result2.text_detected == result1.text_detected
        assert result2.confidence == result1.confidence
        assert result2.score == result1.score
        assert result2.analysis == result1.analysis


@given(
    base_color=frame_color_strategy,
    noise_level=st.integers(min_value=1, max_value=5)
)
@settings(
    max_examples=50, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_slight_noise_still_deduplicated(
    base_color: Tuple[int, int, int],
    noise_level: int,
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any frame with slight noise added (noise_level ≤ 5), the noisy frame
    should still be deduplicated as it will have similarity > 0.95.
    
    This tests that minor variations (camera noise, compression artifacts)
    don't prevent deduplication.
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create base frame
    frame1_bytes = create_test_frame(color=base_color)
    
    # Create slightly noisy version
    frame2_bytes = add_noise_to_frame(frame1_bytes, noise_level)
    
    # Verify frames are different but similar
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    
    # Only test when similarity is high enough
    assume(similarity > 0.95)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        initial_call_count = mock_generate.call_count
        
        # Analyze noisy frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Property: Should be deduplicated despite noise
        assert mock_generate.call_count == initial_call_count, \
            f"Noisy frame should be deduplicated (similarity={similarity:.3f}, noise={noise_level})"
        assert result2.cached == True


@given(
    color1=frame_color_strategy,
    color2=frame_color_strategy
)
@settings(
    max_examples=50, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_different_consecutive_frames_not_deduplicated(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any two consecutive frames with similarity ≤ 0.95, both frames
    should be analyzed separately (no deduplication).
    
    This ensures that significantly different frames are not incorrectly
    deduplicated.
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create two frames
    frame1_bytes = create_test_frame(color=color1)
    frame2_bytes = create_test_frame(color=color2)
    
    # Calculate similarity
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    
    # Only test when frames are different (similarity ≤ 0.95)
    assume(similarity <= 0.95)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        initial_call_count = mock_generate.call_count
        
        # Analyze second different frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Property: API SHOULD be called again (no deduplication)
        assert mock_generate.call_count == initial_call_count + 1, \
            f"API should be called for different frame (similarity={similarity:.3f})"
        
        # Property: First result should not be cached (fresh analysis)
        assert result1.cached == False, "First result should not be cached"


@given(
    colors=st.lists(
        frame_color_strategy,
        min_size=3,
        max_size=10
    )
)
@settings(
    max_examples=30, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_deduplication_sequence(
    colors: List[Tuple[int, int, int]],
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any sequence of frames, deduplication should only compare consecutive
    frames, not all frames in the sequence.
    
    This tests that:
    1. Deduplication tracking updates as frames change
    2. Only the most recent frame is used for comparison
    3. Non-consecutive similar frames are analyzed separately
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create frames from colors
    frames = [create_test_frame(color=color) for color in colors]
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        results = []
        api_calls = []
        
        # Analyze each frame in sequence
        for i, frame_bytes in enumerate(frames):
            initial_calls = mock_generate.call_count
            result = visual_analyzer.analyze_frame(frame_bytes)
            results.append(result)
            
            # Track whether API was called
            api_called = (mock_generate.call_count > initial_calls)
            api_calls.append(api_called)
            
            # Property: First frame should always be analyzed
            if i == 0:
                assert api_called, "First frame should always be analyzed"
                assert result.cached == False
            
            # Property: For subsequent frames, check similarity with previous
            if i > 0:
                similarity = visual_analyzer._calculate_frame_similarity(
                    frames[i-1], frame_bytes
                )
                
                if similarity > 0.95:
                    # Should be deduplicated
                    assert not api_called, \
                        f"Frame {i} should be deduplicated (similarity={similarity:.3f})"
                    assert result.cached == True
                else:
                    # Should be analyzed
                    assert api_called, \
                        f"Frame {i} should be analyzed (similarity={similarity:.3f})"


@given(
    base_color=frame_color_strategy,
    different_color=frame_color_strategy
)
@settings(
    max_examples=30, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_deduplication_resets_on_different_frame(
    base_color: Tuple[int, int, int],
    different_color: Tuple[int, int, int],
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any sequence: similar frame A, different frame B, similar frame C
    (where C is similar to B but not A), deduplication should work correctly:
    - A is analyzed
    - B is analyzed (different from A)
    - C is deduplicated (similar to B)
    
    This tests that deduplication tracking resets when a different frame
    is encountered.
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create frames
    frame_a = create_test_frame(color=base_color)
    frame_b = create_test_frame(color=different_color)
    
    # Ensure frame_b is different from frame_a
    similarity_ab = visual_analyzer._calculate_frame_similarity(frame_a, frame_b)
    assume(similarity_ab <= 0.95)
    
    # Create frame_c similar to frame_b
    frame_c = add_noise_to_frame(frame_b, noise_level=2)
    similarity_bc = visual_analyzer._calculate_frame_similarity(frame_b, frame_c)
    assume(similarity_bc > 0.95)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze frame A
        result_a = visual_analyzer.analyze_frame(frame_a)
        assert mock_generate.call_count == 1
        assert result_a.cached == False
        
        # Analyze frame B (different from A)
        result_b = visual_analyzer.analyze_frame(frame_b)
        assert mock_generate.call_count == 2, "Frame B should be analyzed (different from A)"
        assert result_b.cached == False
        
        # Analyze frame C (similar to B)
        result_c = visual_analyzer.analyze_frame(frame_c)
        assert mock_generate.call_count == 2, "Frame C should be deduplicated (similar to B)"
        assert result_c.cached == True
        
        # Property: Result C should match result B (not A)
        assert result_c.uniform_detected == result_b.uniform_detected
        assert result_c.score == result_b.score


@given(
    color=frame_color_strategy
)
@settings(
    max_examples=30, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_identical_consecutive_frames_always_deduplicated(
    color: Tuple[int, int, int],
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any frame, if the same frame is analyzed twice consecutively,
    the second analysis should always be deduplicated (similarity = 1.0).
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create frame
    frame_bytes = create_test_frame(color=color)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first time
        result1 = visual_analyzer.analyze_frame(frame_bytes)
        assert mock_generate.call_count == 1
        assert result1.cached == False
        
        # Analyze second time (identical frame)
        result2 = visual_analyzer.analyze_frame(frame_bytes)
        
        # Property: Should be deduplicated (identical frames have similarity = 1.0)
        assert mock_generate.call_count == 1, "Identical frame should be deduplicated"
        assert result2.cached == True
        
        # Property: Results should be identical
        assert result2.uniform_detected == result1.uniform_detected
        assert result2.badge_detected == result1.badge_detected
        assert result2.threats == result1.threats
        assert result2.text_detected == result1.text_detected
        assert result2.confidence == result1.confidence
        assert result2.score == result1.score
        assert result2.analysis == result1.analysis


@given(
    color=frame_color_strategy,
    num_repeats=st.integers(min_value=2, max_value=10)
)
@settings(
    max_examples=20, 
    deadline=None, 
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
)
def test_property_multiple_identical_frames_deduplicated(
    color: Tuple[int, int, int],
    num_repeats: int,
    visual_analyzer,
    mock_gemini_response
):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    For any frame repeated N times consecutively, only the first frame
    should be analyzed, and all subsequent frames should be deduplicated.
    """
    # Reset analyzer state for clean test
    visual_analyzer.clear_cache()
    visual_analyzer.last_frame_bytes = None
    visual_analyzer.last_frame_result = None
    
    # Create frame
    frame_bytes = create_test_frame(color=color)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        results = []
        
        # Analyze same frame multiple times
        for i in range(num_repeats):
            result = visual_analyzer.analyze_frame(frame_bytes)
            results.append(result)
        
        # Property: API should only be called once
        assert mock_generate.call_count == 1, \
            f"API should only be called once for {num_repeats} identical frames"
        
        # Property: First result should not be cached, rest should be
        assert results[0].cached == False, "First result should not be cached"
        for i in range(1, num_repeats):
            assert results[i].cached == True, f"Result {i} should be cached"
        
        # Property: All results should be identical
        for i in range(1, num_repeats):
            assert results[i].score == results[0].score
            assert results[i].confidence == results[0].confidence
            assert results[i].uniform_detected == results[0].uniform_detected


@pytest.mark.integration
def test_property_deduplication_threshold_boundary(visual_analyzer, mock_gemini_response):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    Test the exact boundary of the similarity threshold (0.95).
    
    - Similarity = 0.95: Should NOT deduplicate (threshold is >0.95)
    - Similarity > 0.95: Should deduplicate
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        
        # Test at exactly 0.95 (should NOT deduplicate)
        with patch.object(visual_analyzer, '_calculate_frame_similarity', return_value=0.95):
            frame2_bytes = create_test_frame(color=(101, 101, 101))
            result2 = visual_analyzer.analyze_frame(frame2_bytes)
            
            # Property: At exactly 0.95, should NOT deduplicate
            assert mock_generate.call_count == 2, "Should not deduplicate at similarity=0.95"
            assert result2.cached == False
        
        # Test at 0.951 (should deduplicate)
        with patch.object(visual_analyzer, '_calculate_frame_similarity', return_value=0.951):
            frame3_bytes = create_test_frame(color=(102, 102, 102))
            result3 = visual_analyzer.analyze_frame(frame3_bytes)
            
            # Property: Above 0.95, should deduplicate
            assert mock_generate.call_count == 2, "Should deduplicate at similarity=0.951"
            assert result3.cached == True


@pytest.mark.integration
def test_property_deduplication_with_hash_cache_interaction(visual_analyzer, mock_gemini_response):
    """
    **Property 43: Consecutive Frame Deduplication**
    
    Test that frame deduplication works correctly alongside hash-based caching.
    
    Deduplication (similarity-based) should be checked before hash cache.
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    frame2_bytes = add_noise_to_frame(frame1_bytes, noise_level=2)
    
    # Verify frames are similar
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    assert similarity > 0.95
    
    # Note: JPEG compression may make frames identical even with noise
    # This is acceptable - we're testing the deduplication logic
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        
        # Analyze similar frame (should use deduplication or hash cache)
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        assert mock_generate.call_count == 1, "Should use deduplication or hash cache"
        assert result2.cached == True
        
        # Now analyze frame1 again (should use hash cache)
        result3 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1, "Should use hash cache"
        assert result3.cached == True
