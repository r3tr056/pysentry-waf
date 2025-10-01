"""
Base database service interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class DatabaseService(ABC):
    """Abstract base class for database operations"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if database is healthy"""
        pass

    # Threat operations
    @abstractmethod
    async def create_threat(self, threat_data: Dict[str, Any]) -> str:
        """Create a new threat entry"""
        pass

    @abstractmethod
    async def get_threat(self, threat_id: str) -> Optional[Dict[str, Any]]:
        """Get threat by ID"""
        pass

    @abstractmethod
    async def list_threats(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List threats with pagination and filters"""
        pass

    @abstractmethod
    async def update_threat(self, threat_id: str, threat_data: Dict[str, Any]) -> bool:
        """Update threat by ID"""
        pass

    @abstractmethod
    async def delete_threat(self, threat_id: str) -> bool:
        """Delete threat by ID"""
        pass

    # IP blocking operations
    @abstractmethod
    async def block_ip(self, ip_data: Dict[str, Any]) -> str:
        """Block an IP address"""
        pass

    @abstractmethod
    async def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address"""
        pass

    @abstractmethod
    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        pass

    @abstractmethod
    async def list_blocked_ips(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List blocked IPs"""
        pass

    # Request logging operations
    @abstractmethod
    async def log_request(self, request_data: Dict[str, Any]) -> str:
        """Log a request"""
        pass

    @abstractmethod
    async def get_request_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get request logs with pagination and filters"""
        pass
