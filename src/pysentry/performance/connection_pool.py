"""
Database connection pool manager.

Provides connection pooling for MongoDB and PostgreSQL with health checks,
automatic reconnection, and load balancing.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class ConnectionStats:
    """Connection statistics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    total_queries: int
    failed_queries: int
    avg_query_time_ms: float


class DatabaseConnectionPool:
    """
    Database connection pool manager.
    
    Manages a pool of database connections with health checks,
    automatic reconnection, and connection reuse.
    """
    
    def __init__(
        self,
        connection_string: str,
        min_size: int = 5,
        max_size: int = 20,
        max_idle_time: int = 300,
        health_check_interval: int = 60
    ):
        """
        Initialize connection pool.
        
        Args:
            connection_string: Database connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time before connection is closed (seconds)
            health_check_interval: Health check interval (seconds)
        """
        self.connection_string = connection_string
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        
        # Connection pool
        self._pool: List[Any] = []
        self._available_connections: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._lock = asyncio.Lock()
        
        # Stats
        self.total_queries = 0
        self.failed_queries = 0
        self.total_query_time = 0.0
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def _create_connection(self) -> Any:
        """Create a new database connection."""
        # This is a placeholder - actual implementation depends on database type
        # For MongoDB:
        # from motor.motor_asyncio import AsyncIOMotorClient
        # return AsyncIOMotorClient(self.connection_string)
        
        # For PostgreSQL:
        # import asyncpg
        # return await asyncpg.connect(self.connection_string)
        
        return {'connection_string': self.connection_string, 'created_at': datetime.now(timezone.utc)}
    
    async def _close_connection(self, connection: Any):
        """Close a database connection."""
        # Placeholder - implement based on database type
        pass
    
    async def initialize(self):
        """Initialize the connection pool."""
        async with self._lock:
            # Create minimum connections
            for _ in range(self.min_size):
                conn = await self._create_connection()
                self._pool.append(conn)
                await self._available_connections.put(conn)
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.
        
        Yields:
            Database connection
        """
        # Get connection from pool or create new one
        try:
            connection = await asyncio.wait_for(
                self._available_connections.get(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            # Pool exhausted, create temporary connection
            if len(self._pool) < self.max_size:
                async with self._lock:
                    connection = await self._create_connection()
                    self._pool.append(connection)
            else:
                raise RuntimeError("Connection pool exhausted")
        
        try:
            yield connection
        finally:
            # Return connection to pool
            await self._available_connections.put(connection)
    
    async def execute_query(
        self,
        query_fn: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a query using a pooled connection.
        
        Args:
            query_fn: Query function to execute
            *args: Positional arguments for query function
            **kwargs: Keyword arguments for query function
            
        Returns:
            Query result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            async with self.acquire() as connection:
                result = await query_fn(connection, *args, **kwargs)
                
                # Update stats
                end_time = datetime.now(timezone.utc)
                query_time = (end_time - start_time).total_seconds() * 1000
                
                self.total_queries += 1
                self.total_query_time += query_time
                
                return result
                
        except Exception as e:
            self.failed_queries += 1
            raise e
    
    async def _health_check_loop(self):
        """Periodically check connection health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check each connection
                unhealthy = []
                for conn in self._pool:
                    if not await self._is_connection_healthy(conn):
                        unhealthy.append(conn)
                
                # Remove unhealthy connections
                for conn in unhealthy:
                    self._pool.remove(conn)
                    await self._close_connection(conn)
                
                # Recreate minimum connections if needed
                while len(self._pool) < self.min_size:
                    conn = await self._create_connection()
                    self._pool.append(conn)
                    await self._available_connections.put(conn)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error: {e}")
                continue
    
    async def _is_connection_healthy(self, connection: Any) -> bool:
        """Check if a connection is healthy."""
        # Placeholder - implement based on database type
        # For MongoDB: try to ping
        # For PostgreSQL: try simple query
        return True
    
    async def close(self):
        """Close all connections and cleanup."""
        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for conn in self._pool:
            await self._close_connection(conn)
        
        self._pool.clear()
    
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics."""
        active = len(self._pool) - self._available_connections.qsize()
        idle = self._available_connections.qsize()
        
        avg_query_time = (
            self.total_query_time / self.total_queries
            if self.total_queries > 0
            else 0.0
        )
        
        return ConnectionStats(
            total_connections=len(self._pool),
            active_connections=active,
            idle_connections=idle,
            total_queries=self.total_queries,
            failed_queries=self.failed_queries,
            avg_query_time_ms=avg_query_time
        )


# Global connection pools
_connection_pools: Dict[str, DatabaseConnectionPool] = {}


async def get_connection_pool(
    name: str,
    connection_string: str,
    **kwargs
) -> DatabaseConnectionPool:
    """
    Get or create a connection pool.
    
    Args:
        name: Pool name
        connection_string: Database connection string
        **kwargs: Additional pool configuration
        
    Returns:
        DatabaseConnectionPool instance
    """
    if name not in _connection_pools:
        pool = DatabaseConnectionPool(connection_string, **kwargs)
        await pool.initialize()
        _connection_pools[name] = pool
    
    return _connection_pools[name]


async def close_all_pools():
    """Close all connection pools."""
    for pool in _connection_pools.values():
        await pool.close()
    _connection_pools.clear()
