"""
Monitoring and metrics collection for message bus infrastructure.

This module provides:
- Metrics collection for publish/subscribe operations
- Performance timing and counters
- Health monitoring capabilities
- No-op implementations when metrics are disabled
"""

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Container for a metric value with metadata."""
    
    name: str
    value: float
    metric_type: MetricType
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        """Validate metric value after initialization."""
        if not self.name.strip():
            raise ValueError("Metric name cannot be empty")


@dataclass 
class HealthStatus:
    """Health check status information."""
    
    is_healthy: bool
    status: str
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    @property
    def overall_status(self) -> str:
        """Get overall health status string."""
        return "healthy" if self.is_healthy else "unhealthy"


class MetricsCollector:
    """
    Base metrics collector interface.
    
    Provides methods for recording various types of metrics
    with support for tags and timestamps.
    """
    
    def increment(
        self, 
        name: str, 
        value: float = 1.0, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        raise NotImplementedError
    
    def histogram(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Record a histogram value."""
        raise NotImplementedError
    
    def gauge(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Set a gauge value."""
        raise NotImplementedError
    
    def timer(
        self, 
        name: str,
        tags: dict[str, str] | None = None
    ) -> 'TimerContext':
        """Create a timer context for measuring duration."""
        raise NotImplementedError
    
    def get_metrics(self) -> list[MetricValue]:
        """Get all collected metrics."""
        raise NotImplementedError
    
    def reset(self) -> None:
        """Reset all metrics."""
        raise NotImplementedError


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(
        self, 
        collector: MetricsCollector, 
        name: str, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Initialize timer context."""
        self._collector = collector
        self._name = name
        self._tags = tags or {}
        self._start_time: float | None = None
    
    def __enter__(self) -> 'TimerContext':
        """Start timing."""
        self._start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing and record duration."""
        if self._start_time is not None:
            duration = time.time() - self._start_time
            self._collector.histogram(
                f"{self._name}.duration",
                duration * 1000,  # Convert to milliseconds
                self._tags
            )


class InMemoryMetricsCollector(MetricsCollector):
    """
    In-memory implementation of metrics collector.
    
    Stores metrics in memory for testing and development.
    """
    
    def __init__(self) -> None:
        """Initialize in-memory collector."""
        self._metrics: list[MetricValue] = []
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def increment(
        self, 
        name: str, 
        value: float = 1.0, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        tags = tags or {}
        key = f"{name}:{self._tags_to_string(tags)}"
        self._counters[key] += value
        
        metric = MetricValue(
            name=name,
            value=self._counters[key],
            metric_type=MetricType.COUNTER,
            tags=tags
        )
        self._metrics.append(metric)
        
        logger.debug(
            "Counter incremented",
            name=name,
            value=value,
            total=self._counters[key],
            tags=tags
        )
    
    def histogram(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Record a histogram value."""
        tags = tags or {}
        key = f"{name}:{self._tags_to_string(tags)}"
        self._histograms[key].append(value)
        
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            tags=tags
        )
        self._metrics.append(metric)
        
        logger.debug(
            "Histogram value recorded",
            name=name,
            value=value,
            tags=tags
        )
    
    def gauge(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """Set a gauge value."""
        tags = tags or {}
        key = f"{name}:{self._tags_to_string(tags)}"
        self._gauges[key] = value
        
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags
        )
        self._metrics.append(metric)
        
        logger.debug(
            "Gauge value set",
            name=name,
            value=value,
            tags=tags
        )
    
    def timer(
        self, 
        name: str,
        tags: dict[str, str] | None = None
    ) -> TimerContext:
        """Create a timer context for measuring duration."""
        return TimerContext(self, name, tags)
    
    def get_metrics(self) -> list[MetricValue]:
        """Get all collected metrics."""
        return self._metrics.copy()
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        logger.debug("Metrics reset")
    
    def get_counter_value(self, name: str, tags: dict[str, str] | None = None) -> float:
        """Get current counter value."""
        key = f"{name}:{self._tags_to_string(tags or {})}"
        return self._counters.get(key, 0.0)
    
    def get_gauge_value(self, name: str, tags: dict[str, str] | None = None) -> float | None:
        """Get current gauge value."""
        key = f"{name}:{self._tags_to_string(tags or {})}"
        return self._gauges.get(key)
    
    def get_histogram_values(self, name: str, tags: dict[str, str] | None = None) -> list[float]:
        """Get histogram values."""
        key = f"{name}:{self._tags_to_string(tags or {})}"
        return self._histograms.get(key, []).copy()
    
    def get_histogram_stats(self, name: str, tags: dict[str, str] | None = None) -> dict[str, float]:
        """Get histogram statistics (min, max, mean, percentiles)."""
        values = self.get_histogram_values(name, tags)
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        stats = {
            'count': n,
            'min': min(sorted_values),
            'max': max(sorted_values),
            'mean': sum(sorted_values) / n
        }
        
        # Calculate percentiles
        if n >= 2:
            stats['p50'] = self._percentile(sorted_values, 50)
            stats['p90'] = self._percentile(sorted_values, 90)
            stats['p95'] = self._percentile(sorted_values, 95)
            stats['p99'] = self._percentile(sorted_values, 99)
        
        return stats
    
    def _tags_to_string(self, tags: dict[str, str]) -> str:
        """Convert tags dict to string for keying."""
        if not tags:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    
    def _percentile(self, sorted_values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]


class NoOpMetricsCollector(MetricsCollector):
    """
    No-operation metrics collector.
    
    Provides the same interface but doesn't collect any metrics.
    Used when metrics are disabled.
    """
    
    def increment(
        self, 
        name: str, 
        value: float = 1.0, 
        tags: dict[str, str] | None = None
    ) -> None:
        """No-op increment."""
        pass
    
    def histogram(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """No-op histogram."""
        pass
    
    def gauge(
        self, 
        name: str, 
        value: float, 
        tags: dict[str, str] | None = None
    ) -> None:
        """No-op gauge."""
        pass
    
    def timer(
        self, 
        name: str,
        tags: dict[str, str] | None = None
    ) -> TimerContext:
        """Create a no-op timer context."""
        return NoOpTimerContext()
    
    def get_metrics(self) -> list[MetricValue]:
        """Return empty metrics list."""
        return []
    
    def reset(self) -> None:
        """No-op reset."""
        pass


class NoOpTimerContext:
    """No-operation timer context."""
    
    def __enter__(self) -> 'NoOpTimerContext':
        """No-op enter."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """No-op exit."""
        pass


class HealthMonitor:
    """
    Health monitoring for message bus components.
    
    Provides methods to register health checks and get overall status.
    """
    
    def __init__(self) -> None:
        """Initialize health monitor."""
        self._checks: dict[str, Callable[[], bool | asyncio.Future[bool]]] = {}
        self._last_check: dict[str, tuple[bool, float]] = {}
        self._check_timeout = 5.0  # seconds
    
    def register_check(
        self, 
        name: str, 
        check_func: Callable[[], bool | asyncio.Future[bool]]
    ) -> None:
        """Register a health check function."""
        self._checks[name] = check_func
        logger.debug("Health check registered", name=name)
    
    def unregister_check(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)
        self._last_check.pop(name, None)
        logger.debug("Health check unregistered", name=name)
    
    async def check_health(self) -> HealthStatus:
        """Run all health checks and return overall status."""
        checks = {}
        details = {}
        overall_healthy = True
        
        for name, check_func in self._checks.items():
            try:
                # Run check with timeout
                if asyncio.iscoroutinefunction(check_func):
                    result = await asyncio.wait_for(
                        check_func(), 
                        timeout=self._check_timeout
                    )
                else:
                    result = check_func()
                
                checks[name] = bool(result)
                self._last_check[name] = (bool(result), time.time())
                
                if not result:
                    overall_healthy = False
                    
            except TimeoutError:
                checks[name] = False
                overall_healthy = False
                details[name] = "Check timed out"
                logger.warning("Health check timed out", name=name)
                
            except Exception as e:
                checks[name] = False
                overall_healthy = False
                details[name] = f"Check failed: {e}"
                logger.error("Health check failed", name=name, error=str(e))
        
        status = "All checks passed" if overall_healthy else "Some checks failed"
        
        return HealthStatus(
            is_healthy=overall_healthy,
            status=status,
            checks=checks,
            details=details
        )
    
    def get_last_check_time(self, name: str) -> float | None:
        """Get timestamp of last check for a given health check."""
        if name in self._last_check:
            return self._last_check[name][1]
        return None
    
    def get_last_check_result(self, name: str) -> bool | None:
        """Get result of last check for a given health check."""
        if name in self._last_check:
            return self._last_check[name][0]
        return None


class MessageBusMonitor:
    """
    Comprehensive monitoring for message bus operations.
    
    Combines metrics collection and health monitoring.
    """
    
    def __init__(
        self, 
        metrics_enabled: bool = True,
        collector: MetricsCollector | None = None
    ) -> None:
        """
        Initialize message bus monitor.
        
        Args:
            metrics_enabled: Whether to collect metrics
            collector: Custom metrics collector (uses default if None)
        """
        self._metrics_enabled = metrics_enabled
        
        if collector:
            self._metrics = collector
        elif metrics_enabled:
            self._metrics = InMemoryMetricsCollector()
        else:
            self._metrics = NoOpMetricsCollector()
        
        self._health = HealthMonitor()
        
        # Register default health checks
        self._health.register_check("metrics_collector", self._check_metrics_health)
        
        logger.info(
            "Message bus monitor initialized",
            metrics_enabled=metrics_enabled,
            collector_type=type(self._metrics).__name__
        )
    
    @property
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        return self._metrics
    
    @property 
    def health(self) -> HealthMonitor:
        """Get health monitor."""
        return self._health
    
    def record_publish_attempt(self, event_type: str) -> None:
        """Record a publish attempt."""
        self._metrics.increment(
            "message_bus.publish.attempts",
            tags={"event_type": event_type}
        )
    
    def record_publish_success(self, event_type: str, duration_ms: float) -> None:
        """Record a successful publish."""
        self._metrics.increment(
            "message_bus.publish.success",
            tags={"event_type": event_type}
        )
        self._metrics.histogram(
            "message_bus.publish.duration",
            duration_ms,
            tags={"event_type": event_type}
        )
    
    def record_publish_failure(self, event_type: str, error_type: str) -> None:
        """Record a failed publish."""
        self._metrics.increment(
            "message_bus.publish.failures",
            tags={"event_type": event_type, "error_type": error_type}
        )
    
    def record_subscription_created(self, event_type: str) -> None:
        """Record a new subscription."""
        self._metrics.increment(
            "message_bus.subscription.created",
            tags={"event_type": event_type}
        )
    
    def record_subscription_removed(self, event_type: str) -> None:
        """Record a removed subscription."""
        self._metrics.increment(
            "message_bus.subscription.removed",
            tags={"event_type": event_type}
        )
    
    def record_message_received(self, event_type: str) -> None:
        """Record a received message."""
        self._metrics.increment(
            "message_bus.messages.received",
            tags={"event_type": event_type}
        )
    
    def record_message_processed(self, event_type: str, duration_ms: float) -> None:
        """Record a processed message."""
        self._metrics.increment(
            "message_bus.messages.processed",
            tags={"event_type": event_type}
        )
        self._metrics.histogram(
            "message_bus.processing.duration",
            duration_ms,
            tags={"event_type": event_type}
        )
    
    def record_message_failed(self, event_type: str, error_type: str) -> None:
        """Record a failed message processing."""
        self._metrics.increment(
            "message_bus.messages.failed",
            tags={"event_type": event_type, "error_type": error_type}
        )
    
    def record_dlq_entry(self, reason: str) -> None:
        """Record a DLQ entry."""
        self._metrics.increment(
            "message_bus.dlq.entries",
            tags={"reason": reason}
        )
    
    def record_dlq_requeue(self, count: int) -> None:
        """Record DLQ requeue operation."""
        self._metrics.increment("message_bus.dlq.requeue.operations")
        self._metrics.histogram("message_bus.dlq.requeue.count", count)
    
    def set_active_connections(self, count: int) -> None:
        """Set number of active connections."""
        self._metrics.gauge("message_bus.connections.active", count)
    
    def set_queue_depth(self, queue_name: str, depth: int) -> None:
        """Set queue depth."""
        self._metrics.gauge(
            "message_bus.queue.depth",
            depth,
            tags={"queue": queue_name}
        )
    
    async def _check_metrics_health(self) -> bool:
        """Check if metrics collector is healthy."""
        try:
            # Try to get metrics to verify collector is working
            self._metrics.get_metrics()
            return True
        except Exception as e:
            logger.error("Metrics collector health check failed", error=str(e))
            return False


# Global monitor instance
_global_monitor: MessageBusMonitor | None = None


def get_monitor(metrics_enabled: bool = True) -> MessageBusMonitor:
    """Get or create global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = MessageBusMonitor(metrics_enabled=metrics_enabled)
    return _global_monitor


def reset_monitor() -> None:
    """Reset global monitor instance."""
    global _global_monitor
    _global_monitor = None
