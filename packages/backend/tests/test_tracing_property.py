"""
Property-based tests for OpenTelemetry distributed tracing.

These tests verify universal properties that should hold for all tracing operations.

Requirements: 9.8
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.utils.tracing import (
    initialize_tracing,
    get_tracer,
    trace_function,
    add_span_attributes,
    TracedOperation
)


# Strategy for generating valid attribute values
attribute_values = st.one_of(
    st.text(min_size=1, max_size=100),
    st.integers(min_value=-1000000, max_value=1000000),
    st.floats(min_value=-1000000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
    st.booleans()
)

# Strategy for generating attribute dictionaries
attribute_dicts = st.dictionaries(
    keys=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)),
    values=attribute_values,
    min_size=1,
    max_size=10
)


class TestTracingProperties:
    """Property-based tests for tracing operations"""
    
    @given(
        service_name=st.text(min_size=1, max_size=100),
        service_version=st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    def test_initialize_tracing_always_returns_tracer(self, service_name, service_version):
        """
        Property: For any valid service name and version, initialize_tracing
        should return a valid tracer instance.
        
        Validates: Requirement 9.8 - Distributed tracing initialization
        """
        tracer = initialize_tracing(
            service_name=service_name,
            service_version=service_version
        )
        
        assert tracer is not None
        # Tracer should have required methods
        assert hasattr(tracer, 'start_span')
        assert hasattr(tracer, 'start_as_current_span')
    
    @given(attributes=attribute_dicts)
    @settings(max_examples=100)
    def test_add_span_attributes_never_raises(self, attributes):
        """
        Property: For any dictionary of valid attributes, add_span_attributes
        should never raise an exception.
        
        Validates: Requirement 9.8 - Span attribute handling
        """
        # Initialize tracing
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span"):
            # Should not raise any exception
            add_span_attributes(attributes)
    
    @given(
        operation_name=st.text(min_size=1, max_size=100),
        attributes=attribute_dicts
    )
    @settings(max_examples=100)
    def test_traced_operation_completes_successfully(self, operation_name, attributes):
        """
        Property: For any operation name and attributes, TracedOperation
        should complete successfully without errors.
        
        Validates: Requirement 9.8 - Traced operation context management
        """
        initialize_tracing(service_name="test-service")
        
        # Should complete without raising
        with TracedOperation(operation_name, attributes):
            result = "operation_complete"
        
        assert result == "operation_complete"
    
    @given(
        x=st.integers(min_value=-1000, max_value=1000),
        y=st.integers(min_value=-1000, max_value=1000)
    )
    @settings(max_examples=100)
    def test_traced_function_preserves_return_value(self, x, y):
        """
        Property: For any function arguments, a traced function should
        return the same value as the untraced version.
        
        Validates: Requirement 9.8 - Tracing transparency
        """
        initialize_tracing(service_name="test-service")
        
        @trace_function(span_name="add_operation")
        def traced_add(a, b):
            return a + b
        
        def untraced_add(a, b):
            return a + b
        
        traced_result = traced_add(x, y)
        untraced_result = untraced_add(x, y)
        
        assert traced_result == untraced_result
    
    @given(
        operations=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50),
                attribute_dicts
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_multiple_operations_complete_in_order(self, operations):
        """
        Property: For any sequence of operations, all operations should
        complete successfully in order.
        
        Validates: Requirement 9.8 - Sequential operation tracing
        """
        initialize_tracing(service_name="test-service")
        
        completed = []
        
        for op_name, op_attrs in operations:
            with TracedOperation(op_name, op_attrs):
                completed.append(op_name)
        
        # All operations should have completed
        assert len(completed) == len(operations)
        
        # Operations should complete in order
        for i, (op_name, _) in enumerate(operations):
            assert completed[i] == op_name
    
    @given(
        depth=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_nested_spans_complete_successfully(self, depth):
        """
        Property: For any nesting depth, nested spans should complete
        successfully without errors.
        
        Validates: Requirement 9.8 - Nested span handling
        """
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        
        def create_nested_spans(current_depth):
            if current_depth == 0:
                return "complete"
            
            with tracer.start_as_current_span(f"span_depth_{current_depth}"):
                return create_nested_spans(current_depth - 1)
        
        result = create_nested_spans(depth)
        
        assert result == "complete"
    
    @given(
        event_name=st.text(min_size=1, max_size=100),
        event_attrs=attribute_dicts
    )
    @settings(max_examples=100)
    def test_span_events_never_raise(self, event_name, event_attrs):
        """
        Property: For any event name and attributes, adding span events
        should never raise exceptions.
        
        Validates: Requirement 9.8 - Span event handling
        """
        from app.utils.tracing import add_span_event
        
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        with tracer.start_as_current_span("test_span"):
            # Should not raise
            add_span_event(event_name, event_attrs)
    
    @given(
        error_message=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_characters='?+*[](){}^$|\\'))
    )
    @settings(max_examples=100)
    def test_traced_operation_handles_all_exceptions(self, error_message):
        """
        Property: For any exception message, TracedOperation should
        properly handle and re-raise the exception.
        
        Validates: Requirement 9.8 - Exception handling in tracing
        """
        initialize_tracing(service_name="test-service")
        
        with pytest.raises(ValueError):
            with TracedOperation("failing_operation"):
                raise ValueError(error_message)
    
    @given(
        span_name=st.text(min_size=1, max_size=100),
        num_attributes=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=50)
    def test_span_accepts_any_number_of_attributes(self, span_name, num_attributes):
        """
        Property: For any number of attributes (0 to 20), spans should
        accept and store them without errors.
        
        Validates: Requirement 9.8 - Attribute capacity
        """
        initialize_tracing(service_name="test-service")
        
        tracer = get_tracer()
        
        # Generate attributes
        attributes = {f"attr_{i}": i for i in range(num_attributes)}
        
        with tracer.start_as_current_span(span_name):
            add_span_attributes(attributes)
    
    @given(
        operations=st.lists(
            st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_concurrent_operations_all_complete(self, operations):
        """
        Property: For any list of operations, all should complete
        successfully even when executed sequentially.
        
        Validates: Requirement 9.8 - Multiple operation handling
        """
        initialize_tracing(service_name="test-service")
        
        completed_count = 0
        
        for op_name in operations:
            with TracedOperation(op_name):
                completed_count += 1
        
        assert completed_count == len(operations)


class TestTracingInvariantsProperty:
    """Property tests for tracing invariants"""
    
    @given(
        func_name=st.text(min_size=1, max_size=100),
        args=st.lists(st.integers(), min_size=0, max_size=5)
    )
    @settings(max_examples=50)
    def test_traced_function_call_count_invariant(self, func_name, args):
        """
        Property: A traced function should be called exactly once per invocation,
        regardless of tracing overhead.
        
        Validates: Requirement 9.8 - Tracing overhead invariant
        """
        initialize_tracing(service_name="test-service")
        
        call_count = 0
        
        @trace_function(span_name=func_name)
        def counted_function(*args):
            nonlocal call_count
            call_count += 1
            return sum(args) if args else 0
        
        result = counted_function(*args)
        
        # Function should be called exactly once
        assert call_count == 1
        
        # Result should be correct
        expected = sum(args) if args else 0
        assert result == expected
    
    @given(
        operations=st.lists(
            st.text(min_size=1, max_size=50),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_operation_ordering_preserved(self, operations):
        """
        Property: The order of traced operations should be preserved
        in the execution sequence.
        
        Validates: Requirement 9.8 - Operation ordering
        """
        initialize_tracing(service_name="test-service")
        
        execution_order = []
        
        for i, op_name in enumerate(operations):
            with TracedOperation(op_name):
                execution_order.append(i)
        
        # Execution order should match input order
        assert execution_order == list(range(len(operations)))
