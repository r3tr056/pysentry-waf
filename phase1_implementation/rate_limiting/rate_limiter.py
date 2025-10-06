"""
Phase 1.6: Rate Limiting Implementation
Production-grade rate limiting with Redis support
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request, status
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.
    Suitable for single-instance deployments.
    """
    
    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60):
        """
        Initialize in-memory rate limiter.
        
        Args:
            requests_per_window: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for the identifier.
        
        Args:
            identifier: Unique identifier (e.g., IP address)
            
        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < self.requests_per_window:
            self.requests[identifier].append(current_time)
            return True
        
        return False
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        return max(0, self.requests_per_window - len(self.requests[identifier]))
    
    def reset_time(self, identifier: str) -> int:
        """Get seconds until window resets"""
        if not self.requests[identifier]:
            return 0
        
        oldest_request = min(self.requests[identifier])
        reset_time = oldest_request + self.window_seconds
        
        return max(0, int(reset_time - time.time()))


class RedisRateLimiter:
    """
    Redis-based rate limiter for distributed deployments.
    Uses sliding window counter algorithm.
    """
    
    def __init__(self, redis_client, requests_per_window: int = 100, 
                 window_seconds: int = 60):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_client: Redis client instance
            requests_per_window: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.redis = redis_client
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for the identifier.
        
        Args:
            identifier: Unique identifier (e.g., IP address)
            
        Returns:
            True if request is allowed, False otherwise
        """
        try:
            key = f"rate_limit:{identifier}"
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Use Redis pipeline for atomicity
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request with score as timestamp
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window_seconds)
            
            results = pipe.execute()
            request_count = results[1]
            
            return request_count < self.requests_per_window
            
        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            # Fail open on error - allow request
            return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        try:
            key = f"rate_limit:{identifier}"
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Remove old entries
            self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            request_count = self.redis.zcard(key)
            
            return max(0, self.requests_per_window - request_count)
            
        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            return self.requests_per_window
    
    def reset_time(self, identifier: str) -> int:
        """Get seconds until window resets"""
        try:
            key = f"rate_limit:{identifier}"
            
            # Get oldest request timestamp
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            
            if not oldest:
                return 0
            
            oldest_time = oldest[0][1]
            reset_time = oldest_time + self.window_seconds
            
            return max(0, int(reset_time - time.time()))
            
        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            return 0


class RateLimitMiddleware:
    """
    Rate limiting middleware for FastAPI.
    """
    
    def __init__(self, rate_limiter, enabled: bool = True):
        """
        Initialize rate limit middleware.
        
        Args:
            rate_limiter: Rate limiter instance (InMemory or Redis)
            enabled: Whether rate limiting is enabled
        """
        self.rate_limiter = rate_limiter
        self.enabled = enabled
    
    async def __call__(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response or raises HTTPException if rate limited
        """
        if not self.enabled:
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # Check whitelist (for health checks, monitoring, etc.)
        if self._is_whitelisted(client_ip):
            return await call_next(request)
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            remaining = self.rate_limiter.get_remaining(client_ip)
            reset_time = self.rate_limiter.reset_time(client_ip)
            
            logger.warning(f"Rate limit exceeded for {client_ip}")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        remaining = self.rate_limiter.get_remaining(client_ip)
        reset_time = self.rate_limiter.reset_time(client_ip)
        
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _is_whitelisted(self, ip: str) -> bool:
        """
        Check if IP is whitelisted.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if whitelisted, False otherwise
        """
        # Whitelist localhost and health check endpoints
        whitelist = ['127.0.0.1', '::1', 'localhost']
        return ip in whitelist


def create_rate_limiter(redis_url: Optional[str] = None,
                       requests_per_window: int = 100,
                       window_seconds: int = 60):
    """
    Factory function to create appropriate rate limiter.
    
    Args:
        redis_url: Redis URL (if None, uses in-memory)
        requests_per_window: Maximum requests allowed per window
        window_seconds: Time window in seconds
        
    Returns:
        Rate limiter instance
    """
    if redis_url:
        try:
            import redis
            redis_client = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            redis_client.ping()
            logger.info("Using Redis-based rate limiter")
            return RedisRateLimiter(redis_client, requests_per_window, window_seconds)
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory rate limiter")
    
    logger.info("Using in-memory rate limiter")
    return InMemoryRateLimiter(requests_per_window, window_seconds)
