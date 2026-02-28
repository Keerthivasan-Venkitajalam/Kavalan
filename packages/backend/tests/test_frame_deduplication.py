"""
Unit Tests: Frame Deduplication

Tests the frame deduplication feature in the Visual Analyzer service.
Verifies that similar consecutive frames (similarity > 0.95) skip analysis.

Validates: Requirements 19.2
"""
import pytest
from PIL import Image
import io
from app.services.visual_analyzer import VisualAnalyzer, VisualResult
from unittest.mock import patch, MagicMock


def create_test_frame(width: int = 640, height: int = 480, color: tuple = (255, 255, 255)) -> bytes:
    """Create a test frame with specified color"""
    image = Image.new('RGB', (width, height), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def create_slightly_different_frame(base_frame_bytes: bytes, noise_level: int = 5) -> bytes:
    """Create a frame that's very similar to the base frame with slight noise"""
    # Load base image
    base_image = Image.open(io.BytesIO(base_frame_bytes))
    
    # Convert to RGB if needed
    if base_image.mode != 'RGB':
        base_image = base_image.convert('RGB')
    
    # Add slight noise
    import numpy as np
    arr = np.array(base_image)
    noise = np.random.randint(-noise_level, noise_level + 1, arr.shape, dtype=np.int16)
    noisy_arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Create new image
    noisy_image = Image.fromarray(noisy_arr)
    buffer = io.BytesIO()
    noisy_image.save(buffer, format='JPEG')
    return buffer.getvalue()


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


def test_first_frame_analyzed_normally(visual_analyzer, mock_gemini_response):
    """
    Test that the first frame is analyzed normally (no deduplication)
    """
    frame_bytes = create_test_frame(color=(100, 100, 100))
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify analysis was performed
        assert mock_generate.called
        assert result.uniform_detected == True
        assert result.cached == False
        
        # Verify last frame was stored
        assert visual_analyzer.last_frame_bytes is not None
        assert visual_analyzer.last_frame_result is not None


def test_identical_consecutive_frames_deduplicated(visual_analyzer, mock_gemini_response):
    """
    Test that identical consecutive frames are deduplicated
    """
    frame_bytes = create_test_frame(color=(100, 100, 100))
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame_bytes)
        assert mock_generate.call_count == 1
        assert result1.cached == False
        
        # Analyze identical second frame
        result2 = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify API was NOT called again (deduplication occurred)
        assert mock_generate.call_count == 1  # Still 1, not 2
        
        # Verify result was deduplicated
        assert result2.cached == True
        assert result2.uniform_detected == result1.uniform_detected
        assert result2.score == result1.score


def test_similar_consecutive_frames_deduplicated(visual_analyzer, mock_gemini_response):
    """
    Test that similar consecutive frames (similarity > 0.95) are deduplicated
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    frame2_bytes = create_slightly_different_frame(frame1_bytes, noise_level=2)
    
    # Verify frames are similar but not identical
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    assert similarity > 0.95, f"Frames should be similar (got {similarity:.3f})"
    assert frame1_bytes != frame2_bytes, "Frames should not be identical"
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        assert result1.cached == False
        
        # Analyze similar second frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Verify API was NOT called again (deduplication occurred)
        assert mock_generate.call_count == 1  # Still 1, not 2
        
        # Verify result was deduplicated
        assert result2.cached == True
        assert result2.uniform_detected == result1.uniform_detected
        assert result2.score == result1.score


def test_different_consecutive_frames_not_deduplicated(visual_analyzer, mock_gemini_response):
    """
    Test that different consecutive frames are NOT deduplicated
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    frame2_bytes = create_test_frame(color=(200, 50, 50))  # Very different
    
    # Verify frames are different
    similarity = visual_analyzer._calculate_frame_similarity(frame1_bytes, frame2_bytes)
    assert similarity < 0.95, f"Frames should be different (got {similarity:.3f})"
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        
        # Analyze different second frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Verify API WAS called again (no deduplication)
        assert mock_generate.call_count == 2
        
        # Both results should not be cached (fresh analysis)
        assert result1.cached == False
        assert result2.cached == False


def test_deduplication_threshold_boundary(visual_analyzer, mock_gemini_response):
    """
    Test deduplication behavior at the similarity threshold boundary (0.95)
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{str(mock_gemini_response).replace("'", '"')}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        
        # Mock similarity calculation to return exactly 0.95
        with patch.object(visual_analyzer, '_calculate_frame_similarity', return_value=0.95):
            frame2_bytes = create_test_frame(color=(101, 101, 101))
            result2 = visual_analyzer.analyze_frame(frame2_bytes)
            
            # At exactly 0.95, should NOT deduplicate (threshold is >0.95)
            assert mock_generate.call_count == 2
        
        # Mock similarity calculation to return 0.951 (just above threshold)
        with patch.object(visual_analyzer, '_calculate_frame_similarity', return_value=0.951):
            frame3_bytes = create_test_frame(color=(102, 102, 102))
            result3 = visual_analyzer.analyze_frame(frame3_bytes)
            
            # Above 0.95, should deduplicate
            assert mock_generate.call_count == 2  # Still 2, not 3
            assert result3.cached == True


def test_deduplication_resets_on_different_frame(visual_analyzer, mock_gemini_response):
    """
    Test that deduplication tracking resets when a different frame is analyzed
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    frame2_bytes = create_test_frame(color=(200, 50, 50))  # Different
    frame3_bytes = create_slightly_different_frame(frame2_bytes, noise_level=1)  # Similar to frame2
    
    # Verify frame3 is similar to frame2
    similarity_2_3 = visual_analyzer._calculate_frame_similarity(frame2_bytes, frame3_bytes)
    assert similarity_2_3 > 0.95, f"Frame 3 should be similar to frame 2 (got {similarity_2_3:.3f})"
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze frame 1
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        assert mock_generate.call_count == 1
        
        # Analyze frame 2 (different from frame 1)
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        assert mock_generate.call_count == 2
        
        # Analyze frame 3 (similar to frame 2, should deduplicate)
        result3 = visual_analyzer.analyze_frame(frame3_bytes)
        assert mock_generate.call_count == 2  # Still 2, deduplicated
        assert result3.cached == True


def test_deduplication_with_no_previous_frame(visual_analyzer, mock_gemini_response):
    """
    Test that deduplication works correctly when there's no previous frame
    """
    frame_bytes = create_test_frame(color=(100, 100, 100))
    
    # Verify no previous frame
    assert visual_analyzer.last_frame_bytes is None
    assert visual_analyzer.last_frame_result is None
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Should analyze normally (no deduplication)
        assert mock_generate.call_count == 1
        assert result.cached == False
        
        # Previous frame should now be set
        assert visual_analyzer.last_frame_bytes is not None
        assert visual_analyzer.last_frame_result is not None


def test_similarity_calculation_accuracy(visual_analyzer):
    """
    Test that frame similarity calculation is accurate
    """
    # Identical frames should have similarity = 1.0
    frame1 = create_test_frame(color=(100, 100, 100))
    similarity_identical = visual_analyzer._calculate_frame_similarity(frame1, frame1)
    assert similarity_identical == 1.0
    
    # Very similar frames should have high similarity
    frame2 = create_slightly_different_frame(frame1, noise_level=2)
    similarity_similar = visual_analyzer._calculate_frame_similarity(frame1, frame2)
    assert similarity_similar > 0.95
    
    # Different frames should have low similarity
    frame3 = create_test_frame(color=(255, 0, 0))
    similarity_different = visual_analyzer._calculate_frame_similarity(frame1, frame3)
    assert similarity_different < 0.95


def test_deduplication_preserves_result_fields(visual_analyzer, mock_gemini_response):
    """
    Test that deduplicated results preserve all fields from the original result
    """
    frame1_bytes = create_test_frame(color=(100, 100, 100))
    frame2_bytes = create_slightly_different_frame(frame1_bytes, noise_level=2)
    
    # Mock the Gemini API call
    with patch.object(visual_analyzer.model, 'generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = f'```json\n{mock_gemini_response}\n```'
        mock_generate.return_value = mock_response
        
        # Analyze first frame
        result1 = visual_analyzer.analyze_frame(frame1_bytes)
        
        # Analyze similar second frame
        result2 = visual_analyzer.analyze_frame(frame2_bytes)
        
        # Verify all fields are preserved
        assert result2.uniform_detected == result1.uniform_detected
        assert result2.badge_detected == result1.badge_detected
        assert result2.threats == result1.threats
        assert result2.text_detected == result1.text_detected
        assert result2.confidence == result1.confidence
        assert result2.score == result1.score
        assert result2.analysis == result1.analysis
        assert result2.cached == True
