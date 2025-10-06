"""
IP blocking service
"""

from typing import List, Optional
from datetime import datetime, timedelta
import logging

from pysentry.database import DatabaseService, RedisService
from pysentry.models import IPAddress, BlockedIP

logger = logging.getLogger(__name__)


class IPBlockingService:
    """Service for managing IP blocking"""

    def __init__(self, db_service: DatabaseService, redis_service: Optional[RedisService] = None):
        self.db = db_service
        self.redis = redis_service

    async def block_ip(
        self,
        ip_address: str,
        reason: str = "Malicious activity detected",
        duration_hours: Optional[int] = None,
        blocked_by: str = "system",
    ) -> BlockedIP:
        """Block an IP address"""
        ip_data = {
            "ip_address": ip_address,
            "reason": reason,
            "blocked_by": blocked_by,
        }

        if duration_hours:
            ip_data["expires_at"] = datetime.utcnow() + timedelta(hours=duration_hours)

        blocked_id = await self.db.block_ip(ip_data)

        # Cache in Redis for fast lookups
        if self.redis:
            cache_key = f"blocked_ip:{ip_address}"
            ttl = duration_hours * 3600 if duration_hours else None
            await self.redis.set(cache_key, "1", expire=ttl)

        blocked_data = await self.db.get_threat(blocked_id)  # Reuse get method
        logger.info(f"Blocked IP {ip_address}: {reason}")
        return BlockedIP(**{**ip_data, "id": blocked_id})

    async def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address"""
        success = await self.db.unblock_ip(ip_address)

        # Remove from Redis cache
        if self.redis:
            cache_key = f"blocked_ip:{ip_address}"
            await self.redis.delete(cache_key)

        if success:
            logger.info(f"Unblocked IP {ip_address}")
        return success

    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked (with caching)"""
        # Check Redis first
        if self.redis:
            cache_key = f"blocked_ip:{ip_address}"
            cached = await self.redis.exists(cache_key)
            if cached:
                return True

        # Check database
        return await self.db.is_ip_blocked(ip_address)

    async def list_blocked_ips(self, skip: int = 0, limit: int = 100) -> List[BlockedIP]:
        """List all blocked IPs"""
        blocked_data = await self.db.list_blocked_ips(skip, limit)
        return [BlockedIP(**ip) for ip in blocked_data]

    async def cleanup_expired_blocks(self) -> int:
        """Remove expired IP blocks"""
        # This would typically be run as a scheduled task
        blocked_ips = await self.list_blocked_ips(limit=1000)
        removed_count = 0

        for ip in blocked_ips:
            if ip.expires_at and datetime.utcnow() > ip.expires_at:
                await self.unblock_ip(ip.ip_address)
                removed_count += 1

        logger.info(f"Cleaned up {removed_count} expired IP blocks")
        return removed_count
