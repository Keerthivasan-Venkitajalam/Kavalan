"""
Unit tests for media compression utility
"""
import pytest
from app.utils.media_compressor import MediaCompressor, compress_media, decompress_media


class TestMediaCompressor:
    """Test MediaCompressor class"""
    
    def test_initialization_default_level(self):
        """Test compressor initializes with default compression level"""
        compressor = MediaCompressor()
        assert compressor.compression_level == MediaCompressor.DEFAULT_COMPRESSION_LEVEL
    
    def test_initialization_custom_level(self):
        """Test compressor initializes with custom compression level"""
        compressor = MediaCompressor(compression_level=9)
        assert compressor.compression_level == 9
    
    def test_initialization_invalid_level_too_low(self):
        """Test compressor rejects compression level below 1"""
        with pytest.raises(ValueError, match="Compression level must be between 1 and 9"):
            MediaCompressor(compression_level=0)
    
    def test_initialization_invalid_level_too_high(self):
        """Test compressor rejects compression level above 9"""
        with pytest.raises(ValueError, match="Compression level must be between 1 and 9"):
            MediaCompressor(compression_level=10)
    
    def test_compress_empty_data(self):
        """Test compression fails on empty data"""
        compressor = MediaCompressor()
        with pytest.raises(ValueError, match="Cannot compress empty data"):
            compressor.compress(b"")
    
    def test_compress_small_data(self):
        """Test compression of small data"""
        compressor = MediaCompressor()
        data = b"Hello, World!" * 10
        
        compressed, ratio = compressor.compress(data)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) < len(data)
        assert 0 < ratio < 1
    
    def test_compress_large_repetitive_data(self):
        """Test compression achieves good ratio on repetitive data"""
        compressor = MediaCompressor()
        # Highly repetitive data should compress well
        data = b"A" * 10000
        
        compressed, ratio = compressor.compress(data)
        
        assert len(compressed) < len(data)
        assert ratio > 0.9  # Should achieve >90% compression on repetitive data
    
    def test_compress_random_data(self):
        """Test compression on random data (low compression ratio expected)"""
        compressor = MediaCompressor()
        # Random data doesn't compress well
        import os
        data = os.urandom(1000)
        
        compressed, ratio = compressor.compress(data)
        
        # Random data may not compress much, but should not fail
        assert isinstance(compressed, bytes)
        # Random data may expand due to gzip overhead (negative ratio is OK)
    
    def test_decompress_empty_data(self):
        """Test decompression fails on empty data"""
        compressor = MediaCompressor()
        with pytest.raises(ValueError, match="Cannot decompress empty data"):
            compressor.decompress(b"")
    
    def test_decompress_invalid_data(self):
        """Test decompression fails on invalid gzip data"""
        compressor = MediaCompressor()
        with pytest.raises(ValueError, match="Invalid compressed data"):
            compressor.decompress(b"not gzip data")
    
    def test_compress_decompress_roundtrip(self):
        """Test compression and decompression round-trip preserves data"""
        compressor = MediaCompressor()
        original_data = b"This is test audio/video data" * 100
        
        # Compress
        compressed, ratio = compressor.compress(original_data)
        
        # Decompress
        decompressed = compressor.decompress(compressed)
        
        # Should match original
        assert decompressed == original_data
    
    def test_compress_if_beneficial_high_compression(self):
        """Test compress_if_beneficial returns compressed data when ratio is good"""
        compressor = MediaCompressor()
        # Repetitive data compresses well
        data = b"ABCD" * 1000
        
        result_data, was_compressed, ratio = compressor.compress_if_beneficial(data)
        
        assert was_compressed is True
        assert ratio >= MediaCompressor.MIN_COMPRESSION_RATIO
        assert len(result_data) < len(data)
    
    def test_compress_if_beneficial_low_compression(self):
        """Test compress_if_beneficial returns original data when ratio is poor"""
        compressor = MediaCompressor()
        # Very small data may not compress well
        data = b"AB"
        
        result_data, was_compressed, ratio = compressor.compress_if_beneficial(data)
        
        # May or may not compress depending on overhead
        if not was_compressed:
            assert ratio == 0.0
            assert result_data == data
    
    def test_different_compression_levels(self):
        """Test different compression levels produce different results"""
        data = b"Test data " * 1000
        
        compressor_low = MediaCompressor(compression_level=1)
        compressor_high = MediaCompressor(compression_level=9)
        
        compressed_low, ratio_low = compressor_low.compress(data)
        compressed_high, ratio_high = compressor_high.compress(data)
        
        # Higher compression level should achieve better ratio
        assert ratio_high >= ratio_low
        # But both should compress
        assert len(compressed_low) < len(data)
        assert len(compressed_high) < len(data)


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_compress_media_function(self):
        """Test compress_media convenience function"""
        data = b"Test media data" * 100
        
        compressed, ratio = compress_media(data)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) < len(data)
        assert ratio > 0
    
    def test_decompress_media_function(self):
        """Test decompress_media convenience function"""
        data = b"Test media data" * 100
        
        # Compress first
        compressed, _ = compress_media(data)
        
        # Decompress
        decompressed = decompress_media(compressed)
        
        assert decompressed == data
    
    def test_convenience_functions_roundtrip(self):
        """Test convenience functions preserve data in round-trip"""
        original = b"Audio/Video data sample" * 200
        
        compressed, ratio = compress_media(original)
        decompressed = decompress_media(compressed)
        
        assert decompressed == original
        assert ratio > 0


class TestCompressionRatios:
    """Test compression ratio calculations"""
    
    def test_compression_ratio_calculation(self):
        """Test compression ratio is calculated correctly"""
        compressor = MediaCompressor()
        data = b"X" * 1000
        
        compressed, ratio = compressor.compress(data)
        
        expected_ratio = (len(data) - len(compressed)) / len(data)
        assert abs(ratio - expected_ratio) < 0.001  # Floating point tolerance
    
    def test_minimum_compression_ratio_threshold(self):
        """Test minimum compression ratio threshold is enforced"""
        compressor = MediaCompressor()
        
        # Test with data that should meet threshold
        good_data = b"AAAA" * 1000
        _, was_compressed, ratio = compressor.compress_if_beneficial(good_data)
        
        if was_compressed:
            assert ratio >= MediaCompressor.MIN_COMPRESSION_RATIO


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_compress_single_byte(self):
        """Test compression of single byte"""
        compressor = MediaCompressor()
        data = b"A"
        
        compressed, ratio = compressor.compress(data)
        
        # Single byte may not compress (gzip overhead)
        assert isinstance(compressed, bytes)
        # Ratio may be negative due to overhead
    
    def test_compress_large_data(self):
        """Test compression of large data (simulating video frame)"""
        compressor = MediaCompressor()
        # Simulate 640x480 RGB frame
        data = b"X" * (640 * 480 * 3)
        
        compressed, ratio = compressor.compress(data)
        
        assert len(compressed) < len(data)
        assert ratio > 0
    
    def test_multiple_compress_decompress_cycles(self):
        """Test multiple compression/decompression cycles"""
        compressor = MediaCompressor()
        original = b"Cycle test data" * 50
        
        # Compress and decompress multiple times
        data = original
        for _ in range(3):
            compressed, _ = compressor.compress(data)
            data = compressor.decompress(compressed)
        
        # Should still match original
        assert data == original
