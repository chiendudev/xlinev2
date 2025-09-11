"""Tests for monitoring and metrics functionality."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock

from xline.infrastructure.messaging.monitoring import (
    HealthMonitor,
    HealthStatus,
    InMemoryMetricsCollector,
    MessageBusMonitor,
    MetricType,
    MetricValue,
    NoOpMetricsCollector,
    TimerContext,
    get_monitor,
    reset_monitor,
)


class TestMetricValue:
    """Test metric value functionality."""
    
    def test_metric_value_creation(self):
        """Test creating metric value with all fields."""
        timestamp = time.time()
        tags = {"service": "test", "version": "1.0"}
        
        metric = MetricValue(
            name="test.counter",
            value=42.0,
            metric_type=MetricType.COUNTER,
            tags=tags,
            timestamp=timestamp
        )
        
        assert metric.name == "test.counter"
        assert metric.value == 42.0
        assert metric.metric_type == MetricType.COUNTER
        assert metric.tags == tags
        assert metric.timestamp == timestamp
    
    def test_metric_value_validation_empty_name(self):
        """Test validation fails for empty metric name."""
        with pytest.raises(ValueError, match="Metric name cannot be empty"):
            MetricValue(
                name="   ",
                value=1.0,
                metric_type=MetricType.COUNTER
            )


class TestHealthStatus:
    """Test health status functionality."""
    
    def test_health_status_creation(self):
        """Test creating health status."""
        checks = {"db": True, "cache": False}
        details = {"cache": "Connection timeout"}
        
        status = HealthStatus(
            is_healthy=False,
            status="Some checks failed",
            checks=checks,
            details=details
        )
        
        assert status.is_healthy is False
        assert status.status == "Some checks failed"
        assert status.checks == checks
        assert status.details == details
        assert isinstance(status.timestamp, float)
    
    def test_overall_status_property(self):
        """Test overall status property."""
        healthy_status = HealthStatus(is_healthy=True, status="All good")
        unhealthy_status = HealthStatus(is_healthy=False, status="Problems")
        
        assert healthy_status.overall_status == "healthy"
        assert unhealthy_status.overall_status == "unhealthy"


class TestInMemoryMetricsCollector:
    """Test in-memory metrics collector."""
    
    @pytest.fixture
    def collector(self):
        """Create metrics collector for testing."""
        return InMemoryMetricsCollector()
    
    def test_increment_counter(self, collector):
        """Test incrementing counter metrics."""
        collector.increment("test.counter", 5.0, {"type": "test"})
        collector.increment("test.counter", 3.0, {"type": "test"})
        
        value = collector.get_counter_value("test.counter", {"type": "test"})
        assert value == 8.0
        
        metrics = collector.get_metrics()
        counter_metrics = [m for m in metrics if m.name == "test.counter"]
        assert len(counter_metrics) == 2
        assert counter_metrics[0].value == 5.0
        assert counter_metrics[1].value == 8.0
    
    def test_increment_counter_default_value(self, collector):
        """Test incrementing counter with default value."""
        collector.increment("test.counter")
        
        value = collector.get_counter_value("test.counter")
        assert value == 1.0
    
    def test_histogram_recording(self, collector):
        """Test recording histogram values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            collector.histogram("test.latency", value, {"endpoint": "api"})
        
        recorded_values = collector.get_histogram_values("test.latency", {"endpoint": "api"})
        assert recorded_values == values
        
        metrics = collector.get_metrics()
        histogram_metrics = [m for m in metrics if m.name == "test.latency"]
        assert len(histogram_metrics) == 5
    
    def test_histogram_stats_calculation(self, collector):
        """Test histogram statistics calculation."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            collector.histogram("test.latency", value)
        
        stats = collector.get_histogram_stats("test.latency")
        
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["p50"] == 30.0
        assert stats["p95"] == 48.0  # P95 with 5 values: interpolation between index 3 and 4
    
    def test_histogram_stats_empty(self, collector):
        """Test histogram stats for empty dataset."""
        stats = collector.get_histogram_stats("nonexistent")
        assert stats == {}
    
    def test_gauge_setting(self, collector):
        """Test setting gauge values."""
        collector.gauge("test.gauge", 42.0, {"instance": "web1"})
        collector.gauge("test.gauge", 43.0, {"instance": "web1"})  # Overwrite
        
        value = collector.get_gauge_value("test.gauge", {"instance": "web1"})
        assert value == 43.0
        
        # Different tags should be separate
        collector.gauge("test.gauge", 50.0, {"instance": "web2"})
        value2 = collector.get_gauge_value("test.gauge", {"instance": "web2"})
        assert value2 == 50.0
    
    def test_timer_context(self, collector):
        """Test timer context manager."""
        with collector.timer("test.operation", {"type": "async"}):
            time.sleep(0.1)  # Simulate work
        
        duration_values = collector.get_histogram_values(
            "test.operation.duration", 
            {"type": "async"}
        )
        
        assert len(duration_values) == 1
        assert 90 <= duration_values[0] <= 150  # ~100ms in milliseconds
    
    def test_reset_metrics(self, collector):
        """Test resetting all metrics."""
        collector.increment("test.counter")
        collector.histogram("test.latency", 10.0)
        collector.gauge("test.gauge", 5.0)
        
        assert len(collector.get_metrics()) > 0
        assert collector.get_counter_value("test.counter") == 1.0
        
        collector.reset()
        
        assert len(collector.get_metrics()) == 0
        assert collector.get_counter_value("test.counter") == 0.0
        assert collector.get_gauge_value("test.gauge") is None
    
    def test_tags_to_string_conversion(self, collector):
        """Test internal tags to string conversion."""
        tags1 = {"service": "api", "version": "1.0"}
        tags2 = {"version": "1.0", "service": "api"}  # Different order
        
        # Same tags should produce same string regardless of order
        string1 = collector._tags_to_string(tags1)
        string2 = collector._tags_to_string(tags2)
        assert string1 == string2
        
        # Empty tags should produce empty string
        assert collector._tags_to_string({}) == ""
    
    def test_percentile_calculation(self, collector):
        """Test percentile calculation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        assert collector._percentile(values, 50) == 5.5  # Median
        assert collector._percentile(values, 90) == 9.1
        assert collector._percentile(values, 100) == 10.0
        
        # Edge cases
        assert collector._percentile([], 50) == 0.0
        assert collector._percentile([5.0], 50) == 5.0


class TestNoOpMetricsCollector:
    """Test no-op metrics collector."""
    
    @pytest.fixture
    def collector(self):
        """Create no-op metrics collector for testing."""
        return NoOpMetricsCollector()
    
    def test_all_operations_noop(self, collector):
        """Test all operations are no-op and don't raise errors."""
        # All these should work without error but do nothing
        collector.increment("test.counter", 5.0, {"type": "test"})
        collector.histogram("test.latency", 100.0)
        collector.gauge("test.gauge", 42.0)
        
        # Timer should return working context manager
        with collector.timer("test.operation"):
            pass
        
        # Should return empty metrics
        assert collector.get_metrics() == []
        
        # Reset should work
        collector.reset()


class TestTimerContext:
    """Test timer context functionality."""
    
    def test_timer_context_manual(self):
        """Test timer context with manual collector."""
        collector = InMemoryMetricsCollector()
        timer = TimerContext(collector, "test.timer", {"operation": "test"})
        
        start_time = time.time()
        with timer:
            time.sleep(0.05)  # 50ms
        end_time = time.time()
        
        duration_values = collector.get_histogram_values(
            "test.timer.duration",
            {"operation": "test"}
        )
        
        assert len(duration_values) == 1
        expected_duration = (end_time - start_time) * 1000  # ms
        assert abs(duration_values[0] - expected_duration) < 10  # Within 10ms


class TestHealthMonitor:
    """Test health monitor functionality."""
    
    @pytest.fixture
    def monitor(self):
        """Create health monitor for testing."""
        return HealthMonitor()
    
    def test_register_sync_check(self, monitor):
        """Test registering synchronous health check."""
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        monitor.register_check("healthy", healthy_check)
        monitor.register_check("unhealthy", unhealthy_check)
        
        assert "healthy" in monitor._checks
        assert "unhealthy" in monitor._checks
    
    def test_register_async_check(self, monitor):
        """Test registering asynchronous health check."""
        async def async_check():
            return True
        
        monitor.register_check("async", async_check)
        assert "async" in monitor._checks
    
    def test_unregister_check(self, monitor):
        """Test unregistering health check."""
        monitor.register_check("test", lambda: True)
        assert "test" in monitor._checks
        
        monitor.unregister_check("test")
        assert "test" not in monitor._checks
    
    async def test_check_health_all_passing(self, monitor):
        """Test health check with all checks passing."""
        monitor.register_check("check1", lambda: True)
        monitor.register_check("check2", lambda: True)
        
        status = await monitor.check_health()
        
        assert status.is_healthy is True
        assert status.overall_status == "healthy"
        assert status.checks["check1"] is True
        assert status.checks["check2"] is True
        assert len(status.details) == 0
    
    async def test_check_health_some_failing(self, monitor):
        """Test health check with some checks failing."""
        monitor.register_check("good", lambda: True)
        monitor.register_check("bad", lambda: False)
        
        status = await monitor.check_health()
        
        assert status.is_healthy is False
        assert status.overall_status == "unhealthy"
        assert status.checks["good"] is True
        assert status.checks["bad"] is False
    
    async def test_check_health_async_checks(self, monitor):
        """Test health check with async functions."""
        async def async_good():
            return True
        
        async def async_bad():
            await asyncio.sleep(0.01)  # Small delay
            return False
        
        monitor.register_check("async_good", async_good)
        monitor.register_check("async_bad", async_bad)
        
        status = await monitor.check_health()
        
        assert status.is_healthy is False
        assert status.checks["async_good"] is True
        assert status.checks["async_bad"] is False
    
    async def test_check_health_timeout(self, monitor):
        """Test health check with timeout."""
        async def slow_check():
            await asyncio.sleep(10)  # Longer than timeout
            return True
        
        monitor.register_check("slow", slow_check)
        monitor._check_timeout = 0.1  # Short timeout
        
        status = await monitor.check_health()
        
        assert status.is_healthy is False
        assert status.checks["slow"] is False
        assert "Check timed out" in status.details["slow"]
    
    async def test_check_health_exception(self, monitor):
        """Test health check with exception."""
        def failing_check():
            raise ValueError("Test error")
        
        monitor.register_check("failing", failing_check)
        
        status = await monitor.check_health()
        
        assert status.is_healthy is False
        assert status.checks["failing"] is False
        assert "Check failed: Test error" in status.details["failing"]
    
    def test_last_check_tracking(self, monitor):
        """Test tracking of last check results and times."""
        monitor.register_check("test", lambda: True)
        
        # Before any checks
        assert monitor.get_last_check_time("test") is None
        assert monitor.get_last_check_result("test") is None
        
        # After running check (need to use asyncio.run for async method)
        async def run_check():
            await monitor.check_health()
        
        asyncio.run(run_check())
        
        # After check
        assert monitor.get_last_check_time("test") is not None
        assert monitor.get_last_check_result("test") is True


class TestMessageBusMonitor:
    """Test comprehensive message bus monitor."""
    
    def test_monitor_creation_with_metrics_enabled(self):
        """Test creating monitor with metrics enabled."""
        monitor = MessageBusMonitor(metrics_enabled=True)
        
        assert isinstance(monitor.metrics, InMemoryMetricsCollector)
        assert isinstance(monitor.health, HealthMonitor)
    
    def test_monitor_creation_with_metrics_disabled(self):
        """Test creating monitor with metrics disabled."""
        monitor = MessageBusMonitor(metrics_enabled=False)
        
        assert isinstance(monitor.metrics, NoOpMetricsCollector)
        assert isinstance(monitor.health, HealthMonitor)
    
    def test_monitor_creation_with_custom_collector(self):
        """Test creating monitor with custom collector."""
        custom_collector = InMemoryMetricsCollector()
        monitor = MessageBusMonitor(collector=custom_collector)
        
        assert monitor.metrics is custom_collector
    
    def test_publish_metrics_recording(self):
        """Test recording publish metrics."""
        monitor = MessageBusMonitor()
        
        # Record publish attempt
        monitor.record_publish_attempt("test.event")
        attempts = monitor.metrics.get_counter_value(
            "message_bus.publish.attempts",
            {"event_type": "test.event"}
        )
        assert attempts == 1.0
        
        # Record successful publish
        monitor.record_publish_success("test.event", 50.0)
        successes = monitor.metrics.get_counter_value(
            "message_bus.publish.success",
            {"event_type": "test.event"}
        )
        assert successes == 1.0
        
        durations = monitor.metrics.get_histogram_values(
            "message_bus.publish.duration",
            {"event_type": "test.event"}
        )
        assert durations == [50.0]
        
        # Record failed publish
        monitor.record_publish_failure("test.event", "network_error")
        failures = monitor.metrics.get_counter_value(
            "message_bus.publish.failures",
            {"event_type": "test.event", "error_type": "network_error"}
        )
        assert failures == 1.0
    
    def test_subscription_metrics_recording(self):
        """Test recording subscription metrics."""
        monitor = MessageBusMonitor()
        
        monitor.record_subscription_created("test.event")
        created = monitor.metrics.get_counter_value(
            "message_bus.subscription.created",
            {"event_type": "test.event"}
        )
        assert created == 1.0
        
        monitor.record_subscription_removed("test.event")
        removed = monitor.metrics.get_counter_value(
            "message_bus.subscription.removed",
            {"event_type": "test.event"}
        )
        assert removed == 1.0
    
    def test_message_processing_metrics(self):
        """Test recording message processing metrics."""
        monitor = MessageBusMonitor()
        
        # Record received message
        monitor.record_message_received("test.event")
        received = monitor.metrics.get_counter_value(
            "message_bus.messages.received",
            {"event_type": "test.event"}
        )
        assert received == 1.0
        
        # Record processed message
        monitor.record_message_processed("test.event", 25.0)
        processed = monitor.metrics.get_counter_value(
            "message_bus.messages.processed",
            {"event_type": "test.event"}
        )
        assert processed == 1.0
        
        durations = monitor.metrics.get_histogram_values(
            "message_bus.processing.duration",
            {"event_type": "test.event"}
        )
        assert durations == [25.0]
        
        # Record failed processing
        monitor.record_message_failed("test.event", "parse_error")
        failed = monitor.metrics.get_counter_value(
            "message_bus.messages.failed",
            {"event_type": "test.event", "error_type": "parse_error"}
        )
        assert failed == 1.0
    
    def test_dlq_metrics_recording(self):
        """Test recording DLQ metrics."""
        monitor = MessageBusMonitor()
        
        # Record DLQ entry
        monitor.record_dlq_entry("timeout")
        entries = monitor.metrics.get_counter_value(
            "message_bus.dlq.entries",
            {"reason": "timeout"}
        )
        assert entries == 1.0
        
        # Record DLQ requeue
        monitor.record_dlq_requeue(5)
        operations = monitor.metrics.get_counter_value("message_bus.dlq.requeue.operations")
        assert operations == 1.0
        
        counts = monitor.metrics.get_histogram_values("message_bus.dlq.requeue.count")
        assert counts == [5.0]
    
    def test_gauge_metrics_recording(self):
        """Test recording gauge metrics."""
        monitor = MessageBusMonitor()
        
        # Set active connections
        monitor.set_active_connections(10)
        connections = monitor.metrics.get_gauge_value("message_bus.connections.active")
        assert connections == 10.0
        
        # Set queue depth
        monitor.set_queue_depth("events", 25)
        depth = monitor.metrics.get_gauge_value(
            "message_bus.queue.depth",
            {"queue": "events"}
        )
        assert depth == 25.0
    
    async def test_metrics_health_check(self):
        """Test built-in metrics health check."""
        monitor = MessageBusMonitor()
        
        status = await monitor.health.check_health()
        
        assert status.is_healthy is True
        assert status.checks["metrics_collector"] is True


class TestGlobalMonitor:
    """Test global monitor functionality."""
    
    def test_get_monitor_singleton(self):
        """Test global monitor is singleton."""
        reset_monitor()  # Start fresh
        
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        
        assert monitor1 is monitor2
    
    def test_reset_monitor(self):
        """Test resetting global monitor."""
        monitor1 = get_monitor()
        reset_monitor()
        monitor2 = get_monitor()
        
        assert monitor1 is not monitor2
    
    def test_get_monitor_with_settings(self):
        """Test getting monitor with specific settings."""
        reset_monitor()
        
        monitor = get_monitor(metrics_enabled=False)
        assert isinstance(monitor.metrics, NoOpMetricsCollector)
