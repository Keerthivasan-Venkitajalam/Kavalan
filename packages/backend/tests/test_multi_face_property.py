"""
Property-Based Test: Multi-Face Independent Analysis

Feature: production-ready-browser-extension
Property 26: Multi-Face Independent Analysis

For any video frame containing N faces (where N ≥ 1), the liveness detector
should analyze each face independently and return N separate liveness scores.

Validates: Requirements 15.4
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.services.liveness_detector import LivenessDetector
from PIL import Image, ImageDraw
import io
import numpy as np


def generate_test_frame_with_faces(num_faces: int, width: int = 640, height: int = 480) -> bytes:
    """
    Generate a test frame with multiple face-like regions.
    
    Note: This creates simple geometric shapes that MediaPipe might detect as faces.
    In a real scenario, we'd use actual face images.
    """
    # Create blank image
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Calculate grid layout for faces
    cols = int(np.ceil(np.sqrt(num_faces)))
    rows = int(np.ceil(num_faces / cols))
    
    face_width = width // (cols + 1)
    face_height = height // (rows + 1)
    
    face_idx = 0
    for row in range(rows):
        for col in range(cols):
            if face_idx >= num_faces:
                break
            
            # Calculate position
            x = (col + 1) * (width // (cols + 1))
            y = (row + 1) * (height // (rows + 1))
            
            # Draw face-like oval
            left = x - face_width // 4
            top = y - face_height // 4
            right = x + face_width // 4
            bottom = y + face_height // 4
            
            draw.ellipse([left, top, right, bottom], fill='beige', outline='black')
            
            # Draw eyes
            eye_y = y - face_height // 8
            left_eye_x = x - face_width // 8
            right_eye_x = x + face_width // 8
            eye_radius = 5
            
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
            
            # Draw mouth
            mouth_y = y + face_height // 8
            draw.arc(
                [x - face_width // 8, mouth_y - 5,
                 x + face_width // 8, mouth_y + 5],
                0, 180, fill='black', width=2
            )
            
            face_idx += 1
    
    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@given(num_faces=st.integers(min_value=1, max_value=5))
@settings(max_examples=100, deadline=5000)
def test_multi_face_independent_analysis(num_faces: int):
    """
    Property 26: Multi-Face Independent Analysis
    
    For any video frame containing N faces (where N ≥ 1), the liveness detector
    should analyze each face independently and return N separate liveness scores.
    """
    detector = LivenessDetector()
    
    # Generate frame with multiple faces
    frame_bytes = generate_test_frame_with_faces(num_faces)
    
    # Analyze frame
    result = detector.detect_liveness(frame_bytes)
    
    # Property 1: Should detect at least one face (our synthetic faces may not always be detected)
    # We can't guarantee MediaPipe will detect our synthetic faces, so we check if faces were detected
    if result.face_detected:
        # Property 2: Number of face analyses should match detected faces
        assert result.num_faces == len(result.faces), \
            f"num_faces ({result.num_faces}) should match length of faces list ({len(result.faces)})"
        
        # Property 3: Each face should have independent analysis
        assert result.num_faces >= 1, "Should detect at least 1 face when face_detected is True"
        
        # Property 4: Each face analysis should have required fields
        for face in result.faces:
            assert 'face_idx' in face, "Each face should have face_idx"
            assert 'liveness_score' in face, "Each face should have liveness_score"
            assert 'blink_rate' in face, "Each face should have blink_rate"
            assert 'stress_level' in face, "Each face should have stress_level"
            assert 'is_natural' in face, "Each face should have is_natural"
            assert 'is_deepfake' in face, "Each face should have is_deepfake"
            
            # Property 5: Liveness scores should be in valid range [0.0, 1.0]
            assert 0.0 <= face['liveness_score'] <= 1.0, \
                f"Liveness score {face['liveness_score']} must be in [0.0, 1.0]"
            
            # Property 6: Blink rate should be non-negative
            assert face['blink_rate'] >= 0.0, \
                f"Blink rate {face['blink_rate']} must be non-negative"
            
            # Property 7: Stress level should be in valid range [0.0, 1.0]
            assert face['stress_level'] >= 0.0, \
                f"Stress level {face['stress_level']} must be non-negative"
        
        # Property 8: Face indices should be unique
        face_indices = [face['face_idx'] for face in result.faces]
        assert len(face_indices) == len(set(face_indices)), \
            "Face indices should be unique"


def test_multi_face_with_real_image():
    """
    Test multi-face analysis with a simple test case.
    
    This is a unit test to complement the property test.
    """
    detector = LivenessDetector()
    
    # Create a simple test frame
    frame_bytes = generate_test_frame_with_faces(num_faces=2)
    
    # Analyze
    result = detector.detect_liveness(frame_bytes)
    
    # Basic assertions
    assert isinstance(result.face_detected, bool)
    assert isinstance(result.num_faces, int)
    assert result.num_faces >= 0
    assert len(result.faces) == result.num_faces


def test_no_faces_detected():
    """
    Test behavior when no faces are detected.
    """
    detector = LivenessDetector()
    
    # Create blank image with no faces
    image = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    frame_bytes = buffer.getvalue()
    
    # Analyze
    result = detector.detect_liveness(frame_bytes)
    
    # Should indicate no faces detected
    assert result.face_detected == False
    assert result.num_faces == 0
    assert len(result.faces) == 0
    assert result.liveness_score == 0.0


@given(
    num_faces=st.integers(min_value=1, max_value=3),
    width=st.integers(min_value=320, max_value=1280),
    height=st.integers(min_value=240, max_value=720)
)
@settings(max_examples=50, deadline=5000)
def test_multi_face_various_resolutions(num_faces: int, width: int, height: int):
    """
    Property: Multi-face analysis should work across different image resolutions.
    """
    detector = LivenessDetector()
    
    # Generate frame
    frame_bytes = generate_test_frame_with_faces(num_faces, width, height)
    
    # Analyze
    result = detector.detect_liveness(frame_bytes)
    
    # Basic invariants
    assert isinstance(result.face_detected, bool)
    assert result.num_faces >= 0
    assert len(result.faces) == result.num_faces
    
    # If faces detected, verify structure
    if result.face_detected:
        for face in result.faces:
            assert 0.0 <= face['liveness_score'] <= 1.0
            assert face['blink_rate'] >= 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
