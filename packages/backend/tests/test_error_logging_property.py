"""
Property-Based Tests for Error Logging with Context

Feature: production-ready-browser-extension
Property 40: Error Logging with Context

For any error or exception that occurs, the system should log the error with
contextual information including: timestamp, component name, error message,
stack trace, and relevant request/session IDs.

Validates: Requirements 18.5
"""

import pytest
import json
import logging
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from uuid import UUID
from app.utils.error_logger import (
    StructuredErrorLogger,
    ErrorSeverity,
    get_error_logger
)


# Custom strategies for generating test data
@st.composite
def component_names(draw):
    """Generate valid component names"""
    components = [
        "audio_transcriber",
        "visual_analyzer",
        "liveness_detector",
        "threat_analyzer",
        "database",
        "api_gateway",
        "celery_worker"
    ]
    return draw(st.sampled_from(components))


@st.composite
def error_messages(draw):
    """Generate realistic error messages"""
    messages = [
        "Connection timeout",
        "Invalid input format",
        "API rate limit exceeded",
        "Database connection lost",
        "Processing failed",
        "Authentication failed",
        "Resource not found",
        "Permission denied"
    ]
    return draw(st.sampled_from(messages))


@st.composite
def exception_types(draw):
    """Generate different exception types"""
    exceptions = [
        ValueError,
        RuntimeError,
        ConnectionError,
        TimeoutError,
        KeyError,
        TypeError
    ]
    exc_class = draw(st.sampled_from(exceptions))
    message = draw(error_messages())
    return exc_class(message)


@given(
    component=component_names(),
    message=error_messages(),
    session_id=st.uuids(),
    user_id=st.uuids(),
    request_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_error_logging_includes_all_required_context(
    caplog,
    component: str,
    message: str,
    session_id: UUID,
    user_id: UUID,
    request_id: str
):
    """
    Property: All error logs include required contextual information.
    
    For any error logged with session_id, user_id, and request_id,
    the log entry must contain:
    - timestamp (ISO 8601 format)
    - component name
    - error message
    - session_id
    - user_id
    - request_id
    """
    caplog.clear()
    caplog.set_level(logging.ERROR)
    logger = StructuredErrorLogger(component)
    
    # Log an error with all context
    logger.error(
        message,
        session_id=session_id,
        user_id=user_id,
        request_id=request_id
    )
    
    # Parse the JSON log output
    assert len(caplog.records) > 0, "No log records were created"
    log_record = json.loads(caplog.records[-1].getMessage())  # Use last record
    
    # Verify all required fields are present
    assert "timestamp" in log_record, "Missing timestamp"
    assert "component" in log_record, "Missing component"
    assert "message" in log_record, "Missing message"
    assert "session_id" in log_record, "Missing session_id"
    assert "user_id" in log_record, "Missing user_id"
    assert "request_id" in log_record, "Missing request_id"
    
    # Verify values match
    assert log_record["component"] == component
    assert log_record["message"] == message
    assert log_record["session_id"] == str(session_id)
    assert log_record["user_id"] == str(user_id)
    assert log_record["request_id"] == request_id
    
    # Verify timestamp is valid ISO 8601 format
    timestamp_str = log_record["timestamp"]
    assert timestamp_str.endswith("Z"), "Timestamp should be in UTC (end with Z)"
    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert isinstance(timestamp, datetime)


@given(
    component=component_names(),
    message=error_messages(),
    exception=exception_types()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_exception_logging_includes_stack_trace(
    caplog,
    component: str,
    message: str,
    exception: Exception
):
    """
    Property: All exception logs include stack trace information.
    
    For any exception logged, the log entry must contain:
    - error_type (exception class name)
    - error_message (exception message)
    - stack_trace (list of stack trace lines)
    """
    caplog.clear()
    caplog.set_level(logging.ERROR)
    logger = StructuredErrorLogger(component)
    
    # Create a real exception with stack trace
    try:
        raise exception
    except Exception as e:
        logger.error(message, error=e)
    
    # Parse the JSON log output
    log_record = json.loads(caplog.records[-1].getMessage())
    
    # Verify exception details are present
    assert "error_type" in log_record, "Missing error_type"
    assert "error_message" in log_record, "Missing error_message"
    assert "stack_trace" in log_record, "Missing stack_trace"
    
    # Verify error_type matches exception class
    assert log_record["error_type"] == type(exception).__name__
    
    # Verify error_message matches exception message
    assert log_record["error_message"] == str(exception)
    
    # Verify stack_trace is a list and contains relevant information
    assert isinstance(log_record["stack_trace"], list)
    assert len(log_record["stack_trace"]) > 0
    
    # Stack trace should contain the exception type and message
    stack_trace_str = "".join(log_record["stack_trace"])
    assert type(exception).__name__ in stack_trace_str
    assert str(exception) in stack_trace_str


@given(
    component=component_names(),
    message=error_messages(),
    severity=st.sampled_from([
        ErrorSeverity.DEBUG,
        ErrorSeverity.INFO,
        ErrorSeverity.WARNING,
        ErrorSeverity.ERROR,
        ErrorSeverity.CRITICAL
    ])
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_all_severity_levels_produce_valid_logs(
    caplog,
    component: str,
    message: str,
    severity: ErrorSeverity
):
    """
    Property: All severity levels produce valid JSON logs.
    
    For any severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL),
    the log output should be valid JSON with correct severity field.
    """
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    logger = StructuredErrorLogger(component)
    
    # Log at the specified severity level
    if severity == ErrorSeverity.DEBUG:
        logger.debug(message)
    elif severity == ErrorSeverity.INFO:
        logger.info(message)
    elif severity == ErrorSeverity.WARNING:
        logger.warning(message)
    elif severity == ErrorSeverity.ERROR:
        logger.error(message)
    elif severity == ErrorSeverity.CRITICAL:
        logger.critical(message)
    
    # Parse the JSON log output
    log_record = json.loads(caplog.records[0].getMessage())
    
    # Verify severity is correct
    assert log_record["severity"] == severity.value
    assert log_record["message"] == message
    assert log_record["component"] == component


@given(
    component=component_names(),
    message=error_messages(),
    context_keys=st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        min_size=1,
        max_size=10,
        unique=True
    ),
    context_values=st.lists(
        st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=50),
            st.booleans()
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_additional_context_is_preserved(
    caplog,
    component: str,
    message: str,
    context_keys: list,
    context_values: list
):
    """
    Property: Additional context fields are preserved in logs.
    
    For any additional context key-value pairs provided,
    they should be present in the log entry's context field.
    """
    assume(len(context_keys) == len(context_values))
    
    caplog.clear()
    caplog.set_level(logging.ERROR)
    logger = StructuredErrorLogger(component)
    
    # Create context dictionary
    context = dict(zip(context_keys, context_values))
    
    # Log with additional context
    logger.error(message, **context)
    
    # Parse the JSON log output
    log_record = json.loads(caplog.records[0].getMessage())
    
    # Verify context field exists
    assert "context" in log_record, "Missing context field"
    
    # Verify all context keys and values are preserved
    for key, value in context.items():
        assert key in log_record["context"], f"Missing context key: {key}"
        assert log_record["context"][key] == value, \
            f"Context value mismatch for key {key}"


@given(
    component=component_names(),
    message=error_messages()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_log_output_is_valid_json(
    caplog,
    component: str,
    message: str
):
    """
    Property: All log output is valid JSON.
    
    For any log message, the output should be parseable as JSON
    and contain the expected structure.
    """
    caplog.clear()
    caplog.set_level(logging.INFO)
    logger = StructuredErrorLogger(component)
    
    logger.info(message)
    
    # Attempt to parse as JSON (will raise exception if invalid)
    log_record = json.loads(caplog.records[0].getMessage())
    
    # Verify it's a dictionary
    assert isinstance(log_record, dict)
    
    # Verify required top-level fields exist
    required_fields = ["timestamp", "component", "severity", "message"]
    for field in required_fields:
        assert field in log_record, f"Missing required field: {field}"


@given(
    component=component_names(),
    num_logs=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_multiple_logs_maintain_independence(
    caplog,
    component: str,
    num_logs: int
):
    """
    Property: Multiple log entries maintain independence.
    
    For any number of log entries, each should be independent
    and contain its own complete context.
    """
    caplog.clear()
    caplog.set_level(logging.INFO)
    logger = StructuredErrorLogger(component)
    
    # Generate multiple log entries with different messages
    messages = [f"Message {i}" for i in range(num_logs)]
    
    for msg in messages:
        logger.info(msg, log_index=messages.index(msg))
    
    # Verify we have the correct number of log records
    assert len(caplog.records) == num_logs
    
    # Verify each log is independent and valid
    for i, record in enumerate(caplog.records):
        log_record = json.loads(record.getMessage())
        
        assert log_record["message"] == f"Message {i}"
        assert log_record["component"] == component
        assert "timestamp" in log_record
        
        # Verify context is specific to this log
        if "context" in log_record:
            assert log_record["context"]["log_index"] == i


@given(
    component=component_names(),
    message=error_messages(),
    session_id=st.one_of(st.none(), st.uuids()),
    user_id=st.one_of(st.none(), st.uuids()),
    request_id=st.one_of(st.none(), st.text(min_size=5, max_size=20))
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_optional_ids_handled_correctly(
    caplog,
    component: str,
    message: str,
    session_id,
    user_id,
    request_id
):
    """
    Property: Optional IDs are handled correctly.
    
    For any combination of present/absent IDs (session_id, user_id, request_id),
    the log should only include IDs that were provided.
    """
    caplog.clear()
    caplog.set_level(logging.ERROR)
    logger = StructuredErrorLogger(component)
    
    # Log with optional IDs
    logger.error(
        message,
        session_id=session_id,
        user_id=user_id,
        request_id=request_id
    )
    
    # Parse the JSON log output
    log_record = json.loads(caplog.records[0].getMessage())
    
    # Verify IDs are present only if provided
    if session_id is not None:
        assert "session_id" in log_record
        assert log_record["session_id"] == str(session_id)
    else:
        assert "session_id" not in log_record
    
    if user_id is not None:
        assert "user_id" in log_record
        assert log_record["user_id"] == str(user_id)
    else:
        assert "user_id" not in log_record
    
    if request_id is not None:
        assert "request_id" in log_record
        assert log_record["request_id"] == request_id
    else:
        assert "request_id" not in log_record


@given(
    component=component_names(),
    message=error_messages()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_timestamp_is_monotonically_increasing(
    caplog,
    component: str,
    message: str
):
    """
    Property: Timestamps are monotonically increasing.
    
    For any sequence of log entries, timestamps should be
    in chronological order (non-decreasing).
    """
    caplog.clear()
    caplog.set_level(logging.INFO)
    logger = StructuredErrorLogger(component)
    
    # Generate multiple log entries
    num_logs = 5
    for i in range(num_logs):
        logger.info(f"{message} {i}")
    
    # Extract timestamps
    timestamps = []
    for record in caplog.records:
        log_record = json.loads(record.getMessage())
        timestamp_str = log_record["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamps.append(timestamp)
    
    # Verify timestamps are non-decreasing
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i + 1], \
            f"Timestamps not monotonic: {timestamps[i]} > {timestamps[i + 1]}"


@given(
    component=component_names()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_log_exception_convenience_method_includes_context(
    caplog,
    component: str
):
    """
    Property: log_exception convenience method includes all context.
    
    For any exception logged via log_exception(), the log should
    contain error_type, error_message, and stack_trace.
    """
    caplog.clear()
    caplog.set_level(logging.ERROR)
    logger = StructuredErrorLogger(component)
    
    # Create and log an exception
    try:
        raise ValueError("Test exception")
    except ValueError as e:
        logger.log_exception(e, custom_field="custom_value")
    
    # Parse the JSON log output
    log_record = json.loads(caplog.records[0].getMessage())
    
    # Verify exception details
    assert "error_type" in log_record
    assert log_record["error_type"] == "ValueError"
    assert "error_message" in log_record
    assert log_record["error_message"] == "Test exception"
    assert "stack_trace" in log_record
    
    # Verify custom context is preserved
    assert "context" in log_record
    assert log_record["context"]["custom_field"] == "custom_value"


@given(
    component1=component_names(),
    component2=component_names(),
    message=error_messages()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_different_components_log_independently(
    caplog,
    component1: str,
    component2: str,
    message: str
):
    """
    Property: Different components log independently.
    
    For any two components, their logs should be independent
    and correctly identify their source component.
    """
    assume(component1 != component2)
    
    caplog.clear()
    caplog.set_level(logging.INFO)
    logger1 = StructuredErrorLogger(component1)
    logger2 = StructuredErrorLogger(component2)
    
    # Log from both components
    logger1.info(f"{message} from component1")
    logger2.info(f"{message} from component2")
    
    # Verify we have two log records
    assert len(caplog.records) == 2
    
    # Parse logs
    log1 = json.loads(caplog.records[0].getMessage())
    log2 = json.loads(caplog.records[1].getMessage())
    
    # Verify components are correctly identified
    assert log1["component"] == component1
    assert log2["component"] == component2
    assert log1["message"] == f"{message} from component1"
    assert log2["message"] == f"{message} from component2"
