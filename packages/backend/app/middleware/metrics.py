"""
Prometheus Metrics Middleware

Automatically tracks HTTP request metrics for all endpoints.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from app.utils.metrics import get_metrics, track_request


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        """Track request latency and count"""
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Track metrics
        metrics = get_metrics()
        method = request.method
        endpoint = request.url.path
        status = response.status_code
        
        # Track request count
        track_request(method, endpoint, status)
        
        # Track request duration
        metrics['http_request_duration_seconds'].labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response
