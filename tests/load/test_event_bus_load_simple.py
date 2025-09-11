"""
Simplified load tests for Event Bus system.

Tests basic load scenarios with proper EventBusFactory usage.
"""

import asyncio
import time
import threading

import pytest

from xline.core.events.types import Event, SystemEvent
from xline.core.events.factory import EventBusFactory


class LoadMetrics:
    """Simple metrics collector for load testing."""
    
    def __init__(self):
        self.events_published = 0
        self.events_received = 0
        self.errors = 0
        self.start_time = 0
        self.end_time = 0
        self.lock = threading.Lock()
        
    def increment_published(self):
        with self.lock:
            self.events_published += 1
            
    def increment_received(self):
        with self.lock:
            self.events_received += 1
            
    def increment_errors(self):
        with self.lock:
            self.errors += 1
            
    def get_stats(self):
        duration = self.end_time - self.start_time if self.end_time > self.start_time else 0
        return {
            "duration": duration,
            "published": self.events_published,
            "received": self.events_received,
            "errors": self.errors,
            "success_rate": self.events_received / self.events_published if self.events_published > 0 else 0,
            "throughput": self.events_received / duration if duration > 0 else 0,
        }


@pytest.mark.load
class TestEventBusLoadSimple:
    """Simplified load tests for Event Bus system."""
    
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load over time."""
        
        factory = EventBusFactory()
        bus = await factory.create()
        
        duration_seconds = 10
        target_eps = 500  # Reduced target for simple test
        
        metrics = LoadMetrics()
        metrics.start_time = time.perf_counter()
        
        async def load_handler(event: Event):
            metrics.increment_received()
        
        await bus.subscribe("sustained_load", load_handler)
        
        # Publish events at target rate
        event_counter = 0
        
        while time.perf_counter() - metrics.start_time < duration_seconds:
            event = SystemEvent(
                type="system.sustained",
                source="sustained_test",
                data={
                    "sequence": event_counter,
                    "timestamp": time.perf_counter(),
                    "message": f"Sustained load event {event_counter}"
                }
            )
            
            await bus.publish("sustained_load", event)
            metrics.increment_published()
            event_counter += 1
            
            # Control rate
            await asyncio.sleep(1.0 / target_eps)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        metrics.end_time = time.perf_counter()
        stats = metrics.get_stats()
        
        print("\\n🔄 SUSTAINED LOAD TEST RESULTS:")
        print(f"   📊 Duration: {stats['duration']:.1f} seconds")
        print(f"   📊 Events Published: {stats['published']:,}")
        print(f"   📊 Events Received: {stats['received']:,}")
        print(f"   📊 Success Rate: {stats['success_rate']:.1%}")
        print(f"   📊 Throughput: {stats['throughput']:.1f} events/second")
        print(f"   📊 Target: {target_eps} eps")
        print(f"   ⚡ Result: {'✅ PASSED' if stats['success_rate'] >= 0.9 else '❌ FAILED'}")
        
        # Verify sustained performance
        assert stats["success_rate"] >= 0.9, f"Success rate {stats['success_rate']:.1%} below 90%"
        assert stats["throughput"] >= target_eps * 0.8, f"Throughput {stats['throughput']:.1f} below 80% of target"
    
    @pytest.mark.asyncio
    async def test_concurrent_publishers(self):
        """Test multiple concurrent publishers."""
        
        factory = EventBusFactory()
        bus = await factory.create()
        
        num_publishers = 5
        events_per_publisher = 200
        
        metrics = LoadMetrics()
        metrics.start_time = time.perf_counter()
        
        async def concurrent_handler(event: Event):
            metrics.increment_received()
        
        await bus.subscribe("concurrent", concurrent_handler)
        
        # Create publisher tasks
        async def publisher_task(publisher_id: int):
            for i in range(events_per_publisher):
                event = SystemEvent(
                    type="system.concurrent",
                    source=f"publisher_{publisher_id}",
                    data={
                        "publisher_id": publisher_id,
                        "sequence": i,
                        "message": f"Event {i} from publisher {publisher_id}"
                    }
                )
                await bus.publish("concurrent", event)
                metrics.increment_published()
                await asyncio.sleep(0.002)  # Small delay
        
        # Run publishers concurrently
        tasks = [publisher_task(i) for i in range(num_publishers)]
        await asyncio.gather(*tasks)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        metrics.end_time = time.perf_counter()
        stats = metrics.get_stats()
        
        expected_events = num_publishers * events_per_publisher
        
        print("\\n👥 CONCURRENT PUBLISHERS TEST RESULTS:")
        print(f"   📊 Publishers: {num_publishers}")
        print(f"   📊 Events per Publisher: {events_per_publisher}")
        print(f"   📊 Expected Events: {expected_events:,}")
        print(f"   📊 Events Published: {stats['published']:,}")
        print(f"   📊 Events Received: {stats['received']:,}")
        print(f"   📊 Success Rate: {stats['success_rate']:.1%}")
        print(f"   📊 Throughput: {stats['throughput']:.1f} events/second")
        print(f"   📊 Duration: {stats['duration']:.2f} seconds")
        print(f"   ⚡ Result: {'✅ PASSED' if stats['success_rate'] >= 0.95 else '❌ FAILED'}")
        
        # Verify concurrent handling
        assert stats["success_rate"] >= 0.95, f"Success rate {stats['success_rate']:.1%} below 95%"
        assert stats["published"] == expected_events, f"Published {stats['published']} != expected {expected_events}"
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers handling same events."""
        
        factory = EventBusFactory()
        bus = await factory.create()
        
        num_subscribers = 4
        test_events = 500
        
        subscriber_counts = {f"sub_{i}": 0 for i in range(num_subscribers)}
        
        # Create subscribers
        async def create_subscriber(sub_id: str):
            async def handler(event: Event):
                subscriber_counts[sub_id] += 1
            return handler
        
        for i in range(num_subscribers):
            sub_id = f"sub_{i}"
            handler = await create_subscriber(sub_id)
            await bus.subscribe("multi_sub", handler)
        
        start_time = time.perf_counter()
        
        # Publish events
        for i in range(test_events):
            event = SystemEvent(
                type="system.multi_sub",
                source="multi_sub_test",
                data={
                    "sequence": i,
                    "message": f"Multi-subscriber event {i}"
                }
            )
            await bus.publish("multi_sub", event)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Calculate results
        total_received = sum(subscriber_counts.values())
        expected_total = test_events * num_subscribers
        success_rate = total_received / expected_total if expected_total > 0 else 0
        throughput = total_received / duration
        
        print("\\n📡 MULTIPLE SUBSCRIBERS TEST RESULTS:")
        print(f"   📊 Subscribers: {num_subscribers}")
        print(f"   📊 Test Events: {test_events:,}")
        print(f"   📊 Expected Total Receives: {expected_total:,}")
        print(f"   📊 Actual Total Receives: {total_received:,}")
        print(f"   📊 Success Rate: {success_rate:.1%}")
        print(f"   📊 Throughput: {throughput:.1f} receives/second")
        print(f"   📊 Duration: {duration:.2f} seconds")
        
        # Show per-subscriber stats
        for sub_id, count in subscriber_counts.items():
            sub_rate = count / test_events if test_events > 0 else 0
            print(f"   📊 {sub_id}: {count:,} events ({sub_rate:.1%})")
        
        print(f"   ⚡ Result: {'✅ PASSED' if success_rate >= 0.9 else '❌ FAILED'}")
        
        # Verify all subscribers received events
        assert success_rate >= 0.9, f"Success rate {success_rate:.1%} below 90%"
        
        # Verify each subscriber got most events
        for sub_id, count in subscriber_counts.items():
            sub_rate = count / test_events
            assert sub_rate >= 0.9, f"Subscriber {sub_id} only received {sub_rate:.1%} of events"
    
    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test system resilience to errors in event handlers."""
        
        factory = EventBusFactory()
        bus = await factory.create()
        
        successful_events = []
        error_events = []
        
        async def error_prone_handler(event: Event):
            if event.data.get("should_error"):
                error_events.append(event)
                raise ValueError("Simulated handler error")
            else:
                successful_events.append(event)
        
        await bus.subscribe("error_test", error_prone_handler)
        
        # Mix of good and bad events
        total_events = 100
        error_events_count = 20
        
        start_time = time.perf_counter()
        
        for i in range(total_events):
            should_error = i < error_events_count
            
            event = SystemEvent(
                type="system.error_test",
                source="error_test",
                data={
                    "sequence": i,
                    "should_error": should_error,
                    "message": f"{'Error' if should_error else 'Good'} event {i}"
                }
            )
            await bus.publish("error_test", event)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        expected_good = total_events - error_events_count
        good_rate = len(successful_events) / expected_good if expected_good > 0 else 0
        
        print("\\n🛡️ ERROR RESILIENCE TEST RESULTS:")
        print(f"   📊 Total Events: {total_events}")
        print(f"   📊 Expected Errors: {error_events_count}")
        print(f"   📊 Expected Good: {expected_good}")
        print(f"   📊 Successful Events: {len(successful_events)}")
        print(f"   📊 Good Event Rate: {good_rate:.1%}")
        print(f"   📊 Duration: {duration:.2f} seconds")
        print(f"   ⚡ Result: {'✅ PASSED' if good_rate >= 0.9 else '❌ FAILED'}")
        
        # Verify good events were processed despite errors
        assert good_rate >= 0.9, f"Good event processing rate {good_rate:.1%} below 90%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "load"])
