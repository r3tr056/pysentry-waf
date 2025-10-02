"""Tests for health check system."""

import pytest
from datetime import datetime
from pysentry.monitoring.health import (
    HealthStatus,
    ComponentHealth,
    HealthCheckResult,
    HealthCheck,
    get_health_check
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestComponentHealth:
    """Tests for ComponentHealth model."""
    
    def test_component_health_creation(self):
        """Test creating ComponentHealth."""
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connection OK",
            last_check=datetime.utcnow()
        )
        
        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Connection OK"
        
    def test_component_health_with_details(self):
        """Test ComponentHealth with details."""
        health = ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            last_check=datetime.utcnow(),
            response_time_ms=15.5,
            details={"connections": 10}
        )
        
        assert health.response_time_ms == 15.5
        assert health.details["connections"] == 10


class TestHealthCheckResult:
    """Tests for HealthCheckResult model."""
    
    def test_health_check_result_creation(self):
        """Test creating HealthCheckResult."""
        components = [
            ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
        ]
        
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            timestamp=datetime.utcnow(),
            components=components,
            overall_response_time_ms=25.0
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 1


class TestHealthCheck:
    """Tests for HealthCheck class."""
    
    def setup_method(self):
        """Setup health check instance."""
        self.health_check = HealthCheck()
        
    @pytest.mark.asyncio
    async def test_register_check(self):
        """Test registering a health check."""
        async def mock_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("test", mock_check)
        assert "test" in self.health_check._checks
        
    @pytest.mark.asyncio
    async def test_check_component_success(self):
        """Test successful component check."""
        async def mock_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                message="OK",
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("test", mock_check)
        result = await self.health_check.check_component("test")
        
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None
        
    @pytest.mark.asyncio
    async def test_check_component_failure(self):
        """Test component check with failure."""
        async def failing_check():
            raise Exception("Connection failed")
            
        self.health_check.register_check("failing", failing_check)
        result = await self.health_check.check_component("failing")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message
        
    @pytest.mark.asyncio
    async def test_check_component_not_registered(self):
        """Test checking unregistered component."""
        result = await self.health_check.check_component("nonexistent")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "not registered" in result.message
        
    @pytest.mark.asyncio
    async def test_check_all_healthy(self):
        """Test check_all with all healthy components."""
        async def healthy_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("component1", healthy_check)
        self.health_check.register_check("component2", healthy_check)
        
        result = await self.health_check.check_all()
        
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 2
        
    @pytest.mark.asyncio
    async def test_check_all_degraded(self):
        """Test check_all with degraded component."""
        async def healthy_check():
            return ComponentHealth(
                name="healthy",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
            
        async def degraded_check():
            return ComponentHealth(
                name="degraded",
                status=HealthStatus.DEGRADED,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("component1", healthy_check)
        self.health_check.register_check("component2", degraded_check)
        
        result = await self.health_check.check_all()
        
        assert result.status == HealthStatus.DEGRADED
        
    @pytest.mark.asyncio
    async def test_check_all_unhealthy(self):
        """Test check_all with unhealthy component."""
        async def healthy_check():
            return ComponentHealth(
                name="healthy",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
            
        async def unhealthy_check():
            return ComponentHealth(
                name="unhealthy",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("component1", healthy_check)
        self.health_check.register_check("component2", unhealthy_check)
        
        result = await self.health_check.check_all()
        
        assert result.status == HealthStatus.UNHEALTHY
        
    @pytest.mark.asyncio
    async def test_check_liveness(self):
        """Test liveness check."""
        result = await self.health_check.check_liveness()
        assert result is True
        
    @pytest.mark.asyncio
    async def test_check_readiness_healthy(self):
        """Test readiness check when healthy."""
        async def healthy_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("test", healthy_check)
        result = await self.health_check.check_readiness()
        assert result is True
        
    @pytest.mark.asyncio
    async def test_check_readiness_unhealthy(self):
        """Test readiness check when unhealthy."""
        async def unhealthy_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow()
            )
            
        self.health_check.register_check("test", unhealthy_check)
        result = await self.health_check.check_readiness()
        assert result is False


class TestGetHealthCheck:
    """Tests for get_health_check singleton."""
    
    def test_singleton_instance(self):
        """Test singleton pattern."""
        instance1 = get_health_check()
        instance2 = get_health_check()
        
        assert instance1 is instance2
