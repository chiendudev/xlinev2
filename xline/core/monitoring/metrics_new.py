import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    event_count: int = 0
    total_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_latency_sample(self, latency: float) -> None:
        """Add latency sample and update metrics."""
        self.event_count += 1
        self.total_latency += latency
        self.min_latency = min(self.min_latency, latency)
        self.max_latency = max(self.max_latency, latency)
        self.latency_samples.append(latency)
        
    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        return self.total_latency / self.event_count if self.event_count > 0 else 0.0
        
    @property
    def p99_latency(self) -> float:
        """Calculate 99th percentile latency."""
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        index = int(0.99 * len(sorted_samples))
        return sorted_samples[index] if index < len(sorted_samples) else 0.0


class MetricsCollector:
    """Collect and aggregate performance metrics."""
    
    def __init__(self) -> None:
        self.metrics: dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.start_time = time.time()
        
    def record_event_latency(self, event_type: str, latency: float) -> None:
        """Record event processing latency."""
        self.metrics[event_type].add_latency_sample(latency)
        
    def get_summary(self) -> dict[str, Any]:
        """Get performance summary."""
        summary = {}
        for event_type, metrics in self.metrics.items():
            summary[event_type] = {
                "count": metrics.event_count,
                "avg_latency_ms": metrics.avg_latency * 1000,
                "p99_latency_ms": metrics.p99_latency * 1000,
                "min_latency_ms": metrics.min_latency * 1000,
                "max_latency_ms": metrics.max_latency * 1000
            }
        return summary
