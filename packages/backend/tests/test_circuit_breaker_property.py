"""
Property-Based Tests for Circuit Breaker

Feature: production-ready-browser-extension
Property 38: Circuit Breaker State Transitions

For any external dependency (Whisper, Gemini, MediaPipe), after 5 consecutive
failures, the circuit breaker should open and reject requests for 30 seconds
before attempting recovery.

Validates: Requirements 18.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import time
from app.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState
)


@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
    num_failures=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=100, deadline=None)
def test_circuit_opens_after_threshold_failures(
    failure_threshold: int,
    num_failures: int
):
    """
    Property: Circuit breaker opens after reaching failure threshold.
    
    For any failure threshold N and number of failures M:
    - If M >= N, circuit should be OPEN
    - If M < N, circuit should be CLOSED
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=30.0
    )
    
    # Record failures
    for _ in range(num_failures):
        circuit.record_failure()
    
    # Verify state
    if num_failures >= failure_threshold:
        assert circuit.is_open(), \
            f"Circuit should be OPEN after {num_failures} failures " \
            f"(threshold={failure_threshold})"
        assert circuit.state == CircuitState.OPEN
    else:
        assert circuit.is_closed(), \
            f"Circuit should be CLOSED with {num_failures} failures " \
            f"(threshold={failure_threshold})"
        assert circuit.state == CircuitState.CLOSED


@given(
    failure_threshold=st.integers(min_value=3, max_value=10),
    timeout=st.floats(min_value=0.1, max_value=2.0)
)
@settings(max_examples=100, deadline=None)
def test_circuit_transitions_to_half_open_after_timeout(
    failure_threshold: int,
    timeout: float
):
    """
    Property: Circuit breaker transitions to HALF_OPEN after timeout.
    
    For any timeout T, after circuit opens and T seconds elapse,
    the circuit should transition to HALF_OPEN state.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=timeout
    )
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
    
    assert circuit.is_open()
    
    # Wait for timeout
    time.sleep(timeout + 0.1)  # Add small buffer
    
    # Check if circuit allows attempt (should transition to half-open)
    can_attempt = circuit.can_attempt()
    
    # After timeout, circuit should allow attempts (half-open)
    assert can_attempt, \
        f"Circuit should allow attempts after {timeout}s timeout"
    
    # Verify state is half-open
    assert circuit.state == CircuitState.HALF_OPEN


@given(
    failure_threshold=st.integers(min_value=2, max_value=8),
    num_successes=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
def test_circuit_closes_after_success_in_half_open(
    failure_threshold: int,
    num_successes: int
):
    """
    Property: Circuit breaker closes after success in HALF_OPEN state.
    
    For any circuit in HALF_OPEN state, recording a success should
    transition it back to CLOSED state.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=0.1
    )
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
    
    assert circuit.is_open()
    
    # Wait for timeout to transition to half-open
    time.sleep(0.2)
    circuit.can_attempt()  # Trigger transition
    
    assert circuit.state == CircuitState.HALF_OPEN
    
    # Record success
    circuit.record_success()
    
    # Should transition to CLOSED
    assert circuit.is_closed(), \
        "Circuit should be CLOSED after success in HALF_OPEN state"
    assert circuit.state == CircuitState.CLOSED


@given(
    failure_threshold=st.integers(min_value=2, max_value=8)
)
@settings(max_examples=100, deadline=None)
def test_circuit_reopens_on_failure_in_half_open(
    failure_threshold: int
):
    """
    Property: Circuit breaker reopens on failure in HALF_OPEN state.
    
    For any circuit in HALF_OPEN state, recording a failure should
    transition it back to OPEN state.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=0.1
    )
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
    
    # Wait for timeout to transition to half-open
    time.sleep(0.2)
    circuit.can_attempt()  # Trigger transition
    
    assert circuit.state == CircuitState.HALF_OPEN
    
    # Record failure in half-open state
    circuit.record_failure()
    
    # Should transition back to OPEN
    assert circuit.is_open(), \
        "Circuit should be OPEN after failure in HALF_OPEN state"
    assert circuit.state == CircuitState.OPEN


@given(
    failure_threshold=st.integers(min_value=3, max_value=10),
    num_failures_before_success=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
def test_success_resets_failure_count_in_closed_state(
    failure_threshold: int,
    num_failures_before_success: int
):
    """
    Property: Success resets failure count in CLOSED state.
    
    For any number of failures < threshold, recording a success
    should reset the failure count to 0.
    """
    assume(num_failures_before_success < failure_threshold)
    
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=30.0
    )
    
    # Record some failures (but not enough to open)
    for _ in range(num_failures_before_success):
        circuit.record_failure()
    
    assert circuit.is_closed()
    assert circuit.failure_count == num_failures_before_success
    
    # Record success
    circuit.record_success()
    
    # Failure count should be reset
    assert circuit.failure_count == 0, \
        "Failure count should be reset to 0 after success"
    assert circuit.is_closed()


@given(
    failure_threshold=st.integers(min_value=3, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_circuit_rejects_calls_when_open(
    failure_threshold: int
):
    """
    Property: Circuit breaker rejects calls when OPEN.
    
    For any circuit in OPEN state, attempting to call a function
    should raise CircuitBreakerOpen exception.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=30.0
    )
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
    
    assert circuit.is_open()
    
    # Attempt to call function
    def dummy_function():
        return "success"
    
    with pytest.raises(CircuitBreakerOpen) as exc_info:
        circuit.call(dummy_function)
    
    assert "open" in str(exc_info.value).lower()


@given(
    failure_threshold=st.integers(min_value=3, max_value=10),
    timeout=st.floats(min_value=0.1, max_value=2.0)
)
@settings(max_examples=100, deadline=None)
def test_circuit_state_transitions_are_logged(
    failure_threshold: int,
    timeout: float
):
    """
    Property: All circuit state transitions are properly tracked.
    
    For any sequence of failures and successes, the circuit state
    should always be one of: CLOSED, OPEN, or HALF_OPEN.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=timeout
    )
    
    # Initial state should be CLOSED
    assert circuit.state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    assert circuit.state == CircuitState.CLOSED
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
        assert circuit.state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    
    assert circuit.state == CircuitState.OPEN
    
    # Wait for timeout
    time.sleep(timeout + 0.1)
    circuit.can_attempt()
    
    assert circuit.state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    assert circuit.state == CircuitState.HALF_OPEN
    
    # Record success to close
    circuit.record_success()
    
    assert circuit.state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]
    assert circuit.state == CircuitState.CLOSED


@given(
    failure_threshold=st.integers(min_value=3, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_get_state_returns_complete_information(
    failure_threshold: int
):
    """
    Property: get_state() returns complete circuit breaker information.
    
    For any circuit breaker, get_state() should return a dict with
    all relevant state information.
    """
    circuit = CircuitBreaker(
        name="test_service",
        failure_threshold=failure_threshold,
        timeout=30.0
    )
    
    state = circuit.get_state()
    
    # Verify all required fields are present
    assert 'name' in state
    assert 'state' in state
    assert 'failure_count' in state
    assert 'success_count' in state
    assert 'last_failure_time' in state
    assert 'config' in state
    
    # Verify config fields
    assert 'failure_threshold' in state['config']
    assert 'timeout' in state['config']
    assert 'half_open_max_calls' in state['config']
    
    # Verify values
    assert state['name'] == "test_service"
    assert state['state'] in ['closed', 'open', 'half_open']
    assert state['config']['failure_threshold'] == failure_threshold


@given(
    failure_threshold=st.integers(min_value=3, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_reset_transitions_to_closed_from_any_state(
    failure_threshold: int
):
    """
    Property: reset() transitions circuit to CLOSED from any state.
    
    For any circuit in any state, calling reset() should transition
    it to CLOSED state and reset all counters.
    """
    circuit = CircuitBreaker(
        name="test",
        failure_threshold=failure_threshold,
        timeout=0.1
    )
    
    # Open the circuit
    for _ in range(failure_threshold):
        circuit.record_failure()
    
    assert circuit.is_open()
    
    # Reset
    circuit.reset()
    
    # Should be closed with reset counters
    assert circuit.is_closed()
    assert circuit.state == CircuitState.CLOSED
    assert circuit.failure_count == 0
    assert circuit.success_count == 0
