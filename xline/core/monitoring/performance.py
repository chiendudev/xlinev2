"""
System and application performance monitoring for Xline trading system.

Provides comprehensive performance monitoring including system resource tracking,
event latency measurement, and real-time threshold monitoring for optimal
trading system performance.
"""

import asyncio
import psutil
import time
from typing import Any

from xline.core.events.bus import InMemoryEventBus
from xline.core.monitoring.metrics import MetricsCollector


class PerformanceMonitor:
    """
    Comprehensive system and application performance monitoring.
    
    Monitors system resources, event processing latency, and provides
    real-time alerts when performance thresholds are exceeded.
    Designed for minimal overhead in high-frequency trading environments.
    
    Example:
        >>> event_bus = InMemoryEventBus()
        >>> monitor = PerformanceMonitor(event_bus)
        >>> await monitor.start_monitoring()
        >>> # System will now track all event latencies
        >>> report = monitor.get_performance_report()
        >>> await monitor.stop_monitoring()
    """
    
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        """
        Initialize performance monitor with event bus integration.
        
        Args:
            event_bus: Event bus instance to monitor for performance
            
        Example:
            >>> event_bus = InMemoryEventBus()
            >>> monitor = PerformanceMonitor(event_bus)
            >>> assert monitor.event_bus is event_bus
            >>> assert not monitor.is_monitoring
        """
        self.event_bus = event_bus
        self.metrics_collector = MetricsCollector()
        self.system_stats: dict[str, Any] = {}
        self.is_monitoring = False
        self._original_publish = None
        self._monitoring_task = None
        
    async def start_monitoring(self) -> None:
        """
        Start comprehensive performance monitoring.
        
        Begins system resource monitoring loop and hooks into event bus
        for latency tracking. Monitoring runs in background task.
        
        Example:
            >>> monitor = PerformanceMonitor(event_bus)
            >>> await monitor.start_monitoring()
            >>> assert monitor.is_monitoring
        """
        self.is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        # Hook into event bus for latency measurement
        self._setup_latency_tracking()
        
    async def stop_monitoring(self) -> None:
        """
        Stop performance monitoring and restore original event bus.
        
        Stops monitoring loop and restores original event bus publish
        method to remove monitoring overhead.
        
        Example:
            >>> await monitor.start_monitoring()
            >>> await monitor.stop_monitoring()
            >>> assert not monitor.is_monitoring
        """
        self.is_monitoring = False

        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None

        # Restore original publish method
        if self._original_publish is not None:
            self.event_bus.publish = self._original_publish
            self._original_publish = None
        
    def _setup_latency_tracking(self) -> None:
        """
        Setup event latency tracking with minimal overhead.
        
        Wraps event bus publish method to measure processing latency
        without significantly impacting performance.
        """
        if self._original_publish is None:
            self._original_publish = self.event_bus.publish
        
        async def tracked_publish(event):
            start_time = time.perf_counter()
            result = await self._original_publish(event)
            latency = time.perf_counter() - start_time
            self.metrics_collector.record_event_latency(
                str(event.type), latency
            )
            return result
            
        self.event_bus.publish = tracked_publish
        
    async def _monitoring_loop(self) -> None:
        """
        Main monitoring loop for system resource tracking.
        
        Continuously monitors CPU, memory usage and checks performance
        thresholds. Runs with 1-second intervals for balance between
        accuracy and overhead.
        """
        while self.is_monitoring:
            try:
                # Collect system metrics
                self.system_stats = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
                    "timestamp": time.time()
                }
                
                # Check performance thresholds
                await self._check_performance_thresholds()
                
                await asyncio.sleep(1)  # Monitor every second
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                
    async def _check_performance_thresholds(self) -> None:
        """
        Check if performance thresholds are exceeded and alert.
        
        Monitors P99 latency target of <1ms and memory usage <80%.
        Prints warnings when thresholds are exceeded for immediate
        attention in trading environments.
        """
        summary = self.metrics_collector.get_summary()
        
        for event_type, metrics in summary.items():
            if metrics["p99_latency_ms"] > 1.0:  # > 1ms threshold
                print(
                    f"WARNING: {event_type} P99 latency exceeded: "
                    f"{metrics['p99_latency_ms']:.2f}ms"
                )
                
        if self.system_stats.get("memory_percent", 0) > 80:
            print(f"WARNING: High memory usage: {self.system_stats['memory_percent']:.1f}%")
            
    def get_performance_report(self) -> dict[str, Any]:
        """
        Get comprehensive performance report for analysis.
        
        Returns:
            Complete performance report including event metrics,
            system statistics, and monitoring duration
            
        Example:
            >>> report = monitor.get_performance_report()
            >>> assert "event_metrics" in report
            >>> assert "system_stats" in report
            >>> assert "monitoring_duration" in report
        """
        return {
            "event_metrics": self.metrics_collector.get_summary(),
            "system_stats": self.system_stats,
            "monitoring_duration": time.time() - self.metrics_collector.start_time
        }
