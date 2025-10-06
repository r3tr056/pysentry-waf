"""
Comprehensive tests for WAFService  
Tests end-to-end request analysis workflow
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from pysentry.services.waf_service import WAFService
from pysentry.models.request import WAFRequest


@pytest.fixture
def mock_threat_classifier():
    """Mock threat classifier"""
    classifier = MagicMock()
    classifier.classify_request = MagicMock()
    return classifier


@pytest.fixture
def mock_ip_service():
    """Mock IP blocking service"""
    service = AsyncMock()
    service.is_blocked = AsyncMock()
    service.block_ip = AsyncMock()
    return service


@pytest.fixture
def mock_logger():
    """Mock logger"""
    logger = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Mock metrics collector"""
    metrics = MagicMock()
    return metrics


@pytest.fixture
def waf_service(mock_threat_classifier, mock_ip_service, mock_logger, mock_metrics):
    """Create WAFService with mocked dependencies"""
    return WAFService(
        threat_classifier=mock_threat_classifier,
        ip_service=mock_ip_service,
        logger=mock_logger,
        metrics=mock_metrics
    )


@pytest.fixture
def sample_request():
    """Sample WAF request"""
    return WAFRequest(
        method="GET",
        path="/api/users",
        headers={"User-Agent": "Mozilla/5.0"},
        query_params={"id": "1"},
        body="",
        source_ip="192.168.1.100",
        timestamp=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_analyze_request_clean(waf_service, mock_threat_classifier, mock_ip_service, sample_request):
    """Test analyzing a clean request"""
    mock_ip_service.is_blocked.return_value = False
    mock_threat_classifier.classify_request.return_value = {"valid": "location"}
    
    result = await waf_service.analyze_request(sample_request)
    
    assert result["allowed"] is True
    assert result["threats"] == []
    assert "request_id" in result


@pytest.mark.asyncio
async def test_analyze_request_blocked_ip(waf_service, mock_ip_service, sample_request):
    """Test analyzing request from blocked IP"""
    mock_ip_service.is_blocked.return_value = True
    
    result = await waf_service.analyze_request(sample_request)
    
    assert result["allowed"] is False
    assert result["reason"] == "IP blocked"
    mock_ip_service.is_blocked.assert_called_once_with(sample_request.source_ip)


@pytest.mark.asyncio
async def test_analyze_request_with_threats(waf_service, mock_threat_classifier, mock_ip_service, sample_request):
    """Test analyzing request with detected threats"""
    mock_ip_service.is_blocked.return_value = False
    mock_threat_classifier.classify_request.return_value = {
        "sqli": "query parameter",
        "xss": "body"
    }
    
    result = await waf_service.analyze_request(sample_request)
    
    assert result["allowed"] is False
    assert len(result["threats"]) == 2
    assert "sqli" in [t["type"] for t in result["threats"]]


@pytest.mark.asyncio
async def test_analyze_request_metrics_recorded(waf_service, mock_metrics, mock_ip_service, sample_request):
    """Test that metrics are recorded"""
    mock_ip_service.is_blocked.return_value = False
    
    await waf_service.analyze_request(sample_request)
    
    mock_metrics.record_request.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_request_logging(waf_service, mock_logger, mock_ip_service, sample_request):
    """Test that requests are logged"""
    mock_ip_service.is_blocked.return_value = False
    
    await waf_service.analyze_request(sample_request)
    
    mock_logger.log_request.assert_called()


@pytest.mark.asyncio
async def test_analyze_request_auto_block_on_critical_threat(waf_service, mock_threat_classifier, mock_ip_service, sample_request):
    """Test auto-blocking IP on critical threat detection"""
    mock_ip_service.is_blocked.return_value = False
    mock_threat_classifier.classify_request.return_value = {
        "sqli": "query parameter"
    }
    
    # Enable auto-blocking
    waf_service.auto_block_enabled = True
    
    result = await waf_service.analyze_request(sample_request)
    
    assert result["allowed"] is False
    mock_ip_service.block_ip.assert_called_once_with(
        sample_request.source_ip,
        reason=pytest.approx("Critical threat detected:", abs=1)
    )


@pytest.mark.asyncio
async def test_analyze_request_with_exception(waf_service, mock_threat_classifier, sample_request):
    """Test handling exceptions during analysis"""
    mock_threat_classifier.classify_request.side_effect = Exception("Classification error")
    
    result = await waf_service.analyze_request(sample_request)
    
    # Should fail-safe and block request
    assert result["allowed"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_analyze_batch_requests(waf_service, mock_ip_service, sample_request):
    """Test analyzing multiple requests in batch"""
    mock_ip_service.is_blocked.return_value = False
    
    requests = [sample_request, sample_request, sample_request]
    results = await waf_service.analyze_batch(requests)
    
    assert len(results) == 3
    for result in results:
        assert "allowed" in result


@pytest.mark.asyncio
async def test_get_statistics(waf_service):
    """Test getting WAF statistics"""
    waf_service.total_requests = 1000
    waf_service.blocked_requests = 50
    waf_service.threats_detected = 75
    
    stats = await waf_service.get_statistics()
    
    assert stats["total_requests"] == 1000
    assert stats["blocked_requests"] == 50
    assert stats["threats_detected"] == 75
    assert stats["block_rate"] == 5.0


@pytest.mark.asyncio
async def test_analyze_request_performance(waf_service, mock_ip_service, sample_request):
    """Test that analysis performance is tracked"""
    mock_ip_service.is_blocked.return_value = False
    
    result = await waf_service.analyze_request(sample_request)
    
    assert "analysis_time_ms" in result
    assert result["analysis_time_ms"] >= 0


@pytest.mark.asyncio
async def test_analyze_request_with_rate_limit_exceeded(waf_service, sample_request):
    """Test handling rate limit exceeded scenario"""
    waf_service.rate_limit_exceeded = MagicMock(return_value=True)
    
    result = await waf_service.analyze_request(sample_request)
    
    assert result["allowed"] is False
    assert result["reason"] == "Rate limit exceeded"
