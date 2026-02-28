"""
OpenTelemetry distributed tracing configuration and utilities.

This module provides centralized tracing setup for the Kavalan backend,
enabling end-to-end request flow tracking across all services.

Requirements: 9.8
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode
import logging
import os
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def initialize_tracing(
    service_name: str = "kavalan-backend",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False
) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing with OTLP exporter.
    
    Args:
        service_name: Name of the service for trace identification
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console_export: If True, also export traces to console for debugging
    
    Returns:
        Configured tracer instance
    """
    global _tracer
    
    # Create resource with service information
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP trace exporter configured: {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")
    
    # Add console exporter for debugging
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console trace exporter enabled")
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer instance
    _tracer = trace.get_tracer(__name__)
    
    logger.info(f"OpenTelemetry tracing initialized for {service_name}")
    
    return _tracer


def instrument_fastapi(app):
    """
    Instrument FastAPI application with automatic tracing.
    
    This adds automatic span creation for all HTTP requests.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def instrument_celery():
    """
    Instrument Celery with automatic tracing.
    
    This adds automatic span creation for all Celery tasks.
    """
    try:
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument Celery: {e}")


def instrument_redis():
    """
    Instrument Redis client with automatic tracing.
    
    This adds automatic span creation for all Redis operations.
    """
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}")


def instrument_requests():
    """
    Instrument requests library with automatic tracing.
    
    This adds automatic span creation for all HTTP requests made via requests library.
    """
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests library instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument requests: {e}")


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.
    
    Returns:
        Tracer instance
    
    Raises:
        RuntimeError: If tracing not initialized
    """
    global _tracer
    if _tracer is None:
        # Auto-initialize with defaults if not already done
        _tracer = initialize_tracing()
    return _tracer


def trace_function(span_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to add tracing to a function.
    
    Args:
        span_name: Name for the span (defaults to function name)
        attributes: Additional attributes to add to the span
    
    Example:
        @trace_function(span_name="process_audio", attributes={"modality": "audio"})
        def process_audio_chunk(data):
            # Function implementation
            pass
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function arguments as attributes (if simple types)
                for i, arg in enumerate(args[:3]):  # Limit to first 3 args
                    if isinstance(arg, (str, int, float, bool)):
                        span.set_attribute(f"arg.{i}", arg)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function arguments as attributes (if simple types)
                for i, arg in enumerate(args[:3]):  # Limit to first 3 args
                    if isinstance(arg, (str, int, float, bool)):
                        span.set_attribute(f"arg.{i}", arg)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def add_span_attributes(attributes: Dict[str, Any]):
    """
    Add attributes to the current active span.
    
    Args:
        attributes: Dictionary of attributes to add
    
    Example:
        add_span_attributes({
            "session_id": "abc123",
            "user_id": "user456",
            "threat_score": 8.5
        })
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            # Convert complex types to strings
            if isinstance(value, (list, dict)):
                value = str(value)
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current active span.
    
    Args:
        name: Event name
        attributes: Optional event attributes
    
    Example:
        add_span_event("keyword_detected", {"keyword": "arrest", "category": "authority"})
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_error(error: Exception):
    """
    Mark the current span as error and record exception.
    
    Args:
        error: Exception that occurred
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)


class TracedOperation:
    """
    Context manager for creating traced operations.
    
    Example:
        with TracedOperation("database_write", {"table": "threat_events"}):
            # Perform database operation
            db.insert(...)
    """
    
    def __init__(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.span = None
    
    def __enter__(self):
        tracer = get_tracer()
        self.span = tracer.start_span(self.operation_name)
        self.span.__enter__()
        
        # Add attributes
        for key, value in self.attributes.items():
            if isinstance(value, (list, dict)):
                value = str(value)
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        
        self.span.__exit__(exc_type, exc_val, exc_tb)
