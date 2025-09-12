"""
Integration tests for Analytics System Day 6: Production Monitoring
Tests monitoring, alerts, and API integration functionality.
"""

import json
import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from xline.core.analytics.monitoring import (
    SystemMonitor, ApplicationMonitor, HealthStatus, HealthMetric,
    SystemHealth, get_comprehensive_health, PerformanceTracker
)
from xline.core.analytics.alerts import (
    AlertManager, AlertRule, AlertType, AlertSeverity, EmailNotifier,
    alert_manager, trigger_test_alert
)
from xline.core.analytics.api import (
    AnalyticsAPIServer, start_api_server, get_api_status
)


class TestSystemMonitoring:
    """Test system monitoring functionality"""

    def test_system_monitor_initialization(self):
        """Test system monitor initialization"""
        monitor = SystemMonitor()
        
        assert monitor.start_time > 0
        assert not monitor._running
        assert monitor._monitor_thread is None
        assert monitor.monitor_interval == 5.0

    def test_health_metric_creation(self):
        """Test health metric creation and status updates"""
        metric = HealthMetric(
            name="test_metric",
            value=75.0,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=80.0,
            threshold_critical=95.0
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 75.0
        assert metric.is_healthy()
        
        # Test status update
        metric.value = 85.0
        metric.update_status()
        assert metric.status == HealthStatus.WARNING
        
        metric.value = 97.0
        metric.update_status()
        assert metric.status == HealthStatus.CRITICAL

    def test_system_health_summary(self):
        """Test system health summary functionality"""
        metrics = {
            "cpu": HealthMetric(
                name="cpu",
                value=60.0,
                unit="%",
                status=HealthStatus.HEALTHY,
                threshold_warning=80.0,
                threshold_critical=95.0
            ),
            "memory": HealthMetric(
                name="memory",
                value=85.0,
                unit="%",
                status=HealthStatus.WARNING,
                threshold_warning=80.0,
                threshold_critical=95.0
            )
        }
        
        health = SystemHealth(
            overall_status=HealthStatus.WARNING,
            metrics=metrics,
            uptime=3600.0,
            error_count=0,
            warning_count=1
        )
        
        assert health.overall_status == HealthStatus.WARNING
        assert len(health.get_warnings()) == 1
        assert len(health.get_critical_issues()) == 0

    def test_get_current_health(self):
        """Test getting current system health"""
        monitor = SystemMonitor()
        health = monitor.get_current_health()
        
        assert isinstance(health, SystemHealth)
        assert "cpu_usage" in health.metrics
        assert "memory_usage" in health.metrics
        assert "disk_usage" in health.metrics
        assert health.uptime > 0

    def test_comprehensive_health_function(self):
        """Test comprehensive health function"""
        health_data = get_comprehensive_health()
        
        assert "system" in health_data
        assert "application" in health_data
        assert "overall_status" in health_data
        assert "timestamp" in health_data

    def test_performance_tracker_context_manager(self):
        """Test performance tracker context manager"""
        app_monitor = ApplicationMonitor()
        
        with PerformanceTracker("test_operation") as tracker:
            time.sleep(0.1)  # Simulate work
            assert tracker.operation_name == "test_operation"
        
        # Check that performance was tracked
        health = app_monitor.get_application_health()
        assert "analytics_performance" in health

    def test_application_monitor_trading_events(self):
        """Test application monitor trading event tracking"""
        app_monitor = ApplicationMonitor()
        
        # Track some trading events
        app_monitor.track_trading_event("order_placed", 0.05)
        app_monitor.track_trading_event("order_placed", 0.08)
        app_monitor.track_trading_event("trade_executed", 0.12)
        
        health = app_monitor.get_application_health()
        trading_events = health["trading_events"]
        
        assert "order_placed" in trading_events
        assert trading_events["order_placed"]["count"] == 2
        assert trading_events["order_placed"]["avg_time"] > 0
        
        assert "trade_executed" in trading_events
        assert trading_events["trade_executed"]["count"] == 1


class TestAlertSystem:
    """Test alert system functionality"""

    def test_alert_rule_creation(self):
        """Test alert rule creation and validation"""
        rule = AlertRule(
            name="test_rule",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            condition=lambda data: data.get("value", 0) > 80,
            threshold=80.0,
            cooldown_minutes=10
        )
        
        assert rule.name == "test_rule"
        assert rule.can_trigger()
        assert rule.should_trigger({"value": 85})
        assert not rule.should_trigger({"value": 75})

    def test_alert_cooldown_mechanism(self):
        """Test alert cooldown mechanism"""
        rule = AlertRule(
            name="cooldown_test",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            condition=lambda data: True,  # Always trigger
            cooldown_minutes=1  # 1 minute cooldown
        )
        
        # First trigger should work
        assert rule.can_trigger()
        rule.last_triggered = datetime.now()
        
        # Immediate second trigger should not work
        assert not rule.can_trigger()
        
        # Trigger after cooldown period should work
        rule.last_triggered = datetime.now() - timedelta(minutes=2)
        assert rule.can_trigger()

    def test_alert_creation_and_management(self):
        """Test alert creation and management"""
        manager = AlertManager()
        
        # Add a test rule
        test_rule = AlertRule(
            name="test_alert_rule",
            alert_type=AlertType.APPLICATION_ERROR,
            severity=AlertSeverity.ERROR,
            condition=lambda data: data.get("error_count", 0) > 0,
            description="Test alert for errors"
        )
        
        manager.add_rule(test_rule)
        
        # Verify rule was added
        retrieved_rule = manager.get_rule("test_alert_rule")
        assert retrieved_rule is not None
        assert retrieved_rule.name == "test_alert_rule"
        
        # Test rule removal
        assert manager.remove_rule("test_alert_rule")
        assert manager.get_rule("test_alert_rule") is None

    def test_email_notifier_configuration(self):
        """Test email notifier configuration"""
        notifier = EmailNotifier(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            password="password"
        )
        
        assert notifier.enabled
        assert notifier.smtp_server == "smtp.gmail.com"
        assert notifier.smtp_port == 587

    def test_alert_statistics(self):
        """Test alert statistics tracking"""
        manager = AlertManager()
        
        # Clear any existing alerts for clean test
        manager._alerts.clear()
        manager._alert_history.clear()
        manager._alert_stats.clear()
        
        stats = manager.get_alert_statistics()
        
        assert "active_alerts" in stats
        assert "total_alerts_24h" in stats
        assert "rules_count" in stats
        assert "enabled_rules" in stats

    def test_alert_dashboard_data(self):
        """Test alert dashboard data generation"""
        manager = AlertManager()
        
        dashboard_data = manager.get_dashboard_data()
        
        assert "active_alerts" in dashboard_data
        assert "recent_alerts" in dashboard_data
        assert "statistics" in dashboard_data
        assert "severity_breakdown" in dashboard_data

    @patch('smtplib.SMTP')
    def test_email_alert_sending(self, mock_smtp):
        """Test email alert sending functionality"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        notifier = EmailNotifier(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="test@example.com",
            password="password"
        )
        
        from xline.core.analytics.alerts import Alert
        
        alert = Alert(
            rule_name="test_rule",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert"
        )
        
        # Test sending email
        result = notifier.send_alert(alert, ["recipient@example.com"])
        
        # Verify SMTP calls were made
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()
        
        assert result is True


class TestAnalyticsAPI:
    """Test analytics API functionality"""

    def test_api_server_initialization(self):
        """Test API server initialization"""
        server = AnalyticsAPIServer(host="localhost", port=8081)
        
        assert server.host == "localhost"
        assert server.port == 8081
        assert not server.is_running()

    def test_api_server_start_stop(self):
        """Test API server start and stop"""
        server = AnalyticsAPIServer(host="localhost", port=8082)
        
        try:
            # Start server
            server.start()
            assert server.is_running()
            
            # Get server info
            info = server.get_server_info()
            assert info["running"] is True
            assert info["host"] == "localhost"
            assert info["port"] == 8082
            
        finally:
            # Stop server
            server.stop()
            assert not server.is_running()

    def test_api_status_function(self):
        """Test API status function"""
        status = get_api_status()
        
        assert "host" in status
        assert "port" in status
        assert "running" in status
        assert "url" in status
        assert "endpoints" in status

    @pytest.mark.integration
    def test_health_endpoint_integration(self):
        """Test health endpoint integration"""
        server = AnalyticsAPIServer(host="localhost", port=8083)
        
        try:
            server.start()
            time.sleep(0.5)  # Wait for server to start
            
            # Test would require actual HTTP request
            # This is a placeholder for integration test
            assert server.is_running()
            
        finally:
            server.stop()

    def test_trigger_test_alert_function(self):
        """Test trigger test alert functionality"""
        # This should not raise an exception
        trigger_test_alert()
        
        # Verify test rule was added
        test_rule = alert_manager.get_rule("test_alert")
        assert test_rule is not None
        assert test_rule.alert_type == AlertType.APPLICATION_ERROR


class TestProductionIntegration:
    """Test production-ready integration scenarios"""

    def test_full_monitoring_pipeline(self):
        """Test complete monitoring pipeline"""
        # Start system monitoring
        system_monitor = SystemMonitor()
        system_monitor.start_monitoring()
        
        try:
            # Start alert monitoring
            alert_manager.start_monitoring()
            
            # Wait for monitoring cycles
            time.sleep(2)
            
            # Get comprehensive health
            health = get_comprehensive_health()
            
            assert "system" in health
            assert "application" in health
            assert "overall_status" in health
            
            # Verify monitoring is working
            assert system_monitor._running
            
        finally:
            # Cleanup
            system_monitor.stop_monitoring()
            alert_manager.stop_monitoring()

    def test_alert_integration_with_monitoring(self):
        """Test alert integration with monitoring system"""
        from xline.core.analytics.alerts import AlertManager
        
        # Create isolated alert manager instance to avoid global state issues
        local_manager = AlertManager()
        
        # Create a test rule that should trigger
        test_rule = AlertRule(
            name="integration_test",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.INFO,
            condition=lambda data: data.get('value', 0) > 50,
            cooldown_minutes=0,  # No cooldown for test
            description="Integration test alert"
        )
        
        # Add rule to local manager
        local_manager.add_rule(test_rule)
        
        try:
            # Create mock data to trigger alert
            test_data = {
                'timestamp': datetime.now(),
                'metric': 'test_metric',
                'value': 100
            }
            
            # Use the private method directly for testing
            local_manager._trigger_alert(test_rule, test_data)
            
            # Check if alert was created
            active_alerts = local_manager.get_active_alerts()
            integration_alerts = [a for a in active_alerts
                                 if a.rule_name == "integration_test"]
            
            assert len(integration_alerts) > 0
            assert integration_alerts[0].alert_type == AlertType.SYSTEM_HEALTH
            assert integration_alerts[0].severity == AlertSeverity.INFO
            
        finally:
            # Cleanup
            local_manager.remove_rule("integration_test")
            # Stop any background threads
            if hasattr(local_manager, 'stop'):
                local_manager.stop()

    def test_performance_under_load(self):
        """Test system performance under load"""
        app_monitor = ApplicationMonitor()
        
        # Simulate high load
        start_time = time.time()
        
        for i in range(100):
            app_monitor.track_trading_event("load_test", 0.01 + (i * 0.001))
            app_monitor.track_analytics_performance("load_operation", 0.05, True)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance is acceptable (should complete in < 1 second)
        assert processing_time < 1.0
        
        # Verify data was tracked correctly
        health = app_monitor.get_application_health()
        assert "load_test" in health["trading_events"]
        assert health["trading_events"]["load_test"]["count"] == 100

    def test_concurrent_access_safety(self):
        """Test thread safety under concurrent access"""
        app_monitor = ApplicationMonitor()
        
        def worker_function(worker_id: int):
            """Worker function for concurrent testing"""
            for i in range(50):
                app_monitor.track_trading_event(f"worker_{worker_id}", 0.01)
                app_monitor.track_analytics_performance(f"worker_{worker_id}_op", 0.02, True)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify data integrity
        health = app_monitor.get_application_health()
        
        # Should have events from all 5 workers
        worker_events = [
            key for key in health["trading_events"].keys()
            if key.startswith("worker_")
        ]
        assert len(worker_events) == 5
        
        # Each worker should have tracked 50 events
        for i in range(5):
            worker_key = f"worker_{i}"
            assert worker_key in health["trading_events"]
            assert health["trading_events"][worker_key]["count"] == 50

    def test_system_recovery_after_errors(self):
        """Test system recovery after errors"""
        monitor = SystemMonitor()
        
        # Simulate error condition
        with patch('psutil.cpu_percent', side_effect=Exception("Test error")):
            # This should not crash the system
            health = monitor.get_current_health()
            
            # System should still return health data with fallback values
            assert isinstance(health, SystemHealth)
            assert health.overall_status in [HealthStatus.HEALTHY, HealthStatus.UNKNOWN]

    def test_memory_usage_under_extended_operation(self):
        """Test memory usage during extended operation"""
        import gc
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Run extended operation
        app_monitor = ApplicationMonitor()
        
        for i in range(1000):
            app_monitor.track_trading_event("memory_test", 0.001)
            
            # Periodic cleanup check
            if i % 100 == 0:
                gc.collect()
        
        # Check memory usage hasn't grown excessively
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object growth should be reasonable (< 50% increase)
        growth_ratio = (final_objects - initial_objects) / initial_objects
        assert growth_ratio < 0.5, f"Memory usage grew by {growth_ratio:.2%}"
