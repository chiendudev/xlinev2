#!/usr/bin/env python3
"""
Xline Performance     def __init__(self, event_bus: InMemoryEventBus) -> None:
        self.event_bus = event_bus
        self.subscription_id: str | None = None
        self.events_processed = 0hmark Script

Comprehensive performance validation for the Xline trading system,
testing all mandatory requirements including:
- Event latency <1ms (P99)
- Memory usage <500MB under load  
- Throughput >1000 events/sec
- Memory optimization with event pooling
"""

import asyncio
import time
import psutil
import statistics
import gc
import random
import sys
from decimal import Decimal
from typing import Any, Optional
from datetime import datetime

# Import all monitoring components
from xline.core.monitoring import (
    PerformanceMonitor,
    MemoryMonitor, 
    MetricsCollector,
    EventPool,
    OptimizedEventBus
)

# Import event system
from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import OrderEvent, EventType, OrderSide, OrderType, OrderStatus, Event

import structlog

# Configure structured logging
logging = structlog.get_logger(__name__)


class MarketDataFeed:
    """Simulates market data feed for benchmarking"""
    
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        self.event_bus = event_bus
        self.is_running = False
        self._task: Optional[asyncio.Task[None]] = None
        self.subscription_id: Optional[str] = None
        self.events_generated = 0
        self.running = False
        self.start_time = 0.0
        self.feed_task: Optional[asyncio.Task[None]] = None
    
    async def start(self) -> None:
        """Start the market data feed."""
        self.running = True
        self.start_time = time.perf_counter()
        self.feed_task = asyncio.create_task(self._generate_data())
    
    async def stop(self) -> None:
        """Stop the feed."""
        self.running = False
        if hasattr(self, 'feed_task') and self.feed_task:
            self.feed_task.cancel()
            try:
                await self.feed_task
            except asyncio.CancelledError:
                pass
    
    async def _generate_data(self) -> None:
        """Generate market data events."""
        interval = 0.01  # 10ms interval for high-frequency simulation
        
        while self.running:
            # Generate price tick event
            tick_event = OrderEvent(
                type=EventType.ORDER_CREATED,
                source="market_data_feed",
                order_id=f"order_{random.randint(1000, 9999)}",
                account_id="test_account",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal(str(random.uniform(0.1, 10.0))),
                price=Decimal(str(random.uniform(50000, 70000))),
                order_type=OrderType.LIMIT,
                status=OrderStatus.PENDING
            )
            await self.event_bus.publish(tick_event)
            self.events_generated += 1
            
            # Generate depth update occasionally
            if self.events_generated % 10 == 0:
                depth_event = OrderEvent(
                    type=EventType.ORDER_CREATED,
                    source="market_data_feed",
                    order_id=f"order_{random.randint(2000, 2999)}",
                    account_id="test_account",
                    symbol='BTCUSD',
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal('1.0'),
                    price=Decimal('50001.0'),
                    status=OrderStatus.PENDING
                )
                await self.event_bus.publish(depth_event)
                self.events_generated += 1
            
            await asyncio.sleep(interval)
    
    def get_performance_stats(self) -> dict[str, Any]:
        """Get feed performance statistics."""
        duration = time.perf_counter() - self.start_time if self.start_time > 0 else 0
        rate = self.events_generated / duration if duration > 0 else 0
        
        return {
            "events_generated": self.events_generated,
            "duration_seconds": duration,
            "generation_rate": rate
        }


class MarketDataProcessor:
    """Simulated market data processor for benchmarking."""
    
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        self.event_bus = event_bus
        self.running = False
        self.ticks_processed = 0
        self.depth_processed = 0
        self.start_time = 0.0
        self.subscription_id_tick: str | None = None
        self.subscription_id_depth: str | None = None
        
    async def start(self) -> None:
        """Start the market data processor."""
        self.running = True
        self.start_time = time.perf_counter()
        self.subscription_id_tick = await self.event_bus.subscribe("market_data.price_tick", self._process_tick)
        self.subscription_id_depth = await self.event_bus.subscribe("market_data.depth", self._process_depth)
        
    async def stop(self) -> None:
        """Stop the market data processor."""
        self.running = False
        if self.subscription_id_tick:
            await self.event_bus.unsubscribe(self.subscription_id_tick)
        if self.subscription_id_depth:
            await self.event_bus.unsubscribe(self.subscription_id_depth)
        
    async def _process_tick(self, event: Event) -> None:
        """Process price tick event."""
        self.ticks_processed += 1
        # Simulated processing work
        await asyncio.sleep(0.0001)  # 0.1ms processing time
        
    async def _process_depth(self, event: Event) -> None:
        """Process depth update event."""
        self.depth_processed += 1
        # Simulated processing work
        await asyncio.sleep(0.0002)  # 0.2ms processing time
    
    def get_performance_stats(self) -> dict[str, Any]:
        """Get processor performance statistics."""
        duration = time.perf_counter() - self.start_time if self.start_time > 0 else 0
        total_processed = self.ticks_processed + self.depth_processed
        rate = total_processed / duration if duration > 0 else 0
        
        return {
            "ticks_processed": self.ticks_processed,
            "depth_processed": self.depth_processed,
            "total_processed": total_processed,
            "duration_seconds": duration,
            "processing_rate": rate
        }


async def run_latency_benchmark() -> dict[str, Any]:
    """
    Run comprehensive latency benchmark test.
    
    Returns:
        Latency benchmark results
    """
    print("🚀 Running Latency Benchmark...")
    
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    await monitor.start_monitoring()
    
    try:
        # High-frequency event publishing
        start_time = time.perf_counter()
        
        for i in range(10000):
            event = OrderEvent(
                type=EventType.ORDER_CREATED,
                source="latency_benchmark",
                order_id=f"bench_{i}",
                account_id="BENCH_ACCOUNT",
                symbol=f"BENCH_{i % 10}USD",
                side="BUY",
                quantity=Decimal("1000.0"),
                price=Decimal("50000.00") + Decimal(str(i * 0.01)),
                order_type="LIMIT"
            )
            await event_bus.publish(event)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Allow processing to complete
        await asyncio.sleep(0.5)
        
        report = monitor.get_performance_report()
        
        results = {
            "total_events": 10000,
            "total_time_seconds": total_time,
            "events_per_second": 10000 / total_time,
            "avg_event_time_ms": (total_time / 10000) * 1000,
            "performance_report": report
        }
        
        print(f"   ✅ Events/second: {results['events_per_second']:.0f}")
        print(f"   ✅ Avg event time: {results['avg_event_time_ms']:.3f}ms")
        
        for event_type, metrics in report["event_metrics"].items():
            print(f"   ✅ {event_type} P99 latency: {metrics['p99_latency_ms']:.3f}ms")
            
        return results
        
    finally:
        await monitor.stop_monitoring()


async def run_memory_benchmark() -> dict[str, Any]:
    """
    Run memory optimization benchmark test.
    
    Returns:
        Memory benchmark results
    """
    print("🚀 Running Memory Optimization Benchmark...")
    
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    # Test without optimization
    monitor1 = PerformanceMonitor(event_bus)
    await monitor1.start_monitoring()
    
    baseline_start = time.perf_counter()
    for i in range(5000):
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="baseline_memory",
            order_id=f"baseline_{i}",
            account_id="BASELINE_ACCOUNT",
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal("1.0"),
            price=Decimal("50000.00"),
            order_type="MARKET"
        )
        await event_bus.publish(event)
    
    baseline_time = time.perf_counter() - baseline_start
    baseline_report = monitor1.get_performance_report()
    await monitor1.stop_monitoring()
    
    # Test with optimization
    optimized_bus = OptimizedEventBus(event_bus, pool_size=1000)
    monitor2 = PerformanceMonitor(event_bus)
    
    await monitor2.start_monitoring()
    optimized_bus.memory_monitor.start_monitoring()
    
    optimized_start = time.perf_counter()
    for i in range(5000):
        await optimized_bus.publish_optimized(
            EventType.TRADE_EXECUTED,
            {"trade_id": f"optimized_{i}", "price": Decimal("50000.00")},
            "optimized_memory"
        )
    
    optimized_time = time.perf_counter() - optimized_start
    optimized_report = monitor2.get_performance_report()
    optimization_stats = optimized_bus.get_optimization_stats()
    
    await monitor2.stop_monitoring()
    optimized_bus.memory_monitor.stop_monitoring()
    
    results = {
        "baseline_time": baseline_time,
        "optimized_time": optimized_time,
        "improvement_percent": ((baseline_time - optimized_time) / baseline_time) * 100,
        "baseline_memory": baseline_report["system_stats"].get("memory_used_mb", 0),
        "optimized_memory": optimized_report["system_stats"].get("memory_used_mb", 0),
        "pool_stats": optimization_stats["event_pool"],
        "memory_stats": optimization_stats["memory_stats"]
    }
    
    print(f"   ✅ Baseline time: {baseline_time:.3f}s")
    print(f"   ✅ Optimized time: {optimized_time:.3f}s")
    print(f"   ✅ Improvement: {results['improvement_percent']:.1f}%")
    print(f"   ✅ Pool utilization: {results['pool_stats']['pool_size']}/{results['pool_stats']['pool_capacity']}")
    
    return results


async def run_market_data_benchmark() -> dict[str, Any]:
    """
    Run market data pipeline benchmark test.
    
    Returns:
        Market data benchmark results
    """
    print("🚀 Running Market Data Pipeline Benchmark...")
    
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    
    monitor = PerformanceMonitor(event_bus)
    memory_monitor = MemoryMonitor()
    
    await monitor.start_monitoring()
    memory_monitor.start_monitoring()
    
    try:
        # Initialize market data components
        feed = MarketDataFeed(event_bus)
        processor = MarketDataProcessor(event_bus)
        
        await processor.start()
        await feed.start()
        
        # Run for benchmark duration
        benchmark_duration = 5.0  # 5 seconds
        
        await asyncio.sleep(benchmark_duration)
        
        # Stop components
        await feed.stop()
        await processor.stop()
        
        # Collect final metrics
        performance_report = monitor.get_performance_report()
        memory_stats = memory_monitor.get_memory_stats()
        feed_stats = feed.get_performance_stats()
        processor_stats = processor.get_performance_stats()
        
        total_events = sum(m["count"] for m in performance_report["event_metrics"].values())
        throughput = total_events / benchmark_duration
        
        results = {
            "duration_seconds": benchmark_duration,
            "total_events": total_events,
            "throughput_events_per_second": throughput,
            "feed_stats": feed_stats,
            "processor_stats": processor_stats,
            "performance_report": performance_report,
            "memory_stats": memory_stats
        }
        
        print(f"   ✅ Duration: {benchmark_duration}s")
        print(f"   ✅ Total events: {total_events}")
        print(f"   ✅ Throughput: {throughput:.0f} events/sec")
        print(f"   ✅ Feed performance: {feed_stats}")
        print(f"   ✅ Processor performance: {processor_stats}")
        
        return results
        
    finally:
        await monitor.stop_monitoring()
        memory_monitor.stop_monitoring()


async def run_comprehensive_benchmark() -> dict[str, Any]:
    """
    Run comprehensive system benchmark covering all performance aspects.
    
    Returns:
        Complete benchmark results
    """
    print("=" * 60)
    print("🎯 XLINE PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)
    
    results = {}
    
    # Run individual benchmarks
    results["latency"] = await run_latency_benchmark()
    print()
    
    results["memory"] = await run_memory_benchmark()
    print()
    
    results["market_data"] = await run_market_data_benchmark()
    print()
    
    # Overall analysis
    print("=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)
    
    # Latency analysis
    latency_metrics = results["latency"]["performance_report"]["event_metrics"]
    max_p99_latency = max(m["p99_latency_ms"] for m in latency_metrics.values())
    
    print("🎯 Latency Performance:")
    print(f"   • Maximum P99 latency: {max_p99_latency:.3f}ms")
    print(f"   • Target <1ms: {'✅ PASS' if max_p99_latency < 1.0 else '❌ FAIL'}")
    print(f"   • Event throughput: {results['latency']['events_per_second']:.0f}/sec")
    
    # Memory analysis
    memory_improvement = results["memory"]["improvement_percent"]
    pool_efficiency = results["memory"]["pool_stats"]["pool_size"] / results["memory"]["pool_stats"]["pool_capacity"] * 100
    
    print("🎯 Memory Optimization:")
    print(f"   • Performance improvement: {memory_improvement:.1f}%")
    print(f"   • Pool efficiency: {pool_efficiency:.1f}%")
    print(f"   • Memory target <500MB: {'✅ PASS' if results['memory']['optimized_memory'] < 500 else '❌ FAIL'}")
    
    # Market data analysis
    market_throughput = results["market_data"]["throughput_events_per_second"]
    
    print("🎯 Market Data Pipeline:")
    print(f"   • Throughput: {market_throughput:.0f} events/sec")
    print(f"   • Target >1000/sec: {'✅ PASS' if market_throughput > 1000 else '❌ FAIL'}")
    print(f"   • Total events processed: {results['market_data']['total_events']}")
    
    # Overall assessment
    latency_pass = max_p99_latency < 1.0
    memory_pass = results["memory"]["optimized_memory"] < 500
    throughput_pass = market_throughput > 1000
    
    overall_pass = latency_pass and memory_pass and throughput_pass
    
    print("🎯 Overall Performance:")
    print(f"   • All targets met: {'✅ PASS' if overall_pass else '❌ FAIL'}")
    print(f"   • System ready for production: {'✅ YES' if overall_pass else '❌ NO'}")
    
    results["summary"] = {
        "latency_pass": latency_pass,
        "memory_pass": memory_pass,
        "throughput_pass": throughput_pass,
        "overall_pass": overall_pass,
        "max_p99_latency_ms": max_p99_latency,
        "memory_usage_mb": results["memory"]["optimized_memory"],
        "market_throughput": market_throughput
    }
    
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    print("Starting Xline Performance Benchmark...")
    
    try:
        results = asyncio.run(run_comprehensive_benchmark())
        
        # Exit with appropriate code
        if results["summary"]["overall_pass"]:
            print("✅ All benchmarks passed - system ready for production!")
            sys.exit(0)
        else:
            print("❌ Some benchmarks failed - optimization needed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
