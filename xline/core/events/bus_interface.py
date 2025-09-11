"""Event Bus Protocol Interface and Data Structures.

This module defines the core abstractions for event-driven messaging in Xline.
Protocol: EventBusInterface for publish/subscribe operations
Dataclass: Envelope for message encapsulation
Dataclass: PublishResult for publish operation responses
"""

from abc import abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Protocol
import uuid


@dataclass(frozen=True)
class Envelope:
    """Message envelope containing event data and metadata.
    
    Attributes:
        event_type: Unique identifier for the event type (e.g., 'trade.executed')
        data: The actual event payload (JSON-serializable)
        event_id: Unique identifier for this specific event instance
        timestamp: UTC timestamp when event was created
        correlation_id: Optional correlation ID for request tracing
        source: Source system/component that generated the event
        headers: Additional metadata key-value pairs
        retry_count: Number of times this message has been retried
    """
    event_type: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    source: str = "xline"
    headers: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0

    def __post_init__(self) -> None:
        """Validate envelope data after initialization."""
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(self.data, dict):
            raise ValueError("data must be a dictionary")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")


@dataclass(frozen=True)
class PublishResult:
    """Result of a publish operation.
    
    Attributes:
        success: Whether the publish operation succeeded
        message_id: Unique identifier assigned by the message bus
        event_id: Original event ID from the envelope
        error: Error message if publish failed
        timestamp: UTC timestamp when publish completed
    """
    success: bool
    message_id: str | None = None
    event_id: str | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate publish result data."""
        if self.success and not self.message_id:
            raise ValueError("message_id is required for successful publish operations")
        if not self.success and not self.error:
            raise ValueError("error message is required for failed publish operations")


class EventBusInterface(Protocol):
    """Protocol interface for event bus implementations.
    
    Defines the contract that all event bus implementations must follow.
    Supports publish/subscribe patterns with graceful error handling.
    """

    @abstractmethod
    async def publish(self, envelope: Envelope) -> PublishResult:
        """Publish an event to the bus.
        
        Args:
            envelope: The event envelope to publish
            
        Returns:
            PublishResult indicating success/failure and metadata
            
        Raises:
            EventBusError: If publish operation fails
        """
        ...

    @abstractmethod
    async def subscribe(
        self, 
        event_types: list[str], 
        consumer_group: str,
        consumer_name: str
    ) -> AsyncIterator[Envelope]:
        """Subscribe to events of specified types.
        
        Args:
            event_types: List of event type patterns to subscribe to
            consumer_group: Consumer group name for load balancing
            consumer_name: Unique name for this consumer instance
            
        Yields:
            Envelope: Received event envelopes
            
        Raises:
            EventBusError: If subscription fails
        """
        ...

    @abstractmethod
    async def unsubscribe(self, consumer_group: str, consumer_name: str) -> None:
        """Unsubscribe from all events for the given consumer.
        
        Args:
            consumer_group: Consumer group to unsubscribe from
            consumer_name: Consumer instance to unsubscribe
            
        Raises:
            EventBusError: If unsubscribe operation fails
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check the health status of the event bus.
        
        Returns:
            Dictionary containing health status information:
            - status: 'healthy' | 'unhealthy' | 'degraded'
            - timestamp: UTC timestamp of the check
            - details: Additional health information
            
        Raises:
            EventBusError: If health check fails
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the event bus connection gracefully.
        
        Should clean up all resources, close connections, and ensure
        all pending operations complete.
        
        Raises:
            EventBusError: If close operation fails
        """
        ...


class EventBusError(Exception):
    """Base exception for event bus operations."""
    
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class PublishError(EventBusError):
    """Exception raised when publish operation fails."""
    pass


class SubscribeError(EventBusError):
    """Exception raised when subscribe operation fails."""
    pass


class EventBusConnectionError(EventBusError):
    """Exception raised when event bus connection fails."""
    pass
