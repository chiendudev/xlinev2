# File: xline/core/events/bus.py
from typing import Dict, Any, Optional, Protocol, Callable, Awaitable
from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Type definitions
EventHandlerFunc = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    """Base event class for all system events."""

    id: str
    type: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = str(uuid4())


@dataclass
class PublishResult:
    """Result of event publishing operation."""

    success: bool
    event_id: str
    error: Optional[str] = None
    message_id: Optional[str] = None
    handlers_notified: int = 0


@dataclass
class SubscriptionId:
    """Unique identifier for event subscription."""

    id: str


class EventBusInterface(Protocol):
    """Protocol defining event bus interface that ALL implementations must follow."""

    async def initialize(self) -> bool:
        """Initialize the event bus.

        Returns:
            True if initialization successful, False otherwise
        """
        ...

    async def health_check(self) -> bool:
        """Check if event bus is healthy.

        Returns:
            True if healthy, False otherwise
        """
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

    async def subscribe(self, event_type: str, handler: EventHandlerFunc) -> SubscriptionId:
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


class EventBusError(Exception):
    """Base exception for event bus operations."""

    pass


class EventPublishError(EventBusError):
    """Exception raised when event publishing fails."""

    pass


class EventSubscriptionError(EventBusError):
    """Exception raised when event subscription fails."""

    pass


class CircuitBreakerError(EventBusError):
    """Exception raised when circuit breaker is open."""

    pass
