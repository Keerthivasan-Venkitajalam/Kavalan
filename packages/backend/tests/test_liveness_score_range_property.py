"""
Property-Based Test: Liveness Score Range Constraint

Feature: production-ready-browser-extension
Property 27: Liveness Score Range Constraint

For any face analyzed by the liveness detector, the liveness score must be
in the range [0.0, 1.0], where 0.0 indicates fake and 1.0 indicates real.

Validates: Requirements 15.5
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.liveness_detector import LivenessDetector
from PIL import Image, ImageDraw
import io
import numpy as np


def generate_random_frame(width: int = 640, height: int = 480, seed: int = None) -> bytes:
    """
    Generate a random test frame.
    
    Args:
        width: Frame width
        height: Frame height
        seed: Random seed for reproducibility
        
    Returns:
        JPEG bytes
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Create random image
    random_array = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    image = Image.fromarray(random_array, 'RGB')
    
    # Optionally add face-like features
    draw = ImageDraw.Draw(image)
    
    # Draw a simple face
    face_x = width // 2
    face_y = height // 2
    face_radius = min(width, height) // 4
    
    # Face oval
    draw.ellipse(
        [face_x - face_radius, face_y - face_radius,
         face_x + face_radius, face_y + face_radius],
        fill='beige', outline='black'
    )
    
    # Eyes
    eye_y = face_y - face_radius // 3
    left_eye_x = face_x - face_radius // 3
    right_eye_x = face_x + face_radius // 3
    eye_radius = 8
    
    draw.ellipse(
        [left_eye_x - eye_radius, eye_y - eye_radius,
         left_eye_x + eye_radius, eye_y + eye_radius],
        fill='black'
    )
    draw.ellipse(
        [right_eye_x - eye_radius, eye_y - eye_radius,
         right_eye_x + eye_radius, eye_y + eye_radius],
        fill='black'
    )
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@given(
    width=st.integers(min_value=320, max_value=1280),
    height=st.integers(min_value=240, max_value=720),
    seed=st.integers(min_value=0, max_value=10000)
)
@settings(max_examples=100, deadline=5000)
def test_liveness_score_range_constraint(width: int, height: int, seed: int):
    """
    Property 27: Liveness Score Range Constraint
    
    For any face analyzed by the liveness detector, the liveness score must be
    in the range [0.0, 1.0].
    """
    detector = LivenessDetector()
    
    # Generate random frame
    frame_bytes = generate_random_frame(width, height, seed)
    
    # Analyze frame
    result = detector.detect_liveness(frame_bytes)
    
    # Property 1: Overall liveness score must be in [0.0, 1.0]
    assert 0.0 <= result.liveness_score <= 1.0, \
        f"Overall liveness score {result.liveness_score} must be in [0.0, 1.0]"
    
    # Property 2: If faces detected, each face score must be in [0.0, 1.0]
    if result.face_detected:
        for face in result.faces:
            assert 0.0 <= face['liveness_score'] <= 1.0, \
                f"Face {face['face_idx']} liveness score {face['liveness_score']} must be in [0.0, 1.0]"
    
    # Property 3: Stress level must be in [0.0, 1.0]
    assert 0.0 <= result.stress_level <= 1.0, \
        f"Stress level {result.stress_level} must be in [0.0, 1.0]"
    
    # Property 4: Blink rate must be non-negative
    assert result.blink_rate >= 0.0, \
        f"Blink rate {result.blink_rate} must be non-negative"
    
    # Property 5: If no faces detected, liveness score should be 0.0
    if not result.face_detected:
        assert result.liveness_score == 0.0, \
            "Liveness score should be 0.0 when no faces detected"


@given(num_iterations=st.integers(min_value=1, max_value=10))
@settings(max_examples=50, deadline=5000)
def test_liveness_score_consistency(num_iterations: int):
    """
    Property: Analyzing the same frame multiple times should yield consistent scores.
    """
    detector = LivenessDetector()
    
    # Generate a single frame
    frame_bytes = generate_random_frame(seed=42)
    
    # Analyze multiple times
    scores = []
    for _ in range(num_iterations):
        result = detector.detect_liveness(frame_bytes)
        scores.append(result.liveness_score)
    
    # All scores should be in valid range
    for score in scores:
        assert 0.0 <= score <= 1.0, f"Score {score} must be in [0.0, 1.0]"
    
    # Scores should be consistent (same frame = same score)
    if len(scores) > 1:
        # Allow small floating point differences
        score_variance = np.var(scores)
        assert score_variance < 0.01, \
            f"Score variance {score_variance} too high for same frame"


def test_liveness_score_edge_cases():
    """
    Test edge cases for liveness score range.
    """
    detector = LivenessDetector()
    
    # Test 1: Blank white image (no face)
    blank_image = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    blank_image.save(buffer, format='JPEG')
    
    result = detector.detect_liveness(buffer.getvalue())
    assert 0.0 <= result.liveness_score <= 1.0
    assert result.liveness_score == 0.0  # No face = 0.0 score
    
    # Test 2: Blank black image (no face)
    black_image = Image.new('RGB', (640, 480), color='black')
    buffer = io.BytesIO()
    black_image.save(buffer, format='JPEG')
    
    result = detector.detect_liveness(buffer.getvalue())
    assert 0.0 <= result.liveness_score <= 1.0
    assert result.liveness_score == 0.0  # No face = 0.0 score
    
    # Test 3: Very small image
    tiny_image = Image.new('RGB', (32, 32), color='gray')
    buffer = io.BytesIO()
    tiny_image.save(buffer, format='JPEG')
    
    result = detector.detect_liveness(buffer.getvalue())
    assert 0.0 <= result.liveness_score <= 1.0
    
    # Test 4: Very large image
    large_frame = generate_random_frame(width=1920, height=1080)
    result = detector.detect_liveness(large_frame)
    assert 0.0 <= result.liveness_score <= 1.0


@given(
    brightness=st.integers(min_value=0, max_value=255),
    contrast=st.floats(min_value=0.5, max_value=2.0)
)
@settings(max_examples=50, deadline=5000)
def test_liveness_score_under_varying_conditions(brightness: int, contrast: float):
    """
    Property: Liveness score should remain in valid range under varying image conditions.
    """
    detector = LivenessDetector()
    
    # Create image with specific brightness
    image = Image.new('RGB', (640, 480), color=(brightness, brightness, brightness))
    
    # Add a face
    draw = ImageDraw.Draw(image)
    draw.ellipse([200, 150, 440, 330], fill='beige', outline='black')
    draw.ellipse([260, 200, 280, 220], fill='black')  # Left eye
    draw.ellipse([360, 200, 380, 220], fill='black')  # Right eye
    
    # Apply contrast adjustment
    image_array = np.array(image).astype(float)
    image_array = ((image_array - 128) * contrast + 128).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(image_array)
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    
    # Analyze
    result = detector.detect_liveness(buffer.getvalue())
    
    # Score must be in valid range regardless of image conditions
    assert 0.0 <= result.liveness_score <= 1.0, \
        f"Liveness score {result.liveness_score} must be in [0.0, 1.0] " \
        f"(brightness={brightness}, contrast={contrast})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
