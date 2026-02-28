"""
Unit tests for OpenTelemetry distributed tracing.

Tests verify that tracing is properly initialized and instrumented
across all service components.

Requirements: 9.8
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from app.utils.tracing import (
    initialize_tracing,
    get_tracer,
    trace_function,
    add_span_attributes,
    add_span_event,
    set_span_error,
    TracedOperation
)


class TestTracingInitialization:
    """Test tracing initialization"""
    
    def test_initialize_tracing_creates_tracer(self):
        """Test that initialize_tracing creates a valid tracer"""
        tracer = initialize_tracing(
            service_name="test-service",
            service_version="1.0.0"
        )
        
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)
    
    def test_initialize_tracing_with_otlp_endpoint(self):
        """Test tracing initialization with OTLP endpoint"""
        with patch('app.utils.tracing.OTLPSpanExporter') as mock_exporter:
            tracer = initialize_tracing(
                service_name="test-service",
                service_version="1.0.0",
                otlp_endpoint="http://localhost:4317"
            )
            
            assert tracer is not None
            mock_exporter.assert_called_once()
    
    def test_initialize_tracing_with_console_export(self):
        """Test tracing initialization with console export enabled"""
        with patch('app.utils.tracing.ConsoleSpanExporter') as mock_console:
            tracer = initialize_tracing(
                service_name="test-service",
                service_version="1.0.0",
                enable_console_export=True
            )
            
            assert tracer is not None
            mock_console.assert_called_once()
    
    def test_get_tracer_returns_initialized_tracer(self):
        """Test that get_tracer returns the initialized tracer"""
        # Initialize first
        initialize_tracing(service_name="test-service")
        
        # Get tracer
        tracer = get_tracer()
        
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)
    
    def test_get_tracer_auto_initializes_if_needed(self):
        """Test that get_tracer auto-initializes if not already done"""
        # Reset global tracer
        import app.utils.tracing as tracing_module
        tracing_module._tracer = None
        
        # Get tracer should auto-initialize
        tracer = get_tracer()
        
        assert tracer is not None


class TestTraceFunctionDecorator:
    """Test trace_function decorator"""
    
    def test_trace_function_decorator_on_sync_function(self):
        """Test that trace_function decorator works on synchronous functions"""
        @trace_function(span_name="test_operation")
        def test_func(x, y):
            return x + y
        
        result = test_func(2, 3)
        
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_trace_function_decorator_on_async_function(self):
        """Test that trace_function decorator works on async functions"""
        @trace_function(span_name="async_test_operation")
        async def async_test_func(x, y):
            return x * y
        
        result = await async_test_func(3, 4)
        
        assert result == 12
    
    def test_trace_function_with_custom_attributes(self):
        """Test trace_function with custom attributes"""
        @trace_function(
            span_name="custom_operation",
            attributes={"operation_type": "test", "priority": "high"}
        )
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
    
    def test_trace_function_handles_exceptions(self):
        """Test that trace_function properly handles exceptions"""
        @trace_function(span_name="failing_operation")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_func()


class TestSpanOperations:
    """Test span attribute and event operations"""
    
    def test_add_span_attributes(self):
        """Test adding attributes to current span"""
        # Initialize tracing
        initialize_tracing(service_name="test-service")
        
        # Create a span context
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span") as span:
            # Add attributes
            add_span_attributes({
                "user_id": "user123",
                "session_id": "session456",
                "score": 8.5
            })
            
            # Verify span is recording
            assert span.is_recording()
    
    def test_add_span_attributes_with_complex_types(self):
        """Test that complex types are converted to strings"""
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span"):
            # Should not raise error with list/dict
            add_span_attributes({
                "keywords": ["arrest", "police"],
                "metadata": {"key": "value"}
            })
    
    def test_add_span_event(self):
        """Test adding events to current span"""
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span") as span:
            # Add event
            add_span_event("keyword_detected", {
                "keyword": "arrest",
                "category": "authority"
            })
            
            assert span.is_recording()
    
    def test_set_span_error(self):
        """Test marking span as error"""
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span") as span:
            error = ValueError("Test error")
            set_span_error(error)
            
            assert span.is_recording()


class TestTracedOperation:
    """Test TracedOperation context manager"""
    
    def test_traced_operation_context_manager(self):
        """Test TracedOperation creates and manages span"""
        initialize_tracing(service_name="test-service")
        
        with TracedOperation("database_write", {"table": "threat_events"}):
            # Perform operation
            result = "operation_complete"
        
        assert result == "operation_complete"
    
    def test_traced_operation_handles_exceptions(self):
        """Test TracedOperation properly handles exceptions"""
        initialize_tracing(service_name="test-service")
        
        with pytest.raises(ValueError, match="Test error"):
            with TracedOperation("failing_operation"):
                raise ValueError("Test error")
    
    def test_traced_operation_with_attributes(self):
        """Test TracedOperation with custom attributes"""
        initialize_tracing(service_name="test-service")
        
        with TracedOperation("custom_operation", {
            "operation_type": "test",
            "priority": "high",
            "user_id": "user123"
        }) as span:
            assert span is not None


class TestInstrumentation:
    """Test automatic instrumentation of libraries"""
    
    @patch('app.utils.tracing.FastAPIInstrumentor')
    def test_instrument_fastapi(self, mock_instrumentor):
        """Test FastAPI instrumentation"""
        from app.utils.tracing import instrument_fastapi
        
        mock_app = Mock()
        instrument_fastapi(mock_app)
        
        mock_instrumentor.instrument_app.assert_called_once_with(mock_app)
    
    @patch('app.utils.tracing.CeleryInstrumentor')
    def test_instrument_celery(self, mock_instrumentor):
        """Test Celery instrumentation"""
        from app.utils.tracing import instrument_celery
        
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance
        
        instrument_celery()
        
        mock_instance.instrument.assert_called_once()
    
    @patch('app.utils.tracing.RedisInstrumentor')
    def test_instrument_redis(self, mock_instrumentor):
        """Test Redis instrumentation"""
        from app.utils.tracing import instrument_redis
        
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance
        
        instrument_redis()
        
        mock_instance.instrument.assert_called_once()
    
    @patch('app.utils.tracing.RequestsInstrumentor')
    def test_instrument_requests(self, mock_instrumentor):
        """Test requests library instrumentation"""
        from app.utils.tracing import instrument_requests
        
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance
        
        instrument_requests()
        
        mock_instance.instrument.assert_called_once()


class TestEndToEndTracing:
    """Test end-to-end tracing scenarios"""
    
    def test_nested_spans(self):
        """Test creating nested spans"""
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        
        with tracer.start_as_current_span("parent_operation") as parent:
            add_span_attributes({"operation": "parent"})
            
            with tracer.start_as_current_span("child_operation") as child:
                add_span_attributes({"operation": "child"})
                
                assert parent.is_recording()
                assert child.is_recording()
    
    def test_multiple_operations_in_sequence(self):
        """Test multiple traced operations in sequence"""
        initialize_tracing(service_name="test-service")
        
        with TracedOperation("operation_1", {"step": 1}):
            result1 = "step1_complete"
        
        with TracedOperation("operation_2", {"step": 2}):
            result2 = "step2_complete"
        
        with TracedOperation("operation_3", {"step": 3}):
            result3 = "step3_complete"
        
        assert result1 == "step1_complete"
        assert result2 == "step2_complete"
        assert result3 == "step3_complete"
    
    def test_traced_function_with_nested_operations(self):
        """Test traced function containing nested operations"""
        initialize_tracing(service_name="test-service")
        
        @trace_function(span_name="main_function")
        def main_function():
            with TracedOperation("sub_operation_1"):
                step1 = "complete"
            
            with TracedOperation("sub_operation_2"):
                step2 = "complete"
            
            return f"{step1}_{step2}"
        
        result = main_function()
        
        assert result == "complete_complete"
