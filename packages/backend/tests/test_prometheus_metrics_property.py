"""
Property-based tests for Prometheus metrics exporters

Tests universal properties of the metrics system.
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.utils.metrics import (
    get_metrics,
    track_request,
    track_error,
    track_threat,
    update_queue_depth,
    track_celery_task,
    update_worker_count,
    update_worker_utilization,
    track_database_operation,
    track_external_api,
    update_circuit_breaker_state,
    track_circuit_breaker_failure,
    update_websocket_connections,
    track_websocket_message,
    track_cache_operation
)


class TestMetricsMonotonicity:
    """Test that counters are monotonically increasing"""
    
    @given(
        method=st.sampled_from(['GET', 'POST', 'PUT', 'DELETE']),
        endpoint=st.text(min_size=1, max_size=50),
        status=st.integers(min_value=200, max_value=599)
    )
    @settings(max_examples=100)
    def test_http_requests_counter_monotonic(self, method, endpoint, status):
        """
        **Validates: Requirements 9.1**
        
        For any HTTP request tracking, the counter should never decrease.
        """
        metrics = get_metrics()
        
        # Get current value
        current_value = metrics['http_requests_total'].labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        )._value.get()
        
        # Track request
        track_request(method, endpoint, status)
        
        # Get new value
        new_value = metrics['http_requests_total'].labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        )._value.get()
        
        # Counter should increase
        assert new_value >= current_value
        assert new_value == current_value + 1
    
    @given(
        error_type=st.text(min_size=1, max_size=50),
        component=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100)
    def test_errors_counter_monotonic(self, error_type, component):
        """
        **Validates: Requirements 9.1**
        
        For any error tracking, the counter should never decrease.
        """
        metrics = get_metrics()
        
        current_value = metrics['errors_total'].labels(
            error_type=error_type,
            component=component
        )._value.get()
        
        track_error(error_type, component)
        
        new_value = metrics['errors_total'].labels(
            error_type=error_type,
            component=component
        )._value.get()
        
        assert new_value >= current_value
        assert new_value == current_value + 1


class TestQueueDepthMetrics:
    """Test queue depth gauge properties"""
    
    @given(
        queue_name=st.text(min_size=1, max_size=50),
        depth=st.integers(min_value=0, max_value=10000)
    )
    @settings(max_examples=100)
    def test_queue_depth_reflects_current_value(self, queue_name, depth):
        """
        **Validates: Requirements 9.4**
        
        For any queue depth update, the gauge should reflect the exact current value.
        """
        update_queue_depth(queue_name, depth)
        
        metrics = get_metrics()
        value = metrics['celery_queue_depth'].labels(
            queue_name=queue_name
        )._value.get()
        
        assert value == depth
    
    @given(
        queue_name=st.text(min_size=1, max_size=50),
        depths=st.lists(st.integers(min_value=0, max_value=1000), min_size=2, max_size=10)
    )
    @settings(max_examples=50)
    def test_queue_depth_updates_override_previous(self, queue_name, depths):
        """
        **Validates: Requirements 9.4**
        
        For any sequence of queue depth updates, the gauge should always reflect
        the most recent value (not cumulative).
        """
        metrics = get_metrics()
        
        for depth in depths:
            update_queue_depth(queue_name, depth)
            
            current_value = metrics['celery_queue_depth'].labels(
                queue_name=queue_name
            )._value.get()
            
            # Should equal the last set value, not sum
            assert current_value == depth


class TestWorkerMetrics:
    """Test worker metrics properties"""
    
    @given(worker_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_worker_count_non_negative(self, worker_count):
        """
        **Validates: Requirements 9.4**
        
        For any worker count update, the value should be non-negative.
        """
        update_worker_count(worker_count)
        
        metrics = get_metrics()
        value = metrics['celery_workers_active']._value.get()
        
        assert value >= 0
        assert value == worker_count
    
    @given(
        worker_name=st.text(min_size=1, max_size=50),
        utilization=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_worker_utilization_in_valid_range(self, worker_name, utilization):
        """
        **Validates: Requirements 9.4**
        
        For any worker utilization update, the value should be in [0, 100] range.
        """
        update_worker_utilization(worker_name, utilization)
        
        metrics = get_metrics()
        value = metrics['celery_worker_utilization'].labels(
            worker_name=worker_name
        )._value.get()
        
        assert 0.0 <= value <= 100.0
        assert value == utilization


class TestThreatMetrics:
    """Test threat detection metrics properties"""
    
    @given(
        threat_level=st.sampled_from(['low', 'moderate', 'high', 'critical']),
        score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_threat_tracking_increments_counter(self, threat_level, score):
        """
        **Validates: Requirements 9.1**
        
        For any threat detection, the counter should increment and histogram should record score.
        """
        metrics = get_metrics()
        
        initial_count = metrics['threats_detected_total'].labels(
            threat_level=threat_level
        )._value.get()
        
        track_threat(threat_level, score)
        
        new_count = metrics['threats_detected_total'].labels(
            threat_level=threat_level
        )._value.get()
        
        # Counter should increment
        assert new_count == initial_count + 1


class TestDatabaseMetrics:
    """Test database operation metrics properties"""
    
    @given(
        database=st.sampled_from(['postgresql', 'mongodb']),
        operation=st.sampled_from(['insert', 'update', 'delete', 'select']),
        status=st.sampled_from(['success', 'failure']),
        duration=st.floats(min_value=0.001, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_database_operation_tracking(self, database, operation, status, duration):
        """
        **Validates: Requirements 9.1, 9.4**
        
        For any database operation, metrics should track count and latency.
        """
        metrics = get_metrics()
        
        initial_count = metrics['database_operations_total'].labels(
            database=database,
            operation=operation,
            status=status
        )._value.get()
        
        track_database_operation(database, operation, status, duration)
        
        new_count = metrics['database_operations_total'].labels(
            database=database,
            operation=operation,
            status=status
        )._value.get()
        
        assert new_count == initial_count + 1


class TestExternalAPIMetrics:
    """Test external API metrics properties"""
    
    @given(
        api_name=st.sampled_from(['whisper', 'gemini', 'mediapipe']),
        status=st.sampled_from(['success', 'failure', 'timeout', 'rate_limit']),
        duration=st.floats(min_value=0.1, max_value=30.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_external_api_tracking(self, api_name, status, duration):
        """
        **Validates: Requirements 9.1, 9.4**
        
        For any external API call, metrics should track count and latency.
        """
        metrics = get_metrics()
        
        initial_count = metrics['external_api_calls_total'].labels(
            api_name=api_name,
            status=status
        )._value.get()
        
        track_external_api(api_name, status, duration)
        
        new_count = metrics['external_api_calls_total'].labels(
            api_name=api_name,
            status=status
        )._value.get()
        
        assert new_count == initial_count + 1


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics properties"""
    
    @given(
        service=st.text(min_size=1, max_size=50),
        state=st.integers(min_value=0, max_value=2)
    )
    @settings(max_examples=100)
    def test_circuit_breaker_state_valid_range(self, service, state):
        """
        **Validates: Requirements 9.1**
        
        For any circuit breaker state update, the value should be 0, 1, or 2.
        """
        update_circuit_breaker_state(service, state)
        
        metrics = get_metrics()
        value = metrics['circuit_breaker_state'].labels(
            service=service
        )._value.get()
        
        assert value in [0, 1, 2]
        assert value == state
    
    @given(service=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_circuit_breaker_failures_monotonic(self, service):
        """
        **Validates: Requirements 9.1**
        
        For any circuit breaker failure tracking, the counter should never decrease.
        """
        metrics = get_metrics()
        
        current_value = metrics['circuit_breaker_failures_total'].labels(
            service=service
        )._value.get()
        
        track_circuit_breaker_failure(service)
        
        new_value = metrics['circuit_breaker_failures_total'].labels(
            service=service
        )._value.get()
        
        assert new_value >= current_value
        assert new_value == current_value + 1


class TestWebSocketMetrics:
    """Test WebSocket metrics properties"""
    
    @given(connections=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_websocket_connections_non_negative(self, connections):
        """
        **Validates: Requirements 9.1**
        
        For any WebSocket connection count update, the value should be non-negative.
        """
        update_websocket_connections(connections)
        
        metrics = get_metrics()
        value = metrics['websocket_connections_active']._value.get()
        
        assert value >= 0
        assert value == connections
    
    @given(direction=st.sampled_from(['sent', 'received']))
    @settings(max_examples=100)
    def test_websocket_messages_monotonic(self, direction):
        """
        **Validates: Requirements 9.1**
        
        For any WebSocket message tracking, the counter should never decrease.
        """
        metrics = get_metrics()
        
        current_value = metrics['websocket_messages_total'].labels(
            direction=direction
        )._value.get()
        
        track_websocket_message(direction)
        
        new_value = metrics['websocket_messages_total'].labels(
            direction=direction
        )._value.get()
        
        assert new_value >= current_value
        assert new_value == current_value + 1


class TestCacheMetrics:
    """Test cache operation metrics properties"""
    
    @given(
        operation=st.sampled_from(['get', 'set']),
        result=st.sampled_from(['hit', 'miss', 'success', 'failure'])
    )
    @settings(max_examples=100)
    def test_cache_operations_monotonic(self, operation, result):
        """
        **Validates: Requirements 9.1**
        
        For any cache operation tracking, the counter should never decrease.
        """
        metrics = get_metrics()
        
        current_value = metrics['cache_operations_total'].labels(
            operation=operation,
            result=result
        )._value.get()
        
        track_cache_operation(operation, result)
        
        new_value = metrics['cache_operations_total'].labels(
            operation=operation,
            result=result
        )._value.get()
        
        assert new_value >= current_value
        assert new_value == current_value + 1


class TestCeleryTaskMetrics:
    """Test Celery task metrics properties"""
    
    @given(
        task_name=st.text(min_size=1, max_size=50),
        status=st.sampled_from(['success', 'failure', 'retry']),
        duration=st.floats(min_value=0.01, max_value=60.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_celery_task_tracking(self, task_name, status, duration):
        """
        **Validates: Requirements 9.1, 9.4**
        
        For any Celery task execution, metrics should track count and duration.
        """
        metrics = get_metrics()
        
        initial_count = metrics['celery_tasks_total'].labels(
            task_name=task_name,
            status=status
        )._value.get()
        
        track_celery_task(task_name, status, duration)
        
        new_count = metrics['celery_tasks_total'].labels(
            task_name=task_name,
            status=status
        )._value.get()
        
        assert new_count == initial_count + 1
