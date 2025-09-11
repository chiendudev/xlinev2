# 🚀 XLINE WEEK 2 - COMPLETE AI AGENT IMPLEMENTATION GUIDE

**Implementation Period:** September 10-16, 2025  
**Target:** 100% Successful AI Agent Implementation  
**Focus:** Freqtrade Integration & Adapter Layer  
**Base Directory:** `/Users/chiendu/XlineV2`

**🎯 MỤC TIÊU:** Document hoàn chỉnh để copy-paste cho AI Agent implement Week 2 thành công 100%

---

## 🔴 **MANDATORY COMPLIANCE RULES** (Apply to ALL tasks)

**CRITICAL: AI Agent MUST follow these rules throughout Week 2:**

### **1. Code Quality Gates**
- ALL code MUST have type hints (100% coverage): `from typing import Dict, List, Optional, Any, Union`
- ALL public methods MUST have docstrings with examples
- Unit test coverage MUST be > 95% before commit
- Pass mypy, flake8, black formatting checks
- Use async/await patterns consistently

### **2. Architecture Constraints**
- NO direct imports between enterprise/* and freqtrade/* modules
- ALL communication via event bus or adapter layer
- NO blocking synchronous calls between services
- ALL database operations MUST be async
- Use existing event system: `xline.core.events.bus.InMemoryEventBus`

### **3. Security Requirements**
- NO hardcoded secrets or API keys
- ALL user inputs MUST be validated with Pydantic
- ALL database queries MUST use parameterized statements
- ALL API endpoints MUST have authentication

### **4. Integration Requirements**
- ALL Freqtrade integration MUST go through `core/adapters/`
- ALL external API calls MUST have circuit breakers
- ALL events MUST be published to message bus
- NO direct database access from business logic

### **5. Week 1 Dependencies (MUST USE)**
- Event system: `xline.core.events.bus.InMemoryEventBus`
- Event types: `xline.core.events.types` (Event, OrderEvent, TradeEvent, etc.)
- Validation: `xline.core.events.validation.EventValidator`
- Follow async patterns established in Week 1

---

## 📅 **DAY 1 PROMPT (Sept 10) - COVERAGE COMPLETION**

```
TASK: Complete Week 1 test coverage gaps và achieve 95%+ coverage

CONTEXT: 
- Current coverage: 94% (814 statements, 46 missing lines)
- Base directory: /Users/chiendu/XlineV2
- Must maintain 100% test pass rate

MANDATORY COMPLIANCE: Follow ALL rules above

EXACT REQUIREMENTS:
1. Fix these specific missing lines:
   - xline/core/events/bus.py: Line 168 (connection recovery edge case)
   - xline/core/events/types.py: Lines 125, 271, 615 (validation edge cases)
   - xline/core/events/validation.py: Lines 398-399, 441, 451, 466, 473, 491, 507, 530, 543-548
   - xline/core/events/versioning.py: Lines 52, 170, 254, 345-346, 383-385, 391-395, 403-407
   - xline/core/events/factory.py: Lines 61, 68-73, 97-102

2. Implementation steps:
   a) Read each file to understand untested code paths
   b) Create specific test cases for each missing line
   c) Add error injection tests for exception handling
   d) Implement boundary condition tests
   e) Add stress testing for concurrent operations

3. Create these new test files:
   - tests/integration/events/test_stress_scenarios.py
   - tests/unit/events/test_edge_cases.py

4. Test requirements:
   - Use pytest-asyncio for all async tests
   - Add memory leak detection with tracemalloc
   - Include latency assertions (<1ms for single events)
   - Test 1000+ events/second throughput
   - Proper fixture cleanup in teardown

5. Example test structure:
   ```python
   import pytest
   import asyncio
   import tracemalloc
   from typing import Dict, Any
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.events.types import Event, EventType
   
   @pytest.mark.asyncio
   async def test_connection_recovery_edge_case():
       """Test line 168 in bus.py - connection recovery"""
       bus = InMemoryEventBus()
       # Simulate connection failure and recovery
       # Add specific test logic for line 168
       
   @pytest.mark.asyncio  
   async def test_stress_high_volume():
       """Stress test: 1000+ events/second"""
       bus = InMemoryEventBus()
       tracemalloc.start()
       # Test high volume event processing
       # Verify memory doesn't grow
       # Assert latency < 1ms
   ```

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest --cov=xline.core.events --cov-report=html tests/
pytest tests/integration/events/test_stress_scenarios.py -v
pytest tests/unit/events/test_edge_cases.py -v
```

SUCCESS CRITERIA:
- Coverage 94% → 95%+
- All performance targets met
- 100% tests passing
- Memory usage stable under stress
```

---

## 📅 **DAY 2 PROMPT (Sept 11) - FREQTRADE ADAPTER**

```
TASK: Implement FreqtradeAdapter for bridging Freqtrade with Xline event system

CONTEXT:
- Week 1 event system complete with 95%+ coverage
- Base directory: /Users/chiendu/XlineV2
- Need seamless integration with Freqtrade trading engine

MANDATORY COMPLIANCE: Follow ALL rules above + adapter pattern constraints

EXACT REQUIREMENTS:
1. Create file: xline/core/adapters/freqtrade_adapter.py

2. Complete implementation:
   ```python
   from typing import Dict, Any, Optional, List
   from decimal import Decimal
   import asyncio
   import logging
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.events.types import Event, OrderEvent, EventType
   from freqtrade.freqtradebot import FreqtradeBot
   
   logger = logging.getLogger(__name__)
   
   class FreqtradeAdapter:
       """
       Adapter layer bridging Freqtrade trading engine with Xline event system.
       
       Example usage:
           adapter = FreqtradeAdapter(event_bus, config)
           await adapter.setup_event_handlers()
           success = await adapter.start_trading("account_1", "RSIStrategy")
       """
       
       def __init__(self, event_bus: InMemoryEventBus, config: Dict[str, Any]) -> None:
           """Initialize adapter with event bus and configuration."""
           self.event_bus = event_bus
           self.config = config
           self.freqtrade_bot: Optional[FreqtradeBot] = None
           self.active_sessions: Dict[str, Dict[str, Any]] = {}
           self._is_setup = False
           
       async def setup_event_handlers(self) -> None:
           """Setup event subscriptions for risk management."""
           # Subscribe to RISK_LIMIT_BREACHED events
           await self.event_bus.subscribe(
               EventType.RISK_LIMIT_BREACHED, 
               self._handle_risk_event
           )
           self._setup_freqtrade_hooks()
           self._is_setup = True
           logger.info("FreqtradeAdapter event handlers setup complete")
           
       async def start_trading(self, account_id: str, strategy_name: str) -> bool:
           """
           Start trading for specific account with validation.
           
           Args:
               account_id: Unique identifier for trading account
               strategy_name: Name of strategy to deploy
               
           Returns:
               bool: True if trading started successfully
           """
           try:
               # Validate inputs
               if not account_id or not strategy_name:
                   raise ValueError("account_id and strategy_name required")
                   
               # Initialize FreqtradeBot if needed
               if not self.freqtrade_bot:
                   self.freqtrade_bot = FreqtradeBot(self.config)
                   
               # Start trading session
               session_id = f"{account_id}_{strategy_name}"
               self.active_sessions[session_id] = {
                   "account_id": account_id,
                   "strategy_name": strategy_name,
                   "start_time": asyncio.get_event_loop().time(),
                   "status": "active"
               }
               
               # Publish strategy started event
               await self._publish_strategy_event(
                   "STRATEGY_STARTED", account_id, strategy_name
               )
               
               logger.info(f"Trading started for {account_id} with {strategy_name}")
               return True
               
           except Exception as e:
               logger.error(f"Failed to start trading: {e}")
               return False
               
       async def stop_trading(self, account_id: str) -> bool:
           """Stop trading for account with cleanup."""
           try:
               # Find and stop sessions for this account
               sessions_to_stop = [
                   sid for sid, session in self.active_sessions.items()
                   if session["account_id"] == account_id
               ]
               
               for session_id in sessions_to_stop:
                   session = self.active_sessions[session_id]
                   session["status"] = "stopped"
                   
                   await self._publish_strategy_event(
                       "STRATEGY_STOPPED", 
                       session["account_id"], 
                       session["strategy_name"]
                   )
                   
               logger.info(f"Trading stopped for account {account_id}")
               return True
               
           except Exception as e:
               logger.error(f"Failed to stop trading: {e}")
               return False
               
       async def emergency_stop(self) -> None:
           """Emergency stop with immediate cleanup."""
           try:
               # Stop all active sessions immediately
               for session_id, session in self.active_sessions.items():
                   session["status"] = "emergency_stopped"
                   
               # Publish emergency stop event
               emergency_event = Event(
                   event_type=EventType.EMERGENCY_STOP,
                   data={"reason": "emergency_stop_triggered", "timestamp": asyncio.get_event_loop().time()},
                   source="freqtrade_adapter"
               )
               await self.event_bus.publish(emergency_event)
               
               logger.critical("Emergency stop executed")
               
           except Exception as e:
               logger.critical(f"Emergency stop failed: {e}")
               
       def _setup_freqtrade_hooks(self) -> None:
           """Setup hooks into Freqtrade execution methods."""
           if not self.freqtrade_bot:
               return
               
           # Hook into order execution methods
           original_execute_entry = self.freqtrade_bot.execute_entry
           original_execute_exit = self.freqtrade_bot.execute_exit
           
           async def hooked_execute_entry(*args, **kwargs):
               result = await original_execute_entry(*args, **kwargs)
               if result:
                   await self._publish_order_event(result, "BUY")
               return result
               
           async def hooked_execute_exit(*args, **kwargs):
               result = await original_execute_exit(*args, **kwargs)
               if result:
                   await self._publish_order_event(result, "SELL")
               return result
               
           self.freqtrade_bot.execute_entry = hooked_execute_entry
           self.freqtrade_bot.execute_exit = hooked_execute_exit
           
       async def _publish_order_event(self, order_data: Dict[str, Any], order_side: str) -> None:
           """Publish order event to event bus."""
           try:
               order_event = OrderEvent(
                   order_id=order_data.get("id", ""),
                   symbol=order_data.get("symbol", ""),
                   side=order_side,
                   amount=Decimal(str(order_data.get("amount", 0))),
                   price=Decimal(str(order_data.get("price", 0))),
                   status=order_data.get("status", ""),
                   source="freqtrade_adapter"
               )
               await self.event_bus.publish(order_event)
               
           except Exception as e:
               logger.error(f"Failed to publish order event: {e}")
               
       async def _handle_risk_event(self, event: Event) -> None:
           """Handle risk management events."""
           try:
               if event.event_type == EventType.RISK_LIMIT_BREACHED:
                   # Immediate emergency stop on risk breach
                   await self.emergency_stop()
                   logger.warning(f"Risk event triggered emergency stop: {event.data}")
                   
           except Exception as e:
               logger.error(f"Failed to handle risk event: {e}")
               
       async def _publish_strategy_event(self, event_type: str, account_id: str, strategy_name: str) -> None:
           """Publish strategy lifecycle events."""
           strategy_event = Event(
               event_type=getattr(EventType, event_type),
               data={
                   "account_id": account_id,
                   "strategy_name": strategy_name,
                   "timestamp": asyncio.get_event_loop().time()
               },
               source="freqtrade_adapter"
           )
           await self.event_bus.publish(strategy_event)
   ```

3. Create integration test: tests/integration/adapters/test_freqtrade_adapter.py
   ```python
   import pytest
   import asyncio
   from unittest.mock import Mock, AsyncMock, patch
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter
   
   @pytest.fixture
   async def adapter_setup():
       event_bus = InMemoryEventBus()
       config = {"test": True}
       adapter = FreqtradeAdapter(event_bus, config)
       return event_bus, adapter
   
   @pytest.mark.asyncio
   async def test_freqtrade_adapter_initialization(adapter_setup):
       """Test adapter initialization and setup."""
       event_bus, adapter = adapter_setup
       await adapter.setup_event_handlers()
       assert adapter._is_setup
       
   @pytest.mark.asyncio
   async def test_start_trading_success(adapter_setup):
       """Test successful trading start."""
       event_bus, adapter = adapter_setup
       await adapter.setup_event_handlers()
       
       with patch('xline.core.adapters.freqtrade_adapter.FreqtradeBot'):
           result = await adapter.start_trading("test_account", "RSIStrategy")
           assert result is True
           assert len(adapter.active_sessions) == 1
           
   @pytest.mark.asyncio
   async def test_emergency_stop(adapter_setup):
       """Test emergency stop functionality."""
       event_bus, adapter = adapter_setup
       await adapter.setup_event_handlers()
       
       # Start a session first
       with patch('xline.core.adapters.freqtrade_adapter.FreqtradeBot'):
           await adapter.start_trading("test_account", "RSIStrategy")
           
       # Trigger emergency stop
       await adapter.emergency_stop()
       
       # Verify all sessions stopped
       for session in adapter.active_sessions.values():
           assert session["status"] == "emergency_stopped"
   ```

4. Performance requirements:
   - Event publishing latency < 1ms
   - Support 100+ concurrent trading sessions
   - Memory usage < 100MB for adapter layer
   - 95%+ test coverage

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/integration/adapters/test_freqtrade_adapter.py -v
pytest --cov=xline.core.adapters.freqtrade_adapter tests/
python -c "from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter; print('Import success')"
```

SUCCESS CRITERIA:
- FreqtradeAdapter class fully operational
- Event publishing from Freqtrade hooks working
- Risk event handling validated
- Emergency stop functionality verified
- 95%+ test coverage for adapter module
```

---

## 📅 **DAY 3 PROMPT (Sept 12) - EVENT MAPPER & STRATEGY BRIDGE**

```
TASK: Implement EventMapper và StrategyBridge for complete data translation and strategy management

CONTEXT:
- FreqtradeAdapter operational from Day 2
- Base directory: /Users/chiendu/XlineV2
- Need bidirectional data mapping and dynamic strategy deployment

MANDATORY COMPLIANCE: Follow ALL rules + maintain decimal precision for financial data

EXACT REQUIREMENTS:
1. Create file: xline/core/adapters/event_mapper.py
   ```python
   from typing import Dict, Any, Optional
   from decimal import Decimal, ROUND_HALF_UP
   import logging
   from xline.core.events.types import Event, OrderEvent, TradeEvent, EventType
   
   logger = logging.getLogger(__name__)
   
   class EventMapper:
       """
       Bidirectional translation between Freqtrade and Xline event formats.
       
       Example usage:
           order_event = EventMapper.map_freqtrade_order(ft_order_dict)
           ft_dict = EventMapper.map_order_event(order_event)
       """
       
       @staticmethod
       def map_freqtrade_order(ft_order: Dict[str, Any]) -> OrderEvent:
           """Convert Freqtrade order to Xline OrderEvent."""
           try:
               return OrderEvent(
                   order_id=str(ft_order.get("id", "")),
                   symbol=str(ft_order.get("symbol", "")),
                   side=str(ft_order.get("side", "")).upper(),
                   amount=EventMapper.validate_decimal_precision(ft_order.get("amount", 0)),
                   price=EventMapper.validate_decimal_precision(ft_order.get("price", 0)),
                   status=str(ft_order.get("status", "")),
                   timestamp=ft_order.get("timestamp", 0),
                   source="freqtrade"
               )
           except Exception as e:
               logger.error(f"Failed to map Freqtrade order: {e}")
               raise ValueError(f"Invalid Freqtrade order data: {e}")
               
       @staticmethod
       def map_freqtrade_trade(ft_trade: Dict[str, Any]) -> TradeEvent:
           """Convert Freqtrade trade to Xline TradeEvent."""
           try:
               return TradeEvent(
                   trade_id=str(ft_trade.get("id", "")),
                   order_id=str(ft_trade.get("order_id", "")),
                   symbol=str(ft_trade.get("symbol", "")),
                   side=str(ft_trade.get("side", "")).upper(),
                   amount=EventMapper.validate_decimal_precision(ft_trade.get("amount", 0)),
                   price=EventMapper.validate_decimal_precision(ft_trade.get("price", 0)),
                   fee=EventMapper.validate_decimal_precision(ft_trade.get("fee", 0)),
                   timestamp=ft_trade.get("timestamp", 0),
                   source="freqtrade"
               )
           except Exception as e:
               logger.error(f"Failed to map Freqtrade trade: {e}")
               raise ValueError(f"Invalid Freqtrade trade data: {e}")
               
       @staticmethod
       def map_order_event(order_event: OrderEvent) -> Dict[str, Any]:
           """Convert Xline OrderEvent to Freqtrade format."""
           try:
               return {
                   "id": order_event.order_id,
                   "symbol": order_event.symbol,
                   "side": order_event.side.lower(),
                   "amount": float(order_event.amount),
                   "price": float(order_event.price),
                   "status": order_event.status,
                   "timestamp": order_event.timestamp
               }
           except Exception as e:
               logger.error(f"Failed to map order event: {e}")
               raise ValueError(f"Invalid OrderEvent data: {e}")
               
       @staticmethod
       def validate_decimal_precision(value: Any, precision: int = 8) -> Decimal:
           """Validate and convert to Decimal with specified precision."""
           try:
               if value is None:
                   return Decimal("0")
                   
               decimal_value = Decimal(str(value))
               quantized = decimal_value.quantize(
                   Decimal(10) ** -precision,
                   rounding=ROUND_HALF_UP
               )
               return quantized
               
           except Exception as e:
               logger.error(f"Failed to validate decimal precision: {e}")
               raise ValueError(f"Invalid decimal value: {value}")
   ```

2. Create file: xline/core/adapters/strategy_bridge.py
   ```python
   from typing import Dict, Any, List, Optional
   import asyncio
   import logging
   import uuid
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.events.types import Event, EventType
   
   logger = logging.getLogger(__name__)
   
   class StrategyBridge:
       """
       Dynamic strategy deployment and lifecycle management.
       
       Example usage:
           bridge = StrategyBridge(event_bus)
           strategy_id = await bridge.deploy_strategy(strategy_config)
           await bridge.start_strategy(strategy_id)
       """
       
       def __init__(self, event_bus: InMemoryEventBus) -> None:
           """Initialize strategy bridge with event bus."""
           self.event_bus = event_bus
           self.deployed_strategies: Dict[str, Dict[str, Any]] = {}
           self.active_strategies: Dict[str, bool] = {}
           
       async def deploy_strategy(self, strategy_config: Dict[str, Any]) -> str:
           """
           Deploy new strategy with configuration validation.
           
           Args:
               strategy_config: Strategy configuration dictionary
               
           Returns:
               str: Unique strategy ID
           """
           try:
               # Validate required fields
               required_fields = ["name", "class_name", "parameters"]
               for field in required_fields:
                   if field not in strategy_config:
                       raise ValueError(f"Missing required field: {field}")
                       
               strategy_id = str(uuid.uuid4())
               
               self.deployed_strategies[strategy_id] = {
                   "id": strategy_id,
                   "config": strategy_config,
                   "deploy_time": asyncio.get_event_loop().time(),
                   "status": "deployed"
               }
               
               # Publish deployment event
               deploy_event = Event(
                   event_type=EventType.STRATEGY_DEPLOYED,
                   data={
                       "strategy_id": strategy_id,
                       "strategy_name": strategy_config["name"],
                       "timestamp": asyncio.get_event_loop().time()
                   },
                   source="strategy_bridge"
               )
               await self.event_bus.publish(deploy_event)
               
               logger.info(f"Strategy deployed: {strategy_id}")
               return strategy_id
               
           except Exception as e:
               logger.error(f"Failed to deploy strategy: {e}")
               raise
               
       async def start_strategy(self, strategy_id: str) -> bool:
           """Start deployed strategy."""
           try:
               if strategy_id not in self.deployed_strategies:
                   raise ValueError(f"Strategy not found: {strategy_id}")
                   
               if self.active_strategies.get(strategy_id, False):
                   logger.warning(f"Strategy already active: {strategy_id}")
                   return True
                   
               self.active_strategies[strategy_id] = True
               self.deployed_strategies[strategy_id]["status"] = "active"
               
               # Publish start event
               start_event = Event(
                   event_type=EventType.STRATEGY_STARTED,
                   data={
                       "strategy_id": strategy_id,
                       "timestamp": asyncio.get_event_loop().time()
                   },
                   source="strategy_bridge"
               )
               await self.event_bus.publish(start_event)
               
               logger.info(f"Strategy started: {strategy_id}")
               return True
               
           except Exception as e:
               logger.error(f"Failed to start strategy: {e}")
               return False
               
       async def stop_strategy(self, strategy_id: str) -> bool:
           """Stop active strategy."""
           try:
               if strategy_id not in self.deployed_strategies:
                   raise ValueError(f"Strategy not found: {strategy_id}")
                   
               self.active_strategies[strategy_id] = False
               self.deployed_strategies[strategy_id]["status"] = "stopped"
               
               # Publish stop event
               stop_event = Event(
                   event_type=EventType.STRATEGY_STOPPED,
                   data={
                       "strategy_id": strategy_id,
                       "timestamp": asyncio.get_event_loop().time()
                   },
                   source="strategy_bridge"
               )
               await self.event_bus.publish(stop_event)
               
               logger.info(f"Strategy stopped: {strategy_id}")
               return True
               
           except Exception as e:
               logger.error(f"Failed to stop strategy: {e}")
               return False
               
       async def list_strategies(self) -> List[Dict[str, Any]]:
           """List all deployed strategies."""
           return list(self.deployed_strategies.values())
           
       async def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
           """Get detailed strategy status."""
           if strategy_id not in self.deployed_strategies:
               raise ValueError(f"Strategy not found: {strategy_id}")
               
           strategy = self.deployed_strategies[strategy_id]
           return {
               "id": strategy_id,
               "status": strategy["status"],
               "active": self.active_strategies.get(strategy_id, False),
               "config": strategy["config"],
               "deploy_time": strategy["deploy_time"]
           }
   ```

3. Create tests:
   a) tests/unit/adapters/test_event_mapper.py
   b) tests/integration/adapters/test_strategy_bridge.py

4. Testing requirements:
   - Test bidirectional mapping accuracy
   - Test decimal precision handling
   - Test field validation and error cases
   - Test strategy lifecycle management
   - Test concurrent strategy operations
   - 95%+ test coverage for both modules

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/unit/adapters/test_event_mapper.py -v
pytest tests/integration/adapters/test_strategy_bridge.py -v
pytest --cov=xline.core.adapters tests/
```

SUCCESS CRITERIA:
- EventMapper bidirectional translation working
- Decimal precision handling validated
- StrategyBridge dynamic deployment operational
- Strategy lifecycle management functional
- 95%+ test coverage for both modules
```

---

## 📅 **DAY 4 PROMPT (Sept 13) - MARKET DATA PIPELINE**

```
TASK: Implement real-time market data processing pipeline

CONTEXT:
- Adapter layer complete from Days 2-3
- Base directory: /Users/chiendu/XlineV2
- Need high-performance market data processing

MANDATORY COMPLIANCE: Follow ALL rules + achieve 1000+ ticks/second throughput

EXACT REQUIREMENTS:
1. Create market data module structure:
   - xline/core/market_data/__init__.py
   - xline/core/market_data/types.py
   - xline/core/market_data/feed.py
   - xline/core/market_data/processor.py

2. Implement types.py:
   ```python
   from typing import Dict, Any, Optional
   from decimal import Decimal
   from dataclasses import dataclass
   from xline.core.events.types import Event, EventType
   
   @dataclass
   class PriceTickEvent(Event):
       """Real-time price tick event."""
       symbol: str
       bid: Decimal
       ask: Decimal
       volume: Decimal
       timestamp: float
       source: str = "market_data"
       
       def __post_init__(self):
           self.event_type = EventType.PRICE_TICK
   
   @dataclass
   class MarketDepthEvent(Event):
       """Market depth/order book event."""
       symbol: str
       bids: Dict[str, Decimal]  # price -> volume
       asks: Dict[str, Decimal]  # price -> volume
       timestamp: float
       source: str = "market_data"
       
       def __post_init__(self):
           self.event_type = EventType.MARKET_DEPTH
   ```

3. Implement high-performance feed.py:
   ```python
   import asyncio
   import logging
   from typing import Dict, Any, List, Optional, Callable
   from decimal import Decimal
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.market_data.types import PriceTickEvent, MarketDepthEvent
   
   logger = logging.getLogger(__name__)
   
   class MarketDataFeed:
       """High-performance real-time market data feed."""
       
       def __init__(self, event_bus: InMemoryEventBus, config: Dict[str, Any]) -> None:
           self.event_bus = event_bus
           self.config = config
           self.subscribed_symbols: set = set()
           self.is_running = False
           self.tick_count = 0
           self.start_time = 0
           
       async def start(self) -> None:
           """Start market data feed."""
           self.is_running = True
           self.start_time = asyncio.get_event_loop().time()
           asyncio.create_task(self._market_data_loop())
           logger.info("Market data feed started")
           
       async def stop(self) -> None:
           """Stop market data feed."""
           self.is_running = False
           logger.info("Market data feed stopped")
           
       async def subscribe_symbol(self, symbol: str) -> None:
           """Subscribe to symbol for market data."""
           self.subscribed_symbols.add(symbol)
           logger.info(f"Subscribed to {symbol}")
           
       async def unsubscribe_symbol(self, symbol: str) -> None:
           """Unsubscribe from symbol."""
           self.subscribed_symbols.discard(symbol)
           logger.info(f"Unsubscribed from {symbol}")
           
       async def _market_data_loop(self) -> None:
           """Main market data processing loop."""
           while self.is_running:
               try:
                   # Process each subscribed symbol
                   tasks = [
                       self._process_symbol_data(symbol) 
                       for symbol in self.subscribed_symbols
                   ]
                   
                   if tasks:
                       await asyncio.gather(*tasks, return_exceptions=True)
                   
                   # Control throughput (target: 1000+ ticks/second)
                   await asyncio.sleep(0.001)  # 1ms interval
                   
               except Exception as e:
                   logger.error(f"Market data loop error: {e}")
                   
       async def _process_symbol_data(self, symbol: str) -> None:
           """Process market data for specific symbol."""
           try:
               # Simulate real market data (replace with actual data source)
               tick_event = PriceTickEvent(
                   symbol=symbol,
                   bid=Decimal("100.50"),
                   ask=Decimal("100.55"),
                   volume=Decimal("1000"),
                   timestamp=asyncio.get_event_loop().time()
               )
               
               await self.event_bus.publish(tick_event)
               self.tick_count += 1
               
           except Exception as e:
               logger.error(f"Failed to process {symbol}: {e}")
               
       def get_performance_stats(self) -> Dict[str, Any]:
           """Get feed performance statistics."""
           elapsed = asyncio.get_event_loop().time() - self.start_time
           ticks_per_second = self.tick_count / elapsed if elapsed > 0 else 0
           
           return {
               "ticks_processed": self.tick_count,
               "elapsed_seconds": elapsed,
               "ticks_per_second": ticks_per_second,
               "subscribed_symbols": len(self.subscribed_symbols)
           }
   ```

4. Implement processor.py:
   ```python
   import asyncio
   from typing import Dict, Any, List
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.events.types import EventType
   from xline.core.market_data.types import PriceTickEvent
   
   class MarketDataProcessor:
       """Process and analyze market data events."""
       
       def __init__(self, event_bus: InMemoryEventBus) -> None:
           self.event_bus = event_bus
           self.price_cache: Dict[str, PriceTickEvent] = {}
           self.processing_stats = {"events_processed": 0, "avg_latency": 0}
           
       async def start(self) -> None:
           """Start processing market data."""
           await self.event_bus.subscribe(EventType.PRICE_TICK, self._process_tick)
           
       async def _process_tick(self, event: PriceTickEvent) -> None:
           """Process price tick with latency tracking."""
           start_time = asyncio.get_event_loop().time()
           
           # Update price cache
           self.price_cache[event.symbol] = event
           
           # Calculate processing latency
           latency = asyncio.get_event_loop().time() - start_time
           self.processing_stats["events_processed"] += 1
           
           # Update average latency
           prev_avg = self.processing_stats["avg_latency"]
           count = self.processing_stats["events_processed"]
           self.processing_stats["avg_latency"] = (prev_avg * (count - 1) + latency) / count
   ```

5. Performance testing (tests/performance/test_market_data_throughput.py):
   ```python
   import pytest
   import asyncio
   import time
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.market_data.feed import MarketDataFeed
   
   @pytest.mark.asyncio
   async def test_throughput_target():
       """Test 1000+ ticks/second throughput."""
       event_bus = InMemoryEventBus()
       feed = MarketDataFeed(event_bus, {})
       
       await feed.start()
       await feed.subscribe_symbol("BTCUSD")
       
       # Run for 5 seconds
       await asyncio.sleep(5)
       
       stats = feed.get_performance_stats()
       await feed.stop()
       
       # Assert throughput target
       assert stats["ticks_per_second"] >= 1000
       
   @pytest.mark.asyncio
   async def test_latency_target():
       """Test <5ms tick-to-event latency."""
       # Implementation for latency testing
       pass
   ```

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/integration/market_data/ -v
pytest tests/performance/test_market_data_throughput.py
pytest --cov=xline.core.market_data tests/
```

SUCCESS CRITERIA:
- Real-time market data feed operational
- 1000+ ticks/second throughput achieved
- <5ms tick-to-event latency validated
- Integration with event system verified
- Performance targets met and documented
```

---

## 📅 **DAY 5 PROMPT (Sept 14) - PERFORMANCE OPTIMIZATION**

```
TASK: Optimize performance and implement monitoring system

CONTEXT:
- Complete pipeline from Days 1-4
- Base directory: /Users/chiendu/XlineV2
- Target: <1ms event latency, comprehensive monitoring

MANDATORY COMPLIANCE: Follow ALL rules + achieve performance targets

EXACT REQUIREMENTS:
1. Create monitoring module:
   - xline/core/monitoring/__init__.py
   - xline/core/monitoring/metrics.py
   - xline/core/monitoring/performance.py

2. Implement metrics.py:
   ```python
   import time
   import asyncio
   from typing import Dict, Any, List
   from collections import defaultdict, deque
   from dataclasses import dataclass, field
   
   @dataclass
   class PerformanceMetrics:
       """Performance metrics tracking."""
       event_count: int = 0
       total_latency: float = 0.0
       min_latency: float = float('inf')
       max_latency: float = 0.0
       latency_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
       
       def add_latency_sample(self, latency: float) -> None:
           """Add latency sample and update metrics."""
           self.event_count += 1
           self.total_latency += latency
           self.min_latency = min(self.min_latency, latency)
           self.max_latency = max(self.max_latency, latency)
           self.latency_samples.append(latency)
           
       @property
       def avg_latency(self) -> float:
           """Calculate average latency."""
           return self.total_latency / self.event_count if self.event_count > 0 else 0.0
           
       @property
       def p99_latency(self) -> float:
           """Calculate 99th percentile latency."""
           if not self.latency_samples:
               return 0.0
           sorted_samples = sorted(self.latency_samples)
           index = int(0.99 * len(sorted_samples))
           return sorted_samples[index] if index < len(sorted_samples) else 0.0
   
   class MetricsCollector:
       """Collect and aggregate performance metrics."""
       
       def __init__(self) -> None:
           self.metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
           self.start_time = time.time()
           
       def record_event_latency(self, event_type: str, latency: float) -> None:
           """Record event processing latency."""
           self.metrics[event_type].add_latency_sample(latency)
           
       def get_summary(self) -> Dict[str, Any]:
           """Get performance summary."""
           summary = {}
           for event_type, metrics in self.metrics.items():
               summary[event_type] = {
                   "count": metrics.event_count,
                   "avg_latency_ms": metrics.avg_latency * 1000,
                   "p99_latency_ms": metrics.p99_latency * 1000,
                   "min_latency_ms": metrics.min_latency * 1000,
                   "max_latency_ms": metrics.max_latency * 1000
               }
           return summary
   ```

3. Implement performance.py:
   ```python
   import asyncio
   import psutil
   import time
   from typing import Dict, Any, Optional
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.monitoring.metrics import MetricsCollector
   
   class PerformanceMonitor:
       """System and application performance monitoring."""
       
       def __init__(self, event_bus: InMemoryEventBus) -> None:
           self.event_bus = event_bus
           self.metrics_collector = MetricsCollector()
           self.system_stats = {}
           self.is_monitoring = False
           
       async def start_monitoring(self) -> None:
           """Start performance monitoring."""
           self.is_monitoring = True
           asyncio.create_task(self._monitoring_loop())
           # Hook into event bus for latency measurement
           self._setup_latency_tracking()
           
       async def stop_monitoring(self) -> None:
           """Stop performance monitoring."""
           self.is_monitoring = False
           
       def _setup_latency_tracking(self) -> None:
           """Setup event latency tracking."""
           original_publish = self.event_bus.publish
           
           async def tracked_publish(event):
               start_time = time.perf_counter()
               result = await original_publish(event)
               latency = time.perf_counter() - start_time
               self.metrics_collector.record_event_latency(
                   str(event.event_type), latency
               )
               return result
               
           self.event_bus.publish = tracked_publish
           
       async def _monitoring_loop(self) -> None:
           """Main monitoring loop."""
           while self.is_monitoring:
               try:
                   # Collect system metrics
                   self.system_stats = {
                       "cpu_percent": psutil.cpu_percent(),
                       "memory_percent": psutil.virtual_memory().percent,
                       "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
                       "timestamp": time.time()
                   }
                   
                   # Check performance thresholds
                   await self._check_performance_thresholds()
                   
                   await asyncio.sleep(1)  # Monitor every second
                   
               except Exception as e:
                   print(f"Monitoring error: {e}")
                   
       async def _check_performance_thresholds(self) -> None:
           """Check if performance thresholds are exceeded."""
           summary = self.metrics_collector.get_summary()
           
           for event_type, metrics in summary.items():
               if metrics["p99_latency_ms"] > 1.0:  # > 1ms threshold
                   print(f"WARNING: {event_type} P99 latency exceeded: {metrics['p99_latency_ms']:.2f}ms")
                   
           if self.system_stats.get("memory_percent", 0) > 80:
               print(f"WARNING: High memory usage: {self.system_stats['memory_percent']:.1f}%")
               
       def get_performance_report(self) -> Dict[str, Any]:
           """Get comprehensive performance report."""
           return {
               "event_metrics": self.metrics_collector.get_summary(),
               "system_stats": self.system_stats,
               "monitoring_duration": time.time() - self.metrics_collector.start_time
           }
   ```

4. Create optimization tests:
   ```python
   # tests/performance/test_event_bus_performance.py
   import pytest
   import asyncio
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.monitoring.performance import PerformanceMonitor
   
   @pytest.mark.asyncio
   async def test_event_latency_target():
       """Test <1ms P99 latency target."""
       event_bus = InMemoryEventBus()
       monitor = PerformanceMonitor(event_bus)
       await monitor.start_monitoring()
       
       # Publish 1000 events
       for i in range(1000):
           event = Event(event_type=EventType.ORDER_CREATED, data={}, source="test")
           await event_bus.publish(event)
           
       # Check latency metrics
       report = monitor.get_performance_report()
       await monitor.stop_monitoring()
       
       # Assert P99 latency < 1ms
       for event_type, metrics in report["event_metrics"].items():
           assert metrics["p99_latency_ms"] < 1.0
   ```

5. Memory optimization:
   - Implement event object pooling
   - Add memory leak detection
   - Optimize data structures
   - Add garbage collection monitoring

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/performance/ -v
pytest --cov=xline.core.monitoring tests/
python -m scripts.performance_benchmark
```

SUCCESS CRITERIA:
- <1ms P99 latency achieved
- Memory usage < 500MB under load
- Comprehensive monitoring operational
- Performance benchmarks documented
- System optimization complete
```

---

## 📅 **DAY 6 PROMPT (Sept 15) - INTEGRATION & DOCUMENTATION**

```
TASK: Complete end-to-end integration testing and comprehensive documentation

CONTEXT:
- All core components implemented (Days 1-5)
- Base directory: /Users/chiendu/XlineV2
- Need complete integration validation and production-ready docs

MANDATORY COMPLIANCE: Follow ALL rules + create production-ready documentation

EXACT REQUIREMENTS:
1. End-to-end integration tests:
   ```python
   # tests/integration/week2/test_complete_pipeline.py
   import pytest
   import asyncio
   from xline.core.events.bus import InMemoryEventBus
   from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter
   from xline.core.adapters.strategy_bridge import StrategyBridge
   from xline.core.market_data.feed import MarketDataFeed
   from xline.core.monitoring.performance import PerformanceMonitor
   
   @pytest.mark.asyncio
   async def test_complete_trading_pipeline():
       """Test complete trading pipeline end-to-end."""
       # Setup components
       event_bus = InMemoryEventBus()
       adapter = FreqtradeAdapter(event_bus, {})
       bridge = StrategyBridge(event_bus)
       feed = MarketDataFeed(event_bus, {})
       monitor = PerformanceMonitor(event_bus)
       
       # Initialize system
       await adapter.setup_event_handlers()
       await monitor.start_monitoring()
       await feed.start()
       await feed.subscribe_symbol("BTCUSD")
       
       # Deploy and start strategy
       strategy_config = {
           "name": "TestStrategy",
           "class_name": "RSIStrategy",
           "parameters": {"rsi_period": 14}
       }
       strategy_id = await bridge.deploy_strategy(strategy_config)
       await bridge.start_strategy(strategy_id)
       await adapter.start_trading("test_account", "TestStrategy")
       
       # Let system run for 5 seconds
       await asyncio.sleep(5)
       
       # Verify system operation
       report = monitor.get_performance_report()
       assert report["event_metrics"]  # Events were processed
       
       # Cleanup
       await adapter.stop_trading("test_account")
       await bridge.stop_strategy(strategy_id)
       await feed.stop()
       await monitor.stop_monitoring()
   ```

2. Create comprehensive documentation:

   a) docs/week2/FREQTRADE_INTEGRATION_GUIDE.md:
   ```markdown
   # Freqtrade Integration Guide
   
   ## Overview
   Complete guide for integrating Freqtrade with Xline event system.
   
   ## Architecture
   [Detailed architecture diagrams and explanations]
   
   ## Installation
   [Step-by-step setup instructions]
   
   ## Configuration
   [Configuration examples and best practices]
   
   ## API Reference
   [Complete API documentation with examples]
   
   ## Troubleshooting
   [Common issues and solutions]
   ```

   b) docs/week2/ADAPTER_LAYER_ARCHITECTURE.md:
   ```markdown
   # Adapter Layer Architecture
   
   ## Design Principles
   [Architecture design principles and patterns]
   
   ## Component Overview
   [Detailed component specifications]
   
   ## Event Flow
   [Event flow diagrams and explanations]
   
   ## Performance Characteristics
   [Performance benchmarks and optimization tips]
   ```

   c) docs/week2/PERFORMANCE_TUNING_GUIDE.md:
   ```markdown
   # Performance Tuning Guide
   
   ## Performance Targets
   - Event latency: <1ms P99
   - Throughput: 1000+ events/second
   - Memory usage: <500MB
   
   ## Optimization Techniques
   [Detailed optimization strategies]
   
   ## Monitoring and Metrics
   [Monitoring setup and key metrics]
   
   ## Troubleshooting Performance Issues
   [Performance debugging guide]
   ```

3. Integration validation tests:
   - Test Freqtrade adapter with real FreqtradeBot
   - Test market data pipeline under load
   - Test strategy deployment and lifecycle
   - Test error handling and recovery
   - Test performance under stress

4. Documentation requirements:
   - Complete API reference
   - Architecture diagrams
   - Setup and configuration guides
   - Performance tuning guides
   - Troubleshooting guides

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/integration/week2/ -v
pytest tests/validation/week2_final_validation.py
python -m scripts.generate_api_docs
```

SUCCESS CRITERIA:
- Complete end-to-end pipeline working
- All integration tests passing
- Performance targets met
- Comprehensive documentation complete
- Production readiness validated
```

---

## 📅 **DAY 7 PROMPT (Sept 16) - FINAL VALIDATION & WEEK 3 PREP**

```
TASK: Final validation, completion report, and Week 3 planning

CONTEXT:
- Week 2 implementation complete
- Base directory: /Users/chiendu/XlineV2
- Need comprehensive validation and handoff documentation

MANDATORY COMPLIANCE: Follow ALL rules + create complete validation report

EXACT REQUIREMENTS:
1. Final validation suite:
   ```python
   # tests/validation/week2_final_validation.py
   import pytest
   import asyncio
   from xline.core.events.bus import InMemoryEventBus
   # Import all Week 2 components
   
   class TestWeek2FinalValidation:
       """Comprehensive Week 2 validation test suite."""
       
       @pytest.mark.asyncio
       async def test_coverage_target_achieved(self):
           """Validate 95%+ test coverage achieved."""
           # Run coverage analysis
           # Assert coverage >= 95%
           
       @pytest.mark.asyncio
       async def test_performance_targets_met(self):
           """Validate all performance targets met."""
           # Test event latency < 1ms
           # Test throughput > 1000 events/sec
           # Test memory usage < 500MB
           
       @pytest.mark.asyncio
       async def test_freqtrade_integration_complete(self):
           """Validate complete Freqtrade integration."""
           # Test adapter functionality
           # Test event publishing/subscribing
           # Test error handling
           
       @pytest.mark.asyncio
       async def test_strategy_management_working(self):
           """Validate strategy management system."""
           # Test strategy deployment
           # Test lifecycle management
           # Test concurrent strategies
           
       @pytest.mark.asyncio
       async def test_market_data_pipeline_operational(self):
           """Validate market data pipeline."""
           # Test real-time data processing
           # Test throughput targets
           # Test latency requirements
   ```

2. Week 2 completion report:
   ```markdown
   # WEEK 2 COMPLETION REPORT
   
   ## Implementation Summary
   - ✅ Test coverage: 94% → 95%+
   - ✅ Freqtrade adapter layer complete
   - ✅ Event mapping and strategy bridge operational
   - ✅ Market data pipeline working
   - ✅ Performance optimization complete
   - ✅ Integration testing validated
   - ✅ Documentation complete
   
   ## Performance Metrics Achieved
   - Event latency: <1ms P99 ✅
   - Throughput: 1000+ events/second ✅
   - Memory usage: <500MB ✅
   - Test coverage: 95%+ ✅
   
   ## Components Delivered
   [Detailed component list with status]
   
   ## Known Issues
   [Any remaining issues and workarounds]
   
   ## Week 3 Recommendations
   [Recommendations for Week 3 development]
   ```

3. Week 3 planning document:
   ```markdown
   # WEEK 3 IMPLEMENTATION PLAN
   
   ## Objectives
   - Risk management system
   - Portfolio optimization
   - Advanced analytics
   - Production deployment
   
   ## Dependencies from Week 2
   [List of Week 2 deliverables needed for Week 3]
   
   ## Implementation Schedule
   [7-day detailed plan for Week 3]
   ```

4. Handoff documentation:
   - Complete API reference
   - Architecture decision records
   - Performance benchmarks
   - Known limitations
   - Future enhancement suggestions

VALIDATION COMMANDS:
```bash
cd /Users/chiendu/XlineV2
pytest tests/validation/week2_final_validation.py -v
pytest --cov=xline --cov-report=html tests/
python -m scripts.generate_week2_report
python -m scripts.week3_planning
```

SUCCESS CRITERIA:
- All Week 2 objectives completed
- Performance targets validated
- Comprehensive completion report
- Week 3 plan ready
- Clean handoff to next phase
```

---

## 🎯 **WEEK 2 SUCCESS METRICS**

### **Daily Validation Commands**
```bash
# Day 1: Coverage validation
pytest --cov=xline.core.events --cov-report=html tests/
coverage report --fail-under=95

# Day 2: Adapter validation  
pytest tests/integration/adapters/test_freqtrade_adapter.py -v
pytest --cov=xline.core.adapters.freqtrade_adapter tests/

# Day 3: Mapping validation
pytest tests/unit/adapters/test_event_mapper.py -v
pytest tests/integration/adapters/test_strategy_bridge.py -v

# Day 4: Market data validation
pytest tests/performance/test_market_data_throughput.py
pytest --cov=xline.core.market_data tests/

# Day 5: Performance validation
pytest tests/performance/ -v
python -m scripts.performance_benchmark

# Day 6: Integration validation
pytest tests/integration/week2/ -v
python -m scripts.generate_api_docs

# Day 7: Final validation
pytest tests/validation/week2_final_validation.py -v
python -m scripts.generate_week2_report
```

### **Performance Targets (MUST ACHIEVE)**
- ✅ Test Coverage: 94% → 95%+
- ✅ Event Latency: <1ms P99
- ✅ Market Data Throughput: 1000+ ticks/second  
- ✅ Memory Usage: <500MB under load
- ✅ Integration Tests: 200+ tests passing
- ✅ Zero memory leaks under stress

### **Architecture Compliance (MANDATORY)**
- ✅ All communication via event bus
- ✅ NO direct freqtrade/* imports in business logic
- ✅ Async/await patterns throughout
- ✅ Comprehensive type hints
- ✅ Security validation for all inputs
- ✅ Circuit breakers for external calls

---

## 🚀 **QUICK START CHECKLIST**

### **Prerequisites Verification**
```bash
cd /Users/chiendu/XlineV2
python --version  # Must be 3.11+
pip list | grep freqtrade  # Must be v2023.9+
pytest --version  # Must be latest
```

### **Daily Execution Pattern**
1. **Copy exact prompt for the day**
2. **Paste to AI Agent with full context**
3. **Follow implementation requirements exactly**
4. **Run validation commands**
5. **Verify success criteria met**
6. **Proceed to next day only if all criteria passed**

### **Emergency Procedures**
- If any validation fails: STOP and fix before proceeding
- If performance targets not met: Review optimization guide
- If tests fail: Debug using provided troubleshooting steps
- If architecture violations: Review compliance rules

---

**📋 FINAL NOTE: This document contains COMPLETE implementation guidance for Week 2. Copy exact prompts for each day and paste to AI Agent for 100% successful implementation.**
