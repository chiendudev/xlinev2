"""
Unit tests for Message Bus Factory.

Tests the factory pattern for message bus backend selection, including:
- Environment-based backend selection
- Singleton pattern behavior
- Async initialization guard
- Graceful degradation
- Backend failover capabilities
"""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from xline.core.events.bus_interface import EventBusInterface
from xline.infrastructure.messaging.factory import MessageBusFactory


@pytest.fixture
def clean_factory():
    """Reset factory singleton state before each test."""
    MessageBusFactory._instance = None
    MessageBusFactory._lock = asyncio.Lock()
    MessageBusFactory._initialization_lock = asyncio.Lock()
    MessageBusFactory._bus = None
    yield
    # Cleanup after test
    MessageBusFactory._instance = None
    MessageBusFactory._lock = asyncio.Lock()
    MessageBusFactory._initialization_lock = asyncio.Lock()
    MessageBusFactory._bus = None


@pytest.fixture
def mock_redis_bus():
    """Mock Redis Event Bus."""
    mock_bus = AsyncMock(spec=EventBusInterface)
    mock_bus.connect = AsyncMock()
    mock_bus.disconnect = AsyncMock()
    return mock_bus


@pytest.fixture
def mock_nats_bus():
    """Mock NATS Event Bus."""
    mock_bus = AsyncMock(spec=EventBusInterface)
    mock_bus.connect = AsyncMock()
    mock_bus.disconnect = AsyncMock()
    return mock_bus


class TestMessageBusFactory:
    """Test cases for Message Bus Factory."""

    async def test_singleton_behavior(self, clean_factory):
        """Test that factory maintains singleton pattern."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus"
            ) as mock_redis:
                mock_redis.return_value = AsyncMock(spec=EventBusInterface)
                mock_redis.return_value.connect = AsyncMock()

                # Get factory instance twice
                factory1 = await MessageBusFactory.get_instance()
                factory2 = await MessageBusFactory.get_instance()

                # Should be the same instance
                assert factory1 is factory2

    async def test_redis_backend_selection(self, clean_factory, mock_redis_bus):
        """Test Redis backend selection via environment variable."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis_bus
            ):
                bus = await MessageBusFactory.get_message_bus()

                assert bus is mock_redis_bus
                mock_redis_bus.connect.assert_called_once()

    async def test_nats_backend_selection(self, clean_factory, mock_nats_bus):
        """Test NATS backend selection via environment variable."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "nats"}):
            with patch(
                "xline.infrastructure.messaging.factory.NATSEventBus",
                return_value=mock_nats_bus
            ) as mock_nats_class:
                # Mock the lazy import
                with patch(
                    "xline.infrastructure.messaging.factory.import_module"
                ) as mock_import:
                    mock_module = Mock()
                    mock_module.NATSEventBus = mock_nats_class
                    mock_import.return_value = mock_module

                    bus = await MessageBusFactory.get_message_bus()

                    assert bus is mock_nats_bus
                    mock_nats_bus.connect.assert_called_once()

    async def test_default_backend_redis(self, clean_factory, mock_redis_bus):
        """Test default backend selection when no environment variable set."""
        # Clear any existing environment variable
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis_bus
            ):
                bus = await MessageBusFactory.get_message_bus()

                assert bus is mock_redis_bus
                mock_redis_bus.connect.assert_called_once()

    async def test_invalid_backend_fallback(self, clean_factory, mock_redis_bus):
        """Test fallback to Redis when invalid backend specified."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "invalid_backend"}):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis_bus
            ):
                bus = await MessageBusFactory.get_message_bus()

                assert bus is mock_redis_bus
                mock_redis_bus.connect.assert_called_once()

    async def test_connection_failure_handling(self, clean_factory):
        """Test handling of connection failures."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            mock_bus = AsyncMock(spec=EventBusInterface)
            mock_bus.connect.side_effect = ConnectionError("Connection failed")

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_bus
            ):
                with pytest.raises(
                    RuntimeError, match="Failed to initialize any message bus backend"
                ):
                    await MessageBusFactory.get_message_bus()

    async def test_nats_import_failure_fallback(self, clean_factory, mock_redis_bus):
        """Test fallback to Redis when NATS import fails."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "nats"}):
            with patch(
                "xline.infrastructure.messaging.factory.import_module",
                side_effect=ImportError("NATS not available")
            ):
                with patch(
                    "xline.infrastructure.messaging.factory.RedisEventBus",
                    return_value=mock_redis_bus
                ):
                    bus = await MessageBusFactory.get_message_bus()

                    assert bus is mock_redis_bus
                    mock_redis_bus.connect.assert_called_once()

    async def test_concurrent_initialization(self, clean_factory):
        """Test concurrent factory initialization."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            mock_bus = AsyncMock(spec=EventBusInterface)
            mock_bus.connect = AsyncMock()

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_bus
            ):
                # Start multiple concurrent initialization tasks
                tasks = [
                    MessageBusFactory.get_message_bus() for _ in range(5)
                ]

                buses = await asyncio.gather(*tasks)

                # All should return the same bus instance
                assert all(bus is buses[0] for bus in buses)

                # Connect should only be called once
                mock_bus.connect.assert_called_once()

    async def test_bus_reuse_after_initialization(self, clean_factory, mock_redis_bus):
        """Test bus reuse after initial initialization."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis_bus
            ):
                # Get bus first time
                bus1 = await MessageBusFactory.get_message_bus()

                # Get bus second time
                bus2 = await MessageBusFactory.get_message_bus()

                # Should be the same instance
                assert bus1 is bus2

                # Connect should only be called once
                mock_redis_bus.connect.assert_called_once()

    async def test_failover_disabled_by_default(self, clean_factory):
        """Test that failover is disabled by default."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            mock_redis = AsyncMock(spec=EventBusInterface)
            mock_redis.connect.side_effect = ConnectionError("Redis unavailable")

            mock_nats = AsyncMock(spec=EventBusInterface)
            mock_nats.connect = AsyncMock()

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis
            ):
                with patch(
                    "xline.infrastructure.messaging.factory.import_module"
                ) as mock_import:
                    mock_module = Mock()
                    mock_module.NATSEventBus = Mock(return_value=mock_nats)
                    mock_import.return_value = mock_module

                    # Should fail without trying NATS
                    with pytest.raises(RuntimeError):
                        await MessageBusFactory.get_message_bus()

                    # NATS should not be attempted
                    mock_import.assert_not_called()

    async def test_failover_enabled(self, clean_factory, mock_nats_bus):
        """Test failover when enabled via environment variable."""
        with patch.dict(os.environ, {
            "XLINE_MESSAGE_BUS": "redis",
            "ENABLE_FAILOVER": "1"
        }):
            mock_redis = AsyncMock(spec=EventBusInterface)
            mock_redis.connect.side_effect = ConnectionError("Redis unavailable")
            mock_redis.disconnect = AsyncMock()

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis
            ):
                with patch(
                    "xline.infrastructure.messaging.factory.import_module"
                ) as mock_import:
                    mock_module = Mock()
                    mock_module.NATSEventBus = Mock(return_value=mock_nats_bus)
                    mock_import.return_value = mock_module

                    bus = await MessageBusFactory.get_message_bus()

                    # Should get NATS bus after Redis failure
                    assert bus is mock_nats_bus
                    mock_nats_bus.connect.assert_called_once()

                    # Redis disconnect should be called for cleanup
                    mock_redis.disconnect.assert_called_once()

    async def test_environment_variable_normalization(self, clean_factory, mock_redis_bus):
        """Test environment variable value normalization."""
        test_cases = [
            "Redis",  # Different case
            "REDIS",  # Upper case
            " redis ",  # With whitespace
        ]

        for backend_value in test_cases:
            MessageBusFactory._instance = None
            MessageBusFactory._bus = None

            with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": backend_value}):
                with patch(
                    "xline.infrastructure.messaging.factory.RedisEventBus",
                    return_value=mock_redis_bus
                ):
                    bus = await MessageBusFactory.get_message_bus()
                    assert bus is mock_redis_bus

    async def test_both_backends_fail(self, clean_factory):
        """Test behavior when both Redis and NATS backends fail."""
        with patch.dict(os.environ, {
            "XLINE_MESSAGE_BUS": "redis",
            "ENABLE_FAILOVER": "1"
        }):
            mock_redis = AsyncMock(spec=EventBusInterface)
            mock_redis.connect.side_effect = ConnectionError("Redis failed")
            mock_redis.disconnect = AsyncMock()

            mock_nats = AsyncMock(spec=EventBusInterface)
            mock_nats.connect.side_effect = ConnectionError("NATS failed")
            mock_nats.disconnect = AsyncMock()

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis
            ):
                with patch(
                    "xline.infrastructure.messaging.factory.import_module"
                ) as mock_import:
                    mock_module = Mock()
                    mock_module.NATSEventBus = Mock(return_value=mock_nats)
                    mock_import.return_value = mock_module

                    with pytest.raises(
                        RuntimeError, match="Failed to initialize any message bus backend"
                    ):
                        await MessageBusFactory.get_message_bus()

                    # Both disconnects should be called for cleanup
                    mock_redis.disconnect.assert_called_once()
                    mock_nats.disconnect.assert_called_once()

    async def test_lazy_nats_import_success(self, clean_factory, mock_nats_bus):
        """Test successful lazy import of NATS module."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "nats"}):
            with patch(
                "xline.infrastructure.messaging.factory.import_module"
            ) as mock_import:
                mock_module = Mock()
                mock_module.NATSEventBus = Mock(return_value=mock_nats_bus)
                mock_import.return_value = mock_module

                bus = await MessageBusFactory.get_message_bus()

                # Verify correct module import
                mock_import.assert_called_once_with(
                    "xline.infrastructure.messaging.nats.bus"
                )

                # Verify NATS bus creation and connection
                mock_module.NATSEventBus.assert_called_once()
                assert bus is mock_nats_bus
                mock_nats_bus.connect.assert_called_once()

    async def test_factory_reset_after_failure(self, clean_factory):
        """Test factory can be reused after initialization failure."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            # First attempt - connection fails
            mock_bus_fail = AsyncMock(spec=EventBusInterface)
            mock_bus_fail.connect.side_effect = ConnectionError("Connection failed")

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_bus_fail
            ):
                with pytest.raises(RuntimeError):
                    await MessageBusFactory.get_message_bus()

            # Reset factory state
            MessageBusFactory._instance = None
            MessageBusFactory._bus = None

            # Second attempt - connection succeeds
            mock_bus_success = AsyncMock(spec=EventBusInterface)
            mock_bus_success.connect = AsyncMock()

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_bus_success
            ):
                bus = await MessageBusFactory.get_message_bus()

                assert bus is mock_bus_success
                mock_bus_success.connect.assert_called_once()


class TestMessageBusFactoryEdgeCases:
    """Edge case tests for Message Bus Factory."""

    async def test_partial_nats_import_failure(self, clean_factory, mock_redis_bus):
        """Test handling when NATS module imports but class is missing."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "nats"}):
            with patch(
                "xline.infrastructure.messaging.factory.import_module"
            ) as mock_import:
                # Mock module without NATSEventBus class
                mock_module = Mock(spec=[])  # Empty spec, no NATSEventBus
                mock_import.return_value = mock_module

                with patch(
                    "xline.infrastructure.messaging.factory.RedisEventBus",
                    return_value=mock_redis_bus
                ):
                    bus = await MessageBusFactory.get_message_bus()

                    # Should fallback to Redis
                    assert bus is mock_redis_bus
                    mock_redis_bus.connect.assert_called_once()

    async def test_concurrent_failure_and_success(self, clean_factory):
        """Test concurrent initialization where some tasks fail and others succeed."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": "redis"}):
            call_count = 0

            def mock_redis_factory():
                nonlocal call_count
                call_count += 1
                mock_bus = AsyncMock(spec=EventBusInterface)
                if call_count == 1:
                    # First call fails
                    mock_bus.connect.side_effect = ConnectionError("First attempt failed")
                else:
                    # Subsequent calls succeed
                    mock_bus.connect = AsyncMock()
                return mock_bus

            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                side_effect=mock_redis_factory
            ):
                # Start multiple tasks
                tasks = [
                    MessageBusFactory.get_message_bus() for _ in range(3)
                ]

                # Some should fail, some should succeed
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # At least one should fail with RuntimeError
                assert any(isinstance(result, RuntimeError) for result in results)

    async def test_empty_environment_variable(self, clean_factory, mock_redis_bus):
        """Test handling of empty environment variable."""
        with patch.dict(os.environ, {"XLINE_MESSAGE_BUS": ""}):
            with patch(
                "xline.infrastructure.messaging.factory.RedisEventBus",
                return_value=mock_redis_bus
            ):
                bus = await MessageBusFactory.get_message_bus()

                # Should default to Redis
                assert bus is mock_redis_bus
                mock_redis_bus.connect.assert_called_once()
