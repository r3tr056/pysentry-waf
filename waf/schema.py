import json
from typing import Optional
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel, Field

def parse_request(data, request: FastAPIRequest):
    return WAFRequest(
        id=data.get("id"),
        timestamp=data.get("timestamp"),
        origin=str(request.client.host),
        host=str(request.url.hostname),
        request=data.get("request", ""),
        body=data.get("body", ""),
        method=str(request.method),
        headers=dict(request.headers),
    )

class WAFRequest(object):
    def __init__(
        self,
        id=None,
        timestamp=None,
        origin=None,
        host=None,
        request=None,
        body=None,
        method=None, 
        headers=None,
        threats=None
    ):
        self.id = id
        self.timestamp = timestamp
        self.origin = origin
        self.host = host
        self.request = request
        self.body = body
        self.method = method
        self.headers = headers
        self.threats = threats


    def to_json(self):
        output = {}
        if self.request != None and self.request != '':
            output['request'] = self.request
        if self.body != None and self.body != '':
            output['body'] = self.body
        if self.headers != None:
            for header, value in self.headers.items():
                output[header] = value

        return json.dumps(output)
    
class Threat(BaseModel):
    threat_type: str
    description: str
    severity: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[dict]

class ThreatUpdate(BaseModel):
    description: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[dict] = None

class IPAddress(BaseModel):
    ip_address: str = Field(..., regex=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")