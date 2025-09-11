"""
Performance tests for Xline Market Data Pipeline.

Tests throughput and latency requirements:
- 1000+ ticks/second throughput
- <5ms tick-to-event latency
"""

import asyncio
import pytest
import time
from decimal import Decimal

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType
from xline.core.market_data.feed import MarketDataFeed
from xline.core.market_data.processor import MarketDataProcessor
from xline.core.market_data.types import PriceTickEvent


@pytest.mark.asyncio
async def test_throughput_target() -> None:
    """Test 1000+ ticks/second throughput requirement."""
    # Setup
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    
    config = {"tick_interval_ms": 1, "batch_size": 10}
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    # Start systems
    await feed.start()
    await processor.start()
    
    # Subscribe to multiple symbols for higher throughput
    test_symbols = ["BTCUSD", "ETHUSDT", "ADAUSD", "DOGEUSDT", "SOLUSDT"]
    for symbol in test_symbols:
        await feed.subscribe_symbol(symbol)
    
    # Run for 5 seconds to measure sustained throughput
    test_duration = 5.0
    await asyncio.sleep(test_duration)
    
    # Get performance statistics
    feed_stats = feed.get_performance_stats()
    processor_stats = processor.get_processing_stats()
    
    # Cleanup
    await feed.stop()
    await processor.stop()
    
    # Assertions for throughput target
    assert feed_stats["ticks_per_second"] >= 1000, (
        f"Expected >=1000 ticks/sec, got {feed_stats['ticks_per_second']}"
    )
    
    # Verify processor kept up with feed
    assert processor_stats["events_processed"] > 0
    assert processor_stats["events_processed"] >= feed_stats["ticks_processed"] * 0.95
    
    print(f"✅ Throughput test passed: {feed_stats['ticks_per_second']:.2f} ticks/sec")
    print(f"   Events processed: {processor_stats['events_processed']}")
    print(f"   Test duration: {test_duration}s")


@pytest.mark.asyncio
async def test_latency_target() -> None:
    """Test <5ms tick-to-event latency requirement."""
    # Setup
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    
    processor = MarketDataProcessor(event_bus)
    
    await processor.start()
    
    # Create test events and measure end-to-end latency
    latencies = []
    num_tests = 100
    
    for i in range(num_tests):
        start_time = time.perf_counter()
        
        # Create and publish price tick event
        tick_event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source="latency_test",
            symbol="BTCUSD",
            bid=Decimal("50000.00"),
            ask=Decimal("50001.00"),
            volume=Decimal("1.0"),
            tick_timestamp=start_time
        )
        
        await event_bus.publish(tick_event)
        
        # Small delay to allow processing
        await asyncio.sleep(0.001)
        
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)
    
    # Cleanup
    await processor.stop()
    
    # Calculate latency statistics
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
    
    # Get processor stats
    processor_stats = processor.get_processing_stats()
    
    # Assertions for latency target
    assert avg_latency < 5.0, (
        f"Expected avg latency <5ms, got {avg_latency:.2f}ms"
    )
    assert p95_latency < 10.0, (
        f"Expected P95 latency <10ms, got {p95_latency:.2f}ms"
    )
    assert processor_stats["avg_latency_ms"] < 5.0, (
        f"Expected processor avg latency <5ms, got {processor_stats['avg_latency_ms']:.2f}ms"
    )
    
    print(f"✅ Latency test passed:")
    print(f"   Average latency: {avg_latency:.2f}ms")
    print(f"   Max latency: {max_latency:.2f}ms")
    print(f"   P95 latency: {p95_latency:.2f}ms")
    print(f"   Processor avg latency: {processor_stats['avg_latency_ms']:.2f}ms")


@pytest.mark.asyncio
async def test_sustained_performance() -> None:
    """Test sustained performance over extended period."""
    # Setup
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    
    config = {"tick_interval_ms": 0.5}  # Aggressive timing for stress test
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    # Start systems
    await feed.start()
    await processor.start()
    
    # Subscribe to symbols
    for symbol in ["BTCUSD", "ETHUSDT", "ADAUSD"]:
        await feed.subscribe_symbol(symbol)
    
    # Run for 10 seconds to test sustained performance
    test_duration = 10.0
    checkpoints = []
    
    # Take performance snapshots every 2 seconds
    for i in range(5):
        await asyncio.sleep(2.0)
        
        feed_stats = feed.get_performance_stats()
        processor_stats = processor.get_processing_stats()
        
        checkpoints.append({
            "time": i * 2 + 2,
            "ticks_per_second": feed_stats["ticks_per_second"],
            "events_processed": processor_stats["events_processed"],
            "avg_latency_ms": processor_stats["avg_latency_ms"]
        })
    
    # Cleanup
    await feed.stop()
    await processor.stop()
    
    # Verify sustained performance
    final_stats = checkpoints[-1]
    
    assert final_stats["ticks_per_second"] >= 1000, (
        f"Sustained throughput below target: {final_stats['ticks_per_second']}"
    )
    assert final_stats["avg_latency_ms"] < 5.0, (
        f"Sustained latency above target: {final_stats['avg_latency_ms']}"
    )
    
    # Check performance consistency (no significant degradation)
    first_half_tps = sum(cp["ticks_per_second"] for cp in checkpoints[:2]) / 2
    second_half_tps = sum(cp["ticks_per_second"] for cp in checkpoints[3:]) / 2
    
    performance_degradation = (first_half_tps - second_half_tps) / first_half_tps
    assert performance_degradation < 0.1, (
        f"Performance degraded by {performance_degradation*100:.1f}%"
    )
    
    print(f"✅ Sustained performance test passed:")
    print(f"   Final throughput: {final_stats['ticks_per_second']:.2f} ticks/sec")
    print(f"   Final avg latency: {final_stats['avg_latency_ms']:.2f}ms")
    print(f"   Performance degradation: {performance_degradation*100:.1f}%")


@pytest.mark.asyncio
async def test_memory_efficiency() -> None:
    """Test memory efficiency under high load."""
    import tracemalloc
    
    tracemalloc.start()
    
    # Setup
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    
    config = {"tick_interval_ms": 1}
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    # Start systems
    await feed.start()
    await processor.start()
    
    # Subscribe to many symbols
    for i in range(20):
        await feed.subscribe_symbol(f"SYMBOL{i:02d}")
    
    # Measure initial memory
    initial_snapshot = tracemalloc.take_snapshot()
    
    # Run for 5 seconds with high load
    await asyncio.sleep(5.0)
    
    # Measure final memory
    final_snapshot = tracemalloc.take_snapshot()
    
    # Cleanup
    await feed.stop()
    await processor.stop()
    
    # Analyze memory usage
    top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')
    total_memory_mb = sum(stat.size_diff for stat in top_stats) / 1024 / 1024
    
    feed_stats = feed.get_performance_stats()
    
    # Memory efficiency assertions
    assert total_memory_mb < 50, (
        f"Memory usage too high: {total_memory_mb:.2f}MB"
    )
    
    print(f"✅ Memory efficiency test passed:")
    print(f"   Memory usage: {total_memory_mb:.2f}MB")
    print(f"   Events processed: {feed_stats['ticks_processed']}")
    print(f"   Memory per event: {total_memory_mb*1024/feed_stats['ticks_processed']:.2f}KB")
    
    tracemalloc.stop()


if __name__ == "__main__":
    # Run performance tests directly
    import sys
    
    async def run_all_tests():
        print("🚀 Running Xline Market Data Performance Tests")
        print("=" * 60)
        
        try:
            await test_throughput_target()
            print()
            
            await test_latency_target()
            print()
            
            await test_sustained_performance()
            print()
            
            await test_memory_efficiency()
            print()
            
            print("🎉 All performance tests passed!")
            
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            sys.exit(1)
    
    asyncio.run(run_all_tests())
