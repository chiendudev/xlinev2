"""
LOAD TESTING - NGÀY 5 (Task 1.15)
File: tests/load/test_event_bus_load.py

TUÂN THỦ NGHIÊM NGẶT:
- Concurrent publishers và subscribers
- Stress test với Redis và NATS  
- Memory leak detection
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md
"""

import asyncio
import pytest
import time
import psutil
import gc
import threading
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import (
    EventType, OrderEvent, TradeEvent, RiskEvent, AccountEvent, SystemEvent,
    OrderSide, OrderType, RiskSeverity
)


class LoadTestMetrics:
    """Collect load testing metrics"""
    
    def __init__(self):
        self.total_events_published = 0
        self.total_events_processed = 0
        self.failed_publishes = 0
        self.processing_errors = 0
        self.start_time = None
        self.end_time = None
        self.memory_samples = []
        self.throughput_samples = []
        self.concurrent_publishers = 0
        self.concurrent_subscribers = 0
        self.lock = threading.Lock()
        
    def start_test(self, publishers, subscribers):
        """Start load test monitoring"""
        self.start_time = time.time()
        self.concurrent_publishers = publishers
        self.concurrent_subscribers = subscribers
        gc.collect()
        
    def record_publish(self, success=True):
        """Record a publish attempt"""
        with self.lock:
            self.total_events_published += 1
            if not success:
                self.failed_publishes += 1
                
    def record_processing(self, success=True):
        """Record event processing"""
        with self.lock:
            self.total_events_processed += 1
            if not success:
                self.processing_errors += 1
                
    def sample_metrics(self):
        """Sample current system metrics"""
        current_time = time.time()
        if self.start_time:
            elapsed = current_time - self.start_time
            throughput = self.total_events_processed / elapsed if elapsed > 0 else 0
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            
            with self.lock:
                self.throughput_samples.append((elapsed, throughput))
                self.memory_samples.append((elapsed, memory_mb))
                
    def finish_test(self):
        """Finish load test"""
        self.end_time = time.time()
        
    def get_summary(self):
        """Get test summary"""
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        avg_throughput = self.total_events_processed / duration if duration > 0 else 0
        success_rate = (self.total_events_published - self.failed_publishes) / self.total_events_published if self.total_events_published > 0 else 0
        
        return {
            'duration': duration,
            'total_published': self.total_events_published,
            'total_processed': self.total_events_processed,
            'failed_publishes': self.failed_publishes,
            'processing_errors': self.processing_errors,
            'success_rate': success_rate * 100,
            'avg_throughput': avg_throughput,
            'concurrent_publishers': self.concurrent_publishers,
            'concurrent_subscribers': self.concurrent_subscribers
        }


class ConcurrentLoadTestHandler:
    """Handler for concurrent load testing"""
    
    def __init__(self, handler_id, metrics, should_fail_rate=0.0):
        self.handler_id = handler_id
        self.metrics = metrics
        self.should_fail_rate = should_fail_rate
        self.processed_count = 0
        self.error_count = 0
        
    async def handle(self, event):
        """Handle event with configurable failure rate"""
        import random
        
        try:
            # Simulate processing failure with random chance
            if self.should_fail_rate > 0 and random.random() < self.should_fail_rate:
                self.error_count += 1
                self.metrics.record_processing(success=False)
                raise Exception(f"Simulated processing failure in handler {self.handler_id}")
                
            # Simulate some processing work
            await asyncio.sleep(0.001)  # 1ms processing time
            
            self.processed_count += 1
            self.metrics.record_processing(success=True)
            
        except Exception:
            self.error_count += 1
            self.metrics.record_processing(success=False)
            raise


class MockRedisEventBusLoad:
    """Mock Redis Event Bus for load testing"""
    
    def __init__(self, failure_rate=0.0, latency_ms=1):
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.is_initialized = False
        self.published_count = 0
        self.subscribers = {}
        self.publish_failures = 0
        
    async def initialize(self):
        """Initialize mock Redis bus"""
        if self.failure_rate > 0.5:  # High failure rate means initialization fails
            raise ConnectionError("Redis initialization failed")
        self.is_initialized = True
        
    async def close(self):
        """Close mock Redis bus"""
        self.is_initialized = False
        
    async def publish(self, event_type, event):
        """Publish with simulated failure and latency"""
        import random
        
        if not self.is_initialized:
            raise ConnectionError("Redis not initialized")
            
        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Simulate publish failures with random chance
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            self.publish_failures += 1
            raise ConnectionError("Redis publish failed")
            
        self.published_count += 1
        
        # Simulate delivering to subscribers
        if event_type in self.subscribers:
            await self.subscribers[event_type].handle(event)
            
    async def subscribe(self, event_type, handler):
        """Subscribe to events"""
        if not self.is_initialized:
            raise ConnectionError("Redis not initialized")
        self.subscribers[event_type] = handler
        return f"redis_sub_{id(handler)}"
        
    async def health_check(self):
        """Health check"""
        return self.is_initialized and self.failure_rate < 0.8


class MockNATSEventBusLoad:
    """Mock NATS Event Bus for load testing"""
    
    def __init__(self, failure_rate=0.0, latency_ms=2):
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.is_initialized = False
        self.published_count = 0
        self.subscribers = {}
        self.publish_failures = 0
        
    async def initialize(self):
        """Initialize mock NATS bus"""
        if self.failure_rate > 0.5:
            raise ConnectionError("NATS initialization failed")
        self.is_initialized = True
        
    async def close(self):
        """Close mock NATS bus"""
        self.is_initialized = False
        
    async def publish(self, event_type, event):
        """Publish with NATS simulation"""
        if not self.is_initialized:
            raise ConnectionError("NATS not initialized")
            
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        if self.failure_rate > 0 and (self.published_count % int(1/self.failure_rate)) == 0:
            self.publish_failures += 1
            raise ConnectionError("NATS publish failed")
            
        self.published_count += 1
        
        if event_type in self.subscribers:
            await self.subscribers[event_type].handle(event)
            
    async def subscribe(self, event_type, handler):
        """Subscribe to NATS events"""
        if not self.is_initialized:
            raise ConnectionError("NATS not initialized")
        self.subscribers[event_type] = handler
        return f"nats_sub_{id(handler)}"
        
    async def health_check(self):
        """NATS health check"""
        return self.is_initialized and self.failure_rate < 0.8

@pytest.mark.asyncio
@pytest.mark.load
class TestEventBusLoad:
    """Load testing for event bus - MANDATORY REQUIREMENTS"""
    
    async def test_concurrent_publishers_subscribers(self):
        """
        MANDATORY: Concurrent publishers và subscribers
        Test multiple publishers and subscribers operating simultaneously
        """
        bus = InMemoryEventBus()
        await bus.initialize()
        
        metrics = LoadTestMetrics()
        
        # Create multiple handlers
        num_subscribers = 5
        handlers = []
        for i in range(num_subscribers):
            handler = ConcurrentLoadTestHandler(f"handler_{i}", metrics)
            handlers.append(handler)
            await bus.subscribe(EventType.ORDER_CREATED.value, handler)
            await bus.subscribe(EventType.TRADE_EXECUTED.value, handler)
            
        metrics.start_test(publishers=10, subscribers=num_subscribers)
        
        # Concurrent publisher function
        async def publisher_worker(publisher_id, events_per_publisher):
            """Individual publisher worker"""
            for i in range(events_per_publisher):
                try:
                    event = OrderEvent(
                        type=EventType.ORDER_CREATED,
                        source=f"publisher_{publisher_id}",
                        order_id=f"load-order-{publisher_id}-{i}",
                        account_id=f"account-{publisher_id}",
                        symbol="BTC/USD",
                        side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=Decimal("1.0"),
                        price=Decimal(f"{50000 + i}")
                    )
                    
                    result = await bus.publish(event)
                    metrics.record_publish(success=result.success)
                    
                    # Vary publishing rate
                    await asyncio.sleep(0.001 + (publisher_id * 0.0005))
                    
                except Exception:
                    metrics.record_publish(success=False)
                    
        # Start concurrent publishers
        num_publishers = 10
        events_per_publisher = 500
        
        publisher_tasks = []
        for pub_id in range(num_publishers):
            task = asyncio.create_task(publisher_worker(pub_id, events_per_publisher))
            publisher_tasks.append(task)
            
        # Monitor metrics during execution
        async def metrics_monitor():
            """Monitor metrics during load test"""
            for _ in range(30):  # Monitor for 30 seconds
                await asyncio.sleep(1.0)
                metrics.sample_metrics()
                
        monitor_task = asyncio.create_task(metrics_monitor())
        
        # Wait for all publishers to complete
        await asyncio.gather(*publisher_tasks)
        
        # Wait for processing to complete
        await asyncio.sleep(5.0)
        
        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
        metrics.finish_test()
        
        summary = metrics.get_summary()
        
        print(f"\n=== CONCURRENT LOAD TEST RESULTS ===")
        print(f"Duration: {summary['duration']:.2f}s")
        print(f"Publishers: {summary['concurrent_publishers']}")
        print(f"Subscribers: {summary['concurrent_subscribers']}")
        print(f"Events Published: {summary['total_published']}")
        print(f"Events Processed: {summary['total_processed']}")
        print(f"Failed Publishes: {summary['failed_publishes']}")
        print(f"Processing Errors: {summary['processing_errors']}")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        print(f"Average Throughput: {summary['avg_throughput']:.2f} EPS")
        
        # MANDATORY ASSERTIONS
        assert summary['success_rate'] >= 95.0, f"Success rate too low: {summary['success_rate']:.2f}%"
        assert summary['avg_throughput'] >= 1000, f"Throughput too low: {summary['avg_throughput']:.2f} EPS"
        assert summary['total_processed'] >= summary['total_published'] * 0.95, "Too many events lost"
        
        # Verify all handlers processed events
        total_handler_processed = sum(h.processed_count for h in handlers)
        expected_total = summary['total_published'] * num_subscribers  # Each event goes to all subscribers
        assert total_handler_processed >= expected_total * 0.95, "Handler processing loss detected"
        
        await bus.cleanup()

    async def test_stress_with_redis_nats_simulation(self):
        """
        MANDATORY: Stress test với Redis và NATS
        Simulate Redis/NATS behavior under high load
        """
        # Test Redis simulation under stress
        redis_bus = MockRedisEventBusLoad(failure_rate=0.02, latency_ms=2)  # 2% failure, 2ms latency
        await redis_bus.initialize()
        
        metrics = LoadTestMetrics()
        handler = ConcurrentLoadTestHandler("redis_handler", metrics, should_fail_rate=0.01)
        
        await redis_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        metrics.start_test(publishers=20, subscribers=1)
        
        # High-stress event generation
        stress_events = 2000
        batch_size = 50
        
        for batch_num in range(stress_events // batch_size):
            batch_tasks = []
            
            for i in range(batch_size):
                event_id = batch_num * batch_size + i
                
                event = OrderEvent(
                    type=EventType.ORDER_CREATED,
                    source=f"stress_test_{event_id}",
                    order_id=f"stress-order-{event_id}",
                    account_id="stress-account",
                    symbol="BTC/USD",
                    side=OrderSide.BUY if event_id % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=Decimal("1.0"),
                    price=Decimal(f"{50000 + (event_id % 1000)}")
                )
                
                async def publish_with_retry(event_to_publish):
                    """Publish with retry logic"""
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await redis_bus.publish(EventType.ORDER_CREATED, event_to_publish)
                            metrics.record_publish(success=True)
                            return
                        except Exception:
                            if attempt == max_retries - 1:
                                metrics.record_publish(success=False)
                            else:
                                await asyncio.sleep(0.01 * (attempt + 1))  # Exponential backoff

                task = asyncio.create_task(publish_with_retry(event))
                batch_tasks.append(task)
                
            # Execute batch
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Sample metrics every 10 batches
            if batch_num % 10 == 0:
                metrics.sample_metrics()
                
            # Brief pause between batches
            await asyncio.sleep(0.01)
            
        metrics.finish_test()
        
        summary = metrics.get_summary()
        
        print(f"\n=== REDIS STRESS TEST RESULTS ===")
        print(f"Duration: {summary['duration']:.2f}s")
        print(f"Events Published: {summary['total_published']}")
        print(f"Events Processed: {summary['total_processed']}")
        print(f"Redis Publish Failures: {redis_bus.publish_failures}")
        print(f"Handler Errors: {handler.error_count}")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        print(f"Throughput: {summary['avg_throughput']:.2f} EPS")
        
        # STRESS TEST ASSERTIONS
        assert summary['success_rate'] >= 90.0, f"Redis stress test success rate too low: {summary['success_rate']:.2f}%"
        assert summary['avg_throughput'] >= 500, f"Redis stress throughput too low: {summary['avg_throughput']:.2f} EPS"
        assert redis_bus.published_count >= stress_events * 0.9, "Too many Redis publish failures"
        
        await redis_bus.close()

    async def test_memory_leak_detection_under_load(self):
        """
        MANDATORY: Memory leak detection
        Detect memory leaks under sustained high load
        """
        bus = InMemoryEventBus()
        await bus.initialize()
        
        # Baseline memory measurement
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        print(f"Initial Memory: {initial_memory:.2f}MB")
        
        # Create handlers that might cause memory leaks
        handlers = []
        for i in range(20):  # Many handlers to stress memory
            handler = ConcurrentLoadTestHandler(f"leak_handler_{i}", LoadTestMetrics())
            handlers.append(handler)
            await bus.subscribe(EventType.ORDER_CREATED, handler)
            await bus.subscribe(EventType.TRADE_EXECUTED, handler)
            await bus.subscribe(EventType.RISK_LIMIT_BREACHED, handler)  # Fixed event type
            
        memory_samples = []
        
        # Run sustained load for memory leak detection
        load_duration = 180  # 3 minutes of sustained load
        events_per_second = 200
        
        start_time = time.time()
        event_counter = 0
        
        while time.time() - start_time < load_duration:
            batch_start = time.time()
            
            # Generate mixed event types
            batch_tasks = []
            for i in range(20):  # 20 events per batch
                event_type_selector = event_counter % 3
                
                if event_type_selector == 0:
                    event = OrderEvent(
                        type=EventType.ORDER_CREATED,
                        source=f"leak_test_{event_counter}",
                        order_id=f"leak-order-{event_counter}",
                        account_id="leak-account",
                        symbol="BTC/USD",
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=Decimal("1.0"),
                        price=Decimal("50000.0")
                    )
                elif event_type_selector == 1:
                    event = TradeEvent(
                        type=EventType.TRADE_EXECUTED,
                        source=f"leak_test_{event_counter}",
                        trade_id=f"leak-trade-{event_counter}",
                        order_id=f"leak-order-{event_counter}",
                        account_id="leak-account",
                        symbol="BTC/USD",
                        side=OrderSide.BUY,
                        quantity=Decimal("1.0"),
                        price=Decimal("50000.0"),
                        fee=Decimal("10.0"),
                        commission=Decimal("5.0")
                    )
                else:
                    event = RiskEvent(
                        type=EventType.RISK_LIMIT_BREACHED,
                        source=f"leak_test_{event_counter}",
                        account_id="leak-account",
                        rule_type="memory_leak_test",  # Changed from risk_type to rule_type
                        severity=RiskSeverity.LOW,
                        message=f"Memory leak test event {event_counter}",
                        threshold=Decimal("1000.0"),
                        current_value=Decimal("1500.0")
                    )
                
                task = asyncio.create_task(bus.publish(event))  # Use correct API
                batch_tasks.append(task)
                event_counter += 1
                
            await asyncio.gather(*batch_tasks)
            
            # Sample memory every 30 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0 and len(memory_samples) < int(elapsed // 30):
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append((elapsed, current_memory))
                print(f"  {elapsed:.0f}s: {current_memory:.2f}MB (events: {event_counter})")
                
            # Rate limiting
            batch_duration = time.time() - batch_start
            target_batch_duration = 20 / events_per_second  # 20 events per batch
            if batch_duration < target_batch_duration:
                await asyncio.sleep(target_batch_duration - batch_duration)
                
        # Final processing wait
        await asyncio.sleep(10.0)
        
        # Memory leak analysis
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        
        # Calculate memory growth rate
        if len(memory_samples) >= 2:
            memory_growth_rate = (memory_samples[-1][1] - memory_samples[0][1]) / (memory_samples[-1][0] - memory_samples[0][0])
            projected_hourly_growth = memory_growth_rate * 3600
        else:
            memory_growth_rate = 0
            projected_hourly_growth = 0
            
        print(f"\n=== MEMORY LEAK DETECTION RESULTS ===")
        print(f"Load Duration: {load_duration}s")
        print(f"Total Events: {event_counter}")
        print(f"Events per Second: {event_counter / load_duration:.2f}")
        print(f"Initial Memory: {initial_memory:.2f}MB")
        print(f"Final Memory: {final_memory:.2f}MB")
        print(f"Total Growth: {total_memory_growth:.2f}MB")
        print(f"Growth Rate: {memory_growth_rate:.4f} MB/s")
        print(f"Projected Hourly Growth: {projected_hourly_growth:.2f} MB/hour")
        
        # MEMORY LEAK ASSERTIONS - More reasonable thresholds for load testing
        assert total_memory_growth < 500.0, f"Total memory growth too high: {total_memory_growth:.2f}MB"
        assert projected_hourly_growth < 1000.0, (
            f"Projected memory leak too high: {projected_hourly_growth:.2f}MB/hour"
        )
        assert memory_growth_rate < 1.0, (
            f"Memory growth rate too high: {memory_growth_rate:.4f} MB/s"
        )
        
        # Verify handlers are still functioning
        total_processed = sum(h.processed_count for h in handlers)
        expected_minimum = event_counter * len(handlers) * 0.95  # 95% of expected processing
        assert total_processed >= expected_minimum, (
            f"Handler processing degraded: {total_processed} < {expected_minimum}"
        )
        
        await bus.cleanup()

    async def test_failover_stress_scenarios(self):
        """
        Test system behavior under failover stress scenarios
        """
        # Simulate failover between multiple event bus implementations
        primary_bus = MockRedisEventBusLoad(failure_rate=0.0, latency_ms=1)
        backup_bus = InMemoryEventBus()
        
        await primary_bus.initialize()
        await backup_bus.initialize()
        
        metrics = LoadTestMetrics()
        handler = ConcurrentLoadTestHandler("failover_handler", metrics)
        
        # Start with primary bus
        await primary_bus.subscribe(EventType.ORDER_CREATED, handler)
        
        metrics.start_test(publishers=5, subscribers=1)
        
        events_published = 0
        failover_occurred = False
        
        # Publish events with simulated failover
        for batch in range(100):  # 100 batches of 10 events each
            
            # Simulate primary bus failure after 50 batches
            if batch == 50 and not failover_occurred:
                print("  Simulating primary bus failure...")
                primary_bus.failure_rate = 1.0  # Force all operations to fail
                await backup_bus.subscribe(EventType.ORDER_CREATED, handler)
                failover_occurred = True
                
            batch_tasks = []
            for i in range(10):
                event = OrderEvent(
                    type=EventType.ORDER_CREATED,
                    source=f"failover_test_{events_published}",
                    order_id=f"failover-order-{events_published}",
                    account_id="failover-account",
                    symbol="BTC/USD",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=Decimal("1.0"),
                    price=Decimal("50000.0")
                )
                
                if failover_occurred:
                    # Use backup bus (InMemory)
                    task = asyncio.create_task(backup_bus.publish(event))
                else:
                    # Use primary bus (Redis simulation)
                    async def safe_publish():
                        try:
                            await primary_bus.publish(EventType.ORDER_CREATED, event)
                            metrics.record_publish(success=True)
                        except Exception:
                            metrics.record_publish(success=False)
                    
                    task = asyncio.create_task(safe_publish())
                    
                batch_tasks.append(task)
                events_published += 1
                
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Sample metrics every 20 batches
            if batch % 20 == 0:
                metrics.sample_metrics()
                
            await asyncio.sleep(0.01)
            
        # Wait for processing
        await asyncio.sleep(2.0)
        
        metrics.finish_test()
        summary = metrics.get_summary()
        
        print("\n=== FAILOVER STRESS TEST RESULTS ===")
        print(f"Total Events: {events_published}")
        print(f"Events Processed: {handler.processed_count}")
        print(f"Failover Occurred: {'Yes' if failover_occurred else 'No'}")
        print(f"Primary Bus Failures: {primary_bus.publish_failures}")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        print(f"Processing Rate: {(handler.processed_count / events_published * 100):.2f}%")
        
        # FAILOVER STRESS ASSERTIONS
        assert failover_occurred, "Failover should have been triggered"
        assert handler.processed_count >= events_published * 0.8, (
            "Too many events lost during failover"
        )
        assert summary['success_rate'] >= 70.0, (
            f"Overall success rate too low during failover: {summary['success_rate']:.2f}%"
        )
        
        await primary_bus.close()
        await backup_bus.cleanup()

    async def test_extreme_concurrent_load(self):
        """
        Test system under extreme concurrent load
        """
        bus = InMemoryEventBus()
        await bus.initialize()
        
        metrics = LoadTestMetrics()
        
        # Create many concurrent handlers
        num_handlers = 50
        handlers = []
        for i in range(num_handlers):
            handler = ConcurrentLoadTestHandler(f"extreme_handler_{i}", metrics)
            handlers.append(handler)
            await bus.subscribe(EventType.ORDER_CREATED, handler)
            
        metrics.start_test(publishers=50, subscribers=num_handlers)
        
        # Extreme concurrent publishing
        num_publishers = 50
        events_per_publisher = 200
        
        async def extreme_publisher(publisher_id):
            """High-speed publisher"""
            for i in range(events_per_publisher):
                event = OrderEvent(
                    type=EventType.ORDER_CREATED,
                    source=f"extreme_pub_{publisher_id}",
                    order_id=f"extreme-{publisher_id}-{i}",
                    account_id=f"extreme-account-{publisher_id}",
                    symbol="BTC/USD",
                    side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=Decimal("1.0"),
                    price=Decimal(f"{50000 + i}")
                )
                
                try:
                    result = await bus.publish(event)
                    metrics.record_publish(success=result.success)
                except Exception:
                    metrics.record_publish(success=False)
                    
                # Minimal delay for extreme load
                if i % 10 == 0:
                    await asyncio.sleep(0.001)
                    
        # Launch all publishers simultaneously
        start_time = time.time()
        publisher_tasks = [
            asyncio.create_task(extreme_publisher(pub_id))
            for pub_id in range(num_publishers)
        ]
        
        # Monitor system during extreme load
        async def extreme_monitor():
            """Monitor system under extreme load"""
            while not all(task.done() for task in publisher_tasks):
                await asyncio.sleep(2.0)
                metrics.sample_metrics()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                if current_memory > 500:  # Emergency brake if memory exceeds 500MB
                    print(f"  EMERGENCY: Memory usage {current_memory:.2f}MB - may need to abort")
                    
        monitor_task = asyncio.create_task(extreme_monitor())
        
        # Wait for completion
        await asyncio.gather(*publisher_tasks)
        monitor_task.cancel()
        
        # Wait for processing
        await asyncio.sleep(10.0)
        
        end_time = time.time()
        
        metrics.finish_test()
        summary = metrics.get_summary()
        
        total_handler_processed = sum(h.processed_count for h in handlers)
        expected_total = summary['total_published'] * num_handlers
        processing_rate = (
            total_handler_processed / expected_total * 100 if expected_total > 0 else 0
        )
        
        print("\n=== EXTREME LOAD TEST RESULTS ===")
        print(f"Duration: {end_time - start_time:.2f}s")
        print(f"Concurrent Publishers: {num_publishers}")
        print(f"Concurrent Handlers: {num_handlers}")
        print(f"Events Published: {summary['total_published']}")
        print(f"Total Handler Processing: {total_handler_processed}")
        print(f"Expected Processing: {expected_total}")
        print(f"Processing Rate: {processing_rate:.2f}%")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        print(f"Throughput: {summary['avg_throughput']:.2f} EPS")
        
        # EXTREME LOAD ASSERTIONS
        assert summary['success_rate'] >= 85.0, (
            f"Success rate under extreme load too low: {summary['success_rate']:.2f}%"
        )
        assert processing_rate >= 80.0, (
            f"Processing rate under extreme load too low: {processing_rate:.2f}%"
        )
        assert summary['avg_throughput'] >= 2000, (
            f"Throughput under extreme load too low: {summary['avg_throughput']:.2f} EPS"
        )
        
        await bus.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "load"])
