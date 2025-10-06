"""
Tests for batch processor.
"""

import pytest
import asyncio
from pysentry.performance.batch_processor import BatchProcessor, BatchOperation
from datetime import datetime


@pytest.fixture
def batch_processor():
    """Create batch processor for testing."""
    return BatchProcessor(
        batch_size=10,
        batch_timeout=0.1,
        max_queue_size=100
    )


@pytest.mark.asyncio
async def test_batch_processor_initialization(batch_processor):
    """Test batch processor initialization."""
    assert batch_processor.batch_size == 10
    assert batch_processor.batch_timeout == 0.1
    assert batch_processor.total_batches_processed == 0


@pytest.mark.asyncio
async def test_add_insert(batch_processor):
    """Test adding insert operation."""
    success = await batch_processor.add_insert(
        'test_collection',
        {'name': 'test', 'value': 123}
    )
    
    assert success is True
    queue = batch_processor.queues['test_collection']
    assert queue.qsize() == 1


@pytest.mark.asyncio
async def test_add_update(batch_processor):
    """Test adding update operation."""
    success = await batch_processor.add_update(
        'test_collection',
        {'id': '123'},
        {'$set': {'value': 456}}
    )
    
    assert success is True


@pytest.mark.asyncio
async def test_add_delete(batch_processor):
    """Test adding delete operation."""
    success = await batch_processor.add_delete(
        'test_collection',
        {'id': '123'}
    )
    
    assert success is True


@pytest.mark.asyncio
async def test_batch_processing(batch_processor):
    """Test batch processing."""
    processed_operations = []
    
    async def mock_db_executor(operation, collection, *args):
        processed_operations.append({
            'operation': operation,
            'collection': collection,
            'args': args
        })
    
    # Start processor
    processor_task = asyncio.create_task(
        batch_processor.start_processor('test_collection', mock_db_executor)
    )
    
    # Add operations
    for i in range(5):
        await batch_processor.add_insert(
            'test_collection',
            {'id': i, 'value': f'val-{i}'}
        )
    
    # Wait for processing
    await asyncio.sleep(0.3)
    
    # Stop processor
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Check processing occurred
    assert len(processed_operations) > 0


@pytest.mark.asyncio
async def test_batch_size_trigger(batch_processor):
    """Test batch triggers when size is reached."""
    processed_count = []
    
    async def mock_db_executor(operation, collection, *args):
        if operation == 'insert_many':
            processed_count.append(len(args[0]))
    
    processor_task = asyncio.create_task(
        batch_processor.start_processor('test_collection', mock_db_executor)
    )
    
    # Add exact batch size
    for i in range(10):
        await batch_processor.add_insert('test_collection', {'id': i})
    
    await asyncio.sleep(0.2)
    
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Should have processed a batch
    assert batch_processor.total_batches_processed >= 1


@pytest.mark.asyncio
async def test_timeout_trigger(batch_processor):
    """Test batch triggers on timeout."""
    processed_count = []
    
    async def mock_db_executor(operation, collection, *args):
        processed_count.append(True)
    
    processor_task = asyncio.create_task(
        batch_processor.start_processor('test_collection', mock_db_executor)
    )
    
    # Add fewer than batch size
    for i in range(3):
        await batch_processor.add_insert('test_collection', {'id': i})
    
    # Wait for timeout
    await asyncio.sleep(0.25)
    
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Should have processed despite not reaching batch size
    assert len(processed_count) > 0


@pytest.mark.asyncio
async def test_multiple_collections(batch_processor):
    """Test handling multiple collections."""
    await batch_processor.add_insert('collection1', {'data': '1'})
    await batch_processor.add_insert('collection2', {'data': '2'})
    
    assert 'collection1' in batch_processor.queues
    assert 'collection2' in batch_processor.queues


@pytest.mark.asyncio
async def test_get_stats(batch_processor):
    """Test statistics retrieval."""
    # Add some operations
    await batch_processor.add_insert('test_collection', {'id': 1})
    
    stats = batch_processor.get_stats()
    
    assert 'total_batches_processed' in stats
    assert 'total_operations_processed' in stats
    assert 'queue_sizes' in stats
    assert 'batch_size' in stats


@pytest.mark.asyncio
async def test_stop_all_processors(batch_processor):
    """Test stopping all processors."""
    async def mock_db_executor(operation, collection, *args):
        pass
    
    batch_processor.start_all_processors(
        ['col1', 'col2'],
        mock_db_executor
    )
    
    assert len(batch_processor._tasks) == 2
    
    await batch_processor.stop_all_processors()
    
    assert len(batch_processor._tasks) == 0
