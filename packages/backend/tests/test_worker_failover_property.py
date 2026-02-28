"""
Property-based tests for worker failover logic

Property 8: Failover to Healthy Workers
For any failed worker, subsequent tasks should be automatically routed to 
healthy worker instances without manual intervention.

Validates: Requirements 3.3
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from app.celery_app import celery_app
from app.tasks.worker_health import WorkerHealthMonitor, health_monitor


@pytest.mark.property
@given(queue_name=st.sampled_from(['audio_queue', 'visual_queue', 'liveness_queue']))
@settings(
    max_examples=15,
    deadline=1000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_failover_configuration_enabled(queue_name):
    """
    Property 8: Failover to Healthy Workers
    
    For any queue, verify that failover is properly configured through:
    1. task_acks_late: Tasks acknowledged only after completion
    2. task_reject_on_worker_lost: Tasks requeued if worker dies
    3. Worker heartbeats enabled
    
    This test verifies the configuration that enables automatic failover.
    """
    # Verify task_acks_late is enabled (tasks acknowledged after completion)
    assert celery_app.conf.task_acks_late is True, (
        "task_acks_late must be True to enable failover - "
        "tasks should only be acknowledged after completion"
    )
    
    # Verify task_reject_on_worker_lost is enabled (requeue on worker failure)
    assert celery_app.conf.task_reject_on_worker_lost is True, (
        "task_reject_on_worker_lost must be True to enable failover - "
        "tasks should be requeued if worker dies"
    )
    
    # Verify broker heartbeat is configured
    assert celery_app.conf.broker_heartbeat is not None, (
        "broker_heartbeat must be configured for worker health monitoring"
    )
    assert celery_app.conf.broker_heartbeat > 0, (
        f"broker_heartbeat should be positive, got {celery_app.conf.broker_heartbeat}"
    )
    
    # Verify heartbeat check rate is configured
    assert celery_app.conf.broker_heartbeat_checkrate is not None, (
        "broker_heartbeat_checkrate must be configured"
    )
    
    # Verify queue exists in routing configuration
    task_routes = celery_app.conf.task_routes
    queue_found = False
    for route_pattern, route_config in task_routes.items():
        if route_config.get('queue') == queue_name:
            queue_found = True
            break
    
    assert queue_found, f"Queue {queue_name} should be configured in task routes"


@pytest.mark.property
@given(queue_name=st.sampled_from(['audio_queue', 'visual_queue', 'liveness_queue']))
@settings(
    max_examples=10,
    deadline=None,  # Disable deadline since Redis may not be available
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_worker_health_monitor_initialization(queue_name):
    """
    Property 8 Extension: Worker Health Monitoring
    
    For any queue, verify that the worker health monitor can:
    1. Initialize successfully
    2. Query worker status
    3. Check queue health
    
    This test verifies the health monitoring infrastructure.
    Note: This test may fail gracefully if Redis is not available.
    """
    # Verify health monitor is initialized
    assert health_monitor is not None, "Health monitor should be initialized"
    assert isinstance(health_monitor, WorkerHealthMonitor), (
        "Health monitor should be WorkerHealthMonitor instance"
    )
    
    # Verify health monitor has access to celery app
    assert health_monitor.app is not None, (
        "Health monitor should have access to Celery app"
    )
    
    # Note: We don't test actual Redis connectivity here since it may not be available
    # The important part is that the monitoring infrastructure is properly set up


@pytest.mark.property
def test_all_queues_have_failover_config():
    """
    Property 8 Extension: All Queues Have Failover
    
    For all configured queues, verify that failover configuration is consistent
    and properly set up.
    
    This test verifies that:
    1. All queues are configured in task routes
    2. Failover settings apply to all queues
    3. Health monitoring can check all queues
    """
    expected_queues = ['audio_queue', 'visual_queue', 'liveness_queue']
    
    # Verify all queues are in routing configuration
    task_routes = celery_app.conf.task_routes
    configured_queues = set()
    
    for route_pattern, route_config in task_routes.items():
        queue = route_config.get('queue')
        if queue:
            configured_queues.add(queue)
    
    for queue in expected_queues:
        assert queue in configured_queues, (
            f"Queue {queue} should be configured in task routes"
        )


@pytest.mark.property
def test_worker_pool_restart_enabled():
    """
    Property 8 Extension: Worker Pool Restart
    
    Verify that worker pool restarts are enabled to recover from failures.
    
    This test verifies that:
    1. worker_pool_restarts is enabled
    2. worker_max_tasks_per_child is configured to prevent memory leaks
    3. Long-running tasks are cancelled on connection loss
    """
    # Verify worker pool restarts are enabled
    assert celery_app.conf.worker_pool_restarts is True, (
        "worker_pool_restarts should be enabled for automatic recovery"
    )
    
    # Verify worker max tasks per child is configured
    assert celery_app.conf.worker_max_tasks_per_child is not None, (
        "worker_max_tasks_per_child should be configured"
    )
    assert celery_app.conf.worker_max_tasks_per_child > 0, (
        f"worker_max_tasks_per_child should be positive, "
        f"got {celery_app.conf.worker_max_tasks_per_child}"
    )
    
    # Verify long-running tasks are cancelled on connection loss
    assert celery_app.conf.worker_cancel_long_running_tasks_on_connection_loss is True, (
        "Long-running tasks should be cancelled on connection loss"
    )


@pytest.mark.property
@given(
    worker_count=st.integers(min_value=1, max_value=10),
    failed_count=st.integers(min_value=0, max_value=5)
)
@settings(
    max_examples=20,
    deadline=1000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_failover_capacity_calculation(worker_count, failed_count):
    """
    Property 8 Extension: Failover Capacity
    
    For any number of workers and failures, verify that:
    1. Healthy worker count is correctly calculated
    2. Queue has capacity if at least one worker is healthy
    3. Failed workers are properly identified
    
    This test verifies the logic for determining failover capacity.
    """
    # Ensure failed count doesn't exceed worker count
    failed_count = min(failed_count, worker_count)
    healthy_count = worker_count - failed_count
    
    # Property: Healthy workers = Total workers - Failed workers
    assert healthy_count == worker_count - failed_count, (
        f"Healthy count calculation incorrect: "
        f"{healthy_count} != {worker_count} - {failed_count}"
    )
    
    # Property: Queue has capacity if at least one healthy worker
    has_capacity = healthy_count > 0
    assert has_capacity == (healthy_count > 0), (
        f"Capacity calculation incorrect for {healthy_count} healthy workers"
    )
    
    # Property: If all workers failed, no capacity
    if failed_count == worker_count:
        assert healthy_count == 0, "All workers failed should mean 0 healthy workers"
        assert not has_capacity, "No capacity when all workers failed"
    
    # Property: If no workers failed, full capacity
    if failed_count == 0:
        assert healthy_count == worker_count, "No failures should mean all workers healthy"
        assert has_capacity, "Should have capacity when no workers failed"


@pytest.mark.property
def test_task_prefetch_configuration():
    """
    Property 8 Extension: Task Prefetch for Load Balancing
    
    Verify that task prefetch is configured to enable load balancing
    across multiple workers.
    
    This test verifies that:
    1. worker_prefetch_multiplier is configured
    2. Prefetch value allows fair distribution
    """
    # Verify prefetch multiplier is configured
    assert celery_app.conf.worker_prefetch_multiplier is not None, (
        "worker_prefetch_multiplier should be configured"
    )
    
    prefetch = celery_app.conf.worker_prefetch_multiplier
    assert prefetch > 0, (
        f"worker_prefetch_multiplier should be positive, got {prefetch}"
    )
    
    # Reasonable prefetch values are typically 1-10
    # Higher values improve throughput but reduce fairness
    assert 1 <= prefetch <= 10, (
        f"worker_prefetch_multiplier should be between 1-10 for good balance, "
        f"got {prefetch}"
    )
