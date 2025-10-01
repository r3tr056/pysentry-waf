"""
Tests for data models (Phase 3)
"""

import pytest
from datetime import datetime
from pysentry.models import (
    Threat,
    ThreatCreate,
    ThreatUpdate,
    IPAddress,
    BlockedIP,
    WAFRequest,
    RequestLog,
)


class TestThreatModels:
    """Test threat data models"""

    def test_threat_create_valid(self):
        """Test creating a valid threat"""
        threat = ThreatCreate(
            threat_type="sql_injection",
            description="SQL injection attempt detected",
            severity=4,
            metadata={"pattern": "' OR '1'='1"},
        )
        assert threat.threat_type == "sql_injection"
        assert threat.severity == 4

    def test_threat_severity_validation(self):
        """Test threat severity must be 1-5"""
        with pytest.raises(ValueError):
            ThreatCreate(
                threat_type="xss",
                description="XSS attempt",
                severity=6,  # Invalid
            )

    def test_threat_update_partial(self):
        """Test partial threat update"""
        update = ThreatUpdate(description="Updated description")
        assert update.description == "Updated description"
        assert update.severity is None

    def test_threat_full_model(self):
        """Test full threat model with timestamps"""
        threat = Threat(
            threat_type="command_injection",
            description="Command injection detected",
            severity=5,
            id="123",
        )
        assert threat.id == "123"
        assert isinstance(threat.created_at, datetime)


class TestIPAddressModels:
    """Test IP address models"""

    def test_valid_ipv4(self):
        """Test valid IPv4 address"""
        ip = IPAddress(ip_address="192.168.1.1")
        assert ip.ip_address == "192.168.1.1"

    def test_valid_ipv6(self):
        """Test valid IPv6 address"""
        ip = IPAddress(ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert "2001" in ip.ip_address

    def test_invalid_ip(self):
        """Test invalid IP address"""
        with pytest.raises(ValueError):
            IPAddress(ip_address="999.999.999.999")

    def test_blocked_ip_with_reason(self):
        """Test blocked IP with reason"""
        blocked = BlockedIP(
            ip_address="192.168.1.100",
            reason="Multiple failed login attempts",
            blocked_by="admin",
        )
        assert blocked.reason == "Multiple failed login attempts"
        assert blocked.blocked_by == "admin"
        assert isinstance(blocked.blocked_at, datetime)


class TestRequestModels:
    """Test request models"""

    def test_waf_request_creation(self):
        """Test WAF request creation"""
        request = WAFRequest(
            origin="192.168.1.1",
            host="example.com",
            method="POST",
            path="/api/login",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        assert request.origin == "192.168.1.1"
        assert request.method == "POST"
        assert request.threats == {}

    def test_waf_request_with_threats(self):
        """Test WAF request with detected threats"""
        request = WAFRequest(
            origin="192.168.1.1",
            host="example.com",
            method="POST",
            path="/api/login",
            threats={"sql_injection": "query_params"},
        )
        assert "sql_injection" in request.threats

    def test_request_log_creation(self):
        """Test request log creation"""
        log = RequestLog(
            request_id="req_123",
            origin="192.168.1.1",
            host="example.com",
            method="GET",
            path="/",
            status_code=200,
            blocked=False,
        )
        assert log.request_id == "req_123"
        assert log.status_code == 200
        assert not log.blocked

    def test_request_log_blocked(self):
        """Test blocked request log"""
        log = RequestLog(
            request_id="req_456",
            origin="192.168.1.100",
            host="example.com",
            method="POST",
            path="/admin",
            status_code=403,
            blocked=True,
            threats_detected=["sql_injection", "xss"],
            processing_time_ms=15.5,
        )
        assert log.blocked
        assert len(log.threats_detected) == 2
        assert log.processing_time_ms == 15.5
