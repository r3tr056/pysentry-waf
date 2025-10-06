"""
Async request processor for high-throughput WAF operations.

Provides asynchronous classification, parallel ML inference, and batch processing.
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import multiprocessing as mp


@dataclass
class ProcessingResult:
    """Result from async processing."""
    request_id: str
    is_threat: bool
    threat_types: List[str]
    confidence: float
    processing_time_ms: float
    timestamp: datetime


class AsyncRequestProcessor:
    """
    Async processor for WAF request classification.
    
    Uses process pools for CPU-bound ML inference and thread pools
    for I/O-bound operations.
    """
    
    def __init__(
        self,
        num_workers: Optional[int] = None,
        max_queue_size: int = 1000,
        batch_size: int = 10,
        batch_timeout: float = 0.1
    ):
        """
        Initialize async processor.
        
        Args:
            num_workers: Number of worker processes (default: CPU count)
            max_queue_size: Maximum queue size for backpressure
            batch_size: Size of batches for processing
            batch_timeout: Timeout for batch accumulation in seconds
        """
        self.num_workers = num_workers or mp.cpu_count()
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Process pool for CPU-bound ML inference
        self.process_pool = ProcessPoolExecutor(max_workers=self.num_workers)
        
        # Thread pool for I/O operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.num_workers * 2)
        
        # Processing queue
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # Stats
        self.total_processed = 0
        self.total_threats_detected = 0
        
    async def classify_request_async(
        self,
        request_data: Dict[str, Any],
        classifier_fn: Callable
    ) -> ProcessingResult:
        """
        Classify a single request asynchronously.
        
        Args:
            request_data: Request data to classify
            classifier_fn: Classification function to use
            
        Returns:
            ProcessingResult with classification results
        """
        start_time = datetime.now(timezone.utc)
        request_id = request_data.get('id', 'unknown')
        
        # Run classifier in process pool (CPU-bound)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.process_pool,
            classifier_fn,
            request_data
        )
        
        end_time = datetime.now(timezone.utc)
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        is_threat = result.get('is_threat', False)
        threat_types = result.get('threat_types', [])
        
        self.total_processed += 1
        if is_threat:
            self.total_threats_detected += 1
        
        return ProcessingResult(
            request_id=request_id,
            is_threat=is_threat,
            threat_types=threat_types,
            confidence=result.get('confidence', 0.0),
            processing_time_ms=processing_time,
            timestamp=end_time
        )
    
    async def classify_batch_async(
        self,
        requests: List[Dict[str, Any]],
        classifier_fn: Callable
    ) -> List[ProcessingResult]:
        """
        Classify multiple requests in parallel.
        
        Args:
            requests: List of request data to classify
            classifier_fn: Classification function to use
            
        Returns:
            List of ProcessingResult objects
        """
        tasks = [
            self.classify_request_async(req, classifier_fn)
            for req in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_results = [r for r in results if isinstance(r, ProcessingResult)]
        return valid_results
    
    async def start_batch_processor(
        self,
        classifier_fn: Callable,
        result_callback: Optional[Callable] = None
    ):
        """
        Start batch processor that accumulates requests and processes in batches.
        
        Args:
            classifier_fn: Classification function to use
            result_callback: Optional callback for processing results
        """
        batch = []
        last_batch_time = datetime.now(timezone.utc)
        
        while True:
            try:
                # Try to get item with timeout
                try:
                    item = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=self.batch_timeout
                    )
                    batch.append(item)
                except asyncio.TimeoutError:
                    pass
                
                # Process batch if full or timeout exceeded
                current_time = datetime.now(timezone.utc)
                time_since_last = (current_time - last_batch_time).total_seconds()
                
                should_process = (
                    len(batch) >= self.batch_size or
                    (len(batch) > 0 and time_since_last >= self.batch_timeout)
                )
                
                if should_process:
                    results = await self.classify_batch_async(batch, classifier_fn)
                    
                    if result_callback:
                        await result_callback(results)
                    
                    batch = []
                    last_batch_time = current_time
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error and continue
                print(f"Error in batch processor: {e}")
                continue
    
    async def submit_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Submit a request for async processing.
        
        Args:
            request_data: Request data to process
            
        Returns:
            True if queued successfully, False if queue is full
        """
        try:
            await self.queue.put(request_data)
            return True
        except asyncio.QueueFull:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'total_processed': self.total_processed,
            'total_threats_detected': self.total_threats_detected,
            'queue_size': self.queue.qsize(),
            'queue_max_size': self.max_queue_size,
            'num_workers': self.num_workers,
            'batch_size': self.batch_size
        }
    
    async def shutdown(self):
        """Gracefully shutdown the processor."""
        self.process_pool.shutdown(wait=True)
        self.thread_pool.shutdown(wait=True)
