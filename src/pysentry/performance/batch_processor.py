"""
Batch processor for efficient database operations.

Provides batch insert, update, and delete operations with configurable
batch sizes and timeouts.
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class BatchOperation:
    """Represents a batch operation."""
    operation_type: str  # 'insert', 'update', 'delete'
    collection: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BatchProcessor:
    """
    Batch processor for efficient database operations.
    
    Accumulates operations and executes them in batches to reduce
    database round-trips and improve throughput.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
        max_queue_size: int = 10000
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of operations per batch
            batch_timeout: Maximum time to wait before processing batch (seconds)
            max_queue_size: Maximum queue size for backpressure
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_queue_size = max_queue_size
        
        # Queues by collection
        self.queues: Dict[str, asyncio.Queue] = defaultdict(
            lambda: asyncio.Queue(maxsize=max_queue_size)
        )
        
        # Stats
        self.total_batches_processed = 0
        self.total_operations_processed = 0
        self.failed_operations = 0
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
    
    async def add_insert(
        self,
        collection: str,
        document: Dict[str, Any]
    ) -> bool:
        """
        Add insert operation to batch.
        
        Args:
            collection: Collection name
            document: Document to insert
            
        Returns:
            True if queued successfully
        """
        operation = BatchOperation(
            operation_type='insert',
            collection=collection,
            data=document
        )
        
        try:
            await self.queues[collection].put(operation)
            return True
        except asyncio.QueueFull:
            return False
    
    async def add_update(
        self,
        collection: str,
        filter_query: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Add update operation to batch.
        
        Args:
            collection: Collection name
            filter_query: Filter for update
            update_data: Update data
            
        Returns:
            True if queued successfully
        """
        operation = BatchOperation(
            operation_type='update',
            collection=collection,
            data={'filter': filter_query, 'update': update_data}
        )
        
        try:
            await self.queues[collection].put(operation)
            return True
        except asyncio.QueueFull:
            return False
    
    async def add_delete(
        self,
        collection: str,
        filter_query: Dict[str, Any]
    ) -> bool:
        """
        Add delete operation to batch.
        
        Args:
            collection: Collection name
            filter_query: Filter for deletion
            
        Returns:
            True if queued successfully
        """
        operation = BatchOperation(
            operation_type='delete',
            collection=collection,
            data={'filter': filter_query}
        )
        
        try:
            await self.queues[collection].put(operation)
            return True
        except asyncio.QueueFull:
            return False
    
    async def _process_batch(
        self,
        collection: str,
        operations: List[BatchOperation],
        db_executor: Callable
    ):
        """
        Process a batch of operations.
        
        Args:
            collection: Collection name
            operations: List of operations to process
            db_executor: Database executor function
        """
        if not operations:
            return
        
        # Group by operation type
        inserts = [op.data for op in operations if op.operation_type == 'insert']
        updates = [op.data for op in operations if op.operation_type == 'update']
        deletes = [op.data for op in operations if op.operation_type == 'delete']
        
        try:
            # Execute batch operations
            if inserts:
                await db_executor('insert_many', collection, inserts)
            
            if updates:
                for update_op in updates:
                    await db_executor(
                        'update_one',
                        collection,
                        update_op['filter'],
                        update_op['update']
                    )
            
            if deletes:
                for delete_op in deletes:
                    await db_executor('delete_one', collection, delete_op['filter'])
            
            self.total_batches_processed += 1
            self.total_operations_processed += len(operations)
            
        except Exception as e:
            self.failed_operations += len(operations)
            print(f"Batch processing error for {collection}: {e}")
    
    async def start_processor(
        self,
        collection: str,
        db_executor: Callable
    ):
        """
        Start batch processor for a collection.
        
        Args:
            collection: Collection name to process
            db_executor: Database executor function
        """
        queue = self.queues[collection]
        batch = []
        last_batch_time = datetime.now(timezone.utc)
        
        while True:
            try:
                # Try to get item with timeout
                try:
                    operation = await asyncio.wait_for(
                        queue.get(),
                        timeout=self.batch_timeout
                    )
                    batch.append(operation)
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
                    await self._process_batch(collection, batch, db_executor)
                    batch = []
                    last_batch_time = current_time
                    
            except asyncio.CancelledError:
                # Process remaining batch before exiting
                if batch:
                    await self._process_batch(collection, batch, db_executor)
                break
            except Exception as e:
                print(f"Error in batch processor for {collection}: {e}")
                continue
    
    def start_all_processors(
        self,
        collections: List[str],
        db_executor: Callable
    ):
        """
        Start batch processors for multiple collections.
        
        Args:
            collections: List of collection names
            db_executor: Database executor function
        """
        for collection in collections:
            task = asyncio.create_task(
                self.start_processor(collection, db_executor)
            )
            self._tasks.append(task)
    
    async def stop_all_processors(self):
        """Stop all batch processors gracefully."""
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics."""
        queue_sizes = {
            collection: queue.qsize()
            for collection, queue in self.queues.items()
        }
        
        success_rate = (
            (self.total_operations_processed - self.failed_operations) /
            self.total_operations_processed
            if self.total_operations_processed > 0
            else 0
        )
        
        return {
            'total_batches_processed': self.total_batches_processed,
            'total_operations_processed': self.total_operations_processed,
            'failed_operations': self.failed_operations,
            'success_rate': success_rate,
            'queue_sizes': queue_sizes,
            'batch_size': self.batch_size,
            'batch_timeout': self.batch_timeout
        }
