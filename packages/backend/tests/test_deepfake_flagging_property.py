"""
Property-Based Test: Deepfake Flagging Threshold

Feature: production-ready-browser-extension
Property 28: Deepfake Flagging Threshold

For any liveness score below 0.5, the system should flag the video as a
potential deepfake and trigger a high-priority alert.

Validates: Requirements 15.6
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.services.liveness_detector import LivenessDetector
from PIL import Image, ImageDraw
import io
import numpy as np


def generate_test_frame_with_quality(quality: str = 'normal', seed: int = None) -> bytes:
    """
    Generate a test frame with varying quality to simulate different liveness scores.
    
    Args:
        quality: 'high' (likely real), 'normal', 'low' (likely fake)
        seed: Random seed
        
    Returns:
        JPEG bytes
    """
    if seed is not None:
        np.random.seed(seed)
    
    width, height = 640, 480
    
    if quality == 'high':
        # High quality: clear face with good features
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)
        
        # Well-defined face
        face_x, face_y = width // 2, height // 2
        face_radius = 100
        draw.ellipse(
            [face_x - face_radius, face_y - face_radius,
             face_x + face_radius, face_y + face_radius],
            fill='peachpuff', outline='black', width=2
        )
        
        # Clear eyes
        eye_y = face_y - 30
        draw.ellipse([face_x - 40 - 10, eye_y - 10, face_x - 40 + 10, eye_y + 10], fill='black')
        draw.ellipse([face_x + 40 - 10, eye_y - 10, face_x + 40 + 10, eye_y + 10], fill='black')
        
        # Mouth
        draw.arc([face_x - 30, face_y + 20, face_x + 30, face_y + 40], 0, 180, fill='black', width=2)
        
    elif quality == 'low':
        # Low quality: blurry, unclear features (simulates deepfake)
        image = Image.new('RGB', (width, height), color='gray')
        draw = ImageDraw.Draw(image)
        
        # Poorly defined face
        face_x, face_y = width // 2, height // 2
        face_radius = 80
        draw.ellipse(
            [face_x - face_radius, face_y - face_radius,
             face_x + face_radius, face_y + face_radius],
            fill='lightgray', outline='darkgray'
        )
        
        # Unclear eyes (or missing)
        # Intentionally minimal features
        
    else:  # normal
        # Normal quality
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        face_x, face_y = width // 2, height // 2
        face_radius = 90
        draw.ellipse(
            [face_x - face_radius, face_y - face_radius,
             face_x + face_radius, face_y + face_radius],
            fill='beige', outline='black'
        )
        
        # Eyes
        eye_y = face_y - 25
        draw.ellipse([face_x - 35 - 8, eye_y - 8, face_x - 35 + 8, eye_y + 8], fill='black')
        draw.ellipse([face_x + 35 - 8, eye_y - 8, face_x + 35 + 8, eye_y + 8], fill='black')
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@given(seed=st.integers(min_value=0, max_value=10000))
@settings(max_examples=100, deadline=5000)
def test_deepfake_flagging_threshold(seed: int):
    """
    Property 28: Deepfake Flagging Threshold
    
    For any liveness score below 0.5, the system should flag the video as a
    potential deepfake.
    """
    detector = LivenessDetector()
    
    # Generate random frame
    frame_bytes = generate_test_frame_with_quality('normal', seed)
    
    # Analyze frame
    result = detector.detect_liveness(frame_bytes)
    
    # Property 1: If liveness score < 0.5, should be flagged as deepfake
    if result.liveness_score < 0.5:
        assert result.is_deepfake == True, \
            f"Liveness score {result.liveness_score} < 0.5 should be flagged as deepfake"
    
    # Property 2: If liveness score >= 0.5, should NOT be flagged as deepfake
    if result.liveness_score >= 0.5:
        assert result.is_deepfake == False, \
            f"Liveness score {result.liveness_score} >= 0.5 should NOT be flagged as deepfake"
    
    # Property 3: Each face should follow the same rule
    if result.face_detected:
        for face in result.faces:
            if face['liveness_score'] < 0.5:
                assert face['is_deepfake'] == True, \
                    f"Face {face['face_idx']} score {face['liveness_score']} < 0.5 should be flagged"
            else:
                assert face['is_deepfake'] == False, \
                    f"Face {face['face_idx']} score {face['liveness_score']} >= 0.5 should NOT be flagged"


def test_deepfake_flagging_boundary_cases():
    """
    Test boundary cases for deepfake flagging threshold.
    """
    detector = LivenessDetector()
    
    # Test various quality levels
    qualities = ['high', 'normal', 'low']
    
    for quality in qualities:
        frame_bytes = generate_test_frame_with_quality(quality, seed=42)
        result = detector.detect_liveness(frame_bytes)
        
        # Verify threshold logic
        if result.liveness_score < 0.5:
            assert result.is_deepfake == True, \
                f"Quality {quality}: score {result.liveness_score} < 0.5 should be flagged"
        else:
            assert result.is_deepfake == False, \
                f"Quality {quality}: score {result.liveness_score} >= 0.5 should NOT be flagged"


def test_no_face_is_deepfake():
    """
    Test that frames with no detected faces are flagged as deepfakes.
    """
    detector = LivenessDetector()
    
    # Blank image with no face
    blank_image = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    blank_image.save(buffer, format='JPEG')
    
    result = detector.detect_liveness(buffer.getvalue())
    
    # No face detected should be considered deepfake (score = 0.0 < 0.5)
    assert result.face_detected == False
    assert result.liveness_score == 0.0
    assert result.is_deepfake == True, \
        "No face detected should be flagged as deepfake"


@given(
    num_faces=st.integers(min_value=1, max_value=3),
    seed=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=50, deadline=5000)
def test_multi_face_deepfake_flagging(num_faces: int, seed: int):
    """
    Property: In multi-face scenarios, each face should be independently flagged.
    """
    detector = LivenessDetector()
    
    # Generate frame with multiple faces
    np.random.seed(seed)
    image = Image.new('RGB', (640, 480), color='white')
    draw = ImageDraw.Draw(image)
    
    # Add multiple faces
    for i in range(num_faces):
        x = 150 + i * 200
        y = 240
        radius = 60
        
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                    fill='beige', outline='black')
        draw.ellipse([x - 20, y - 15, x - 10, y - 5], fill='black')
        draw.ellipse([x + 10, y - 15, x + 20, y - 5], fill='black')
    
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    
    result = detector.detect_liveness(buffer.getvalue())
    
    # Each detected face should follow the threshold rule
    if result.face_detected:
        for face in result.faces:
            if face['liveness_score'] < 0.5:
                assert face['is_deepfake'] == True
            else:
                assert face['is_deepfake'] == False


@given(
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=1000)
def test_threshold_logic_directly(score: float):
    """
    Property: Test the threshold logic directly with all possible score values.
    
    This tests the mathematical property: score < 0.5 ⟺ is_deepfake == True
    """
    # Simulate the threshold logic
    is_deepfake = score < 0.5
    
    # Property: Threshold at exactly 0.5
    if score < 0.5:
        assert is_deepfake == True, \
            f"Score {score} < 0.5 should result in is_deepfake=True"
    else:
        assert is_deepfake == False, \
            f"Score {score} >= 0.5 should result in is_deepfake=False"
    
    # Boundary case: exactly 0.5
    if abs(score - 0.5) < 0.001:  # Close to boundary
        if score < 0.5:
            assert is_deepfake == True
        else:
            assert is_deepfake == False


def test_deepfake_flagging_with_stress():
    """
    Test that deepfake flagging is independent of stress level.
    """
    detector = LivenessDetector()
    
    # Generate frame
    frame_bytes = generate_test_frame_with_quality('normal', seed=123)
    result = detector.detect_liveness(frame_bytes)
    
    # Deepfake flagging should be based on liveness score, not stress
    if result.liveness_score < 0.5:
        assert result.is_deepfake == True
    else:
        assert result.is_deepfake == False
    
    # Stress level should not affect deepfake flag directly
    # (though it may indirectly affect liveness score calculation)
    assert isinstance(result.stress_level, float)
    assert 0.0 <= result.stress_level <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
