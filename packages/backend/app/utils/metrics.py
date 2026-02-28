"""
Prometheus Metrics Exporters

This module provides Prometheus metrics for monitoring system performance and health.
Implements Requirements 9.1 and 9.4:
- Collects metrics using Prometheus exporters from all services
- Tracks end-to-end latency for each processing pipeline stage
- Monitors queue depth and worker utilization
- Exposes /metrics endpoint for Prometheus scraping
"""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    REGISTRY,
    CollectorRegistry
)
from typing import Optional
import time
from functools import wraps
from contextlib import contextmanager

# Use a singleton pattern to avoid duplicate metric registration
_metrics_initialized = False
_metrics = {}


def initialize_metrics():
    """Initialize all Prometheus metrics (call once at startup)"""
    global _metrics_initialized, _metrics
    
    if _metrics_initialized:
        return _metrics
    
    # System info
    _metrics['system_info'] = Info(
        'kavalan_system',
        'System information'
    )
    _metrics['system_info'].info({
        'version': '1.0.0',
        'service': 'kavalan-api'
    })
    
    # Request metrics
    _metrics['http_requests_total'] = Counter(
        'kavalan_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    _metrics['http_request_duration_seconds'] = Histogram(
        'kavalan_http_request_duration_seconds',
        'HTTP request latency in seconds',
        ['method', 'endpoint'],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # Error metrics
    _metrics['errors_total'] = Counter(
        'kavalan_errors_total',
        'Total errors by type',
        ['error_type', 'component']
    )
    
    # Processing pipeline metrics
    _metrics['audio_transcription_duration_seconds'] = Histogram(
        'kavalan_audio_transcription_duration_seconds',
        'Audio transcription latency in seconds',
        buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
    )
    
    _metrics['visual_analysis_duration_seconds'] = Histogram(
        'kavalan_visual_analysis_duration_seconds',
        'Visual analysis latency in seconds',
        buckets=(0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0)
    )
    
    _metrics['liveness_detection_duration_seconds'] = Histogram(
        'kavalan_liveness_detection_duration_seconds',
        'Liveness detection latency in seconds',
        buckets=(0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0)
    )
    
    _metrics['threat_fusion_duration_seconds'] = Histogram(
        'kavalan_threat_fusion_duration_seconds',
        'Threat score fusion latency in seconds',
        buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3)
    )
    
    _metrics['end_to_end_latency_seconds'] = Histogram(
        'kavalan_end_to_end_latency_seconds',
        'Total end-to-end processing latency in seconds',
        buckets=(0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0)
    )
    
    # Task queue metrics
    _metrics['celery_queue_depth'] = Gauge(
        'kavalan_celery_queue_depth',
        'Number of tasks in Celery queue',
        ['queue_name']
    )
    
    _metrics['celery_tasks_total'] = Counter(
        'kavalan_celery_tasks_total',
        'Total Celery tasks processed',
        ['task_name', 'status']
    )
    
    _metrics['celery_task_duration_seconds'] = Histogram(
        'kavalan_celery_task_duration_seconds',
        'Celery task execution time in seconds',
        ['task_name'],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
    )
    
    # Worker metrics
    _metrics['celery_workers_active'] = Gauge(
        'kavalan_celery_workers_active',
        'Number of active Celery workers'
    )
    
    _metrics['celery_worker_utilization'] = Gauge(
        'kavalan_celery_worker_utilization',
        'Worker utilization percentage (0-100)',
        ['worker_name']
    )
    
    # Threat detection metrics
    _metrics['threats_detected_total'] = Counter(
        'kavalan_threats_detected_total',
        'Total threats detected',
        ['threat_level']
    )
    
    _metrics['threat_score'] = Histogram(
        'kavalan_threat_score',
        'Distribution of threat scores',
        buckets=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)
    )
    
    # Database metrics
    _metrics['database_operations_total'] = Counter(
        'kavalan_database_operations_total',
        'Total database operations',
        ['database', 'operation', 'status']
    )
    
    _metrics['database_operation_duration_seconds'] = Histogram(
        'kavalan_database_operation_duration_seconds',
        'Database operation latency in seconds',
        ['database', 'operation'],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
    )
    
    # External API metrics
    _metrics['external_api_calls_total'] = Counter(
        'kavalan_external_api_calls_total',
        'Total external API calls',
        ['api_name', 'status']
    )
    
    _metrics['external_api_duration_seconds'] = Histogram(
        'kavalan_external_api_duration_seconds',
        'External API call latency in seconds',
        ['api_name'],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
    )
    
    # Circuit breaker metrics
    _metrics['circuit_breaker_state'] = Gauge(
        'kavalan_circuit_breaker_state',
        'Circuit breaker state (0=closed, 1=open, 2=half-open)',
        ['service']
    )
    
    _metrics['circuit_breaker_failures_total'] = Counter(
        'kavalan_circuit_breaker_failures_total',
        'Total circuit breaker failures',
        ['service']
    )
    
    # WebSocket metrics
    _metrics['websocket_connections_active'] = Gauge(
        'kavalan_websocket_connections_active',
        'Number of active WebSocket connections'
    )
    
    _metrics['websocket_messages_total'] = Counter(
        'kavalan_websocket_messages_total',
        'Total WebSocket messages',
        ['direction']  # 'sent' or 'received'
    )
    
    # Cache metrics
    _metrics['cache_operations_total'] = Counter(
        'kavalan_cache_operations_total',
        'Total cache operations',
        ['operation', 'result']  # operation: get/set, result: hit/miss/success/failure
    )
    
    _metrics_initialized = True
    return _metrics


def get_metrics():
    """Get initialized metrics dictionary"""
    if not _metrics_initialized:
        initialize_metrics()
    return _metrics


@contextmanager
def track_latency(metric_name: str, labels: Optional[dict] = None):
    """
    Context manager to track operation latency
    
    Usage:
        with track_latency('audio_transcription_duration_seconds'):
            # perform audio transcription
            pass
    """
    metrics = get_metrics()
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if labels:
            metrics[metric_name].labels(**labels).observe(duration)
        else:
            metrics[metric_name].observe(duration)


def track_request(method: str, endpoint: str, status: int):
    """Track HTTP request metrics"""
    metrics = get_metrics()
    metrics['http_requests_total'].labels(
        method=method,
        endpoint=endpoint,
        status=str(status)
    ).inc()


def track_error(error_type: str, component: str):
    """Track error occurrence"""
    metrics = get_metrics()
    metrics['errors_total'].labels(
        error_type=error_type,
        component=component
    ).inc()


def track_threat(threat_level: str, score: float):
    """Track threat detection"""
    metrics = get_metrics()
    metrics['threats_detected_total'].labels(threat_level=threat_level).inc()
    metrics['threat_score'].observe(score)


def update_queue_depth(queue_name: str, depth: int):
    """Update Celery queue depth gauge"""
    metrics = get_metrics()
    metrics['celery_queue_depth'].labels(queue_name=queue_name).set(depth)


def track_celery_task(task_name: str, status: str, duration: Optional[float] = None):
    """Track Celery task execution"""
    metrics = get_metrics()
    metrics['celery_tasks_total'].labels(
        task_name=task_name,
        status=status
    ).inc()
    
    if duration is not None:
        metrics['celery_task_duration_seconds'].labels(
            task_name=task_name
        ).observe(duration)


def update_worker_count(count: int):
    """Update active worker count"""
    metrics = get_metrics()
    metrics['celery_workers_active'].set(count)


def update_worker_utilization(worker_name: str, utilization: float):
    """Update worker utilization percentage"""
    metrics = get_metrics()
    metrics['celery_worker_utilization'].labels(
        worker_name=worker_name
    ).set(utilization)


def track_database_operation(database: str, operation: str, status: str, duration: float):
    """Track database operation metrics"""
    metrics = get_metrics()
    metrics['database_operations_total'].labels(
        database=database,
        operation=operation,
        status=status
    ).inc()
    metrics['database_operation_duration_seconds'].labels(
        database=database,
        operation=operation
    ).observe(duration)


def track_external_api(api_name: str, status: str, duration: float):
    """Track external API call metrics"""
    metrics = get_metrics()
    metrics['external_api_calls_total'].labels(
        api_name=api_name,
        status=status
    ).inc()
    metrics['external_api_duration_seconds'].labels(
        api_name=api_name
    ).observe(duration)


def update_circuit_breaker_state(service: str, state: int):
    """
    Update circuit breaker state
    0 = closed (normal operation)
    1 = open (failing)
    2 = half-open (testing recovery)
    """
    metrics = get_metrics()
    metrics['circuit_breaker_state'].labels(service=service).set(state)


def track_circuit_breaker_failure(service: str):
    """Track circuit breaker failure"""
    metrics = get_metrics()
    metrics['circuit_breaker_failures_total'].labels(service=service).inc()


def update_websocket_connections(count: int):
    """Update active WebSocket connection count"""
    metrics = get_metrics()
    metrics['websocket_connections_active'].set(count)


def track_websocket_message(direction: str):
    """Track WebSocket message (sent or received)"""
    metrics = get_metrics()
    metrics['websocket_messages_total'].labels(direction=direction).inc()


def track_cache_operation(operation: str, result: str):
    """Track cache operation (get/set with hit/miss/success/failure)"""
    metrics = get_metrics()
    metrics['cache_operations_total'].labels(
        operation=operation,
        result=result
    ).inc()


def get_metrics_output():
    """Generate Prometheus metrics output"""
    return generate_latest(REGISTRY)
