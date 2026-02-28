"""
Redis-based caching for threat patterns

Implements:
- Frequency tracking for pattern access
- Automatic caching of frequently accessed patterns (>10 accesses/minute)
- TTL-based cache expiration (5 minutes)
"""
import json
import logging
import time
from typing import Dict, List, Optional
from redis import Redis
from app.config import settings

logger = logging.getLogger(__name__)


class PatternCache:
    """
    Redis-based cache for threat patterns with frequency tracking
    
    Caches patterns that are accessed more than 10 times per minute.
    Cached patterns expire after 5 minutes (TTL).
    """
    
    # Cache configuration
    FREQUENCY_THRESHOLD = 10  # Accesses per minute to trigger caching
    CACHE_TTL = 300  # 5 minutes in seconds
    FREQUENCY_WINDOW = 60  # 1 minute window for frequency tracking
    
    # Redis key prefixes
    PATTERN_KEY_PREFIX = "pattern:cache:"
    FREQUENCY_KEY_PREFIX = "pattern:freq:"
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize pattern cache
        
        Args:
            redis_client: Redis client instance. If None, creates new client.
        """
        if redis_client is None:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        else:
            self.redis = redis_client
        
        logger.info("Pattern cache initialized")
    
    def _get_pattern_key(self, category: str, language: str = 'en') -> str:
        """Generate Redis key for cached pattern"""
        return f"{self.PATTERN_KEY_PREFIX}{language}:{category}"
    
    def _get_frequency_key(self, category: str, language: str = 'en') -> str:
        """Generate Redis key for frequency tracking"""
        return f"{self.FREQUENCY_KEY_PREFIX}{language}:{category}"
    
    def _track_access(self, category: str, language: str = 'en') -> int:
        """
        Track pattern access and return access count in current window
        
        Args:
            category: Pattern category (e.g., 'authority', 'coercion')
            language: Language code
        
        Returns:
            Number of accesses in the current minute window
        """
        freq_key = self._get_frequency_key(category, language)
        current_time = time.time()
        
        try:
            # Add current access timestamp to sorted set
            self.redis.zadd(freq_key, {str(current_time): current_time})
            
            # Remove old entries outside the window
            cutoff_time = current_time - self.FREQUENCY_WINDOW
            self.redis.zremrangebyscore(freq_key, 0, cutoff_time)
            
            # Set expiration on frequency key
            self.redis.expire(freq_key, self.FREQUENCY_WINDOW)
            
            # Count accesses in current window
            access_count = self.redis.zcard(freq_key)
            
            return access_count
        
        except Exception as e:
            logger.error(f"Failed to track access for {category}: {e}")
            return 0
    
    def get_patterns(
        self,
        category: str,
        language: str = 'en',
        fallback_patterns: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """
        Get patterns from cache if available
        
        Args:
            category: Pattern category
            language: Language code
            fallback_patterns: Patterns to cache if not in cache
        
        Returns:
            List of patterns if cached, None otherwise
        """
        pattern_key = self._get_pattern_key(category, language)
        
        try:
            # Try to get from cache
            cached_data = self.redis.get(pattern_key)
            
            if cached_data:
                patterns = json.loads(cached_data)
                logger.debug(f"Cache hit for {category} ({language})")
                return patterns
            
            logger.debug(f"Cache miss for {category} ({language})")
            return None
        
        except Exception as e:
            logger.error(f"Failed to get patterns from cache: {e}")
            return None
    
    def cache_patterns(
        self,
        category: str,
        patterns: List[str],
        language: str = 'en',
        force: bool = False
    ) -> bool:
        """
        Cache patterns if frequency threshold is met
        
        Args:
            category: Pattern category
            patterns: List of patterns to cache
            language: Language code
            force: If True, cache regardless of frequency
        
        Returns:
            True if patterns were cached, False otherwise
        """
        # Track access and get frequency
        access_count = self._track_access(category, language)
        
        # Check if frequency threshold is met
        if not force and access_count < self.FREQUENCY_THRESHOLD:
            logger.debug(
                f"Pattern {category} ({language}) not cached: "
                f"access count {access_count} < threshold {self.FREQUENCY_THRESHOLD}"
            )
            return False
        
        pattern_key = self._get_pattern_key(category, language)
        
        try:
            # Serialize patterns to JSON
            patterns_json = json.dumps(patterns)
            
            # Cache with TTL
            self.redis.setex(pattern_key, self.CACHE_TTL, patterns_json)
            
            logger.info(
                f"Cached {len(patterns)} patterns for {category} ({language}) "
                f"with TTL {self.CACHE_TTL}s (access count: {access_count})"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to cache patterns: {e}")
            return False
    
    def get_or_cache_patterns(
        self,
        category: str,
        patterns: List[str],
        language: str = 'en'
    ) -> List[str]:
        """
        Get patterns from cache or cache them if frequently accessed
        
        This is the main method to use for pattern access with automatic caching.
        
        Args:
            category: Pattern category
            patterns: Original patterns (used if not cached)
            language: Language code
        
        Returns:
            Patterns (either from cache or original)
        """
        # Try to get from cache
        cached_patterns = self.get_patterns(category, language)
        
        if cached_patterns is not None:
            return cached_patterns
        
        # Not in cache, track access and potentially cache
        self.cache_patterns(category, patterns, language)
        
        # Return original patterns
        return patterns
    
    def clear_cache(self, category: Optional[str] = None, language: Optional[str] = None):
        """
        Clear cached patterns
        
        Args:
            category: If specified, clear only this category. Otherwise clear all.
            language: If specified, clear only this language. Otherwise clear all.
        """
        try:
            if category and language:
                # Clear specific pattern
                pattern_key = self._get_pattern_key(category, language)
                freq_key = self._get_frequency_key(category, language)
                self.redis.delete(pattern_key, freq_key)
                logger.info(f"Cleared cache for {category} ({language})")
            else:
                # Clear all patterns
                pattern_keys = self.redis.keys(f"{self.PATTERN_KEY_PREFIX}*")
                freq_keys = self.redis.keys(f"{self.FREQUENCY_KEY_PREFIX}*")
                
                if pattern_keys:
                    self.redis.delete(*pattern_keys)
                if freq_keys:
                    self.redis.delete(*freq_keys)
                
                logger.info(f"Cleared all cached patterns ({len(pattern_keys)} entries)")
        
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            pattern_keys = self.redis.keys(f"{self.PATTERN_KEY_PREFIX}*")
            freq_keys = self.redis.keys(f"{self.FREQUENCY_KEY_PREFIX}*")
            
            stats = {
                'cached_patterns': len(pattern_keys),
                'tracked_frequencies': len(freq_keys),
                'cache_ttl': self.CACHE_TTL,
                'frequency_threshold': self.FREQUENCY_THRESHOLD,
                'frequency_window': self.FREQUENCY_WINDOW
            }
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis.close()
            logger.info("Pattern cache connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")
