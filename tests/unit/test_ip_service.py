"""
Comprehensive tests for IPBlockingService
Tests IP blocking, unblocking, caching, and TTL expiration
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from pysentry.services.ip_service import IPBlockingService
from pysentry.models.ip_address import IPAddress, BlockedIP


@pytest.fixture
def mock_db_service():
    """Mock database service"""
    db = AsyncMock()
    db.find_one = AsyncMock()
    db.find = AsyncMock()
    db.insert_one = AsyncMock()
    db.delete_one = AsyncMock()
    db.count_documents = AsyncMock()
    return db


@pytest.fixture
def mock_cache():
    """Mock cache manager"""
    cache = AsyncMock()
    cache.get = AsyncMock()
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock()
    return cache


@pytest.fixture
def ip_service(mock_db_service, mock_cache):
    """Create IPBlockingService with mocked dependencies"""
    return IPBlockingService(mock_db_service, mock_cache)


@pytest.fixture
def sample_blocked_ip():
    """Sample blocked IP data"""
    return {
        "ip_address": "192.168.1.100",
        "reason": "Multiple failed login attempts",
        "blocked_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        "blocked_by": "auto"
    }


@pytest.mark.asyncio
async def test_block_ip_success(ip_service, mock_db_service, mock_cache):
    """Test successfully blocking an IP address"""
    ip_address = "192.168.1.100"
    reason = "Suspicious activity"
    
    mock_db_service.find_one.return_value = None  # IP not already blocked
    mock_db_service.insert_one.return_value = "block123"
    
    result = await ip_service.block_ip(ip_address, reason)
    
    assert result is True
    mock_db_service.insert_one.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_block_ip_already_blocked(ip_service, mock_db_service, mock_cache, sample_blocked_ip):
    """Test blocking an already blocked IP"""
    mock_db_service.find_one.return_value = sample_blocked_ip
    
    result = await ip_service.block_ip("192.168.1.100", "Test")
    
    assert result is False
    mock_db_service.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_unblock_ip_success(ip_service, mock_db_service, mock_cache):
    """Test successfully unblocking an IP"""
    ip_address = "192.168.1.100"
    mock_db_service.delete_one.return_value = True
    
    result = await ip_service.unblock_ip(ip_address)
    
    assert result is True
    mock_db_service.delete_one.assert_called_once()
    mock_cache.delete.assert_called_once()


@pytest.mark.asyncio
async def test_unblock_ip_not_blocked(ip_service, mock_db_service, mock_cache):
    """Test unblocking an IP that isn't blocked"""
    mock_db_service.delete_one.return_value = False
    
    result = await ip_service.unblock_ip("192.168.1.100")
    
    assert result is False


@pytest.mark.asyncio
async def test_is_ip_blocked_cache_hit(ip_service, mock_cache):
    """Test checking if IP is blocked (cache hit)"""
    mock_cache.exists.return_value = True
    
    result = await ip_service.is_blocked("192.168.1.100")
    
    assert result is True
    mock_cache.exists.assert_called_once()


@pytest.mark.asyncio
async def test_is_ip_blocked_cache_miss_db_hit(ip_service, mock_db_service, mock_cache, sample_blocked_ip):
    """Test checking if IP is blocked (cache miss, DB hit)"""
    mock_cache.exists.return_value = False
    mock_db_service.find_one.return_value = sample_blocked_ip
    
    result = await ip_service.is_blocked("192.168.1.100")
    
    assert result is True
    mock_cache.set.assert_called_once()  # Should cache the result


@pytest.mark.asyncio
async def test_is_ip_blocked_not_blocked(ip_service, mock_db_service, mock_cache):
    """Test checking IP that is not blocked"""
    mock_cache.exists.return_value = False
    mock_db_service.find_one.return_value = None
    
    result = await ip_service.is_blocked("192.168.1.100")
    
    assert result is False


@pytest.mark.asyncio
async def test_list_blocked_ips(ip_service, mock_db_service, sample_blocked_ip):
    """Test listing all blocked IPs"""
    mock_db_service.find.return_value = [sample_blocked_ip, sample_blocked_ip.copy()]
    
    result = await ip_service.list_blocked_ips()
    
    assert len(result) == 2
    assert result[0]["ip_address"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_list_blocked_ips_with_pagination(ip_service, mock_db_service, sample_blocked_ip):
    """Test listing blocked IPs with pagination"""
    mock_db_service.find.return_value = [sample_blocked_ip]
    
    result = await ip_service.list_blocked_ips(skip=10, limit=10)
    
    call_args = mock_db_service.find.call_args
    assert call_args[1]["skip"] == 10
    assert call_args[1]["limit"] == 10


@pytest.mark.asyncio
async def test_block_ip_with_ttl(ip_service, mock_db_service, mock_cache):
    """Test blocking IP with TTL expiration"""
    ttl_seconds = 3600  # 1 hour
    
    mock_db_service.find_one.return_value = None
    mock_db_service.insert_one.return_value = "block123"
    
    result = await ip_service.block_ip("192.168.1.100", "Test", ttl_seconds=ttl_seconds)
    
    assert result is True
    # Verify TTL was set
    call_args = mock_cache.set.call_args
    assert call_args[1].get("ttl") == ttl_seconds


@pytest.mark.asyncio
async def test_block_subnet(ip_service, mock_db_service, mock_cache):
    """Test blocking an entire subnet"""
    subnet = "192.168.1.0/24"
    
    mock_db_service.find_one.return_value = None
    mock_db_service.insert_one.return_value = "block123"
    
    result = await ip_service.block_ip(subnet, "Malicious subnet")
    
    assert result is True


@pytest.mark.asyncio
async def test_count_blocked_ips(ip_service, mock_db_service):
    """Test counting blocked IPs"""
    mock_db_service.count_documents.return_value = 42
    
    result = await ip_service.count_blocked_ips()
    
    assert result == 42
