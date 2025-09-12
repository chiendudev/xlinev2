"""
System Health Monitoring for Xline Analytics
Provides real-time monitoring of system health, performance metrics, and resource usage.
"""

import logging
import psutil
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of monitoring metrics"""
    SYSTEM = "system"
    APPLICATION = "application"
    TRADING = "trading"
    PERFORMANCE = "performance"


@dataclass
class HealthMetric:
    """Individual health metric data"""
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: MetricType = MetricType.SYSTEM
    
    def is_healthy(self) -> bool:
        """Check if metric is in healthy range"""
        return self.status == HealthStatus.HEALTHY
    
    def update_status(self) -> None:
        """Update status based on thresholds"""
        if self.value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY


@dataclass
class SystemHealth:
    """Overall system health summary"""
    overall_status: HealthStatus
    metrics: dict[str, HealthMetric]
    last_updated: datetime = field(default_factory=datetime.now)
    uptime: float = 0.0
    error_count: int = 0
    warning_count: int = 0

    def get_critical_issues(self) -> list[HealthMetric]:
        """Get all critical health issues"""
        return [metric for metric in self.metrics.values()
                if metric.status == HealthStatus.CRITICAL]

    def get_warnings(self) -> list[HealthMetric]:
        """Get all warning-level issues"""
        return [metric for metric in self.metrics.values()
                if metric.status == HealthStatus.WARNING]


class SystemMonitor:
    """System health monitoring service"""
    
    def __init__(self):
        self.start_time = time.time()
        self._metrics_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        
        # Monitoring configuration
        self.monitor_interval = 5.0  # seconds
        self.history_retention = 3600  # 1 hour in seconds
        
        # System thresholds
        self.cpu_warning_threshold = 70.0  # percent
        self.cpu_critical_threshold = 90.0
        self.memory_warning_threshold = 80.0  # percent
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 85.0  # percent
        self.disk_critical_threshold = 95.0
        
    def start_monitoring(self) -> None:
        """Start continuous system monitoring"""
        if self._running:
            logger.warning("Monitoring already running")
            return
            
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop system monitoring"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_system_metrics()
                time.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitor_interval)
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        timestamp = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_metric = HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.cpu_warning_threshold,
            threshold_critical=self.cpu_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        cpu_metric.update_status()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_metric = HealthMetric(
            name="memory_usage",
            value=memory.percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.memory_warning_threshold,
            threshold_critical=self.memory_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        memory_metric.update_status()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_metric = HealthMetric(
            name="disk_usage",
            value=disk_percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.disk_warning_threshold,
            threshold_critical=self.disk_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        disk_metric.update_status()
        
        # Store metrics with thread safety
        with self._lock:
            self._metrics_history["cpu_usage"].append((timestamp, cpu_percent))
            self._metrics_history["memory_usage"].append((timestamp, memory.percent))
            self._metrics_history["disk_usage"].append((timestamp, disk_percent))
    
    def get_current_health(self) -> SystemHealth:
        """Get current system health status"""
        timestamp = datetime.now()
        
        # Collect current metrics with error handling
        try:
            cpu_percent = psutil.cpu_percent()
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {e}")
            cpu_percent = 0.0
            
        try:
            memory = psutil.virtual_memory()
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            # Create fallback memory object
            from collections import namedtuple
            Memory = namedtuple('Memory', ['percent'])
            memory = Memory(percent=0.0)
            
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")
            disk_percent = 0.0
        
        # Create health metrics
        metrics = {}
        
        # CPU metric
        cpu_metric = HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.cpu_warning_threshold,
            threshold_critical=self.cpu_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        cpu_metric.update_status()
        metrics["cpu_usage"] = cpu_metric
        
        # Memory metric
        memory_metric = HealthMetric(
            name="memory_usage",
            value=memory.percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.memory_warning_threshold,
            threshold_critical=self.memory_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        memory_metric.update_status()
        metrics["memory_usage"] = memory_metric
        
        # Disk metric
        disk_metric = HealthMetric(
            name="disk_usage",
            value=disk_percent,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=self.disk_warning_threshold,
            threshold_critical=self.disk_critical_threshold,
            timestamp=timestamp,
            metric_type=MetricType.SYSTEM
        )
        disk_metric.update_status()
        metrics["disk_usage"] = disk_metric
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        critical_count = sum(1 for m in metrics.values() if m.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for m in metrics.values() if m.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        
        # Calculate uptime
        uptime = time.time() - self.start_time
        
        return SystemHealth(
            overall_status=overall_status,
            metrics=metrics,
            last_updated=timestamp,
            uptime=uptime,
            error_count=critical_count,
            warning_count=warning_count
        )
    
    def get_metric_history(self, metric_name: str, duration_minutes: int = 60) -> list[tuple[datetime, float]]:
        """Get historical data for a specific metric"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)

        with self._lock:
            history = self._metrics_history.get(metric_name, deque())
            return [(ts, value) for ts, value in history if ts >= cutoff_time]

    def get_system_summary(self) -> dict[str, Any]:
        """Get comprehensive system summary"""
        health = self.get_current_health()
        
        return {
            "timestamp": health.last_updated.isoformat(),
            "overall_status": health.overall_status.value,
            "uptime_seconds": health.uptime,
            "uptime_formatted": self._format_uptime(health.uptime),
            "metrics": {
                name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value,
                    "threshold_warning": metric.threshold_warning,
                    "threshold_critical": metric.threshold_critical
                }
                for name, metric in health.metrics.items()
            },
            "issues": {
                "critical": len(health.get_critical_issues()),
                "warnings": len(health.get_warnings())
            }
        }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class ApplicationMonitor:
    """Application-specific monitoring for Xline Analytics"""
    
    def __init__(self):
        self._application_metrics: dict[str, Any] = {}
        self._trading_metrics: dict[str, Any] = {}
        self._performance_metrics: dict[str, Any] = {}
        self._lock = threading.Lock()
        
    def track_trading_event(self, event_type: str, processing_time: float) -> None:
        """Track trading event processing metrics"""
        with self._lock:
            if event_type not in self._trading_metrics:
                self._trading_metrics[event_type] = {
                    "count": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                    "max_time": 0.0,
                    "min_time": float('inf')
                }
            
            metrics = self._trading_metrics[event_type]
            metrics["count"] += 1
            metrics["total_time"] += processing_time
            metrics["avg_time"] = metrics["total_time"] / metrics["count"]
            metrics["max_time"] = max(metrics["max_time"], processing_time)
            metrics["min_time"] = min(metrics["min_time"], processing_time)
    
    def track_analytics_performance(self, operation: str, execution_time: float, success: bool) -> None:
        """Track analytics operation performance"""
        with self._lock:
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = {
                    "success_count": 0,
                    "error_count": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                    "success_rate": 0.0
                }
            
            metrics = self._performance_metrics[operation]
            if success:
                metrics["success_count"] += 1
            else:
                metrics["error_count"] += 1
            
            total_operations = metrics["success_count"] + metrics["error_count"]
            metrics["total_time"] += execution_time
            metrics["avg_time"] = metrics["total_time"] / total_operations
            metrics["success_rate"] = metrics["success_count"] / total_operations
    
    def get_application_health(self) -> dict[str, Any]:
        """Get application-specific health metrics"""
        with self._lock:
            return {
                "trading_events": dict(self._trading_metrics),
                "analytics_performance": dict(self._performance_metrics),
                "timestamp": datetime.now().isoformat()
            }


# Global monitoring instances
system_monitor = SystemMonitor()
application_monitor = ApplicationMonitor()


def get_comprehensive_health() -> dict[str, Any]:
    """Get comprehensive system and application health"""
    system_health = system_monitor.get_system_summary()
    app_health = application_monitor.get_application_health()
    
    return {
        "system": system_health,
        "application": app_health,
        "overall_status": system_health["overall_status"],
        "timestamp": datetime.now().isoformat()
    }


# Context manager for performance tracking
class PerformanceTracker:
    """Context manager for tracking operation performance"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            execution_time = time.time() - self.start_time
            self.success = exc_type is None
            application_monitor.track_analytics_performance(
                self.operation_name, execution_time, self.success
            )
        return False  # Don't suppress exceptions
