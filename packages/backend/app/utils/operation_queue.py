"""
Database Operation Queue for Resilience

Queues failed database write operations for retry after reconnection.
Persists queue to disk for durability across service restarts.

Validates: Requirements 18.4
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of database operations"""
    POSTGRES_INSERT = "postgres_insert"
    POSTGRES_UPDATE = "postgres_update"
    POSTGRES_DELETE = "postgres_delete"
    MONGODB_INSERT = "mongodb_insert"
    MONGODB_UPDATE = "mongodb_update"
    MONGODB_DELETE = "mongodb_delete"


@dataclass
class QueuedOperation:
    """Represents a queued database operation"""
    operation_id: str
    operation_type: OperationType
    table_or_collection: str
    data: Dict[str, Any]
    timestamp: str
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type.value,
            'table_or_collection': self.table_or_collection,
            'data': self.data,
            'timestamp': self.timestamp,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedOperation':
        """Create from dictionary"""
        return cls(
            operation_id=data['operation_id'],
            operation_type=OperationType(data['operation_type']),
            table_or_collection=data['table_or_collection'],
            data=data['data'],
            timestamp=data['timestamp'],
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )


class DatabaseOperationQueue:
    """
    Queue for failed database operations with disk persistence.
    
    Features:
    - In-memory queue for fast access
    - Disk persistence for durability
    - Automatic retry with exponential backoff
    - Max retry limit to prevent infinite loops
    """
    
    def __init__(self, queue_file: str = "data/operation_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue: List[QueuedOperation] = []
        self.lock = asyncio.Lock()
        self.is_processing = False
        
        # Ensure directory exists
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Database operation queue initialized: {self.queue_file}")
    
    async def enqueue(
        self,
        operation_id: str,
        operation_type: OperationType,
        table_or_collection: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Add a failed operation to the queue.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of database operation
            table_or_collection: Target table or collection name
            data: Operation data
            
        Returns:
            True if successfully queued
        """
        async with self.lock:
            operation = QueuedOperation(
                operation_id=operation_id,
                operation_type=operation_type,
                table_or_collection=table_or_collection,
                data=data,
                timestamp=datetime.utcnow().isoformat()
            )
            
            self.queue.append(operation)
            
            logger.warning(
                f"Queued operation {operation_id} "
                f"({operation_type.value} on {table_or_collection})"
            )
            
            # Persist to disk
            await self._persist_to_disk()
            
            return True
    
    async def dequeue(self) -> Optional[QueuedOperation]:
        """
        Remove and return the next operation from the queue.
        
        Returns:
            QueuedOperation or None if queue is empty
        """
        async with self.lock:
            if not self.queue:
                return None
            
            operation = self.queue.pop(0)
            
            # Persist updated queue to disk
            await self._persist_to_disk()
            
            return operation
    
    async def peek(self) -> Optional[QueuedOperation]:
        """
        View the next operation without removing it.
        
        Returns:
            QueuedOperation or None if queue is empty
        """
        async with self.lock:
            if not self.queue:
                return None
            return self.queue[0]
    
    async def size(self) -> int:
        """Get current queue size"""
        async with self.lock:
            return len(self.queue)
    
    async def clear(self):
        """Clear all operations from the queue"""
        async with self.lock:
            self.queue.clear()
            await self._persist_to_disk()
            logger.info("Operation queue cleared")
    
    async def get_all(self) -> List[QueuedOperation]:
        """Get all queued operations (for inspection)"""
        async with self.lock:
            return self.queue.copy()
    
    async def remove_operation(self, operation_id: str) -> bool:
        """
        Remove a specific operation from the queue.
        
        Args:
            operation_id: ID of operation to remove
            
        Returns:
            True if operation was found and removed
        """
        async with self.lock:
            initial_size = len(self.queue)
            self.queue = [op for op in self.queue if op.operation_id != operation_id]
            
            if len(self.queue) < initial_size:
                await self._persist_to_disk()
                logger.info(f"Removed operation {operation_id} from queue")
                return True
            
            return False
    
    async def increment_retry_count(self, operation_id: str) -> bool:
        """
        Increment retry count for an operation.
        
        Args:
            operation_id: ID of operation
            
        Returns:
            True if operation was found and updated
        """
        async with self.lock:
            for operation in self.queue:
                if operation.operation_id == operation_id:
                    operation.retry_count += 1
                    await self._persist_to_disk()
                    
                    logger.info(
                        f"Operation {operation_id} retry count: "
                        f"{operation.retry_count}/{operation.max_retries}"
                    )
                    
                    return True
            
            return False
    
    async def _persist_to_disk(self):
        """Persist queue to disk for durability"""
        try:
            queue_data = [op.to_dict() for op in self.queue]
            
            async with aiofiles.open(self.queue_file, 'w') as f:
                await f.write(json.dumps(queue_data, indent=2))
            
            logger.debug(f"Persisted {len(self.queue)} operations to disk")
        
        except Exception as e:
            logger.error(f"Failed to persist queue to disk: {e}")
    
    async def load_from_disk(self):
        """Load queue from disk on startup"""
        try:
            if not self.queue_file.exists():
                logger.info("No existing queue file found")
                return
            
            async with aiofiles.open(self.queue_file, 'r') as f:
                content = await f.read()
                queue_data = json.loads(content)
            
            async with self.lock:
                self.queue = [
                    QueuedOperation.from_dict(op_data)
                    for op_data in queue_data
                ]
            
            logger.info(f"Loaded {len(self.queue)} operations from disk")
        
        except Exception as e:
            logger.error(f"Failed to load queue from disk: {e}")
    
    async def process_queue(
        self,
        processor_func,
        max_batch_size: int = 10
    ):
        """
        Process queued operations using provided processor function.
        
        Args:
            processor_func: Async function to process each operation
            max_batch_size: Maximum operations to process in one batch
        """
        if self.is_processing:
            logger.debug("Queue processing already in progress")
            return
        
        self.is_processing = True
        processed_count = 0
        failed_count = 0
        
        try:
            while await self.size() > 0 and processed_count < max_batch_size:
                operation = await self.peek()
                
                if not operation:
                    break
                
                # Check if max retries exceeded
                if operation.retry_count >= operation.max_retries:
                    logger.error(
                        f"Operation {operation.operation_id} exceeded max retries, "
                        f"removing from queue"
                    )
                    await self.dequeue()
                    failed_count += 1
                    continue
                
                try:
                    # Process the operation
                    await processor_func(operation)
                    
                    # Success - remove from queue
                    await self.dequeue()
                    processed_count += 1
                    
                    logger.info(
                        f"Successfully processed queued operation "
                        f"{operation.operation_id}"
                    )
                
                except Exception as e:
                    logger.warning(
                        f"Failed to process operation {operation.operation_id}: {e}"
                    )
                    
                    # Increment retry count
                    await self.increment_retry_count(operation.operation_id)
                    failed_count += 1
                    
                    # Move to end of queue for retry later
                    op = await self.dequeue()
                    if op:
                        async with self.lock:
                            self.queue.append(op)
                            await self._persist_to_disk()
                    
                    # Wait before next retry
                    await asyncio.sleep(2 ** operation.retry_count)
            
            if processed_count > 0 or failed_count > 0:
                logger.info(
                    f"Queue processing complete: "
                    f"{processed_count} processed, {failed_count} failed"
                )
        
        finally:
            self.is_processing = False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self.lock:
            stats = {
                'total_operations': len(self.queue),
                'by_type': {},
                'by_table': {},
                'retry_counts': {}
            }
            
            for operation in self.queue:
                # Count by type
                op_type = operation.operation_type.value
                stats['by_type'][op_type] = stats['by_type'].get(op_type, 0) + 1
                
                # Count by table/collection
                table = operation.table_or_collection
                stats['by_table'][table] = stats['by_table'].get(table, 0) + 1
                
                # Count by retry count
                retry_key = f"retry_{operation.retry_count}"
                stats['retry_counts'][retry_key] = \
                    stats['retry_counts'].get(retry_key, 0) + 1
            
            return stats


# Global operation queue instance
operation_queue = DatabaseOperationQueue()


async def initialize_operation_queue():
    """Initialize the operation queue on startup"""
    await operation_queue.load_from_disk()
    logger.info("Operation queue initialized and loaded from disk")


async def shutdown_operation_queue():
    """Shutdown the operation queue gracefully"""
    await operation_queue._persist_to_disk()
    logger.info("Operation queue persisted to disk on shutdown")
