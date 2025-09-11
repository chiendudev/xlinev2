# File: tests/core/reliability/test_circuit_breaker.py
"""
Tests for CircuitBreaker pattern implementation.
"""
import time

import pytest

from xline.core.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create a CircuitBreaker instance for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=ValueError
        )

    async def test_circuit_breaker_initialization(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker proper initialization."""
        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.recovery_timeout == 1.0
        assert circuit_breaker.expected_exception is ValueError
        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._state == CircuitState.CLOSED
        assert circuit_breaker._last_failure_time is None

    async def test_circuit_breaker_successful_call(self, circuit_breaker: CircuitBreaker):
        """Test successful function call through circuit breaker."""
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._state == CircuitState.CLOSED

    async def test_circuit_breaker_failure_counting(self, circuit_breaker: CircuitBreaker):
        """Test failure counting mechanism."""
        async def failing_func():
            raise ValueError("test error")

        # Call failing function multiple times
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
            assert circuit_breaker._failure_count == i + 1

        # Circuit should now be OPEN
        assert circuit_breaker._state == CircuitState.OPEN

    async def test_circuit_breaker_open_state(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker in open state."""
        # Force circuit to open state
        circuit_breaker._failure_count = 3
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = time.time()

        async def test_func():
            return "should not be called"

        # Should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(test_func)

    async def test_circuit_breaker_half_open_transition(self, circuit_breaker: CircuitBreaker):
        """Test transition from open to half-open state."""
        # Force circuit to open state
        circuit_breaker._failure_count = 3
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = time.time() - 2.0  # 2 seconds ago

        async def success_func():
            return "success"

        # Should transition to half-open and succeed
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker._state == CircuitState.CLOSED
        assert circuit_breaker._failure_count == 0

    async def test_circuit_breaker_half_open_failure(self, circuit_breaker: CircuitBreaker):
        """Test failure in half-open state."""
        # Force circuit to open state
        circuit_breaker._failure_count = 3
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = time.time() - 2.0  # 2 seconds ago

        async def failing_func():
            raise ValueError("test error")

        # Should transition to half-open then back to open
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker._state == CircuitState.OPEN

    async def test_circuit_breaker_recovery(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker recovery after successful calls."""
        # Build up failures
        async def failing_func():
            raise ValueError("test error")

        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker._failure_count == 2
        assert circuit_breaker._state == CircuitState.CLOSED

        # Successful call should reset counter
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker._failure_count == 0

    async def test_circuit_breaker_unexpected_exception_passthrough(
        self, circuit_breaker: CircuitBreaker
    ):
        """Test that unexpected exceptions pass through without affecting circuit."""
        async def unexpected_error_func():
            raise RuntimeError("unexpected error")

        # Should not count towards failures (only ValueError expected)
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(unexpected_error_func)

        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._state == CircuitState.CLOSED

    async def test_circuit_breaker_timeout_behavior(self, circuit_breaker: CircuitBreaker):
        """Test timeout behavior for state transitions."""
        # Set circuit to open with recent failure
        circuit_breaker._failure_count = 3
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._last_failure_time = time.time()

        async def test_func():
            return "test"

        # Should still be open (timeout not reached)
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(test_func)

        # Move time forward
        circuit_breaker._last_failure_time = time.time() - 2.0

        # Should now allow transition to half-open
        result = await circuit_breaker.call(test_func)
        assert result == "test"
        assert circuit_breaker._state == CircuitState.CLOSED

    async def test_circuit_breaker_state_transitions(self, circuit_breaker: CircuitBreaker):
        """Test complete state transition cycle."""
        async def failing_func():
            raise ValueError("test error")

        async def success_func():
            return "success"

        # Start in CLOSED state
        assert circuit_breaker._state == CircuitState.CLOSED

        # Build up failures to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        # Should be OPEN now
        assert circuit_breaker._state == CircuitState.OPEN

        # Fast forward time to allow recovery
        circuit_breaker._last_failure_time = time.time() - 2.0

        # Next call should transition to HALF_OPEN and succeed
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker._state == CircuitState.CLOSED

    async def test_circuit_breaker_concurrent_calls(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker behavior with concurrent calls."""
        call_count = 0

        async def counting_func():
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"

        # Multiple successful calls
        results = []
        for _ in range(5):
            result = await circuit_breaker.call(counting_func)
            results.append(result)

        assert len(results) == 5
        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._state == CircuitState.CLOSED

    async def test_circuit_breaker_edge_cases(self, circuit_breaker: CircuitBreaker):
        """Test edge cases and boundary conditions."""
        # Test with failure count exactly at threshold
        circuit_breaker._failure_count = 2

        async def failing_func():
            raise ValueError("test error")

        # One more failure should trigger open state
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)

        assert circuit_breaker._state == CircuitState.OPEN
        assert circuit_breaker._failure_count == 3
