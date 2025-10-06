"""
Tests for cache manager.
"""

import pytest
import time
from pysentry.performance.cache_manager import CacheManager, CacheEntry
from datetime import datetime, timedelta, timezone


@pytest.fixture
def cache_manager():
    """Create cache manager for testing."""
    return CacheManager(default_ttl=60, max_memory_size=100)


def test_cache_manager_initialization(cache_manager):
    """Test cache manager initialization."""
    assert cache_manager.default_ttl == 60
    assert cache_manager.max_memory_size == 100
    assert cache_manager.hits == 0
    assert cache_manager.misses == 0


def test_set_and_get(cache_manager):
    """Test basic set and get operations."""
    cache_manager.set('key1', 'value1')
    value = cache_manager.get('key1')
    
    assert value == 'value1'
    assert cache_manager.hits == 1
    assert cache_manager.misses == 0


def test_get_nonexistent_key(cache_manager):
    """Test getting nonexistent key returns None."""
    value = cache_manager.get('nonexistent')
    
    assert value is None
    assert cache_manager.misses == 1


def test_ttl_expiration(cache_manager):
    """Test TTL expiration."""
    cache_manager.set('expiring_key', 'value', ttl=1)
    
    # Should be available immediately
    value = cache_manager.get('expiring_key')
    assert value == 'value'
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired
    value = cache_manager.get('expiring_key')
    assert value is None


def test_cache_eviction(cache_manager):
    """Test cache eviction when full."""
    # Fill cache to capacity
    for i in range(100):
        cache_manager.set(f'key{i}', f'value{i}')
    
    assert len(cache_manager._memory_cache) == 100
    
    # Add one more - should trigger eviction
    cache_manager.set('key100', 'value100')
    
    # Cache should still be at or below max size
    assert len(cache_manager._memory_cache) <= 100


def test_delete(cache_manager):
    """Test cache deletion."""
    cache_manager.set('delete_me', 'value')
    assert cache_manager.get('delete_me') == 'value'
    
    cache_manager.delete('delete_me')
    assert cache_manager.get('delete_me') is None


def test_clear(cache_manager):
    """Test cache clear."""
    cache_manager.set('key1', 'value1')
    cache_manager.set('key2', 'value2')
    
    cache_manager.clear()
    
    assert cache_manager.get('key1') is None
    assert cache_manager.get('key2') is None
    assert len(cache_manager._memory_cache) == 0


def test_blocked_ips_cache(cache_manager):
    """Test blocked IPs caching."""
    blocked_ips = {'192.168.1.1', '10.0.0.1'}
    cache_manager.set_blocked_ips(blocked_ips)
    
    cached_ips = cache_manager.get_blocked_ips()
    assert cached_ips == blocked_ips


def test_whitelist_cache(cache_manager):
    """Test whitelist caching."""
    whitelist = {'192.168.1.100', '10.0.0.100'}
    cache_manager.set_whitelist(whitelist)
    
    cached_whitelist = cache_manager.get_whitelist()
    assert cached_whitelist == whitelist


def test_is_whitelisted(cache_manager):
    """Test whitelist check with LRU cache."""
    whitelist = {'192.168.1.100'}
    cache_manager.set_whitelist(whitelist)
    
    assert cache_manager.is_whitelisted('192.168.1.100') is True
    assert cache_manager.is_whitelisted('192.168.1.1') is False


def test_threat_prediction_cache(cache_manager):
    """Test threat prediction caching."""
    signature = 'request-hash-123'
    cache_manager.cache_threat_prediction(
        signature,
        is_threat=True,
        threat_types=['sqli', 'xss'],
        ttl=60
    )
    
    cached = cache_manager.get_cached_prediction(signature)
    
    assert cached is not None
    assert cached['is_threat'] is True
    assert 'sqli' in cached['threat_types']
    assert 'cached_at' in cached


def test_cache_stats(cache_manager):
    """Test cache statistics."""
    cache_manager.set('key1', 'value1')
    cache_manager.get('key1')  # Hit
    cache_manager.get('nonexistent')  # Miss
    
    stats = cache_manager.get_stats()
    
    assert stats['hits'] == 1
    assert stats['misses'] == 1
    assert stats['hit_rate'] == 0.5
    assert stats['memory_size'] == 1
    assert stats['max_memory_size'] == 100


def test_cache_entry_expiration():
    """Test CacheEntry expiration check."""
    entry = CacheEntry(
        key='test',
        value='value',
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        ttl_seconds=5
    )
    
    assert entry.is_expired() is True
    
    fresh_entry = CacheEntry(
        key='test2',
        value='value2',
        created_at=datetime.now(timezone.utc),
        ttl_seconds=60
    )
    
    assert fresh_entry.is_expired() is False


def test_custom_ttl(cache_manager):
    """Test custom TTL values."""
    cache_manager.set('short_ttl', 'value', ttl=1)
    cache_manager.set('long_ttl', 'value', ttl=3600)
    
    # Short TTL should expire quickly
    time.sleep(1.1)
    assert cache_manager.get('short_ttl') is None
    assert cache_manager.get('long_ttl') == 'value'
