"""Simplified tests for memory optimization utilities."""

import asyncio
import pytest

from xline.core.events.types import EventType
from xline.core.monitoring.memory import EventPool, MemoryMonitor, OptimizedEventBus


class TestEventPool:
    """Test event pooling functionality."""

    def test_pool_initialization(self):
        """Test event pool initializes correctly."""
        pool = EventPool(pool_size=100)
        assert pool.pool_size == 100
        assert len(pool._pool) == 0

    def test_get_event_from_empty_pool(self):
        """Test getting event from empty pool creates new event."""
        pool = EventPool()
        event = pool.get_event(EventType.ORDER_CREATED, {"test": "data"}, "test_source")
        assert event.type == EventType.ORDER_CREATED
        assert event.source == "test_source"
        
    def test_return_and_reuse_event(self):
        """Test returning and reusing events."""
        pool = EventPool()
        event = pool.get_event(EventType.ORDER_CREATED, {"test": "data"}, "test_source")
        pool.return_event(event)
        assert len(pool._pool) == 1

    def test_pool_statistics(self):
        """Test pool statistics."""
        pool = EventPool()
        stats = pool.get_pool_stats()
        assert "pool_size" in stats
        assert "active_events" in stats
        assert "pool_capacity" in stats


class TestMemoryMonitor:
    """Test memory monitoring functionality."""

    def test_monitor_initialization(self):
        """Test memory monitor initializes correctly."""
        monitor = MemoryMonitor()
        assert not monitor.is_monitoring
        assert monitor.baseline_objects > 0

    def test_monitoring_lifecycle(self):
        """Test start/stop monitoring lifecycle."""
        monitor = MemoryMonitor()
        monitor.start_monitoring()
        assert monitor.is_monitoring
        monitor.stop_monitoring()
        assert not monitor.is_monitoring

    def test_memory_snapshots(self):
        """Test memory snapshot collection."""
        monitor = MemoryMonitor()
        monitor.start_monitoring()
        monitor._take_snapshot("test_snapshot")
        assert len(monitor._snapshots) >= 2
        snapshot = monitor._snapshots[-1]
        assert "label" in snapshot
        assert "total_objects" in snapshot

    def test_memory_leak_detection(self):
        """Test memory leak detection."""
        monitor = MemoryMonitor()
        monitor.start_monitoring()
        monitor.stop_monitoring()
        leaks = monitor.detect_memory_leaks()
        assert "object_growth" in leaks

    def test_gc_statistics(self):
        """Test garbage collection statistics."""
        monitor = MemoryMonitor()
        monitor.start_monitoring()
        gc_stats = monitor.force_gc()
        assert "objects_collected" in gc_stats
        assert "objects_before" in gc_stats
        assert "objects_after" in gc_stats
        monitor.stop_monitoring()

    def test_memory_statistics(self):
        """Test memory statistics collection."""
        monitor = MemoryMonitor()
        monitor.start_monitoring()
        stats = monitor.get_memory_stats()
        assert "snapshots_taken" in stats
        assert "current_objects" in stats
        assert "baseline_objects" in stats
        monitor.stop_monitoring()


class TestOptimizedEventBus:
    """Test optimized event bus functionality."""

    @pytest.mark.asyncio
    async def test_optimized_bus_initialization(self):
        """Test optimized event bus initializes correctly."""
        from xline.core.events.bus import InMemoryEventBus
        base_bus = InMemoryEventBus()
        bus = OptimizedEventBus(base_bus, pool_size=100)
        assert bus.event_pool.pool_size == 100
        assert isinstance(bus.memory_monitor, MemoryMonitor)

    @pytest.mark.asyncio
    async def test_event_publishing_with_pool(self):
        """Test event publishing uses object pooling."""
        from xline.core.events.bus import InMemoryEventBus
        base_bus = InMemoryEventBus()
        await base_bus.initialize()
        bus = OptimizedEventBus(base_bus, pool_size=50)

        # Publish event using optimized bus
        await bus.publish_optimized(
            EventType.ORDER_CREATED,
            {"order_id": "test_order"},
            "test_source"
        )

        # Verify pool stats
        stats = bus.get_optimization_stats()
        assert "event_pool" in stats

    @pytest.mark.asyncio
    async def test_memory_optimization_features(self):
        """Test memory optimization features."""
        from xline.core.events.bus import InMemoryEventBus
        base_bus = InMemoryEventBus()
        await base_bus.initialize()
        bus = OptimizedEventBus(base_bus, pool_size=20)

        # Publish many events
        for i in range(10):
            await bus.publish_optimized(
                EventType.TRADE_EXECUTED,
                {"trade_id": f"trade_{i}"},
                "trading_engine"
            )

        # Get optimization statistics
        stats = bus.get_optimization_stats()
        assert "event_pool" in stats
        assert "memory_stats" in stats


class TestMemoryIntegration:
    """Test integrated memory optimization scenarios."""

    def test_pool_with_real_events(self):
        """Test event pool with real event objects."""
        pool = EventPool()
        
        # Create multiple events
        events = []
        for i in range(5):
            event = pool.get_event(
                EventType.ORDER_CREATED,
                {"order_id": f"order_{i}"},
                "test_source"
            )
            events.append(event)
        
        # Return all events to pool
        for event in events:
            pool.return_event(event)
            
        # Verify pool contains returned events
        stats = pool.get_pool_stats()
        assert stats["pool_size"] == 5

    def test_memory_optimization_workflow(self):
        """Test complete memory optimization workflow."""
        # Initialize components
        pool = EventPool(pool_size=10)
        monitor = MemoryMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Simulate event processing
        for i in range(20):
            event = pool.get_event(
                EventType.PRICE_TICK,
                {"price": f"{50000 + i}"},
                "market_data"
            )
            pool.return_event(event)
        
        # Stop monitoring and analyze
        monitor.stop_monitoring()
        stats = monitor.get_memory_stats()
        assert "object_growth" in stats
        
        pool_stats = pool.get_pool_stats()
        assert pool_stats["pool_size"] <= 10  # Pool size should not exceed limit

    @pytest.mark.asyncio
    async def test_memory_with_event_bus(self):
        """Test memory optimization with event bus integration."""
        from xline.core.events.bus import InMemoryEventBus

        pool = EventPool()
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        # Create event from pool
        event = pool.get_event(
            EventType.ORDER_CREATED,
            {"order_id": "test_123"},
            "pool_test"
        )

        # Publish event
        await event_bus.publish(event)
        await asyncio.sleep(0.01)

        # Return event to pool
        pool.return_event(event)

        # Verify integration
        assert len(pool._pool) == 1
        await event_bus.cleanup()
