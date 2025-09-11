"""Message routing engine with topic mapping, filtering, and idempotency.

This module provides sophisticated message routing capabilities:
- Event type to handler mapping with subscription IDs
- Predicate-based filtering
- Idempotency detection and suppression
- Correlation ID tracking
- Performance metrics integration
"""

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from xline.core.events.bus_interface import Envelope, EventBusError


class RoutingError(EventBusError):
    """Exception raised when routing operations fail."""
    pass


@dataclass(frozen=True)
class RouteEntry:
    """Represents a single routing entry with handler and metadata.
    
    Attributes:
        subscription_id: Unique identifier for this subscription
        handler: Async callable that processes the envelope
        filter_fn: Optional predicate function for envelope filtering
        idempotency_key_fn: Optional function to extract idempotency key
        created_at: UTC timestamp when this route was registered
    """
    subscription_id: str
    handler: Callable[[Envelope], Awaitable[None]]
    filter_fn: Callable[[Envelope], bool] | None = None
    idempotency_key_fn: Callable[[Envelope], str] | None = None
    created_at: float = 0.0

    def __post_init__(self) -> None:
        """Set creation timestamp if not provided."""
        if self.created_at == 0.0:
            object.__setattr__(self, 'created_at', time.time())


class IdempotencyStore:
    """In-memory store for idempotency key tracking with TTL cleanup."""

    def __init__(self, default_ttl: int = 3600, cleanup_interval: int = 1000) -> None:
        """Initialize idempotency store.
        
        Args:
            default_ttl: Default time-to-live for keys in seconds
            cleanup_interval: Number of operations between cleanup runs
        """
        self._store: dict[str, float] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._operation_count = 0

    def is_duplicate(self, key: str, ttl: int | None = None) -> bool:
        """Check if a key has been seen before within TTL.
        
        Args:
            key: Idempotency key to check
            ttl: Custom TTL in seconds (uses default if None)
            
        Returns:
            True if key is a duplicate, False if new
        """
        self._operation_count += 1
        current_time = time.time()
        
        # Cleanup expired entries periodically
        if self._operation_count % self._cleanup_interval == 0:
            self._cleanup_expired(current_time)
        
        # Check if key exists and is not expired
        if key in self._store:
            if current_time <= self._store[key]:
                return True
            else:
                # Key expired, remove it
                del self._store[key]
        
        # Store key with expiration time
        effective_ttl = ttl or self._default_ttl
        self._store[key] = current_time + effective_ttl
        return False

    def _cleanup_expired(self, current_time: float) -> None:
        """Remove expired keys from store."""
        expired_keys = [
            key for key, expires_at in self._store.items()
            if current_time > expires_at
        ]
        for key in expired_keys:
            del self._store[key]

    def clear(self) -> None:
        """Clear all stored keys."""
        self._store.clear()
        self._operation_count = 0

    def size(self) -> int:
        """Return number of stored keys."""
        return len(self._store)


class Router:
    """Event router with filtering and idempotency support."""

    def __init__(self, idempotency_ttl: int = 3600) -> None:
        """Initialize router.
        
        Args:
            idempotency_ttl: Default TTL for idempotency keys in seconds
        """
        self._routes: dict[str, list[RouteEntry]] = defaultdict(list)
        self._subscriptions: dict[str, RouteEntry] = {}
        self._idempotency_store = IdempotencyStore(default_ttl=idempotency_ttl)
        self._metrics: dict[str, Any] = {
            'routes_registered': 0,
            'routes_unregistered': 0,
            'messages_routed': 0,
            'messages_filtered': 0,
            'duplicates_suppressed': 0,
            'handler_errors': 0,
        }

    def register(
        self,
        event_type: str,
        handler: Callable[[Envelope], Awaitable[None]],
        filter_fn: Callable[[Envelope], bool] | None = None,
        idempotency_key_fn: Callable[[Envelope], str] | None = None,
    ) -> str:
        """Register a handler for an event type.
        
        Args:
            event_type: Event type pattern to subscribe to
            handler: Async function to handle matching envelopes
            filter_fn: Optional predicate for additional filtering
            idempotency_key_fn: Optional function to extract idempotency key
            
        Returns:
            Unique subscription ID
            
        Raises:
            RoutingError: If registration parameters are invalid
        """
        if not event_type:
            raise RoutingError("Event type cannot be empty")
        
        if not callable(handler):
            raise RoutingError("Handler must be callable")
        
        if filter_fn is not None and not callable(filter_fn):
            raise RoutingError("Filter function must be callable")
        
        if idempotency_key_fn is not None and not callable(idempotency_key_fn):
            raise RoutingError("Idempotency key function must be callable")
        
        subscription_id = str(uuid.uuid4())
        route_entry = RouteEntry(
            subscription_id=subscription_id,
            handler=handler,
            filter_fn=filter_fn,
            idempotency_key_fn=idempotency_key_fn,
        )
        
        self._routes[event_type].append(route_entry)
        self._subscriptions[subscription_id] = route_entry
        self._metrics['routes_registered'] += 1
        
        return subscription_id

    def unregister(self, subscription_id: str) -> bool:
        """Unregister a subscription by ID.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was found and removed, False otherwise
        """
        if subscription_id not in self._subscriptions:
            return False
        
        # Find and remove from routes
        for event_type, routes in self._routes.items():
            routes[:] = [r for r in routes if r.subscription_id != subscription_id]
            # Clean up empty route lists
            if not routes:
                del self._routes[event_type]
                break
        
        del self._subscriptions[subscription_id]
        self._metrics['routes_unregistered'] += 1
        
        return True

    async def route(self, envelope: Envelope) -> list[Awaitable[None]]:
        """Route an envelope to matching handlers.
        
        Args:
            envelope: Envelope to route
            
        Returns:
            List of awaitable handler calls (not yet executed)
            
        Raises:
            RoutingError: If routing fails
        """
        if not envelope.event_type:
            raise RoutingError("Envelope event_type cannot be empty")
        
        self._metrics['messages_routed'] += 1
        
        # Find matching routes
        matching_routes = []
        for event_type, routes in self._routes.items():
            if self._matches_event_type(envelope.event_type, event_type):
                matching_routes.extend(routes)
        
        # Apply filters and collect handler tasks
        handler_tasks: list[Awaitable[None]] = []
        for route in matching_routes:
            # Apply filter if present
            if route.filter_fn is not None:
                try:
                    if not route.filter_fn(envelope):
                        self._metrics['messages_filtered'] += 1
                        continue
                except Exception:
                    # Filter function failed, skip this route
                    self._metrics['handler_errors'] += 1
                    continue
            
            # Check for idempotency
            if route.idempotency_key_fn is not None:
                try:
                    idempotency_key = route.idempotency_key_fn(envelope)
                    if self._idempotency_store.is_duplicate(idempotency_key):
                        self._metrics['duplicates_suppressed'] += 1
                        continue
                except Exception:
                    # Idempotency key extraction failed, proceed without idempotency
                    # Could add structured logging here in production
                    pass
            
            # Create handler task
            handler_tasks.append(self._create_handler_task(route.handler, envelope))
        
        return handler_tasks

    def _matches_event_type(self, envelope_type: str, pattern: str) -> bool:
        """Check if envelope event type matches a routing pattern.
        
        Args:
            envelope_type: Actual event type from envelope
            pattern: Pattern from route registration
            
        Returns:
            True if types match
        """
        # For now, simple exact match and basic wildcard support
        if pattern == envelope_type:
            return True
        
        # Basic wildcard support: pattern.* matches pattern.anything
        if pattern.endswith('.*'):
            prefix = pattern[:-2]
            return envelope_type.startswith(prefix + '.')
        
        return False

    async def _create_handler_task(
        self, handler: Callable[[Envelope], Awaitable[None]], envelope: Envelope
    ) -> None:
        """Create and wrap a handler task with error handling.
        
        Args:
            handler: Handler function to call
            envelope: Envelope to pass to handler
        """
        try:
            await handler(envelope)
        except Exception as e:
            self._metrics['handler_errors'] += 1
            # In production, this should use structured logging
            # For now, just increment error counter
            raise RoutingError(f"Handler failed: {e}") from e

    def get_metrics(self) -> dict[str, Any]:
        """Get routing metrics.
        
        Returns:
            Dictionary of metric name to value mappings
        """
        metrics = self._metrics.copy()
        metrics['active_subscriptions'] = len(self._subscriptions)
        metrics['idempotency_store_size'] = self._idempotency_store.size()
        return metrics

    def list_subscriptions(self) -> list[dict[str, Any]]:
        """List all active subscriptions.
        
        Returns:
            List of subscription information dictionaries
        """
        subscriptions = []
        for subscription_id, route in self._subscriptions.items():
            subscription_info = {
                'subscription_id': subscription_id,
                'created_at': route.created_at,
                'has_filter': route.filter_fn is not None,
                'has_idempotency': route.idempotency_key_fn is not None,
            }
            subscriptions.append(subscription_info)
        
        return subscriptions

    def clear_idempotency_store(self) -> None:
        """Clear the idempotency store."""
        self._idempotency_store.clear()

    def health_check(self) -> dict[str, Any]:
        """Perform health check on router.
        
        Returns:
            Health status information
        """
        return {
            'status': 'healthy',
            'active_routes': len(self._routes),
            'active_subscriptions': len(self._subscriptions),
            'idempotency_store_size': self._idempotency_store.size(),
            'metrics': self.get_metrics(),
        }


# Utility functions for common filter patterns

def create_source_filter(allowed_sources: list[str]) -> Callable[[Envelope], bool]:
    """Create a filter that only allows envelopes from specific sources.
    
    Args:
        allowed_sources: List of allowed source identifiers
        
    Returns:
        Filter function
    """
    allowed_set = set(allowed_sources)
    
    def filter_fn(envelope: Envelope) -> bool:
        return envelope.source in allowed_set
    
    return filter_fn


def create_correlation_filter(correlation_id: str) -> Callable[[Envelope], bool]:
    """Create a filter for a specific correlation ID.
    
    Args:
        correlation_id: Correlation ID to match
        
    Returns:
        Filter function
    """
    def filter_fn(envelope: Envelope) -> bool:
        return envelope.correlation_id == correlation_id
    
    return filter_fn


def create_data_filter(key: str, value: Any) -> Callable[[Envelope], bool]:
    """Create a filter that checks for a specific data field value.
    
    Args:
        key: Key to check in envelope.data
        value: Value that must match
        
    Returns:
        Filter function
    """
    def filter_fn(envelope: Envelope) -> bool:
        return bool(envelope.data.get(key) == value)
    
    return filter_fn


# Utility functions for common idempotency key patterns

def event_id_key(envelope: Envelope) -> str:
    """Extract event ID as idempotency key."""
    return envelope.event_id


def correlation_id_key(envelope: Envelope) -> str:
    """Extract correlation ID as idempotency key."""
    return envelope.correlation_id or envelope.event_id


def composite_key(envelope: Envelope, fields: list[str]) -> str:
    """Create composite idempotency key from multiple envelope fields.
    
    Args:
        envelope: Envelope to extract key from
        fields: List of field names to include in key
        
    Returns:
        Composite key string
    """
    key_parts = []
    
    for field in fields:
        if hasattr(envelope, field):
            value = getattr(envelope, field)
            key_parts.append(f"{field}:{value}")
        elif field in envelope.data:
            value = envelope.data[field]
            key_parts.append(f"data.{field}:{value}")
    
    return "|".join(key_parts)
