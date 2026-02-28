"""
Property-Based Test: Visual Confidence Scoring

Feature: production-ready-browser-extension
Property 23: Visual Confidence Scoring

For any visual threat detection (uniform, badge, weapon), the analyzer should
generate a confidence score in the range [0.0, 1.0].

Validates: Requirements 14.5
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from PIL import Image, ImageDraw, ImageFont
import io
import os
from app.services.visual_analyzer import VisualAnalyzer, RateLimitError


def create_test_frame(width: int = 640, height: int = 480, content: str = 'blank') -> bytes:
    """
    Create a test frame with various content
    
    Args:
        width: Frame width
        height: Frame height
        content: Type of content ('blank', 'uniform', 'badge', 'threat')
    
    Returns:
        Frame as JPEG bytes
    """
    # Create white background
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font = ImageFont.load_default()
    
    if content == 'uniform':
        # Draw text suggesting uniform
        draw.text((50, 200), "POLICE UNIFORM", fill='black', font=font)
    elif content == 'badge':
        # Draw text suggesting badge
        draw.text((50, 200), "CBI BADGE", fill='black', font=font)
    elif content == 'threat':
        # Draw text suggesting threat
        draw.text((50, 200), "ARREST WARRANT", fill='black', font=font)
    # else: blank frame
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@pytest.fixture
def visual_analyzer():
    """Create visual analyzer instance for testing"""
    api_key = os.getenv('GEMINI_API_KEY', 'test-api-key')
    
    # Skip test if no API key
    if api_key == 'test-api-key':
        pytest.skip("GEMINI_API_KEY not set")
    
    return VisualAnalyzer(api_key=api_key)


@given(
    content_type=st.sampled_from(['blank', 'uniform', 'badge', 'threat']),
    width=st.integers(min_value=320, max_value=1920),
    height=st.integers(min_value=240, max_value=1080)
)
@settings(max_examples=10, deadline=60000)  # Reduced examples due to API calls
def test_confidence_score_in_valid_range(content_type: str, width: int, height: int, visual_analyzer):
    """
    Property 23: Visual Confidence Scoring
    
    For any visual threat detection, the analyzer should generate a confidence
    score in the range [0.0, 1.0].
    
    This test verifies that:
    1. Confidence score is always in [0.0, 1.0]
    2. Confidence score is a valid float
    3. Result contains confidence field
    """
    try:
        # Create test frame
        frame_bytes = create_test_frame(width, height, content_type)
        
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Property 1: Confidence field must exist
        assert hasattr(result, 'confidence'), "Result must have confidence field"
        assert result.confidence is not None, "Confidence must not be None"
        
        # Property 2: Confidence must be a float
        assert isinstance(result.confidence, (float, int)), \
            f"Confidence must be numeric, got {type(result.confidence)}"
        
        # Property 3: Confidence must be in range [0.0, 1.0]
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} must be in range [0.0, 1.0]"
    
    except RateLimitError:
        # Skip test if rate limit is hit
        pytest.skip("API rate limit exceeded")
    
    except Exception as e:
        # Log error but don't fail test for API issues
        if 'API' in str(e) or 'quota' in str(e).lower():
            pytest.skip(f"API error: {e}")
        raise


@pytest.mark.integration
def test_confidence_with_uniform_detection(visual_analyzer):
    """
    Integration test: Verify confidence scoring with uniform detection
    
    When a uniform is detected, confidence should be reasonable.
    """
    # Create frame with uniform text
    frame_bytes = create_test_frame(content='uniform')
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # If uniform is detected, confidence should be reasonable (> 0.3)
        if result.uniform_detected:
            assert result.confidence >= 0.3, \
                f"Confidence {result.confidence} too low for uniform detection"
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration
def test_confidence_with_badge_detection(visual_analyzer):
    """
    Integration test: Verify confidence scoring with badge detection
    
    When a badge is detected, confidence should be reasonable.
    """
    # Create frame with badge text
    frame_bytes = create_test_frame(content='badge')
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # If badge is detected, confidence should be reasonable (> 0.3)
        if result.badge_detected:
            assert result.confidence >= 0.3, \
                f"Confidence {result.confidence} too low for badge detection"
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration
def test_confidence_with_threat_detection(visual_analyzer):
    """
    Integration test: Verify confidence scoring with threat detection
    
    When threats are detected, confidence should be reasonable.
    """
    # Create frame with threat text
    frame_bytes = create_test_frame(content='threat')
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # If threats are detected, confidence should be reasonable (> 0.3)
        if result.threats:
            assert result.confidence >= 0.3, \
                f"Confidence {result.confidence} too low for threat detection"
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration
def test_confidence_with_blank_frame(visual_analyzer):
    """
    Integration test: Verify confidence scoring with blank frame
    
    Even blank frames should have valid confidence scores.
    """
    # Create blank frame
    frame_bytes = create_test_frame(content='blank')
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # Blank frames might have lower confidence or high confidence
        # depending on how certain the model is that nothing is there
        assert isinstance(result.confidence, (float, int))
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration
def test_visual_score_in_valid_range(visual_analyzer):
    """
    Integration test: Verify visual threat score is in valid range [0.0, 10.0]
    
    This complements the confidence test by checking the threat score.
    """
    # Create frame with threat content
    frame_bytes = create_test_frame(content='threat')
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify score is in valid range [0.0, 10.0]
        assert 0.0 <= result.score <= 10.0, \
            f"Visual threat score {result.score} must be in range [0.0, 10.0]"
        
        # Verify score is numeric
        assert isinstance(result.score, (float, int))
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@given(
    uniform=st.booleans(),
    badge=st.booleans(),
    threat_count=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=20)
def test_calculate_score_range(uniform: bool, badge: bool, threat_count: int):
    """
    Property test: Verify calculate_score always returns value in [0.0, 10.0]
    
    This tests the scoring logic directly without API calls.
    """
    # Create mock analysis
    analysis = {
        'uniform_detected': uniform,
        'badge_detected': badge,
        'threats': ['threat'] * threat_count,
        'text_detected': 'test text',
        'confidence': 0.8
    }
    
    # Create analyzer (no API key needed for this test)
    analyzer = VisualAnalyzer(api_key='test-key')
    
    # Calculate score
    score = analyzer.calculate_score(analysis)
    
    # Property: Score must be in range [0.0, 10.0]
    assert 0.0 <= score <= 10.0, \
        f"Score {score} must be in range [0.0, 10.0]"
    
    # Property: Score must be numeric
    assert isinstance(score, (float, int))


@given(
    uniform=st.booleans(),
    badge=st.booleans()
)
@settings(max_examples=20)
def test_score_increases_with_detections(uniform: bool, badge: bool):
    """
    Property test: Verify score increases with more detections
    
    More threat indicators should result in higher scores.
    """
    # Create analyzer
    analyzer = VisualAnalyzer(api_key='test-key')
    
    # Analysis with no detections
    analysis_none = {
        'uniform_detected': False,
        'badge_detected': False,
        'threats': [],
        'text_detected': '',
        'confidence': 0.8
    }
    score_none = analyzer.calculate_score(analysis_none)
    
    # Analysis with some detections
    analysis_some = {
        'uniform_detected': uniform,
        'badge_detected': badge,
        'threats': [],
        'text_detected': '',
        'confidence': 0.8
    }
    score_some = analyzer.calculate_score(analysis_some)
    
    # Property: More detections should result in higher or equal score
    if uniform or badge:
        assert score_some >= score_none, \
            "Score should increase with detections"
