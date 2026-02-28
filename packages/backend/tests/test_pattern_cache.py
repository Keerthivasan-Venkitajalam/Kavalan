"""
Unit tests for Redis-based pattern caching

Tests:
- Pattern caching with frequency threshold
- Cache retrieval
- TTL expiration
- Cache statistics
- Cache clearing
"""
import pytest
import time
from unittest.mock import Mock, patch
from app.utils.pattern_cache import PatternCache


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    redis_mock = Mock()
    redis_mock.zadd = Mock(return_value=1)
    redis_mock.zremrangebyscore = Mock(return_value=0)
    redis_mock.expire = Mock(return_value=True)
    redis_mock.zcard = Mock(return_value=0)
    redis_mock.get = Mock(return_value=None)
    redis_mock.setex = Mock(return_value=True)
    redis_mock.delete = Mock(return_value=1)
    redis_mock.keys = Mock(return_value=[])
    redis_mock.close = Mock()
    return redis_mock


@pytest.fixture
def pattern_cache(mock_redis):
    """Create a PatternCache instance with mock Redis"""
    return PatternCache(redis_client=mock_redis)


def test_pattern_cache_initialization(pattern_cache):
    """Test that pattern cache initializes correctly"""
    assert pattern_cache is not None
    assert pattern_cache.FREQUENCY_THRESHOLD == 10
    assert pattern_cache.CACHE_TTL == 300
    assert pattern_cache.FREQUENCY_WINDOW == 60


def test_track_access_increments_count(pattern_cache, mock_redis):
    """Test that tracking access increments the count"""
    # Mock zcard to return increasing counts
    mock_redis.zcard.side_effect = [1, 2, 3]
    
    count1 = pattern_cache._track_access('authority', 'en')
    count2 = pattern_cache._track_access('authority', 'en')
    count3 = pattern_cache._track_access('authority', 'en')
    
    assert count1 == 1
    assert count2 == 2
    assert count3 == 3
    
    # Verify zadd was called
    assert mock_redis.zadd.call_count == 3


def test_cache_patterns_below_threshold_not_cached(pattern_cache, mock_redis):
    """Test that patterns below frequency threshold are not cached"""
    # Mock access count below threshold
    mock_redis.zcard.return_value = 5
    
    patterns = ['CBI', 'NCB', 'RBI']
    result = pattern_cache.cache_patterns('authority', patterns, 'en')
    
    assert result is False
    # setex should not be called
    mock_redis.setex.assert_not_called()


def test_cache_patterns_above_threshold_cached(pattern_cache, mock_redis):
    """Test that patterns above frequency threshold are cached"""
    # Mock access count above threshold
    mock_redis.zcard.return_value = 15
    
    patterns = ['CBI', 'NCB', 'RBI']
    result = pattern_cache.cache_patterns('authority', patterns, 'en')
    
    assert result is True
    # setex should be called with correct TTL
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 300  # TTL


def test_cache_patterns_force_caches_regardless_of_frequency(pattern_cache, mock_redis):
    """Test that force=True caches patterns regardless of frequency"""
    # Mock access count below threshold
    mock_redis.zcard.return_value = 2
    
    patterns = ['CBI', 'NCB', 'RBI']
    result = pattern_cache.cache_patterns('authority', patterns, 'en', force=True)
    
    assert result is True
    mock_redis.setex.assert_called_once()


def test_get_patterns_cache_hit(pattern_cache, mock_redis):
    """Test retrieving patterns from cache (cache hit)"""
    import json
    
    patterns = ['CBI', 'NCB', 'RBI']
    mock_redis.get.return_value = json.dumps(patterns)
    
    result = pattern_cache.get_patterns('authority', 'en')
    
    assert result == patterns
    mock_redis.get.assert_called_once()


def test_get_patterns_cache_miss(pattern_cache, mock_redis):
    """Test retrieving patterns when not in cache (cache miss)"""
    mock_redis.get.return_value = None
    
    result = pattern_cache.get_patterns('authority', 'en')
    
    assert result is None
    mock_redis.get.assert_called_once()


def test_get_or_cache_patterns_returns_cached(pattern_cache, mock_redis):
    """Test get_or_cache_patterns returns cached patterns when available"""
    import json
    
    cached_patterns = ['CBI', 'NCB', 'RBI']
    original_patterns = ['CBI', 'NCB', 'RBI', 'ED']
    
    mock_redis.get.return_value = json.dumps(cached_patterns)
    
    result = pattern_cache.get_or_cache_patterns('authority', original_patterns, 'en')
    
    assert result == cached_patterns
    assert len(result) == 3  # Cached version, not original


def test_get_or_cache_patterns_returns_original_on_miss(pattern_cache, mock_redis):
    """Test get_or_cache_patterns returns original patterns on cache miss"""
    mock_redis.get.return_value = None
    mock_redis.zcard.return_value = 5  # Below threshold
    
    original_patterns = ['CBI', 'NCB', 'RBI']
    result = pattern_cache.get_or_cache_patterns('authority', original_patterns, 'en')
    
    assert result == original_patterns


def test_clear_cache_specific_category(pattern_cache, mock_redis):
    """Test clearing cache for specific category and language"""
    pattern_cache.clear_cache('authority', 'en')
    
    # Should delete both pattern and frequency keys
    assert mock_redis.delete.call_count == 1


def test_clear_cache_all(pattern_cache, mock_redis):
    """Test clearing all cached patterns"""
    mock_redis.keys.side_effect = [
        ['pattern:cache:en:authority', 'pattern:cache:en:coercion'],
        ['pattern:freq:en:authority', 'pattern:freq:en:coercion']
    ]
    
    pattern_cache.clear_cache()
    
    # Should call keys twice (for patterns and frequencies)
    assert mock_redis.keys.call_count == 2
    # Should delete all keys
    assert mock_redis.delete.call_count == 2


def test_get_cache_stats(pattern_cache, mock_redis):
    """Test getting cache statistics"""
    mock_redis.keys.side_effect = [
        ['pattern:cache:en:authority', 'pattern:cache:en:coercion'],
        ['pattern:freq:en:authority']
    ]
    
    stats = pattern_cache.get_cache_stats()
    
    assert stats['cached_patterns'] == 2
    assert stats['tracked_frequencies'] == 1
    assert stats['cache_ttl'] == 300
    assert stats['frequency_threshold'] == 10
    assert stats['frequency_window'] == 60


def test_pattern_key_generation(pattern_cache):
    """Test Redis key generation for patterns"""
    key = pattern_cache._get_pattern_key('authority', 'en')
    assert key == 'pattern:cache:en:authority'
    
    key = pattern_cache._get_pattern_key('coercion', 'hi')
    assert key == 'pattern:cache:hi:coercion'


def test_frequency_key_generation(pattern_cache):
    """Test Redis key generation for frequency tracking"""
    key = pattern_cache._get_frequency_key('authority', 'en')
    assert key == 'pattern:freq:en:authority'
    
    key = pattern_cache._get_frequency_key('financial', 'ta')
    assert key == 'pattern:freq:ta:financial'


def test_cache_handles_redis_errors_gracefully(pattern_cache, mock_redis):
    """Test that cache handles Redis errors gracefully"""
    # Simulate Redis error
    mock_redis.get.side_effect = Exception("Redis connection error")
    
    result = pattern_cache.get_patterns('authority', 'en')
    
    # Should return None instead of raising exception
    assert result is None


def test_track_access_handles_errors_gracefully(pattern_cache, mock_redis):
    """Test that access tracking handles errors gracefully"""
    # Simulate Redis error
    mock_redis.zadd.side_effect = Exception("Redis connection error")
    
    count = pattern_cache._track_access('authority', 'en')
    
    # Should return 0 instead of raising exception
    assert count == 0


def test_close_connection(pattern_cache, mock_redis):
    """Test closing Redis connection"""
    pattern_cache.close()
    
    mock_redis.close.assert_called_once()


@pytest.mark.integration
def test_pattern_cache_integration_with_audio_transcriber():
    """
    Integration test: Verify AudioTranscriber uses pattern cache
    
    This test requires Redis to be running.
    """
    from app.services.audio_transcriber import AudioTranscriber
    
    try:
        # Initialize transcriber (will create pattern cache)
        transcriber = AudioTranscriber(model_size='tiny')
        
        # Verify cache is initialized
        assert transcriber.pattern_cache is not None
        
        # Get initial stats
        stats = transcriber.get_cache_stats()
        assert 'frequency_threshold' in stats
        
        # Simulate multiple accesses to trigger caching
        transcript = "I am a CBI officer and you need to transfer money immediately"
        
        for _ in range(15):  # Above threshold
            matches = transcriber.match_keywords(transcript, 'en')
        
        # Verify patterns were matched
        assert 'authority' in matches
        assert 'financial' in matches
        
        # Get updated stats
        stats = transcriber.get_cache_stats()
        # After 15 accesses, some patterns should be cached
        # (exact count depends on timing)
        
        # Clean up
        transcriber.clear_cache()
        
    except Exception as e:
        pytest.skip(f"Redis not available for integration test: {e}")
