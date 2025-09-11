# Freqtrade Integration Guide

## Overview
This guide provides comprehensive instructions for integrating Xline with Freqtrade for advanced crypto trading operations. The integration allows seamless communication between Xline's enterprise-grade event bus architecture and Freqtrade's proven trading framework.

## Architecture Overview

### Component Interaction
```
[Xline Event Bus] <-> [FreqtradeAdapter] <-> [Freqtrade Core]
        |                     |                      |
[Strategy Bridge]    [Trade Execution]      [Exchange APIs]
        |                     |                      |
[Performance Monitor] [Risk Management]   [Market Data]
```

### Key Components

#### FreqtradeAdapter
- **Location**: `xline/core/adapters/freqtrade_adapter.py`
- **Purpose**: Primary interface between Xline and Freqtrade
- **Responsibilities**:
  - Trade execution and order management
  - Account balance synchronization
  - Position tracking and updates
  - Error handling and recovery

#### StrategyBridge
- **Location**: `xline/core/adapters/strategy_bridge.py`
- **Purpose**: Manages strategy lifecycle and deployment
- **Responsibilities**:
  - Strategy deployment and configuration
  - Runtime strategy management
  - Strategy performance monitoring
  - Hot-swapping capabilities

## Installation & Setup

### Prerequisites
```bash
# Ensure Python 3.12+ and virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Xline with Freqtrade dependencies
pip install -e .[freqtrade]
```

### Configuration Files

#### Basic Freqtrade Configuration
Create `user_data/config.json`:
```json
{
    "max_open_trades": 5,
    "stake_currency": "USDT",
    "stake_amount": 100,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "exchange": {
        "name": "binance",
        "key": "your_api_key",
        "secret": "your_api_secret",
        "ccxt_config": {
            "enableRateLimit": true
        }
    },
    "pairlists": [
        {
            "method": "StaticPairList",
            "pairs": ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        }
    ],
    "edge": {
        "enabled": false
    },
    "telegram": {
        "enabled": false
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": false,
        "jwt_secret_key": "your_jwt_secret",
        "CORS_origins": []
    },
    "bot_name": "xline_freqtrade_bot",
    "initial_state": "running",
    "force_entry_enable": true,
    "internals": {
        "process_throttle_secs": 5
    }
}
```

#### Xline Event Bus Configuration
Create `user_data/xline_config.json`:
```json
{
    "event_bus": {
        "type": "memory",
        "max_queue_size": 10000,
        "batch_size": 100,
        "timeout_seconds": 5.0
    },
    "adapters": {
        "freqtrade": {
            "config_path": "user_data/config.json",
            "data_dir": "user_data/data",
            "auto_start": true,
            "heartbeat_interval": 30
        }
    },
    "monitoring": {
        "performance": {
            "enabled": true,
            "metrics_interval": 60,
            "memory_threshold_mb": 1024
        }
    }
}
```

## Integration Examples

### Basic Integration Setup
```python
import asyncio
from xline.core.events.bus import InMemoryEventBus
from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter
from xline.core.adapters.strategy_bridge import StrategyBridge

async def setup_basic_integration():
    """Set up basic Xline-Freqtrade integration."""
    # Initialize event bus
    event_bus = InMemoryEventBus()
    
    # Initialize Freqtrade adapter
    adapter = FreqtradeAdapter(
        event_bus=event_bus,
        config_path="user_data/config.json"
    )
    
    # Initialize strategy bridge
    bridge = StrategyBridge(
        event_bus=event_bus,
        adapter=adapter
    )
    
    # Start components
    await adapter.start()
    await bridge.start()
    
    return event_bus, adapter, bridge

# Usage
async def main():
    event_bus, adapter, bridge = await setup_basic_integration()
    
    # Deploy a strategy
    strategy_config = {
        "name": "RSI_Strategy",
        "class_name": "RSIStrategy",
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70
        }
    }
    
    strategy_id = await bridge.deploy_strategy(strategy_config)
    await bridge.start_strategy(strategy_id)
    
    # Start trading
    await adapter.start_trading("binance_account", "RSI_Strategy")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Event Handling
```python
from xline.core.events.types import OrderEvent, TradeEvent, PriceTickEvent

async def setup_event_handlers(event_bus):
    """Set up advanced event handlers for trading signals."""
    
    @event_bus.subscribe("trade.executed")
    async def handle_trade_executed(event: TradeEvent):
        print(f"Trade executed: {event.symbol} - {event.side} - {event.quantity}")
        
        # Log trade for analysis
        await log_trade_execution(event)
        
        # Update portfolio metrics
        await update_portfolio_metrics(event)
    
    @event_bus.subscribe("order.filled")
    async def handle_order_filled(event: OrderEvent):
        print(f"Order filled: {event.order_id} - {event.status}")
        
        # Notify risk management
        await notify_risk_management(event)
    
    @event_bus.subscribe("price.tick")
    async def handle_price_update(event: PriceTickEvent):
        # Real-time strategy signal generation
        await generate_trading_signals(event)

async def log_trade_execution(event: TradeEvent):
    """Log trade execution for compliance and analysis."""
    trade_log = {
        "timestamp": event.timestamp_ms,
        "symbol": event.symbol,
        "side": event.side,
        "quantity": str(event.quantity),
        "price": str(event.price),
        "value": str(event.value)
    }
    # Save to database or file
    print(f"Trade logged: {trade_log}")

async def update_portfolio_metrics(event: TradeEvent):
    """Update real-time portfolio metrics."""
    # Implementation for portfolio tracking
    pass

async def notify_risk_management(event: OrderEvent):
    """Notify risk management system of order fills."""
    # Implementation for risk checks
    pass

async def generate_trading_signals(event: PriceTickEvent):
    """Generate trading signals based on price updates."""
    # Implementation for signal generation
    pass
```

## Strategy Development

### Creating Custom Strategies
```python
# user_data/strategies/xline_rsi_strategy.py
from typing import Optional
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class XlineRSIStrategy(IStrategy):
    """
    Xline-integrated RSI strategy with event bus communication.
    """
    
    INTERFACE_VERSION = 3
    
    # Strategy parameters
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    # Minimal ROI designed for the strategy
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }
    
    # Optimal stoploss
    stoploss = -0.10
    
    # Optimal timeframe
    timeframe = '5m'
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add RSI indicator to the dataframe."""
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define entry conditions."""
        dataframe.loc[
            (dataframe['rsi'] < self.rsi_oversold),
            'enter_long'
        ] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define exit conditions."""
        dataframe.loc[
            (dataframe['rsi'] > self.rsi_overbought),
            'exit_long'
        ] = 1
        return dataframe
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                          rate: float, time_in_force: str, current_time, 
                          entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """Confirm trade entry with Xline event bus."""
        # Emit entry signal to Xline event bus
        self.emit_xline_event("strategy.entry_signal", {
            "pair": pair,
            "side": side,
            "amount": amount,
            "rate": rate,
            "strategy": self.__class__.__name__
        })
        return True
    
    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                         rate: float, time_in_force: str, exit_reason: str,
                         current_time, **kwargs) -> bool:
        """Confirm trade exit with Xline event bus."""
        # Emit exit signal to Xline event bus
        self.emit_xline_event("strategy.exit_signal", {
            "pair": pair,
            "exit_reason": exit_reason,
            "profit": trade.calc_profit_ratio(rate),
            "strategy": self.__class__.__name__
        })
        return True
    
    def emit_xline_event(self, event_type: str, data: dict):
        """Emit event to Xline event bus."""
        # This would be implemented by the StrategyBridge
        pass
```

### Strategy Deployment via API
```python
async def deploy_strategy_via_api():
    """Deploy strategy using Xline API."""
    import json
    import aiohttp
    
    strategy_config = {
        "name": "XlineRSI_v1",
        "class_name": "XlineRSIStrategy",
        "file_path": "user_data/strategies/xline_rsi_strategy.py",
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "minimal_roi": {
                "60": 0.01,
                "30": 0.02,
                "0": 0.04
            },
            "stoploss": -0.08
        },
        "trading_pairs": ["BTC/USDT", "ETH/USDT"],
        "timeframe": "5m"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8080/api/v1/xline/strategies/deploy",
            json=strategy_config,
            headers={"Authorization": "Bearer your_jwt_token"}
        ) as response:
            result = await response.json()
            strategy_id = result["strategy_id"]
            print(f"Strategy deployed with ID: {strategy_id}")
            return strategy_id
```

## Error Handling & Recovery

### Automatic Recovery Mechanisms
```python
from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter

class RobustFreqtradeAdapter(FreqtradeAdapter):
    """Enhanced Freqtrade adapter with automatic recovery."""
    
    async def handle_connection_error(self, error: Exception):
        """Handle connection errors with automatic retry."""
        self.logger.error(f"Connection error: {error}")
        
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                await self.reconnect()
                self.logger.info("Reconnection successful")
                break
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"Retry {retry_count} failed: {e}")
        
        if retry_count >= max_retries:
            await self.emit_critical_error("Max retries exceeded")
    
    async def handle_order_error(self, order_id: str, error: Exception):
        """Handle order execution errors."""
        self.logger.error(f"Order {order_id} error: {error}")
        
        # Attempt order recovery
        try:
            order_status = await self.get_order_status(order_id)
            if order_status in ["open", "partially_filled"]:
                await self.cancel_order(order_id)
                self.logger.info(f"Cancelled problematic order: {order_id}")
        except Exception as e:
            self.logger.error(f"Order recovery failed: {e}")
```

### Health Monitoring
```python
from xline.core.monitoring.performance import PerformanceMonitor

async def setup_health_monitoring():
    """Set up comprehensive health monitoring."""
    
    monitor = PerformanceMonitor()
    
    # Monitor adapter health
    @monitor.track_performance("adapter.health_check")
    async def check_adapter_health(adapter: FreqtradeAdapter):
        """Check adapter health status."""
        try:
            # Check API connectivity
            api_status = await adapter.check_api_connection()
            
            # Check order book access
            orderbook_status = await adapter.check_orderbook_access()
            
            # Check balance access
            balance_status = await adapter.check_balance_access()
            
            health_score = sum([api_status, orderbook_status, balance_status]) / 3
            
            await monitor.record_metric("adapter.health_score", health_score)
            
            if health_score < 0.8:
                await adapter.handle_degraded_performance()
            
            return health_score
            
        except Exception as e:
            await monitor.record_error("adapter.health_check", str(e))
            return 0.0
    
    # Schedule regular health checks
    async def run_health_monitoring():
        while True:
            health_score = await check_adapter_health(adapter)
            
            if health_score == 0.0:
                await adapter.emergency_shutdown()
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    return run_health_monitoring
```

## Performance Optimization

### Connection Pooling
```python
import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry

class OptimizedFreqtradeClient:
    """Optimized HTTP client for Freqtrade API calls."""
    
    def __init__(self):
        self.session = None
        self.retry_options = ExponentialRetry(
            attempts=3,
            start_timeout=1,
            max_timeout=10
        )
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=20
        )
        
        self.session = RetryClient(
            connector=connector,
            timeout=timeout,
            retry_options=self.retry_options
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
```

### Batch Operations
```python
async def batch_order_operations(adapter: FreqtradeAdapter, orders: list):
    """Execute multiple orders in batches for better performance."""
    
    batch_size = 10
    results = []
    
    for i in range(0, len(orders), batch_size):
        batch = orders[i:i + batch_size]
        
        # Execute batch concurrently
        batch_tasks = [
            adapter.place_order(order) for order in batch
        ]
        
        batch_results = await asyncio.gather(
            *batch_tasks,
            return_exceptions=True
        )
        
        results.extend(batch_results)
        
        # Rate limiting between batches
        await asyncio.sleep(0.1)
    
    return results
```

## Troubleshooting

### Common Issues

#### 1. Connection Timeouts
**Problem**: Frequent connection timeouts to Freqtrade API
**Solution**:
```python
# Increase timeout settings in config
{
    "api_server": {
        "timeout": 30,
        "max_retries": 5
    }
}

# Implement circuit breaker pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
```

#### 2. Memory Leaks in Event Handling
**Problem**: Memory usage increases over time
**Solution**:
```python
# Implement proper event cleanup
class EventBusManager:
    def __init__(self):
        self.event_history = deque(maxlen=10000)  # Limit history size
        self.cleanup_interval = 3600  # 1 hour
    
    async def cleanup_old_events(self):
        """Periodic cleanup of old events."""
        current_time = time.time()
        cutoff_time = current_time - self.cleanup_interval
        
        # Remove old events
        while (self.event_history and 
               self.event_history[0].timestamp < cutoff_time):
            self.event_history.popleft()
```

#### 3. Strategy Synchronization Issues
**Problem**: Strategies getting out of sync with market data
**Solution**:
```python
# Implement strategy synchronization checkpoint
async def sync_strategy_state(bridge: StrategyBridge, strategy_id: str):
    """Synchronize strategy state with current market."""
    
    # Get current market state
    market_state = await bridge.get_market_state()
    
    # Get strategy state
    strategy_state = await bridge.get_strategy_state(strategy_id)
    
    # Check for discrepancies
    if abs(market_state.timestamp - strategy_state.last_update) > 60000:
        # Resync if more than 1 minute out of sync
        await bridge.resync_strategy(strategy_id, market_state)
```

## Testing Integration

### Unit Testing
```bash
# Run Freqtrade adapter tests
pytest tests/adapters/test_freqtrade_adapter.py -v

# Run strategy bridge tests
pytest tests/adapters/test_strategy_bridge.py -v

# Run integration tests
pytest tests/integration/week2/ -v
```

### Integration Testing
```bash
# Run complete pipeline tests
pytest tests/integration/week2/test_complete_pipeline.py::TestCompleteIntegration::test_complete_trading_pipeline -v

# Run stress tests
pytest tests/integration/week2/test_complete_pipeline.py::TestSystemResilience -v
```

### Performance Testing
```bash
# Run performance benchmarks
python scripts/benchmark_freqtrade_integration.py

# Monitor resource usage
python scripts/monitor_integration_performance.py
```

## Security Considerations

### API Key Management
```python
import os
from cryptography.fernet import Fernet

class SecureConfigManager:
    """Secure configuration management for API keys."""
    
    def __init__(self):
        self.key = os.environ.get('XLINE_ENCRYPTION_KEY', self.generate_key())
        self.cipher = Fernet(self.key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for storage."""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use."""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate new encryption key."""
        return Fernet.generate_key()
```

### Rate Limiting
```python
from aiohttp_ratelimiter import RateLimiter

# Configure rate limiting for API calls
rate_limiter = RateLimiter(
    max_requests=100,
    time_window=60,  # 100 requests per minute
    storage="memory"
)

@rate_limiter
async def protected_api_call(adapter: FreqtradeAdapter, endpoint: str):
    """Rate-limited API call."""
    return await adapter.make_api_call(endpoint)
```

## Production Deployment

### Docker Configuration
```dockerfile
# Dockerfile.freqtrade-integration
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-xline.txt .
COPY requirements-freqtrade.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-xline.txt
RUN pip install --no-cache-dir -r requirements-freqtrade.txt

# Copy application
COPY . .

# Install Xline
RUN pip install -e .

# Create user data directory
RUN mkdir -p user_data/strategies user_data/data

# Set environment variables
ENV PYTHONPATH=/app
ENV XLINE_CONFIG_PATH=/app/user_data/xline_config.json

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Start command
CMD ["python", "-m", "xline.main", "start", "--config", "user_data/xline_config.json"]
```

### Monitoring & Logging
```python
import logging
from pythonjsonlogger import jsonlogger

# Configure structured logging
def setup_production_logging():
    """Set up production-grade logging."""
    
    # JSON formatter for structured logs
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for application logs
    file_handler = logging.FileHandler('/var/log/xline/application.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler
    error_handler = logging.FileHandler('/var/log/xline/errors.log')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure Freqtrade logger
    freqtrade_logger = logging.getLogger('freqtrade')
    freqtrade_logger.setLevel(logging.WARNING)
    
    return root_logger
```

## Conclusion

This integration guide provides a comprehensive foundation for connecting Xline with Freqtrade. The event-driven architecture ensures loose coupling between components while maintaining high performance and reliability.

For additional support:
- Check the troubleshooting section for common issues
- Review the performance optimization guidelines
- Consult the API documentation for detailed method signatures
- Use the provided test suites to validate your integration

Remember to always test integrations thoroughly in a paper trading environment before deploying to production.
