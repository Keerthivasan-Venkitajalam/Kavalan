"""
Metrics Endpoint

Exposes Prometheus metrics at /metrics endpoint for scraping.
Implements Requirement 9.1: Collect metrics using Prometheus exporters from all services
"""
from fastapi import APIRouter, Response
from app.utils.metrics import get_metrics_output, initialize_metrics

router = APIRouter(tags=["metrics"])

# Initialize metrics on module load
initialize_metrics()


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint
    
    Returns metrics in Prometheus text format for scraping.
    This endpoint exposes:
    - HTTP request latency and counts
    - Error rates by type and component
    - Processing pipeline latencies (audio, visual, liveness, fusion)
    - Celery queue depth and worker utilization
    - Threat detection metrics
    - Database operation metrics
    - External API call metrics
    - Circuit breaker states
    - WebSocket connection metrics
    - Cache operation metrics
    """
    metrics_output = get_metrics_output()
    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
