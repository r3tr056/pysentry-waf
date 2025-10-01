"""
Phase 1 Tests: Rate Limiting
Test in-memory and Redis-based rate limiting
"""
import pytest
import time
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add phase1_implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pysentry.core.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    RateLimitMiddleware,
    create_rate_limiter
)
from fastapi import HTTPException


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return InMemoryRateLimiter(requests_per_window=5, window_seconds=10)
    
    def test_allows_requests_under_limit(self, rate_limiter):
        """Test that requests under limit are allowed"""
        identifier = "test_client"
        
        for i in range(5):
            assert rate_limiter.is_allowed(identifier), f"Request {i+1} should be allowed"
    
    def test_blocks_requests_over_limit(self, rate_limiter):
        """Test that requests over limit are blocked"""
        identifier = "test_client"
        
        # Use up all requests
        for i in range(5):
            rate_limiter.is_allowed(identifier)
        
        # Next request should be blocked
        assert not rate_limiter.is_allowed(identifier)
    
    def test_window_reset(self, rate_limiter):
        """Test that window resets after time"""
        identifier = "test_client"
        
        # Use up all requests
        for i in range(5):
            rate_limiter.is_allowed(identifier)
        
        # Should be blocked
        assert not rate_limiter.is_allowed(identifier)
        
        # Wait for window to expire
        time.sleep(10.1)
        
        # Should be allowed again
        assert rate_limiter.is_allowed(identifier)
    
    def test_get_remaining(self, rate_limiter):
        """Test getting remaining requests"""
        identifier = "test_client"
        
        assert rate_limiter.get_remaining(identifier) == 5
        
        rate_limiter.is_allowed(identifier)
        assert rate_limiter.get_remaining(identifier) == 4
        
        rate_limiter.is_allowed(identifier)
        assert rate_limiter.get_remaining(identifier) == 3
    
    def test_reset_time(self, rate_limiter):
        """Test getting reset time"""
        identifier = "test_client"
        
        # Make first request
        rate_limiter.is_allowed(identifier)
        
        # Get reset time
        reset_time = rate_limiter.reset_time(identifier)
        
        # Should be approximately 10 seconds
        assert 9 <= reset_time <= 11
    
    def test_multiple_clients(self, rate_limiter):
        """Test rate limiting with multiple clients"""
        client1 = "client1"
        client2 = "client2"
        
        # Use up client1's requests
        for i in range(5):
            rate_limiter.is_allowed(client1)
        
        # Client1 should be blocked
        assert not rate_limiter.is_allowed(client1)
        
        # Client2 should still be allowed
        assert rate_limiter.is_allowed(client2)


class TestRedisRateLimiter:
    """Test Redis-based rate limiter"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        redis_mock = MagicMock()
        
        # Mock pipeline
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, 0, None, None]  # [zremrangebyscore, zcard, zadd, expire]
        redis_mock.pipeline.return_value = pipeline_mock
        
        # Mock direct operations
        redis_mock.zremrangebyscore.return_value = None
        redis_mock.zcard.return_value = 0
        redis_mock.zrange.return_value = []
        
        return redis_mock
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create Redis rate limiter for testing"""
        return RedisRateLimiter(mock_redis, requests_per_window=5, window_seconds=10)
    
    def test_allows_requests_under_limit(self, rate_limiter, mock_redis):
        """Test that requests under limit are allowed"""
        identifier = "test_client"
        
        # Mock zcard to return increasing count
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute.return_value = [None, 0, None, None]
        
        assert rate_limiter.is_allowed(identifier)
    
    def test_blocks_requests_over_limit(self, rate_limiter, mock_redis):
        """Test that requests over limit are blocked"""
        identifier = "test_client"
        
        # Mock zcard to return count at limit
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute.return_value = [None, 5, None, None]
        
        assert not rate_limiter.is_allowed(identifier)
    
    def test_get_remaining(self, rate_limiter, mock_redis):
        """Test getting remaining requests"""
        identifier = "test_client"
        
        # Mock current count
        mock_redis.zcard.return_value = 2
        
        remaining = rate_limiter.get_remaining(identifier)
        assert remaining == 3  # 5 - 2
    
    def test_redis_error_failopen(self, rate_limiter, mock_redis):
        """Test that Redis errors fail open (allow request)"""
        identifier = "test_client"
        
        # Make pipeline raise error
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")
        
        # Should allow request on error (fail open)
        assert rate_limiter.is_allowed(identifier)


class TestRateLimitMiddleware:
    """Test rate limit middleware"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return InMemoryRateLimiter(requests_per_window=5, window_seconds=10)
    
    @pytest.fixture
    def middleware(self, rate_limiter):
        """Create middleware for testing"""
        return RateLimitMiddleware(rate_limiter, enabled=True)
    
    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self, middleware):
        """Test that requests under limit pass through"""
        # Mock request
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        
        # Mock call_next
        async def call_next(req):
            response = Mock()
            response.headers = {}
            return response
        
        response = await middleware(request, call_next)
        
        assert response is not None
        assert "X-RateLimit-Limit" in response.headers
    
    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self, middleware, rate_limiter):
        """Test that requests over limit are blocked"""
        # Mock request
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        
        # Mock call_next
        async def call_next(req):
            response = Mock()
            response.headers = {}
            return response
        
        # Use up all requests
        for i in range(5):
            await middleware(request, call_next)
        
        # Next request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware(request, call_next)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_disabled_middleware(self, rate_limiter):
        """Test that disabled middleware passes all requests"""
        middleware = RateLimitMiddleware(rate_limiter, enabled=False)
        
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        
        async def call_next(req):
            return Mock()
        
        # Should allow unlimited requests
        for i in range(10):
            await middleware(request, call_next)
    
    @pytest.mark.asyncio
    async def test_whitelist(self, middleware):
        """Test that whitelisted IPs bypass rate limiting"""
        # Mock request from localhost
        request = Mock()
        request.client = Mock(host="127.0.0.1")
        
        async def call_next(req):
            response = Mock()
            response.headers = {}
            return response
        
        # Should allow unlimited requests from localhost
        for i in range(10):
            response = await middleware(request, call_next)
            assert response is not None


class TestCreateRateLimiter:
    """Test rate limiter factory function"""
    
    def test_creates_inmemory_without_redis(self):
        """Test creating in-memory rate limiter"""
        limiter = create_rate_limiter(redis_url=None)
        
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_creates_inmemory_on_redis_failure(self):
        """Test fallback to in-memory on Redis connection failure"""
        limiter = create_rate_limiter(redis_url="redis://nonexistent:6379")
        
        # Should fall back to in-memory
        assert isinstance(limiter, InMemoryRateLimiter)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
