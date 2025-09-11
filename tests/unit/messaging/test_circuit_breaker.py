"""Unit tests for Circuit Breaker utility."""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from xline.core.events.utils import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception is Exception
        assert config.timeout == 30.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=ValueError,
            timeout=10.0
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.expected_exception is ValueError
        assert config.timeout == 10.0


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create circuit breaker with test config."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Short timeout for testing
            expected_exception=ValueError,
            timeout=1.0
        )
        return CircuitBreaker(config)

    @pytest.fixture
    async def success_func(self) -> AsyncMock:
        """Mock async function that succeeds."""
        mock = AsyncMock(return_value="success")
        return mock

    @pytest.fixture
    async def failure_func(self) -> AsyncMock:
        """Mock async function that fails."""
        mock = AsyncMock(side_effect=ValueError("test error"))
        return mock

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker starts in closed state."""
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
        assert not circuit_breaker.is_half_open

    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker: CircuitBreaker, success_func: AsyncMock):
        """Test successful function call through circuit breaker."""
        result = await circuit_breaker.call(success_func, "arg1", key="value")

        assert result == "success"
        success_func.assert_called_once_with("arg1", key="value")
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_failure_doesnt_open_immediately(
        self, circuit_breaker: CircuitBreaker, failure_func: AsyncMock
    ):
        """Test single failure doesn't open circuit."""
        with pytest.raises(ValueError, match="test error"):
            await circuit_breaker.call(failure_func)

        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_multiple_failures_open_circuit(
        self, circuit_breaker: CircuitBreaker, failure_func: AsyncMock
    ):
        """Test multiple failures open the circuit."""
        # First failure
        with pytest.raises(ValueError, match="test error"):
            await circuit_breaker.call(failure_func)

        assert circuit_breaker.is_closed

        # Second failure should open circuit
        with pytest.raises(ValueError, match="test error"):
            await circuit_breaker.call(failure_func)

        assert circuit_breaker.is_open
        assert circuit_breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(
        self, circuit_breaker: CircuitBreaker, failure_func: AsyncMock, success_func: AsyncMock
    ):
        """Test open circuit blocks all calls."""
        # Force circuit to open
        circuit_breaker.failure_count = 2
        circuit_breaker.last_failure_time = time.time()
        circuit_breaker.state = CircuitState.OPEN

        # Try to call - should be blocked
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker is open"):
            await circuit_breaker.call(success_func)

        success_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker: CircuitBreaker):
        """Test circuit transitions from open to half-open after timeout."""
        # Force circuit to open
        circuit_breaker.failure_count = 2
        circuit_breaker.last_failure_time = time.time() - 0.2  # Past recovery timeout
        circuit_breaker.state = CircuitState.OPEN

        # Create a successful function to test half-open state
        success_func = AsyncMock(return_value="success")

        # Call should succeed and close circuit
        result = await circuit_breaker.call(success_func)

        assert result == "success"
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker: CircuitBreaker):
        """Test failure in half-open state reopens circuit."""
        # Force circuit to half-open
        circuit_breaker.failure_count = 1
        circuit_breaker.last_failure_time = time.time() - 0.2
        circuit_breaker.state = CircuitState.HALF_OPEN

        failure_func = AsyncMock(side_effect=ValueError("test error"))

        # Failure in half-open should immediately open circuit
        with pytest.raises(ValueError, match="test error"):
            await circuit_breaker.call(failure_func)

        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_timeout_failure(self, circuit_breaker: CircuitBreaker):
        """Test function timeout is handled as failure."""
        async def slow_func():
            await asyncio.sleep(2)
            return "success"

        with pytest.raises(TimeoutError, match="Operation timed out after 1.0s"):
            await circuit_breaker.call(slow_func)

        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_unexpected_exception_passes_through(self, circuit_breaker: CircuitBreaker):
        """Test unexpected exceptions pass through without affecting circuit."""
        # Circuit breaker is configured to only catch ValueError
        runtime_error_func = AsyncMock(side_effect=RuntimeError("unexpected"))

        with pytest.raises(RuntimeError, match="unexpected"):
            await circuit_breaker.call(runtime_error_func)

        # Should not affect circuit state since RuntimeError is not expected
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_reset_circuit(self, circuit_breaker: CircuitBreaker):
        """Test manual circuit reset."""
        # Force circuit to open
        circuit_breaker.failure_count = 5
        circuit_breaker.last_failure_time = time.time()
        circuit_breaker.state = CircuitState.OPEN

        # Reset circuit
        await circuit_breaker.reset()

        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time == 0.0

    @pytest.mark.asyncio
    async def test_get_status(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker status reporting."""
        status = circuit_breaker.get_status()

        assert "state" in status
        assert "failure_count" in status
        assert "last_failure_time" in status
        assert "config" in status

        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["last_failure_time"] == 0.0

        config = status["config"]
        assert config["failure_threshold"] == 2
        assert config["recovery_timeout"] == 0.1
        assert config["timeout"] == 1.0

    @pytest.mark.asyncio
    async def test_decorator_usage(self):
        """Test circuit breaker as decorator."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=1.0)
        breaker = CircuitBreaker(config)

        @breaker
        async def decorated_func(x: int) -> int:
            if x < 0:
                raise ValueError("negative number")
            return x * 2

        # Test successful call
        result = await decorated_func(5)
        assert result == 10

        # Test failure
        with pytest.raises(ValueError, match="negative number"):
            await decorated_func(-1)

        # Circuit should be open now
        with pytest.raises(CircuitBreakerOpenError):
            await decorated_func(5)

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker with concurrent calls."""
        call_count = 0

        async def counting_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Small delay
            return call_count

        # Execute multiple calls concurrently
        tasks = [
            circuit_breaker.call(counting_func)
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All calls should succeed
        assert len(results) == 5
        assert all(isinstance(r, int) for r in results)
        assert circuit_breaker.is_closed


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=0)
        breaker = CircuitBreaker(config)

        failure_func = AsyncMock(side_effect=ValueError("error"))

        # First failure should immediately open circuit
        with pytest.raises(ValueError):
            await breaker.call(failure_func)

        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_negative_recovery_timeout(self):
        """Test circuit breaker behavior with negative recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=-1.0  # Negative timeout
        )
        breaker = CircuitBreaker(config)

        # Force circuit open
        breaker.failure_count = 1
        breaker.last_failure_time = time.time()
        breaker.state = CircuitState.OPEN

        success_func = AsyncMock(return_value="success")

        # Should immediately transition to half-open due to negative timeout
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_very_long_timeout(self):
        """Test circuit breaker with very long operation timeout."""
        config = CircuitBreakerConfig(timeout=0.001)  # Very short timeout
        breaker = CircuitBreaker(config)

        async def slow_func():
            await asyncio.sleep(0.1)
            return "success"

        with pytest.raises(TimeoutError):
            await breaker.call(slow_func)

        assert breaker.failure_count == 1
