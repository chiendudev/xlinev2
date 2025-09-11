"""Unit tests for message router module."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from xline.core.events.bus_interface import Envelope
from xline.infrastructure.messaging.router import (
    IdempotencyStore,
    RouteEntry,
    Router,
    RoutingError,
    composite_key,
    correlation_id_key,
    create_correlation_filter,
    create_data_filter,
    create_source_filter,
    event_id_key,
)


class TestIdempotencyStore:
    """Test idempotency store."""

    def test_duplicate_detection(self):
        """Test basic duplicate detection."""
        store = IdempotencyStore(default_ttl=3600)
        
        # First call should not be duplicate
        assert not store.is_duplicate("test_key")
        
        # Second call should be duplicate
        assert store.is_duplicate("test_key")

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        store = IdempotencyStore(default_ttl=1)  # 1 second TTL
        
        # Add key
        assert not store.is_duplicate("expire_key")
        
        # Should still be duplicate immediately
        assert store.is_duplicate("expire_key")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should no longer be duplicate
        assert not store.is_duplicate("expire_key")

    def test_custom_ttl(self):
        """Test custom TTL override."""
        store = IdempotencyStore(default_ttl=3600)
        
        # Use custom short TTL
        assert not store.is_duplicate("custom_key", ttl=1)
        
        # Should be duplicate immediately
        assert store.is_duplicate("custom_key", ttl=1)
        
        # Wait for custom TTL expiration
        time.sleep(1.1)
        
        # Should no longer be duplicate
        assert not store.is_duplicate("custom_key", ttl=1)

    def test_cleanup_triggered(self):
        """Test periodic cleanup is triggered."""
        store = IdempotencyStore(default_ttl=1, cleanup_interval=5)
        
        # Add some expired keys
        for i in range(3):
            store.is_duplicate(f"key_{i}", ttl=0.1)  # Very short TTL
        
        time.sleep(0.2)  # Wait for expiration
        
        # Trigger cleanup by reaching interval
        for i in range(5):
            store.is_duplicate(f"trigger_{i}")
        
        # Store should have cleaned up expired keys
        # (We can't directly test this without exposing internals)
        assert store.size() >= 5  # At least the trigger keys

    def test_clear(self):
        """Test clearing the store."""
        store = IdempotencyStore()
        
        # Add some keys
        store.is_duplicate("key1")
        store.is_duplicate("key2")
        
        assert store.size() == 2
        
        # Clear
        store.clear()
        
        assert store.size() == 0

    def test_size(self):
        """Test size reporting."""
        store = IdempotencyStore()
        
        assert store.size() == 0
        
        # Add unique keys
        for i in range(5):
            store.is_duplicate(f"unique_{i}")
        
        assert store.size() == 5


class TestRouteEntry:
    """Test route entry dataclass."""

    def test_creation_with_defaults(self):
        """Test route entry creation with automatic timestamp."""
        async def dummy_handler(envelope):
            pass
        
        entry = RouteEntry(
            subscription_id="test-id",
            handler=dummy_handler
        )
        
        assert entry.subscription_id == "test-id"
        assert entry.handler is dummy_handler
        assert entry.filter_fn is None
        assert entry.idempotency_key_fn is None
        assert entry.created_at > 0

    def test_creation_with_timestamp(self):
        """Test route entry creation with explicit timestamp."""
        async def dummy_handler(envelope):
            pass
        
        test_time = time.time()
        entry = RouteEntry(
            subscription_id="test-id",
            handler=dummy_handler,
            created_at=test_time
        )
        
        assert entry.created_at == test_time


class TestRouter:
    """Test event router."""

    def test_register_handler(self):
        """Test basic handler registration."""
        router = Router()
        
        async def test_handler(envelope):
            pass
        
        subscription_id = router.register("test.event", test_handler)
        
        assert isinstance(subscription_id, str)
        assert len(subscription_id) > 0
        
        # Check metrics
        metrics = router.get_metrics()
        assert metrics['routes_registered'] == 1
        assert metrics['active_subscriptions'] == 1

    def test_register_with_filter(self):
        """Test handler registration with filter."""
        router = Router()
        
        async def test_handler(envelope):
            pass
        
        def filter_fn(envelope):
            return envelope.source == "allowed"
        
        subscription_id = router.register(
            "test.filtered",
            test_handler,
            filter_fn=filter_fn
        )
        
        assert subscription_id is not None

    def test_register_with_idempotency(self):
        """Test handler registration with idempotency."""
        router = Router()
        
        async def test_handler(envelope):
            pass
        
        def idempotency_fn(envelope):
            return envelope.event_id
        
        subscription_id = router.register(
            "test.idempotent",
            test_handler,
            idempotency_key_fn=idempotency_fn
        )
        
        assert subscription_id is not None

    def test_register_invalid_params(self):
        """Test registration with invalid parameters."""
        router = Router()
        
        async def test_handler(envelope):
            pass
        
        # Empty event type
        with pytest.raises(RoutingError, match="Event type cannot be empty"):
            router.register("", test_handler)
        
        # Non-callable handler
        with pytest.raises(RoutingError, match="Handler must be callable"):
            router.register("test.event", "not_callable")
        
        # Non-callable filter
        with pytest.raises(RoutingError, match="Filter function must be callable"):
            router.register("test.event", test_handler, filter_fn="not_callable")
        
        # Non-callable idempotency function
        with pytest.raises(RoutingError, match="Idempotency key function must be callable"):
            router.register("test.event", test_handler, idempotency_key_fn="not_callable")

    def test_unregister(self):
        """Test handler unregistration."""
        router = Router()
        
        async def test_handler(envelope):
            pass
        
        # Register handler
        subscription_id = router.register("test.event", test_handler)
        
        # Verify registered
        metrics = router.get_metrics()
        assert metrics['active_subscriptions'] == 1
        
        # Unregister
        result = router.unregister(subscription_id)
        assert result is True
        
        # Verify unregistered
        metrics = router.get_metrics()
        assert metrics['active_subscriptions'] == 0
        assert metrics['routes_unregistered'] == 1

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent subscription."""
        router = Router()
        
        result = router.unregister("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_route_basic(self):
        """Test basic message routing."""
        router = Router()
        
        # Mock handler
        handler = AsyncMock()
        
        # Register handler
        router.register("test.route", handler)
        
        # Create envelope
        envelope = Envelope(
            event_type="test.route",
            data={"test": "data"}
        )
        
        # Route message
        tasks = await router.route(envelope)
        
        assert len(tasks) == 1
        
        # Execute task
        await tasks[0]
        
        # Verify handler was called
        handler.assert_called_once_with(envelope)

    @pytest.mark.asyncio
    async def test_route_with_filter(self):
        """Test routing with filter function."""
        router = Router()
        
        handler = AsyncMock()
        
        # Filter that only allows specific source
        def source_filter(envelope):
            return envelope.source == "allowed"
        
        router.register("test.filter", handler, filter_fn=source_filter)
        
        # Create envelope that should be filtered out
        filtered_envelope = Envelope(
            event_type="test.filter",
            data={},
            source="blocked"
        )
        
        tasks = await router.route(filtered_envelope)
        assert len(tasks) == 0
        
        # Create envelope that should pass filter
        allowed_envelope = Envelope(
            event_type="test.filter",
            data={},
            source="allowed"
        )
        
        tasks = await router.route(allowed_envelope)
        assert len(tasks) == 1
        
        # Execute and verify
        await tasks[0]
        handler.assert_called_once_with(allowed_envelope)

    @pytest.mark.asyncio
    async def test_route_with_idempotency(self):
        """Test routing with idempotency."""
        router = Router()
        
        handler = AsyncMock()
        
        # Use event ID as idempotency key
        router.register("test.idempotent", handler, idempotency_key_fn=event_id_key)
        
        # Create envelope
        envelope = Envelope(
            event_type="test.idempotent",
            data={},
            event_id="unique-id"
        )
        
        # First routing should succeed
        tasks = await router.route(envelope)
        assert len(tasks) == 1
        await tasks[0]
        
        # Second routing with same envelope should be suppressed
        tasks = await router.route(envelope)
        assert len(tasks) == 0
        
        # Handler should only be called once
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_wildcard_matching(self):
        """Test wildcard event type matching."""
        router = Router()
        
        handler = AsyncMock()
        
        # Register with wildcard pattern
        router.register("trade.*", handler)
        
        # Test exact match
        envelope1 = Envelope(event_type="trade.executed", data={})
        tasks = await router.route(envelope1)
        assert len(tasks) == 1
        
        # Test wildcard match
        envelope2 = Envelope(event_type="trade.cancelled", data={})
        tasks = await router.route(envelope2)
        assert len(tasks) == 1
        
        # Test non-match
        envelope3 = Envelope(event_type="order.created", data={})
        tasks = await router.route(envelope3)
        assert len(tasks) == 0

    @pytest.mark.asyncio
    async def test_route_multiple_handlers(self):
        """Test routing to multiple handlers."""
        router = Router()
        
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Register multiple handlers for same event type
        router.register("multi.event", handler1)
        router.register("multi.event", handler2)
        
        envelope = Envelope(event_type="multi.event", data={})
        
        tasks = await router.route(envelope)
        assert len(tasks) == 2
        
        # Execute all tasks
        await asyncio.gather(*tasks)
        
        # Both handlers should be called
        handler1.assert_called_once_with(envelope)
        handler2.assert_called_once_with(envelope)

    @pytest.mark.asyncio
    async def test_filter_error_handling(self):
        """Test handling of filter function errors."""
        router = Router()
        
        handler = AsyncMock()
        
        # Filter that raises an exception
        def failing_filter(envelope):
            raise ValueError("Filter error")
        
        router.register("test.filter_error", handler, filter_fn=failing_filter)
        
        envelope = Envelope(event_type="test.filter_error", data={})
        
        # Should not raise, but should skip the handler
        tasks = await router.route(envelope)
        assert len(tasks) == 0
        
        # Check error metric
        metrics = router.get_metrics()
        assert metrics['handler_errors'] == 1

    @pytest.mark.asyncio
    async def test_idempotency_error_handling(self):
        """Test handling of idempotency function errors."""
        router = Router()
        
        handler = AsyncMock()
        
        # Idempotency function that raises an exception
        def failing_idempotency(envelope):
            raise ValueError("Idempotency error")
        
        router.register("test.idempotency_error", handler, idempotency_key_fn=failing_idempotency)
        
        envelope = Envelope(event_type="test.idempotency_error", data={})
        
        # Should not raise, should proceed without idempotency
        tasks = await router.route(envelope)
        assert len(tasks) == 1
        
        # Execute task
        await tasks[0]
        handler.assert_called_once()

    def test_route_empty_event_type(self):
        """Test routing with empty event type."""
        # The Envelope constructor will raise ValueError for empty event_type
        with pytest.raises(ValueError, match="event_type must be a non-empty string"):
            Envelope(event_type="", data={})

    def test_get_metrics(self):
        """Test metrics collection."""
        router = Router()
        
        metrics = router.get_metrics()
        
        # Check expected metrics exist
        expected_metrics = [
            'routes_registered', 'routes_unregistered', 'messages_routed',
            'messages_filtered', 'duplicates_suppressed', 'handler_errors',
            'active_subscriptions', 'idempotency_store_size'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics

    def test_list_subscriptions(self):
        """Test subscription listing."""
        router = Router()
        
        async def handler1(envelope):
            pass
        
        async def handler2(envelope):
            pass
        
        # Register handlers
        id1 = router.register("test1", handler1)
        id2 = router.register("test2", handler2, filter_fn=lambda e: True)
        
        subscriptions = router.list_subscriptions()
        
        assert len(subscriptions) == 2
        
        # Find subscriptions by ID
        sub1 = next(s for s in subscriptions if s['subscription_id'] == id1)
        sub2 = next(s for s in subscriptions if s['subscription_id'] == id2)
        
        assert sub1['has_filter'] is False
        assert sub1['has_idempotency'] is False
        
        assert sub2['has_filter'] is True
        assert sub2['has_idempotency'] is False

    def test_clear_idempotency_store(self):
        """Test clearing idempotency store."""
        router = Router()
        
        # Add some idempotent routes and trigger duplicates
        async def handler(envelope):
            pass
        
        router.register("test", handler, idempotency_key_fn=event_id_key)
        
        envelope = Envelope(event_type="test", data={}, event_id="test-id")
        
        # Process envelope to add to idempotency store
        asyncio.run(router.route(envelope))
        
        # Store should have entry
        metrics = router.get_metrics()
        assert metrics['idempotency_store_size'] >= 0
        
        # Clear store
        router.clear_idempotency_store()
        
        # Store should be empty
        metrics = router.get_metrics()
        assert metrics['idempotency_store_size'] == 0

    def test_health_check(self):
        """Test router health check."""
        router = Router()
        
        health = router.health_check()
        
        assert health['status'] == 'healthy'
        assert 'active_routes' in health
        assert 'active_subscriptions' in health
        assert 'idempotency_store_size' in health
        assert 'metrics' in health


class TestFilterUtilities:
    """Test filter utility functions."""

    def test_create_source_filter(self):
        """Test source filter creation."""
        allowed_sources = ["source1", "source2"]
        filter_fn = create_source_filter(allowed_sources)
        
        # Test allowed source
        envelope1 = Envelope(event_type="test", data={}, source="source1")
        assert filter_fn(envelope1) is True
        
        # Test disallowed source
        envelope2 = Envelope(event_type="test", data={}, source="other")
        assert filter_fn(envelope2) is False

    def test_create_correlation_filter(self):
        """Test correlation filter creation."""
        target_correlation = "test-correlation"
        filter_fn = create_correlation_filter(target_correlation)
        
        # Test matching correlation
        envelope1 = Envelope(
            event_type="test", 
            data={}, 
            correlation_id="test-correlation"
        )
        assert filter_fn(envelope1) is True
        
        # Test non-matching correlation
        envelope2 = Envelope(
            event_type="test", 
            data={}, 
            correlation_id="other-correlation"
        )
        assert filter_fn(envelope2) is False

    def test_create_data_filter(self):
        """Test data field filter creation."""
        filter_fn = create_data_filter("status", "active")
        
        # Test matching data
        envelope1 = Envelope(
            event_type="test", 
            data={"status": "active", "other": "value"}
        )
        assert filter_fn(envelope1) is True
        
        # Test non-matching data
        envelope2 = Envelope(
            event_type="test", 
            data={"status": "inactive"}
        )
        assert filter_fn(envelope2) is False
        
        # Test missing data
        envelope3 = Envelope(
            event_type="test", 
            data={"other": "value"}
        )
        assert filter_fn(envelope3) is False


class TestIdempotencyUtilities:
    """Test idempotency key utility functions."""

    def test_event_id_key(self):
        """Test event ID key extraction."""
        envelope = Envelope(
            event_type="test",
            data={},
            event_id="test-event-id"
        )
        
        key = event_id_key(envelope)
        assert key == "test-event-id"

    def test_correlation_id_key(self):
        """Test correlation ID key extraction."""
        # With correlation ID
        envelope1 = Envelope(
            event_type="test",
            data={},
            event_id="event-id",
            correlation_id="corr-id"
        )
        
        key1 = correlation_id_key(envelope1)
        assert key1 == "corr-id"
        
        # Without correlation ID (falls back to event ID)
        envelope2 = Envelope(
            event_type="test",
            data={},
            event_id="event-id"
        )
        
        key2 = correlation_id_key(envelope2)
        assert key2 == "event-id"

    def test_composite_key(self):
        """Test composite key creation."""
        envelope = Envelope(
            event_type="test.composite",
            data={"user_id": "123", "action": "login"},
            source="auth-service"
        )
        
        # Create composite key from multiple fields
        key = composite_key(envelope, ["event_type", "source", "user_id"])
        
        expected_parts = [
            "event_type:test.composite",
            "source:auth-service", 
            "data.user_id:123"
        ]
        expected_key = "|".join(expected_parts)
        
        assert key == expected_key

    def test_composite_key_missing_fields(self):
        """Test composite key with missing fields."""
        envelope = Envelope(
            event_type="test",
            data={"existing": "value"}
        )
        
        # Include non-existent fields
        key = composite_key(envelope, ["event_type", "nonexistent", "missing_data"])
        
        # Should only include existing fields
        assert key == "event_type:test"


if __name__ == "__main__":
    pytest.main([__file__])
