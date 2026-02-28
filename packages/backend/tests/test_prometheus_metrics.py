"""
Unit tests for Prometheus metrics exporters

Tests the metrics collection and export functionality.
"""
import pytest
from app.utils.metrics import (
    initialize_metrics,
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
    track_cache_operation,
    get_metrics_output,
    track_latency
)
from prometheus_client import REGISTRY
import time


class TestMetricsInitialization:
    """Test metrics initialization"""
    
    def test_initialize_metrics_creates_all_metrics(self):
        """Test that initialize_metrics creates all expected metrics"""
        metrics = initialize_metrics()
        
        # Verify key metrics exist
        assert 'system_info' in metrics
        assert 'http_requests_total' in metrics
        assert 'http_request_duration_seconds' in metrics
        assert 'errors_total' in metrics
        assert 'audio_transcription_duration_seconds' in metrics
        assert 'visual_analysis_duration_seconds' in metrics
        assert 'liveness_detection_duration_seconds' in metrics
        assert 'threat_fusion_duration_seconds' in metrics
        assert 'end_to_end_latency_seconds' in metrics
        assert 'celery_queue_depth' in metrics
        assert 'celery_tasks_total' in metrics
        assert 'celery_task_duration_seconds' in metrics
        assert 'celery_workers_active' in metrics
        assert 'celery_worker_utilization' in metrics
        assert 'threats_detected_total' in metrics
        assert 'threat_score' in metrics
        assert 'database_operations_total' in metrics
        assert 'database_operation_duration_seconds' in metrics
        assert 'external_api_calls_total' in metrics
        assert 'external_api_duration_seconds' in metrics
        assert 'circuit_breaker_state' in metrics
        assert 'circuit_breaker_failures_total' in metrics
        assert 'websocket_connections_active' in metrics
        assert 'websocket_messages_total' in metrics
        assert 'cache_operations_total' in metrics
    
    def test_get_metrics_returns_initialized_metrics(self):
        """Test that get_metrics returns the initialized metrics"""
        metrics = get_metrics()
        assert metrics is not None
        assert len(metrics) > 0


class TestHTTPMetrics:
    """Test HTTP request metrics tracking"""
    
    def test_track_request_increments_counter(self):
        """Test that track_request increments the request counter"""
        metrics = get_metrics()
        
        # Get initial value
        initial_value = metrics['http_requests_total'].labels(
            method='GET',
            endpoint='/test',
            status='200'
        )._value.get()
        
        # Track a request
        track_request('GET', '/test', 200)
        
        # Verify counter incremented
        new_value = metrics['http_requests_total'].labels(
            method='GET',
            endpoint='/test',
            status='200'
        )._value.get()
        
        assert new_value == initial_value + 1
    
    def test_track_request_with_different_status_codes(self):
        """Test tracking requests with different status codes"""
        track_request('POST', '/api/analyze', 200)
        track_request('POST', '/api/analyze', 400)
        track_request('POST', '/api/analyze', 500)
        
        metrics = get_metrics()
        
        # Verify each status code is tracked separately
        success_count = metrics['http_requests_total'].labels(
            method='POST',
            endpoint='/api/analyze',
            status='200'
        )._value.get()
        
        error_count = metrics['http_requests_total'].labels(
            method='POST',
            endpoint='/api/analyze',
            status='500'
        )._value.get()
        
        assert success_count >= 1
        assert error_count >= 1


class TestErrorMetrics:
    """Test error tracking metrics"""
    
    def test_track_error_increments_counter(self):
        """Test that track_error increments the error counter"""
        metrics = get_metrics()
        
        initial_value = metrics['errors_total'].labels(
            error_type='NetworkError',
            component='audio_transcriber'
        )._value.get()
        
        track_error('NetworkError', 'audio_transcriber')
        
        new_value = metrics['errors_total'].labels(
            error_type='NetworkError',
            component='audio_transcriber'
        )._value.get()
        
        assert new_value == initial_value + 1


class TestThreatMetrics:
    """Test threat detection metrics"""
    
    def test_track_threat_increments_counter_and_histogram(self):
        """Test that track_threat updates both counter and histogram"""
        metrics = get_metrics()
        
        initial_count = metrics['threats_detected_total'].labels(
            threat_level='high'
        )._value.get()
        
        track_threat('high', 8.5)
        
        new_count = metrics['threats_detected_total'].labels(
            threat_level='high'
        )._value.get()
        
        assert new_count == initial_count + 1
        
        # Verify histogram was updated (check sample count)
        histogram_count = metrics['threat_score']._sum.get()
        assert histogram_count > 0


class TestQueueMetrics:
    """Test Celery queue metrics"""
    
    def test_update_queue_depth_sets_gauge(self):
        """Test that update_queue_depth sets the gauge value"""
        update_queue_depth('audio_queue', 42)
        
        metrics = get_metrics()
        value = metrics['celery_queue_depth'].labels(
            queue_name='audio_queue'
        )._value.get()
        
        assert value == 42
    
    def test_track_celery_task_increments_counter(self):
        """Test that track_celery_task increments the task counter"""
        metrics = get_metrics()
        
        initial_value = metrics['celery_tasks_total'].labels(
            task_name='analyze_audio',
            status='success'
        )._value.get()
        
        track_celery_task('analyze_audio', 'success', 1.5)
        
        new_value = metrics['celery_tasks_total'].labels(
            task_name='analyze_audio',
            status='success'
        )._value.get()
        
        assert new_value == initial_value + 1


class TestWorkerMetrics:
    """Test worker metrics"""
    
    def test_update_worker_count_sets_gauge(self):
        """Test that update_worker_count sets the gauge value"""
        update_worker_count(5)
        
        metrics = get_metrics()
        value = metrics['celery_workers_active']._value.get()
        
        assert value == 5
    
    def test_update_worker_utilization_sets_gauge(self):
        """Test that update_worker_utilization sets the gauge value"""
        update_worker_utilization('worker-1', 75.5)
        
        metrics = get_metrics()
        value = metrics['celery_worker_utilization'].labels(
            worker_name='worker-1'
        )._value.get()
        
        assert value == 75.5


class TestDatabaseMetrics:
    """Test database operation metrics"""
    
    def test_track_database_operation_updates_metrics(self):
        """Test that track_database_operation updates counter and histogram"""
        metrics = get_metrics()
        
        initial_count = metrics['database_operations_total'].labels(
            database='postgresql',
            operation='insert',
            status='success'
        )._value.get()
        
        track_database_operation('postgresql', 'insert', 'success', 0.05)
        
        new_count = metrics['database_operations_total'].labels(
            database='postgresql',
            operation='insert',
            status='success'
        )._value.get()
        
        assert new_count == initial_count + 1


class TestExternalAPIMetrics:
    """Test external API metrics"""
    
    def test_track_external_api_updates_metrics(self):
        """Test that track_external_api updates counter and histogram"""
        metrics = get_metrics()
        
        initial_count = metrics['external_api_calls_total'].labels(
            api_name='gemini',
            status='success'
        )._value.get()
        
        track_external_api('gemini', 'success', 2.5)
        
        new_count = metrics['external_api_calls_total'].labels(
            api_name='gemini',
            status='success'
        )._value.get()
        
        assert new_count == initial_count + 1


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics"""
    
    def test_update_circuit_breaker_state_sets_gauge(self):
        """Test that update_circuit_breaker_state sets the gauge value"""
        update_circuit_breaker_state('whisper', 1)  # 1 = open
        
        metrics = get_metrics()
        value = metrics['circuit_breaker_state'].labels(
            service='whisper'
        )._value.get()
        
        assert value == 1
    
    def test_track_circuit_breaker_failure_increments_counter(self):
        """Test that track_circuit_breaker_failure increments the counter"""
        metrics = get_metrics()
        
        initial_value = metrics['circuit_breaker_failures_total'].labels(
            service='gemini'
        )._value.get()
        
        track_circuit_breaker_failure('gemini')
        
        new_value = metrics['circuit_breaker_failures_total'].labels(
            service='gemini'
        )._value.get()
        
        assert new_value == initial_value + 1


class TestWebSocketMetrics:
    """Test WebSocket metrics"""
    
    def test_update_websocket_connections_sets_gauge(self):
        """Test that update_websocket_connections sets the gauge value"""
        update_websocket_connections(10)
        
        metrics = get_metrics()
        value = metrics['websocket_connections_active']._value.get()
        
        assert value == 10
    
    def test_track_websocket_message_increments_counter(self):
        """Test that track_websocket_message increments the counter"""
        metrics = get_metrics()
        
        initial_value = metrics['websocket_messages_total'].labels(
            direction='sent'
        )._value.get()
        
        track_websocket_message('sent')
        
        new_value = metrics['websocket_messages_total'].labels(
            direction='sent'
        )._value.get()
        
        assert new_value == initial_value + 1


class TestCacheMetrics:
    """Test cache operation metrics"""
    
    def test_track_cache_operation_increments_counter(self):
        """Test that track_cache_operation increments the counter"""
        metrics = get_metrics()
        
        initial_value = metrics['cache_operations_total'].labels(
            operation='get',
            result='hit'
        )._value.get()
        
        track_cache_operation('get', 'hit')
        
        new_value = metrics['cache_operations_total'].labels(
            operation='get',
            result='hit'
        )._value.get()
        
        assert new_value == initial_value + 1


class TestLatencyTracking:
    """Test latency tracking context manager"""
    
    def test_track_latency_measures_duration(self):
        """Test that track_latency measures operation duration"""
        metrics = get_metrics()
        
        # Track latency
        with track_latency('audio_transcription_duration_seconds'):
            time.sleep(0.1)  # Simulate work
        
        # Verify histogram was updated by checking the sum
        # (we can't easily check count without accessing internal state)
        total_duration = metrics['audio_transcription_duration_seconds']._sum.get()
        assert total_duration >= 0.1


class TestMetricsOutput:
    """Test metrics output generation"""
    
    def test_get_metrics_output_returns_prometheus_format(self):
        """Test that get_metrics_output returns Prometheus text format"""
        output = get_metrics_output()
        
        # Verify it's bytes
        assert isinstance(output, bytes)
        
        # Verify it contains Prometheus metrics
        output_str = output.decode('utf-8')
        assert 'kavalan_' in output_str
        assert 'TYPE' in output_str
        assert 'HELP' in output_str
    
    def test_metrics_output_includes_custom_metrics(self):
        """Test that metrics output includes our custom metrics"""
        # Track some metrics
        track_request('GET', '/test', 200)
        track_error('TestError', 'test_component')
        
        output = get_metrics_output().decode('utf-8')
        
        # Verify our metrics are in the output
        assert 'kavalan_http_requests_total' in output
        assert 'kavalan_errors_total' in output
