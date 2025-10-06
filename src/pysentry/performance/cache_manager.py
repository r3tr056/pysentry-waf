"""
Multi-level caching system for WAF components.

Provides in-memory and Redis-based caching for blocked IPs, whitelists,
threat intelligence, and ML predictions.
"""

import pickle
from functools import lru_cache
from typing import Optional, Set, Dict, Any, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now(timezone.utc) > expiry


class CacheManager:
    """
    Multi-level cache manager for WAF components.
    
    Provides in-memory caching with LRU eviction and optional Redis backend.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 300,
        max_memory_size: int = 10000
    ):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Optional Redis connection URL
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_memory_size: Maximum number of items in memory cache
        """
        self.default_ttl = default_ttl
        self.max_memory_size = max_memory_size
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Redis client
        self.redis_client = None
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
            except ImportError:
                print("Redis not available, using memory cache only")
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def _evict_if_needed(self):
        """Evict old entries if cache is full."""
        if len(self._memory_cache) >= self.max_memory_size:
            # Remove oldest entries (25% of cache)
            to_remove = self.max_memory_size // 4
            sorted_entries = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1].created_at
            )
            for key, _ in sorted_entries[:to_remove]:
                del self._memory_cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                self.hits += 1
                return entry.value
            else:
                # Remove expired entry
                del self._memory_cache[key]
        
        # Check Redis if available
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.hits += 1
                    decoded_value = pickle.loads(value)
                    # Store in memory cache for faster access
                    self.set(key, decoded_value, ttl=self.default_ttl)
                    return decoded_value
            except Exception as e:
                print(f"Redis get error: {e}")
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        
        # Store in memory cache
        self._evict_if_needed()
        self._memory_cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(timezone.utc),
            ttl_seconds=ttl
        )
        
        # Store in Redis if available
        if self.redis_client:
            try:
                pickled_value = pickle.dumps(value)
                self.redis_client.setex(key, ttl, pickled_value)
            except Exception as e:
                print(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete key from cache."""
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                print(f"Redis delete error: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        self._memory_cache.clear()
        
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                print(f"Redis clear error: {e}")
    
    # WAF-specific cache methods
    
    def get_blocked_ips(self) -> Set[str]:
        """Get cached set of blocked IP addresses."""
        cached = self.get('blocked_ips')
        return cached if cached is not None else set()
    
    def set_blocked_ips(self, ips: Set[str], ttl: int = 300):
        """Cache set of blocked IP addresses."""
        self.set('blocked_ips', ips, ttl=ttl)
    
    def get_whitelist(self) -> Set[str]:
        """Get cached whitelist."""
        cached = self.get('whitelist')
        return cached if cached is not None else set()
    
    def set_whitelist(self, ips: Set[str], ttl: int = 600):
        """Cache whitelist."""
        self.set('whitelist', ips, ttl=ttl)
    
    @lru_cache(maxsize=10000)
    def is_whitelisted(self, ip: str) -> bool:
        """
        Check if IP is whitelisted (with LRU cache).
        
        Args:
            ip: IP address to check
            
        Returns:
            True if whitelisted
        """
        whitelist = self.get_whitelist()
        return ip in whitelist
    
    def cache_threat_prediction(
        self,
        request_signature: str,
        is_threat: bool,
        threat_types: List[str],
        ttl: int = 60
    ):
        """
        Cache threat prediction result.
        
        Args:
            request_signature: Unique signature of the request
            is_threat: Whether threat was detected
            threat_types: List of detected threat types
            ttl: TTL in seconds (default: 1 minute)
        """
        result = {
            'is_threat': is_threat,
            'threat_types': threat_types,
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        self.set(f'prediction:{request_signature}', result, ttl=ttl)
    
    def get_cached_prediction(self, request_signature: str) -> Optional[Dict[str, Any]]:
        """Get cached threat prediction."""
        return self.get(f'prediction:{request_signature}')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'memory_size': len(self._memory_cache),
            'max_memory_size': self.max_memory_size,
            'redis_available': self.redis_client is not None
        }
