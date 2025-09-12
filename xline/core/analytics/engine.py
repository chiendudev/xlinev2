"""Advanced Analytics Engine for Xline Trading System.

This module provides comprehensive real-time analytics and reporting
capabilities for trading performance, risk analysis, and strategy optimization.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from xline.core.analytics.metrics import TradingMetricsCalculator

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsConfig:
    """Configuration for analytics engine."""
    
    enable_real_time: bool = True
    metrics_interval: int = 60  # seconds
    cache_duration: int = 300  # seconds
    max_events_buffer: int = 10000
    risk_free_rate: float = 0.02
    enable_alerts: bool = True
    alert_thresholds: dict[str, float] | None = None


@dataclass
class TradeEvent:
    """Trading event for analytics processing."""
    
    event_id: str
    timestamp: datetime
    strategy_id: str
    symbol: str
    action: str  # 'buy', 'sell', 'close'
    amount: float
    price: float
    profit: float = 0.0
    commission: float = 0.0
    metadata: dict[str, Any] | None = None


@dataclass
class AnalyticsResult:
    """Analytics processing result."""
    
    timestamp: datetime
    strategy_id: str
    metrics: dict[str, Any]
    alerts: list[dict[str, Any]] | None = None
    performance_summary: dict[str, Any] | None = None


class AnalyticsEngine:
    """Advanced analytics engine for trading system."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize analytics engine."""
        self.config = config
        self.metrics_calculator = TradingMetricsCalculator(
            risk_free_rate=config.risk_free_rate
        )
        
        # Event processing - lazy initialization
        self._event_queue: asyncio.Queue[TradeEvent] | None = None
        self._is_running = False
        self._processing_task: asyncio.Task | None = None
        
        # Data storage
        self._trade_history: dict[str, list[dict[str, Any]]] = {}
        self._metrics_cache: dict[str, AnalyticsResult] = {}
        self._last_update: dict[str, datetime] = {}
        
        # Callbacks
        self._result_callbacks: list[Callable[[AnalyticsResult], None]] = []
        self._alert_callbacks: list[Callable[[dict[str, Any]], None]] = []

    def _ensure_event_queue(self) -> None:
        """Ensure event queue is initialized."""
        if self._event_queue is None:
            self._event_queue = asyncio.Queue(maxsize=self.config.max_events_buffer)

    async def start(self) -> None:
        """Start the analytics engine."""
        if self._is_running:
            return
        
        self._ensure_event_queue()
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Analytics engine started")

    async def stop(self) -> None:
        """Stop the analytics engine."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Analytics engine stopped")

    async def process_trade_event(self, event: TradeEvent) -> None:
        """Process a trading event."""
        self._ensure_event_queue()
        try:
            await self._event_queue.put(event)
        except asyncio.QueueFull:
            logger.error("Analytics event queue is full, dropping event")

    def get_strategy_metrics(self, strategy_id: str) -> AnalyticsResult | None:
        """Get latest metrics for a strategy."""
        return self._metrics_cache.get(strategy_id)

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get portfolio-level summary."""
        if not self._trade_history:
            return {}
        
        # Calculate portfolio metrics
        portfolio_metrics = self.metrics_calculator.get_portfolio_metrics(
            self._trade_history
        )
        
        # Add timing information
        portfolio_metrics['last_updated'] = datetime.now()
        portfolio_metrics['strategies_count'] = len(self._trade_history)
        
        return portfolio_metrics

    async def _process_events(self) -> None:
        """Main event processing loop."""
        while self._is_running:
            try:
                # Process events with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=1.0
                )
                
                await self._handle_trade_event(event)
                
            except TimeoutError:
                # Check for periodic updates
                pass
                
            except Exception as e:
                logger.error(f"Error processing analytics event: {e}")

    async def _handle_trade_event(self, event: TradeEvent) -> None:
        """Handle individual trade event."""
        try:
            # Store trade data
            trade_data = {
                'timestamp': event.timestamp,
                'symbol': event.symbol,
                'action': event.action,
                'amount': event.amount,
                'price': event.price,
                'profit': event.profit,
                'commission': event.commission
            }
            
            if event.strategy_id not in self._trade_history:
                self._trade_history[event.strategy_id] = []
            
            self._trade_history[event.strategy_id].append(trade_data)
            
            # Calculate metrics if enough data
            if len(self._trade_history[event.strategy_id]) >= 2:
                await self._calculate_and_cache_metrics(event.strategy_id)
                
        except Exception as e:
            logger.error(f"Error handling trade event: {e}")

    async def _calculate_and_cache_metrics(self, strategy_id: str) -> None:
        """Calculate and cache metrics for a strategy."""
        try:
            trades = self._trade_history[strategy_id]
            
            # Calculate metrics
            trade_metrics = self.metrics_calculator.calculate_trade_metrics(trades)
            performance_metrics = self.metrics_calculator.calculate_performance_metrics(trades)
            risk_metrics = self.metrics_calculator.calculate_risk_metrics(trades)
            
            # Create analytics result
            result = AnalyticsResult(
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                metrics={
                    'trade_metrics': trade_metrics.__dict__,
                    'performance_metrics': performance_metrics.__dict__,
                    'risk_metrics': risk_metrics.__dict__
                },
                alerts=self._generate_alerts(trade_metrics, performance_metrics, risk_metrics),
                performance_summary=self._create_performance_summary(
                    trade_metrics, performance_metrics, risk_metrics
                )
            )
            
            # Cache result
            self._metrics_cache[strategy_id] = result
            self._last_update[strategy_id] = datetime.now()
            
            # Trigger callbacks
            for callback in self._result_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in result callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error calculating metrics for {strategy_id}: {e}")

    def _generate_alerts(
        self, 
        trade_metrics, 
        performance_metrics, 
        risk_metrics
    ) -> list[dict[str, Any]]:
        """Generate alerts based on thresholds."""
        alerts = []
        
        if not self.config.enable_alerts or not self.config.alert_thresholds:
            return alerts
        
        thresholds = self.config.alert_thresholds
        
        # Win rate alert
        if 'min_win_rate' in thresholds:
            if trade_metrics.win_rate < thresholds['min_win_rate']:
                alerts.append({
                    'type': 'win_rate_alert',
                    'severity': 'warning',
                    'message': f'Win rate {trade_metrics.win_rate:.2%} below threshold {thresholds["min_win_rate"]:.2%}',
                    'timestamp': datetime.now()
                })
        
        # Max drawdown alert
        if 'max_drawdown' in thresholds:
            if performance_metrics.max_drawdown < thresholds['max_drawdown']:
                alerts.append({
                    'type': 'drawdown_alert',
                    'severity': 'critical',
                    'message': f'Max drawdown {performance_metrics.max_drawdown:.2%} exceeds threshold {thresholds["max_drawdown"]:.2%}',
                    'timestamp': datetime.now()
                })
        
        return alerts

    def _create_performance_summary(
        self, 
        trade_metrics, 
        performance_metrics, 
        risk_metrics
    ) -> dict[str, Any]:
        """Create performance summary."""
        return {
            'total_trades': trade_metrics.total_trades,
            'win_rate': trade_metrics.win_rate,
            'total_return': performance_metrics.total_return,
            'sharpe_ratio': performance_metrics.sharpe_ratio,
            'max_drawdown': performance_metrics.max_drawdown,
            'profit_factor': trade_metrics.profit_factor,
            'avg_win': trade_metrics.avg_win,
            'avg_loss': trade_metrics.avg_loss,
            'volatility': risk_metrics.volatility,
            'var_95': risk_metrics.var_95
        }

    def add_result_callback(self, callback: Callable[[AnalyticsResult], None]) -> None:
        """Add callback for analytics results."""
        self._result_callbacks.append(callback)

    def add_alert_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Add callback for alerts."""
        self._alert_callbacks.append(callback)

    def _generate_alert(self, alert_data: dict[str, Any]) -> None:
        """Generate and send alert to all registered callbacks."""
        for callback in self._alert_callbacks:
            callback(alert_data)
