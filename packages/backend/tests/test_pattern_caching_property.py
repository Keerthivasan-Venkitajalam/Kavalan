"""
Property-Based Test: Threat Pattern Caching

Feature: production-ready-browser-extension
Property 42: Threat Pattern Caching

**Validates: Requirements 19.1**

For any frequently accessed threat pattern (accessed > 10 times in 1 minute),
the pattern should be cached in Redis with a TTL of 5 minutes.

This property test verifies:
1. Patterns accessed >10 times/minute are automatically cached
2. Cached patterns have correct TTL (5 minutes = 300 seconds)
3. Patterns accessed <10 times/minute are NOT cached
4. Cache retrieval returns correct patterns
5. Frequency tracking works correctly across time windows
"""
import pytest
import time
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock
from app.utils.pattern_cache import PatternCache


# Strategy for generating pattern categories
pattern_categories = st.sampled_from([
    'authority', 'coercion', 'financial', 'crime', 'urgency'
])

# Strategy for generating language codes
language_codes = st.sampled_from([
    'en', 'hi', 'ta', 'te', 'ml', 'kn'
])

# Strategy for generating pattern lists
pattern_lists = st.lists(
    st.text(min_size=2, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    min_size=1,
    max_size=20
)

# Strategy for access counts
access_counts = st.integers(min_value=1, max_value=50)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client that simulates real Redis behavior"""
    redis_mock = Mock()
    
    # Internal state for simulation
    redis_mock._sorted_sets = {}  # For frequency tracking (zadd, zcard, etc.)
    redis_mock._cache = {}  # For pattern cache (get, setex)
    redis_mock._ttls = {}  # Track TTLs
    
    def zadd_impl(key, mapping):
        """Simulate zadd - add to sorted set"""
        if key not in redis_mock._sorted_sets:
            redis_mock._sorted_sets[key] = {}
        redis_mock._sorted_sets[key].update(mapping)
        return len(mapping)
    
    def zremrangebyscore_impl(key, min_score, max_score):
        """Simulate zremrangebyscore - remove by score range"""
        if key not in redis_mock._sorted_sets:
            return 0
        
        to_remove = [k for k, v in redis_mock._sorted_sets[key].items() 
                     if min_score <= v <= max_score]
        for k in to_remove:
            del redis_mock._sorted_sets[key][k]
        return len(to_remove)
    
    def zcard_impl(key):
        """Simulate zcard - count elements in sorted set"""
        if key not in redis_mock._sorted_sets:
            return 0
        return len(redis_mock._sorted_sets[key])
    
    def expire_impl(key, seconds):
        """Simulate expire - set TTL"""
        redis_mock._ttls[key] = seconds
        return True
    
    def get_impl(key):
        """Simulate get - retrieve cached value"""
        return redis_mock._cache.get(key)
    
    def setex_impl(key, seconds, value):
        """Simulate setex - set with expiration"""
        redis_mock._cache[key] = value
        redis_mock._ttls[key] = seconds
        return True
    
    def delete_impl(*keys):
        """Simulate delete - remove keys"""
        count = 0
        for key in keys:
            if key in redis_mock._cache:
                del redis_mock._cache[key]
                count += 1
            if key in redis_mock._sorted_sets:
                del redis_mock._sorted_sets[key]
                count += 1
            if key in redis_mock._ttls:
                del redis_mock._ttls[key]
        return count
    
    def keys_impl(pattern):
        """Simulate keys - find keys matching pattern"""
        import re
        # Convert Redis pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        regex = re.compile(regex_pattern)
        
        all_keys = set(redis_mock._cache.keys()) | set(redis_mock._sorted_sets.keys())
        return [k for k in all_keys if regex.match(k)]
    
    # Attach implementations
    redis_mock.zadd.side_effect = zadd_impl
    redis_mock.zremrangebyscore.side_effect = zremrangebyscore_impl
    redis_mock.zcard.side_effect = zcard_impl
    redis_mock.expire.side_effect = expire_impl
    redis_mock.get.side_effect = get_impl
    redis_mock.setex.side_effect = setex_impl
    redis_mock.delete.side_effect = delete_impl
    redis_mock.keys.side_effect = keys_impl
    redis_mock.close = Mock()
    
    return redis_mock


@pytest.fixture
def pattern_cache(mock_redis):
    """Create a PatternCache instance with mock Redis"""
    return PatternCache(redis_client=mock_redis)


@given(
    category=pattern_categories,
    language=language_codes,
    patterns=pattern_lists,
    access_count=st.integers(min_value=11, max_value=50)
)
@settings(max_examples=50)
def test_frequent_patterns_are_cached(
    category: str,
    language: str,
    patterns: list,
    access_count: int
):
    """
    Property 42: Threat Pattern Caching (Frequent Access)
    
    For any pattern accessed more than 10 times in 1 minute,
    the pattern should be cached in Redis.
    
    This test verifies:
    - Patterns with access_count > 10 are cached
    - cache_patterns returns True for frequent patterns
    """
    # Assume valid inputs
    assume(len(patterns) > 0)
    assume(access_count > 10)
    
    # Create mock Redis and cache
    mock_redis = Mock()
    mock_redis._sorted_sets = {}
    mock_redis._cache = {}
    mock_redis._ttls = {}
    
    def zcard_impl(key):
        return access_count  # Simulate frequent access
    
    def setex_impl(key, seconds, value):
        mock_redis._cache[key] = value
        mock_redis._ttls[key] = seconds
        return True
    
    mock_redis.zadd = Mock(return_value=1)
    mock_redis.zremrangebyscore = Mock(return_value=0)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.zcard = Mock(side_effect=zcard_impl)
    mock_redis.setex = Mock(side_effect=setex_impl)
    mock_redis.close = Mock()
    
    cache = PatternCache(redis_client=mock_redis)
    
    # Cache patterns
    result = cache.cache_patterns(category, patterns, language)
    
    # Property: Frequent patterns should be cached
    assert result is True, f"Patterns with {access_count} accesses should be cached"
    
    # Verify setex was called (pattern was stored)
    assert mock_redis.setex.called, "setex should be called to cache patterns"
    
    # Verify TTL is correct (5 minutes = 300 seconds)
    call_args = mock_redis.setex.call_args
    if call_args:
        ttl_used = call_args[0][1]
        assert ttl_used == 300, f"TTL should be 300 seconds, got {ttl_used}"


@given(
    category=pattern_categories,
    language=language_codes,
    patterns=pattern_lists,
    access_count=st.integers(min_value=1, max_value=9)
)
@settings(max_examples=50)
def test_infrequent_patterns_not_cached(
    category: str,
    language: str,
    patterns: list,
    access_count: int
):
    """
    Property 42: Threat Pattern Caching (Infrequent Access)
    
    For any pattern accessed fewer than 10 times in 1 minute,
    the pattern should NOT be cached in Redis.
    
    This test verifies:
    - Patterns with access_count < 10 are not cached
    - cache_patterns returns False for infrequent patterns
    """
    # Assume valid inputs
    assume(len(patterns) > 0)
    assume(access_count < 10)
    
    # Create mock Redis and cache
    mock_redis = Mock()
    mock_redis._sorted_sets = {}
    mock_redis._cache = {}
    
    def zcard_impl(key):
        return access_count  # Simulate infrequent access
    
    mock_redis.zadd = Mock(return_value=1)
    mock_redis.zremrangebyscore = Mock(return_value=0)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.zcard = Mock(side_effect=zcard_impl)
    mock_redis.setex = Mock()
    mock_redis.close = Mock()
    
    cache = PatternCache(redis_client=mock_redis)
    
    # Try to cache patterns
    result = cache.cache_patterns(category, patterns, language)
    
    # Property: Infrequent patterns should NOT be cached
    assert result is False, f"Patterns with {access_count} accesses should not be cached"
    
    # Verify setex was NOT called
    assert not mock_redis.setex.called, "setex should not be called for infrequent patterns"


@given(
    category=pattern_categories,
    language=language_codes,
    patterns=pattern_lists
)
@settings(max_examples=30)
def test_cache_ttl_is_five_minutes(
    category: str,
    language: str,
    patterns: list
):
    """
    Property 42: Threat Pattern Caching (TTL Verification)
    
    For any cached pattern, the TTL should be exactly 5 minutes (300 seconds).
    
    This test verifies:
    - Cached patterns have TTL = 300 seconds
    - TTL is set correctly via setex
    """
    # Assume valid inputs
    assume(len(patterns) > 0)
    
    # Create mock Redis and cache
    mock_redis = Mock()
    mock_redis._cache = {}
    mock_redis._ttls = {}
    
    def setex_impl(key, seconds, value):
        mock_redis._cache[key] = value
        mock_redis._ttls[key] = seconds
        return True
    
    mock_redis.zadd = Mock(return_value=1)
    mock_redis.zremrangebyscore = Mock(return_value=0)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.zcard = Mock(return_value=15)  # Above threshold
    mock_redis.setex = Mock(side_effect=setex_impl)
    mock_redis.close = Mock()
    
    cache = PatternCache(redis_client=mock_redis)
    
    # Cache patterns (force to ensure caching happens)
    result = cache.cache_patterns(category, patterns, language, force=True)
    
    assert result is True, "Forced caching should succeed"
    
    # Property: TTL should be exactly 300 seconds (5 minutes)
    pattern_key = cache._get_pattern_key(category, language)
    assert pattern_key in mock_redis._ttls, "TTL should be set for cached pattern"
    assert mock_redis._ttls[pattern_key] == 300, "TTL should be 300 seconds (5 minutes)"


@given(
    category=pattern_categories,
    language=language_codes,
    patterns=pattern_lists
)
@settings(max_examples=30)
def test_cached_patterns_retrievable(
    category: str,
    language: str,
    patterns: list
):
    """
    Property 42: Threat Pattern Caching (Retrieval)
    
    For any cached pattern, get_patterns should return the exact same patterns.
    
    This test verifies:
    - Cached patterns can be retrieved
    - Retrieved patterns match original patterns
    """
    # Assume valid inputs
    assume(len(patterns) > 0)
    
    # Create mock Redis and cache
    import json
    mock_redis = Mock()
    mock_redis._cache = {}
    mock_redis._ttls = {}
    
    def setex_impl(key, seconds, value):
        mock_redis._cache[key] = value
        mock_redis._ttls[key] = seconds
        return True
    
    def get_impl(key):
        return mock_redis._cache.get(key)
    
    mock_redis.zadd = Mock(return_value=1)
    mock_redis.zremrangebyscore = Mock(return_value=0)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.zcard = Mock(return_value=15)  # Above threshold
    mock_redis.setex = Mock(side_effect=setex_impl)
    mock_redis.get = Mock(side_effect=get_impl)
    mock_redis.close = Mock()
    
    cache = PatternCache(redis_client=mock_redis)
    
    # Cache patterns
    cache.cache_patterns(category, patterns, language, force=True)
    
    # Retrieve patterns
    retrieved = cache.get_patterns(category, language)
    
    # Property: Retrieved patterns should match original patterns
    assert retrieved is not None, "Should retrieve cached patterns"
    assert retrieved == patterns, "Retrieved patterns should match original patterns"


@pytest.mark.integration
def test_frequency_tracking_over_time(pattern_cache):
    """
    Integration test: Verify frequency tracking works correctly over time
    
    This test simulates multiple accesses over time and verifies:
    - Access count increases with each access
    - Patterns are cached when threshold is reached
    """
    category = 'authority'
    language = 'en'
    patterns = ['CBI', 'NCB', 'RBI', 'ED']
    
    # Simulate multiple accesses
    for i in range(15):
        access_count = pattern_cache._track_access(category, language)
        
        # Access count should increase
        assert access_count == i + 1, f"Access count should be {i + 1}, got {access_count}"
    
    # After 15 accesses, caching should succeed
    result = pattern_cache.cache_patterns(category, patterns, language)
    assert result is True, "Should cache after 15 accesses"
    
    # Verify patterns are in cache
    cached = pattern_cache.get_patterns(category, language)
    assert cached == patterns, "Cached patterns should match original"


@pytest.mark.integration
def test_get_or_cache_patterns_workflow(pattern_cache):
    """
    Integration test: Verify get_or_cache_patterns workflow
    
    This test verifies the complete workflow:
    1. First access: not cached, returns original
    2. Multiple accesses: frequency tracked
    3. After threshold: patterns cached
    4. Subsequent access: returns cached patterns
    """
    category = 'coercion'
    language = 'hi'
    patterns = ['धमकी', 'गिरफ्तारी', 'जेल']
    
    # First few accesses - should return original patterns
    for i in range(5):
        result = pattern_cache.get_or_cache_patterns(category, patterns, language)
        assert result == patterns, "Should return original patterns"
    
    # Access more times to exceed threshold
    for i in range(10):
        result = pattern_cache.get_or_cache_patterns(category, patterns, language)
    
    # Now patterns should be cached
    cached = pattern_cache.get_patterns(category, language)
    assert cached is not None, "Patterns should be cached after threshold"
    assert cached == patterns, "Cached patterns should match original"


@pytest.mark.integration
def test_cache_stats_accuracy(pattern_cache):
    """
    Integration test: Verify cache statistics are accurate
    
    This test verifies:
    - Cache stats reflect actual cache state
    - Stats include correct configuration values
    """
    # Get initial stats
    stats = pattern_cache.get_cache_stats()
    
    assert 'cached_patterns' in stats
    assert 'tracked_frequencies' in stats
    assert 'cache_ttl' in stats
    assert 'frequency_threshold' in stats
    assert 'frequency_window' in stats
    
    # Verify configuration values
    assert stats['cache_ttl'] == 300, "TTL should be 300 seconds"
    assert stats['frequency_threshold'] == 10, "Threshold should be 10 accesses/minute"
    assert stats['frequency_window'] == 60, "Window should be 60 seconds"
    
    initial_cached = stats['cached_patterns']
    
    # Cache some patterns
    pattern_cache.cache_patterns('authority', ['CBI', 'NCB'], 'en', force=True)
    pattern_cache.cache_patterns('coercion', ['arrest', 'jail'], 'en', force=True)
    
    # Get updated stats
    new_stats = pattern_cache.get_cache_stats()
    
    # Verify stats updated
    assert new_stats['cached_patterns'] >= initial_cached + 2, "Should have at least 2 more cached patterns"


@pytest.mark.integration
def test_clear_cache_removes_patterns(pattern_cache):
    """
    Integration test: Verify clear_cache removes cached patterns
    
    This test verifies:
    - Cached patterns can be cleared
    - After clearing, patterns are not in cache
    """
    category = 'financial'
    language = 'en'
    patterns = ['money', 'transfer', 'account', 'bank']
    
    # Cache patterns
    pattern_cache.cache_patterns(category, patterns, language, force=True)
    
    # Verify cached
    cached = pattern_cache.get_patterns(category, language)
    assert cached is not None, "Patterns should be cached"
    
    # Clear specific category
    pattern_cache.clear_cache(category, language)
    
    # Verify cleared
    cached_after = pattern_cache.get_patterns(category, language)
    assert cached_after is None, "Patterns should be cleared from cache"


@pytest.mark.integration
def test_multiple_languages_cached_separately(pattern_cache):
    """
    Integration test: Verify patterns for different languages are cached separately
    
    This test verifies:
    - Same category, different languages have separate cache entries
    - Retrieving one language doesn't affect another
    """
    category = 'authority'
    patterns_en = ['CBI', 'NCB', 'RBI']
    patterns_hi = ['सीबीआई', 'एनसीबी', 'आरबीआई']
    patterns_ta = ['சிபிஐ', 'என்சிபி', 'ஆர்பிஐ']
    
    # Cache patterns for different languages
    pattern_cache.cache_patterns(category, patterns_en, 'en', force=True)
    pattern_cache.cache_patterns(category, patterns_hi, 'hi', force=True)
    pattern_cache.cache_patterns(category, patterns_ta, 'ta', force=True)
    
    # Retrieve each language
    cached_en = pattern_cache.get_patterns(category, 'en')
    cached_hi = pattern_cache.get_patterns(category, 'hi')
    cached_ta = pattern_cache.get_patterns(category, 'ta')
    
    # Verify each language has correct patterns
    assert cached_en == patterns_en, "English patterns should match"
    assert cached_hi == patterns_hi, "Hindi patterns should match"
    assert cached_ta == patterns_ta, "Tamil patterns should match"
    
    # Verify they are different
    assert cached_en != cached_hi, "English and Hindi patterns should be different"
    assert cached_en != cached_ta, "English and Tamil patterns should be different"


@pytest.mark.integration
def test_force_cache_bypasses_frequency_check(pattern_cache):
    """
    Integration test: Verify force=True bypasses frequency threshold
    
    This test verifies:
    - force=True caches patterns regardless of access count
    - Useful for pre-warming cache
    """
    category = 'urgency'
    language = 'en'
    patterns = ['immediately', 'urgent', 'now', 'quickly']
    
    # Cache with force=True (no prior accesses)
    result = pattern_cache.cache_patterns(category, patterns, language, force=True)
    
    assert result is True, "Force caching should succeed"
    
    # Verify patterns are cached
    cached = pattern_cache.get_patterns(category, language)
    assert cached == patterns, "Forced cached patterns should be retrievable"
