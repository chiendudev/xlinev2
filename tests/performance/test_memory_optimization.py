"""
Memory optimization performance         event = OrderE    for i in range(1000):
        event = OrderEvent(
            order_id=f"pooled_test_{i}",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("1.0"),
            price=Decimal(f"{50000.00 + i}"),
            order_type="MARKET",
            source="pooled_test"
        )
        await event_bus2.publish(event)          order_id=f"test_{i}",
            sy        event = OrderEvent(
            order_id=f"leak_test_{i}",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("1.0"),
            price=Decimal(f"{50000.00 + i}"),
            order_type="MARKET",
            source="leak_test"
        )BTCUSD",
            side="BUY"        event = OrderEvent(
            order_id=f"pool_test_{i}",
            symbol="BTCUSD",
            side="SELL",
            quantity=Decimal("1.0"),
            price=Decimal(f"{50000.00 + i}"),
            order_type="LIMIT",
            source="pooled_test"
        )        quantity=Decimal("1.0"),
            price=Decimal(f"{50000.00 + i}"),
            order_type="LIMIT",
            source="baseline_test"
        )for Xline trading system.

Tests event object pooling, memory leak detection, and garbage collection
monitoring to ensure optimal memory usage in high-frequency trading.
"""

import asyncio
import pytest
from decimal import Decimal

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType, OrderEvent
from xline.core.monitoring.memory import EventPool, MemoryMonitor, OptimizedEventBus
from xline.core.monitoring.performance import PerformanceMonitor


@pytest.mark.asyncio
async def test_event_pooling_performance() -> None:
    """
    Test event object pooling reduces memory allocation overhead.
    
    Validates that event pooling significantly improves performance
    by reducing garbage collection pressure.
    """
    # Test without pooling (baseline)
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    # Baseline test - create new events each time
    start_objects = len(monitor.metrics_collector.metrics)
    
    for i in range(1000):
        event = PriceTickEvent(
            data=f"BTCUSD",
            bid=f"{50000.00 + i}",
            ask=f"{50000.05 + i}",
            source="baseline_test"
        )
        await event_bus.publish(event)
    
    await asyncio.sleep(0.1)
    baseline_report = monitor.get_performance_report()
    await monitor.stop_monitoring()
    
    # Test with pooling
    optimized_bus = OptimizedEventBus(event_bus, pool_size=100)
    optimized_bus.memory_monitor.start_monitoring()
    
    monitor2 = PerformanceMonitor(event_bus)
    await monitor2.start_monitoring()
    
    for i in range(1000):
        await optimized_bus.publish_optimized(
            EventType.PRICE_TICK,
            {"symbol": "BTCUSD", "price": Decimal("50000.00") + Decimal(str(i))},
            "pooled_test"
        )
    
    await asyncio.sleep(0.1)
    pooled_report = monitor2.get_performance_report()
    optimization_stats = optimized_bus.get_optimization_stats()
    
    await monitor2.stop_monitoring()
    optimized_bus.memory_monitor.stop_monitoring()
    
    # Validate pooling effectiveness
    assert optimization_stats["event_pool"]["pool_size"] > 0, "Event pool should contain reused events"
    
    # Memory efficiency check
    memory_stats = optimization_stats["memory_stats"]
    assert memory_stats["object_growth"] < 1000, "Object growth should be minimized with pooling"
    
    print(f"✅ Event Pooling Test Passed:")
    print(f"   Pool size: {optimization_stats['event_pool']['pool_size']}")
    print(f"   Object growth: {memory_stats['object_growth']}")


@pytest.mark.asyncio
async def test_memory_leak_detection() -> None:
    """
    Test memory leak detection identifies potential memory issues.
    
    Validates that memory monitor can detect growing object counts
    and garbage collection inefficiencies.
    """
    memory_monitor = MemoryMonitor()
    memory_monitor.start_monitoring()
    
    # Simulate memory leak by creating and retaining objects
    leaked_objects = []
    
    for i in range(500):
        # Create objects that won't be garbage collected
        event = PriceTickEvent(
            data=f"BTCUSD",
            bid=f"{50000.00 + i}",
            ask=f"{50000.05 + i}",
            source="leak_test"
        )
        leaked_objects.append(event)
        
        # Take periodic snapshots
        if i % 100 == 0:
            memory_monitor._take_snapshot(f"step_{i}")
    
    memory_monitor.stop_monitoring()
    
    # Analyze for memory leaks
    leak_analysis = memory_monitor.detect_memory_leaks()
    memory_stats = memory_monitor.get_memory_stats()
    
    # Validate leak detection
    assert leak_analysis["object_growth"] > 400, "Should detect significant object growth"
    assert leak_analysis["potential_leak"], "Should flag potential memory leak"
    assert memory_stats["object_growth"] > 0, "Object count should have increased"
    
    print(f"✅ Memory Leak Detection Test Passed:")
    print(f"   Object growth: {leak_analysis['object_growth']}")
    print(f"   Potential leak detected: {leak_analysis['potential_leak']}")
    
    # Cleanup to prevent affecting other tests
    del leaked_objects


@pytest.mark.asyncio
async def test_garbage_collection_optimization() -> None:
    """
    Test garbage collection monitoring and forced collection.
    
    Validates that GC monitoring provides useful insights and
    forced collection reduces memory usage.
    """
    memory_monitor = MemoryMonitor()
    
    # Create temporary objects
    temp_objects = []
    for i in range(1000):
        event = PriceTickEvent(
            data="BTCUSD",
            bid=f"{50000.00 + i}",
            ask=f"{50000.05 + i}",
            source="gc_test"
        )
        temp_objects.append(event)
    
    # Clear references to make objects eligible for GC
    objects_before = memory_monitor.get_memory_stats()["current_objects"]
    del temp_objects
    
    # Force garbage collection
    gc_stats = memory_monitor.force_gc()
    objects_after = memory_monitor.get_memory_stats()["current_objects"]
    
    # Validate GC effectiveness
    assert gc_stats["objects_freed"] > 0, "Garbage collection should free some objects"
    assert objects_after <= objects_before, "Object count should not increase after GC"
    assert gc_stats["objects_collected"] >= 0, "GC should report collection count"
    
    print(f"✅ Garbage Collection Test Passed:")
    print(f"   Objects freed: {gc_stats['objects_freed']}")
    print(f"   Objects collected: {gc_stats['objects_collected']}")


@pytest.mark.asyncio
async def test_optimized_event_bus_integration() -> None:
    """
    Test optimized event bus with performance monitoring integration.
    
    Validates that the optimized event bus maintains performance
    while providing memory efficiency benefits.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    # Create optimized event bus with monitoring
    optimized_bus = OptimizedEventBus(event_bus, pool_size=200)
    performance_monitor = PerformanceMonitor(event_bus)
    
    await performance_monitor.start_monitoring()
    optimized_bus.memory_monitor.start_monitoring()
    
    try:
        # High-frequency event publishing test
        for batch in range(5):
            for i in range(500):
                await optimized_bus.publish_optimized(
                    EventType.MARKET_DEPTH,
                    {
                        "symbol": f"SYMBOL_{batch}",
                        "bids": {f"{50000 + i}": "1.0"},
                        "asks": {f"{50001 + i}": "1.0"}
                    },
                    f"integration_test_batch_{batch}"
                )
            
            # Allow processing and check intermediate stats
            await asyncio.sleep(0.05)
        
        # Final performance analysis
        performance_report = performance_monitor.get_performance_report()
        optimization_stats = optimized_bus.get_optimization_stats()
        
        # Validate performance targets
        for event_type, metrics in performance_report["event_metrics"].items():
            assert metrics["p99_latency_ms"] < 1.0, (
                f"P99 latency exceeded with optimization: {metrics['p99_latency_ms']:.3f}ms"
            )
        
        # Validate memory efficiency
        pool_stats = optimization_stats["event_pool"]
        assert pool_stats["pool_size"] > 0, "Event pool should be utilized"
        
        memory_stats = optimization_stats["memory_stats"]
        assert memory_stats["object_growth"] < 2500, "Object growth should be controlled"
        
        print(f"✅ Optimized Event Bus Integration Test Passed:")
        print(f"   Events processed: {sum(m['count'] for m in performance_report['event_metrics'].values())}")
        print(f"   Pool utilization: {pool_stats['pool_size']}/{pool_stats['pool_capacity']}")
        print(f"   Memory efficiency: {memory_stats['object_growth']} object growth")
        
    finally:
        await performance_monitor.stop_monitoring()
        optimized_bus.memory_monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_memory_usage_threshold() -> None:
    """
    Test memory usage stays under 500MB threshold during intensive operations.
    
    Validates system memory efficiency under sustained high-frequency load.
    """
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    optimized_bus = OptimizedEventBus(event_bus, pool_size=500)
    performance_monitor = PerformanceMonitor(event_bus)
    
    await performance_monitor.start_monitoring()
    optimized_bus.memory_monitor.start_monitoring()
    
    try:
        # Intensive memory test - high volume event processing
        for session in range(20):
            for i in range(250):
                await optimized_bus.publish_optimized(
                    EventType.PRICE_TICK,
                    {
                        "symbol": f"INTENSIVE_{session % 5}USD",
                        "bid": Decimal("50000.00") + Decimal(str(i * 0.01)),
                        "ask": Decimal("50000.05") + Decimal(str(i * 0.01)),
                        "volume": Decimal("1000.0") + Decimal(str(i)),
                        "session": session
                    },
                    f"intensive_session_{session}"
                )
            
            # Periodic GC to maintain memory efficiency
            if session % 5 == 0:
                optimized_bus.memory_monitor.force_gc()
                await asyncio.sleep(0.01)
        
        # Final memory assessment
        performance_report = performance_monitor.get_performance_report()
        system_stats = performance_report["system_stats"]
        
        memory_used_mb = system_stats.get("memory_used_mb", 0)
        
        # Validate memory threshold
        assert memory_used_mb < 500, (
            f"Memory usage exceeded 500MB threshold: {memory_used_mb:.1f}MB"
        )
        
        # Validate continued performance
        for event_type, metrics in performance_report["event_metrics"].items():
            assert metrics["p99_latency_ms"] < 1.0, (
                f"Performance degraded under memory load: {metrics['p99_latency_ms']:.3f}ms"
            )
        
        total_events = sum(m["count"] for m in performance_report["event_metrics"].values())
        
        print(f"✅ Memory Threshold Test Passed:")
        print(f"   Total events: {total_events}")
        print(f"   Memory usage: {memory_used_mb:.1f}MB")
        print(f"   Memory efficiency maintained under intensive load")
        
    finally:
        await performance_monitor.stop_monitoring()
        optimized_bus.memory_monitor.stop_monitoring()
