"""Advanced trading metrics calculator for Xline Analytics Engine.

This module provides comprehensive metrics calculations for trading performance,
risk analysis, and portfolio optimization.
"""

import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class TradeMetrics:
    """Basic trade statistics."""
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_volume: float = 0.0
    total_commission: float = 0.0


@dataclass
class PerformanceMetrics:
    """Performance analysis metrics."""
    
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    daily_return: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0
    profit_to_maxdd_ratio: float = 0.0


@dataclass
class RiskMetrics:
    """Risk analysis metrics."""
    
    volatility: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    expected_shortfall: float = 0.0
    max_consecutive_losses: int = 0
    downside_deviation: float = 0.0
    upside_deviation: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0


class TradingMetricsCalculator:
    """Advanced trading metrics calculator.
    
    Calculates comprehensive trading and performance metrics from trade data.
    Supports real-time calculations and historical analysis.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """Initialize metrics calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate for calculations
        """
        self.risk_free_rate = risk_free_rate
        self._daily_risk_free_rate = risk_free_rate / 365
        
        # Cache for performance optimization
        self._cached_metrics: dict[str, Any] = {}
        self._cache_timestamp: datetime | None = None
        self._cache_duration = timedelta(seconds=30)

    def calculate_trade_metrics(self, trades: list[dict[str, Any]]) -> TradeMetrics:
        """Calculate basic trade statistics.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            TradeMetrics object with calculated statistics
        """
        if not trades:
            return TradeMetrics()
        
        metrics = TradeMetrics()
        metrics.total_trades = len(trades)
        
        winning_profits = []
        losing_profits = []
        
        for trade in trades:
            profit = trade.get('profit', 0.0)
            volume = trade.get('amount', 0.0) * trade.get('price', 0.0)
            commission = trade.get('commission', 0.0)
            
            metrics.total_profit += profit
            metrics.total_volume += volume
            metrics.total_commission += commission
            
            if profit > 0:
                metrics.winning_trades += 1
                metrics.gross_profit += profit
                winning_profits.append(profit)
                metrics.largest_win = max(metrics.largest_win, profit)
            elif profit < 0:
                metrics.losing_trades += 1
                metrics.gross_loss += abs(profit)  # Convert to positive for gross_loss
                losing_profits.append(profit)
                metrics.largest_loss = min(metrics.largest_loss, profit)
        
        # Calculate derived metrics
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
        
        if winning_profits:
            metrics.avg_win = statistics.mean(winning_profits)
        
        if losing_profits:
            metrics.avg_loss = statistics.mean(losing_profits)
        
        if metrics.gross_loss > 0:  # gross_loss is now positive
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        
        return metrics

    def calculate_performance_metrics(
        self,
        trades: list[dict[str, Any]] | list[float],
        initial_capital: float = 100000.0
    ) -> PerformanceMetrics:
        """Calculate performance metrics from trade data.
        
        Args:
            trades: List of trade dictionaries or list of returns
            initial_capital: Starting capital amount
            
        Returns:
            PerformanceMetrics object with calculated metrics
        """
        if not trades:
            return PerformanceMetrics()
        
        # Extract returns from trade data or use directly if already returns
        if trades and isinstance(trades[0], dict):
            returns = [trade.get('profit', 0.0) / initial_capital for trade in trades]
        else:
            returns = list(trades)  # Already returns
        
        metrics = PerformanceMetrics()
        
        # Total return
        if isinstance(trades[0], dict):
            total_profit = sum(trade.get('profit', 0.0) for trade in trades)
        else:
            total_profit = sum(returns) * initial_capital
        metrics.total_return = total_profit
        metrics.total_return_pct = total_profit / initial_capital
        
        # Daily return
        if len(returns) > 0:
            metrics.daily_return = statistics.mean(returns)
        
        # Volatility (annualized)
        if len(returns) > 1:
            daily_volatility = statistics.stdev(returns)
            metrics.volatility = daily_volatility * math.sqrt(365)
        
        # Drawdown calculation
        metrics.max_drawdown = self._calculate_max_drawdown(returns)
        
        # Risk-adjusted metrics
        if metrics.volatility > 0:
            annualized_return = metrics.total_return_pct * 365 / len(trades)
            excess_return = annualized_return - self.risk_free_rate
            metrics.sharpe_ratio = excess_return / metrics.volatility
        
        return metrics

    def calculate_risk_metrics(
        self,
        trades: list[dict[str, Any]] | list[float],
        initial_capital: float = 100000.0,
        benchmark_returns: list[float] | None = None
    ) -> RiskMetrics:
        """Calculate risk metrics from trade data.
        
        Args:
            trades: List of trade dictionaries or list of returns
            initial_capital: Starting capital for return calculations
            benchmark_returns: Optional benchmark returns for beta/alpha
            
        Returns:
            RiskMetrics object with calculated risk metrics
        """
        if not trades:
            return RiskMetrics()
        
        # Extract returns from trade data or use directly if already returns
        if trades and isinstance(trades[0], dict):
            returns = [trade.get('profit', 0.0) / initial_capital for trade in trades]
        else:
            returns = list(trades)  # Already returns
        
        metrics = RiskMetrics()
        
        # Value at Risk (VaR)
        if len(returns) >= 5:  # Need some data
            sorted_returns = sorted(returns)
            
            # 95% VaR (5th percentile)
            var_95_index = int(len(sorted_returns) * 0.05)
            if var_95_index < len(sorted_returns):
                metrics.var_95 = sorted_returns[var_95_index]
            
            # Expected Shortfall
            if var_95_index > 0:
                metrics.expected_shortfall = statistics.mean(
                    sorted_returns[:var_95_index + 1]
                )
        
        # Volatility
        if len(returns) > 1:
            metrics.volatility = statistics.stdev(returns) * math.sqrt(365)
        
        # Max consecutive losses
        current_streak = 0
        max_streak = 0
        
        if trades and isinstance(trades[0], dict):
            # Use trade dictionaries
            for trade in trades:
                if trade.get('profit', 0.0) < 0:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0
        else:
            # Use returns directly
            for ret in returns:
                if ret < 0:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0
                    
        metrics.max_consecutive_losses = max_streak
        
        return metrics

    def get_portfolio_metrics(
        self, 
        strategy_data: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Calculate portfolio-level metrics.
        
        Args:
            strategy_data: Dictionary of strategy_id -> trades
            
        Returns:
            Dictionary with portfolio analytics
        """
        if not strategy_data:
            return {}
        
        portfolio_metrics = {
            'total_strategies': len(strategy_data),
            'individual_strategies': {},
            'correlation_matrix': {},
            'total_trades': 0,
            'total_portfolio_return': 0.0,
            'weighted_profit': 0.0,
            'strategies_summary': {}
        }
        
        # Calculate metrics for each strategy
        strategy_profits = {}
        for strategy_id, trades in strategy_data.items():
            strategy_metrics = self.calculate_trade_metrics(trades)
            portfolio_metrics['individual_strategies'][strategy_id] = strategy_metrics
            portfolio_metrics['total_trades'] += strategy_metrics.total_trades
            portfolio_metrics['total_portfolio_return'] += strategy_metrics.total_profit
            
            # Store profits for correlation calculation
            strategy_profits[strategy_id] = [t.get('profit', 0.0) for t in trades]
            
            # Strategy summary
            portfolio_metrics['strategies_summary'][strategy_id] = {
                'net_profit': strategy_metrics.total_profit,
                'total_trades': strategy_metrics.total_trades,
                'win_rate': strategy_metrics.win_rate,
                'profit_factor': strategy_metrics.profit_factor
            }
        
        # Calculate correlation matrix
        portfolio_metrics['correlation_matrix'] = self.calculate_strategy_correlation(
            strategy_profits
        )
        
        # Weighted metrics
        if portfolio_metrics['total_trades'] > 0:
            portfolio_metrics['weighted_profit'] = (
                portfolio_metrics['total_portfolio_return'] / 
                portfolio_metrics['total_trades']
            )
        
        return portfolio_metrics

    def calculate_strategy_correlation(
        self, 
        strategy_returns: dict[str, list[float]]
    ) -> dict[str, dict[str, float]]:
        """Calculate correlation matrix between strategies.
        
        Args:
            strategy_returns: Dictionary of strategy returns
            
        Returns:
            Correlation matrix dictionary
        """
        strategies = list(strategy_returns.keys())
        correlation_matrix = {}
        
        for strategy1 in strategies:
            correlation_matrix[strategy1] = {}
            for strategy2 in strategies:
                if strategy1 == strategy2:
                    correlation_matrix[strategy1][strategy2] = 1.0
                else:
                    returns1 = strategy_returns[strategy1]
                    returns2 = strategy_returns[strategy2]
                    
                    if len(returns1) > 1 and len(returns2) > 1:
                        # Ensure same length for correlation
                        min_len = min(len(returns1), len(returns2))
                        returns1_trimmed = returns1[:min_len]
                        returns2_trimmed = returns2[:min_len]
                        
                        try:
                            correlation = statistics.correlation(
                                returns1_trimmed, returns2_trimmed
                            )
                            correlation_matrix[strategy1][strategy2] = correlation
                        except statistics.StatisticsError:
                            correlation_matrix[strategy1][strategy2] = 0.0
                    else:
                        correlation_matrix[strategy1][strategy2] = 0.0
        
        return correlation_matrix

    def _calculate_max_drawdown(self, returns: list[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0.0
        
        cumulative = 1.0
        peak = 1.0
        max_drawdown = 0.0
        
        for ret in returns:
            cumulative *= (1 + ret)
            if cumulative > peak:
                peak = cumulative
            
            drawdown = (peak - cumulative) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return -max_drawdown  # Return as negative value

    def _is_cache_valid(self) -> bool:
        """Check if cached metrics are still valid."""
        if self._cache_timestamp is None:
            return False
        
        return datetime.now() - self._cache_timestamp < self._cache_duration

    def clear_cache(self) -> None:
        """Clear the metrics cache."""
        self._cached_metrics.clear()
        self._cache_timestamp = None
