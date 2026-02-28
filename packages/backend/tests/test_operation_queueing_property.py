"""
Property-Based Tests for Database Operation Queueing

Feature: production-ready-browser-extension
Property 39: Database Operation Queueing on Failure

For any database write operation that fails due to connection loss,
the operation should be queued in memory and retried after reconnection
is established.

**Validates: Requirements 18.4**
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from app.utils.operation_queue import (
    DatabaseOperationQueue,
    QueuedOperation,
    OperationType
)


@given(
    operation_id=st.text(min_size=1, max_size=50),
    table_name=st.text(min_size=1, max_size=50),
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans()
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=50, deadline=None)
def test_enqueue_persists_operation(
    operation_id: str,
    table_name: str,
    data: dict
):
    """
    Property: Enqueuing an operation adds it to the queue.
    
    For any valid operation, enqueuing should add it to the queue
    and the queue size should increase by 1.
    
    **Validates: Requirements 18.4**
    """
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "test_queue.json"
            queue = DatabaseOperationQueue(str(queue_file))
            
            initial_size = await queue.size()
            
            # Enqueue operation
            success = await queue.enqueue(
                operation_id=operation_id,
                operation_type=OperationType.POSTGRES_INSERT,
                table_or_collection=table_name,
                data=data
            )
            
            assert success, "Enqueue should return True"
            
            # Verify size increased
            new_size = await queue.size()
            assert new_size == initial_size + 1, \
                f"Queue size should increase by 1 (was {initial_size}, now {new_size})"
    
    asyncio.run(run_test())


@given(
    num_operations=st.integers(min_value=1, max_value=15)
)
@settings(max_examples=50, deadline=None)
def test_dequeue_removes_operations_in_order(
    num_operations: int
):
    """
    Property: Dequeuing removes operations in FIFO order.
    
    For any number of operations N, dequeuing N times should
    return operations in the same order they were enqueued.
    
    **Validates: Requirements 18.4**
    """
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "test_queue.json"
            queue = DatabaseOperationQueue(str(queue_file))
            
            # Enqueue operations
            operation_ids = []
            for i in range(num_operations):
                op_id = f"op_{i}"
                operation_ids.append(op_id)
                await queue.enqueue(
                    operation_id=op_id,
                    operation_type=OperationType.POSTGRES_INSERT,
                    table_or_collection="test_table",
                    data={"index": i}
                )
            
            # Dequeue and verify order
            dequeued_ids = []
            for _ in range(num_operations):
                operation = await queue.dequeue()
                assert operation is not None
                dequeued_ids.append(operation.operation_id)
            
            assert dequeued_ids == operation_ids, \
                "Operations should be dequeued in FIFO order"
    
    asyncio.run(run_test())


@given(
    num_operations=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=None)
def test_queue_persists_to_disk(
    num_operations: int
):
    """
    Property: Queue persists to disk for durability.
    
    For any number of operations N, after enqueuing and reloading,
    all N operations should be restored from disk.
    
    **Validates: Requirements 18.4**
    """
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "test_queue.json"
            
            # Create queue and enqueue operations
            queue1 = DatabaseOperationQueue(str(queue_file))
            operation_ids = []
            
            for i in range(num_operations):
                op_id = f"op_{i}"
                operation_ids.append(op_id)
                await queue1.enqueue(
                    operation_id=op_id,
                    operation_type=OperationType.MONGODB_INSERT,
                    table_or_collection="test_collection",
                    data={"value": i}
                )
            
            # Verify file exists
            assert queue_file.exists(), "Queue file should exist on disk"
            
            # Create new queue instance and load from disk
            queue2 = DatabaseOperationQueue(str(queue_file))
            await queue2.load_from_disk()
            
            # Verify all operations were restored
            restored_size = await queue2.size()
            assert restored_size == num_operations, \
                f"All {num_operations} operations should be restored from disk"
            
            # Verify operation IDs match
            restored_ops = await queue2.get_all()
            restored_ids = [op.operation_id for op in restored_ops]
            assert restored_ids == operation_ids, \
                "Restored operations should match original operations"
    
    asyncio.run(run_test())
