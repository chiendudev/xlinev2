"""Comprehensive test suite for Xline Analytics Engine - 95% Coverage Target.

This module provides extensive tests to achieve >95% coverage across
all analytics components including engine, metrics, reporter, and dashboard.
"""

from datetime import datetime
from unittest.mock import MagicMock

from xline.core.analytics.engine import (
    AnalyticsConfig,
    AnalyticsEngine,
    AnalyticsResult,
    TradeEvent,
)
from xline.core.analytics.metrics import TradingMetricsCalculator
from xline.core.analytics.reporter import AnalyticsReporter
from xline.core.analytics.dashboard import AnalyticsDashboard


class TestComprehensiveAnalytics:
    """Comprehensive test coverage for all analytics components."""

    def test_analytics_config_comprehensive(self):
        """Test all AnalyticsConfig options."""
        # Test default config
        config = AnalyticsConfig()
        assert config.enable_real_time is True
        assert config.metrics_interval == 60
        assert config.cache_duration == 300
        assert config.max_events_buffer == 10000
        assert config.risk_free_rate == 0.02
        assert config.enable_alerts is True
        assert config.alert_thresholds is None
        
        # Test custom config
        custom_config = AnalyticsConfig(
            enable_real_time=False,
            metrics_interval=30,
            cache_duration=600,
            max_events_buffer=5000,
            risk_free_rate=0.03,
            enable_alerts=False,
            alert_thresholds={'max_drawdown': -0.15}
        )
        assert custom_config.enable_real_time is False
        assert custom_config.metrics_interval == 30
        assert custom_config.cache_duration == 600
        assert custom_config.max_events_buffer == 5000
        assert custom_config.risk_free_rate == 0.03
        assert custom_config.enable_alerts is False
        assert custom_config.alert_thresholds == {'max_drawdown': -0.15}
        
        print("✅ Analytics config comprehensive test passed")

    def test_trade_event_comprehensive(self):
        """Test TradeEvent with all possible fields."""
        # Test with minimal data
        minimal_event = TradeEvent(
            event_id='min_001',
            timestamp=datetime.now(),
            strategy_id='minimal_strategy',
            symbol='BTC/USDT',
            action='buy',
            amount=1.0,
            price=50000.0
        )
        assert minimal_event.profit == 0.0
        assert minimal_event.commission == 0.0
        assert minimal_event.metadata is None
        
        # Test with full data
        full_event = TradeEvent(
            event_id='full_001',
            timestamp=datetime.now(),
            strategy_id='full_strategy',
            symbol='ETH/USDT',
            action='sell',
            amount=2.5,
            price=3000.0,
            profit=150.0,
            commission=7.5,
            metadata={'source': 'manual', 'confidence': 0.95}
        )
        assert full_event.profit == 150.0
        assert full_event.commission == 7.5
        assert full_event.metadata == {'source': 'manual', 'confidence': 0.95}
        
        print("✅ Trade event comprehensive test passed")

    def test_analytics_result_comprehensive(self):
        """Test AnalyticsResult with various data combinations."""
        # Test minimal result
        minimal_result = AnalyticsResult(
            timestamp=datetime.now(),
            strategy_id='test_strategy',
            metrics={'basic': 'data'}
        )
        assert minimal_result.alerts is None
        assert minimal_result.performance_summary is None
        
        # Test full result
        full_result = AnalyticsResult(
            timestamp=datetime.now(),
            strategy_id='full_strategy',
            metrics={
                'trade_metrics': {'total_trades': 10},
                'performance_metrics': {'total_return': 1500.0},
                'risk_metrics': {'var_95': -0.02}
            },
            alerts=[
                {'type': 'warning', 'message': 'High volatility detected'},
                {'type': 'info', 'message': 'Strategy performing well'}
            ],
            performance_summary={
                'grade': 'A',
                'risk_level': 'medium',
                'recommendation': 'continue'
            }
        )
        assert len(full_result.alerts) == 2
        assert full_result.performance_summary['grade'] == 'A'
        
        print("✅ Analytics result comprehensive test passed")

    def test_metrics_calculator_edge_cases(self):
        """Test metrics calculator with edge cases and boundary conditions."""
        calculator = TradingMetricsCalculator(risk_free_rate=0.025)
        
        # Test empty trades
        empty_trades = []
        trade_metrics = calculator.calculate_trade_metrics(empty_trades)
        assert trade_metrics.total_trades == 0
        assert trade_metrics.win_rate == 0.0
        assert trade_metrics.profit_factor == 0.0
        
        performance_metrics = calculator.calculate_performance_metrics(empty_trades)
        assert performance_metrics.total_return == 0.0
        assert performance_metrics.volatility == 0.0
        
        risk_metrics = calculator.calculate_risk_metrics(empty_trades)
        assert risk_metrics.var_95 == 0.0
        assert risk_metrics.volatility == 0.0
        
        # Test single trade
        single_trade = [{'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0}]
        single_trade_metrics = calculator.calculate_trade_metrics(single_trade)
        assert single_trade_metrics.total_trades == 1
        assert single_trade_metrics.winning_trades == 1
        assert single_trade_metrics.losing_trades == 0
        assert single_trade_metrics.win_rate == 1.0
        
        # Test all losing trades
        losing_trades = [
            {'profit': -50.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
            {'profit': -75.0, 'amount': 1.5, 'price': 48000.0, 'commission': 7.5}
        ]
        losing_metrics = calculator.calculate_trade_metrics(losing_trades)
        assert losing_metrics.winning_trades == 0
        assert losing_metrics.losing_trades == 2
        assert losing_metrics.win_rate == 0.0
        assert losing_metrics.gross_profit == 0.0
        assert losing_metrics.gross_loss == -125.0
        
        # Test all winning trades
        winning_trades = [
            {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
            {'profit': 150.0, 'amount': 2.0, 'price': 52000.0, 'commission': 10.0}
        ]
        winning_metrics = calculator.calculate_trade_metrics(winning_trades)
        assert winning_metrics.winning_trades == 2
        assert winning_metrics.losing_trades == 0
        assert winning_metrics.win_rate == 1.0
        assert winning_metrics.gross_profit == 250.0
        assert winning_metrics.gross_loss == 0.0
        
        print("✅ Metrics calculator edge cases test passed")

    def test_analytics_engine_comprehensive(self):
        """Test analytics engine with comprehensive scenarios."""
        config = AnalyticsConfig(
            enable_real_time=False,  # Disable for sync testing
            metrics_interval=1,
            enable_alerts=True,
            alert_thresholds={
                'max_drawdown': -0.10,
                'min_win_rate': 0.40
            }
        )
        engine = AnalyticsEngine(config)
        
        # Test callback registration
        result_callback = MagicMock()
        alert_callback = MagicMock()
        
        engine.add_result_callback(result_callback)
        engine.add_alert_callback(alert_callback)
        
        assert len(engine._result_callbacks) == 1
        assert len(engine._alert_callbacks) == 1
        
        # Test portfolio summary with no data
        empty_summary = engine.get_portfolio_summary()
        assert empty_summary == {}
        
        # Test portfolio summary with data
        engine._trade_history = {
            'strategy1': [
                {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
                {'profit': -50.0, 'amount': 1.0, 'price': 49000.0, 'commission': 5.0}
            ],
            'strategy2': [
                {'profit': 200.0, 'amount': 2.0, 'price': 51000.0, 'commission': 10.0}
            ]
        }
        
        summary = engine.get_portfolio_summary()
        assert 'strategies_count' in summary
        assert summary['strategies_count'] == 2
        assert 'last_updated' in summary
        
        # Test metrics retrieval
        metrics_result = engine.get_strategy_metrics('nonexistent_strategy')
        assert metrics_result is None
        
        print("✅ Analytics engine comprehensive test passed")

    def test_reporter_initialization(self):
        """Test reporter component initialization."""
        from xline.core.analytics.reporter import AnalyticsReporter, ReportConfig
        
        config = ReportConfig()
        reporter = AnalyticsReporter(config)
        
        assert reporter.config == config
        assert reporter.metrics_calculator is not None
        assert reporter.reports_cache == {}
        
        print("✅ Reporter initialization test passed")

    def test_dashboard_initialization(self):
        """Test dashboard component initialization."""
        from xline.core.analytics.reporter import AnalyticsReporter, ReportConfig
        
        config = AnalyticsConfig()
        engine = AnalyticsEngine(config)
        reporter_config = ReportConfig()
        reporter = AnalyticsReporter(reporter_config)
        dashboard = AnalyticsDashboard(engine, reporter)
        
        assert dashboard.analytics_engine == engine
        assert dashboard.reporter == reporter
        assert dashboard.widgets == {}
        assert dashboard.layout_config == {}
        
        print("✅ Dashboard initialization test passed")

    def test_correlation_calculation(self):
        """Test strategy correlation calculations."""
        calculator = TradingMetricsCalculator()
        
        # Test correlation with multiple strategies
        strategy_returns = {
            'strategy1': [0.01, -0.02, 0.03, -0.01, 0.02],
            'strategy2': [0.02, -0.01, 0.04, 0.00, 0.01],
            'strategy3': [0.00, -0.03, 0.02, -0.02, 0.03]
        }
        
        correlation_matrix = calculator.calculate_strategy_correlation(strategy_returns)
        
        # Validate structure
        assert len(correlation_matrix) == 3
        for strategy in strategy_returns.keys():
            assert strategy in correlation_matrix
            assert len(correlation_matrix[strategy]) == 3
            # Self-correlation should be 1.0
            assert correlation_matrix[strategy][strategy] == 1.0
        
        # Test with insufficient data
        insufficient_data = {
            'strategy1': [0.01],
            'strategy2': [0.02]
        }
        insufficient_correlation = calculator.calculate_strategy_correlation(insufficient_data)
        assert insufficient_correlation['strategy1']['strategy2'] == 0.0
        
        print("✅ Correlation calculation test passed")

    def test_cache_functionality(self):
        """Test metrics calculator cache functionality."""
        calculator = TradingMetricsCalculator()
        
        # Test cache validation
        assert not calculator._is_cache_valid()
        
        # Test cache clearing
        calculator._cached_metrics = {'test': 'data'}
        calculator.clear_cache()
        assert calculator._cached_metrics == {}
        assert calculator._cache_timestamp is None
        
        print("✅ Cache functionality test passed")

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation with various scenarios."""
        calculator = TradingMetricsCalculator()
        
        # Test empty returns
        empty_drawdown = calculator._calculate_max_drawdown([])
        assert empty_drawdown == 0.0
        
        # Test positive returns only
        positive_returns = [0.01, 0.02, 0.015, 0.025, 0.01]
        positive_drawdown = calculator._calculate_max_drawdown(positive_returns)
        assert positive_drawdown <= 0.0  # Should be non-positive
        
        # Test negative returns only
        negative_returns = [-0.01, -0.02, -0.015, -0.025, -0.01]
        negative_drawdown = calculator._calculate_max_drawdown(negative_returns)
        assert negative_drawdown < 0.0  # Should be negative
        
        # Test mixed returns with significant drawdown
        mixed_returns = [0.05, 0.03, -0.10, -0.05, 0.02, 0.04]
        mixed_drawdown = calculator._calculate_max_drawdown(mixed_returns)
        assert mixed_drawdown < 0.0  # Should capture the drawdown
        
        print("✅ Max drawdown calculation test passed")

    def test_risk_metrics_consecutive_losses(self):
        """Test max consecutive losses calculation."""
        calculator = TradingMetricsCalculator()
        
        # Test no losses
        winning_trades = [
            {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
            {'profit': 50.0, 'amount': 1.0, 'price': 51000.0, 'commission': 5.0}
        ]
        winning_risk = calculator.calculate_risk_metrics(winning_trades)
        assert winning_risk.max_consecutive_losses == 0
        
        # Test consecutive losses
        consecutive_loss_trades = [
            {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},  # win
            {'profit': -25.0, 'amount': 1.0, 'price': 49000.0, 'commission': 5.0},  # loss 1
            {'profit': -30.0, 'amount': 1.0, 'price': 48000.0, 'commission': 5.0},  # loss 2
            {'profit': -20.0, 'amount': 1.0, 'price': 47000.0, 'commission': 5.0},  # loss 3
            {'profit': 75.0, 'amount': 1.0, 'price': 52000.0, 'commission': 5.0},   # win
            {'profit': -15.0, 'amount': 1.0, 'price': 51000.0, 'commission': 5.0}   # loss 1
        ]
        consecutive_risk = calculator.calculate_risk_metrics(consecutive_loss_trades)
        assert consecutive_risk.max_consecutive_losses == 3  # Three consecutive losses
        
        print("✅ Risk metrics consecutive losses test passed")

    def test_portfolio_metrics_comprehensive(self):
        """Test comprehensive portfolio metrics calculation."""
        calculator = TradingMetricsCalculator()
        
        # Test empty portfolio
        empty_portfolio = {}
        empty_metrics = calculator.get_portfolio_metrics(empty_portfolio)
        assert empty_metrics == {}
        
        # Test single strategy portfolio
        single_strategy = {
            'only_strategy': [
                {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0}
            ]
        }
        single_metrics = calculator.get_portfolio_metrics(single_strategy)
        assert single_metrics['total_strategies'] == 1
        assert single_metrics['total_trades'] == 1
        assert single_metrics['total_portfolio_return'] == 100.0
        
        # Test complex portfolio
        complex_portfolio = {
            'aggressive': [
                {'profit': 200.0, 'amount': 2.0, 'price': 50000.0, 'commission': 10.0},
                {'profit': -100.0, 'amount': 1.0, 'price': 48000.0, 'commission': 5.0},
                {'profit': 150.0, 'amount': 1.5, 'price': 52000.0, 'commission': 7.5}
            ],
            'conservative': [
                {'profit': 50.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
                {'profit': 25.0, 'amount': 0.5, 'price': 51000.0, 'commission': 2.5}
            ],
            'balanced': [
                {'profit': 80.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
                {'profit': -40.0, 'amount': 0.8, 'price': 49000.0, 'commission': 4.0},
                {'profit': 60.0, 'amount': 1.2, 'price': 51000.0, 'commission': 6.0}
            ]
        }
        
        complex_metrics = calculator.get_portfolio_metrics(complex_portfolio)
        
        # Validate comprehensive metrics
        assert complex_metrics['total_strategies'] == 3
        assert complex_metrics['total_trades'] == 8  # 3 + 2 + 3
        assert 'correlation_matrix' in complex_metrics
        assert 'individual_strategies' in complex_metrics
        assert 'strategies_summary' in complex_metrics
        
        # Validate individual strategy metrics
        assert 'aggressive' in complex_metrics['individual_strategies']
        assert 'conservative' in complex_metrics['individual_strategies']
        assert 'balanced' in complex_metrics['individual_strategies']
        
        # Validate correlation matrix structure
        correlation = complex_metrics['correlation_matrix']
        assert len(correlation) == 3
        for strategy in complex_portfolio.keys():
            assert strategy in correlation
            assert correlation[strategy][strategy] == 1.0
        
        print("✅ Portfolio metrics comprehensive test passed")


def test_complete_integration_comprehensive():
    """Comprehensive integration test covering all major code paths."""
    print("\n🔄 Running comprehensive integration test...")
    
    # Create comprehensive configuration
    config = AnalyticsConfig(
        enable_real_time=False,
        metrics_interval=1,
        cache_duration=300,
        max_events_buffer=1000,
        risk_free_rate=0.025,
        enable_alerts=True,
        alert_thresholds={
            'max_drawdown': -0.15,
            'min_win_rate': 0.35,
            'max_consecutive_losses': 5
        }
    )
    
    # Initialize all components
    engine = AnalyticsEngine(config)
    calculator = TradingMetricsCalculator(risk_free_rate=0.025)
    
    from xline.core.analytics.reporter import AnalyticsReporter, ReportConfig
    reporter_config = ReportConfig()
    reporter = AnalyticsReporter(reporter_config)
    dashboard = AnalyticsDashboard(engine, reporter)
    
    # Create comprehensive test data
    comprehensive_trades = [
        {'profit': 150.0, 'amount': 1.5, 'price': 50000.0, 'commission': 7.5},
        {'profit': -75.0, 'amount': 1.0, 'price': 49000.0, 'commission': 5.0},
        {'profit': 200.0, 'amount': 2.0, 'price': 52000.0, 'commission': 10.0},
        {'profit': -50.0, 'amount': 1.0, 'price': 48000.0, 'commission': 5.0},
        {'profit': 100.0, 'amount': 1.0, 'price': 51000.0, 'commission': 5.0},
        {'profit': -25.0, 'amount': 0.5, 'price': 47000.0, 'commission': 2.5},
        {'profit': 175.0, 'amount': 1.8, 'price': 53000.0, 'commission': 9.0},
        {'profit': -100.0, 'amount': 1.2, 'price': 46000.0, 'commission': 6.0}
    ]
    
    # Test all metrics calculations
    trade_metrics = calculator.calculate_trade_metrics(comprehensive_trades)
    performance_metrics = calculator.calculate_performance_metrics(comprehensive_trades)
    risk_metrics = calculator.calculate_risk_metrics(comprehensive_trades)
    
    # Validate comprehensive results
    assert trade_metrics.total_trades == 8
    assert trade_metrics.winning_trades == 4
    assert trade_metrics.losing_trades == 4
    assert trade_metrics.win_rate == 0.5
    assert trade_metrics.gross_profit == 625.0  # 150+200+100+175
    assert trade_metrics.gross_loss == -250.0   # -75-50-25-100
    assert trade_metrics.total_profit == 375.0  # 625-250
    
    assert performance_metrics.total_return == 375.0
    assert performance_metrics.volatility > 0
    assert performance_metrics.max_drawdown <= 0
    
    assert risk_metrics.volatility > 0
    assert risk_metrics.var_95 <= 0
    assert risk_metrics.max_consecutive_losses >= 0
    
    # Test portfolio-level functionality
    portfolio_data = {
        'strategy_alpha': comprehensive_trades[:4],
        'strategy_beta': comprehensive_trades[4:],
        'strategy_gamma': [
            {'profit': 50.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
            {'profit': 30.0, 'amount': 0.6, 'price': 51000.0, 'commission': 3.0}
        ]
    }
    
    portfolio_metrics = calculator.get_portfolio_metrics(portfolio_data)
    assert portfolio_metrics['total_strategies'] == 3
    assert portfolio_metrics['total_trades'] == 10  # 4+4+2
    assert portfolio_metrics['total_portfolio_return'] == 455.0  # 375+80
    
    # Test correlation matrix
    correlation_matrix = portfolio_metrics['correlation_matrix']
    assert len(correlation_matrix) == 3
    for strategy in portfolio_data.keys():
        assert strategy in correlation_matrix
        assert correlation_matrix[strategy][strategy] == 1.0
    
    # Test caching functionality
    calculator.clear_cache()
    assert calculator._cached_metrics == {}
    
    print("✅ Comprehensive integration test passed")
    print("🎉 All comprehensive analytics tests completed successfully!")


if __name__ == "__main__":
    test_complete_integration_comprehensive()
