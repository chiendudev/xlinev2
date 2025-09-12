"""Final comprehensive test coverage for Analytics Reporter module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
from xline.core.analytics.reporter import (
    AnalyticsReporter, ReportConfig, PerformanceReport, PortfolioReport
)
from xline.core.analytics.metrics import (
    TradeMetrics, PerformanceMetrics, RiskMetrics
)
from xline.core.analytics.engine import AnalyticsResult


class TestAnalyticsReporterFinal:
    """Final comprehensive test for AnalyticsReporter coverage."""
    
    @pytest.fixture
    def reporter(self):
        """Create reporter instance."""
        config = ReportConfig(
            include_charts=True,
            export_format='json',
            date_format='%Y-%m-%d %H:%M:%S',
            decimal_places=4,
            include_raw_data=False,
            compress_output=False
        )
        return AnalyticsReporter(config)
    
    @pytest.fixture
    def reporter_no_config(self):
        """Create reporter without config."""
        return AnalyticsReporter()
    
    @pytest.fixture
    def sample_analytics_result(self):
        """Create sample analytics result."""
        trade_metrics = TradeMetrics(
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            total_profit=1500.0,
            total_loss=-800.0,
            gross_profit=2300.0,
            gross_loss=-800.0,
            largest_win=200.0,
            largest_loss=-150.0,
            avg_win=38.33,
            avg_loss=-20.0,
            win_rate=0.6,
            profit_factor=2.875,
            total_volume=100000.0,
            total_commission=50.0
        )
        
        performance_metrics = PerformanceMetrics(
            total_return=1500.0,
            total_return_pct=15.0,
            annualized_return=12.0,
            daily_return=0.05,
            volatility=0.15,
            max_drawdown=0.08,
            sharpe_ratio=1.8,
            sortino_ratio=2.1,
            calmar_ratio=1.5,
            recovery_factor=2.0,
            profit_to_maxdd_ratio=18.75
        )
        
        risk_metrics = RiskMetrics(
            volatility=0.15,
            var_95=50.0,
            var_99=75.0,
            expected_shortfall=62.5,
            max_consecutive_losses=3,
            downside_deviation=0.08,
            upside_deviation=0.12,
            beta=1.1,
            alpha=0.02,
            tracking_error=0.03,
            information_ratio=0.67
        )
        
        return AnalyticsResult(
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            metrics={
                'trade_metrics': trade_metrics,
                'performance_metrics': performance_metrics,
                'risk_metrics': risk_metrics
            },
            alerts=[],
            performance_summary={
                'period_start': datetime.now() - timedelta(days=30),
                'period_end': datetime.now()
            }
        )
    
    @pytest.fixture
    def sample_performance_report(self):
        """Create sample performance report."""
        trade_metrics = TradeMetrics(
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate=0.6,
            total_profit=1000.0,
            avg_win=33.33,
            avg_loss=-15.0
        )
        
        performance_metrics = PerformanceMetrics(
            total_return=1000.0,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            volatility=0.2
        )
        
        risk_metrics = RiskMetrics(
            volatility=0.2,
            var_95=40.0,
            max_consecutive_losses=2
        )
        
        now = datetime.now()
        return PerformanceReport(
            strategy_id="test_strategy",
            period_start=now - timedelta(days=30),
            period_end=now,
            trade_metrics=trade_metrics,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            summary={},
            recommendations=[],
            generated_at=now
        )
    
    def test_reporter_initialization_with_config(self, reporter):
        """Test reporter initialization with config."""
        assert reporter.config is not None
        assert reporter.config.include_charts is True
        assert reporter.config.export_format == 'json'
        assert reporter.config.decimal_places == 4
    
    def test_reporter_initialization_without_config(self, reporter_no_config):
        """Test reporter initialization without config."""
        assert reporter_no_config.config is not None
        assert reporter_no_config.config.include_charts is True
        assert reporter_no_config.config.export_format == 'json'
    
    def test_generate_strategy_report(self, reporter, sample_analytics_result):
        """Test strategy report generation."""
        report = reporter.generate_strategy_report("test_strategy", sample_analytics_result)
        assert isinstance(report, PerformanceReport)
        assert report.strategy_id == "test_strategy"
        assert report.trade_metrics.total_trades == 100
        assert report.performance_metrics.total_return == 1500.0
        assert report.risk_metrics.volatility == 0.15
    
    def test_generate_strategy_report_default_periods(self, reporter):
        """Test strategy report with default periods."""
        # Create analytics result without specific periods
        trade_metrics = TradeMetrics(total_trades=50, win_rate=0.6)
        performance_metrics = PerformanceMetrics(total_return=500.0)
        risk_metrics = RiskMetrics(volatility=0.1)
        
        analytics_result = AnalyticsResult(
            timestamp=datetime.now(),
            strategy_id="default_test",
            metrics={
                'trade_metrics': trade_metrics,
                'performance_metrics': performance_metrics,
                'risk_metrics': risk_metrics
            },
            alerts=[],
            performance_summary={}
        )
        
        report = reporter.generate_strategy_report("default_test", analytics_result)
        assert report.strategy_id == "default_test"
        assert report.period_start is not None
        assert report.period_end is not None
    
    def test_generate_portfolio_report(self, reporter, sample_analytics_result):
        """Test portfolio report generation."""
        reports = {"test_strategy": sample_analytics_result}
        portfolio_report = reporter.generate_portfolio_report(reports)
        
        assert isinstance(portfolio_report, PortfolioReport)
        assert portfolio_report.total_strategies == 1
        assert len(portfolio_report.strategy_reports) == 1
        assert portfolio_report.portfolio_metrics is not None
    
    def test_export_report_json_format(self, reporter, sample_performance_report):
        """Test JSON export format."""
        result = reporter.export_report(sample_performance_report, 'json')
        assert isinstance(result, str)
        assert 'test_strategy' in result
    
    def test_export_report_csv_format(self, reporter, sample_performance_report):
        """Test CSV export format."""
        result = reporter.export_report(sample_performance_report, 'csv')
        assert isinstance(result, str)
        assert 'test_strategy' in result
    
    def test_export_report_html_format(self, reporter, sample_performance_report):
        """Test HTML export format."""
        result = reporter.export_report(sample_performance_report, 'html')
        assert isinstance(result, str)
        assert 'test_strategy' in result
    
    def test_export_report_invalid_format(self, reporter, sample_performance_report):
        """Test export with invalid format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            reporter.export_report(sample_performance_report, 'invalid')
    
    def test_export_report_default_format(self, reporter, sample_performance_report):
        """Test export with default format."""
        result = reporter.export_report(sample_performance_report)
        assert isinstance(result, str)
    
    def test_get_dashboard_data(self, reporter, sample_analytics_result):
        """Test dashboard data generation."""
        reports = {"test_strategy": sample_analytics_result}
        dashboard_data = reporter.get_dashboard_data(reports)
        
        assert isinstance(dashboard_data, dict)
        assert 'timestamp' in dashboard_data
        assert 'strategies' in dashboard_data
        assert 'portfolio_summary' in dashboard_data
        assert 'risk_indicators' in dashboard_data
    
    def test_generate_strategy_summary(self, reporter, sample_performance_report):
        """Test strategy summary generation."""
        summary = reporter._generate_strategy_summary(
            sample_performance_report.trade_metrics,
            sample_performance_report.performance_metrics,
            sample_performance_report.risk_metrics
        )
        
        assert isinstance(summary, dict)
        assert 'total_trades' in summary
        assert 'win_rate' in summary
        assert 'total_return' in summary
        assert 'max_drawdown' in summary
        assert 'sharpe_ratio' in summary
    
    def test_generate_recommendations(self, reporter, sample_performance_report):
        """Test recommendations generation."""
        recommendations = reporter._generate_recommendations(
            sample_performance_report.trade_metrics,
            sample_performance_report.performance_metrics,
            sample_performance_report.risk_metrics
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)
    
    def test_calculate_portfolio_metrics(self, reporter):
        """Test portfolio metrics calculation."""
        # Create multiple performance reports
        now = datetime.now()
        reports = []
        
        for i in range(3):
            trade_metrics = TradeMetrics(
                total_trades=50 + i * 10,
                win_rate=0.6 + i * 0.05,
                total_profit=1000.0 + i * 200
            )
            performance_metrics = PerformanceMetrics(
                total_return=1000.0 + i * 200,
                sharpe_ratio=1.5 + i * 0.2
            )
            risk_metrics = RiskMetrics(volatility=0.15 - i * 0.02)
            
            report = PerformanceReport(
                strategy_id=f"strategy_{i}",
                period_start=now - timedelta(days=30),
                period_end=now,
                trade_metrics=trade_metrics,
                performance_metrics=performance_metrics,
                risk_metrics=risk_metrics,
                summary={},
                recommendations=[],
                generated_at=now
            )
            reports.append(report)
        
        metrics = reporter._calculate_portfolio_metrics(reports)
        assert isinstance(metrics, dict)
        assert 'strategy_count' in metrics
        assert 'total_profit' in metrics
        assert 'weighted_sharpe_ratio' in metrics
    
    def test_calculate_portfolio_correlation(self, reporter):
        """Test portfolio correlation calculation."""
        # Create test reports
        now = datetime.now()
        reports = []
        
        for i in range(2):
            performance_metrics = PerformanceMetrics(
                total_return=1000.0 + i * 100,
                volatility=0.15 + i * 0.05
            )
            
            report = PerformanceReport(
                strategy_id=f"strategy_{i}",
                period_start=now - timedelta(days=30),
                period_end=now,
                trade_metrics=TradeMetrics(),
                performance_metrics=performance_metrics,
                risk_metrics=RiskMetrics(),
                summary={},
                recommendations=[],
                generated_at=now
            )
            reports.append(report)
        
        # Convert to dict format expected by method
        from xline.core.analytics.engine import AnalyticsResult
        strategy_results = {}
        for i in range(2):
            strategy_results[f"strategy_{i}"] = AnalyticsResult(
                timestamp=now,
                strategy_id=f"strategy_{i}",
                metrics={'trade_metrics': TradeMetrics()},
                alerts=[],
                performance_summary={}
            )
        correlation = reporter._calculate_portfolio_correlation(strategy_results)
        assert isinstance(correlation, dict)
        # Method returns empty dict when insufficient data - this is expected behavior
    
    def test_generate_portfolio_risk_summary(self, reporter):
        """Test portfolio risk summary generation."""
        now = datetime.now()
        reports = []
        
        for i in range(2):
            risk_metrics = RiskMetrics(
                volatility=0.15 + i * 0.05,
                var_95=50.0 + i * 10,
                max_consecutive_losses=2 + i
            )
            
            report = PerformanceReport(
                strategy_id=f"strategy_{i}",
                period_start=now - timedelta(days=30),
                period_end=now,
                trade_metrics=TradeMetrics(),
                performance_metrics=PerformanceMetrics(),
                risk_metrics=risk_metrics,
                summary={},
                recommendations=[],
                generated_at=now
            )
            reports.append(report)
        
        risk_summary = reporter._generate_portfolio_risk_summary(reports)
        assert isinstance(risk_summary, dict)
        assert 'avg_max_drawdown' in risk_summary
        assert 'avg_sharpe_ratio' in risk_summary
    
    def test_calculate_risk_score(self, reporter):
        """Test risk score calculation."""
        risk_metrics = RiskMetrics(
            volatility=0.15,
            var_95=50.0,
            max_consecutive_losses=3,
            downside_deviation=0.08
        )
        
        performance_metrics = PerformanceMetrics(volatility=0.15, max_drawdown=0.1, sharpe_ratio=1.5)
        score = reporter._calculate_risk_score(performance_metrics, risk_metrics)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
    
    def test_calculate_performance_grade(self, reporter):
        """Test performance grade calculation."""
        performance_metrics = PerformanceMetrics(
            sharpe_ratio=1.8,
            total_return_pct=15.0,
            max_drawdown=0.08
        )
        trade_metrics = TradeMetrics(
            win_rate=0.6,
            profit_factor=2.5
        )
        
        grade = reporter._calculate_performance_grade(performance_metrics, trade_metrics)
        assert isinstance(grade, str)
        assert grade in ['A', 'B', 'C', 'D', 'F']
    
    def test_assess_portfolio_risk_level(self, reporter):
        """Test portfolio risk level assessment."""
        now = datetime.now()
        reports = []
        
        risk_metrics = RiskMetrics(
            volatility=0.2,
            var_95=60.0,
            max_consecutive_losses=4
        )
        
        report = PerformanceReport(
            strategy_id="high_risk_strategy",
            period_start=now - timedelta(days=30),
            period_end=now,
            trade_metrics=TradeMetrics(),
            performance_metrics=PerformanceMetrics(),
            risk_metrics=risk_metrics,
            summary={},
            recommendations=[],
            generated_at=now
        )
        reports.append(report)
        
        risk_level = reporter._assess_portfolio_risk_level(reports)
        assert isinstance(risk_level, str)
        assert risk_level in ['Low', 'Medium', 'High', 'Very High']
    
    def test_calculate_diversification_score(self, reporter):
        """Test diversification score calculation."""
        now = datetime.now()
        reports = []
        
        # Create multiple diverse strategies
        for i in range(3):
            performance_metrics = PerformanceMetrics(
                volatility=0.15 + i * 0.03,
                total_return=1000 + i * 200
            )
            
            report = PerformanceReport(
                strategy_id=f"diverse_strategy_{i}",
                period_start=now - timedelta(days=30),
                period_end=now,
                trade_metrics=TradeMetrics(),
                performance_metrics=performance_metrics,
                risk_metrics=RiskMetrics(),
                summary={},
                recommendations=[],
                generated_at=now
            )
            reports.append(report)
        
        score = reporter._calculate_diversification_score(reports)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
    
    def test_export_json_with_datetime_serialization(self, reporter, sample_performance_report):
        """Test JSON export with datetime objects."""
        result = reporter._export_json(sample_performance_report)
        assert isinstance(result, str)
        assert 'test_strategy' in result
    
    def test_export_csv_with_performance_report(self, reporter, sample_performance_report):
        """Test CSV export with performance report."""
        result = reporter._export_csv(sample_performance_report)
        assert isinstance(result, str)
        assert 'test_strategy' in result
    
    def test_export_csv_with_portfolio_report(self, reporter, sample_performance_report):
        """Test CSV export with portfolio report."""
        now = datetime.now()
        portfolio_report = PortfolioReport(
            period_start=now - timedelta(days=30),
            period_end=now,
            total_strategies=1,
            portfolio_metrics={'total_return': 1000.0},
            strategy_reports=[sample_performance_report],
            correlation_matrix={},
            risk_summary={},
            generated_at=now
        )
        
        result = reporter._export_csv(portfolio_report)
        assert isinstance(result, str)
    
    def test_export_html_basic(self, reporter, sample_performance_report):
        """Test basic HTML export."""
        result = reporter._export_html(sample_performance_report)
        assert isinstance(result, str)
        assert 'test_strategy' in result
