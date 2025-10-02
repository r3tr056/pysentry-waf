"""
Health check system for PySentry WAF.
"""

import asyncio
from enum import Enum
from typing import Dict, List, Optional, Callable, Awaitable
from datetime import datetime
from pydantic import BaseModel


class HealthStatus(str, Enum):
    """Health check status values."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    
    name: str
    status: HealthStatus
    message: Optional[str] = None
    last_check: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict] = None


class HealthCheckResult(BaseModel):
    """Overall system health check result."""
    
    status: HealthStatus
    timestamp: datetime
    components: List[ComponentHealth]
    overall_response_time_ms: float
    
    class Config:
        use_enum_values = True


class HealthCheck:
    """
    Production-grade health check system.
    
    Monitors system components and provides health status endpoints
    for load balancers, orchestrators, and monitoring systems.
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], Awaitable[ComponentHealth]]] = {}
        
    def register_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[ComponentHealth]]
    ):
        """
        Register a health check for a component.
        
        Args:
            name: Component name
            check_func: Async function that returns ComponentHealth
        """
        self._checks[name] = check_func
        
    async def check_component(self, name: str) -> ComponentHealth:
        """
        Check health of a single component.
        
        Args:
            name: Component name
            
        Returns:
            ComponentHealth result
        """
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Component '{name}' not registered",
                last_check=datetime.utcnow()
            )
            
        start_time = datetime.utcnow()
        
        try:
            result = await self._checks[name]()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.response_time_ms = response_time
            result.last_check = datetime.utcnow()
            return result
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                last_check=datetime.utcnow(),
                response_time_ms=response_time
            )
            
    async def check_all(self) -> HealthCheckResult:
        """
        Check health of all registered components.
        
        Returns:
            HealthCheckResult with all component statuses
        """
        start_time = datetime.utcnow()
        
        # Run all checks concurrently
        check_tasks = [
            self.check_component(name)
            for name in self._checks.keys()
        ]
        
        components = await asyncio.gather(*check_tasks)
        
        # Determine overall status
        if all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
            
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheckResult(
            status=overall_status,
            timestamp=datetime.utcnow(),
            components=list(components),
            overall_response_time_ms=response_time
        )
        
    async def check_liveness(self) -> bool:
        """
        Simple liveness check for Kubernetes.
        
        Returns:
            True if service is alive
        """
        return True
        
    async def check_readiness(self) -> bool:
        """
        Readiness check for Kubernetes.
        
        Returns:
            True if service is ready to handle requests
        """
        result = await self.check_all()
        return result.status != HealthStatus.UNHEALTHY


# Singleton instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get the singleton health check instance."""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check


# Common health check implementations
async def check_database_health(db_service) -> ComponentHealth:
    """Check database connectivity."""
    try:
        # Try a simple ping operation
        await db_service.ping()
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection OK",
            last_check=datetime.utcnow()
        )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}",
            last_check=datetime.utcnow()
        )


async def check_redis_health(redis_client) -> ComponentHealth:
    """Check Redis connectivity."""
    try:
        await redis_client.ping()
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection OK",
            last_check=datetime.utcnow()
        )
    except Exception as e:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            last_check=datetime.utcnow()
        )


async def check_ml_model_health(classifier) -> ComponentHealth:
    """Check ML model availability."""
    try:
        # Try a simple prediction
        test_input = ["test"]
        result = classifier.clf.predict(test_input)
        return ComponentHealth(
            name="ml_model",
            status=HealthStatus.HEALTHY,
            message="ML model operational",
            last_check=datetime.utcnow()
        )
    except Exception as e:
        return ComponentHealth(
            name="ml_model",
            status=HealthStatus.UNHEALTHY,
            message=f"ML model check failed: {str(e)}",
            last_check=datetime.utcnow()
        )
