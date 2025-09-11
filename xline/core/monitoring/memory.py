"""
Memory optimization utilities for Xline trading system.

Provides event object pooling, memory leak detection, and garbage collection
monitoring to ensure optimal memory usage in high-frequency trading environments.
"""

import gc
import weakref
from typing import Any, Optional
from collections import deque

from xline.core.events.types import Event, EventType, OrderEvent


class EventPool:
    """
    High-performance event object pooling for memory optimization.
    
    Reuses event objects to minimize garbage collection overhead
    and memory allocation in high-frequency trading scenarios.
    
    Example:
        >>> pool = EventPool()
        >>> event = pool.get_event(EventType.PRICE_TICK, {"symbol": "BTCUSD"}, "feed")
        >>> pool.return_event(event)
        >>> # Event object is now available for reuse
    """
    
    def __init__(self, pool_size: int = 1000) -> None:
        """
        Initialize event pool with specified size.
        
        Args:
            pool_size: Maximum number of events to pool
        """
        self.pool_size = pool_size
        self._pool: deque[Event] = deque(maxlen=pool_size)
        self._active_events: weakref.WeakSet[Event] = weakref.WeakSet()
        
    def get_event(self, event_type: EventType, data: dict[str, Any], source: str) -> Event:
        """
        Get event from pool or create new one if pool is empty.
        
        Args:
            event_type: Type of event to create/reuse
            data: Event data payload
            source: Event source identifier
            
        Returns:
            Event object ready for use
            
        Example:
            >>> pool = EventPool()
            >>> event = pool.get_event(EventType.ORDER_CREATED, {"order_id": "123"}, "test")
            >>> assert event.event_type == EventType.ORDER_CREATED
        """
        if self._pool:
            event = self._pool.popleft()
            # Reset event for reuse
            event.type = event_type
            event.data = data
            event.source = source
            event.timestamp = event._generate_timestamp()
        else:
            from decimal import Decimal
            event = OrderEvent(
                type=event_type,
                source=source,
                order_id=f"pool_{event_type.value}",
                account_id="POOL_ACCOUNT",
                symbol=data.get("symbol", "DEFAULT"),
                side="BUY",
                quantity=Decimal(str(data.get("quantity", 1.0))),
                price=Decimal(str(data.get("price", 0.0))),
                order_type="LIMIT"
            )
            
        self._active_events.add(event)
        return event
        
    def return_event(self, event: Event) -> None:
        """
        Return event to pool for reuse.
        
        Args:
            event: Event object to return to pool
            
        Example:
            >>> pool = EventPool()
            >>> event = pool.get_event(EventType.TRADE_EXECUTED, {}, "test")
            >>> pool.return_event(event)
            >>> assert len(pool._pool) == 1
        """
        if event in self._active_events:
            self._active_events.discard(event)
            
            # Clear sensitive data before pooling
            event.data.clear()
            
            if len(self._pool) < self.pool_size:
                self._pool.append(event)
                
    def get_pool_stats(self) -> dict[str, Any]:
        """
        Get pool statistics for monitoring.
        
        Returns:
            Dictionary with pool size, active events count
        """
        return {
            "pool_size": len(self._pool),
            "active_events": len(self._active_events),
            "pool_capacity": self.pool_size
        }


class MemoryMonitor:
    """
    Memory leak detection and garbage collection monitoring.
    
    Tracks memory usage patterns and detects potential memory leaks
    in long-running trading systems.
    
    Example:
        >>> monitor = MemoryMonitor()
        >>> monitor.start_monitoring()
        >>> # System operations...
        >>> stats = monitor.get_memory_stats()
        >>> monitor.stop_monitoring()
    """
    
    def __init__(self) -> None:
        """Initialize memory monitor with baseline measurements."""
        self.baseline_objects = len(gc.get_objects())
        self.gc_collections = {gen: gc.get_count()[gen] for gen in range(3)}
        self.is_monitoring = False
        self._snapshots: list[dict[str, Any]] = []
        
    def start_monitoring(self) -> None:
        """
        Start memory monitoring with baseline snapshot.
        
        Example:
            >>> monitor = MemoryMonitor()
            >>> monitor.start_monitoring()
            >>> assert monitor.is_monitoring
        """
        self.is_monitoring = True
        self._take_snapshot("baseline")
        
    def stop_monitoring(self) -> None:
        """
        Stop memory monitoring and analyze trends.
        
        Example:
            >>> monitor.start_monitoring()
            >>> monitor.stop_monitoring()
            >>> assert not monitor.is_monitoring
        """
        self.is_monitoring = False
        if self._snapshots:
            self._take_snapshot("final")
            
    def _take_snapshot(self, label: str) -> None:
        """Take memory usage snapshot."""
        gc.collect()  # Force garbage collection
        
        snapshot = {
            "label": label,
            "total_objects": len(gc.get_objects()),
            "gc_counts": gc.get_count(),
            "uncollectable": len(gc.garbage) if hasattr(gc, 'garbage') else 0
        }
        
        self._snapshots.append(snapshot)
        
    def force_gc(self) -> dict[str, Any]:
        """
        Force garbage collection and return statistics.
        
        Returns:
            Garbage collection statistics
            
        Example:
            >>> monitor = MemoryMonitor()
            >>> stats = monitor.force_gc()
            >>> assert "objects_collected" in stats
        """
        objects_before = len(gc.get_objects())
        collected = gc.collect()
        objects_after = len(gc.get_objects())
        
        return {
            "objects_collected": collected,
            "objects_before": objects_before,
            "objects_after": objects_after,
            "objects_freed": objects_before - objects_after
        }
        
    def detect_memory_leaks(self) -> dict[str, Any]:
        """
        Analyze snapshots to detect potential memory leaks.
        
        Returns:
            Memory leak analysis results
            
        Example:
            >>> monitor = MemoryMonitor()
            >>> monitor.start_monitoring()
            >>> # ... operations ...
            >>> monitor.stop_monitoring()
            >>> leaks = monitor.detect_memory_leaks()
            >>> assert "object_growth" in leaks
        """
        if len(self._snapshots) < 2:
            return {"warning": "Insufficient snapshots for leak detection"}
            
        baseline = self._snapshots[0]
        latest = self._snapshots[-1]
        
        object_growth = latest["total_objects"] - baseline["total_objects"]
        gc_efficiency = sum(latest["gc_counts"]) - sum(baseline["gc_counts"])
        
        return {
            "object_growth": object_growth,
            "gc_collections": gc_efficiency,
            "uncollectable_objects": latest["uncollectable"],
            "potential_leak": object_growth > 1000,  # Threshold for concern
            "snapshots": len(self._snapshots)
        }
        
    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get comprehensive memory statistics.
        
        Returns:
            Complete memory usage and GC statistics
        """
        return {
            "current_objects": len(gc.get_objects()),
            "baseline_objects": self.baseline_objects,
            "object_growth": len(gc.get_objects()) - self.baseline_objects,
            "gc_counts": gc.get_count(),
            "monitoring_active": self.is_monitoring,
            "snapshots_taken": len(self._snapshots)
        }


class OptimizedEventBus:
    """
    Memory-optimized event bus wrapper with object pooling.
    
    Extends the standard event bus with automatic event pooling
    to reduce memory allocation overhead.
    """
    
    def __init__(self, event_bus, pool_size: int = 1000) -> None:
        """
        Initialize optimized event bus with pooling.
        
        Args:
            event_bus: Underlying event bus implementation
            pool_size: Size of event object pool
        """
        self.event_bus = event_bus
        self.event_pool = EventPool(pool_size)
        self.memory_monitor = MemoryMonitor()
        
    async def publish_optimized(self, event_type: EventType, data: dict[str, Any], source: str) -> None:
        """
        Publish event using object pooling for memory efficiency.
        
        Args:
            event_type: Type of event to publish
            data: Event data payload
            source: Event source identifier
        """
        event = self.event_pool.get_event(event_type, data, source)
        try:
            await self.event_bus.publish(event)
        finally:
            # Return event to pool after publishing
            self.event_pool.return_event(event)
            
    def get_optimization_stats(self) -> dict[str, Any]:
        """
        Get memory optimization statistics.
        
        Returns:
            Combined pool and memory statistics
        """
        return {
            "event_pool": self.event_pool.get_pool_stats(),
            "memory_stats": self.memory_monitor.get_memory_stats()
        }
