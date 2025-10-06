"""
Integration tests for database services (Phase 3)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pysentry.database import MongoDBService, RedisService


@pytest.mark.asyncio
class TestMongoDBService:
    """Test MongoDB service"""

    @pytest_asyncio.fixture
    async def mock_mongodb(self):
        """Create mock MongoDB service"""
        service = MongoDBService("mongodb://localhost:27017", "test_db")
        service.client = AsyncMock()
        service.db = MagicMock()
        return service

    async def test_health_check_success(self, mock_mongodb):
        """Test successful health check"""
        mock_mongodb.client.admin.command = AsyncMock(return_value={"ok": 1})
        result = await mock_mongodb.health_check()
        assert result is True

    async def test_health_check_failure(self, mock_mongodb):
        """Test failed health check"""
        mock_mongodb.client = None
        result = await mock_mongodb.health_check()
        assert result is False

    async def test_create_threat(self, mock_mongodb):
        """Test creating a threat"""
        mock_result = MagicMock()
        mock_result.inserted_id = "123456"
        mock_mongodb.db.threats.insert_one = AsyncMock(return_value=mock_result)

        threat_data = {
            "threat_type": "sql_injection",
            "description": "Test threat",
            "severity": 4,
        }
        threat_id = await mock_mongodb.create_threat(threat_data)
        assert threat_id == "123456"

    async def test_block_ip(self, mock_mongodb):
        """Test blocking an IP"""
        mock_result = MagicMock()
        mock_result.inserted_id = "789"
        mock_mongodb.db.blocked_ips.insert_one = AsyncMock(return_value=mock_result)

        ip_data = {"ip_address": "192.168.1.100", "reason": "Test block"}
        ip_id = await mock_mongodb.block_ip(ip_data)
        assert ip_id == "789"


@pytest.mark.asyncio
class TestRedisService:
    """Test Redis service"""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis service"""
        service = RedisService("redis://localhost:6379")
        service.client = AsyncMock()
        return service

    async def test_health_check_success(self, mock_redis):
        """Test successful Redis health check"""
        mock_redis.client.ping = AsyncMock(return_value=True)
        result = await mock_redis.health_check()
        assert result is True

    async def test_set_and_get(self, mock_redis):
        """Test setting and getting values"""
        mock_redis.client.set = AsyncMock(return_value=True)
        mock_redis.client.get = AsyncMock(return_value="test_value")

        await mock_redis.set("test_key", "test_value")
        value = await mock_redis.get("test_key")
        assert value == "test_value"

    async def test_increment(self, mock_redis):
        """Test incrementing counter"""
        mock_redis.client.incrby = AsyncMock(return_value=5)
        result = await mock_redis.increment("counter", 5)
        assert result == 5

    async def test_list_operations(self, mock_redis):
        """Test list push and pop"""
        mock_redis.client.lpush = AsyncMock(return_value=1)
        mock_redis.client.rpop = AsyncMock(return_value='{"key": "value"}')

        await mock_redis.lpush("queue", {"key": "value"})
        value = await mock_redis.rpop("queue")
        assert value == {"key": "value"}
