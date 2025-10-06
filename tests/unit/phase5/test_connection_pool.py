"""
Tests for database connection pool.
"""

import pytest
import asyncio
from pysentry.performance.connection_pool import (
    DatabaseConnectionPool,
    ConnectionStats,
    get_connection_pool,
    close_all_pools
)


@pytest.fixture
def connection_pool():
    """Create connection pool for testing (sync fixture)."""
    import asyncio
    pool = DatabaseConnectionPool(
        connection_string='test://localhost',
        min_size=2,
        max_size=5,
        max_idle_time=60,
        health_check_interval=30
    )
    # Initialize synchronously
    loop = asyncio.new_event_loop()
    loop.run_until_complete(pool.initialize())
    
    yield pool
    
    # Cleanup
    loop.run_until_complete(pool.close())
    loop.close()


@pytest.mark.asyncio
async def test_connection_pool_initialization(connection_pool):
    """Test connection pool initialization."""
    assert connection_pool.min_size == 2
    assert connection_pool.max_size == 5
    assert len(connection_pool._pool) >= 2


@pytest.mark.asyncio
async def test_acquire_connection(connection_pool):
    """Test acquiring connection from pool."""
    async with connection_pool.acquire() as conn:
        assert conn is not None
        assert 'connection_string' in conn


@pytest.mark.asyncio
async def test_connection_reuse(connection_pool):
    """Test connection is returned to pool after use."""
    initial_available = connection_pool._available_connections.qsize()
    
    async with connection_pool.acquire() as conn:
        pass
    
    # Connection should be returned
    final_available = connection_pool._available_connections.qsize()
    assert final_available == initial_available


@pytest.mark.asyncio
async def test_execute_query(connection_pool):
    """Test executing query with pooled connection."""
    async def mock_query(conn, value):
        return {'result': value * 2}
    
    result = await connection_pool.execute_query(mock_query, 21)
    
    assert result == {'result': 42}
    assert connection_pool.total_queries == 1


@pytest.mark.asyncio
async def test_query_stats_tracking(connection_pool):
    """Test query statistics are tracked."""
    async def mock_query(conn):
        await asyncio.sleep(0.01)
        return 'success'
    
    await connection_pool.execute_query(mock_query)
    
    stats = connection_pool.get_stats()
    assert stats.total_queries == 1
    assert stats.failed_queries == 0
    assert stats.avg_query_time_ms > 0


@pytest.mark.asyncio
async def test_failed_query_tracking(connection_pool):
    """Test failed queries are tracked."""
    async def failing_query(conn):
        raise ValueError("Query failed")
    
    with pytest.raises(ValueError):
        await connection_pool.execute_query(failing_query)
    
    assert connection_pool.failed_queries == 1


@pytest.mark.asyncio
async def test_get_stats(connection_pool):
    """Test statistics retrieval."""
    stats = connection_pool.get_stats()
    
    assert isinstance(stats, ConnectionStats)
    assert stats.total_connections >= 2
    assert stats.idle_connections > 0
    assert stats.total_queries == 0


@pytest.mark.asyncio
async def test_concurrent_acquisitions(connection_pool):
    """Test concurrent connection acquisitions."""
    async def use_connection(delay):
        async with connection_pool.acquire() as conn:
            await asyncio.sleep(delay)
            return conn
    
    # Start multiple concurrent operations
    tasks = [use_connection(0.01) for _ in range(3)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_get_connection_pool_global():
    """Test global connection pool management."""
    pool1 = await get_connection_pool(
        'test_pool',
        'test://localhost',
        min_size=1,
        max_size=3
    )
    
    # Getting same pool should return same instance
    pool2 = await get_connection_pool('test_pool', 'test://localhost')
    
    assert pool1 is pool2
    
    await close_all_pools()


@pytest.mark.asyncio
async def test_close_pool(connection_pool):
    """Test pool closure."""
    await connection_pool.close()
    
    # Health check task should be cancelled
    if connection_pool._health_check_task:
        assert connection_pool._health_check_task.cancelled()


@pytest.mark.asyncio
async def test_pool_exhaustion_handling():
    """Test handling when pool is exhausted."""
    pool = DatabaseConnectionPool(
        connection_string='test://localhost',
        min_size=1,
        max_size=2,
        max_idle_time=60
    )
    await pool.initialize()
    
    try:
        # Acquire all connections
        conn1_cm = pool.acquire()
        conn1 = await conn1_cm.__aenter__()
        
        conn2_cm = pool.acquire()
        conn2 = await conn2_cm.__aenter__()
        
        # Try to acquire one more (should timeout)
        with pytest.raises(RuntimeError):
            async with pool.acquire() as conn:
                pass
        
        # Release connections
        await conn1_cm.__aexit__(None, None, None)
        await conn2_cm.__aexit__(None, None, None)
    
    finally:
        await pool.close()
