"""
Tests for async request processor.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from pysentry.performance.async_processor import (
    AsyncRequestProcessor,
    ProcessingResult
)


@pytest.fixture
def async_processor():
    """Create async processor for testing."""
    return AsyncRequestProcessor(
        num_workers=2,
        max_queue_size=100,
        batch_size=5,
        batch_timeout=0.1
    )


def dummy_classifier(request_data):
    """Dummy classifier for testing."""
    return {
        'is_threat': request_data.get('malicious', False),
        'threat_types': ['test_threat'] if request_data.get('malicious') else [],
        'confidence': 0.9 if request_data.get('malicious') else 0.1
    }


@pytest.mark.asyncio
async def test_async_processor_initialization(async_processor):
    """Test async processor initialization."""
    assert async_processor.num_workers == 2
    assert async_processor.max_queue_size == 100
    assert async_processor.batch_size == 5
    assert async_processor.total_processed == 0
    
@pytest.mark.asyncio
async def test_classify_request_async(async_processor):
    """Test async request classification."""
    request_data = {
        'id': 'test-123',
        'path': '/api/test',
        'malicious': False
    }
    
    result = await async_processor.classify_request_async(
        request_data,
        dummy_classifier
    )
    
    assert isinstance(result, ProcessingResult)
    assert result.request_id == 'test-123'
    assert result.is_threat is False
    assert result.processing_time_ms > 0
    assert isinstance(result.timestamp, datetime)


@pytest.mark.asyncio
async def test_classify_threat_request(async_processor):
    """Test classification of malicious request."""
    request_data = {
        'id': 'threat-456',
        'path': '/api/admin',
        'malicious': True
    }
    
    result = await async_processor.classify_request_async(
        request_data,
        dummy_classifier
    )
    
    assert result.is_threat is True
    assert 'test_threat' in result.threat_types
    assert result.confidence == 0.9
    assert async_processor.total_threats_detected == 1


@pytest.mark.asyncio
async def test_classify_batch_async(async_processor):
    """Test batch classification."""
    requests = [
        {'id': f'req-{i}', 'malicious': i % 2 == 0}
        for i in range(10)
    ]
    
    results = await async_processor.classify_batch_async(
        requests,
        dummy_classifier
    )
    
    assert len(results) == 10
    threat_count = sum(1 for r in results if r.is_threat)
    assert threat_count == 5  # Every other request


@pytest.mark.asyncio
async def test_submit_request(async_processor):
    """Test request submission to queue."""
    request_data = {'id': 'queued-1', 'path': '/test'}
    
    success = await async_processor.submit_request(request_data)
    assert success is True
    assert async_processor.queue.qsize() == 1


@pytest.mark.asyncio
async def test_queue_full_handling(async_processor):
    """Test handling of full queue."""
    # Fill the queue
    for i in range(100):
        await async_processor.submit_request({'id': f'req-{i}'})
    
    # Try to add more
    success = await async_processor.submit_request({'id': 'overflow'})
    assert success is False


@pytest.mark.asyncio
async def test_get_stats(async_processor):
    """Test statistics retrieval."""
    # Process some requests
    await async_processor.classify_request_async(
        {'id': 'test', 'malicious': True},
        dummy_classifier
    )
    
    stats = async_processor.get_stats()
    
    assert 'total_processed' in stats
    assert 'total_threats_detected' in stats
    assert 'queue_size' in stats
    assert stats['total_processed'] == 1
    assert stats['total_threats_detected'] == 1
    assert stats['num_workers'] == 2


@pytest.mark.asyncio
async def test_batch_processor_accumulation(async_processor):
    """Test batch processor accumulates requests."""
    results_collected = []
    
    async def result_callback(results):
        results_collected.extend(results)
    
    # Start batch processor
    processor_task = asyncio.create_task(
        async_processor.start_batch_processor(
            dummy_classifier,
            result_callback
        )
    )
    
    # Submit requests
    for i in range(3):
        await async_processor.submit_request({'id': f'batch-{i}'})
    
    # Wait for processing
    await asyncio.sleep(0.3)
    
    # Cancel processor
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Some results should have been processed
    assert len(results_collected) > 0


@pytest.mark.asyncio
async def test_batch_timeout_triggers_processing(async_processor):
    """Test batch processing triggers on timeout."""
    results_collected = []
    
    async def result_callback(results):
        results_collected.extend(results)
    
    processor_task = asyncio.create_task(
        async_processor.start_batch_processor(
            dummy_classifier,
            result_callback
        )
    )
    
    # Submit just 2 requests (below batch size of 5)
    await async_processor.submit_request({'id': 'timeout-1'})
    await asyncio.sleep(0.05)
    await async_processor.submit_request({'id': 'timeout-2'})
    
    # Wait for timeout to trigger
    await asyncio.sleep(0.2)
    
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Should have processed despite not reaching batch size
    assert len(results_collected) == 2


@pytest.mark.asyncio
async def test_shutdown(async_processor):
    """Test graceful shutdown."""
    # Submit some requests
    await async_processor.submit_request({'id': 'shutdown-test'})
    
    # Shutdown
    await async_processor.shutdown()
    
    # Executors should be shutdown
    assert async_processor.process_pool._shutdown is True
