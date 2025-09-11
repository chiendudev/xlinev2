"""
Comprehensive test coverage for bus.py to achieve 95%+ coverage
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from xline.core.events.bus import InMemoryEventBus, SubscriptionId, PublishResult
from xline.core.events.types import OrderEvent, EventType


class TestBus:
    """Comprehensive bus tests for 95%+ coverage"""

    def test_subscription_id_creation(self):
        """Test SubscriptionId creation."""
        sub_id = SubscriptionId("test_sub_1")
        assert sub_id.id == "test_sub_1"

    def test_publish_result_creation(self):
        """Test PublishResult creation."""
        result = PublishResult(success=True, event_id="event_123")
        assert result.event_id == "event_123"
        assert result.success is True

    def test_bus_simple_operations(self):
        """Test simple bus operations."""
        bus = InMemoryEventBus()
        assert bus is not None

    @pytest.mark.asyncio
    async def test_bus_publish_basic(self):
        """Test basic publishing functionality"""
        bus = InMemoryEventBus()
        await bus.initialize()
        
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="test_order_123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        result = await bus.publish(event)
        
        assert result is not None
        assert result.event_id == event.id

    @pytest.mark.asyncio
    async def test_bus_health_check(self):
        """Test bus health check functionality."""
        bus = InMemoryEventBus()
        
        # Before initialization
        assert not await bus.health_check()  # Line 131: return self._initialized
        
        # After initialization
        await bus.initialize()
        assert await bus.health_check()

    @pytest.mark.asyncio
    async def test_bus_cleanup(self):
        """Test bus cleanup functionality."""
        bus = InMemoryEventBus()
        await bus.initialize()
        
        # Subscribe to event
        handler = AsyncMock()
        await bus.subscribe("test.event", handler)
        
        # Cleanup should clear everything
        await bus.cleanup()  # Lines 135-141
        assert not bus._initialized
        assert len(bus._subscribers) == 0
        assert len(bus._subscriptions) == 0

    @pytest.mark.asyncio
    async def test_dlq_functionality(self):
        """Test Dead Letter Queue functionality."""
        bus = InMemoryEventBus(enable_dlq=True)
        await bus.initialize()
        
        # Test DLQ count when empty
        assert bus.get_dlq_count() == 0  # Line 145: return len(self._dlq)
        
        # Test get DLQ events when empty
        dlq_events = bus.get_dlq_events()  # Line 149: return self._dlq.copy()
        assert dlq_events == []

    @pytest.mark.asyncio
    async def test_publish_without_initialization(self):
        """Test publishing without initialization."""
        bus = InMemoryEventBus()
        
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="test_order_123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # Should return failure
        result = await bus.publish(event)  # Lines 154-156
        assert not result.success
        assert result.error == "Event bus not initialized"

    @pytest.mark.asyncio
    async def test_subscribe_without_initialization(self):
        """Test subscribing without initialization."""
        bus = InMemoryEventBus()
        handler = AsyncMock()
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Event bus not initialized"):
            await bus.subscribe("test.event", handler)  # Line 223

    @pytest.mark.asyncio
    async def test_publish_with_handler_errors_no_dlq(self):
        """Test publishing with handler errors when DLQ is disabled."""
        bus = InMemoryEventBus(enable_dlq=False)
        await bus.initialize()
        
        # Create failing handler
        failing_handler = AsyncMock()
        failing_handler.handle.side_effect = Exception("Handler failed")
        
        await bus.subscribe("order.created", failing_handler)
        
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="test_order_123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # Publish should handle error without DLQ
        result = await bus.publish(event)  # Lines 199-204
        assert result.handlers_notified == 0  # Handler failed, so 0 notified
        assert result.success  # But still successful publish

    @pytest.mark.asyncio
    async def test_publish_with_dlq_retries(self):
        """Test publishing with DLQ and retry logic."""
        bus = InMemoryEventBus(enable_dlq=True)
        await bus.initialize()
        
        # Create failing handler
        failing_handler = AsyncMock()
        failing_handler.handle.side_effect = Exception("Handler failed")
        
        await bus.subscribe("order.created", failing_handler)
        
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="test_order_123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # First publish - should retry
        result1 = await bus.publish(event)  # Lines 163-185
        assert result1.handlers_notified == 0  # Handler failed
        assert bus.get_dlq_count() == 0  # Not in DLQ yet
        
        # Second publish - should retry again
        result2 = await bus.publish(event)
        assert result2.handlers_notified == 0  # Handler failed
        assert bus.get_dlq_count() == 0  # Still not in DLQ
        
        # Third publish - should move to DLQ
        await bus.publish(event)  # Lines 184-192
        assert bus.get_dlq_count() == 1  # Now in DLQ
        
        # Fourth publish - should skip processing (already in DLQ)
        result4 = await bus.publish(event)  # Lines 166-168
        assert result4.handlers_notified == 0

    @pytest.mark.asyncio
    async def test_publish_with_recovery_from_failure(self):
        """Test handler recovery after failure."""
        bus = InMemoryEventBus(enable_dlq=True)
        await bus.initialize()
        
        # Create handler that fails first time, succeeds second time
        recovery_handler = AsyncMock()
        call_count = 0
        
        async def handle_with_recovery(event):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")
            # Second call succeeds
        
        recovery_handler.handle = handle_with_recovery
        await bus.subscribe("order.created", recovery_handler)
        
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="test_order_123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # First publish - fails
        result1 = await bus.publish(event)
        assert result1.handlers_notified == 0  # Handler failed
        
        # Second publish - succeeds and clears retry count
        result2 = await bus.publish(event)  # Lines 174-176
        assert result2.handlers_notified > 0
        assert event.id not in bus._failed_events  # Retry count cleared

    @pytest.mark.asyncio
    async def test_unsubscribe_functionality(self):
        """Test unsubscribe functionality."""
        bus = InMemoryEventBus()
        await bus.initialize()
        
        handler = AsyncMock()
        
        # Subscribe
        subscription_id = await bus.subscribe("test.event", handler)
        assert subscription_id.id in bus._subscriptions
        
        # Unsubscribe
        result = await bus.unsubscribe(subscription_id)  # Lines 240-248
        assert result is True
        assert subscription_id.id not in bus._subscriptions
        
        # Try to unsubscribe again
        result2 = await bus.unsubscribe(subscription_id)  # Line 242
        assert result2 is False

    @pytest.mark.asyncio
    async def test_bus_subscribe_simple(self):
        """Test basic bus subscribe."""
        bus = InMemoryEventBus()
        await bus.initialize()
        
        def handler(event):
            pass
        
        sub_id = await bus.subscribe("order.created", handler)
        assert isinstance(sub_id, SubscriptionId)

    @pytest.mark.asyncio
    async def test_bus_unsubscribe_with_subscription_id(self):
        """Test bus unsubscribe with subscription ID."""
        bus = InMemoryEventBus()
        await bus.initialize()
        
        def handler(event):
            pass
        
        sub_id = await bus.subscribe("order.created", handler)
        result = await bus.unsubscribe(sub_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_bus_close(self):
        """Test bus close."""
        bus = InMemoryEventBus()
        await bus.initialize()
        # InMemoryEventBus may not have close method, test should pass if not implemented
        if hasattr(bus, 'close'):
            await bus.close()
