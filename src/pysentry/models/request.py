"""
Request data models
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class WAFRequest(BaseModel):
    """WAF Request model for analyzing incoming requests"""

    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    origin: str = Field(..., description="Source IP address")
    host: str = Field(..., description="Target host")
    method: str = Field(..., description="HTTP method")
    path: str = Field(default="/", description="Request path")
    query_params: Optional[str] = Field(default=None, description="Query parameters")
    body: Optional[str] = Field(default=None, description="Request body")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    threats: Dict[str, str] = Field(
        default_factory=dict, description="Detected threats {type: location}"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "origin": "192.168.1.100",
                "host": "example.com",
                "method": "POST",
                "path": "/api/login",
                "headers": {"User-Agent": "Mozilla/5.0"},
                "threats": {},
            }
        }


class RequestLog(BaseModel):
    """Model for logged requests"""

    id: Optional[str] = None
    request_id: str = Field(..., description="Original request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    origin: str
    host: str
    method: str
    path: str
    status_code: int = Field(..., description="Response status code")
    blocked: bool = Field(default=False, description="Whether request was blocked")
    threats_detected: List[str] = Field(
        default_factory=list, description="List of threat types detected"
    )
    processing_time_ms: Optional[float] = Field(
        default=None, description="Request processing time in milliseconds"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "request_id": "req_123456",
                "origin": "192.168.1.100",
                "host": "example.com",
                "method": "POST",
                "path": "/api/login",
                "status_code": 403,
                "blocked": True,
                "threats_detected": ["sql_injection"],
                "processing_time_ms": 45.2,
            }
        }
