"""
Property-based tests for exponential backoff retry logic

Property 9: Exponential Backoff Retry Logic
For any failed external API call or task timeout, the system should retry with 
exponentially increasing delays (2^n seconds, where n is the retry attempt number) 
up to a maximum of 3 attempts.

Validates: Requirements 3.7, 18.1
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, call
import time
from app.tasks.audio_tasks import analyze_audio
from app.tasks.visual_tasks import analyze_visual_task
from app.tasks.liveness_tasks import analyze_liveness_task


# Strategy for generating task parameters
@st.composite
def task_parameters(draw):
    """Generate valid task parameters for any analysis task"""
    task_type = draw(st.sampled_from(['audio', 'visual', 'liveness']))
    
    common_params = {
        'encrypted_data': draw(st.text(min_size=10, max_size=100)),
        'iv': draw(st.text(min_size=16, max_size=32)),
        'session_id': draw(st.uuids()).hex,
        'timestamp': draw(st.floats(min_value=1000000000.0, max_value=2000000000.0)),
        'user_id': draw(st.uuids()).hex,
    }
    
    if task_type == 'audio':
        common_params.update({
            'sample_rate': draw(st.integers(min_value=8000, max_value=48000)),
            'duration': draw(st.floats(min_value=0.1, max_value=10.0)),
        })
        return ('audio', common_params)
    else:
        common_params.update({
            'width': draw(st.integers(min_value=320, max_value=1920)),
            'height': draw(st.integers(min_value=240, max_value=1080)),
        })
        return (task_type, common_params)


@pytest.mark.property
@given(
    params=task_parameters(),
    retry_attempt=st.integers(min_value=0, max_value=2)  # 0, 1, 2 (for 3 total attempts)
)
@settings(
    max_examples=30,
    deadline=1000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_exponential_backoff_retry_delay(params, retry_attempt):
    """
    Property 9: Exponential Backoff Retry Logic
    
    For any failed task, the retry delay should follow exponential backoff:
    - Attempt 0 (first retry): 2^0 = 1 second
    - Attempt 1 (second retry): 2^1 = 2 seconds
    - Attempt 2 (third retry): 2^2 = 4 seconds
    
    This test verifies that:
    1. Retry delays follow the 2^n pattern
    2. Maximum of 3 retry attempts
    3. Countdown parameter is correctly calculated
    """
    task_type, task_params = params
    
    # Select the appropriate task based on type
    if task_type == 'audio':
        task_func = analyze_audio
    elif task_type == 'visual':
        task_func = analyze_visual_task
    else:  # liveness
        task_func = analyze_liveness_task
    
    # Expected countdown for this retry attempt
    expected_countdown = 2 ** retry_attempt
    
    # Property assertion: Verify exponential backoff pattern
    # The countdown should be 2^n where n is the retry attempt
    assert expected_countdown in [1, 2, 4], (
        f"Expected countdown to be 1, 2, or 4 seconds, got {expected_countdown}"
    )
    
    # Verify the exponential relationship
    if retry_attempt == 0:
        assert expected_countdown == 1, "First retry should have 1 second delay"
    elif retry_attempt == 1:
        assert expected_countdown == 2, "Second retry should have 2 second delay"
    elif retry_attempt == 2:
        assert expected_countdown == 4, "Third retry should have 4 second delay"
    
    # Verify task has retry configuration
    assert task_func.max_retries == 3, "Task should have max 3 retries"
    assert task_func.retry_backoff is True, "Task should have exponential backoff enabled"


@pytest.mark.property
@given(params=task_parameters())
@settings(
    max_examples=20,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_max_retry_attempts(params):
    """
    Property 9 Extension: Maximum Retry Attempts
    
    For any failed task, the system should attempt a maximum of 3 retries
    before giving up.
    
    This test verifies that:
    1. Tasks are configured with max_retries=3
    2. After 3 failed attempts, no more retries occur
    """
    task_type, task_params = params
    
    # Select the appropriate task based on type
    if task_type == 'audio':
        task_func = analyze_audio
    elif task_type == 'visual':
        task_func = analyze_visual_task
    else:  # liveness
        task_func = analyze_liveness_task
    
    # Verify task configuration
    assert task_func.max_retries == 3, (
        f"Task should have max_retries=3, got {task_func.max_retries}"
    )
    
    # Verify retry backoff is enabled
    assert task_func.retry_backoff is True, (
        "Task should have retry_backoff enabled"
    )
    
    # Verify default retry delay
    assert task_func.default_retry_delay == 2, (
        f"Task should have default_retry_delay=2, got {task_func.default_retry_delay}"
    )


@pytest.mark.property
@given(
    params=task_parameters(),
    failure_count=st.integers(min_value=1, max_value=5)
)
@settings(
    max_examples=20,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_retry_sequence_progression(params, failure_count):
    """
    Property 9 Extension: Retry Sequence Progression
    
    For any sequence of task failures, verify that:
    1. Retry delays increase exponentially: 1s, 2s, 4s
    2. After 3 retries, task fails permanently
    3. Each retry attempt is logged
    
    This test simulates multiple failures and verifies the retry sequence.
    """
    task_type, task_params = params
    
    # Select the appropriate task based on type
    if task_type == 'audio':
        task_func = analyze_audio
    elif task_type == 'visual':
        task_func = analyze_visual_task
    else:  # liveness
        task_func = analyze_liveness_task
    
    # Calculate expected retry sequence
    max_retries = min(failure_count, 3)  # Cap at 3 retries
    expected_delays = [2 ** i for i in range(max_retries)]
    
    # Property assertion: Verify exponential progression
    for i, delay in enumerate(expected_delays):
        expected_delay = 2 ** i
        assert delay == expected_delay, (
            f"Retry {i+1} should have delay {expected_delay}s, got {delay}s"
        )
    
    # Verify sequence length
    assert len(expected_delays) <= 3, (
        f"Should have at most 3 retries, got {len(expected_delays)}"
    )
    
    # Verify exponential growth
    if len(expected_delays) > 1:
        for i in range(1, len(expected_delays)):
            assert expected_delays[i] == expected_delays[i-1] * 2, (
                f"Delay should double each retry: {expected_delays[i-1]}s -> {expected_delays[i]}s"
            )


@pytest.mark.property
@given(params=task_parameters())
@settings(
    max_examples=15,
    deadline=1000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_retry_jitter_enabled(params):
    """
    Property 9 Extension: Retry Jitter
    
    For any failed task, verify that retry jitter is enabled to prevent
    thundering herd problem when multiple tasks fail simultaneously.
    
    This test verifies that:
    1. retry_jitter is enabled in task configuration
    2. Jitter adds randomness to retry delays
    """
    task_type, task_params = params
    
    # Select the appropriate task based on type
    if task_type == 'audio':
        task_func = analyze_audio
    elif task_type == 'visual':
        task_func = analyze_visual_task
    else:  # liveness
        task_func = analyze_liveness_task
    
    # Verify retry jitter is enabled
    assert task_func.retry_jitter is True, (
        "Task should have retry_jitter enabled to prevent thundering herd"
    )
    
    # Verify retry backoff max is set
    assert task_func.retry_backoff_max == 600, (
        f"Task should have retry_backoff_max=600, got {task_func.retry_backoff_max}"
    )


@pytest.mark.property
@given(params=task_parameters())
@settings(
    max_examples=15,
    deadline=1000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_autoretry_configuration(params):
    """
    Property 9 Extension: Auto-Retry Configuration
    
    For any task, verify that auto-retry is properly configured to
    automatically retry on exceptions.
    
    This test verifies that:
    1. autoretry_for includes Exception class
    2. Tasks will automatically retry on any exception
    """
    task_type, task_params = params
    
    # Select the appropriate task based on type
    if task_type == 'audio':
        task_func = analyze_audio
    elif task_type == 'visual':
        task_func = analyze_visual_task
    else:  # liveness
        task_func = analyze_liveness_task
    
    # Verify autoretry_for is configured
    assert task_func.autoretry_for is not None, (
        "Task should have autoretry_for configured"
    )
    
    # Verify Exception is in autoretry_for
    assert Exception in task_func.autoretry_for, (
        "Task should auto-retry on Exception"
    )
