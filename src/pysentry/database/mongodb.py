"""
MongoDB database service implementation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import logging

from .base import DatabaseService

logger = logging.getLogger(__name__)


class MongoDBService(DatabaseService):
    """MongoDB implementation of DatabaseService"""

    def __init__(self, connection_string: str, database_name: str = "pysentry_waf"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self) -> None:
        """Establish MongoDB connection"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            #  Test connection
            await self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def health_check(self) -> bool:
        """Check MongoDB health"""
        try:
            if not self.client:
                return False
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    # Threat operations
    async def create_threat(self, threat_data: Dict[str, Any]) -> str:
        """Create a new threat entry"""
        threat_data["created_at"] = datetime.now(timezone.utc)
        threat_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.db.threats.insert_one(threat_data)
        return str(result.inserted_id)

    async def get_threat(self, threat_id: str) -> Optional[Dict[str, Any]]:
        """Get threat by ID"""
        try:
            threat = await self.db.threats.find_one({"_id": ObjectId(threat_id)})
            if threat:
                threat["id"] = str(threat.pop("_id"))
            return threat
        except Exception as e:
            logger.error(f"Error fetching threat {threat_id}: {e}")
            return None

    async def list_threats(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List threats with pagination and filters"""
        query = filters or {}
        cursor = self.db.threats.find(query).skip(skip).limit(limit)
        threats = []
        async for threat in cursor:
            threat["id"] = str(threat.pop("_id"))
            threats.append(threat)
        return threats

    async def update_threat(self, threat_id: str, threat_data: Dict[str, Any]) -> bool:
        """Update threat by ID"""
        try:
            threat_data["updated_at"] = datetime.utcnow()
            result = await self.db.threats.update_one(
                {"_id": ObjectId(threat_id)}, {"$set": threat_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating threat {threat_id}: {e}")
            return False

    async def delete_threat(self, threat_id: str) -> bool:
        """Delete threat by ID"""
        try:
            result = await self.db.threats.delete_one({"_id": ObjectId(threat_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting threat {threat_id}: {e}")
            return False

    # IP blocking operations
    async def block_ip(self, ip_data: Dict[str, Any]) -> str:
        """Block an IP address"""
        ip_data["blocked_at"] = datetime.now(timezone.utc)
        result = await self.db.blocked_ips.insert_one(ip_data)
        return str(result.inserted_id)

    async def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address"""
        result = await self.db.blocked_ips.delete_one({"ip_address": ip_address})
        return result.deleted_count > 0

    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        result = await self.db.blocked_ips.find_one({"ip_address": ip_address})
        if result:
            # Check if block has expired
            if result.get("expires_at"):
                if datetime.utcnow() > result["expires_at"]:
                    # Block expired, remove it
                    await self.unblock_ip(ip_address)
                    return False
            return True
        return False

    async def list_blocked_ips(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List blocked IPs"""
        cursor = self.db.blocked_ips.find().skip(skip).limit(limit)
        ips = []
        async for ip in cursor:
            ip["id"] = str(ip.pop("_id"))
            ips.append(ip)
        return ips

    # Request logging operations
    async def log_request(self, request_data: Dict[str, Any]) -> str:
        """Log a request"""
        request_data["timestamp"] = datetime.utcnow()
        result = await self.db.request_logs.insert_one(request_data)
        return str(result.inserted_id)

    async def get_request_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get request logs with pagination and filters"""
        query = filters or {}
        cursor = self.db.request_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = []
        async for log in cursor:
            log["id"] = str(log.pop("_id"))
            logs.append(log)
        return logs
