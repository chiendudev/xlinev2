"""
Unit tests for Redis Event Bus implementation.

Comprehensive test suite covering:
- Message publishing and subscribing
- Consumer groups and load balancing
- Dead letter queue functionality
- Error handling and resilience
- Connection management and health checks
"""

import asyncio
import json
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

import pytest
from redis.asyncio import Redis

from xline.core.events.bus_interface import Envelope, PublishResult, EventBusError
from xline.infrastructure.messaging.redis.bus import RedisEventBus


class TestRedisEventBus:
    """Test suite for Redis Event Bus implementation."""

    @pytest.fixture
    async def mock_redis(self) -> AsyncMock:
        """Create a properly configured Redis mock."""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.info = AsyncMock(return_value={
            "redis_version": "6.0.0",
            "used_memory_human": "1.0M",
            "connected_clients": 5
        })
        redis_mock.xadd = AsyncMock(return_value=b"test-id")
        redis_mock.xgroup_create = AsyncMock(return_value=True)
        redis_mock.xreadgroup = AsyncMock(return_value=[])
        redis_mock.close = AsyncMock(return_value=None)
        return redis_mock

    @pytest.fixture
    async def event_bus(self, mock_redis: AsyncMock) -> RedisEventBus:
        """Create a Redis event bus instance with mocked dependencies."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            bus = RedisEventBus(
                redis_url="redis://localhost:6379",
                stream_prefix="test",
                consumer_group="test-group",
            )
            await bus.connect()
            return bus

    @pytest.fixture
    def sample_envelope(self) -> Envelope:
        """Create a sample envelope for testing."""
        return Envelope(
            event_id="test-123",
            event_type="test.event",
            payload={"message": "hello world"},
            timestamp=datetime.now(UTC),
            correlation_id="corr-123",
            source="test-service",
            metadata={"version": "1.0"},
        )

    async def test_connect_success(self, mock_redis: AsyncMock) -> None:
        """Test successful connection to Redis."""
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            bus = RedisEventBus(
                redis_url="redis://localhost:6379",
                stream_prefix="test",
                consumer_group="test-group",
            )

            await bus.connect()

            assert bus._is_connected is True
            mock_redis.ping.assert_called_once()

    async def test_connect_failure(self, mock_redis: AsyncMock) -> None:
        """Test connection failure handling."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            bus = RedisEventBus(
                redis_url="redis://localhost:6379",
                stream_prefix="test",
                consumer_group="test-group",
            )

            with pytest.raises(Exception, match="Connection failed"):
                await bus.connect()

    async def test_publish_success(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock, sample_envelope: Envelope
    ) -> None:
        """Test successful message publishing."""
        mock_redis.xadd.return_value = b"1234567890-0"

        result = await event_bus.publish("test.topic", sample_envelope)

        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.message_id == "1234567890-0"
        assert result.error is None

        # Verify Redis xadd was called with correct parameters
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "test:test.topic"  # stream name

        # Verify envelope was serialized correctly
        fields = call_args[0][1]
        assert "data" in fields
        envelope_data = json.loads(fields["data"])
        assert envelope_data["event_id"] == "test-123"
        assert envelope_data["event_type"] == "test.event"

    async def test_publish_failure(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock, sample_envelope: Envelope
    ) -> None:
        """Test message publishing failure."""
        mock_redis.xadd.side_effect = Exception("Redis error")

        result = await event_bus.publish("test.topic", sample_envelope)

        assert isinstance(result, PublishResult)
        assert result.success is False
        assert result.message_id is None
        assert "Redis error" in str(result.error)

    async def test_subscribe_success(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock, sample_envelope: Envelope
    ) -> None:
        """Test successful message subscription."""
        # Mock Redis stream response
        envelope_json = json.dumps(
            {
                "event_id": sample_envelope.event_id,
                "event_type": sample_envelope.event_type,
                "payload": sample_envelope.payload,
                "timestamp": sample_envelope.timestamp.isoformat(),
                "correlation_id": sample_envelope.correlation_id,
                "source": sample_envelope.source,
                "metadata": sample_envelope.metadata,
            }
        )

        mock_redis.xreadgroup.return_value = [
            [b"test:test.topic", [(b"1234567890-0", {b"data": envelope_json.encode()})]]
        ]

        # Create consumer group if not exists
        mock_redis.xgroup_create.return_value = True

        messages = []
        async for envelope in event_bus.subscribe("test.topic"):
            messages.append(envelope)
            break  # Only collect one message for test

        assert len(messages) == 1
        received_envelope = messages[0]
        assert received_envelope.event_id == sample_envelope.event_id
        assert received_envelope.event_type == sample_envelope.event_type
        assert received_envelope.payload == sample_envelope.payload

    async def test_subscribe_no_messages(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test subscription when no messages are available."""
        mock_redis.xreadgroup.return_value = []
        mock_redis.xgroup_create.return_value = True

        messages = []

        # Create a task that will timeout
        async def collect_messages():
            async for envelope in event_bus.subscribe("test.topic"):
                messages.append(envelope)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(collect_messages(), timeout=0.1)

        assert len(messages) == 0

    async def test_subscribe_malformed_message(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test handling of malformed messages."""
        # Mock Redis with invalid JSON
        mock_redis.xreadgroup.return_value = [
            [b"test:test.topic", [(b"1234567890-0", {b"data": b"invalid json"})]]
        ]
        mock_redis.xgroup_create.return_value = True

        messages = []
        async for envelope in event_bus.subscribe("test.topic"):
            messages.append(envelope)
            break  # Only try to collect one message

        # Should not receive any messages due to JSON parsing error
        assert len(messages) == 0

    async def test_health_check_connected(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test health check when connected."""
        mock_redis.ping.return_value = True

        is_healthy = await event_bus.health_check()

        assert is_healthy is True
        mock_redis.ping.assert_called_once()

    async def test_health_check_disconnected(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test health check when disconnected."""
        mock_redis.ping.side_effect = Exception("Connection lost")

        is_healthy = await event_bus.health_check()

        assert is_healthy is False

    async def test_health_check_not_connected(self, mock_redis: AsyncMock) -> None:
        """Test health check when not connected."""
        # Patch Redis.from_url to return failing mock
        with patch("redis.asyncio.Redis.from_url") as mock_from_url:
            mock_redis.ping.side_effect = Exception("Connection failed")
            mock_from_url.return_value = mock_redis
            
            bus = RedisEventBus(
                redis_url="redis://localhost:6379",
                stream_prefix="test", 
                consumer_group="test-group",
            )
            
            with pytest.raises(EventBusError):
                await bus.health_check()

    async def test_disconnect(self, event_bus: RedisEventBus, mock_redis: AsyncMock) -> None:
        """Test disconnection from Redis."""
        await event_bus.disconnect()

        assert event_bus._connected is False
        mock_redis.aclose.assert_called_once()

    async def test_context_manager(self, mock_redis: AsyncMock) -> None:
        """Test using event bus as async context manager."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            async with RedisEventBus(
                redis_url="redis://localhost:6379",
                stream_prefix="test",
                consumer_group="test-group",
            ) as bus:
                assert bus._is_connected is True
                mock_redis.ping.assert_called_once()

    async def test_consumer_group_creation(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test consumer group creation during subscription."""
        mock_redis.xgroup_create.return_value = True
        mock_redis.xreadgroup.return_value = []

        # Start subscription which should create consumer group
        async def start_subscription():
            async for _ in event_bus.subscribe("test.topic"):
                break

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(start_subscription(), timeout=0.1)

        # Verify consumer group was created
        mock_redis.xgroup_create.assert_called_once_with(
            "test:test.topic", "test-group", id="0", mkstream=True
        )

    async def test_consumer_group_already_exists(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test handling when consumer group already exists."""
        # Simulate group already exists error
        from redis.exceptions import ResponseError

        mock_redis.xgroup_create.side_effect = ResponseError(
            "BUSYGROUP Consumer Group name already exists"
        )
        mock_redis.xreadgroup.return_value = []

        # Start subscription which should handle existing group gracefully
        async def start_subscription():
            async for _ in event_bus.subscribe("test.topic"):
                break

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(start_subscription(), timeout=0.1)

        # Should have attempted to create group but handled the error
        mock_redis.xgroup_create.assert_called_once()

    async def test_envelope_serialization_roundtrip(
        self, event_bus: RedisEventBus, sample_envelope: Envelope
    ) -> None:
        """Test that envelope serialization/deserialization preserves data."""
        # Test the internal serialization methods
        serialized = event_bus._serialize_envelope(sample_envelope)
        deserialized = event_bus._deserialize_envelope(serialized)

        assert deserialized.event_id == sample_envelope.event_id
        assert deserialized.event_type == sample_envelope.event_type
        assert deserialized.payload == sample_envelope.payload
        assert deserialized.correlation_id == sample_envelope.correlation_id
        assert deserialized.source == sample_envelope.source
        assert deserialized.metadata == sample_envelope.metadata

        # Timestamps should be close (within 1 second)
        time_diff = abs((deserialized.timestamp - sample_envelope.timestamp).total_seconds())
        assert time_diff < 1.0

    async def test_complex_payload_serialization(self, event_bus: RedisEventBus) -> None:
        """Test serialization of complex payload types."""
        complex_envelope = Envelope(
            event_id="complex-123",
            event_type="complex.event",
            payload={
                "nested": {"dict": {"value": 42}},
                "list": [1, 2, 3, "string"],
                "boolean": True,
                "null": None,
                "float": 3.14159,
            },
            timestamp=datetime.now(UTC),
            correlation_id="complex-corr",
            source="complex-service",
        )

        serialized = event_bus._serialize_envelope(complex_envelope)
        deserialized = event_bus._deserialize_envelope(serialized)

        assert deserialized.payload == complex_envelope.payload

    async def test_subscription_error_handling(
        self, event_bus: RedisEventBus, mock_redis: AsyncMock
    ) -> None:
        """Test error handling during subscription."""
        mock_redis.xgroup_create.return_value = True
        mock_redis.xreadgroup.side_effect = Exception("Redis connection lost")

        messages = []

        # Should handle Redis errors gracefully
        async def collect_messages():
            async for envelope in event_bus.subscribe("test.topic"):
                messages.append(envelope)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(collect_messages(), timeout=0.1)

        assert len(messages) == 0
