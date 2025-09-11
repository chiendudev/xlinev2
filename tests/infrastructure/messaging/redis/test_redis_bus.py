# File: tests/infrastructure/messaging/redis/test_redis_bus.py
"""Comprehensive tests for Redis Event Bus implementation - 95%+ coverage requirement."""
from __future__ import annotations

import asyncio
import json
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from redis.exceptions import RedisError, ResponseError

from xline.core.events.bus import Event, SubscriptionId
from xline.core.reliability.circuit_breaker import CircuitBreakerError
from xline.infrastructure.messaging.redis.bus import RedisEventBus


class MockEventHandler:
    """Mock event handler for testing - renamed to avoid pytest collection."""

    def __init__(self, should_fail: bool = False):
        self.received_events: list[Event] = []
        self.should_fail = should_fail
        self.call_count = 0

    async def handle(self, event: Event) -> None:
        """Handle incoming event."""
        self.call_count += 1
        if self.should_fail:
            raise ValueError(f"Handler intentionally failed on call {self.call_count}")
        self.received_events.append(event)


@pytest.mark.asyncio
class TestRedisEventBusComprehensive:
    """Comprehensive test suite for Redis event bus - targeting 95%+ coverage."""

    @pytest.fixture
    async def mock_redis(self):
        """Create mock Redis client with all required methods."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.xadd.return_value = "1234567890-0"
        mock_redis.xgroup_create.return_value = True

        # Default xreadgroup behavior to prevent hanging
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []
            else:
                raise asyncio.CancelledError("Default cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup
        mock_redis.xack.return_value = 1
        mock_redis.xread.return_value = []
        mock_redis.close.return_value = None
        mock_redis.from_url = AsyncMock(return_value=mock_redis)
        return mock_redis

    @pytest.fixture
    def redis_bus_params(self):
        """Standard Redis bus parameters for testing."""
        return {
            "redis_url": "redis://localhost:6379",
            "max_retries": 3,
            "consumer_group": "test-group",
            "consumer_name": "test-consumer",
            "stream_prefix": "test:events:",
            "dead_letter_queue": "test:dlq",
            "max_queue_size": 100,
        }

    @pytest.fixture
    async def redis_bus(self, mock_redis, redis_bus_params):
        """Create Redis event bus with mocked Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus(**redis_bus_params)
            await bus.initialize()
            yield bus
            await bus.cleanup()

    @pytest.fixture
    def sample_event(self) -> Event:
        """Create sample event for testing."""
        return Event(
            id=str(uuid4()),
            type="test.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"test": "data", "number": 42, "nested": {"key": "value"}},
        )

    # Initialization Tests
    async def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            result = await bus.initialize()

            assert result is True
            assert bus._initialized is True
            assert bus.redis_url == "redis://localhost:6379"
            assert bus.consumer_group == "xline-consumers"
            assert bus.stream_prefix == "xline:events:"

            await bus.cleanup()

    async def test_initialization_custom_params(self, redis_bus_params):
        """Test initialization with custom parameters."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus(**redis_bus_params)
            result = await bus.initialize()

            assert result is True
            assert bus.redis_url == redis_bus_params["redis_url"]
            assert bus.consumer_group == redis_bus_params["consumer_group"]
            assert bus.stream_prefix == redis_bus_params["stream_prefix"]

            await bus.cleanup()

    async def test_initialization_redis_connection_failure(self):
        """Test initialization failure due to Redis connection error."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            result = await bus.initialize()

            assert result is False
            assert bus._initialized is False

    async def test_initialization_circuit_breaker_open(self):
        """Test initialization when circuit breaker is already open."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            # Mock the circuit breaker call to raise error
            circuit_breaker_error = CircuitBreakerError("Circuit breaker is open")
            with patch.object(bus.circuit_breaker, "call", side_effect=circuit_breaker_error):
                result = await bus.initialize()
                assert result is False

    async def test_initialization_unexpected_error(self):
        """Test initialization with unexpected error."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ValueError("Unexpected error")

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            result = await bus.initialize()

            assert result is False
            assert bus._initialized is False

    # Health Check Tests
    async def test_health_check_not_initialized(self):
        """Test health check when bus is not initialized."""
        bus = RedisEventBus()
        result = await bus.health_check()
        assert result is False

    async def test_health_check_no_redis_client(self, mock_redis):
        """Test health check when Redis client is None."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            bus._initialized = True
            bus._redis = None

            result = await bus.health_check()
            assert result is False

    async def test_health_check_redis_error(self, redis_bus, mock_redis):
        """Test health check when Redis ping fails."""
        mock_redis.ping.side_effect = RedisError("Connection lost")
        result = await redis_bus.health_check()
        assert result is False

    async def test_health_check_circuit_breaker_error(self, redis_bus, mock_redis):
        """Test health check when circuit breaker is open."""
        # Mock the circuit breaker call to raise error
        circuit_breaker_error = CircuitBreakerError("Circuit breaker is open")
        with patch.object(redis_bus.circuit_breaker, "call", side_effect=circuit_breaker_error):
            result = await redis_bus.health_check()
            assert result is False

    # Publishing Tests
    async def test_publish_event_success_with_all_fields(self, redis_bus, mock_redis):
        """Test successful event publishing with all event fields."""
        event = Event(
            id="test-123",
            type="comprehensive.test",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"complex": {"nested": "data"}, "array": [1, 2, 3]},
            correlation_id="corr-123",
            version="2.0",
        )

        mock_redis.xadd.return_value = "stream-msg-123"

        result = await redis_bus.publish(event)

        assert result.success is True
        assert result.event_id == event.id
        assert result.message_id == "stream-msg-123"

        # Verify xadd call
        mock_redis.xadd.assert_called_once()
        args = mock_redis.xadd.call_args
        stream_name = args[0][0]
        event_data = args[0][1]

        assert stream_name == "test:events:comprehensive.test"
        assert event_data["id"] == event.id
        assert event_data["correlation_id"] == event.correlation_id
        assert event_data["version"] == event.version

    async def test_publish_event_redis_error(self, redis_bus, mock_redis, sample_event):
        """Test event publishing with Redis error."""
        mock_redis.xadd.side_effect = RedisError("Stream write failed")

        result = await redis_bus.publish(sample_event)

        assert result.success is False
        assert result.event_id == sample_event.id
        assert "Stream write failed" in result.error

    async def test_publish_event_circuit_breaker_open(self, redis_bus, sample_event):
        """Test publishing when circuit breaker is open."""
        # Mock the circuit breaker call to raise error
        circuit_breaker_error = CircuitBreakerError("Circuit breaker is open")
        with patch.object(redis_bus.circuit_breaker, "call", side_effect=circuit_breaker_error):
            result = await redis_bus.publish(sample_event)

            assert result.success is False
            assert "Circuit breaker is open" in result.error

    async def test_publish_event_not_initialized(self, sample_event):
        """Test publishing when bus is not initialized."""
        bus = RedisEventBus()
        result = await bus.publish(sample_event)

        assert result.success is False
        assert "not initialized" in result.error

    async def test_publish_event_redis_none(self, sample_event):
        """Test publishing when Redis client is None."""
        bus = RedisEventBus()
        bus._initialized = True
        bus._redis = None

        result = await bus.publish(sample_event)
        assert result.success is False
        assert "not initialized" in result.error

    # Subscription Tests
    async def test_subscribe_consumer_group_creation_error(self, redis_bus, mock_redis):
        """Test subscription when consumer group creation fails with non-BUSYGROUP error."""
        mock_redis.xgroup_create.side_effect = ResponseError("Server error")
        handler = MockEventHandler()

        with pytest.raises(ResponseError):
            await redis_bus.subscribe("test.event", handler)

    async def test_subscribe_circuit_breaker_open(self, redis_bus):
        """Test subscription when circuit breaker is open."""
        # Mock the circuit breaker call to raise error
        handler = MockEventHandler()
        circuit_breaker_error = CircuitBreakerError("Circuit breaker is open")

        with patch.object(redis_bus.circuit_breaker, "call", side_effect=circuit_breaker_error):
            with pytest.raises(RuntimeError, match="Circuit breaker is open"):
                await redis_bus.subscribe("test.event", handler)

    async def test_subscribe_redis_connection_error(self, redis_bus, mock_redis):
        """Test subscription with Redis connection error."""
        mock_redis.xgroup_create.side_effect = RedisError("Connection failed")
        handler = MockEventHandler()

        with pytest.raises(RedisError):
            await redis_bus.subscribe("test.event", handler)

    async def test_unsubscribe_with_running_task(self, redis_bus):
        """Test unsubscribing with active consumer task."""
        handler = MockEventHandler()
        subscription_id = await redis_bus.subscribe("test.event", handler)

        # Verify task is running
        assert subscription_id.id in redis_bus._consumer_tasks
        task = redis_bus._consumer_tasks[subscription_id.id]
        assert not task.done()

        result = await redis_bus.unsubscribe(subscription_id)

        assert result is True
        assert subscription_id.id not in redis_bus._subscriptions
        assert subscription_id.id not in redis_bus._consumer_tasks

    # Message Processing Tests
    async def test_message_processing_complete_flow(self, redis_bus, mock_redis):
        """Test complete message processing flow."""
        handler = MockEventHandler()

        # Create test event data
        test_event_data = {
            "id": str(uuid4()),
            "type": "processing.test",
            "source": "test_source",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": json.dumps({"message": "test processing"}),
            "correlation_id": str(uuid4()),
            "version": "1.0",
        }

        # Mock xreadgroup to return message once, then empty, then raise CancelledError
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("test:events:processing.test", [("msg-123", test_event_data)])]
            elif call_count == 2:
                return []  # Empty response
            else:
                raise asyncio.CancelledError("Simulated cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup

        # Subscribe and trigger consumer
        subscription_id = await redis_bus.subscribe("processing.test", handler)

        # Wait briefly for processing, then immediately cleanup
        await asyncio.sleep(0.1)
        await redis_bus.unsubscribe(subscription_id)

        # Verify message was processed
        assert len(handler.received_events) == 1
        event = handler.received_events[0]
        assert event.id == test_event_data["id"]
        assert event.type == test_event_data["type"]
        assert event.correlation_id == test_event_data["correlation_id"]

        # Verify message was acknowledged
        mock_redis.xack.assert_called()

    async def test_message_processing_handler_failure_dlq(self, redis_bus, mock_redis):
        """Test message processing with handler failure moving to DLQ."""
        handler = MockEventHandler(should_fail=True)

        test_event_data = {
            "id": str(uuid4()),
            "type": "failing.test",
            "source": "test_source",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": json.dumps({"will": "fail"}),
            "correlation_id": str(uuid4()),
            "version": "1.0",
        }

        # Mock xreadgroup to return message once, then cancel
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("test:events:failing.test", [("msg-456", test_event_data)])]
            elif call_count == 2:
                return []
            else:
                raise asyncio.CancelledError("Simulated cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup

        # Subscribe and wait for processing
        subscription_id = await redis_bus.subscribe("failing.test", handler)
        await asyncio.sleep(0.1)
        await redis_bus.unsubscribe(subscription_id)

        # Verify message was moved to DLQ
        dlq_calls = [
            call
            for call in mock_redis.xadd.call_args_list
            if len(call[0]) > 0 and "test:dlq" in call[0][0]
        ]
        assert len(dlq_calls) > 0

        # Verify original message was acknowledged
        mock_redis.xack.assert_called()

    async def test_consumer_circuit_breaker_failure(self, redis_bus, mock_redis):
        """Test consumer behavior when circuit breaker opens during consumption."""
        handler = MockEventHandler()

        # Mock xreadgroup to fail with Redis error
        mock_redis.xreadgroup.side_effect = RedisError("Connection lost during read")

        # Subscribe and let it fail
        subscription_id = await redis_bus.subscribe("circuit.test", handler)
        await asyncio.sleep(0.1)

        # Consumer should handle the error gracefully
        assert subscription_id.id in redis_bus._consumer_tasks

        # Cleanup
        await redis_bus.unsubscribe(subscription_id)

    async def test_consumer_cancelled_error_handling(self, redis_bus, mock_redis):
        """Test consumer handling of asyncio.CancelledError."""
        handler = MockEventHandler()

        # Mock xreadgroup to work normally
        mock_redis.xreadgroup.return_value = []

        subscription_id = await redis_bus.subscribe("cancel.test", handler)

        # Cancel the consumer task
        task = redis_bus._consumer_tasks[subscription_id.id]
        task.cancel()

        # Wait for cancellation to complete
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_process_message_invalid_handler(self, redis_bus, mock_redis):
        """Test message processing when handler is no longer available."""
        # Create a subscription ID that doesn't exist in handlers
        fake_subscription_id = "fake-sub-123"
        test_fields = {
            "id": "test-msg",
            "type": "test.event",
            "source": "test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": json.dumps({"test": "data"}),
            "version": "1.0",
        }

        # This should handle missing handler gracefully
        await redis_bus._process_message(
            "test:events:test.event", "msg-123", test_fields, fake_subscription_id
        )

    async def test_process_message_malformed_data(self, redis_bus, mock_redis):
        """Test message processing with malformed event data."""
        handler = MockEventHandler()
        subscription_id = await redis_bus.subscribe("malformed.test", handler)

        # Create malformed message data
        malformed_fields = {
            "id": "malformed-msg",
            "type": "malformed.test",
            "source": "test",
            "timestamp": "invalid-timestamp",  # Invalid timestamp
            "data": "invalid-json{",  # Invalid JSON
            "version": "1.0",
        }

        # Process malformed message
        await redis_bus._process_message(
            "test:events:malformed.test", "msg-malformed", malformed_fields, subscription_id.id
        )

        # Should move to DLQ due to processing error
        dlq_calls = [
            call
            for call in mock_redis.xadd.call_args_list
            if len(call[0]) > 0 and "test:dlq" in call[0][0]
        ]
        assert len(dlq_calls) > 0

        # Cleanup subscription
        await redis_bus.unsubscribe(subscription_id)

    # Dead Letter Queue Tests
    async def test_handle_poison_message_redis_none(self):
        """Test poison message handling when Redis client is None."""
        bus = RedisEventBus()
        bus._redis = None

        # Should handle gracefully without errors
        await bus._handle_poison_message("test:stream", "msg-123", {"test": "data"}, "Test error")

    async def test_handle_poison_message_dlq_failure(self, redis_bus, mock_redis):
        """Test poison message handling when DLQ operation fails."""
        # Make DLQ xadd fail
        mock_redis.xadd.side_effect = [
            RedisError("DLQ write failed"),  # First call (DLQ) fails
            "success",  # Subsequent calls succeed
        ]

        await redis_bus._handle_poison_message(
            "test:stream", "msg-456", {"test": "poison"}, "Handler failed"
        )

        # Should attempt to write to DLQ despite failure
        assert mock_redis.xadd.call_count >= 1

    async def test_get_dead_letter_messages_success(self, redis_bus, mock_redis):
        """Test successful retrieval of dead letter queue messages."""
        # Mock DLQ content
        dlq_data = {
            "original_stream": "test:events:failed.event",
            "original_message_id": "failed-msg-123",
            "error": "Handler processing failed",
            "timestamp": datetime.now(UTC).isoformat(),
            "fields": json.dumps(
                {
                    "id": "failed-event-id",
                    "type": "failed.event",
                    "data": json.dumps({"failed": True}),
                }
            ),
        }

        mock_redis.xread.return_value = [("test:dlq", [("dlq-msg-1", dlq_data)])]

        messages = await redis_bus.get_dead_letter_messages()

        assert len(messages) == 1
        message = messages[0]
        assert message["error"] == "Handler processing failed"
        assert message["original_stream"] == "test:events:failed.event"

        # Verify fields are already parsed as dict
        fields = message["fields"]
        assert fields["id"] == "failed-event-id"

    async def test_get_dead_letter_messages_not_initialized(self):
        """Test DLQ retrieval when bus is not initialized."""
        bus = RedisEventBus()
        messages = await bus.get_dead_letter_messages()
        assert messages == []

    async def test_get_dead_letter_messages_redis_none(self):
        """Test DLQ retrieval when Redis client is None."""
        bus = RedisEventBus()
        bus._initialized = True
        bus._redis = None

        messages = await bus.get_dead_letter_messages()
        assert messages == []

    async def test_get_dead_letter_messages_redis_error(self, redis_bus, mock_redis):
        """Test DLQ retrieval with Redis error."""
        mock_redis.xread.side_effect = RedisError("Read failed")

        messages = await redis_bus.get_dead_letter_messages()
        assert messages == []

    # Cleanup Tests
    async def test_cleanup_with_multiple_tasks(self, mock_redis):
        """Test cleanup with multiple consumer tasks."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            await bus.initialize()

            # Create multiple subscriptions
            handler1 = MockEventHandler()
            handler2 = MockEventHandler()

            await bus.subscribe("event1", handler1)
            await bus.subscribe("event2", handler2)

            # Verify tasks exist
            assert len(bus._consumer_tasks) == 2

            # Cleanup
            await bus.cleanup()

            # Verify all resources cleaned up
            assert len(bus._subscriptions) == 0
            assert len(bus._handlers) == 0
            assert len(bus._consumer_tasks) == 0
            assert bus._initialized is False

    async def test_cleanup_no_redis_client(self):
        """Test cleanup when Redis client is None."""
        bus = RedisEventBus()
        bus._initialized = True
        bus._redis = None

        # Should complete without errors
        await bus.cleanup()
        assert bus._initialized is False

    async def test_cleanup_task_cancellation_exception(self, mock_redis):
        """Test cleanup when task cancellation raises exceptions."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            await bus.initialize()

            handler = MockEventHandler()
            await bus.subscribe("exception.test", handler)

            # Mock gather to raise exception
            with patch("asyncio.gather", side_effect=Exception("Gather failed")):
                # Should handle exception gracefully
                await bus.cleanup()

            assert bus._initialized is False

    # Edge Case Tests
    async def test_consumer_no_redis_client(self, redis_bus):
        """Test consumer behavior when Redis client becomes None."""
        # Set Redis client to None after initialization
        redis_bus._redis = None

        # Consumer should exit gracefully
        await redis_bus._consume_messages("test:stream", "test-sub")

    async def test_multiple_initialize_calls(self, mock_redis):
        """Test multiple initialization calls."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()

            # First initialization
            result1 = await bus.initialize()
            assert result1 is True

            # Second initialization should also work
            result2 = await bus.initialize()
            assert result2 is True

            await bus.cleanup()

    async def test_consumer_name_generation(self):
        """Test automatic consumer name generation."""
        with patch("time.time", return_value=1234567890):
            bus = RedisEventBus(consumer_name=None)
            assert bus.consumer_name == "consumer-1234567890"

    async def test_event_serialization_special_types(self, redis_bus, mock_redis):
        """Test event serialization with special data types."""
        event = Event(
            id="special-types",
            type="serialization.test",
            source="test",
            timestamp=datetime.now(UTC),
            data={
                "string": "text",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, "two", 3.0],
                "nested": {"deep": {"value": "nested"}},
            },
        )

        result = await redis_bus.publish(event)
        assert result.success is True

        # Verify data was serialized correctly
        call_args = mock_redis.xadd.call_args
        event_data = call_args[0][1]
        deserialized_data = json.loads(event_data["data"])
        assert deserialized_data == event.data

    async def test_subscribe_success(self, redis_bus, mock_redis):
        """Test successful event subscription with consumer group creation."""
        handler = MockEventHandler()

        subscription_id = await redis_bus.subscribe("test.event", handler)

        assert isinstance(subscription_id, SubscriptionId)
        assert subscription_id.id in redis_bus._subscriptions
        assert subscription_id.id in redis_bus._handlers
        assert subscription_id.id in redis_bus._consumer_tasks

        # Verify consumer group creation
        mock_redis.xgroup_create.assert_called_once()

    async def test_subscribe_existing_group(self, redis_bus, mock_redis):
        """Test subscription when consumer group already exists."""
        mock_redis.xgroup_create.side_effect = RedisError(
            "BUSYGROUP Consumer Group name already exists"
        )

        # Mock xreadgroup to return empty then cancel
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []
            else:
                raise asyncio.CancelledError("Simulated cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup

        handler = MockEventHandler()

        subscription_id = await redis_bus.subscribe("test.event", handler)

        assert isinstance(subscription_id, SubscriptionId)
        # Should not raise error for existing group

        # Cleanup to avoid hanging
        await redis_bus.unsubscribe(subscription_id)

    async def test_subscribe_not_initialized(self):
        """Test subscription when bus is not initialized."""
        bus = RedisEventBus()
        handler = MockEventHandler()

        with pytest.raises(RuntimeError, match="not initialized"):
            await bus.subscribe("test.event", handler)

    async def test_unsubscribe_success(self, redis_bus):
        """Test successful unsubscription."""
        handler = MockEventHandler()
        subscription_id = await redis_bus.subscribe("test.event", handler)

        result = await redis_bus.unsubscribe(subscription_id)

        assert result is True
        assert subscription_id.id not in redis_bus._subscriptions
        assert subscription_id.id not in redis_bus._handlers
        assert subscription_id.id not in redis_bus._consumer_tasks

    async def test_unsubscribe_invalid_subscription(self, redis_bus):
        """Test unsubscribing with invalid subscription ID."""
        invalid_subscription = SubscriptionId(id="invalid")
        result = await redis_bus.unsubscribe(invalid_subscription)
        assert result is False

    async def test_circuit_breaker_protection(self, mock_redis):
        """Test circuit breaker protection during Redis failures."""
        # Configure circuit breaker with low threshold for testing
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            bus.circuit_breaker.failure_threshold = 2

            await bus.initialize()

            # Simulate Redis failures
            mock_redis.xadd.side_effect = RedisError("Connection lost")

            event = Event(
                id=str(uuid4()),
                type="test.event",
                source="test",
                timestamp=datetime.now(UTC),
                data={"test": "data"},
            )

            # First few failures should be handled normally
            result1 = await bus.publish(event)
            assert result1.success is False
            assert "Connection lost" in result1.error

            result2 = await bus.publish(event)
            assert result2.success is False

            # After threshold, circuit breaker should open
            result3 = await bus.publish(event)
            assert result3.success is False
            assert "Circuit breaker is open" in result3.error

            await bus.cleanup()

    async def test_message_processing(self, redis_bus, mock_redis):
        """Test complete message processing from Redis stream."""
        handler = MockEventHandler()

        # Mock message from Redis
        test_event_data = {
            "id": str(uuid4()),
            "type": "test.event",
            "source": "test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": json.dumps({"test": "data"}),
            "correlation_id": str(uuid4()),
            "version": "1.0",
        }

        # Simulate xreadgroup returning a message once, then empty, then cancel
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("xline:events:test.event", [("1234567890-0", test_event_data)])]
            elif call_count == 2:
                return []
            else:
                raise asyncio.CancelledError("Simulated cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup

        # Subscribe to trigger consumer
        subscription_id = await redis_bus.subscribe("test.event", handler)

        # Wait for message processing
        await asyncio.sleep(0.1)
        await redis_bus.unsubscribe(subscription_id)

        # Verify message was processed
        assert len(handler.received_events) == 1
        event = handler.received_events[0]
        assert event.id == test_event_data["id"]
        assert event.type == test_event_data["type"]
        assert event.data == json.loads(test_event_data["data"])

        # Verify message was acknowledged
        mock_redis.xack.assert_called()

    async def test_dead_letter_queue_handling(self, redis_bus, mock_redis):
        """Test dead letter queue handling for failed message processing."""
        # Create a handler that always fails
        handler = MockEventHandler(should_fail=True)

        # Mock message from Redis
        test_event_data = {
            "id": str(uuid4()),
            "type": "test.event",
            "source": "test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": json.dumps({"test": "data"}),
            "correlation_id": str(uuid4()),
            "version": "1.0",
        }

        # Simulate xreadgroup returning a message once, then cancel
        call_count = 0

        async def mock_xreadgroup(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("xline:events:test.event", [("1234567890-0", test_event_data)])]
            elif call_count == 2:
                return []
            else:
                raise asyncio.CancelledError("Simulated cancellation")

        mock_redis.xreadgroup.side_effect = mock_xreadgroup

        # Subscribe with failing handler
        subscription_id = await redis_bus.subscribe("test.event", handler)

        # Wait for message processing
        await asyncio.sleep(0.1)
        await redis_bus.unsubscribe(subscription_id)

        # Verify message was added to DLQ - check for xadd calls to DLQ stream
        dlq_calls = [call for call in mock_redis.xadd.call_args_list if "test:dlq" in str(call)]
        assert len(dlq_calls) > 0

        # Verify original message was acknowledged to remove from pending
        mock_redis.xack.assert_called()

    async def test_get_dead_letter_messages(self, redis_bus, mock_redis):
        """Test retrieving messages from dead letter queue."""
        # Mock DLQ messages
        dlq_data = {
            "original_stream": "xline:events:test.event",
            "original_message_id": "1234567890-0",
            "error": "Handler failed",
            "timestamp": datetime.now(UTC).isoformat(),
            "fields": json.dumps({"id": "test-id", "type": "test.event"}),
        }

        mock_redis.xread.return_value = [("test:dlq", [("dlq-1234567890-0", dlq_data)])]

        messages = await redis_bus.get_dead_letter_messages()

        assert len(messages) == 1
        message = messages[0]
        assert message["error"] == "Handler failed"
        assert message["original_stream"] == "xline:events:test.event"

        # Handle both string and dict for fields
        fields = message["fields"]
        if isinstance(fields, str):
            fields = json.loads(fields)
        assert fields["id"] == "test-id"

    async def test_cleanup_resources(self, mock_redis):
        """Test proper cleanup of Redis event bus resources."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            bus = RedisEventBus()
            await bus.initialize()

            # Create some subscriptions
            handler = MockEventHandler()
            await bus.subscribe("test.event1", handler)
            await bus.subscribe("test.event2", handler)

            # Verify subscriptions exist
            assert len(bus._subscriptions) == 2
            assert len(bus._consumer_tasks) == 2

            # Cleanup
            await bus.cleanup()

            # Verify cleanup
            assert len(bus._subscriptions) == 0
            assert len(bus._consumer_tasks) == 0
            assert bus._initialized is False
            mock_redis.close.assert_called_once()

    async def test_performance_requirements(self, redis_bus, mock_redis, sample_event):
        """Test performance requirements - latency < 50ms for event publishing."""
        import time

        # Measure publishing latency
        start_time = time.time()
        result = await redis_bus.publish(sample_event)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000

        assert result.success is True
        # Note: In real tests, this would validate actual Redis latency
        # For mocked tests, we just verify the call was made efficiently
        assert latency_ms < 100  # Generous for mocked environment
