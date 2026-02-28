"""
Circuit Breaker Implementation for External API Resilience

Implements the circuit breaker pattern to prevent cascading failures
when external dependencies (Whisper, Gemini, MediaPipe) fail.

Circuit States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests rejected immediately
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import time
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
import logging
from app.utils.error_logger import get_error_logger

logger = logging.getLogger(__name__)
error_logger = get_error_logger("circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Open after N consecutive failures
    timeout: float = 30.0  # Seconds before attempting recovery
    half_open_max_calls: int = 1  # Max calls in half-open state


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Opens after failure_threshold consecutive failures.
    Stays open for timeout seconds before transitioning to half-open.
    In half-open state, allows limited calls to test recovery.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 30.0,
        half_open_max_calls: int = 1
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout=timeout,
            half_open_max_calls=half_open_max_calls
        )
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.last_failure_time and \
               time.time() - self.last_failure_time >= self.config.timeout:
                self._transition_to_half_open()
                return False
            return True
        return False
    
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed"""
        return self.state == CircuitState.CLOSED
    
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open"""
        return self.state == CircuitState.HALF_OPEN
    
    def record_success(self):
        """Record a successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker '{self.name}': Success in half-open state "
                f"({self.success_count} successes)"
            )
            # Transition back to closed after success in half-open
            self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    f"Circuit breaker '{self.name}': "
                    f"Resetting failure count after success"
                )
                self.failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            error_logger.warning(
                f"Circuit breaker '{self.name}': Failure in half-open state, reopening",
                circuit_name=self.name,
                state="half_open",
                failure_count=self.failure_count
            )
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                error_logger.error(
                    f"Circuit breaker '{self.name}': Failure threshold reached, opening",
                    circuit_name=self.name,
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold,
                    state_transition="closed_to_open"
                )
                self._transition_to_open()
            else:
                error_logger.warning(
                    f"Circuit breaker '{self.name}': Failure recorded",
                    circuit_name=self.name,
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold
                )
    
    def can_attempt(self) -> bool:
        """Check if a call attempt is allowed"""
        if self.is_open():
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                return False
        
        return True
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if not self.can_attempt():
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable for {self.config.timeout}s"
            )
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if not self.can_attempt():
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable for {self.config.timeout}s"
            )
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.error(
            f"Circuit breaker '{self.name}': "
            f"Transitioned to OPEN state for {self.config.timeout}s"
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        logger.info(
            f"Circuit breaker '{self.name}': "
            f"Transitioned to HALF_OPEN state (testing recovery)"
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info(
            f"Circuit breaker '{self.name}': "
            f"Transitioned to CLOSED state (service recovered)"
        )
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'timeout': self.config.timeout,
                'half_open_max_calls': self.config.half_open_max_calls
            }
        }
    
    def reset(self):
        """Manually reset circuit breaker to closed state"""
        logger.info(f"Circuit breaker '{self.name}': Manual reset")
        self._transition_to_closed()


# Global circuit breakers for external services
whisper_circuit = CircuitBreaker(
    name="whisper",
    failure_threshold=5,
    timeout=30.0
)

gemini_circuit = CircuitBreaker(
    name="gemini",
    failure_threshold=5,
    timeout=30.0
)

mediapipe_circuit = CircuitBreaker(
    name="mediapipe",
    failure_threshold=5,
    timeout=30.0
)


def get_circuit_breaker(service: str) -> CircuitBreaker:
    """
    Get circuit breaker for a specific service.
    
    Args:
        service: Service name ('whisper', 'gemini', 'mediapipe')
        
    Returns:
        CircuitBreaker instance
        
    Raises:
        ValueError: If service name is unknown
    """
    circuits = {
        'whisper': whisper_circuit,
        'gemini': gemini_circuit,
        'mediapipe': mediapipe_circuit
    }
    
    if service not in circuits:
        raise ValueError(f"Unknown service: {service}")
    
    return circuits[service]


def get_all_circuit_states() -> dict:
    """Get state of all circuit breakers"""
    return {
        'whisper': whisper_circuit.get_state(),
        'gemini': gemini_circuit.get_state(),
        'mediapipe': mediapipe_circuit.get_state()
    }
