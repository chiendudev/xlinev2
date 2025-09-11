"""
Unit tests for NATS Event Bus implementation.

Tests the NATS Event Bus with JetStream support, including:
- Connection handling
- Publishing/subscribing to events
- Durable consumer support
- Dead letter queue handling
- Circuit breaker integration
- Graceful degradation when NATS server unavailable
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from xline.core.events.bus import Event
from xline.infrastructure.messaging.nats.bus import NATSEventBus


@pytest.fixture
def mock_nats():
    """Mock NATS client and dependencies."""
    with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
        mock_client = AsyncMock()
        mock_connect.return_value = mock_client

        # Mock JetStream
        mock_js = AsyncMock()
        mock_client.jetstream.return_value = mock_js

        # Mock stream info
        mock_js.stream_info.return_value = Mock(config=Mock(name="test-stream"))

        # Mock consumer info
        mock_js.consumer_info.return_value = Mock(
            config=Mock(durable_name="test-consumer")
        )

        # Mock pull subscription
        mock_psub = AsyncMock()
        mock_js.pull_subscribe.return_value = mock_psub

        yield {
            "connect": mock_connect,
            "client": mock_client,
            "jetstream": mock_js,
            "pull_sub": mock_psub,
        }


@pytest.fixture
def sample_event():
    """Sample event for testing."""
    return Event(
        id="test-event-123",
        type="user.created",
        source="user-service",
        data={"user_id": "123", "email": "test@example.com"},
        timestamp="2024-01-15T10:30:00Z"
    )


@pytest.fixture
async def nats_bus(mock_nats):
    """Create NATSEventBus instance with mocked dependencies."""
    # Set test environment variables
    import os
    os.environ.update({
        "NATS_URL": "nats://localhost:4222",
        "NATS_STREAM_NAME": "test-stream",
        "NATS_CONSUMER_GROUP": "test-consumer",
        "NATS_BATCH_SIZE": "10",
        "NATS_TIMEOUT": "5.0",
        "DLQ_MAX_RETRIES": "3"
    })

    bus = NATSEventBus()
    yield bus

    # Cleanup
    if hasattr(bus, '_client') and bus._client:
        await bus.disconnect()


class TestNATSEventBus:
    """Test cases for NATS Event Bus."""

    async def test_connect_success(self, nats_bus, mock_nats):
        """Test successful connection to NATS server."""
        await nats_bus.connect()

        # Verify NATS client connection
        mock_nats["connect"].assert_called_once_with("nats://localhost:4222")

        # Verify JetStream setup
        mock_nats["client"].jetstream.assert_called_once()
        mock_nats["jetstream"].stream_info.assert_called_once_with("test-stream")

        # Verify consumer setup
        mock_nats["jetstream"].consumer_info.assert_called_once_with(
            "test-stream", "test-consumer"
        )

        assert nats_bus._client is not None
        assert nats_bus._js is not None

    async def test_connect_failure_circuit_breaker(self, nats_bus):
        """Test connection failure triggers circuit breaker."""
        with patch("nats.connect", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await nats_bus.connect()

        # Circuit breaker should be open after failure
        assert nats_bus._circuit_breaker.failure_count > 0

    async def test_publish_event_success(self, nats_bus, mock_nats, sample_event):
        """Test successful event publishing."""
        await nats_bus.connect()

        # Mock successful publish
        mock_nats["jetstream"].publish.return_value = AsyncMock()

        await nats_bus.publish("user.created", sample_event)

        # Verify publish was called with correct parameters
        mock_nats["jetstream"].publish.assert_called_once()
        call_args = mock_nats["jetstream"].publish.call_args

        assert call_args[0][0] == "user.created"  # subject

        # Verify message payload
        message_data = json.loads(call_args[1]["payload"])
        assert message_data["id"] == "test-event-123"
        assert message_data["type"] == "user.created"
        assert message_data["source"] == "user-service"

    async def test_publish_event_failure_dlq(self, nats_bus, mock_nats, sample_event):
        """Test publish failure sends to DLQ after max retries."""
        await nats_bus.connect()

        # Mock publish failure
        mock_nats["jetstream"].publish.side_effect = Exception("Publish failed")

        with pytest.raises(Exception, match="Publish failed"):
            await nats_bus.publish("user.created", sample_event)

        # Should attempt DLQ after retries
        assert mock_nats["jetstream"].publish.call_count > 1

    async def test_subscribe_handler_invocation(self, nats_bus, mock_nats):
        """Test event subscription and handler invocation."""
        await nats_bus.connect()

        # Mock message from NATS
        mock_message = Mock()
        mock_message.data = json.dumps({
            "id": "test-event-123",
            "type": "user.created",
            "source": "user-service",
            "data": {"user_id": "123"},
            "timestamp": "2024-01-15T10:30:00Z"
        }).encode()
        mock_message.ack = AsyncMock()

        # Mock fetch returning message
        mock_nats["pull_sub"].fetch.return_value = [mock_message]

        # Test handler
        handler_called = asyncio.Event()
        received_event = None

        async def test_handler(event: Event):
            nonlocal received_event
            received_event = event
            handler_called.set()

        # Subscribe and simulate message processing
        await nats_bus.subscribe("user.created", test_handler)

        # Manually trigger message processing
        await nats_bus._process_batch()

        # Wait for handler to be called
        await asyncio.wait_for(handler_called.wait(), timeout=1.0)

        # Verify handler was called with correct event
        assert received_event is not None
        assert received_event.id == "test-event-123"
        assert received_event.type == "user.created"
        assert received_event.data["user_id"] == "123"

        # Verify message was acknowledged
        mock_message.ack.assert_called_once()

    async def test_subscribe_handler_error_dlq(self, nats_bus, mock_nats):
        """Test handler error sends message to DLQ after retries."""
        await nats_bus.connect()

        # Mock message from NATS
        mock_message = Mock()
        mock_message.data = json.dumps({
            "id": "test-event-123",
            "type": "user.created",
            "source": "user-service",
            "data": {"user_id": "123"},
            "timestamp": "2024-01-15T10:30:00Z"
        }).encode()
        mock_message.ack = AsyncMock()
        mock_message.nak = AsyncMock()
        mock_message.metadata = Mock()
        mock_message.metadata.num_delivered = 4  # Exceed max retries

        # Mock fetch returning message
        mock_nats["pull_sub"].fetch.return_value = [mock_message]

        # Handler that always fails
        async def failing_handler(event: Event):
            raise ValueError("Handler failed")

        await nats_bus.subscribe("user.created", failing_handler)

        # Process batch
        await nats_bus._process_batch()

        # Verify DLQ publish was attempted
        dlq_calls = [
            call for call in mock_nats["jetstream"].publish.call_args_list
            if len(call[0]) > 0 and "dlq" in call[0][0].lower()
        ]
        assert len(dlq_calls) > 0

    async def test_batch_processing_empty_fetch(self, nats_bus, mock_nats):
        """Test batch processing handles empty fetch gracefully."""
        await nats_bus.connect()

        # Mock empty fetch
        mock_nats["pull_sub"].fetch.return_value = []

        # Should not raise exception
        await nats_bus._process_batch()

        # Verify fetch was called
        mock_nats["pull_sub"].fetch.assert_called_once()

    async def test_disconnect_cleanup(self, nats_bus, mock_nats):
        """Test proper cleanup during disconnect."""
        await nats_bus.connect()

        # Add some state
        nats_bus._running = True
        nats_bus._handlers["test.event"] = [AsyncMock()]

        await nats_bus.disconnect()

        # Verify cleanup
        assert not nats_bus._running
        assert len(nats_bus._handlers) == 0
        mock_nats["client"].close.assert_called_once()

    async def test_circuit_breaker_open_prevents_operations(self, nats_bus):
        """Test circuit breaker prevents operations when open."""
        # Force circuit breaker open
        nats_bus._circuit_breaker.failure_count = 10

        # Operations should fail fast
        with pytest.raises((ConnectionError, RuntimeError)):
            await nats_bus.connect()

    @pytest.mark.parametrize("invalid_data", [
        b"not-json",
        json.dumps({"missing": "required_fields"}).encode(),
        b"",
    ])
    async def test_invalid_message_handling(self, nats_bus, mock_nats, invalid_data):
        """Test handling of invalid message data."""
        await nats_bus.connect()

        # Mock invalid message
        mock_message = Mock()
        mock_message.data = invalid_data
        mock_message.nak = AsyncMock()

        mock_nats["pull_sub"].fetch.return_value = [mock_message]

        async def test_handler(event: Event):
            pass  # Should not be called

        await nats_bus.subscribe("test.event", test_handler)

        # Should handle gracefully
        await nats_bus._process_batch()

        # Message should be negatively acknowledged
        mock_message.nak.assert_called_once()

    async def test_environment_variable_configuration(self):
        """Test configuration from environment variables."""
        import os

        # Set custom environment variables
        test_env = {
            "NATS_URL": "nats://custom:4222",
            "NATS_STREAM_NAME": "custom-stream",
            "NATS_CONSUMER_GROUP": "custom-consumer",
            "NATS_BATCH_SIZE": "25",
            "NATS_TIMEOUT": "10.0",
            "DLQ_MAX_RETRIES": "5"
        }

        with patch.dict(os.environ, test_env):
            bus = NATSEventBus()

            assert bus._url == "nats://custom:4222"
            assert bus._stream_name == "custom-stream"
            assert bus._consumer_group == "custom-consumer"
            assert bus._batch_size == 25
            assert bus._timeout == 10.0
            assert bus._dlq_max_retries == 5

    async def test_graceful_degradation_no_server(self):
        """Test graceful behavior when NATS server is unavailable."""
        # Mock connection failure
        with patch("nats.connect", side_effect=Exception("No servers available")):
            bus = NATSEventBus()

            # Connection should fail but not crash
            with pytest.raises(Exception, match="No servers available"):
                await bus.connect()

            # Bus should remain in disconnected state
            assert bus._client is None
            assert bus._js is None

    async def test_concurrent_message_processing(self, nats_bus, mock_nats):
        """Test concurrent processing of multiple messages."""
        await nats_bus.connect()

        # Mock multiple messages
        messages = []
        for i in range(5):
            mock_message = Mock()
            mock_message.data = json.dumps({
                "id": f"test-event-{i}",
                "type": "test.event",
                "source": "test-service",
                "data": {"index": i},
                "timestamp": "2024-01-15T10:30:00Z"
            }).encode()
            mock_message.ack = AsyncMock()
            messages.append(mock_message)

        mock_nats["pull_sub"].fetch.return_value = messages

        # Track processed events
        processed_events = []

        async def test_handler(event: Event):
            processed_events.append(event.data["index"])
            await asyncio.sleep(0.1)  # Simulate processing time

        await nats_bus.subscribe("test.event", test_handler)

        # Process batch
        await nats_bus._process_batch()

        # All messages should be processed
        assert len(processed_events) == 5
        assert set(processed_events) == {0, 1, 2, 3, 4}

        # All messages should be acknowledged
        for message in messages:
            message.ack.assert_called_once()


class TestNATSEventBusIntegration:
    """Integration-style tests for end-to-end scenarios."""

    async def test_full_publish_subscribe_cycle(self, nats_bus, mock_nats, sample_event):
        """Test complete publish-subscribe cycle."""
        await nats_bus.connect()

        # Setup subscription first
        received_events = []

        async def event_handler(event: Event):
            received_events.append(event)

        await nats_bus.subscribe("user.created", event_handler)

        # Mock message that would be received after publishing
        mock_message = Mock()
        mock_message.data = json.dumps({
            "id": sample_event.id,
            "type": sample_event.type,
            "source": sample_event.source,
            "data": sample_event.data,
            "timestamp": sample_event.timestamp
        }).encode()
        mock_message.ack = AsyncMock()

        mock_nats["pull_sub"].fetch.return_value = [mock_message]
        mock_nats["jetstream"].publish.return_value = AsyncMock()

        # Publish event
        await nats_bus.publish("user.created", sample_event)

        # Simulate message processing
        await nats_bus._process_batch()

        # Verify event was received
        assert len(received_events) == 1
        received_event = received_events[0]
        assert received_event.id == sample_event.id
        assert received_event.type == sample_event.type
        assert received_event.data == sample_event.data

    async def test_multiple_subscribers_same_event(self, nats_bus, mock_nats):
        """Test multiple handlers for the same event type."""
        await nats_bus.connect()

        # Setup multiple handlers
        handler1_called = []
        handler2_called = []

        async def handler1(event: Event):
            handler1_called.append(event.id)

        async def handler2(event: Event):
            handler2_called.append(event.id)

        await nats_bus.subscribe("test.event", handler1)
        await nats_bus.subscribe("test.event", handler2)

        # Mock message
        mock_message = Mock()
        mock_message.data = json.dumps({
            "id": "test-123",
            "type": "test.event",
            "source": "test",
            "data": {},
            "timestamp": "2024-01-15T10:30:00Z"
        }).encode()
        mock_message.ack = AsyncMock()

        mock_nats["pull_sub"].fetch.return_value = [mock_message]

        # Process message
        await nats_bus._process_batch()

        # Both handlers should be called
        assert "test-123" in handler1_called
        assert "test-123" in handler2_called
