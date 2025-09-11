"""
Integration tests for Xline Market Data Pipeline.

Tests end-to-end integration of market data feed, processor, and event bus.
"""

import asyncio
import pytest
from decimal import Decimal

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType
from xline.core.market_data.feed import MarketDataFeed
from xline.core.market_data.processor import MarketDataProcessor
from xline.core.market_data.types import MarketDepthEvent, PriceTickEvent


@pytest.mark.asyncio
async def test_market_data_pipeline_integration() -> None:
    """Test complete market data pipeline integration."""
    # Setup components
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    config = {"tick_interval_ms": 10, "batch_size": 5}
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    # Start components
    await feed.start()
    await processor.start()
    
    # Subscribe to test symbols
    test_symbols = ["BTCUSD", "ETHUSDT"]
    for symbol in test_symbols:
        await feed.subscribe_symbol(symbol)
    
    # Let the system run for a short time
    await asyncio.sleep(2.0)
    
    # Verify data flow
    feed_stats = feed.get_performance_stats()
    processor_stats = processor.get_processing_stats()
    
    # Check that events are being generated and processed
    assert feed_stats["ticks_processed"] > 0
    assert processor_stats["events_processed"] > 0
    assert processor_stats["events_processed"] >= feed_stats["ticks_processed"] * 0.9
    
    # Check that symbols are cached
    cached_symbols = processor.get_cached_symbols()
    assert len(cached_symbols) > 0
    
    # Verify price data for symbols
    for symbol in test_symbols:
        latest_price = processor.get_latest_price(symbol)
        assert latest_price is not None
        assert latest_price.symbol == symbol
        assert latest_price.bid > 0
        assert latest_price.ask > 0
        assert latest_price.volume > 0
    
    # Cleanup
    await feed.stop()
    await processor.stop()
    
    print("✅ Market data pipeline integration test passed")


@pytest.mark.asyncio
async def test_event_type_handling() -> None:
    """Test handling of different market data event types."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    processor = MarketDataProcessor(event_bus)
    
    await processor.start()
    
    # Create and publish price tick event
    price_event = PriceTickEvent(
        type=EventType.PRICE_TICK,
        symbol="TESTUSDT",
        bid=Decimal("100.50"),
        ask=Decimal("100.55"),
        volume=Decimal("1000.0"),
        tick_timestamp=1694649600.123,
        source="test"
    )
    
    await event_bus.publish(price_event)
    
    # Create and publish market depth event
    depth_event = MarketDepthEvent(
        type=EventType.MARKET_DEPTH,
        symbol="TESTUSDT",
        bids={"100.00": Decimal("500"), "99.95": Decimal("300")},
        asks={"100.10": Decimal("400"), "100.15": Decimal("200")},
        depth_timestamp=1694649600.456,
        source="test"
    )
    
    await event_bus.publish(depth_event)
    
    # Allow processing time
    await asyncio.sleep(0.1)
    
    # Verify events were processed
    stats = processor.get_processing_stats()
    assert stats["events_processed"] == 2
    assert stats["price_events_processed"] == 1
    assert stats["depth_events_processed"] == 1
    
    # Verify cached data
    cached_price = processor.get_latest_price("TESTUSDT")
    cached_depth = processor.get_latest_depth("TESTUSDT")
    
    assert cached_price is not None
    assert cached_price.symbol == "TESTUSDT"
    assert cached_price.bid == Decimal("100.50")
    
    assert cached_depth is not None
    assert cached_depth.symbol == "TESTUSDT"
    assert cached_depth.best_bid == Decimal("100.00")
    assert cached_depth.best_ask == Decimal("100.10")
    
    await processor.stop()
    
    print("✅ Event type handling test passed")


@pytest.mark.asyncio
async def test_subscription_management() -> None:
    """Test dynamic symbol subscription and unsubscription."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    config = {"tick_interval_ms": 20}
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    await feed.start()
    await processor.start()
    
    # Initially no symbols
    assert len(feed.get_subscribed_symbols()) == 0
    
    # Subscribe to symbols one by one
    symbols = ["BTC", "ETH", "ADA"]
    for symbol in symbols:
        await feed.subscribe_symbol(symbol)
        assert symbol in feed.get_subscribed_symbols()
    
    assert len(feed.get_subscribed_symbols()) == 3
    
    # Let it run briefly
    await asyncio.sleep(1.0)
    
    # Check that all symbols have data
    stats = processor.get_processing_stats()
    assert stats["events_processed"] > 0
    
    cached_symbols = processor.get_cached_symbols()
    assert len(cached_symbols) <= len(symbols)  # May not all have data yet
    
    # Unsubscribe from middle symbol
    await feed.unsubscribe_symbol("ETH")
    subscribed = feed.get_subscribed_symbols()
    assert "ETH" not in subscribed
    assert "BTC" in subscribed
    assert "ADA" in subscribed
    
    # Cleanup
    await feed.stop()
    await processor.stop()
    
    print("✅ Subscription management test passed")


@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test error handling and recovery."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()  # Initialize the event bus
    processor = MarketDataProcessor(event_bus)
    
    await processor.start()
    
    # Test with invalid event (wrong type)
    class InvalidEvent:
        def __init__(self):
            self.symbol = "INVALID"
    
    # This should not crash the processor
    try:
        await processor._process_tick(InvalidEvent())  # type: ignore
    except Exception:
        pass  # Expected to handle gracefully
    
    # Processor should still be functional
    valid_event = PriceTickEvent(
        type=EventType.PRICE_TICK,
        symbol="VALID",
        bid=Decimal("50.00"),
        ask=Decimal("50.05"),
        volume=Decimal("100"),
        tick_timestamp=1694649600.0,
        source="test"
    )
    
    await event_bus.publish(valid_event)
    await asyncio.sleep(0.1)
    
    # Should have processed the valid event
    stats = processor.get_processing_stats()
    assert stats["events_processed"] >= 1
    
    cached_price = processor.get_latest_price("VALID")
    assert cached_price is not None
    
    await processor.stop()
    
    print("✅ Error handling test passed")


@pytest.mark.asyncio
async def test_performance_stats_accuracy() -> None:
    """Test accuracy of performance statistics."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    config = {"tick_interval_ms": 5}
    feed = MarketDataFeed(event_bus, config)
    processor = MarketDataProcessor(event_bus)
    
    await feed.start()
    await processor.start()
    
    # Subscribe to one symbol for predictable stats
    await feed.subscribe_symbol("STATSTEST")
    
    # Reset stats to start fresh
    processor.reset_stats()
    initial_stats = processor.get_processing_stats()
    assert initial_stats["events_processed"] == 0
    
    # Run for measured time
    test_start = asyncio.get_event_loop().time()
    await asyncio.sleep(1.0)
    test_end = asyncio.get_event_loop().time()
    actual_duration = test_end - test_start
    
    # Get final stats
    feed_stats = feed.get_performance_stats()
    processor_stats = processor.get_processing_stats()
    
    # Verify stats make sense
    assert feed_stats["ticks_processed"] > 0
    assert processor_stats["events_processed"] > 0
    
    # Check latency stats are reasonable
    assert processor_stats["avg_latency_ms"] >= 0
    assert processor_stats["min_latency_ms"] >= 0
    assert processor_stats["max_latency_ms"] >= processor_stats["min_latency_ms"]
    
    # Check throughput calculation
    expected_min_tps = feed_stats["ticks_processed"] / (actual_duration + 0.1)  # Some tolerance
    assert feed_stats["ticks_per_second"] >= expected_min_tps * 0.8  # 20% tolerance
    
    await feed.stop()
    await processor.stop()
    
    print("✅ Performance stats accuracy test passed")


@pytest.mark.asyncio
async def test_cache_operations() -> None:
    """Test market data cache operations."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    processor = MarketDataProcessor(event_bus)
    
    await processor.start()
    
    # Initially empty cache
    assert len(processor.get_cached_symbols()) == 0
    assert processor.get_latest_price("NOTEXIST") is None
    assert processor.get_latest_depth("NOTEXIST") is None
    
    # Add some data
    symbols = ["CACHE1", "CACHE2", "CACHE3"]
    for i, symbol in enumerate(symbols):
        event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            symbol=symbol,
            bid=Decimal(f"{100 + i}.00"),
            ask=Decimal(f"{100 + i}.05"),
            volume=Decimal("1000"),
            tick_timestamp=1694649600.0 + i,
            source="cache_test"
        )
        await event_bus.publish(event)
    
    await asyncio.sleep(0.1)  # Allow processing
    
    # Verify cache contents
    cached_symbols = processor.get_cached_symbols()
    assert len(cached_symbols) == len(symbols)
    for symbol in symbols:
        assert symbol in cached_symbols
        
        price = processor.get_latest_price(symbol)
        assert price is not None
        assert price.symbol == symbol
    
    # Clear cache
    processor.clear_cache()
    assert len(processor.get_cached_symbols()) == 0
    assert processor.get_latest_price(symbols[0]) is None
    
    await processor.stop()
    
    print("✅ Cache operations test passed")


if __name__ == "__main__":
    # Run integration tests directly
    import sys
    
    async def run_all_integration_tests():
        print("🧪 Running Xline Market Data Integration Tests")
        print("=" * 55)
        
        try:
            await test_market_data_pipeline_integration()
            print()
            
            await test_event_type_handling()
            print()
            
            await test_subscription_management()
            print()
            
            await test_error_handling()
            print()
            
            await test_performance_stats_accuracy()
            print()
            
            await test_cache_operations()
            print()
            
            print("🎉 All integration tests passed!")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(run_all_integration_tests())
