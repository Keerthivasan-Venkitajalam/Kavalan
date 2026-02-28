"""Minimal test to check pytest discovery"""
from app.utils.media_compressor import MediaCompressor, compress_media, decompress_media


def test_basic_compression():
    """Basic compression test"""
    compressor = MediaCompressor()
    data = b"Hello World" * 100
    compressed, ratio = compressor.compress(data)
    decompressed = compressor.decompress(compressed)
    assert decompressed == data
    assert ratio > 0


from hypothesis import given, strategies as st, settings


@given(data=st.binary(min_size=100, max_size=1000))
@settings(max_examples=10, deadline=None)
def test_property_roundtrip(data: bytes):
    """Property test: compression roundtrip preserves data"""
    compressor = MediaCompressor()
    compressed, ratio = compressor.compress(data)
    decompressed = compressor.decompress(compressed)
    assert decompressed == data



def repetitive_data_strategy(min_size: int = 1000, max_size: int = 10000):
    """Generate repetitive data that compresses well"""
    return st.builds(
        lambda pattern, count: pattern * count,
        pattern=st.binary(min_size=1, max_size=100),
        count=st.integers(min_value=max(10, min_size // 100), max_value=max_size // 10)
    )


@given(data=repetitive_data_strategy(min_size=1000, max_size=50000))
@settings(max_examples=100, deadline=None)
def test_property_compression_achieves_minimum_ratio(data: bytes):
    """
    **Property 44: Media Compression Before Transmission**
    
    For any compressible media data (repetitive patterns), compression should
    achieve at least 30% size reduction.
    
    This validates the requirement: "Achieve at least 30% size reduction"
    """
    from hypothesis import assume
    
    # Skip very small data that won't compress well due to gzip overhead
    assume(len(data) >= 100)
    
    compressor = MediaCompressor()
    
    # Compress
    compressed, ratio = compressor.compress(data)
    
    # Property: Compression ratio should be at least 30% for compressible data
    # Note: We use repetitive data which should compress well
    assert ratio >= 0.30, \
        f"Compression ratio {ratio:.1%} is below minimum 30% threshold " \
        f"(original={len(data)} bytes, compressed={len(compressed)} bytes)"
    
    # Property: Compressed size should be smaller than original
    assert len(compressed) < len(data), \
        "Compressed data should be smaller than original"


@given(data=st.binary(min_size=100, max_size=10000))
@settings(max_examples=50, deadline=None)
def test_property_compression_ratio_calculation(data: bytes):
    """
    **Property 44: Media Compression Before Transmission**
    
    For any media data, the compression ratio should be calculated correctly
    as: (original_size - compressed_size) / original_size
    """
    compressor = MediaCompressor()
    original_size = len(data)
    
    # Compress
    compressed, ratio = compressor.compress(data)
    compressed_size = len(compressed)
    
    # Calculate expected ratio
    expected_ratio = (original_size - compressed_size) / original_size
    
    # Property: Reported ratio should match calculated ratio
    assert abs(ratio - expected_ratio) < 0.001, \
        f"Compression ratio mismatch: reported={ratio:.4f}, expected={expected_ratio:.4f}"


@given(data=st.binary(min_size=100, max_size=10000))
@settings(max_examples=50, deadline=None)
def test_property_compress_if_beneficial_threshold(data: bytes):
    """
    **Property 44: Media Compression Before Transmission**
    
    For any media data, compress_if_beneficial should only compress if
    the compression ratio meets the minimum threshold (30%).
    """
    compressor = MediaCompressor()
    result_data, was_compressed, ratio = compressor.compress_if_beneficial(data)
    
    # Property: If compressed, ratio should meet threshold
    if was_compressed:
        assert ratio >= MediaCompressor.MIN_COMPRESSION_RATIO, \
            f"Compressed data should meet {MediaCompressor.MIN_COMPRESSION_RATIO:.0%} threshold, got {ratio:.1%}"
        assert len(result_data) < len(data), \
            "Compressed data should be smaller"
    
    # Property: If not compressed, should return original data
    if not was_compressed:
        assert result_data == data, \
            "If not compressed, should return original data unchanged"
        assert ratio == 0.0, \
            "If not compressed, ratio should be 0.0"


@given(data=st.binary(min_size=100, max_size=10000))
@settings(max_examples=50, deadline=None)
def test_property_compressed_data_is_valid_gzip(data: bytes):
    """
    **Property 44: Media Compression Before Transmission**
    
    For any media data, the compressed output should be valid gzip format
    that can be decompressed by standard gzip tools.
    """
    import gzip
    from io import BytesIO
    
    compressor = MediaCompressor()
    
    # Compress using our compressor
    compressed, ratio = compressor.compress(data)
    
    # Property: Should be decompressible by standard gzip
    try:
        buffer = BytesIO(compressed)
        with gzip.GzipFile(fileobj=buffer, mode='rb') as gz:
            decompressed = gz.read()
        
        assert decompressed == data, \
            "Standard gzip should decompress to original data"
    except Exception as e:
        pytest.fail(f"Compressed data is not valid gzip format: {e}")


@given(data=st.binary(min_size=100, max_size=10000))
@settings(max_examples=50, deadline=None)
def test_property_convenience_functions_match_class(data: bytes):
    """
    **Property 44: Media Compression Before Transmission**
    
    For any media data, the convenience functions (compress_media,
    decompress_media) should produce the same results as the class methods.
    """
    # Use class methods
    compressor = MediaCompressor()
    compressed_class, ratio_class = compressor.compress(data)
    decompressed_class = compressor.decompress(compressed_class)
    
    # Use convenience functions
    compressed_func, ratio_func = compress_media(data)
    decompressed_func = decompress_media(compressed_func)
    
    # Property: Should produce identical results
    assert decompressed_class == data
    assert decompressed_func == data
    assert abs(ratio_class - ratio_func) < 0.001


import pytest
import numpy as np


@pytest.mark.integration
def test_property_compression_meets_requirement_on_real_data():
    """
    **Property 44: Media Compression Before Transmission**
    
    Integration test: Verify that compression meets the 30% requirement
    on realistic media data patterns.
    """
    compressor = MediaCompressor()
    
    # Test case 1: Simulated audio with patterns (not pure random)
    # Create audio with some repetition to simulate real audio patterns
    base_pattern = np.array([100, -100, 50, -50] * 1000, dtype=np.int16)
    audio_data = base_pattern.tobytes()
    
    compressed_audio, audio_ratio = compressor.compress(audio_data)
    assert audio_ratio >= 0.30, \
        f"Audio compression should achieve 30%, got {audio_ratio:.1%}"
    
    # Test case 2: Simulated video frame (640x480 RGB with some repetition)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:240, :, :] = 100  # Half the frame is uniform
    frame[240:, :, :] = np.random.randint(0, 256, (240, 640, 3), dtype=np.uint8)
    frame_data = frame.tobytes()
    
    compressed_frame, frame_ratio = compressor.compress(frame_data)
    assert frame_ratio >= 0.30, \
        f"Video frame compression should achieve 30%, got {frame_ratio:.1%}"
    
    # Test case 3: Text-like data (transcripts)
    text_data = b"This is a sample transcript. " * 100
    
    compressed_text, text_ratio = compressor.compress(text_data)
    assert text_ratio >= 0.30, \
        f"Text compression should achieve 30%, got {text_ratio:.1%}"
