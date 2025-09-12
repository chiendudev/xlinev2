"""
Analytics API Endpoints for Xline
Provides REST API endpoints for accessing analytics data, alerts, and system health.
"""

import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

from .alerts import alert_manager
from .monitoring import get_comprehensive_health

logger = logging.getLogger(__name__)


class AnalyticsAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for analytics API"""

    def do_GET(self) -> None:
        """Handle GET requests"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # Route requests
            if path == "/health":
                self._handle_health()
            elif path == "/alerts":
                self._handle_alerts(query_params)
            elif path == "/alerts/active":
                self._handle_active_alerts()
            elif path == "/alerts/statistics":
                self._handle_alert_statistics()
            elif path == "/alerts/dashboard":
                self._handle_alert_dashboard()
            elif path == "/system/metrics":
                self._handle_system_metrics()
            elif path == "/system/status":
                self._handle_system_status()
            elif path == "/api/info":
                self._handle_api_info()
            else:
                self._send_error(404, "Endpoint not found")

        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self._send_error(500, f"Internal server error: {str(e)}")

    def do_POST(self) -> None:
        """Handle POST requests"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            if path == "/alerts/acknowledge":
                self._handle_acknowledge_alert()
            elif path == "/alerts/resolve":
                self._handle_resolve_alert()
            elif path == "/alerts/test":
                self._handle_test_alert()
            else:
                self._send_error(404, "Endpoint not found")

        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self._send_error(500, f"Internal server error: {str(e)}")

    def _handle_health(self) -> None:
        """Handle health check endpoint"""
        health_data = get_comprehensive_health()
        self._send_json_response(health_data)

    def _handle_alerts(self, query_params: dict) -> None:
        """Handle alerts endpoint with optional filtering"""
        hours = int(query_params.get("hours", ["24"])[0])
        alerts = alert_manager.get_alert_history(hours=hours)
        
        alert_data = {
            "alerts": [alert.to_dict() for alert in alerts],
            "total": len(alerts),
            "timeframe_hours": hours,
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(alert_data)

    def _handle_active_alerts(self) -> None:
        """Handle active alerts endpoint"""
        active_alerts = alert_manager.get_active_alerts()
        
        response_data = {
            "active_alerts": [alert.to_dict() for alert in active_alerts],
            "count": len(active_alerts),
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(response_data)

    def _handle_alert_statistics(self) -> None:
        """Handle alert statistics endpoint"""
        stats = alert_manager.get_alert_statistics()
        self._send_json_response(stats)

    def _handle_alert_dashboard(self) -> None:
        """Handle alert dashboard data endpoint"""
        dashboard_data = alert_manager.get_dashboard_data()
        self._send_json_response(dashboard_data)

    def _handle_system_metrics(self) -> None:
        """Handle system metrics endpoint"""
        health_data = get_comprehensive_health()
        
        response_data = {
            "system_metrics": health_data.get("system", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(response_data)

    def _handle_system_status(self) -> None:
        """Handle system status endpoint"""
        health_data = get_comprehensive_health()
        
        response_data = {
            "status": health_data.get("overall_status", "unknown"),
            "uptime": health_data.get("system", {}).get("uptime_formatted", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(response_data)

    def _handle_api_info(self) -> None:
        """Handle API information endpoint"""
        api_info = {
            "name": "Xline Analytics API",
            "version": "1.0.0",
            "endpoints": {
                "GET": [
                    "/health - Complete system health information",
                    "/alerts?hours=24 - Alert history with optional timeframe",
                    "/alerts/active - Currently active alerts",
                    "/alerts/statistics - Alert statistics and metrics",
                    "/alerts/dashboard - Alert dashboard data",
                    "/system/metrics - System performance metrics",
                    "/system/status - System status summary",
                    "/api/info - This endpoint information"
                ],
                "POST": [
                    "/alerts/acknowledge - Acknowledge an alert",
                    "/alerts/resolve - Resolve an alert",
                    "/alerts/test - Trigger a test alert"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(api_info)

    def _handle_acknowledge_alert(self) -> None:
        """Handle acknowledge alert request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                alert_index = data.get('alert_index')
                
                if alert_index is not None:
                    success = alert_manager.acknowledge_alert(alert_index)
                    if success:
                        self._send_json_response({
                            "success": True,
                            "message": f"Alert {alert_index} acknowledged"
                        })
                    else:
                        self._send_error(400, "Invalid alert index")
                else:
                    self._send_error(400, "Missing alert_index in request")
            else:
                self._send_error(400, "Empty request body")
                
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON in request body")

    def _handle_resolve_alert(self) -> None:
        """Handle resolve alert request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                alert_index = data.get('alert_index')
                
                if alert_index is not None:
                    success = alert_manager.resolve_alert(alert_index)
                    if success:
                        self._send_json_response({
                            "success": True,
                            "message": f"Alert {alert_index} resolved"
                        })
                    else:
                        self._send_error(400, "Invalid alert index")
                else:
                    self._send_error(400, "Missing alert_index in request")
            else:
                self._send_error(400, "Empty request body")
                
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON in request body")

    def _handle_test_alert(self) -> None:
        """Handle test alert creation"""
        from .alerts import trigger_test_alert
        
        try:
            trigger_test_alert()
            self._send_json_response({
                "success": True,
                "message": "Test alert triggered successfully"
            })
        except Exception as e:
            self._send_error(500, f"Failed to trigger test alert: {str(e)}")

    def _send_json_response(self, data: dict) -> None:
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        json_data = json.dumps(data, indent=2, default=str)
        self.wfile.write(json_data.encode('utf-8'))

    def _send_error(self, status_code: int, message: str) -> None:
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        error_data = {
            "error": message,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
        
        json_data = json.dumps(error_data, indent=2)
        self.wfile.write(json_data.encode('utf-8'))

    def log_message(self, format: str, *args) -> None:
        """Override log message to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")


class AnalyticsAPIServer:
    """Analytics API server"""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.server_thread: Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the API server"""
        if self._running:
            logger.warning("API server already running")
            return

        try:
            self.server = HTTPServer((self.host, self.port), AnalyticsAPIHandler)
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self._running = True
            
            logger.info(f"Analytics API server started on http://{self.host}:{self.port}")
            logger.info(f"API documentation available at http://{self.host}:{self.port}/api/info")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

    def stop(self) -> None:
        """Stop the API server"""
        if not self._running:
            return

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5.0)
            
            self._running = False
            logger.info("Analytics API server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping API server: {e}")

    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running

    def get_server_info(self) -> dict[str, Any]:
        """Get server information"""
        return {
            "host": self.host,
            "port": self.port,
            "running": self._running,
            "url": f"http://{self.host}:{self.port}",
            "endpoints": {
                "health": f"http://{self.host}:{self.port}/health",
                "alerts": f"http://{self.host}:{self.port}/alerts",
                "system_status": f"http://{self.host}:{self.port}/system/status",
                "api_info": f"http://{self.host}:{self.port}/api/info"
            }
        }


# Global API server instance
api_server = AnalyticsAPIServer()


def start_api_server(host: str = "localhost", port: int = 8080) -> AnalyticsAPIServer:
    """Start analytics API server"""
    server = AnalyticsAPIServer(host, port)
    server.start()
    return server


def stop_api_server() -> None:
    """Stop the global API server"""
    api_server.stop()


def get_api_status() -> dict[str, Any]:
    """Get API server status"""
    return api_server.get_server_info()
