"""
Phase 1.5: Input Validation Framework
Production-grade input validation and sanitization
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator, field_validator
import re
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    pass


class InputValidator:
    """
    Comprehensive input validation for WAF requests.
    
    Features:
    - SQL injection pattern detection
    - XSS pattern detection
    - Command injection detection
    - Path traversal detection
    - Request size limits
    - Header validation
    """
    
    # OWASP-based attack patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",
        r"(;.*\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE)\b)",
        r"(--\s*$)",
        r"(/\*.*\*/)",
        r"(0x[0-9a-fA-F]+)",
        r"(\bEXEC\b.*\()",
        r"(['\"][\s]*OR[\s]+['\"]?)",
    ]
    
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",
        r"(<object[^>]*>)",
        r"(<embed[^>]*>)",
        r"(eval\s*\()",
        r"(expression\s*\()",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"(;|\|{1,2}|&{1,2}).*\b(cat|ls|wget|curl|bash|sh|nc|netcat)\b",
        r"(\$\(.*\))",
        r"(`.*`)",
        r"(\|\s*\w+)",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.[\\/]){2,}",
        r"(/etc/passwd)",
        r"(/etc/shadow)",
        r"(\\x2e\\x2e[\\/])",
        r"(%2e%2e[\\/])",
    ]
    
    def __init__(self, max_request_size: int = 10 * 1024 * 1024):
        """
        Initialize input validator.
        
        Args:
            max_request_size: Maximum request size in bytes (default 10MB)
        """
        self.max_request_size = max_request_size
        
        # Compile patterns for performance
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.cmd_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
    
    def validate_string(self, value: str, field_name: str = "input") -> Dict[str, List[str]]:
        """
        Validate a string input for common attack patterns.
        
        Args:
            value: String to validate
            field_name: Name of the field being validated
            
        Returns:
            Dictionary of detected threats
        """
        threats = {}
        
        if not value:
            return threats
        
        # Check SQL injection
        for pattern in self.sql_patterns:
            if pattern.search(value):
                threats['sql_injection'] = f"SQL injection pattern detected in {field_name}"
                break
        
        # Check XSS
        for pattern in self.xss_patterns:
            if pattern.search(value):
                threats['xss'] = f"XSS pattern detected in {field_name}"
                break
        
        # Check command injection
        for pattern in self.cmd_patterns:
            if pattern.search(value):
                threats['command_injection'] = f"Command injection pattern detected in {field_name}"
                break
        
        # Check path traversal
        for pattern in self.path_patterns:
            if pattern.search(value):
                threats['path_traversal'] = f"Path traversal pattern detected in {field_name}"
                break
        
        return threats
    
    def validate_headers(self, headers: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Validate HTTP headers.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            Dictionary of detected threats
        """
        threats = {}
        
        # Check critical headers
        for header_name, header_value in headers.items():
            if header_value:
                header_threats = self.validate_string(str(header_value), f"header:{header_name}")
                threats.update(header_threats)
        
        # Check for header injection
        for header_name, header_value in headers.items():
            if '\r' in str(header_value) or '\n' in str(header_value):
                threats['header_injection'] = f"Header injection detected in {header_name}"
                break
        
        return threats
    
    def validate_request_size(self, content_length: Optional[int]) -> None:
        """
        Validate request size.
        
        Args:
            content_length: Content-Length header value
            
        Raises:
            HTTPException: If request size exceeds limit
        """
        if content_length and content_length > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Request size exceeds maximum allowed ({self.max_request_size} bytes)"
            )
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize a string by removing potentially dangerous characters.
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        if not value:
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Normalize unicode
        value = value.encode('ascii', 'ignore').decode('ascii')
        
        # Remove control characters except newlines and tabs
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        return value


# Pydantic models for validated inputs
class ValidatedIPAddress(BaseModel):
    """Validated IP address model"""
    ip_address: str = Field(..., pattern=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_octets(cls, v):
        """Validate IP address octets are in valid range"""
        octets = v.split('.')
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                raise ValueError('IP address octets must be between 0 and 255')
        return v


class ValidatedThreat(BaseModel):
    """Validated threat model"""
    threat_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    severity: int = Field(..., ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('threat_type')
    @classmethod
    def validate_threat_type(cls, v):
        """Validate threat type is alphanumeric with hyphens and underscores"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Threat type must be alphanumeric with hyphens and underscores')
        return v.lower()


class ValidatedThreatUpdate(BaseModel):
    """Validated threat update model"""
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    severity: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = None


class ContentTypeValidator:
    """Validate content types"""
    
    ALLOWED_CONTENT_TYPES = {
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain',
        'text/html',
        'application/xml',
        'text/xml',
    }
    
    @classmethod
    def validate(cls, content_type: Optional[str]) -> bool:
        """
        Validate content type is allowed.
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            True if valid, False otherwise
        """
        if not content_type:
            return True  # No content type is OK for GET requests
        
        # Extract base content type (before semicolon)
        base_type = content_type.split(';')[0].strip().lower()
        
        return base_type in cls.ALLOWED_CONTENT_TYPES


def validate_request_input(
    request_data: Optional[str] = None,
    body_data: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    content_length: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate all inputs from a request.
    
    Args:
        request_data: Request URL parameters
        body_data: Request body
        headers: Request headers
        content_length: Content-Length value
        
    Returns:
        Dictionary with validation results
        
    Raises:
        HTTPException: If validation fails critically
    """
    validator = InputValidator()
    all_threats = {}
    
    # Validate request size
    if content_length:
        validator.validate_request_size(content_length)
    
    # Validate request parameters
    if request_data:
        threats = validator.validate_string(request_data, "request_parameters")
        all_threats.update(threats)
    
    # Validate body
    if body_data:
        threats = validator.validate_string(body_data, "request_body")
        all_threats.update(threats)
    
    # Validate headers
    if headers:
        threats = validator.validate_headers(headers)
        all_threats.update(threats)
    
    return {
        "valid": len(all_threats) == 0,
        "threats": all_threats
    }
