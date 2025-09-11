"""Circuit Breaker Utility for resilient service operations.

Implements the Circuit Breaker pattern to prevent cascading failures
by temporarily stopping operations that are likely to fail.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Requests fail fast, no actual calls made
- HALF_OPEN: Limited requests allowed to test if service recovered
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying HALF_OPEN
        expected_exception: Exception type that counts as failure
        timeout: Maximum seconds to wait for operation
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type[Exception] = Exception
    timeout: float = 30.0


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocks operation."""
    pass


class CircuitBreaker:
    """Circuit breaker for resilient async operations.

    Usage:
        breaker = CircuitBreaker()

        @breaker
        async def risky_operation():
            # Some operation that might fail
            return await external_service_call()
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorator to wrap async functions with circuit breaker."""
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)
        return wrapper

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerOpenError: If circuit is open
            TimeoutError: If operation times out
            Exception: Any exception from the wrapped function
        """
        async with self._lock:
            await self._check_state()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open. Last failure: {self.last_failure_time}"
                )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            await self._on_success()
            return result

        except TimeoutError:
            await self._on_failure()
            raise TimeoutError(f"Operation timed out after {self.config.timeout}s")

        except self.config.expected_exception as e:
            await self._on_failure()
            raise e

    async def _check_state(self) -> None:
        """Check and update circuit state based on current conditions."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN

        elif self.state == CircuitState.HALF_OPEN:
            # Stay in half-open until success or failure
            pass

    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    async def _on_failure(self) -> None:
        """Handle failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if (self.failure_count >= self.config.failure_threshold or
                self.state == CircuitState.HALF_OPEN):
                self.state = CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN

    async def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            self.failure_count = 0
            self.last_failure_time = 0.0
            self.state = CircuitState.CLOSED

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Dictionary with current state, failure count, and timing info
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "timeout": self.config.timeout,
            }
        }
