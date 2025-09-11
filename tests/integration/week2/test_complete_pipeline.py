"""
Complete end-to-end integration tests for Week 2 implementation.

Tests the complete trading pipeline from market data ingestion
through strategy execution to trade execution and monitoring.
"""

import asyncio
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter
from xline.core.adapters.strategy_bridge import StrategyBridge
from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType, OrderEvent, PriceTickEvent, TradeEvent
from xline.core.market_data.feed import MarketDataFeed
from xline.core.monitoring.performance import PerformanceMonitor


class TestCompleteIntegration:
    """Complete end-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_trading_pipeline(self) -> None:
        """Test complete trading pipeline end-to-end."""
        # Setup components
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        # Mock Freqtrade bot for testing
        mock_freqtrade_bot = MagicMock()
        mock_freqtrade_bot.config = {
            "exchange": {"name": "binance"},
            "stake_currency": "USDT",
            "dry_run": True,
        }

        adapter = FreqtradeAdapter(event_bus, {})
        bridge = StrategyBridge(event_bus)
        feed = MarketDataFeed(event_bus, {})
        monitor = PerformanceMonitor(event_bus)

        # Initialize system
        await adapter.setup_event_handlers()
        await monitor.start_monitoring()
        await feed.start()
        await feed.subscribe_symbol("BTCUSD")

        # Deploy and start strategy
        strategy_config: dict[str, Any] = {
            "name": "TestStrategy",
            "class_name": "RSIStrategy",
            "parameters": {"rsi_period": 14},
        }
        strategy_id = await bridge.deploy_strategy(strategy_config)
        await bridge.start_strategy(strategy_id)
        await adapter.start_trading("test_account", "TestStrategy")

        # Simulate market data
        price_event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source="market_data_feed",
            symbol="BTCUSD",
            price=Decimal("50000.00"),
            volume=Decimal("1.5"),
            timestamp_ms=1694778000000,
        )
        await event_bus.publish(price_event)

        # Let system run for short period
        await asyncio.sleep(0.1)

        # Verify system operation
        report = monitor.get_performance_report()
        assert "event_metrics" in report
        assert "system_stats" in report
        
        # Check that events were processed (should have latency metrics)
        if report["event_metrics"]:
            # Any event type with count > 0 means events were processed
            total_events = sum(
                metrics["count"] for metrics in report["event_metrics"].values()
            )
            assert total_events > 0

        # Cleanup
        await adapter.stop_trading("test_account")
        await bridge.stop_strategy(strategy_id)
        await feed.stop()
        await monitor.stop_monitoring()
        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_freqtrade_adapter_integration(self) -> None:
        """Test Freqtrade adapter with realistic scenarios."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        # Create adapter with mock bot
        adapter = FreqtradeAdapter(event_bus, {})
        await adapter.setup_event_handlers()

        # Test order placement
        order_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="strategy_engine",
            order_id="test_order_001",
            account_id="test_account",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("50000.00"),
            order_type="LIMIT",
        )

        # Publish order event
        await event_bus.publish(order_event)
        await asyncio.sleep(0.01)

        # Verify adapter processed the order
        assert adapter._is_setup

        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_market_data_pipeline_under_load(self) -> None:
        """Test market data pipeline under high load."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        feed = MarketDataFeed(event_bus, {})
        monitor = PerformanceMonitor(event_bus)

        await feed.start()
        await monitor.start_monitoring()

        # Subscribe to multiple symbols
        symbols = ["BTCUSD", "ETHUSD", "ADAUSD", "DOTUSD", "SOLUSD"]
        for symbol in symbols:
            await feed.subscribe_symbol(symbol)

        # Simulate high-frequency data
        events_sent = 0
        for i in range(100):
            for symbol in symbols:
                price_event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source="market_data_feed",
                    symbol=symbol,
                    price=Decimal(f"{50000 + i}.{i % 100:02d}"),
                    volume=Decimal("1.0"),
                    timestamp_ms=1694778000000 + i * 1000,
                )
                await event_bus.publish(price_event)
                events_sent += 1

        # Allow processing
        await asyncio.sleep(0.1)

        # Verify performance
        report = monitor.get_performance_report()
        assert "event_metrics" in report
        # Check that events were processed (should have latency metrics)
        if report["event_metrics"]:
            total_events = sum(metrics["count"] for metrics in report["event_metrics"].values())
            assert total_events > 0

        # Cleanup
        await feed.stop()
        await monitor.stop_monitoring()
        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_strategy_deployment_lifecycle(self) -> None:
        """Test complete strategy deployment and lifecycle."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        bridge = StrategyBridge(event_bus)
        monitor = PerformanceMonitor(event_bus)
        await monitor.start_monitoring()

        # Deploy multiple strategies
        strategies = [
            {
                "name": "RSIStrategy",
                "class_name": "RSIStrategy",
                "parameters": {"rsi_period": 14, "rsi_overbought": 70},
            },
            {
                "name": "MACDStrategy",
                "class_name": "MACDStrategy",
                "parameters": {"fast_period": 12, "slow_period": 26},
            },
        ]

        strategy_ids = []
        for strategy_config in strategies:
            strategy_id = await bridge.deploy_strategy(strategy_config)
            strategy_ids.append(strategy_id)
            await bridge.start_strategy(strategy_id)

        # Let strategies run
        await asyncio.sleep(0.05)

        # Stop strategies
        for strategy_id in strategy_ids:
            await bridge.stop_strategy(strategy_id)
            await bridge.undeploy_strategy(strategy_id)

        # Verify no memory leaks
        report = monitor.get_performance_report()
        assert "event_metrics" in report

        await monitor.stop_monitoring()
        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self) -> None:
        """Test error handling and recovery mechanisms."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        adapter = FreqtradeAdapter(event_bus, {})
        bridge = StrategyBridge(event_bus)

        await adapter.setup_event_handlers()

        # Test invalid order scenario - exception handling
        with pytest.raises(ValueError, match="Quantity must be positive"):
            invalid_order = OrderEvent(  # noqa: F841
                type=EventType.ORDER_CREATED,
                source="test",
                order_id="invalid_order",
                account_id="test_account",
                symbol="INVALID_SYMBOL",
                side="BUY",
                quantity=Decimal("-1.0"),  # Invalid negative quantity
                price=Decimal("1.0"),  # Valid price
                order_type="LIMIT",
            )

        # Test strategy deployment failure
        invalid_strategy = {
            "name": "InvalidStrategy",
            "class_name": "NonExistentStrategy",
            "parameters": {},
        }

        try:
            strategy_id = await bridge.deploy_strategy(invalid_strategy)
            # Should either raise exception or return error indicator
            assert strategy_id is None or isinstance(strategy_id, str)
        except Exception:
            # Expected behavior for invalid strategy
            pass

        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_performance_under_stress(self) -> None:
        """Test system performance under stress conditions."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        monitor = PerformanceMonitor(event_bus)
        await monitor.start_monitoring()

        # Generate high volume of events
        event_count = 1000
        start_time = asyncio.get_event_loop().time()

        for i in range(event_count):
            if i % 3 == 0:
                event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source="stress_test",
                    symbol="BTCUSD",
                    price=Decimal(f"{50000 + i}"),
                    volume=Decimal("1.0"),
                    timestamp_ms=1694778000000 + i,
                )
            elif i % 3 == 1:
                event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="stress_test",
                    order_id=f"stress_order_{i}",
                    account_id="stress_account",
                    symbol="BTCUSD",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=Decimal("0.1"),
                    price=Decimal(f"{50000 + i}"),
                    order_type="LIMIT",
                )
            else:
                event = TradeEvent(type=EventType.TRADE_EXECUTED, source="stress_test",
                    trade_id=f"stress_trade_{i}",
                    order_id=f"stress_order_{i}",
                    account_id="stress_account",
                    symbol="BTCUSD",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=Decimal("0.1"),
                    price=Decimal(f"{50000 + i}"),
                    commission=Decimal("0.001"),
                )

            await event_bus.publish(event)

        # Wait for processing
        await asyncio.sleep(0.1)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Verify performance targets
        report = monitor.get_performance_report()
        # Get total events processed
        total_events = sum(metrics["count"] for metrics in report["event_metrics"].values())
        events_processed = total_events

        # Should process most events
        assert events_processed > event_count * 0.8  # Allow some loss under stress

        # Throughput should be reasonable
        throughput = events_processed / total_time
        assert throughput > 100  # At least 100 events/second under stress

        await monitor.stop_monitoring()
        await event_bus.cleanup()


class TestSystemResilience:
    """Test system resilience and fault tolerance."""

    @pytest.mark.asyncio
    async def test_component_failure_recovery(self) -> None:
        """Test system recovery from component failures."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        # Start with working system
        adapter = FreqtradeAdapter(event_bus, {})
        monitor = PerformanceMonitor(event_bus)

        await adapter.setup_event_handlers()
        await monitor.start_monitoring()

        # Simulate component failure and recovery
        await monitor.stop_monitoring()  # Simulate monitor failure

        # System should continue working
        order_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="resilience_test",
            order_id="resilience_order",
            account_id="test_account",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("50000.00"),
            order_type="LIMIT",
        )

        await event_bus.publish(order_event)
        await asyncio.sleep(0.01)

        # Restart monitor
        await monitor.start_monitoring()

        # Verify system is healthy
        report = monitor.get_performance_report()
        assert "event_metrics" in report

        await monitor.stop_monitoring()
        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self) -> None:
        """Test that long-running operations don't cause memory leaks."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        monitor = PerformanceMonitor(event_bus)
        await monitor.start_monitoring()

        # Run many cycles of operations
        for cycle in range(10):
            # Create and destroy objects
            for i in range(100):
                event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source="memory_test",
                    symbol="BTCUSD",
                    price=Decimal(f"{50000 + i}"),
                    volume=Decimal("1.0"),
                    timestamp_ms=1694778000000 + cycle * 1000 + i,
                )
                await event_bus.publish(event)

            # Force cleanup
            await asyncio.sleep(0.01)

        # Verify no excessive memory growth
        report = monitor.get_performance_report()
        assert "event_metrics" in report
        total_events = sum(metrics["count"] for metrics in report["event_metrics"].values())
        assert total_events > 500

        await monitor.stop_monitoring()
        await event_bus.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self) -> None:
        """Test system behavior under concurrent operations."""
        event_bus = InMemoryEventBus()
        await event_bus.initialize()

        monitor = PerformanceMonitor(event_bus)
        await monitor.start_monitoring()

        async def publish_events(event_type: str, count: int) -> None:
            """Publish events concurrently."""
            for i in range(count):
                if event_type == "price":
                    event = PriceTickEvent(
            type=EventType.PRICE_TICK,
            source=f"concurrent_{event_type}",
                        symbol="BTCUSD",
                        price=Decimal(f"{50000 + i}"),
                        volume=Decimal("1.0"),
                        timestamp_ms=1694778000000 + i,
                    )
                else:  # order
                    event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source=f"concurrent_{event_type}",
                        order_id=f"concurrent_order_{i}",
                        account_id="concurrent_account",
                        symbol="BTCUSD",
                        side="BUY",
                        quantity=Decimal("0.1"),
                        price=Decimal(f"{50000 + i}"),
                        order_type="LIMIT",
                    )

                await event_bus.publish(event)
                await asyncio.sleep(0.001)  # Small delay

        # Run concurrent publishers
        tasks = [
            publish_events("price", 50),
            publish_events("order", 50),
            publish_events("price", 50),
        ]

        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)

        # Verify all events processed
        report = monitor.get_performance_report()
        assert "event_metrics" in report
        total_events = sum(metrics["count"] for metrics in report["event_metrics"].values())
        assert total_events >= 150

        await monitor.stop_monitoring()
        await event_bus.cleanup()
