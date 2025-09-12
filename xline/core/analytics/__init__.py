"""Xline Analytics Package.

This package provides comprehensive analytics capabilities for the Xline trading system,
including real-time performance monitoring, risk analysis, and reporting.

Components:
- engine: Core analytics processing engine
- metrics: Trading metrics calculations
- reporter: Analytics reporting and export
- dashboard: Real-time dashboard and visualization

Usage:
    from xline.core.analytics import AnalyticsEngine, AnalyticsConfig
    from xline.core.analytics import TradingMetricsCalculator
    from xline.core.analytics import AnalyticsReporter, AnalyticsDashboard
"""

from xline.core.analytics.dashboard import (
    AnalyticsDashboard,
    ChartData,
    DashboardConfig,
    DashboardLayout,
    DashboardWidget,
)
from xline.core.analytics.engine import (
    AnalyticsConfig,
    AnalyticsEngine,
    AnalyticsResult,
    TradeEvent,
)
from xline.core.analytics.metrics import (
    PerformanceMetrics,
    RiskMetrics,
    TradeMetrics,
    TradingMetricsCalculator,
)
from xline.core.analytics.reporter import (
    AnalyticsReporter,
    PerformanceReport,
    PortfolioReport,
    ReportConfig,
)

__all__ = [
    # Engine components
    'AnalyticsEngine',
    'AnalyticsConfig',
    'AnalyticsResult',
    'TradeEvent',
    
    # Metrics components
    'TradingMetricsCalculator',
    'TradeMetrics',
    'PerformanceMetrics',
    'RiskMetrics',
    
    # Reporter components
    'AnalyticsReporter',
    'ReportConfig',
    'PerformanceReport',
    'PortfolioReport',
    
    # Dashboard components
    'AnalyticsDashboard',
    'DashboardConfig',
    'DashboardWidget',
    'DashboardLayout',
    'ChartData',
]

# Version info
__version__ = '1.0.0'
__author__ = 'Xline Development Team'
