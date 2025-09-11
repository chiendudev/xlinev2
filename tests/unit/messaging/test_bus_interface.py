"""Unit tests for Event Bus Interface and Data Structures."""

from collections.abc import AsyncIterator
from datetime import datetime, UTC
from typing import Any

import pytest

from xline.core.events import (
    Envelope,
    EventBusConnectionError,
    EventBusError,
    PublishError,
    PublishResult,
    SubscribeError,
)


class TestEnvelope:
    """Test Envelope dataclass."""

    def test_envelope_creation_with_required_fields(self):
        """Test creating envelope with only required fields."""
        envelope = Envelope(
            event_type="test.event",
            data={"key": "value"}
        )
        
        assert envelope.event_type == "test.event"
        assert envelope.data == {"key": "value"}
        assert envelope.source == "xline"
        assert envelope.retry_count == 0
        assert envelope.event_id is not None
        assert envelope.timestamp is not None
        assert envelope.correlation_id is None
        assert envelope.headers == {}

    def test_envelope_creation_with_all_fields(self):
        """Test creating envelope with all fields."""
        timestamp = datetime.now(UTC)
        headers = {"header1": "value1"}
        
        envelope = Envelope(
            event_type="test.event",
            data={"key": "value"},
            event_id="test-id",
            timestamp=timestamp,
            correlation_id="corr-123",
            source="test-source",
            headers=headers,
            retry_count=2
        )
        
        assert envelope.event_type == "test.event"
        assert envelope.data == {"key": "value"}
        assert envelope.event_id == "test-id"
        assert envelope.timestamp == timestamp
        assert envelope.correlation_id == "corr-123"
        assert envelope.source == "test-source"
        assert envelope.headers == headers
        assert envelope.retry_count == 2

    def test_envelope_validation_empty_event_type(self):
        """Test validation fails for empty event type."""
        with pytest.raises(ValueError, match="event_type must be a non-empty string"):
            Envelope(event_type="", data={})

    def test_envelope_validation_none_event_type(self):
        """Test validation fails for None event type."""
        with pytest.raises(ValueError, match="event_type must be a non-empty string"):
            Envelope(event_type=None, data={})  # type: ignore

    def test_envelope_validation_non_dict_data(self):
        """Test validation fails for non-dict data."""
        with pytest.raises(ValueError, match="data must be a dictionary"):
            Envelope(event_type="test", data="not a dict")  # type: ignore

    def test_envelope_validation_negative_retry_count(self):
        """Test validation fails for negative retry count."""
        with pytest.raises(ValueError, match="retry_count must be non-negative"):
            Envelope(event_type="test", data={}, retry_count=-1)

    def test_envelope_immutability(self):
        """Test that envelope is immutable (frozen dataclass)."""
        envelope = Envelope(event_type="test", data={})
        
        with pytest.raises(AttributeError):
            envelope.event_type = "new_type"  # type: ignore


class TestPublishResult:
    """Test PublishResult dataclass."""

    def test_successful_publish_result(self):
        """Test creating successful publish result."""
        result = PublishResult(
            success=True,
            message_id="msg-123",
            event_id="evt-123"
        )
        
        assert result.success is True
        assert result.message_id == "msg-123"
        assert result.event_id == "evt-123"
        assert result.error is None
        assert result.timestamp is not None

    def test_failed_publish_result(self):
        """Test creating failed publish result."""
        result = PublishResult(
            success=False,
            event_id="evt-123",
            error="Connection failed"
        )
        
        assert result.success is False
        assert result.message_id is None
        assert result.event_id == "evt-123"
        assert result.error == "Connection failed"
        assert result.timestamp is not None

    def test_publish_result_validation_success_without_message_id(self):
        """Test validation fails for successful result without message_id."""
        with pytest.raises(
            ValueError, match="message_id is required for successful publish operations"
        ):
            PublishResult(success=True, event_id="evt-123")

    def test_publish_result_validation_failure_without_error(self):
        """Test validation fails for failed result without error."""
        with pytest.raises(
            ValueError, match="error message is required for failed publish operations"
        ):
            PublishResult(success=False, event_id="evt-123")

    def test_publish_result_immutability(self):
        """Test that publish result is immutable."""
        result = PublishResult(success=True, message_id="msg-123", event_id="evt-123")
        
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore


class TestEventBusExceptions:
    """Test event bus exception hierarchy."""

    def test_event_bus_error_inheritance(self):
        """Test EventBusError inherits from Exception."""
        error = EventBusError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_event_bus_error_with_cause(self):
        """Test EventBusError with cause."""
        cause = ValueError("original error")
        error = EventBusError("wrapped error", cause=cause)
        
        assert str(error) == "wrapped error"
        assert error.cause == cause

    def test_publish_error_inheritance(self):
        """Test PublishError inherits from EventBusError."""
        error = PublishError("publish failed")
        assert isinstance(error, EventBusError)
        assert isinstance(error, Exception)

    def test_subscribe_error_inheritance(self):
        """Test SubscribeError inherits from EventBusError."""
        error = SubscribeError("subscribe failed")
        assert isinstance(error, EventBusError)
        assert isinstance(error, Exception)

    def test_connection_error_inheritance(self):
        """Test EventBusConnectionError inherits from EventBusError."""
        error = EventBusConnectionError("connection failed")
        assert isinstance(error, EventBusError)
        assert isinstance(error, Exception)


class MockEventBus:
    """Mock implementation of EventBusInterface for testing."""
    
    def __init__(self):
        self.published_events: list[Envelope] = []
        self.subscriptions: dict[str, bool] = {}
        self.health_status = {"status": "healthy"}
        self.closed = False

    async def publish(self, envelope: Envelope) -> PublishResult:
        """Mock publish implementation."""
        if self.closed:
            return PublishResult(
                success=False,
                event_id=envelope.event_id,
                error="Event bus is closed"
            )
        
        self.published_events.append(envelope)
        return PublishResult(
            success=True,
            message_id=f"msg-{len(self.published_events)}",
            event_id=envelope.event_id
        )

    async def subscribe(
        self, 
        event_types: list[str], 
        consumer_group: str,
        consumer_name: str
    ) -> AsyncIterator[Envelope]:
        """Mock subscribe implementation."""
        if self.closed:
            raise SubscribeError("Event bus is closed")
        
        key = f"{consumer_group}:{consumer_name}"
        self.subscriptions[key] = True
        
        # Yield any published events that match the subscription
        for envelope in self.published_events:
            if envelope.event_type in event_types:
                yield envelope

    async def unsubscribe(self, consumer_group: str, consumer_name: str) -> None:
        """Mock unsubscribe implementation."""
        key = f"{consumer_group}:{consumer_name}"
        if key in self.subscriptions:
            del self.subscriptions[key]

    async def health_check(self) -> dict[str, Any]:
        """Mock health check implementation."""
        if self.closed:
            raise EventBusError("Event bus is closed")
        return self.health_status.copy()

    async def close(self) -> None:
        """Mock close implementation."""
        self.closed = True
        self.subscriptions.clear()


class TestEventBusInterface:
    """Test EventBusInterface protocol compliance."""

    @pytest.fixture
    def mock_event_bus(self) -> MockEventBus:
        """Create mock event bus for testing."""
        return MockEventBus()

    @pytest.fixture
    def sample_envelope(self) -> Envelope:
        """Create sample envelope for testing."""
        return Envelope(
            event_type="test.event",
            data={"message": "Hello, World!"},
            correlation_id="test-correlation"
        )

    @pytest.mark.asyncio
    async def test_publish_success(self, mock_event_bus: MockEventBus, sample_envelope: Envelope):
        """Test successful event publishing."""
        result = await mock_event_bus.publish(sample_envelope)
        
        assert result.success is True
        assert result.message_id is not None
        assert result.event_id == sample_envelope.event_id
        assert result.error is None
        assert len(mock_event_bus.published_events) == 1

    @pytest.mark.asyncio
    async def test_publish_failure(self, mock_event_bus: MockEventBus, sample_envelope: Envelope):
        """Test event publishing failure."""
        await mock_event_bus.close()
        
        result = await mock_event_bus.publish(sample_envelope)
        
        assert result.success is False
        assert result.message_id is None
        assert result.event_id == sample_envelope.event_id
        assert result.error == "Event bus is closed"

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self, mock_event_bus: MockEventBus, sample_envelope: Envelope):
        """Test subscribing and receiving events."""
        # First publish an event
        await mock_event_bus.publish(sample_envelope)
        
        # Subscribe to events
        received_events = []
        async for envelope in mock_event_bus.subscribe(
            ["test.event"], "test-group", "test-consumer"
        ):
            received_events.append(envelope)
            break  # Only receive one event for test
        
        assert len(received_events) == 1
        assert received_events[0].event_type == "test.event"
        assert received_events[0].data == {"message": "Hello, World!"}

    @pytest.mark.asyncio
    async def test_subscribe_failure(self, mock_event_bus: MockEventBus):
        """Test subscription failure."""
        await mock_event_bus.close()
        
        with pytest.raises(SubscribeError, match="Event bus is closed"):
            async for _ in mock_event_bus.subscribe(
                ["test.event"], "test-group", "test-consumer"
            ):
                pass

    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_event_bus: MockEventBus):
        """Test unsubscribing from events."""
        # Subscribe first to create subscription
        async for _ in mock_event_bus.subscribe(
            ["test.event"], "test-group", "test-consumer"
        ):
            break  # Exit after first iteration to establish subscription

        # Check subscription exists
        assert "test-group:test-consumer" in mock_event_bus.subscriptions

        # Unsubscribe
        await mock_event_bus.unsubscribe("test-group", "test-consumer")

        # Check subscription removed
        assert "test-group:test-consumer" not in mock_event_bus.subscriptions

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_event_bus: MockEventBus):
        """Test health check when event bus is healthy."""
        health = await mock_event_bus.health_check()
        
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_event_bus: MockEventBus):
        """Test health check when event bus is unhealthy."""
        await mock_event_bus.close()
        
        with pytest.raises(EventBusError, match="Event bus is closed"):
            await mock_event_bus.health_check()

    @pytest.mark.asyncio
    async def test_close(self, mock_event_bus: MockEventBus):
        """Test closing event bus."""
        # Add some subscriptions
        async for _ in mock_event_bus.subscribe(
            ["test.event"], "test-group", "test-consumer"
        ):
            break
        
        assert len(mock_event_bus.subscriptions) > 0
        assert not mock_event_bus.closed
        
        # Close the event bus
        await mock_event_bus.close()
        
        assert mock_event_bus.closed
        assert len(mock_event_bus.subscriptions) == 0
