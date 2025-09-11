"""
Event Bus Performance Tests for Xline Trading System.

Tests event processing latency targets and performance optimization.
Validates <1ms P99 latency requirement for high-frequency trading.
"""

import asyncio
import pytest
from decimal import Decimal

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType
from xline.core.market_data.types import PriceTickEvent, MarketDepthEvent
from xline.core.monitoring.performance import PerformanceMonitor


@pytest.mark.asyncio
async def test_event_latency_target() -> None:
    """
    Test <1ms P99 latency target for event processing.
    
    Publishes 1000 events and validates P99 latency is under 1ms.
    Critical for high-frequency trading performance requirements.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    try:
        # Publish 1000 events to test latency under load
        for i in range(1000):
            event = PriceTickEvent(
                type=EventType.PRICE_TICK,
                source="performance_test",
                symbol="BTCUSD",
                bid=Decimal("50000.00") + Decimal(str(i * 0.01)),
                ask=Decimal("50000.05") + Decimal(str(i * 0.01)),
                volume=Decimal("1000.0"),
                tick_timestamp=1694649600.123
            )
            await event_bus.publish(event)
        
        # Allow processing to complete
        await asyncio.sleep(0.1)
        
        # Check latency metrics
        report = monitor.get_performance_report()
        
        # Assert P99 latency < 1ms for all event types
        for event_type, metrics in report["event_metrics"].items():
            assert metrics["p99_latency_ms"] < 1.0, (
                f"P99 latency exceeded 1ms target: {metrics['p99_latency_ms']:.3f}ms "
                f"for event type {event_type}"
            )
            
            # Additional performance validations
            assert metrics["avg_latency_ms"] < 0.5, (
                f"Average latency too high: {metrics['avg_latency_ms']:.3f}ms"
            )
            
        print(f"✅ P99 Latency Target Met: {report['event_metrics']}")
        
    finally:
        await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_sustained_latency_performance() -> None:
    """
    Test sustained performance under continuous load.
    
    Validates latency remains stable during extended operation periods.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    try:
        # Sustained load test - 5000 events
        for i in range(5000):
            event = PriceTickEvent(
                type=EventType.PRICE_TICK,
                source="sustained_test",
                symbol="EURUSD", 
                bid=Decimal("1.0850"),
                ask=Decimal("1.0852"),
                volume=Decimal("1000000"),
                tick_timestamp=1694649600.123 + i * 0.001
            )
            await event_bus.publish(event)
            
            # Small delay to simulate realistic load
            if i % 100 == 0:
                await asyncio.sleep(0.001)
        
        # Allow processing to complete
        await asyncio.sleep(0.2)
        
        report = monitor.get_performance_report()
        
        # Validate sustained performance
        for event_type, metrics in report["event_metrics"].items():
            assert metrics["p99_latency_ms"] < 1.0, (
                f"Sustained P99 latency exceeded: {metrics['p99_latency_ms']:.3f}ms"
            )
            assert metrics["count"] > 0, "No events processed"
            
        print(f"✅ Sustained Performance Test Passed: {report['event_metrics']}")
        
    finally:
        await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_memory_efficiency() -> None:
    """
    Test memory usage remains under 500MB target during operation.
    
    Validates memory efficiency for long-running trading systems.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    try:
        # Generate significant event load to test memory usage
        for batch in range(10):
            for i in range(1000):
                event = PriceTickEvent(
                    type=EventType.PRICE_TICK,
                    source="memory_test",
                    symbol="BTCUSD",
                    bid=Decimal("50000.00") + Decimal(str(i)),
                    ask=Decimal("50000.05") + Decimal(str(i)),
                    volume=Decimal("1000.0"),
                    tick_timestamp=1694649600.123 + batch * 1000 + i
                )
                await event_bus.publish(event)
            
            # Check memory usage periodically
            await asyncio.sleep(0.1)
        
        # Final memory check
        await asyncio.sleep(0.5)
        report = monitor.get_performance_report()
        
        memory_used_mb = report["system_stats"].get("memory_used_mb", 0)
        
        # Validate memory usage under 500MB
        assert memory_used_mb < 500, (
            f"Memory usage exceeded 500MB target: {memory_used_mb:.1f}MB"
        )
        
        print(f"✅ Memory Efficiency Test Passed: {memory_used_mb:.1f}MB used")
        
    finally:
        await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_concurrent_event_processing() -> None:
    """
    Test latency performance under concurrent event publishing.
    
    Validates system handles concurrent load without latency degradation.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    try:
        # Create concurrent event publishing tasks
        async def publish_events(event_count: int, prefix: str) -> None:
            for i in range(event_count):
                event = MarketDepthEvent(
                    type=EventType.MARKET_DEPTH,
                    source=f"concurrent_{prefix}",
                    symbol=f"{prefix}USD",
                    bids={"50000": Decimal("1.0"), "49999": Decimal("2.0")},
                    asks={"50001": Decimal("1.5"), "50002": Decimal("2.5")},
                    depth_timestamp=1694649600.123 + i * 0.001
                )
                await event_bus.publish(event)
        
        # Run concurrent publishing tasks
        tasks = [
            publish_events(500, "BTC"),
            publish_events(500, "ETH"),
            publish_events(500, "EUR"),
            publish_events(500, "GBP")
        ]
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.2)
        
        report = monitor.get_performance_report()
        
        # Validate concurrent performance
        for event_type, metrics in report["event_metrics"].items():
            assert metrics["p99_latency_ms"] < 1.0, (
                f"Concurrent P99 latency exceeded: {metrics['p99_latency_ms']:.3f}ms"
            )
            
        total_events = sum(m["count"] for m in report["event_metrics"].values())
        assert total_events >= 2000, f"Expected 2000+ events, got {total_events}"
        
        print(f"✅ Concurrent Processing Test Passed: {total_events} events processed")
        
    finally:
        await monitor.stop_monitoring()
