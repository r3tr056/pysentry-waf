"""
Threat intelligence service
"""

from typing import List, Optional, Dict, Any
import logging

from pysentry.database import DatabaseService
from pysentry.models import Threat, ThreatCreate, ThreatUpdate

logger = logging.getLogger(__name__)


class ThreatService:
    """Service for managing threat intelligence"""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    async def create_threat(self, threat: ThreatCreate) -> Threat:
        """Create a new threat entry"""
        threat_data = threat.model_dump()
        threat_id = await self.db.create_threat(threat_data)
        created_threat = await self.db.get_threat(threat_id)
        return Threat(**created_threat)

    async def get_threat(self, threat_id: str) -> Optional[Threat]:
        """Get threat by ID"""
        threat_data = await self.db.get_threat(threat_id)
        if threat_data:
            return Threat(**threat_data)
        return None

    async def list_threats(
        self,
        skip: int = 0,
        limit: int = 100,
        threat_type: Optional[str] = None,
        min_severity: Optional[int] = None,
    ) -> List[Threat]:
        """List threats with optional filters"""
        filters = {}
        if threat_type:
            filters["threat_type"] = threat_type
        if min_severity:
            filters["severity"] = {"$gte": min_severity}

        threats_data = await self.db.list_threats(skip, limit, filters)
        return [Threat(**threat) for threat in threats_data]

    async def update_threat(self, threat_id: str, threat_update: ThreatUpdate) -> Optional[Threat]:
        """Update threat by ID"""
        update_data = {k: v for k, v in threat_update.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_threat(threat_id)

        success = await self.db.update_threat(threat_id, update_data)
        if success:
            return await self.get_threat(threat_id)
        return None

    async def delete_threat(self, threat_id: str) -> bool:
        """Delete threat by ID"""
        return await self.db.delete_threat(threat_id)

    async def search_threats(self, query: str) -> List[Threat]:
        """Search threats by text query"""
        # Simple search - in production, use full-text search indexes
        filters = {
            "$or": [
                {"description": {"$regex": query, "$options": "i"}},
                {"threat_type": {"$regex": query, "$options": "i"}},
            ]
        }
        threats_data = await self.db.list_threats(filters=filters)
        return [Threat(**threat) for threat in threats_data]
