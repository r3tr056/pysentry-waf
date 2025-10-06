"""
Comprehensive tests for ThreatService
Tests CRUD operations, filtering, pagination, and error handling
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from pysentry.services.threat_service import ThreatService
from pysentry.models.threat import Threat, ThreatCreate, ThreatUpdate


@pytest.fixture
def mock_db_service():
    """Mock database service for testing"""
    db = AsyncMock()
    db.find_one = AsyncMock()
    db.find = AsyncMock()
    db.insert_one = AsyncMock()
    db.update_one = AsyncMock()
    db.delete_one = AsyncMock()
    db.count_documents = AsyncMock()
    return db


@pytest.fixture
def threat_service(mock_db_service):
    """Create ThreatService instance with mocked dependencies"""
    return ThreatService(mock_db_service)


@pytest.fixture
def sample_threat_data():
    """Sample threat data for testing"""
    return {
        "id": "threat123",
        "type": "sqli",
        "severity": "critical",
        "description": "SQL injection attempt detected",
        "source_ip": "192.168.1.100",
        "target_url": "/api/users",
        "payload": "' OR '1'='1",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.mark.asyncio
async def test_create_threat_success(threat_service, mock_db_service, sample_threat_data):
    """Test successful threat creation"""
    threat_create = ThreatCreate(
        type=sample_threat_data["type"],
        severity=sample_threat_data["severity"],
        description=sample_threat_data["description"],
        source_ip=sample_threat_data["source_ip"],
        target_url=sample_threat_data["target_url"],
        payload=sample_threat_data["payload"]
    )
    
    mock_db_service.insert_one.return_value = "threat123"
    mock_db_service.find_one.return_value = sample_threat_data
    
    result = await threat_service.create_threat(threat_create)
    
    assert result.id == "threat123"
    assert result.type == "sqli"
    assert result.severity == "critical"
    mock_db_service.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_threat_by_id_success(threat_service, mock_db_service, sample_threat_data):
    """Test retrieving threat by ID"""
    mock_db_service.find_one.return_value = sample_threat_data
    
    result = await threat_service.get_threat("threat123")
    
    assert result.id == "threat123"
    assert result.type == "sqli"
    mock_db_service.find_one.assert_called_once_with("threats", {"_id": "threat123"})


@pytest.mark.asyncio
async def test_get_threat_not_found(threat_service, mock_db_service):
    """Test retrieving non-existent threat"""
    mock_db_service.find_one.return_value = None
    
    result = await threat_service.get_threat("nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_list_threats_with_pagination(threat_service, mock_db_service, sample_threat_data):
    """Test listing threats with pagination"""
    mock_db_service.find.return_value = [sample_threat_data, sample_threat_data.copy()]
    mock_db_service.count_documents.return_value = 2
    
    result = await threat_service.list_threats(skip=0, limit=10)
    
    assert len(result) == 2
    assert result[0].type == "sqli"
    mock_db_service.find.assert_called_once()


@pytest.mark.asyncio
async def test_list_threats_filter_by_severity(threat_service, mock_db_service, sample_threat_data):
    """Test filtering threats by severity"""
    mock_db_service.find.return_value = [sample_threat_data]
    mock_db_service.count_documents.return_value = 1
    
    result = await threat_service.list_threats(severity="critical")
    
    assert len(result) == 1
    assert result[0].severity == "critical"
    # Verify filter was passed
    call_args = mock_db_service.find.call_args
    assert call_args[0][1]["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_threats_filter_by_type(threat_service, mock_db_service, sample_threat_data):
    """Test filtering threats by type"""
    mock_db_service.find.return_value = [sample_threat_data]
    mock_db_service.count_documents.return_value = 1
    
    result = await threat_service.list_threats(type="sqli")
    
    assert len(result) == 1
    assert result[0].type == "sqli"


@pytest.mark.asyncio
async def test_list_threats_filter_by_status(threat_service, mock_db_service, sample_threat_data):
    """Test filtering threats by status"""
    mock_db_service.find.return_value = [sample_threat_data]
    mock_db_service.count_documents.return_value = 1
    
    result = await threat_service.list_threats(status="active")
    
    assert len(result) == 1
    assert result[0].status == "active"


@pytest.mark.asyncio
async def test_update_threat_success(threat_service, mock_db_service, sample_threat_data):
    """Test successful threat update"""
    threat_update = ThreatUpdate(
        severity="high",
        status="mitigated",
        description="Updated description"
    )
    
    updated_data = sample_threat_data.copy()
    updated_data["severity"] = "high"
    updated_data["status"] = "mitigated"
    
    mock_db_service.update_one.return_value = True
    mock_db_service.find_one.return_value = updated_data
    
    result = await threat_service.update_threat("threat123", threat_update)
    
    assert result.severity == "high"
    assert result.status == "mitigated"
    mock_db_service.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_update_threat_not_found(threat_service, mock_db_service):
    """Test updating non-existent threat"""
    threat_update = ThreatUpdate(severity="high")
    mock_db_service.update_one.return_value = False
    
    result = await threat_service.update_threat("nonexistent", threat_update)
    
    assert result is None


@pytest.mark.asyncio
async def test_delete_threat_success(threat_service, mock_db_service):
    """Test successful threat deletion"""
    mock_db_service.delete_one.return_value = True
    
    result = await threat_service.delete_threat("threat123")
    
    assert result is True
    mock_db_service.delete_one.assert_called_once_with("threats", {"_id": "threat123"})


@pytest.mark.asyncio
async def test_delete_threat_not_found(threat_service, mock_db_service):
    """Test deleting non-existent threat"""
    mock_db_service.delete_one.return_value = False
    
    result = await threat_service.delete_threat("nonexistent")
    
    assert result is False


@pytest.mark.asyncio
async def test_count_threats(threat_service, mock_db_service):
    """Test counting threats"""
    mock_db_service.count_documents.return_value = 42
    
    result = await threat_service.count_threats()
    
    assert result == 42
    mock_db_service.count_documents.assert_called_once_with("threats", {})


@pytest.mark.asyncio
async def test_count_threats_with_filter(threat_service, mock_db_service):
    """Test counting threats with filter"""
    mock_db_service.count_documents.return_value = 5
    
    result = await threat_service.count_threats(severity="critical")
    
    assert result == 5
    call_args = mock_db_service.count_documents.call_args
    assert call_args[0][1]["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_threats_pagination_offset(threat_service, mock_db_service, sample_threat_data):
    """Test pagination with offset"""
    mock_db_service.find.return_value = [sample_threat_data]
    mock_db_service.count_documents.return_value = 10
    
    result = await threat_service.list_threats(skip=5, limit=5)
    
    # Verify skip parameter was passed
    call_args = mock_db_service.find.call_args
    assert call_args[1]["skip"] == 5
    assert call_args[1]["limit"] == 5


@pytest.mark.asyncio
async def test_create_threat_with_validation(threat_service, mock_db_service):
    """Test threat creation with invalid data raises validation error"""
    with pytest.raises(Exception):  # Pydantic will raise ValidationError
        threat_create = ThreatCreate(
            type="invalid_type",  # Invalid type
            severity="critical",
            description="Test"
        )


@pytest.mark.asyncio
async def test_list_threats_empty_result(threat_service, mock_db_service):
    """Test listing threats when no threats exist"""
    mock_db_service.find.return_value = []
    mock_db_service.count_documents.return_value = 0
    
    result = await threat_service.list_threats()
    
    assert len(result) == 0
