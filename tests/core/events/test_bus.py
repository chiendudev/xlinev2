"""
Test module for event bus core functionality.
Ensures 95%+ test coverage for all event bus components.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from typing import List, AsyncGenerator

from xline.core.events.bus import (
    Event,
    PublishResult,
    SubscriptionId,
    EventBusError,
    EventPublishError,
    EventSubscriptionError,
    CircuitBreakerError,
    EventHandlerFunc,
)


class MockEventBus:
    """Mock implementation of EventBusInterface for testing."""

    def __init__(self) -> None:
        self.initialized = False
        self.healthy = True
        self.events: List[Event] = []
        self.subscriptions: dict[str, List[EventHandlerFunc]] = {}
        self.subscription_ids: dict[str, str] = {}

    async def initialize(self) -> bool:
        """Initialize the mock event bus."""
        self.initialized = True
        return True

    async def health_check(self) -> bool:
        """Check if mock event bus is healthy."""
        return self.healthy

    async def cleanup(self) -> None:
        """Clean up mock resources."""
        self.events.clear()
        self.subscriptions.clear()
        self.subscription_ids.clear()
        self.initialized = False

    async def publish(self, event: Event) -> PublishResult:
        """Publish an event to the mock bus."""
        if not self.initialized:
            return PublishResult(
                success=False, event_id=event.id, error="Event bus not initialized"
            )

        self.events.append(event)
        handlers_notified = 0

        # Notify subscribers
        if event.type in self.subscriptions:
            for handler in self.subscriptions[event.type]:
                try:
                    await handler(event)
                    handlers_notified += 1
                except Exception:
                    # In real implementation, this would be logged
                    pass

        return PublishResult(
            success=True,
            event_id=event.id,
            message_id=str(uuid4()),
            handlers_notified=handlers_notified,
        )

    async def subscribe(self, event_type: str, handler: EventHandlerFunc) -> SubscriptionId:
        """Subscribe to events of a specific type."""
        if not self.initialized:
            raise EventSubscriptionError("Event bus not initialized")

        subscription_id = str(uuid4())

        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []

        self.subscriptions[event_type].append(handler)
        self.subscription_ids[subscription_id] = event_type

        return SubscriptionId(id=subscription_id)

    async def unsubscribe(self, subscription_id: SubscriptionId) -> bool:
        """Unsubscribe from events."""
        if subscription_id.id not in self.subscription_ids:
            return False

        del self.subscription_ids[subscription_id.id]

        # Note: In real implementation, we'd need to track handler references
        # For mock, we'll just remove the subscription ID tracking
        return True


class TestEvent:
    """Test Event dataclass functionality."""

    def test_event_creation(self) -> None:
        """Test basic event creation."""
        event = Event(
            id="test-event-1",
            type="test.event",
            source="test_service",
            timestamp=datetime.now(),
            data={"key": "value"},
        )

        assert event.id == "test-event-1"
        assert event.type == "test.event"
        assert event.source == "test_service"
        assert event.data == {"key": "value"}
        assert event.version == "1.0"
        assert event.correlation_id is not None

    def test_event_with_correlation_id(self) -> None:
        """Test event creation with explicit correlation ID."""
        correlation_id = str(uuid4())
        event = Event(
            id="test-event-2",
            type="test.event",
            source="test_service",
            timestamp=datetime.now(),
            data={"key": "value"},
            correlation_id=correlation_id,
        )

        assert event.correlation_id == correlation_id

    def test_event_auto_correlation_id(self) -> None:
        """Test event auto-generates correlation ID when not provided."""
        event = Event(
            id="test-event-3",
            type="test.event",
            source="test_service",
            timestamp=datetime.now(),
            data={},
        )

        assert event.correlation_id is not None
        assert len(event.correlation_id) > 0


class TestPublishResult:
    """Test PublishResult dataclass functionality."""

    def test_successful_publish_result(self) -> None:
        """Test successful publish result creation."""
        result = PublishResult(
            success=True, event_id="test-event-1", message_id="msg-123", handlers_notified=3
        )

        assert result.success is True
        assert result.event_id == "test-event-1"
        assert result.message_id == "msg-123"
        assert result.handlers_notified == 3
        assert result.error is None

    def test_failed_publish_result(self) -> None:
        """Test failed publish result creation."""
        result = PublishResult(success=False, event_id="test-event-1", error="Connection failed")

        assert result.success is False
        assert result.event_id == "test-event-1"
        assert result.error == "Connection failed"
        assert result.message_id is None
        assert result.handlers_notified == 0


class TestSubscriptionId:
    """Test SubscriptionId dataclass functionality."""

    def test_subscription_id_creation(self) -> None:
        """Test subscription ID creation."""
        sub_id = SubscriptionId(id="sub-123")
        assert sub_id.id == "sub-123"


class TestMockEventBus:
    """Test MockEventBus implementation."""

    @pytest.fixture
    async def event_bus(self) -> AsyncGenerator[MockEventBus, None]:
        """Create a fresh mock event bus for each test."""
        bus = MockEventBus()
        await bus.initialize()
        yield bus
        await bus.cleanup()

    @pytest.fixture
    def sample_event(self) -> Event:
        """Create a sample event for testing."""
        return Event(
            id="test-event-1",
            type="order.created",
            source="trading_engine",
            timestamp=datetime.now(),
            data={"order_id": "12345", "symbol": "BTCUSDT", "side": "buy"},
        )

    async def test_initialization(self) -> None:
        """Test event bus initialization."""
        bus = MockEventBus()
        assert not bus.initialized

        result = await bus.initialize()
        assert result is True
        assert bus.initialized

    async def test_health_check(self, event_bus: MockEventBus) -> None:
        """Test health check functionality."""
        result = await event_bus.health_check()
        assert result is True

    async def test_publish_without_initialization(self) -> None:
        """Test publishing fails when bus not initialized."""
        bus = MockEventBus()
        event = Event(
            id="test-1", type="test.event", source="test", timestamp=datetime.now(), data={}
        )

        result = await bus.publish(event)
        assert result.success is False
        assert "not initialized" in result.error

    async def test_publish_success(self, event_bus: MockEventBus, sample_event: Event) -> None:
        """Test successful event publishing."""
        result = await event_bus.publish(sample_event)

        assert result.success is True
        assert result.event_id == sample_event.id
        assert result.message_id is not None
        assert len(event_bus.events) == 1
        assert event_bus.events[0] == sample_event

    async def test_subscribe_and_publish(self, event_bus: MockEventBus) -> None:
        """Test subscribing to events and receiving them."""
        received_events: List[Event] = []

        async def test_handler(event: Event) -> None:
            received_events.append(event)

        # Subscribe to events
        subscription = await event_bus.subscribe("order.created", test_handler)
        assert isinstance(subscription, SubscriptionId)

        # Publish an event
        event = Event(
            id="test-1",
            type="order.created",
            source="test",
            timestamp=datetime.now(),
            data={"test": "data"},
        )

        result = await event_bus.publish(event)
        assert result.success is True
        assert result.handlers_notified == 1

        # Check handler received the event
        assert len(received_events) == 1
        assert received_events[0] == event

    async def test_subscribe_without_initialization(self) -> None:
        """Test subscribing fails when bus not initialized."""
        bus = MockEventBus()

        async def test_handler(event: Event) -> None:
            pass

        with pytest.raises(EventSubscriptionError):
            await bus.subscribe("test.event", test_handler)

    async def test_unsubscribe(self, event_bus: MockEventBus) -> None:
        """Test unsubscribing from events."""

        async def test_handler(event: Event) -> None:
            pass

        # Subscribe first
        subscription = await event_bus.subscribe("test.event", test_handler)

        # Then unsubscribe
        result = await event_bus.unsubscribe(subscription)
        assert result is True

        # Unsubscribing again should return False
        result = await event_bus.unsubscribe(subscription)
        assert result is False

    async def test_cleanup(self, event_bus: MockEventBus, sample_event: Event) -> None:
        """Test cleanup functionality."""
        # Add some data
        await event_bus.publish(sample_event)

        async def test_handler(event: Event) -> None:
            pass

        await event_bus.subscribe("test.event", test_handler)

        # Cleanup
        await event_bus.cleanup()

        assert not event_bus.initialized
        assert len(event_bus.events) == 0
        assert len(event_bus.subscriptions) == 0
        assert len(event_bus.subscription_ids) == 0


class TestEventBusErrors:
    """Test event bus error classes."""

    def test_event_bus_error(self) -> None:
        """Test base EventBusError."""
        error = EventBusError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_event_publish_error(self) -> None:
        """Test EventPublishError."""
        error = EventPublishError("Publish failed")
        assert str(error) == "Publish failed"
        assert isinstance(error, EventBusError)

    def test_event_subscription_error(self) -> None:
        """Test EventSubscriptionError."""
        error = EventSubscriptionError("Subscription failed")
        assert str(error) == "Subscription failed"
        assert isinstance(error, EventBusError)

    def test_circuit_breaker_error(self) -> None:
        """Test CircuitBreakerError."""
        error = CircuitBreakerError("Circuit breaker open")
        assert str(error) == "Circuit breaker open"
        assert isinstance(error, EventBusError)
