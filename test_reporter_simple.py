"""Simple test to check reporter current coverage and fix missing lines."""

from datetime import datetime
from unittest.mock import MagicMock
import pytest

from xline.core.analytics.reporter import (
    AnalyticsReporter, 
    ReportConfig, 
    PerformanceReport
)
from xline.core.analytics.metrics import (
    TradeMetrics, 
    PerformanceMetrics, 
    RiskMetrics
)
from xline.core.analytics.engine import AnalyticsResult


def test_reporter_basic_functionality():
    """Test basic reporter functionality to check coverage."""
    # Test initialization
    config = ReportConfig()
    reporter = AnalyticsReporter(config)
    assert reporter is not None
    
    # Test get_dashboard_data with empty data
    dashboard = reporter.get_dashboard_data({})
    assert isinstance(dashboard, dict)
    
    # Test with some mock data
    mock_results = {
        'strategy1': MagicMock(),
        'strategy2': MagicMock()
    }
    
    # Configure mock results properly
    for strategy_id, result in mock_results.items():
        result.metrics = {
            'trade_metrics': MagicMock(
                total_trades=100,
                total_profit=1500.0,
                win_rate=0.65,
                avg_profit=15.0
            ),
            'performance_metrics': MagicMock(
                sharpe_ratio=1.5,
                max_drawdown=-0.12
            ),
            'risk_metrics': MagicMock(
                volatility=0.25,
                var_95=-0.02
            )
        }
    
    dashboard = reporter.get_dashboard_data(mock_results)
    assert isinstance(dashboard, dict)
    assert 'portfolio_summary' in dashboard


def test_reporter_report_generation():
    """Test report generation methods."""
    reporter = AnalyticsReporter()
    
    # Create sample analytics result
    mock_result = AnalyticsResult(
        timestamp=datetime.now(),
        strategy_id="test_strategy",
        metrics={
            'trade_metrics': TradeMetrics(total_trades=50),
            'performance_metrics': PerformanceMetrics(total_return=750.0),
            'risk_metrics': RiskMetrics(volatility=0.15)
        }
    )
    
    # Test strategy report generation
    report = reporter.generate_strategy_report(
        "test_strategy",
        mock_result,
        datetime(2024, 1, 1),
        datetime(2024, 12, 31)
    )
    assert isinstance(report, PerformanceReport)
    assert report.strategy_id == "test_strategy"


def test_reporter_export_functions():
    """Test export functionality."""
    reporter = AnalyticsReporter()
    
    # Create sample performance report
    report = PerformanceReport(
        strategy_id="test_strategy",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31),
        trade_metrics=TradeMetrics(total_trades=100),
        performance_metrics=PerformanceMetrics(total_return=1500.0),
        risk_metrics=RiskMetrics(volatility=0.15),
        summary={'test': 'data'},
        recommendations=['test recommendation'],
        generated_at=datetime.now()
    )
    
    # Test JSON export
    json_result = reporter.export_report(report, 'json')
    assert isinstance(json_result, str)
    
    # Test CSV export
    csv_result = reporter.export_report(report, 'csv')
    assert isinstance(csv_result, str)
    
    # Test HTML export
    html_result = reporter.export_report(report, 'html')
    assert isinstance(html_result, str)


def test_reporter_portfolio_functions():
    """Test portfolio-related functionality."""
    reporter = AnalyticsReporter()
    
    # Create mock analytics results
    analytics_results = {}
    for i in range(3):
        mock_result = MagicMock()
        mock_result.metrics = {
            'trade_metrics': TradeMetrics(
                total_trades=100,
                total_profit=1000.0 + i * 100
            ),
            'performance_metrics': PerformanceMetrics(
                total_return=1000.0 + i * 100,
                sharpe_ratio=1.0 + i * 0.2
            ),
            'risk_metrics': RiskMetrics(
                volatility=0.2 + i * 0.05
            )
        }
        analytics_results[f'strategy_{i}'] = mock_result
    
    # Test portfolio report generation
    portfolio_report = reporter.generate_portfolio_report(
        analytics_results,
        datetime(2024, 1, 1),
        datetime(2024, 12, 31)
    )
    assert portfolio_report is not None
    assert portfolio_report.total_strategies == 3


if __name__ == "__main__":
    test_reporter_basic_functionality()
    test_reporter_report_generation()
    test_reporter_export_functions()
    test_reporter_portfolio_functions()
    print("All tests passed!")
