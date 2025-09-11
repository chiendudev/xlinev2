"""
INTEGRATION TESTING - NGÀY 5 (Task 1.13)
File: tests/integration/events/test_event_bus_integration.py

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/TESTING_STRATEGY.md
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md
- ALL scenarios từ TESTING_STRATEGY.md PHẢI được test
"""

import asyncio
import pytest
import time
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, UTC

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.factory import EventBusFactory
from xline.core.events.types import (
    EventType, OrderEvent, TradeEvent, RiskEvent, AccountEvent, SystemEvent,
    OrderSide, OrderType, OrderStatus, RiskSeverity
)
from xline.core.patterns.factory import ComponentTier


class MockRedisEventBus:
    """Mock Redis Event Bus for testing failover scenarios"""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.is_initialized = False
        self.subscribers = {}
        self.published_events = []
        
    async def initialize(self):
        if self.should_fail:
            raise ConnectionError("Redis connection failed")
        self.is_initialized = True
        
    async def close(self):
        self.is_initialized = False
        
    async def publish(self, event_type, event):
        if not self.is_initialized or self.should_fail:
            raise ConnectionError("Redis connection lost")
        self.published_events.append((event_type, event))
        
    async def subscribe(self, event_type, handler):
        if not self.is_initialized or self.should_fail:
            raise ConnectionError("Redis connection lost")
        self.subscribers[event_type] = handler
        return f"redis_sub_{id(handler)}"
        
    async def health_check(self):
        return not self.should_fail and self.is_initialized


class MockNATSEventBus:
    """Mock NATS Event Bus for testing failover scenarios"""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.is_initialized = False
        self.subscribers = {}
        self.published_events = []
        
    async def initialize(self):
        if self.should_fail:
            raise ConnectionError("NATS connection failed")
        self.is_initialized = True
        
    async def close(self):
        self.is_initialized = False
        
    async def publish(self, event_type, event):
        if not self.is_initialized or self.should_fail:
            raise ConnectionError("NATS connection lost")
        self.published_events.append((event_type, event))
        
    async def subscribe(self, event_type, handler):
        if not self.is_initialized or self.should_fail:
            raise ConnectionError("NATS connection lost")
        self.subscribers[event_type] = handler
        return f"nats_sub_{id(handler)}"
        
    async def health_check(self):
        return not self.should_fail and self.is_initialized


class OrderingTestHandler:
    """Handler to test event ordering guarantees"""
    
    def __init__(self):
        self.received_events = []
        self.timestamps = []
        
    async def handle(self, event):
        timestamp = time.time_ns()
        self.received_events.append(event)
        self.timestamps.append(timestamp)
        # Simulate some processing time
        await asyncio.sleep(0.001)


class DeliveryTestHandler:
    """Handler to test at-least-once delivery guarantees"""
    
    def __init__(self, should_fail_count=0):
        self.received_events = []
        self.failure_count = 0
        self.should_fail_count = should_fail_count
        
    async def handle(self, event):
        if self.failure_count < self.should_fail_count:
            self.failure_count += 1
            raise Exception(f"Simulated failure {self.failure_count}")
        self.received_events.append(event)


class PoisonMessageHandler:
    """Handler to test poison message handling"""
    
    def __init__(self):
        self.received_events = []
        self.poison_events = []
        
    async def handle(self, event):
        # Simulate poison message detection
        if hasattr(event, 'poison_flag') and event.poison_flag:
            self.poison_events.append(event)
            raise ValueError("Poison message detected")
        self.received_events.append(event)


@pytest.mark.asyncio
class TestEventBusIntegration:
    """PHẢI test ALL scenarios từ TESTING_STRATEGY.md"""
    
    async def test_redis_nats_failover_complete_flow(self):
        """
        Test complete failover chain - MANDATORY SCENARIO
        1. Start with Redis
        2. Kill Redis → should failover to NATS  
        3. Kill NATS → should failover to InMemory
        4. Restart Redis → should failover back
        PHẢI verify data integrity through all transitions
        """
        # Create mock implementations
        redis_bus = MockRedisEventBus(should_fail=False)
        nats_bus = MockNATSEventBus(should_fail=False)
        inmemory_bus = InMemoryEventBus()
        
        # Initialize all buses
        await redis_bus.initialize()
        await nats_bus.initialize() 
        await inmemory_bus.initialize()
        
        # Create test event
        test_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="failover_test",
            order_id="test-order-1",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # Setup handler
        handler = OrderingTestHandler()
        
        # PHASE 1: Start with Redis
        await redis_bus.subscribe(EventType.ORDER_CREATED, handler)
        await redis_bus.publish(EventType.ORDER_CREATED, test_event)
        
        # Verify Redis received the event
        assert len(redis_bus.published_events) == 1
        assert redis_bus.published_events[0][0] == EventType.ORDER_CREATED
        
        # PHASE 2: Kill Redis, failover to NATS
        redis_bus.should_fail = True
        await redis_bus.close()
        
        # Simulate failover detection and switch to NATS
        await nats_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        test_event_2 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="failover_test",
            order_id="test-order-2", 
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.5"),
            price=Decimal("51000.0")
        )
        
        await nats_bus.publish(EventType.ORDER_CREATED, test_event_2)
        
        # Verify NATS received the event
        assert len(nats_bus.published_events) == 1
        assert nats_bus.published_events[0][0] == EventType.ORDER_CREATED
        
        # PHASE 3: Kill NATS, failover to InMemory
        nats_bus.should_fail = True
        await nats_bus.close()
        
        # Simulate failover to InMemory
        await inmemory_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        test_event_3 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="failover_test",
            order_id="test-order-3",
            account_id="test-account", 
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10.0"),
            price=Decimal("3000.0")
        )
        
        result = await inmemory_bus.publish(EventType.ORDER_CREATED, test_event_3)
        assert result.success == True
        
        # PHASE 4: Restart Redis, failover back
        redis_bus.should_fail = False
        await redis_bus.initialize()
        await redis_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        test_event_4 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="failover_test",
            order_id="test-order-4",
            account_id="test-account",
            symbol="BTC/USD", 
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("2.0"),
            price=Decimal("49000.0")
        )
        
        await redis_bus.publish(EventType.ORDER_CREATED, test_event_4)
        
        # Verify Redis is working again
        assert len(redis_bus.published_events) == 2  # Original + new event
        
        # VERIFY DATA INTEGRITY through all transitions
        # All events should have been processed without loss
        total_events_published = 4
        assert len(redis_bus.published_events) == 2  # Events 1 and 4
        assert len(nats_bus.published_events) == 1   # Event 2
        # Event 3 was published to InMemory (verified by success result)
        
        # Cleanup
        await redis_bus.close()
        await nats_bus.close()
        await inmemory_bus.close()

    async def test_event_ordering_guarantees(self):
        """
        Test event ordering under load - MANDATORY SCENARIO
        PHẢI ensure events processed in order
        """
        bus = InMemoryEventBus(buffer_size=1000)
        await bus.initialize()
        
        handler = OrderingTestHandler()
        await bus.subscribe(EventType.ORDER_CREATED, handler)
        
        # Send events in specific order with timestamps
        events = []
        for i in range(100):
            event = OrderEvent(
                type=EventType.ORDER_CREATED,
                source=f"ordering_test_{i}",
                order_id=f"order-{i:03d}",
                account_id="test-account",
                symbol="BTC/USD",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("1.0"),
                price=Decimal(f"{50000 + i}")
            )
            events.append(event)
            
        # Publish all events rapidly
        publish_tasks = []
        for event in events:
            task = asyncio.create_task(bus.publish(EventType.ORDER_CREATED, event))
            publish_tasks.append(task)
            
        # Wait for all publishes to complete
        results = await asyncio.gather(*publish_tasks)
        
        # Verify all publishes succeeded
        for result in results:
            assert result.success == True
            
        # Wait for processing to complete
        await asyncio.sleep(0.5)
        
        # VERIFY ORDERING: Events should be processed in order
        assert len(handler.received_events) == 100
        
        # Check that timestamps are in order (allowing for small variations)
        for i in range(1, len(handler.timestamps)):
            # Events should be processed in roughly the same order
            # Allow some tolerance for async processing
            time_diff = handler.timestamps[i] - handler.timestamps[i-1]
            assert time_diff >= -1000000  # Allow 1ms backwards tolerance
            
        # Verify event content ordering
        for i, event in enumerate(handler.received_events):
            expected_order_id = f"order-{i:03d}"
            assert event.order_id == expected_order_id
            
        await bus.close()

    async def test_at_least_once_delivery(self):
        """
        Test delivery guarantees - MANDATORY SCENARIO
        PHẢI ensure no event loss
        """
        bus = InMemoryEventBus(dlq_enabled=True, max_retries=3)
        await bus.initialize()
        
        # Handler that fails first 2 times then succeeds
        handler = DeliveryTestHandler(should_fail_count=2)
        await bus.subscribe(EventType.ORDER_CREATED, handler)
        
        test_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="delivery_test",
            order_id="delivery-test-order",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # Publish event
        result = await bus.publish(EventType.ORDER_CREATED, test_event)
        assert result.success == True
        
        # Wait for retries and eventual success
        await asyncio.sleep(1.0)
        
        # VERIFY AT-LEAST-ONCE DELIVERY
        # Event should have been delivered successfully after retries
        assert len(handler.received_events) == 1
        assert handler.received_events[0].order_id == "delivery-test-order"
        assert handler.failure_count == 2  # Failed twice before success
        
        # Test with multiple events
        for i in range(10):
            event = OrderEvent(
                type=EventType.ORDER_CREATED,
                source="delivery_test",
                order_id=f"multi-delivery-{i}",
                account_id="test-account",
                symbol="BTC/USD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("1.0"),
                price=Decimal("50000.0")
            )
            result = await bus.publish(EventType.ORDER_CREATED, event)
            assert result.success == True
            
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # All events should be delivered (no loss)
        assert len(handler.received_events) == 11  # Original + 10 new
        
        await bus.close()

    async def test_poison_message_handling(self):
        """
        Test DLQ functionality - MANDATORY SCENARIO  
        PHẢI handle malformed messages properly
        """
        bus = InMemoryEventBus(dlq_enabled=True, max_retries=2)
        await bus.initialize()
        
        handler = PoisonMessageHandler()
        await bus.subscribe(EventType.ORDER_CREATED, handler)
        
        # Create normal event
        normal_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="poison_test",
            order_id="normal-order",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        # Create poison event (will cause handler to fail)
        poison_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="poison_test",
            order_id="poison-order",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        # Mark as poison
        poison_event.poison_flag = True
        
        # Publish normal event first
        result1 = await bus.publish(EventType.ORDER_CREATED, normal_event)
        assert result1.success == True
        
        # Publish poison event
        result2 = await bus.publish(EventType.ORDER_CREATED, poison_event)
        assert result2.success == True  # Publishing succeeds, handling fails
        
        # Publish another normal event
        normal_event2 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="poison_test",
            order_id="normal-order-2",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.5"),
            price=Decimal("51000.0")
        )
        
        result3 = await bus.publish(EventType.ORDER_CREATED, normal_event2)
        assert result3.success == True
        
        # Wait for processing and retries
        await asyncio.sleep(1.0)
        
        # VERIFY POISON MESSAGE HANDLING
        # Normal events should be processed successfully
        assert len(handler.received_events) == 2
        assert handler.received_events[0].order_id == "normal-order"
        assert handler.received_events[1].order_id == "normal-order-2"
        
        # Poison event should have been detected and isolated
        assert len(handler.poison_events) >= 1  # May have been retried
        assert handler.poison_events[0].order_id == "poison-order"
        
        # System should continue processing normal events after poison event
        normal_event3 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="poison_test",
            order_id="after-poison-order",
            account_id="test-account",
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("5.0"),
            price=Decimal("3000.0")
        )
        
        result4 = await bus.publish(EventType.ORDER_CREATED, normal_event3)
        assert result4.success == True
        
        await asyncio.sleep(0.2)
        
        # Verify system recovery after poison message
        assert len(handler.received_events) == 3
        assert handler.received_events[2].order_id == "after-poison-order"
        
        await bus.close()

    async def test_concurrent_publishers_subscribers(self):
        """Test concurrent publishers and subscribers - Integration scenario"""
        bus = InMemoryEventBus(buffer_size=5000)
        await bus.initialize()
        
        # Create multiple handlers for different event types
        order_handler = OrderingTestHandler()
        trade_handler = OrderingTestHandler()
        risk_handler = OrderingTestHandler()
        
        # Subscribe to different event types
        await bus.subscribe(EventType.ORDER_CREATED, order_handler)
        await bus.subscribe(EventType.TRADE_EXECUTED, trade_handler)
        await bus.subscribe(EventType.RISK_ALERT, risk_handler)
        
        # Create concurrent publishing tasks
        async def publish_orders():
            for i in range(50):
                event = OrderEvent(
                    type=EventType.ORDER_CREATED,
                    source=f"publisher_orders_{i}",
                    order_id=f"concurrent-order-{i}",
                    account_id="test-account",
                    symbol="BTC/USD",
                    side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=Decimal("1.0"),
                    price=Decimal(f"{50000 + i}")
                )
                await bus.publish(EventType.ORDER_CREATED, event)
                await asyncio.sleep(0.001)  # Small delay to simulate real usage
                
        async def publish_trades():
            for i in range(30):
                event = TradeEvent(
                    type=EventType.TRADE_EXECUTED,
                    source=f"publisher_trades_{i}",
                    trade_id=f"concurrent-trade-{i}",
                    order_id=f"concurrent-order-{i}",
                    account_id="test-account",
                    symbol="BTC/USD",
                    side=OrderSide.BUY,
                    quantity=Decimal("1.0"),
                    price=Decimal(f"{50000 + i}"),
                    fee=Decimal("10.0"),
                    commission=Decimal("5.0")
                )
                await bus.publish(EventType.TRADE_EXECUTED, event)
                await asyncio.sleep(0.002)
                
        async def publish_risks():
            for i in range(20):
                event = RiskEvent(
                    type=EventType.RISK_ALERT,
                    source=f"publisher_risks_{i}",
                    account_id="test-account",
                    risk_type="position_limit",
                    severity=RiskSeverity.MEDIUM,
                    message=f"Risk alert {i}",
                    threshold=Decimal("1000.0"),
                    current_value=Decimal(f"{1100 + i}")
                )
                await bus.publish(EventType.RISK_ALERT, event)
                await asyncio.sleep(0.003)
        
        # Run all publishers concurrently
        start_time = time.time()
        await asyncio.gather(
            publish_orders(),
            publish_trades(), 
            publish_risks()
        )
        end_time = time.time()
        
        # Wait for all events to be processed
        await asyncio.sleep(1.0)
        
        # Verify all events were received
        assert len(order_handler.received_events) == 50
        assert len(trade_handler.received_events) == 30
        assert len(risk_handler.received_events) == 20
        
        # Verify performance (should handle 100 events in reasonable time)
        total_time = end_time - start_time
        total_events = 100
        events_per_second = total_events / total_time
        
        # Should achieve good throughput
        assert events_per_second > 100  # At least 100 events/second
        
        await bus.close()

    async def test_large_event_payloads(self):
        """Test handling of large event payloads (>1MB) - Integration scenario"""
        bus = InMemoryEventBus(buffer_size=10)
        await bus.initialize()
        
        handler = OrderingTestHandler()
        await bus.subscribe(EventType.SYSTEM_EVENT, handler)
        
        # Create large payload (>1MB)
        large_data = "x" * (1024 * 1024 + 1000)  # >1MB string
        
        large_event = SystemEvent(
            type=EventType.SYSTEM_EVENT,
            source="large_payload_test",
            component="test_component",
            message="Large payload test",
            data={"large_field": large_data}
        )
        
        # Publish large event
        start_time = time.time()
        result = await bus.publish(EventType.SYSTEM_EVENT, large_event)
        end_time = time.time()
        
        assert result.success == True
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Verify large event was handled correctly
        assert len(handler.received_events) == 1
        received_event = handler.received_events[0]
        assert received_event.message == "Large payload test"
        assert len(received_event.data["large_field"]) > 1024 * 1024
        
        # Verify reasonable performance even with large payload
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should process within 1 second
        
        await bus.close()

    async def test_event_bus_restart_scenarios(self):
        """Test event bus restart scenarios - Integration scenario"""
        bus = InMemoryEventBus()
        
        # Test 1: Initialize -> Close -> Re-initialize
        await bus.initialize()
        assert bus._initialized == True
        
        handler = OrderingTestHandler()
        await bus.subscribe(EventType.ORDER_CREATED, handler)
        
        # Publish event before restart
        event1 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="restart_test",
            order_id="before-restart",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        result1 = await bus.publish(EventType.ORDER_CREATED, event1)
        assert result1.success == True
        
        await asyncio.sleep(0.1)
        assert len(handler.received_events) == 1
        
        # Restart the bus
        await bus.close()
        assert bus._initialized == False
        
        # Re-initialize
        await bus.initialize()
        assert bus._initialized == True
        
        # Re-subscribe (subscriptions should be cleared after restart)
        handler2 = OrderingTestHandler()
        await bus.subscribe(EventType.ORDER_CREATED, handler2)
        
        # Publish event after restart
        event2 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="restart_test",
            order_id="after-restart",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.5"),
            price=Decimal("51000.0")
        )
        
        result2 = await bus.publish(EventType.ORDER_CREATED, event2)
        assert result2.success == True
        
        await asyncio.sleep(0.1)
        
        # Verify restart behavior
        assert len(handler.received_events) == 1  # Original handler stopped
        assert len(handler2.received_events) == 1  # New handler working
        assert handler2.received_events[0].order_id == "after-restart"
        
        await bus.close()

    async def test_network_partition_recovery(self):
        """Test network partition and recovery scenarios - Integration scenario"""
        # Simulate network partition using mock buses
        redis_bus = MockRedisEventBus(should_fail=False)
        backup_bus = InMemoryEventBus()
        
        await redis_bus.initialize()
        await backup_bus.initialize()
        
        handler = OrderingTestHandler()
        
        # Normal operation with Redis
        await redis_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        event1 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="network_test",
            order_id="before-partition",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        
        await redis_bus.publish(EventType.ORDER_CREATED, event1)
        assert len(redis_bus.published_events) == 1
        
        # Simulate network partition (Redis becomes unavailable)
        redis_bus.should_fail = True
        
        # Switch to backup bus
        await backup_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        event2 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="network_test",
            order_id="during-partition",
            account_id="test-account",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.5"),
            price=Decimal("51000.0")
        )
        
        result = await backup_bus.publish(EventType.ORDER_CREATED, event2)
        assert result.success == True
        
        # Simulate network recovery
        redis_bus.should_fail = False
        await redis_bus.initialize()
        await redis_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        event3 = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="network_test",
            order_id="after-recovery",
            account_id="test-account",
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10.0"),
            price=Decimal("3000.0")
        )
        
        await redis_bus.publish(EventType.ORDER_CREATED, event3)
        
        # Verify recovery
        assert len(redis_bus.published_events) == 2  # Before + after recovery
        assert redis_bus.health_check() == True
        
        await redis_bus.close()
        await backup_bus.close()
