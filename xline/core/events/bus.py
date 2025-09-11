# File: xline/core/events/bus.py
from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

logger = structlog.get_logger(__name__)


@dataclass
class Event:
    """Base event class for all system events."""

    id: str
    type: str
    source: str
    timestamp: datetime
    data: dict[str, Any]
    correlation_id: str | None = None
    version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = str(uuid4())


@dataclass
class PublishResult:
    """Result of event publishing operation."""

    success: bool
    event_id: str
    error: str | None = None
    message_id: str | None = None
    handlers_notified: int = 0


@dataclass
class SubscriptionId:
    """Unique identifier for event subscription."""

    id: str


class EventBusInterface(Protocol):
    """Protocol defining event bus interface that ALL implementations must follow."""

    async def initialize(self) -> bool:
        """Initialize the event bus."""
        ...

    async def health_check(self) -> bool:
        """Check if event bus is healthy."""
        ...

    async def cleanup(self) -> None:
        """Clean up resources."""
        ...

    async def publish(self, event: Event) -> PublishResult:
        """Publish an event to the bus.

        Args:
            event: Event to publish

        Returns:
            PublishResult with success status and metadata
        """
        ...

    async def subscribe(self, event_type: str, handler: EventHandler) -> SubscriptionId:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            handler: Handler function to process events

        Returns:
            SubscriptionId for the subscription
        """
        ...

    async def unsubscribe(self, subscription_id: SubscriptionId) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: Subscription to cancel

        Returns:
            True if successfully unsubscribed
        """
        ...


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: Event) -> None:
        """Handle an event.

        Args:
            event: Event to process
        """
        ...


# In-memory implementation for testing and fallback
class InMemoryEventBus:
    """In-memory event bus implementation for testing and fallback."""

    def __init__(self, enable_dlq: bool = True) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._subscriptions: dict[str, str] = {}  # subscription_id -> event_type
        self._dlq: list[Event] = [] if enable_dlq else None  # Dead Letter Queue
        self._failed_events: dict[str, int] = {}  # event_id -> retry_count
        self._max_retries = 3
        self._enable_dlq = enable_dlq
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the in-memory event bus."""
        self._initialized = True
        logger.info("InMemoryEventBus initialized")
        return True

    async def health_check(self) -> bool:
        """Check if event bus is healthy."""
        return self._initialized

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._subscribers.clear()
        self._subscriptions.clear()
        if self._dlq is not None:
            self._dlq.clear()
        self._failed_events.clear()
        self._initialized = False
        logger.info("InMemoryEventBus cleaned up")
    
    def get_dlq_count(self) -> int:
        """Get the number of events in the Dead Letter Queue."""
        return len(self._dlq) if self._dlq is not None else 0
    
    def get_dlq_events(self) -> list[Event]:
        """Get all events in the Dead Letter Queue."""
        return self._dlq.copy() if self._dlq is not None else []

    async def publish(self, event: Event) -> PublishResult:
        """Publish an event to the bus."""
        if not self._initialized:
            return PublishResult(
                success=False, event_id=event.id, error="Event bus not initialized"
            )

        handlers = self._subscribers.get(event.type, [])
        handlers_notified = 0
        failed_handlers = 0

        for handler in handlers:
            if self._enable_dlq:
                retry_count = self._failed_events.get(event.id, 0)
                
                # If already in DLQ, skip processing
                if retry_count >= self._max_retries:
                    continue
                    
            try:
                await handler.handle(event)
                handlers_notified += 1
                # Reset retry count on success
                if self._enable_dlq and event.id in self._failed_events:
                    del self._failed_events[event.id]
            except Exception as e:
                failed_handlers += 1
                if self._enable_dlq:
                    # Increment retry count
                    retry_count = self._failed_events.get(event.id, 0) + 1
                    self._failed_events[event.id] = retry_count
                    
                    if retry_count >= self._max_retries:
                        # Move to DLQ after max retries
                        if self._dlq is not None:
                            self._dlq.append(event)
                        logger.error(
                            "Event moved to DLQ after max retries",
                            event_id=event.id,
                            event_type=event.type,
                            retry_count=retry_count,
                            error=str(e)
                        )
                    else:
                        logger.error(
                            "Error handling event",
                            event_id=event.id,
                            event_type=event.type,
                            retry_count=retry_count,
                            error=str(e)
                        )
                else:
                    # Just log errors without DLQ tracking
                    logger.error(
                        "Error handling event",
                        event_id=event.id,
                        event_type=event.type,
                        error=str(e)
                    )

        logger.debug(
            "Event published",
            event_id=event.id,
            event_type=event.type,
            handlers_notified=handlers_notified,
        )

        return PublishResult(success=True, event_id=event.id, handlers_notified=handlers_notified)

    async def subscribe(self, event_type: str, handler: EventHandler) -> SubscriptionId:
        """Subscribe to events of a specific type."""
        if not self._initialized:
            raise RuntimeError("Event bus not initialized")

        subscription_id = SubscriptionId(id=str(uuid4()))

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)
        self._subscriptions[subscription_id.id] = event_type

        logger.debug(
            "Subscribed to events", event_type=event_type, subscription_id=subscription_id.id
        )

        return subscription_id

    async def unsubscribe(self, subscription_id: SubscriptionId) -> bool:
        """Unsubscribe from events."""
        if subscription_id.id not in self._subscriptions:
            return False

        event_type = self._subscriptions[subscription_id.id]
        del self._subscriptions[subscription_id.id]

        # Remove handler - Note: this is simplified, in practice you'd track handler instances
        # For now, we'll just log the unsubscription
        logger.debug(
            "Unsubscribed from events", event_type=event_type, subscription_id=subscription_id.id
        )

        return True
