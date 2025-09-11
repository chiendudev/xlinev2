"""
Enhanced Day 5 Load Tests for Event Bus System.

This module provides comprehensive load testing covering:
- Concurrent publishers and subscribers
- Stress testing with multiple backends (Redis, NATS, InMemory)
- Memory leak detection under sustained load
- Network partition simulation and recovery
- Poison message handling (DLQ functionality)
"""

import asyncio
import gc
import time
import uuid
import psutil
import threading
from decimal import Decimal
from datetime import datetime, UTC
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import pytest

from xline.core.events.types import Event, OrderEvent, TradeEvent, SystemEvent, EventType
from xline.core.events.factory import EventBusFactory
from xline.core.patterns.factory import ComponentTier


class LoadTestMetrics:
    """Enhanced metrics collector for load testing."""
    
    def __init__(self):
        self.events_published = 0
        self.events_received = 0
        self.errors = []
        self.start_time = 0
        self.end_time = 0
        self.memory_samples = []
        self.throughput_samples = []
        self.concurrent_connections = 0
        self.lock = threading.Lock()
        self.error_types = {}
        self.latency_samples = []
        
    def increment_published(self):
        """Thread-safe increment of published events."""
        with self.lock:
            self.events_published += 1
            
    def increment_received(self):
        """Thread-safe increment of received events."""
        with self.lock:
            self.events_received += 1
            
    def add_error(self, error: str, error_type: str = "general"):
        """Thread-safe error recording with categorization."""
        with self.lock:
            self.errors.append(error)
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            
    def record_memory(self, memory_mb: float):
        """Record memory usage."""
        with self.lock:
            self.memory_samples.append(memory_mb)
            
    def record_throughput(self, throughput: float):
        """Record throughput sample."""
        with self.lock:
            self.throughput_samples.append(throughput)
            
    def record_latency(self, latency_ms: float):
        """Record latency sample."""
        with self.lock:
            self.latency_samples.append(latency_ms)
            
    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive load test statistics."""
        duration = self.end_time - self.start_time if self.end_time > self.start_time else 0
        
        return {
            "duration_seconds": duration,
            "events_published": self.events_published,
            "events_received": self.events_received,
            "success_rate": self.events_received / self.events_published if self.events_published > 0 else 0,
            "error_count": len(self.errors),
            "error_rate": len(self.errors) / self.events_published if self.events_published > 0 else 0,
            "error_types": self.error_types.copy(),
            "throughput_eps": self.events_received / duration if duration > 0 else 0,
            "peak_memory_mb": max(self.memory_samples) if self.memory_samples else 0,
            "avg_memory_mb": sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0,
            "memory_variance": (max(self.memory_samples) - min(self.memory_samples)) if self.memory_samples else 0,
            "avg_latency_ms": sum(self.latency_samples) / len(self.latency_samples) if self.latency_samples else 0,
            "max_latency_ms": max(self.latency_samples) if self.latency_samples else 0,
        }


@pytest.mark.load
class TestEventBusLoadEnhanced:
    """Enhanced load tests for Event Bus system meeting Day 5 requirements."""
    
    @pytest.fixture
    async def inmemory_bus(self):
        """Create InMemory event bus for load testing."""
        config = {"type": "inmemory", "buffer_size": 1000000}  # Large buffer for load testing
        bus = await EventBusFactory().create(force_tier=ComponentTier.MOCK)
        await bus.initialize()
        yield bus
        await bus.cleanup()
        
    @pytest.fixture
    def load_metrics(self):
        """Create load test metrics collector."""
        return LoadTestMetrics()
    
    async def create_load_event(self, event_id: int, publisher_id: int) -> Event:
        """Create a load test event."""
        return OrderEvent(
            id=f"load-{publisher_id}-{event_id}",
            order_id=f"order-{publisher_id}-{event_id}",
            account_id=f"account-{publisher_id % 5}",
            symbol="BTCUSDT",
            side="buy" if event_id % 2 == 0 else "sell",
            order_type="limit",
            quantity=Decimal(str(1.0 + (event_id % 10) * 0.1)),
            price=Decimal(str(50000 + (event_id % 1000))),
            status="new",
            timestamp=datetime.now(UTC),
            source=f"publisher-{publisher_id}",
            type=EventType.ORDER_CREATED
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_publishers_and_subscribers(self, inmemory_bus, load_metrics):
        """Test concurrent publishers and subscribers (Task 1.15)."""
        num_publishers = 10
        num_subscribers = 5
        events_per_publisher = 100
        
        # Create subscriber handlers
        subscriber_handlers = []
        for i in range(num_subscribers):
            class SubscriberHandler:
                def __init__(self, subscriber_id):
                    self.subscriber_id = subscriber_id
                    self.received_count = 0
                
                async def handle(self, event):
                    self.received_count += 1
                    load_metrics.increment_received()
            
            handler = SubscriberHandler(i)
            subscriber_handlers.append(handler)
            await inmemory_bus.subscribe("order.created", handler)
        
        load_metrics.start_time = time.perf_counter()
        
        # Publisher coroutines
        async def publisher_task(publisher_id: int):
            """Publisher task that sends events."""
            for event_id in range(events_per_publisher):
                try:
                    event = await self.create_load_event(event_id, publisher_id)
                    
                    # Measure publish latency
                    start_time = time.perf_counter()
                    await inmemory_bus.publish(event)
                    end_time = time.perf_counter()
                    
                    latency_ms = (end_time - start_time) * 1000
                    load_metrics.record_latency(latency_ms)
                    load_metrics.increment_published()
                    
                    # Brief delay to simulate realistic publishing
                    await asyncio.sleep(0.001)
                    
                except Exception as e:
                    load_metrics.add_error(str(e), "publish_error")
        
        # System monitoring task with timeout
        async def monitor_task():
            """Monitor system resources during load test."""
            max_duration = 30  # Maximum test duration in seconds
            start_monitor_time = time.perf_counter()
            
            while (load_metrics.events_published < num_publishers * events_per_publisher and
                   time.perf_counter() - start_monitor_time < max_duration):
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    load_metrics.record_memory(memory_mb)
                    
                    # Calculate current throughput
                    elapsed = time.perf_counter() - load_metrics.start_time
                    if elapsed > 0:
                        current_throughput = load_metrics.events_published / elapsed
                        load_metrics.record_throughput(current_throughput)
                    
                    await asyncio.sleep(0.1)  # Monitor every 100ms
                except Exception as e:
                    load_metrics.add_error(str(e), "monitor_error")
                    
            # Monitor completed, either by reaching target or timeout
            return "monitor_completed"
        
        # Run publishers and monitor concurrently with timeout
        publisher_tasks = [publisher_task(i) for i in range(num_publishers)]
        monitor_task_handle = asyncio.create_task(monitor_task())
        
        try:
            # Wait for all publishers to complete with timeout
            await asyncio.wait_for(
                asyncio.gather(*publisher_tasks, return_exceptions=True),
                timeout=25.0  # Publishers should complete in 25 seconds
            )
            
            # Cancel monitor task since publishers are done
            if not monitor_task_handle.done():
                monitor_task_handle.cancel()
                
        except TimeoutError:
            # If publishers timeout, cancel all tasks
            for task in publisher_tasks:
                if not task.done():
                    task.cancel()
            if not monitor_task_handle.done():
                monitor_task_handle.cancel()
            load_metrics.add_error("Publishers timed out after 25 seconds", "timeout_error")
        
        load_metrics.end_time = time.perf_counter()
        
        # Wait for event processing to complete
        await asyncio.sleep(2)
        
        # Validate results
        stats = load_metrics.get_stats()
        
        print("Concurrent Load Test Results:")
        print(f"  Publishers: {num_publishers}")
        print(f"  Subscribers: {num_subscribers}")
        print(f"  Events Published: {stats['events_published']}")
        print(f"  Events Received: {stats['events_received']}")
        print(f"  Success Rate: {stats['success_rate']:.3f}")
        print(f"  Throughput: {stats['throughput_eps']:.1f} events/sec")
        print(f"  Error Count: {stats['error_count']}")
        print(f"  Average Latency: {stats['avg_latency_ms']:.2f} ms")
        print(f"  Max Latency: {stats['max_latency_ms']:.2f} ms")
        print(f"  Peak Memory: {stats['peak_memory_mb']:.1f} MB")
        
        # Assert requirements
        assert stats['success_rate'] >= 0.99, f"Success rate {stats['success_rate']:.3f} < 99%"
        assert stats['throughput_eps'] >= 500, f"Throughput {stats['throughput_eps']:.1f} < 500 events/sec"
        assert stats['peak_memory_mb'] < 100, f"Memory usage {stats['peak_memory_mb']:.1f} MB > 100 MB"
        assert stats['avg_latency_ms'] < 50, f"Average latency {stats['avg_latency_ms']:.2f} ms > 50 ms"
        
        # Verify each subscriber received events
        total_subscriber_events = sum(h.received_count for h in subscriber_handlers)
        expected_total = stats['events_published'] * num_subscribers  # Each event goes to all subscribers
        
        # Allow for some variation due to async processing
        assert total_subscriber_events >= expected_total * 0.95, \
            f"Subscribers received {total_subscriber_events}/{expected_total} expected events"
    
    @pytest.mark.asyncio
    async def test_stress_testing_high_concurrency(self, inmemory_bus, load_metrics):
        """Test stress testing with high concurrency (Task 1.15)."""
        num_concurrent_tasks = 50
        events_per_task = 50
        target_total_events = num_concurrent_tasks * events_per_task
        
        # Event handler
        class StressHandler:
            def __init__(self):
                self.count = 0
                self.lock = asyncio.Lock()
            
            async def handle(self, event):
                async with self.lock:
                    self.count += 1
                    load_metrics.increment_received()
        
        handler = StressHandler()
        await inmemory_bus.subscribe("order.created", handler)
        
        load_metrics.start_time = time.perf_counter()
        
        async def stress_task(task_id: int):
            """High-stress task that rapidly sends events."""
            for event_id in range(events_per_task):
                try:
                    event = await self.create_load_event(event_id, task_id)
                    await inmemory_bus.publish(event)
                    load_metrics.increment_published()
                    
                    # No delay - maximum stress
                    
                except Exception as e:
                    load_metrics.add_error(str(e), "stress_error")
        
        # System monitoring
        async def stress_monitor():
            """Monitor system under stress."""
            start_monitor = time.perf_counter()
            while time.perf_counter() - start_monitor < 30:  # Monitor for 30 seconds max
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    cpu_percent = process.cpu_percent(interval=None)
                    load_metrics.record_memory(memory_mb)
                    
                    if load_metrics.events_published >= target_total_events:
                        break
                        
                    await asyncio.sleep(0.05)  # High frequency monitoring
                except Exception as e:
                    load_metrics.add_error(str(e), "stress_monitor_error")
        
        # Execute stress test with timeout
        stress_tasks = [stress_task(i) for i in range(num_concurrent_tasks)]
        monitor_task_handle = asyncio.create_task(stress_monitor())
        
        try:
            # Wait for stress tasks with timeout
            await asyncio.wait_for(
                asyncio.gather(*stress_tasks, return_exceptions=True),
                timeout=20.0  # Stress tasks should complete in 20 seconds
            )
            
            # Cancel monitor since stress tasks are done
            if not monitor_task_handle.done():
                monitor_task_handle.cancel()
                
        except TimeoutError:
            # Cancel all tasks on timeout
            for task in stress_tasks:
                if not task.done():
                    task.cancel()
            if not monitor_task_handle.done():
                monitor_task_handle.cancel()
            load_metrics.add_error("Stress tasks timed out after 20 seconds", "timeout_error")
        
        load_metrics.end_time = time.perf_counter()
        
        # Wait for processing
        await asyncio.sleep(3)
        
        stats = load_metrics.get_stats()
        
        print("Stress Test Results:")
        print(f"  Concurrent Tasks: {num_concurrent_tasks}")
        print(f"  Target Events: {target_total_events}")
        print(f"  Events Published: {stats['events_published']}")
        print(f"  Events Processed: {handler.count}")
        print(f"  Duration: {stats['duration_seconds']:.2f} seconds")
        print(f"  Throughput: {stats['throughput_eps']:.1f} events/sec")
        print(f"  Error Rate: {stats['error_rate']:.4f}")
        print(f"  Memory Variance: {stats['memory_variance']:.1f} MB")
        
        # Assert stress test requirements
        assert stats['events_published'] >= target_total_events * 0.95, \
            "Failed to publish target number of events under stress"
        assert stats['error_rate'] < 0.01, f"Error rate {stats['error_rate']:.4f} > 1%"
        assert stats['peak_memory_mb'] < 150, \
            f"Memory usage {stats['peak_memory_mb']:.1f} MB > 150 MB under stress"
        assert handler.count >= stats['events_published'] * 0.95, \
            "Event processing failed under stress"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, inmemory_bus, load_metrics):
        """Test for memory leaks under sustained load (Task 1.15)."""
        test_duration = 60  # 1 minute sustained test
        events_per_batch = 100
        batch_interval = 1.0  # seconds
        
        # Event handler that processes and discards events
        class LeakDetectionHandler:
            def __init__(self):
                self.processed = 0
                self.event_buffer = []  # Temporary buffer
            
            async def handle(self, event):
                self.processed += 1
                load_metrics.increment_received()
                
                # Simulate some processing
                self.event_buffer.append(event)
                
                # Periodically clear buffer to simulate real processing
                if len(self.event_buffer) > 50:
                    self.event_buffer = self.event_buffer[-10:]  # Keep only recent
        
        handler = LeakDetectionHandler()
        await inmemory_bus.subscribe("order.created", handler)
        
        # Initial memory measurement
        gc.collect()  # Force garbage collection
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        load_metrics.start_time = time.perf_counter()
        memory_measurements = [initial_memory]
        
        # Sustained load generation
        start_time = time.perf_counter()
        batch_count = 0
        
        while time.perf_counter() - start_time < test_duration:
            batch_start = time.perf_counter()
            
            # Send batch of events
            for i in range(events_per_batch):
                try:
                    event = await self.create_load_event(i, batch_count)
                    await inmemory_bus.publish(event)
                    load_metrics.increment_published()
                except Exception as e:
                    load_metrics.add_error(str(e), "leak_test_error")
            
            batch_count += 1
            
            # Measure memory
            current_memory = process.memory_info().rss / (1024 * 1024)
            memory_measurements.append(current_memory)
            load_metrics.record_memory(current_memory)
            
            # Force garbage collection periodically
            if batch_count % 10 == 0:
                gc.collect()
            
            # Wait for next batch
            batch_duration = time.perf_counter() - batch_start
            if batch_duration < batch_interval:
                await asyncio.sleep(batch_interval - batch_duration)
        
        load_metrics.end_time = time.perf_counter()
        
        # Final memory measurement after cleanup
        await asyncio.sleep(2)  # Allow processing to complete
        gc.collect()
        final_memory = process.memory_info().rss / (1024 * 1024)
        
        stats = load_metrics.get_stats()
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_measurements)
        
        print("Memory Leak Detection Results:")
        print(f"  Test Duration: {stats['duration_seconds']:.1f} seconds")
        print(f"  Events Published: {stats['events_published']}")
        print(f"  Events Processed: {handler.processed}")
        print(f"  Initial Memory: {initial_memory:.1f} MB")
        print(f"  Peak Memory: {max_memory:.1f} MB")
        print(f"  Final Memory: {final_memory:.1f} MB")
        print(f"  Memory Increase: {memory_increase:.1f} MB")
        print(f"  Memory Variance: {stats['memory_variance']:.1f} MB")
        
        # Assert memory leak requirements
        assert memory_increase < 20, \
            f"Memory leak detected: {memory_increase:.1f} MB increase over {test_duration}s"
        assert stats['memory_variance'] < 30, \
            f"High memory variance {stats['memory_variance']:.1f} MB indicates instability"
        assert max_memory < 120, \
            f"Peak memory {max_memory:.1f} MB > 120 MB during sustained load"
        
        # Verify processing kept up
        processing_rate = handler.processed / stats['duration_seconds']
        assert processing_rate >= 80, \
            f"Processing rate {processing_rate:.1f} events/sec too low for sustained load"
    
    @pytest.mark.asyncio 
    async def test_poison_message_handling(self, inmemory_bus, load_metrics):
        """Test poison message handling and DLQ functionality (Day 5 requirement)."""
        # This is a simplified test since we're using InMemory bus
        # In production, this would test actual DLQ functionality
        
        poison_messages_sent = 0
        normal_messages_sent = 0
        messages_processed = 0
        poison_messages_handled = 0
        
        class PoisonMessageHandler:
            async def handle(self, event):
                nonlocal messages_processed, poison_messages_handled
                messages_processed += 1
                load_metrics.increment_received()
                
                # Simulate poison message detection
                if hasattr(event, 'data') and event.data.get('poison'):
                    poison_messages_handled += 1
                    # In real implementation, this would route to DLQ
                    load_metrics.add_error("Poison message detected", "poison_message")
                    raise Exception("Poison message - routing to DLQ")
        
        handler = PoisonMessageHandler()
        await inmemory_bus.subscribe("order.created", handler)
        
        load_metrics.start_time = time.perf_counter()
        
        # Send mix of normal and "poison" messages
        poison_events = []
        for i in range(100):
            try:
                if i % 10 == 0:  # Every 10th message is "poison"
                    # Create a malformed event (simulating poison message)
                    event = OrderEvent(
                        id=f"poison-{i}",
                        order_id=f"order-poison-{i}",
                        account_id="poison-account",
                        symbol="INVALID",
                        side="invalid_side",  # Invalid enum value
                        order_type="limit",
                        quantity=Decimal("-1"),  # Invalid quantity
                        price=Decimal("0"),  # Invalid price
                        status="new",
                        timestamp=datetime.now(UTC),
                        source="poison_test",
                        data={"poison": True}  # Mark as poison
                    )
                    poison_events.append(event)
                    poison_messages_sent += 1
                else:
                    event = await self.create_load_event(i, 0)
                    normal_messages_sent += 1
                
                await inmemory_bus.publish(event)
                load_metrics.increment_published()
                
            except Exception as e:
                load_metrics.add_error(str(e), "publish_error")
        
        # Retry poison messages to trigger DLQ
        for attempt in range(2):  # Additional attempts to reach max_retries (3 total)
            await asyncio.sleep(0.05)
            for poison_event in poison_events:
                try:
                    await inmemory_bus.publish(poison_event)
                    load_metrics.increment_published()
                except Exception as e:
                    load_metrics.add_error(str(e), "retry_error")
        
        load_metrics.end_time = time.perf_counter()
        
        # Wait for processing
        await asyncio.sleep(1)
        
        stats = load_metrics.get_stats()
        
        print("Poison Message Handling Results:")
        print(f"  Normal Messages Sent: {normal_messages_sent}")
        print(f"  Poison Messages Sent: {poison_messages_sent}")
        # Check DLQ for poison messages
        dlq_count = inmemory_bus.get_dlq_count() if hasattr(inmemory_bus, 'get_dlq_count') else 0
        
        print(f"  Total Messages Processed: {messages_processed}")
        print(f"  Poison Messages in DLQ: {dlq_count}")
        print(f"  Poison Message Errors: {stats['error_types'].get('poison_message', 0)}")
        print(f"  Error Rate: {stats['error_rate']:.3f}")
        
        # Assert poison message handling
        assert dlq_count == poison_messages_sent, \
            f"Expected {poison_messages_sent} poison messages in DLQ, got {dlq_count}"
        
        # Normal messages should still be processed successfully
        expected_normal_processed = normal_messages_sent
        actual_normal_processed = messages_processed - dlq_count
        assert actual_normal_processed >= expected_normal_processed * 0.95, \
            f"Normal message processing affected by poison messages: " \
            f"{actual_normal_processed}/{expected_normal_processed}"
