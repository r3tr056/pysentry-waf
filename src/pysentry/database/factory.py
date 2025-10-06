"""
Factory for creating database service instances
"""

from typing import Optional
import logging

from pysentry.core.config import Config
from .mongodb import MongoDBService
from .redis_client import RedisService

logger = logging.getLogger(__name__)

# Singleton instances
_db_service: Optional[MongoDBService] = None
_redis_service: Optional[RedisService] = None


def get_database_service() -> MongoDBService:
    """Get or create MongoDB service instance"""
    global _db_service
    if _db_service is None:
        config = Config()
        _db_service = MongoDBService(
            connection_string=config.mongodb_url, database_name="pysentry_waf"
        )
    return _db_service


def get_redis_service() -> Optional[RedisService]:
    """Get or create Redis service instance"""
    global _redis_service
    if _redis_service is None:
        config = Config()
        if config.redis_url:
            try:
                _redis_service = RedisService(redis_url=config.redis_url)
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                return None
    return _redis_service
