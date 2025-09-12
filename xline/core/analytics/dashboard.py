"""Analytics Dashboard for Xline Trading System.

This module provides real-time dashboard capabilities for monitoring
trading performance, risk metrics, and strategy analytics.

Features:
- Real-time performance monitoring
- Interactive charts and visualizations
- Risk monitoring dashboard
- Strategy comparison views
- Alert management interface
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from xline.core.analytics.engine import AnalyticsEngine, AnalyticsResult
    from xline.core.analytics.reporter import AnalyticsReporter

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Configuration for analytics dashboard."""
    
    refresh_interval: int = 30  # seconds
    chart_history_days: int = 30
    max_alerts_display: int = 20
    enable_real_time: bool = True
    theme: str = 'dark'  # 'light', 'dark'
    auto_refresh: bool = True


@dataclass
class ChartData:
    """Chart data structure."""
    
    chart_type: str  # 'line', 'bar', 'pie', 'candlestick'
    title: str
    data: list[dict[str, Any]]
    labels: list[str]
    series: list[dict[str, Any]]
    options: dict[str, Any] | None = None


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    
    widget_id: str
    widget_type: str  # 'metric', 'chart', 'table', 'alert'
    title: str
    data: Any
    position: dict[str, int]  # {'x': 0, 'y': 0, 'w': 4, 'h': 3}
    config: dict[str, Any] | None = None


@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    
    layout_id: str
    name: str
    widgets: list[DashboardWidget]
    grid_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AnalyticsDashboard:
    """Real-time analytics dashboard for trading system.
    
    Provides comprehensive real-time monitoring capabilities including
    performance metrics, risk indicators, and strategy analytics.
    """
    
    def __init__(
        self,
        analytics_engine: "AnalyticsEngine",
        reporter: "AnalyticsReporter",
        config: DashboardConfig | None = None
    ):
        """Initialize analytics dashboard.
        
        Args:
            analytics_engine: Analytics engine instance
            reporter: Analytics reporter instance
            config: Dashboard configuration
        """
        self.analytics_engine = analytics_engine
        self.reporter = reporter
        self.config = config or DashboardConfig()
        
        # Dashboard state
        self._layouts: dict[str, DashboardLayout] = {}
        self._active_layout: str | None = None
        self._last_update: datetime | None = None
        
        # Data cache
        self._chart_cache: dict[str, ChartData] = {}
        self._metric_cache: dict[str, Any] = {}

    def create_default_layout(self) -> DashboardLayout:
        """Create default dashboard layout.
        
        Returns:
            Default dashboard layout
        """
        widgets = [
            # Portfolio overview metrics
            DashboardWidget(
                widget_id='portfolio_overview',
                widget_type='metric',
                title='Portfolio Overview',
                data={},
                position={'x': 0, 'y': 0, 'w': 6, 'h': 2}
            ),
            
            # Performance chart
            DashboardWidget(
                widget_id='performance_chart',
                widget_type='chart',
                title='Portfolio Performance',
                data={},
                position={'x': 6, 'y': 0, 'w': 6, 'h': 4}
            ),
            
            # Strategy comparison
            DashboardWidget(
                widget_id='strategy_comparison',
                widget_type='table',
                title='Strategy Performance',
                data={},
                position={'x': 0, 'y': 2, 'w': 6, 'h': 4}
            ),
            
            # Risk metrics
            DashboardWidget(
                widget_id='risk_metrics',
                widget_type='metric',
                title='Risk Indicators',
                data={},
                position={'x': 0, 'y': 6, 'w': 4, 'h': 3}
            ),
            
            # Recent alerts
            DashboardWidget(
                widget_id='recent_alerts',
                widget_type='alert',
                title='Recent Alerts',
                data={},
                position={'x': 4, 'y': 6, 'w': 4, 'h': 3}
            ),
            
            # Drawdown chart
            DashboardWidget(
                widget_id='drawdown_chart',
                widget_type='chart',
                title='Drawdown Analysis',
                data={},
                position={'x': 8, 'y': 6, 'w': 4, 'h': 3}
            )
        ]
        
        layout = DashboardLayout(
            layout_id='default',
            name='Default Dashboard',
            widgets=widgets,
            grid_config={
                'cols': 12,
                'row_height': 60,
                'margin': [10, 10],
                'breakpoints': {'lg': 1200, 'md': 996, 'sm': 768, 'xs': 480}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._layouts['default'] = layout
        self._active_layout = 'default'
        
        return layout

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get current dashboard data.
        
        Returns:
            Complete dashboard data including all widgets
        """
        # Get current analytics results
        strategy_results = self._get_current_strategy_results()
        
        # Generate dashboard data using reporter
        dashboard_data = self.reporter.get_dashboard_data(strategy_results)
        
        # Get active layout
        layout = self._layouts.get(self._active_layout or 'default')
        if not layout:
            layout = self.create_default_layout()
        
        # Update widget data
        updated_widgets = []
        for widget in layout.widgets:
            updated_widget = self._update_widget_data(widget, dashboard_data)
            updated_widgets.append(updated_widget)
        
        self._last_update = datetime.now()
        
        return {
            'layout': layout,
            'widgets': updated_widgets,
            'last_update': self._last_update,
            'config': self.config,
            'summary': dashboard_data['portfolio_summary'],
            'alerts': dashboard_data['alerts'][:self.config.max_alerts_display]
        }

    def get_performance_chart_data(self, days: int = 30) -> ChartData:
        """Generate performance chart data.
        
        Args:
            days: Number of days to include
            
        Returns:
            Chart data for performance visualization
        """
        # Get strategy results
        strategy_results = self._get_current_strategy_results()
        
        # Generate time series data (simplified)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Create sample data points (in real implementation, use historical data)
        data_points = []
        labels = []
        
        current_date = start_date
        cumulative_return = 1.0
        
        while current_date <= end_date:
            # Simulate daily returns (in real implementation, use actual data)
            daily_return = 0.001  # 0.1% daily return as baseline
            cumulative_return *= (1 + daily_return)
            
            data_points.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': (cumulative_return - 1) * 100,  # Percentage return
                'timestamp': current_date
            })
            
            labels.append(current_date.strftime('%m/%d'))
            current_date += timedelta(days=1)
        
        return ChartData(
            chart_type='line',
            title='Portfolio Performance',
            data=data_points,
            labels=labels,
            series=[{
                'name': 'Portfolio Return (%)',
                'data': [point['value'] for point in data_points],
                'color': '#4CAF50'
            }],
            options={
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': False,
                        'title': {'display': True, 'text': 'Return (%)'}
                    },
                    'x': {
                        'title': {'display': True, 'text': 'Date'}
                    }
                }
            }
        )

    def get_strategy_comparison_data(self) -> dict[str, Any]:
        """Generate strategy comparison table data.
        
        Returns:
            Table data for strategy comparison
        """
        strategy_results = self._get_current_strategy_results()
        
        table_data = {
            'headers': [
                'Strategy', 'Total Trades', 'Win Rate', 'Total Profit', 
                'Max Drawdown', 'Sharpe Ratio', 'Status'
            ],
            'rows': []
        }
        
        for strategy_id, result in strategy_results.items():
            metrics = result.metrics
            trade_metrics = metrics.get('trade_metrics')
            performance_metrics = metrics.get('performance_metrics')
            
            # Determine status based on performance
            status = 'Active'
            if hasattr(performance_metrics, 'max_drawdown'):
                if performance_metrics.max_drawdown < -0.25:
                    status = 'Critical'
                elif performance_metrics.max_drawdown < -0.15:
                    status = 'Warning'
            
            row = [
                strategy_id,
                getattr(trade_metrics, 'total_trades', 0),
                f"{getattr(trade_metrics, 'win_rate', 0):.1%}",
                f"${getattr(trade_metrics, 'total_profit', 0):.2f}",
                f"{getattr(performance_metrics, 'max_drawdown', 0):.1%}",
                f"{getattr(performance_metrics, 'sharpe_ratio', 0):.2f}",
                status
            ]
            
            table_data['rows'].append(row)
        
        # Sort by total profit descending
        table_data['rows'].sort(key=lambda x: float(x[3].replace('$', '')), reverse=True)
        
        return table_data

    def get_risk_indicators(self) -> dict[str, Any]:
        """Generate risk indicator metrics.
        
        Returns:
            Risk indicator data
        """
        strategy_results = self._get_current_strategy_results()
        
        if not strategy_results:
            return {
                'portfolio_var': 0.0,
                'max_drawdown': 0.0,
                'risk_level': 'Unknown',
                'correlation_risk': 0.0,
                'concentration_risk': 0.0
            }
        
        # Calculate portfolio-level risk metrics
        all_drawdowns = []
        all_sharpe_ratios = []
        
        for result in strategy_results.values():
            metrics = result.metrics
            performance_metrics = metrics.get('performance_metrics')
            
            if performance_metrics:
                all_drawdowns.append(getattr(performance_metrics, 'max_drawdown', 0))
                all_sharpe_ratios.append(getattr(performance_metrics, 'sharpe_ratio', 0))
        
        # Portfolio metrics
        portfolio_drawdown = min(all_drawdowns) if all_drawdowns else 0
        avg_sharpe = sum(all_sharpe_ratios) / len(all_sharpe_ratios) if all_sharpe_ratios else 0
        
        # Risk level assessment
        if portfolio_drawdown > -0.05:
            risk_level = 'Low'
            risk_color = '#4CAF50'
        elif portfolio_drawdown > -0.15:
            risk_level = 'Medium'
            risk_color = '#FF9800'
        else:
            risk_level = 'High'
            risk_color = '#F44336'
        
        return {
            'portfolio_var': abs(portfolio_drawdown) * 100,
            'max_drawdown': portfolio_drawdown * 100,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'avg_sharpe_ratio': avg_sharpe,
            'strategy_count': len(strategy_results),
            'concentration_risk': self._calculate_concentration_risk(strategy_results)
        }

    def get_drawdown_chart_data(self) -> ChartData:
        """Generate drawdown chart data.
        
        Returns:
            Chart data for drawdown visualization
        """
        strategy_results = self._get_current_strategy_results()
        
        # Create drawdown data for each strategy
        series_data = []
        colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#2196F3', '#9C27B0']
        
        for i, (strategy_id, result) in enumerate(strategy_results.items()):
            metrics = result.metrics
            performance_metrics = metrics.get('performance_metrics')
            
            if performance_metrics:
                drawdown = getattr(performance_metrics, 'max_drawdown', 0) * 100
                
                series_data.append({
                    'name': strategy_id,
                    'data': [drawdown],
                    'color': colors[i % len(colors)]
                })
        
        return ChartData(
            chart_type='bar',
            title='Max Drawdown by Strategy',
            data=[],
            labels=[s['name'] for s in series_data],
            series=series_data,
            options={
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'title': {'display': True, 'text': 'Drawdown (%)'}
                    }
                }
            }
        )

    def export_dashboard_data(self, format_type: str = 'json') -> str:
        """Export current dashboard data.
        
        Args:
            format_type: Export format ('json', 'csv')
            
        Returns:
            Exported data as string
        """
        dashboard_data = self.get_dashboard_data()
        
        if format_type == 'json':
            return json.dumps(
                dashboard_data, 
                default=str, 
                indent=2
            )
        elif format_type == 'csv':
            # Simple CSV export of strategy data
            strategy_data = self.get_strategy_comparison_data()
            csv_lines = []
            csv_lines.append(','.join(strategy_data['headers']))
            
            for row in strategy_data['rows']:
                csv_lines.append(','.join(str(cell) for cell in row))
            
            return '\n'.join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def _get_current_strategy_results(self) -> dict[str, "AnalyticsResult"]:
        """Get current analytics results for all strategies.
        
        Returns:
            Dictionary mapping strategy_id to AnalyticsResult
        """
        # In a real implementation, this would fetch from the analytics engine
        # For now, return empty dict (analytics engine integration needed)
        return {}

    def _update_widget_data(
        self, 
        widget: DashboardWidget, 
        dashboard_data: dict[str, Any]
    ) -> DashboardWidget:
        """Update widget with current data.
        
        Args:
            widget: Widget to update
            dashboard_data: Current dashboard data
            
        Returns:
            Updated widget
        """
        if widget.widget_type == 'metric':
            if widget.widget_id == 'portfolio_overview':
                widget.data = self._get_portfolio_overview_metrics(dashboard_data)
            elif widget.widget_id == 'risk_metrics':
                widget.data = self.get_risk_indicators()
                
        elif widget.widget_type == 'chart':
            if widget.widget_id == 'performance_chart':
                widget.data = self.get_performance_chart_data()
            elif widget.widget_id == 'drawdown_chart':
                widget.data = self.get_drawdown_chart_data()
                
        elif widget.widget_type == 'table':
            if widget.widget_id == 'strategy_comparison':
                widget.data = self.get_strategy_comparison_data()
                
        elif widget.widget_type == 'alert':
            if widget.widget_id == 'recent_alerts':
                widget.data = {
                    'alerts': dashboard_data.get('alerts', [])[:10],
                    'total_count': len(dashboard_data.get('alerts', []))
                }
        
        return widget

    def _get_portfolio_overview_metrics(self, dashboard_data: dict[str, Any]) -> dict[str, Any]:
        """Get portfolio overview metrics.
        
        Args:
            dashboard_data: Dashboard data
            
        Returns:
            Portfolio overview metrics
        """
        summary = dashboard_data.get('portfolio_summary', {})
        
        return {
            'total_profit': f"${summary.get('total_profit', 0):.2f}",
            'total_trades': summary.get('total_trades', 0),
            'active_strategies': summary.get('active_strategies', 0),
            'avg_profit_per_trade': f"${summary.get('avg_profit_per_trade', 0):.2f}",
            'last_updated': datetime.now().strftime('%H:%M:%S')
        }

    def _calculate_concentration_risk(
        self,
        strategy_results: dict[str, "AnalyticsResult"]
    ) -> float:
        """Calculate portfolio concentration risk.
        
        Args:
            strategy_results: Strategy analytics results
            
        Returns:
            Concentration risk score (0-100)
        """
        if len(strategy_results) <= 1:
            return 100.0  # High concentration
        
        # Calculate profit distribution
        profits = []
        for result in strategy_results.values():
            metrics = result.metrics
            trade_metrics = metrics.get('trade_metrics')
            
            if trade_metrics:
                profits.append(getattr(trade_metrics, 'total_profit', 0))
        
        if not profits or sum(profits) == 0:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index for concentration
        total_profit = sum(profits)
        market_shares = [p / total_profit for p in profits]
        hhi = sum(share ** 2 for share in market_shares)
        
        # Convert to 0-100 scale (higher = more concentrated)
        return hhi * 100


from enum import Enum


class ChartType(Enum):
    """Chart type enumeration"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    CANDLESTICK = "candlestick"


@dataclass 
class ChartConfig:
    """Chart configuration"""
    chart_type: ChartType
    title: str
    x_axis_label: str
    y_axis_label: str
    colors: list[str]


class DashboardDataGenerator:
    """Dashboard data generator for tests and real-time updates"""
    
    def __init__(self):
        self.chart_configs: dict[str, ChartConfig] = {}
        self.default_colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
        
    def generate_chart_data(self, data: list[dict], chart_type: ChartType) -> dict[str, Any]:
        """Generate chart data from raw data"""
        labels = []
        values = []
        
        for item in data:
            if 'timestamp' in item:
                labels.append(item['timestamp'].strftime('%H:%M'))
            else:
                labels.append(str(len(labels)))
            values.append(item.get('value', 0))
            
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Data',
                'data': values,
                'backgroundColor': self.default_colors[0],
                'borderColor': self.default_colors[1]
            }]
        }
        
    def create_performance_dashboard(self, performance_data: dict[str, Any]) -> dict[str, Any]:
        """Create performance dashboard from data"""
        charts = []
        
        # Daily returns chart
        if 'daily_returns' in performance_data:
            charts.append({
                'id': 'daily_returns',
                'type': 'line',
                'title': 'Daily Returns',
                'data': performance_data['daily_returns']
            })
            
        # Cumulative returns chart  
        if 'cumulative_returns' in performance_data:
            charts.append({
                'id': 'cumulative_returns', 
                'type': 'line',
                'title': 'Cumulative Returns',
                'data': performance_data['cumulative_returns']
            })
            
        return {
            'charts': charts,
            'summary': {
                'total_charts': len(charts),
                'last_updated': datetime.now().isoformat()
            }
        }
        
    def generate_real_time_updates(self, current_metrics: dict[str, Any]) -> dict[str, Any]:
        """Generate real-time updates"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': current_metrics
        }
        
    def add_chart_config(self, chart_id: str, config: ChartConfig) -> None:
        """Add chart configuration"""
        self.chart_configs[chart_id] = config
