"""Complete coverage test for metrics.py - targeting 100% coverage."""

import pytest
from datetime import datetime, timedelta

from xline.core.analytics.metrics import TradingMetricsCalculator


class TestMetricsCompleteCoverage:
    """Test class targeting 100% coverage for metrics.py."""

    def test_metrics_cache_functionality(self):
        """Test cache functionality including edge cases."""
        calculator = TradingMetricsCalculator()
        
        # Test cache validity check when no cache exists
        assert not calculator._is_cache_valid()
        
        # Set cache timestamp and test validity
        calculator._cache_timestamp = datetime.now()
        assert calculator._is_cache_valid()
        
        # Test expired cache
        calculator._cache_timestamp = datetime.now() - timedelta(seconds=31)
        assert not calculator._is_cache_valid()
        
        # Test cache clearing
        calculator._cached_metrics['test'] = 'value'
        calculator.clear_cache()
        assert len(calculator._cached_metrics) == 0
        assert calculator._cache_timestamp is None

    def test_edge_case_empty_trades(self):
        """Test edge cases with empty trade lists."""
        calculator = TradingMetricsCalculator()
        
        # Test empty list for all methods
        empty_trades = []
        
        trade_metrics = calculator.calculate_trade_metrics(empty_trades)
        assert trade_metrics.total_trades == 0
        
        perf_metrics = calculator.calculate_performance_metrics(empty_trades)
        assert perf_metrics.total_return == 0.0
        
        risk_metrics = calculator.calculate_risk_metrics(empty_trades)
        assert risk_metrics.volatility == 0.0

    def test_edge_case_single_trade(self):
        """Test edge cases with single trade."""
        calculator = TradingMetricsCalculator()
        
        single_trade = [{'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0}]
        
        trade_metrics = calculator.calculate_trade_metrics(single_trade)
        assert trade_metrics.total_trades == 1
        assert trade_metrics.winning_trades == 1
        assert trade_metrics.losing_trades == 0
        
        # Test performance metrics with single trade
        perf_metrics = calculator.calculate_performance_metrics(single_trade)
        assert perf_metrics.total_return == 100.0
        assert perf_metrics.volatility == 0.0  # No variance with single data point

    def test_portfolio_metrics_edge_cases(self):
        """Test portfolio metrics with edge cases."""
        calculator = TradingMetricsCalculator()
        
        # Empty strategy data
        empty_portfolio = calculator.get_portfolio_metrics({})
        assert empty_portfolio == {}
        
        # Single strategy
        single_strategy_data = {
            'strategy1': [
                {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
                {'profit': -50.0, 'amount': 1.0, 'price': 49000.0, 'commission': 5.0}
            ]
        }
        
        portfolio = calculator.get_portfolio_metrics(single_strategy_data)
        assert portfolio['total_strategies'] == 1
        assert portfolio['total_trades'] == 2
        assert 'strategy1' in portfolio['individual_strategies']

    def test_correlation_edge_cases(self):
        """Test correlation calculation edge cases."""
        calculator = TradingMetricsCalculator()
        
        # Test with insufficient data
        strategy_returns = {
            'strategy1': [0.01],  # Only one data point
            'strategy2': [0.02]   # Only one data point
        }
        
        correlation_matrix = calculator.calculate_strategy_correlation(strategy_returns)
        assert correlation_matrix['strategy1']['strategy1'] == 1.0
        assert correlation_matrix['strategy1']['strategy2'] == 0.0  # Should be 0 for insufficient data

    def test_risk_metrics_comprehensive(self):
        """Test risk metrics with various scenarios."""
        calculator = TradingMetricsCalculator()
        
        # Test with sufficient data for VaR calculation (>=5 points)
        trades = [{'profit': i * 10} for i in range(10)]  # 0, 10, 20, ..., 90
        
        risk_metrics = calculator.calculate_risk_metrics(trades, initial_capital=1000.0)
        assert risk_metrics.var_95 is not None
        assert risk_metrics.expected_shortfall is not None
        
        # Test with insufficient data for VaR (<5 points)
        few_trades = [{'profit': 10}, {'profit': 20}]
        risk_metrics_few = calculator.calculate_risk_metrics(few_trades)
        assert risk_metrics_few.var_95 == 0.0

    def test_max_drawdown_edge_cases(self):
        """Test max drawdown calculation edge cases."""
        calculator = TradingMetricsCalculator()
        
        # Test with empty returns
        assert calculator._calculate_max_drawdown([]) == 0.0
        
        # Test with all positive returns
        positive_returns = [0.01, 0.02, 0.01, 0.03]
        drawdown = calculator._calculate_max_drawdown(positive_returns)
        assert drawdown <= 0.0  # Should be negative or zero
        
        # Test with all negative returns
        negative_returns = [-0.01, -0.02, -0.01, -0.03]
        drawdown_neg = calculator._calculate_max_drawdown(negative_returns)
        assert drawdown_neg < 0.0  # Should be negative

    def test_performance_metrics_with_returns_list(self):
        """Test performance metrics when passed raw returns instead of trades."""
        calculator = TradingMetricsCalculator()
        
        # Test with raw returns (list of floats)
        returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        
        perf_metrics = calculator.calculate_performance_metrics(returns, initial_capital=10000.0)
        assert perf_metrics.total_return_pct is not None
        assert perf_metrics.daily_return is not None

    def test_risk_metrics_with_returns_list(self):
        """Test risk metrics when passed raw returns instead of trades."""
        calculator = TradingMetricsCalculator()
        
        # Test with raw returns (list of floats)
        returns = [0.01, -0.02, 0.03, -0.01, 0.015] * 10  # 50 data points
        
        risk_metrics = calculator.calculate_risk_metrics(returns, initial_capital=10000.0)
        assert risk_metrics.volatility > 0
        assert risk_metrics.max_consecutive_losses >= 0

    def test_initialization_with_custom_risk_free_rate(self):
        """Test calculator initialization with custom risk-free rate."""
        custom_rate = 0.05
        calculator = TradingMetricsCalculator(risk_free_rate=custom_rate)
        
        assert calculator.risk_free_rate == custom_rate
        assert calculator._daily_risk_free_rate == custom_rate / 365

    def test_sharpe_ratio_calculation_edge_cases(self):
        """Test Sharpe ratio calculation edge cases."""
        calculator = TradingMetricsCalculator(risk_free_rate=0.02)
        
        # Test with zero volatility (should not calculate Sharpe ratio)
        zero_vol_trades = [{'profit': 100}]  # Single trade, no volatility
        perf_metrics = calculator.calculate_performance_metrics(zero_vol_trades)
        assert perf_metrics.sharpe_ratio == 0.0

    def test_zero_division_edge_cases(self):
        """Test edge cases that could cause zero division errors."""
        calculator = TradingMetricsCalculator()
        
        # Test profit factor with zero gross_loss
        all_winning_trades = [
            {'profit': 100.0, 'amount': 1.0, 'price': 50000.0, 'commission': 5.0},
            {'profit': 50.0, 'amount': 1.0, 'price': 51000.0, 'commission': 5.0}
        ]
        
        trade_metrics = calculator.calculate_trade_metrics(all_winning_trades)
        assert trade_metrics.profit_factor == 0.0  # Should handle zero division
        assert trade_metrics.gross_loss == 0.0

    def test_correlation_statistics_error(self):
        """Test correlation calculation with StatisticsError handling."""
        calculator = TradingMetricsCalculator()
        
        # Create data that would cause StatisticsError (identical values)
        strategy_returns = {
            'strategy1': [0.01, 0.01, 0.01, 0.01],  # All identical values
            'strategy2': [0.02, 0.02, 0.02, 0.02]   # All identical values  
        }
        
        correlation_matrix = calculator.calculate_strategy_correlation(strategy_returns)
        # Should handle StatisticsError and return 0.0
        assert correlation_matrix['strategy1']['strategy2'] == 0.0

    def test_risk_metrics_returns_path(self):
        """Test risk metrics with returns path."""
        calculator = TradingMetricsCalculator()
        
        # Test with list of returns
        returns_list = [0.02, -0.01, 0.03, -0.005, 0.015] * 20
        
        # Call with returns parameter - fix to use correct method signature
        risk_metrics = calculator.calculate_risk_metrics(returns_list)
        
        assert risk_metrics.volatility > 0
        assert risk_metrics.var_95 <= 0
        assert risk_metrics.var_99 <= 0
        
    def test_metrics_missing_lines_coverage(self):
        """Test missing lines in metrics.py to improve coverage."""
        calculator = TradingMetricsCalculator()
        
        # Test edge case for missing lines 251-252 and 360
        # Test with specific data that might trigger those lines
        trades_edge_case = [
            {'profit': 0, 'amount': 1, 'price': 1000, 'commission': 0},
            {'profit': 0, 'amount': 1, 'price': 1000, 'commission': 0}
        ]
        
        # Calculate metrics with edge case data
        trade_metrics = calculator.calculate_trade_metrics(trades_edge_case)
        assert trade_metrics.total_trades == 2
        
        # Test performance metrics with zero returns
        returns_zero = [0.0] * 10
        performance_metrics = calculator.calculate_performance_metrics(returns_zero)
        assert performance_metrics.total_return == 0.0
        
        # Test risk metrics with minimal variance
        risk_metrics = calculator.calculate_risk_metrics(returns_zero)
        assert risk_metrics.volatility >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
