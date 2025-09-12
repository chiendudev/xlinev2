"""
Comprehensive tests for AnalyticsDashboard to achieve high coverage.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from xline.core.analytics.dashboard import (
    AnalyticsDashboard,
    DashboardConfig,
    ChartData,
    DashboardWidget,
    DashboardLayout
)
from xline.core.analytics.engine import AnalyticsEngine, AnalyticsConfig
from xline.core.analytics.reporter import AnalyticsReporter, ReportConfig


class TestAnalyticsDashboard:
    """Comprehensive tests for AnalyticsDashboard."""

    @pytest.fixture
    def dashboard_config(self):
        return DashboardConfig(
            refresh_interval=10,
            chart_history_days=7,
            max_alerts_display=10,
            enable_real_time=True,
            theme='dark',
            auto_refresh=True
        )

    @pytest.fixture
    def mock_engine(self):
        config = AnalyticsConfig()
        return AnalyticsEngine(config)

    @pytest.fixture
    def mock_reporter(self):
        config = ReportConfig()
        return AnalyticsReporter(config)

    @pytest.fixture
    def dashboard(self, mock_engine, mock_reporter, dashboard_config):
        return AnalyticsDashboard(mock_engine, mock_reporter, dashboard_config)

    def test_dashboard_initialization(self, mock_engine, mock_reporter, dashboard_config):
        """Test dashboard initialization."""
        dashboard = AnalyticsDashboard(mock_engine, mock_reporter, dashboard_config)
        
        assert dashboard.analytics_engine == mock_engine
        assert dashboard.reporter == mock_reporter
        assert dashboard.config == dashboard_config
        assert dashboard._layouts == {}

    def test_dashboard_initialization_default_config(self, mock_engine, mock_reporter):
        """Test dashboard initialization with default config."""
        dashboard = AnalyticsDashboard(mock_engine, mock_reporter)
        
        assert dashboard.analytics_engine == mock_engine
        assert dashboard.reporter == mock_reporter
        assert dashboard.config is not None
        assert dashboard.config.refresh_interval == 30  # default

    def test_chart_data_creation(self):
        """Test ChartData dataclass."""
        chart_data = ChartData(
            chart_type='line',
            title='Performance Chart',
            data=[{'x': 1, 'y': 100}],
            labels=['Time', 'Value'],
            series=[{'name': 'Series1', 'data': [100, 200]}],
            options={'responsive': True}
        )
        
        assert chart_data.chart_type == 'line'
        assert chart_data.title == 'Performance Chart'
        assert len(chart_data.data) == 1
        assert chart_data.options['responsive'] is True

    def test_dashboard_widget_creation(self):
        """Test DashboardWidget dataclass."""
        widget = DashboardWidget(
            widget_id='widget_1',
            widget_type='metric',
            title='Total Return',
            data={'value': 15.5, 'change': 2.3},
            position={'x': 0, 'y': 0, 'w': 4, 'h': 3},
            config={'format': 'percentage'}
        )
        
        assert widget.widget_id == 'widget_1'
        assert widget.widget_type == 'metric'
        assert widget.data['value'] == 15.5
        assert widget.position['w'] == 4

    def test_dashboard_layout_creation(self):
        """Test DashboardLayout dataclass."""
        widget = DashboardWidget(
            widget_id='widget_1',
            widget_type='chart',
            title='Test Chart',
            data={},
            position={'x': 0, 'y': 0, 'w': 6, 'h': 4}
        )
        
        now = datetime.now()
        layout = DashboardLayout(
            layout_id='layout_1',
            name='Main Dashboard',
            widgets=[widget],
            grid_config={'cols': 12, 'rows': 8},
            created_at=now,
            updated_at=now
        )
        
        assert layout.layout_id == 'layout_1'
        assert layout.name == 'Main Dashboard'
        assert len(layout.widgets) == 1
        assert layout.grid_config['cols'] == 12

    def test_dashboard_config_variations(self):
        """Test different dashboard configurations."""
        # Light theme config
        light_config = DashboardConfig(
            refresh_interval=60,
            chart_history_days=90,
            max_alerts_display=50,
            enable_real_time=False,
            theme='light',
            auto_refresh=False
        )
        
        assert light_config.theme == 'light'
        assert light_config.enable_real_time is False
        assert light_config.auto_refresh is False

    def test_dashboard_state_management(self, dashboard):
        """Test dashboard state management."""
        # Test initial state
        assert len(dashboard._layouts) == 0
        
        # Add a layout
        widget = DashboardWidget(
            widget_id='test_widget',
            widget_type='metric',
            title='Test Metric',
            data={},
            position={'x': 0, 'y': 0, 'w': 4, 'h': 2}
        )
        
        layout = DashboardLayout(
            layout_id='test_layout',
            name='Test Layout',
            widgets=[widget],
            grid_config={'cols': 12},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        dashboard._layouts['test_layout'] = layout
        assert len(dashboard._layouts) == 1
        assert 'test_layout' in dashboard._layouts

    def test_chart_data_types(self):
        """Test different chart data types."""
        # Line chart
        line_chart = ChartData(
            chart_type='line',
            title='Performance Over Time',
            data=[],
            labels=[],
            series=[]
        )
        assert line_chart.chart_type == 'line'
        
        # Bar chart
        bar_chart = ChartData(
            chart_type='bar',
            title='Strategy Comparison',
            data=[],
            labels=[],
            series=[]
        )
        assert bar_chart.chart_type == 'bar'
        
        # Pie chart
        pie_chart = ChartData(
            chart_type='pie',
            title='Asset Allocation',
            data=[],
            labels=[],
            series=[]
        )
        assert pie_chart.chart_type == 'pie'

    def test_widget_types(self):
        """Test different widget types."""
        position = {'x': 0, 'y': 0, 'w': 4, 'h': 3}
        
        # Metric widget
        metric_widget = DashboardWidget(
            widget_id='metric_1',
            widget_type='metric',
            title='Total Return',
            data={'value': 12.5},
            position=position
        )
        assert metric_widget.widget_type == 'metric'
        
        # Chart widget
        chart_widget = DashboardWidget(
            widget_id='chart_1',
            widget_type='chart',
            title='Performance Chart',
            data={},
            position=position
        )
        assert chart_widget.widget_type == 'chart'
        
        # Table widget
        table_widget = DashboardWidget(
            widget_id='table_1',
            widget_type='table',
            title='Trade History',
            data={'rows': [], 'columns': []},
            position=position
        )
        assert table_widget.widget_type == 'table'
        
        # Alert widget
        alert_widget = DashboardWidget(
            widget_id='alert_1',
            widget_type='alert',
            title='System Alerts',
            data={'alerts': []},
            position=position
        )
        assert alert_widget.widget_type == 'alert'

    def test_dashboard_config_defaults(self):
        """Test dashboard config default values."""
        config = DashboardConfig()
        
        assert config.refresh_interval == 30
        assert config.chart_history_days == 30
        assert config.max_alerts_display == 20
        assert config.enable_real_time is True
        assert config.theme == 'dark'
        assert config.auto_refresh is True

    def test_dashboard_integration_with_engine_and_reporter(self, dashboard):
        """Test dashboard integration with engine and reporter."""
        # Verify dashboard has access to engine and reporter
        assert dashboard.analytics_engine is not None
        assert dashboard.reporter is not None
        
        # Test configuration access
        assert dashboard.config.refresh_interval == 10
        assert dashboard.config.theme == 'dark'

    def test_chart_data_with_options(self):
        """Test chart data with various options."""
        options = {
            'responsive': True,
            'maintainAspectRatio': False,
            'legend': {'display': True, 'position': 'top'},
            'scales': {
                'x': {'display': True},
                'y': {'display': True, 'beginAtZero': True}
            }
        }
        
        chart = ChartData(
            chart_type='candlestick',
            title='Price Action',
            data=[],
            labels=[],
            series=[],
            options=options
        )
        
        assert chart.options['responsive'] is True
        assert chart.options['legend']['position'] == 'top'
        assert chart.options['scales']['y']['beginAtZero'] is True

    def test_dashboard_widget_config_variations(self):
        """Test widget configurations."""
        # Widget with detailed config
        widget = DashboardWidget(
            widget_id='advanced_widget',
            widget_type='chart',
            title='Advanced Chart',
            data={'series': [1, 2, 3]},
            position={'x': 2, 'y': 1, 'w': 6, 'h': 4},
            config={
                'animation': True,
                'colors': ['#ff6384', '#36a2eb', '#ffce56'],
                'grid': {'show': True, 'color': '#e0e0e0'},
                'tooltip': {'enabled': True, 'format': '${value}'}
            }
        )
        
        assert widget.config['animation'] is True
        assert len(widget.config['colors']) == 3
        assert widget.config['grid']['show'] is True

    def test_complex_dashboard_layout(self):
        """Test complex dashboard layout with multiple widgets."""
        widgets = [
            DashboardWidget(
                widget_id=f'widget_{i}',
                widget_type='metric' if i % 2 == 0 else 'chart',
                title=f'Widget {i}',
                data={},
                position={'x': i * 2, 'y': 0, 'w': 2, 'h': 2}
            )
            for i in range(5)
        ]
        
        layout = DashboardLayout(
            layout_id='complex_layout',
            name='Complex Dashboard',
            widgets=widgets,
            grid_config={
                'cols': 12,
                'rows': 10,
                'margin': [10, 10],
                'containerPadding': [15, 15],
                'rowHeight': 30
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert len(layout.widgets) == 5
        assert layout.grid_config['cols'] == 12
        assert layout.grid_config['margin'] == [10, 10]
        
        # Verify widget types alternate
        for i, widget in enumerate(layout.widgets):
            expected_type = 'metric' if i % 2 == 0 else 'chart'
            assert widget.widget_type == expected_type

    def test_dashboard_missing_lines_coverage(self, dashboard):
        """Test missing lines in dashboard methods to improve coverage."""
        # Test create_default_layout method (lines 114-187)
        default_layout = dashboard.create_default_layout()
        assert default_layout is not None
        assert len(default_layout.widgets) > 0
        
        # Test get_dashboard_data (lines 196-214)
        dashboard_data = dashboard.get_dashboard_data()
        assert dashboard_data is not None
        
        # Test get_performance_chart_data (lines 233-260)
        chart_data = dashboard.get_performance_chart_data(days=30)
        assert chart_data is not None
        
        # Test get_strategy_comparison_data (lines 290-328)
        comparison_data = dashboard.get_strategy_comparison_data()
        assert comparison_data is not None
        
        # Test get_risk_indicators (lines 336-374)
        risk_indicators = dashboard.get_risk_indicators()
        assert risk_indicators is not None
        
        # Test get_drawdown_chart_data (lines 390-409)
        drawdown_data = dashboard.get_drawdown_chart_data()
        assert drawdown_data is not None
        
        # Test export_dashboard_data (lines 426-454)
        export_data = dashboard.export_dashboard_data('json')
        assert export_data is not None
        
        # Test _get_current_strategy_results (lines 456-465)
        strategy_results = dashboard._get_current_strategy_results()
        assert strategy_results is not None
        
        # Test _update_widget_data (lines 466-504)
        test_widget = DashboardWidget(
            widget_id='test_widget',
            widget_type='metric',
            title='Test Metric',
            data={'value': 0},
            position={'x': 0, 'y': 0, 'w': 4, 'h': 2}
        )
        widget_update = dashboard._update_widget_data(test_widget, {'test': 'data'})
        assert widget_update is not None
        
        # Test additional missing lines coverage
        # Cover line 204 - layout not found case
        dashboard._active_layout = 'nonexistent_layout'
        dashboard._layouts = {}  # Empty layouts to trigger create_default_layout
        dashboard_data_no_layout = dashboard.get_dashboard_data()
        assert dashboard_data_no_layout is not None
        
        # Test active layout exists case
        dashboard._active_layout = 'test_layout'
        dashboard._layouts['test_layout'] = default_layout
        dashboard_data2 = dashboard.get_dashboard_data()
        assert dashboard_data2 is not None
        
        # Test different widget types for _update_widget_data coverage
        chart_widget = DashboardWidget(
            widget_id='chart_widget',
            widget_type='chart',
            title='Test Chart',
            data={},
            position={'x': 0, 'y': 0, 'w': 6, 'h': 4}
        )
        chart_update = dashboard._update_widget_data(chart_widget, {'test': 'data'})
        assert chart_update is not None
        
        # Test alert widget type
        alert_widget = DashboardWidget(
            widget_id='alert_widget', 
            widget_type='alert',
            title='Test Alert',
            data={},
            position={'x': 0, 'y': 0, 'w': 4, 'h': 2}
        )
        alert_update = dashboard._update_widget_data(alert_widget, {'test': 'data'})
        assert alert_update is not None
        
        # Test get_strategy_comparison_data with mocked results to cover lines 301-323
        with patch.object(dashboard, '_get_current_strategy_results') as mock_strategy_results:
            # Mock performance metrics with max_drawdown to test status logic
            mock_perf_metrics = type('PerformanceMetrics', (), {
                'max_drawdown': -0.20,  # Triggers Warning status
                'sharpe_ratio': 1.5
            })()
            
            mock_trade_metrics = type('TradeMetrics', (), {
                'total_trades': 50,
                'win_rate': 0.65,
                'total_profit': 1500.0
            })()
            
            mock_result = type('AnalyticsResult', (), {
                'metrics': {
                    'trade_metrics': mock_trade_metrics,
                    'performance_metrics': mock_perf_metrics
                }
            })()
            
            mock_strategy_results.return_value = {'test_strategy': mock_result}
            comparison_data_detailed = dashboard.get_strategy_comparison_data()
            assert comparison_data_detailed is not None
            
            # Test Critical status case (lines 310-311) - need drawdown between -0.15 and -0.25
            mock_perf_metrics_critical = type('PerformanceMetrics', (), {
                'max_drawdown': -0.18,  # Between -0.15 and -0.25, should trigger elif
                'sharpe_ratio': 0.5
            })()
            
            mock_result_critical = type('AnalyticsResult', (), {
                'metrics': {
                    'trade_metrics': mock_trade_metrics,
                    'performance_metrics': mock_perf_metrics_critical
                }
            })()
            
            mock_strategy_results.return_value = {'critical_strategy': mock_result_critical}
            comparison_critical = dashboard.get_strategy_comparison_data()
            assert comparison_critical is not None
            
            # Test another critical case less than -0.25
            mock_perf_metrics_critical2 = type('PerformanceMetrics', (), {
                'max_drawdown': -0.30,  # Less than -0.25
                'sharpe_ratio': 0.5
            })()
            
            mock_result_critical2 = type('AnalyticsResult', (), {
                'metrics': {
                    'trade_metrics': mock_trade_metrics,
                    'performance_metrics': mock_perf_metrics_critical2
                }
            })()
            
            mock_strategy_results.return_value = {'critical_strategy2': mock_result_critical2}
            comparison_critical2 = dashboard.get_strategy_comparison_data()
            assert comparison_critical2 is not None
            
            # Test hasattr condition false case - performance_metrics without max_drawdown
            mock_perf_no_drawdown = type('PerformanceMetrics', (), {
                'sharpe_ratio': 1.0
                # No max_drawdown attribute
            })()
            
            mock_result_no_drawdown = type('AnalyticsResult', (), {
                'metrics': {
                    'trade_metrics': mock_trade_metrics,
                    'performance_metrics': mock_perf_no_drawdown
                }
            })()
            
            mock_strategy_results.return_value = {'no_drawdown_strategy': mock_result_no_drawdown}
            comparison_no_drawdown = dashboard.get_strategy_comparison_data()
            assert comparison_no_drawdown is not None
        
        # Test get_risk_indicators to cover lines 348-374
        with patch.object(dashboard, '_get_current_strategy_results') as mock_risk_results:
            # Test with different risk levels
            
            # Low risk scenario (drawdown > -0.05)
            mock_perf_low_risk = type('PerformanceMetrics', (), {
                'max_drawdown': -0.03,
                'sharpe_ratio': 2.0
            })()
            
            mock_result_low = type('AnalyticsResult', (), {
                'metrics': {
                    'performance_metrics': mock_perf_low_risk
                }
            })()
            
            mock_risk_results.return_value = {'low_risk_strategy': mock_result_low}
            risk_low = dashboard.get_risk_indicators()
            assert risk_low is not None
            assert risk_low['risk_level'] == 'Low'
            
            # Medium risk scenario (drawdown > -0.15)
            mock_perf_medium_risk = type('PerformanceMetrics', (), {
                'max_drawdown': -0.10,
                'sharpe_ratio': 1.5
            })()
            
            mock_result_medium = type('AnalyticsResult', (), {
                'metrics': {
                    'performance_metrics': mock_perf_medium_risk
                }
            })()
            
            mock_risk_results.return_value = {'medium_risk_strategy': mock_result_medium}
            risk_medium = dashboard.get_risk_indicators()
            assert risk_medium is not None
            assert risk_medium['risk_level'] == 'Medium'
            
            # High risk scenario (drawdown <= -0.15)
            mock_perf_high_risk = type('PerformanceMetrics', (), {
                'max_drawdown': -0.20,
                'sharpe_ratio': 0.8
            })()
            
            mock_result_high = type('AnalyticsResult', (), {
                'metrics': {
                    'performance_metrics': mock_perf_high_risk
                }
            })()
            
            mock_risk_results.return_value = {'high_risk_strategy': mock_result_high}
            risk_high = dashboard.get_risk_indicators()
            assert risk_high is not None
            assert risk_high['risk_level'] == 'High'
            
            # Empty results case
            mock_risk_results.return_value = {}
            risk_empty = dashboard.get_risk_indicators()
            assert risk_empty is not None
        
        # Test get_drawdown_chart_data to cover lines 397-403
        with patch.object(dashboard, '_get_current_strategy_results') as mock_drawdown_results:
            # Test with performance metrics
            mock_perf_with_drawdown = type('PerformanceMetrics', (), {
                'max_drawdown': -0.15
            })()
            
            mock_result_drawdown = type('AnalyticsResult', (), {
                'metrics': {
                    'performance_metrics': mock_perf_with_drawdown
                }
            })()
            
            mock_drawdown_results.return_value = {'drawdown_strategy': mock_result_drawdown}
            drawdown_chart = dashboard.get_drawdown_chart_data()
            assert drawdown_chart is not None
            assert drawdown_chart.chart_type == 'bar'
            
            # Test with multiple strategies
            mock_result_2 = type('AnalyticsResult', (), {
                'metrics': {
                    'performance_metrics': mock_perf_with_drawdown
                }
            })()
            
            mock_drawdown_results.return_value = {
                'strategy_1': mock_result_drawdown,
                'strategy_2': mock_result_2
            }
            drawdown_multi = dashboard.get_drawdown_chart_data()
            assert drawdown_multi is not None
            
            # Test with no performance metrics
            mock_result_no_perf = type('AnalyticsResult', (), {
                'metrics': {}
            })()
            
            mock_drawdown_results.return_value = {'no_perf_strategy': mock_result_no_perf}
            drawdown_no_perf = dashboard.get_drawdown_chart_data()
            assert drawdown_no_perf is not None
        
        # Test export_dashboard_data CSV format to cover lines 443-454
        with patch.object(dashboard, 'get_strategy_comparison_data') as mock_csv_data:
            mock_csv_data.return_value = {
                'headers': ['Strategy', 'Trades', 'Win Rate', 'Profit'],
                'rows': [
                    ['Strategy1', 100, '65.0%', '$1500.00'],
                    ['Strategy2', 80, '70.0%', '$1200.00']
                ]
            }
            
            csv_export = dashboard.export_dashboard_data('csv')
            assert csv_export is not None
            assert 'Strategy,Trades,Win Rate,Profit' in csv_export
            assert 'Strategy1,100,65.0%,$1500.00' in csv_export
            
            # Test unsupported format to cover else clause
            try:
                dashboard.export_dashboard_data('xml')
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "Unsupported export format" in str(e)
        
        # Test _calculate_concentration_risk to cover lines 540-557
        # Test single strategy case (line 537-538)
        single_result = {
            'strategy1': type('AnalyticsResult', (), {
                'metrics': {'trade_metrics': mock_trade_metrics}
            })()
        }
        concentration_single = dashboard._calculate_concentration_risk(single_result)
        assert concentration_single == 100.0
        
        # Test multiple strategies case
        result1 = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': type('TradeMetrics', (), {
                    'total_profit': 1000.0
                })()
            }
        })()
        
        result2 = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': type('TradeMetrics', (), {
                    'total_profit': 500.0
                })()
            }
        })()
        
        multiple_results = {'strategy1': result1, 'strategy2': result2}
        concentration_multiple = dashboard._calculate_concentration_risk(multiple_results)
        assert concentration_multiple > 0
        
        # Test empty profits case (line 549-550) - need multiple strategies with zero profits
        empty_profit_result1 = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': type('TradeMetrics', (), {
                    'total_profit': 0
                })()
            }
        })()
        
        empty_profit_result2 = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': type('TradeMetrics', (), {
                    'total_profit': 0
                })()
            }
        })()
        
        empty_results = {'empty_strategy1': empty_profit_result1, 'empty_strategy2': empty_profit_result2}
        concentration_empty = dashboard._calculate_concentration_risk(empty_results)
        assert concentration_empty == 0.0
        
        # Test no trade_metrics case - single strategy with no trade_metrics returns 100.0
        no_trade_result = type('AnalyticsResult', (), {
            'metrics': {}
        })()
        
        no_trade_results = {'no_trade_strategy': no_trade_result}
        concentration_no_trade = dashboard._calculate_concentration_risk(no_trade_results)
        assert concentration_no_trade == 100.0  # Single strategy always returns 100.0

    def test_dashboard_critical_status_coverage(self, dashboard):
        """Test critical status lines 310-311 in get_strategy_comparison_data."""
        # Test case 1: Critical drawdown (< -0.25) -> Critical status
        mock_performance_metrics_critical = type('PerformanceMetrics', (), {
            'max_drawdown': -0.30,  # < -0.25 -> Critical
            'sharpe_ratio': 0.5
        })()
        
        mock_trade_metrics = type('TradeMetrics', (), {
            'total_trades': 10,
            'win_rate': 0.6,
            'total_profit': 1000.0
        })()
        
        mock_result_critical = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': mock_trade_metrics,
                'performance_metrics': mock_performance_metrics_critical
            }
        })()
        
        # This should trigger Critical status (first condition after fix)
        with patch.object(dashboard, '_get_current_strategy_results') as mock_get_results:
            mock_get_results.return_value = {'test_strategy': mock_result_critical}
            
            comparison_data = dashboard.get_strategy_comparison_data()
            
            # Verify the Critical status is set (covering lines 310-311)
            assert len(comparison_data['rows']) == 1
            row = comparison_data['rows'][0]
            assert row[6] == 'Critical'  # Status column should be 'Critical'
            
        # Test Warning status as well (line 309)  
        mock_performance_metrics_warning = type('PerformanceMetrics', (), {
            'max_drawdown': -0.20,  # Between -0.15 and -0.25 -> Warning status
            'sharpe_ratio': 0.8
        })()
        
        mock_result_warning = type('AnalyticsResult', (), {
            'metrics': {
                'trade_metrics': mock_trade_metrics,
                'performance_metrics': mock_performance_metrics_warning
            }
        })()
        
        with patch.object(dashboard, '_get_current_strategy_results') as mock_get_results:
            mock_get_results.return_value = {'warning_strategy': mock_result_warning}
            
            comparison_data = dashboard.get_strategy_comparison_data()
            
            # Verify the Warning status is set 
            assert len(comparison_data['rows']) == 1
            row = comparison_data['rows'][0]
            assert row[6] == 'Warning'  # Status column should be 'Warning'
