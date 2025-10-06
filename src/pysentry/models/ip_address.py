"""
IP Address data models
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import ipaddress


class IPAddress(BaseModel):
    """IP Address model"""

    ip_address: str = Field(..., description="IPv4 or IPv6 address")

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address format: {v}")

    class Config:
        json_schema_extra = {"example": {"ip_address": "192.168.1.100"}}


class BlockedIP(IPAddress):
    """Blocked IP model with additional fields"""

    id: Optional[str] = Field(default=None, description="Unique identifier")
    reason: str = Field(default="Malicious activity detected", description="Block reason")
    blocked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(
        default=None, description="When the block expires (None for permanent)"
    )
    blocked_by: str = Field(default="system", description="Who/what blocked this IP")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "ip_address": "192.168.1.100",
                "reason": "Multiple failed authentication attempts",
                "blocked_by": "admin",
            }
        }
