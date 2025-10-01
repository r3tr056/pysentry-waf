"""
Threat data models
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ThreatBase(BaseModel):
    """Base threat model"""

    threat_type: str = Field(..., description="Type of threat (e.g., sql_injection, xss)")
    description: str = Field(..., description="Description of the threat")
    severity: int = Field(..., ge=1, le=5, description="Severity level (1-5)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ThreatCreate(ThreatBase):
    """Model for creating a new threat"""

    pass


class ThreatUpdate(BaseModel):
    """Model for updating a threat"""

    threat_type: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = None


class Threat(ThreatBase):
    """Full threat model with database fields"""

    id: Optional[str] = Field(default=None, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "threat_type": "sql_injection",
                "description": "Attempted SQL injection attack",
                "severity": 4,
                "metadata": {"pattern": "' OR '1'='1", "location": "query_parameter"},
            }
        }
