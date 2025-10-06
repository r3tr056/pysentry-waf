"""
Redis service for caching and session management
"""

from typing import Optional, Any
import json
import logging
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and distributed operations"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client: Optional[Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection"""
        try:
            self.client = await Redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self.client:
                return False
            await self.client.ping()
            return True
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # Cache operations
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration (seconds)"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.set(key, value, ex=expire)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            result = await self.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    # Rate limiting operations
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        try:
            return await self.client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return await self.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time-to-live for key"""
        try:
            return await self.client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1

    # List operations (for queues)
    async def lpush(self, key: str, *values: Any) -> Optional[int]:
        """Push values to left of list"""
        try:
            serialized = [json.dumps(v) if isinstance(v, dict) else v for v in values]
            return await self.client.lpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return None

    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list"""
        try:
            value = await self.client.rpop(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except RedisError as e:
            logger.error(f"Redis RPOP error for key {key}: {e}")
            return None

    async def llen(self, key: str) -> int:
        """Get list length"""
        try:
            return await self.client.llen(key)
        except RedisError as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0
