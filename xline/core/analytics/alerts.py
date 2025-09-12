"""
Alert System for Xline Analytics
Provides comprehensive alerting capabilities for system health, trading events, and performance issues.
"""

import logging
import smtplib
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable

from .monitoring import HealthStatus, system_monitor, application_monitor

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    SYSTEM_HEALTH = "system_health"
    TRADING_PERFORMANCE = "trading_performance"
    APPLICATION_ERROR = "application_error"
    THRESHOLD_BREACH = "threshold_breach"
    CONNECTIVITY = "connectivity"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: Callable[[dict], bool]
    threshold: float = 0.0
    cooldown_minutes: int = 15
    enabled: bool = True
    description: str = ""
    recipients: list[str] = field(default_factory=list)
    last_triggered: datetime | None = None

    def can_trigger(self) -> bool:
        """Check if rule can trigger based on cooldown"""
        if not self.enabled:
            return False
        if self.last_triggered is None:
            return True
        cooldown_period = timedelta(minutes=self.cooldown_minutes)
        return datetime.now() - self.last_triggered > cooldown_period

    def should_trigger(self, data: dict) -> bool:
        """Check if rule should trigger based on condition"""
        try:
            return self.can_trigger() and self.condition(data)
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.name}: {e}")
            return False


@dataclass
class Alert:
    """Individual alert instance"""
    rule_name: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: datetime | None = None

    def acknowledge(self) -> None:
        """Mark alert as acknowledged"""
        self.acknowledged = True

    def resolve(self) -> None:
        """Mark alert as resolved"""
        self.resolved = True
        self.resolution_time = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "rule_name": self.rule_name,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }


class EmailNotifier:
    """Email notification service"""

    def __init__(self, smtp_server: str = "", smtp_port: int = 587,
                 username: str = "", password: str = ""):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.enabled = bool(smtp_server and username)

    def send_alert(self, alert: Alert, recipients: list[str]) -> bool:
        """Send alert via email"""
        if not self.enabled or not recipients:
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            body = self._format_alert_email(alert)
            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Alert email sent: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False

    def _format_alert_email(self, alert: Alert) -> str:
        """Format alert as HTML email"""
        severity_colors = {
            AlertSeverity.INFO: "#17a2b8",
            AlertSeverity.WARNING: "#ffc107",
            AlertSeverity.ERROR: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }

        color = severity_colors.get(alert.severity, "#6c757d")

        return f"""
        <html>
        <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                <h2 style="margin: 0;">{alert.title}</h2>
                <p style="margin: 5px 0 0 0;">Severity: {alert.severity.value.title()}</p>
            </div>
            <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                <p><strong>Message:</strong></p>
                <p>{alert.message}</p>
                
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Alert Type:</strong> {alert.alert_type.value.replace('_', ' ').title()}</p>
                
                {self._format_alert_data(alert.data) if alert.data else ''}
            </div>
        </div>
        </body>
        </html>
        """

    def _format_alert_data(self, data: dict) -> str:
        """Format alert data for email"""
        if not data:
            return ""

        items = []
        for key, value in data.items():
            if isinstance(value, float):
                value = f"{value:.2f}"
            items.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")

        return f"""
        <p><strong>Additional Data:</strong></p>
        <ul>
        {''.join(items)}
        </ul>
        """


class AlertManager:
    """Central alert management system"""

    def __init__(self):
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._alert_history: deque = deque(maxlen=10000)
        self._notifiers: list = []
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: threading.Thread | None = None

        # Alert statistics
        self._alert_stats = defaultdict(int)

        # Setup default rules
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default alert rules"""
        # System health rules
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            condition=lambda data: data.get("system", {}).get("metrics", {}).get("cpu_usage", {}).get("value", 0) > 80,
            threshold=80.0,
            cooldown_minutes=10,
            description="CPU usage above 80%"
        ))

        self.add_rule(AlertRule(
            name="critical_cpu_usage",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.CRITICAL,
            condition=lambda data: data.get("system", {}).get("metrics", {}).get("cpu_usage", {}).get("value", 0) > 95,
            threshold=95.0,
            cooldown_minutes=5,
            description="CPU usage above 95%"
        ))

        self.add_rule(AlertRule(
            name="high_memory_usage",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            condition=lambda data: data.get("system", {}).get("metrics", {}).get("memory_usage", {}).get("value", 0) > 85,
            threshold=85.0,
            cooldown_minutes=10,
            description="Memory usage above 85%"
        ))

        self.add_rule(AlertRule(
            name="disk_space_warning",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            condition=lambda data: data.get("system", {}).get("metrics", {}).get("disk_usage", {}).get("value", 0) > 90,
            threshold=90.0,
            cooldown_minutes=30,
            description="Disk usage above 90%"
        ))

        # Trading performance rules
        self.add_rule(AlertRule(
            name="trading_errors",
            alert_type=AlertType.TRADING_PERFORMANCE,
            severity=AlertSeverity.ERROR,
            condition=lambda data: self._check_trading_errors(data),
            cooldown_minutes=5,
            description="High rate of trading errors detected"
        ))

    def _check_trading_errors(self, data: dict) -> bool:
        """Check for trading error patterns"""
        app_data = data.get("application", {})
        trading_events = app_data.get("trading_events", {})

        # Check for high error rates in any trading event type
        for event_type, metrics in trading_events.items():
            if isinstance(metrics, dict):
                count = metrics.get("count", 0)
                avg_time = metrics.get("avg_time", 0)
                # Alert if processing time is too high (> 1 second)
                if count > 0 and avg_time > 1.0:
                    return True

        return False

    def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule"""
        with self._lock:
            self._rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove alert rule"""
        with self._lock:
            if rule_name in self._rules:
                del self._rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
                return True
        return False

    def get_rule(self, rule_name: str) -> AlertRule | None:
        """Get alert rule by name"""
        with self._lock:
            return self._rules.get(rule_name)

    def list_rules(self) -> list[AlertRule]:
        """List all alert rules"""
        with self._lock:
            return list(self._rules.values())

    def add_notifier(self, notifier) -> None:
        """Add notification service"""
        self._notifiers.append(notifier)
        logger.info(f"Added notifier: {type(notifier).__name__}")

    def start_monitoring(self) -> None:
        """Start alert monitoring"""
        if self._running:
            logger.warning("Alert monitoring already running")
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Alert monitoring started")

    def stop_monitoring(self) -> None:
        """Stop alert monitoring"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        logger.info("Alert monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                self._check_all_rules()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                time.sleep(30)

    def _check_all_rules(self) -> None:
        """Check all alert rules against current data"""
        try:
            # Get current system and application data
            system_health = system_monitor.get_system_summary()
            app_health = application_monitor.get_application_health()

            data = {
                "system": system_health,
                "application": app_health,
                "timestamp": datetime.now().isoformat()
            }

            # Check each rule
            with self._lock:
                for rule in self._rules.values():
                    if rule.should_trigger(data):
                        self._trigger_alert(rule, data)

        except Exception as e:
            logger.error(f"Error checking alert rules: {e}")

    def _trigger_alert(self, rule: AlertRule, data: dict) -> None:
        """Trigger an alert"""
        # Create alert
        alert = Alert(
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=f"{rule.name.replace('_', ' ').title()}",
            message=rule.description or f"Alert condition met for {rule.name}",
            data=self._extract_relevant_data(rule, data)
        )

        # Update rule trigger time
        rule.last_triggered = datetime.now()

        # Store alert
        with self._lock:
            self._alerts.append(alert)
            self._alert_history.append(alert)
            self._alert_stats[rule.alert_type.value] += 1
            self._alert_stats[f"{rule.severity.value}_count"] += 1

        # Send notifications
        self._send_notifications(alert, rule.recipients)

        logger.warning(f"Alert triggered: {alert.title} - {alert.message}")

    def _extract_relevant_data(self, rule: AlertRule, data: dict) -> dict[str, Any]:
        """Extract relevant data for alert"""
        relevant_data = {}

        if rule.alert_type == AlertType.SYSTEM_HEALTH:
            system_data = data.get("system", {})
            relevant_data.update({
                "overall_status": system_data.get("overall_status"),
                "uptime": system_data.get("uptime_formatted"),
                "critical_issues": system_data.get("issues", {}).get("critical", 0),
                "warnings": system_data.get("issues", {}).get("warnings", 0)
            })

            # Add specific metric if available
            metrics = system_data.get("metrics", {})
            for metric_name, metric_data in metrics.items():
                if metric_name in rule.name:
                    relevant_data[f"{metric_name}_value"] = metric_data.get("value")
                    relevant_data[f"{metric_name}_status"] = metric_data.get("status")

        elif rule.alert_type == AlertType.TRADING_PERFORMANCE:
            app_data = data.get("application", {})
            relevant_data.update({
                "trading_events": app_data.get("trading_events", {}),
                "analytics_performance": app_data.get("analytics_performance", {})
            })

        return relevant_data

    def _send_notifications(self, alert: Alert, recipients: list[str]) -> None:
        """Send alert notifications"""
        for notifier in self._notifiers:
            try:
                if hasattr(notifier, 'send_alert'):
                    notifier.send_alert(alert, recipients)
            except Exception as e:
                logger.error(f"Failed to send notification via {type(notifier).__name__}: {e}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all active (unresolved) alerts"""
        with self._lock:
            return [alert for alert in self._alerts if not alert.resolved]

    def get_alert_history(self, hours: int = 24) -> list[Alert]:
        """Get alert history for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self._lock:
            return [alert for alert in self._alert_history
                    if alert.timestamp >= cutoff_time]

    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert"""
        with self._lock:
            if 0 <= alert_index < len(self._alerts):
                self._alerts[alert_index].acknowledge()
                return True
        return False

    def resolve_alert(self, alert_index: int) -> bool:
        """Resolve an alert"""
        with self._lock:
            if 0 <= alert_index < len(self._alerts):
                self._alerts[alert_index].resolve()
                return True
        return False

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics"""
        with self._lock:
            active_alerts = len([a for a in self._alerts if not a.resolved])
            total_alerts = len(self._alert_history)

            return {
                "active_alerts": active_alerts,
                "total_alerts_24h": total_alerts,
                "alert_types": dict(self._alert_stats),
                "rules_count": len(self._rules),
                "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
                "last_check": datetime.now().isoformat()
            }

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get alert data for dashboard"""
        active_alerts = self.get_active_alerts()
        recent_alerts = self.get_alert_history(hours=1)
        stats = self.get_alert_statistics()

        return {
            "active_alerts": [alert.to_dict() for alert in active_alerts[:10]],  # Last 10
            "recent_alerts": [alert.to_dict() for alert in recent_alerts[:20]],  # Last 20
            "statistics": stats,
            "severity_breakdown": {
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "error": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR]),
                "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO])
            }
        }


# Global alert manager instance
alert_manager = AlertManager()


def setup_email_alerts(smtp_server: str, smtp_port: int, username: str, password: str) -> None:
    """Setup email notifications"""
    email_notifier = EmailNotifier(smtp_server, smtp_port, username, password)
    alert_manager.add_notifier(email_notifier)
    logger.info("Email alerts configured")


def trigger_test_alert() -> None:
    """Trigger a test alert for verification"""
    test_rule = AlertRule(
        name="test_alert",
        alert_type=AlertType.APPLICATION_ERROR,
        severity=AlertSeverity.INFO,
        condition=lambda data: True,  # Always trigger
        description="Test alert for system verification"
    )

    alert_manager.add_rule(test_rule)
    # The alert will be triggered on next monitoring cycle
    logger.info("Test alert rule added - will trigger on next monitoring cycle")
