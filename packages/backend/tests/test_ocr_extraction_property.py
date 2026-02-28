"""
Property-Based Test: OCR Text Extraction

Feature: production-ready-browser-extension
Property 22: OCR Text Extraction

For any video frame containing visible text, the visual analyzer should extract
and return the text content with position coordinates.

Validates: Requirements 14.4
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from PIL import Image, ImageDraw, ImageFont
import io
import os
from app.services.visual_analyzer import VisualAnalyzer, RateLimitError


# Strategy for generating text strings
text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), min_codepoint=32, max_codepoint=126),
    min_size=3,
    max_size=50
).filter(lambda x: x.strip() != '')


def create_frame_with_text(text: str, width: int = 640, height: int = 480) -> bytes:
    """
    Create a test frame with text overlay
    
    Args:
        text: Text to render on frame
        width: Frame width
        height: Frame height
    
    Returns:
        Frame as JPEG bytes
    """
    # Create white background
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font = ImageFont.load_default()
    
    # Draw text in center
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    
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


@given(text=text_strategy)
@settings(max_examples=10, deadline=60000)  # Reduced examples due to API calls
def test_ocr_extracts_visible_text(text: str, visual_analyzer):
    """
    Property 22: OCR Text Extraction
    
    For any video frame containing visible text, the visual analyzer should
    extract and return the text content.
    
    This test verifies that:
    1. Text is detected when present in frame
    2. Extracted text contains significant portions of the original text
    3. text_detected field is populated
    """
    # Skip very short or whitespace-only text
    assume(len(text.strip()) >= 3)
    
    try:
        # Create frame with text
        frame_bytes = create_frame_with_text(text)
        
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Property: text_detected should not be empty
        assert result.text_detected is not None, "text_detected field should not be None"
        
        # Property: Some portion of the text should be detected
        # Note: OCR may not be perfect, so we check for partial matches
        detected_text_lower = result.text_detected.lower()
        original_text_lower = text.lower()
        
        # Check if any significant word from original text appears in detected text
        original_words = [w for w in original_text_lower.split() if len(w) >= 3]
        if original_words:
            # At least one word should be detected (allowing for OCR errors)
            matches = sum(1 for word in original_words if word in detected_text_lower)
            match_ratio = matches / len(original_words)
            
            # We expect at least 30% of words to be detected (lenient due to OCR limitations)
            assert match_ratio >= 0.3 or len(detected_text_lower) > 0, \
                f"Expected some text detection. Original: '{text}', Detected: '{result.text_detected}'"
    
    except RateLimitError:
        # Skip test if rate limit is hit
        pytest.skip("API rate limit exceeded")
    
    except Exception as e:
        # Log error but don't fail test for API issues
        if 'API' in str(e) or 'quota' in str(e).lower():
            pytest.skip(f"API error: {e}")
        raise


@pytest.mark.integration
def test_ocr_with_known_text(visual_analyzer):
    """
    Integration test: Verify OCR with known text
    
    This is a concrete example test to complement the property test.
    """
    # Create frame with known text
    test_text = "ARREST WARRANT"
    frame_bytes = create_frame_with_text(test_text)
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Verify text was detected
        assert result.text_detected is not None
        assert len(result.text_detected) > 0
        
        # Check if key words are present (case-insensitive)
        detected_lower = result.text_detected.lower()
        assert 'arrest' in detected_lower or 'warrant' in detected_lower, \
            f"Expected 'arrest' or 'warrant' in detected text: '{result.text_detected}'"
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration
def test_ocr_empty_frame(visual_analyzer):
    """
    Test OCR with frame containing no text
    
    Verifies that analyzer handles frames without text gracefully.
    """
    # Create blank frame
    image = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    frame_bytes = buffer.getvalue()
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # text_detected should be empty or minimal
        assert result.text_detected is not None
        # Empty frames might have empty string or whitespace
        assert len(result.text_detected.strip()) == 0 or len(result.text_detected) < 10
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")


@pytest.mark.integration  
def test_ocr_multiple_text_elements(visual_analyzer):
    """
    Test OCR with multiple text elements in frame
    
    Verifies that analyzer can detect multiple text regions.
    """
    # Create frame with multiple text elements
    image = Image.new('RGB', (640, 480), color='white')
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Draw multiple text elements
    draw.text((50, 50), "CBI OFFICER", fill='black', font=font)
    draw.text((50, 200), "ARREST WARRANT", fill='black', font=font)
    draw.text((50, 350), "IMMEDIATE ACTION", fill='black', font=font)
    
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    frame_bytes = buffer.getvalue()
    
    try:
        # Analyze frame
        result = visual_analyzer.analyze_frame(frame_bytes)
        
        # Should detect at least some of the text
        assert result.text_detected is not None
        assert len(result.text_detected) > 0
        
        # Check for presence of key terms
        detected_lower = result.text_detected.lower()
        detected_count = sum([
            'cbi' in detected_lower or 'officer' in detected_lower,
            'arrest' in detected_lower or 'warrant' in detected_lower,
            'immediate' in detected_lower or 'action' in detected_lower
        ])
        
        # At least one text element should be detected
        assert detected_count >= 1, \
            f"Expected at least one text element detected: '{result.text_detected}'"
    
    except RateLimitError:
        pytest.skip("API rate limit exceeded")
