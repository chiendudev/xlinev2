"""
Integration tests for FreqtradeAdapter
File: tests/integration/adapters/test_freqtrade_adapter.py

Comprehensive test suite ensuring 95%+ coverage and proper integration
with the Xline event system and Freqtrade trading engine.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from xline.core.adapters.freqtrade_adapter import FreqtradeAdapter
from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType, OrderEvent, SystemEvent


@pytest.fixture
async def adapter_setup():
    """Setup event bus and adapter for testing."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    config = {"test": True, "dry_run": True}
    adapter = FreqtradeAdapter(event_bus, config)
    return event_bus, adapter


@pytest.fixture
async def adapter_with_handlers():
    """Setup adapter with event handlers configured."""
    event_bus = InMemoryEventBus()
    await event_bus.initialize()
    config = {"test": True, "dry_run": True}
    adapter = FreqtradeAdapter(event_bus, config)
    await adapter.setup_event_handlers()
    return event_bus, adapter


@pytest.mark.asyncio
async def test_freqtrade_adapter_initialization(adapter_setup):
    """Test adapter initialization and setup."""
    event_bus, adapter = adapter_setup

    # Test initial state
    assert adapter.event_bus is event_bus
    assert adapter.config == {"test": True, "dry_run": True}
    assert adapter.freqtrade_bot is None
    assert adapter.active_sessions == {}
    assert adapter._is_setup is False

    # Test setup
    await adapter.setup_event_handlers()
    assert adapter._is_setup is True


@pytest.mark.asyncio
async def test_setup_event_handlers(adapter_setup):
    """Test event handler setup and subscription."""
    event_bus, adapter = adapter_setup

    # Mock the subscription method to verify it's called
    with patch.object(event_bus, "subscribe") as mock_subscribe:
        mock_subscribe.return_value = Mock()

        await adapter.setup_event_handlers()

        # Verify subscription to risk events
        mock_subscribe.assert_called_once_with(
            EventType.RISK_LIMIT_BREACHED.value, adapter._handle_risk_event
        )
        assert adapter._is_setup is True


@pytest.mark.asyncio
async def test_start_trading_success(adapter_with_handlers):
    """Test successful trading start."""
    event_bus, adapter = adapter_with_handlers

    # Mock FreqtradeBot
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot") as mock_bot_class:
        mock_bot = Mock()
        mock_bot_class.return_value = mock_bot

        # Test successful start
        result = await adapter.start_trading("test_account", "RSIStrategy")

        assert result is True
        assert len(adapter.active_sessions) == 1

        # Verify session data
        session_id = "test_account_RSIStrategy"
        assert session_id in adapter.active_sessions
        session = adapter.active_sessions[session_id]
        assert session["account_id"] == "test_account"
        assert session["strategy_name"] == "RSIStrategy"
        assert session["status"] == "active"
        assert "start_time" in session

        # Verify FreqtradeBot was initialized
        assert adapter.freqtrade_bot is mock_bot


@pytest.mark.asyncio
async def test_start_trading_validation_error(adapter_with_handlers):
    """Test trading start with invalid inputs."""
    event_bus, adapter = adapter_with_handlers

    # Test empty account_id
    result = await adapter.start_trading("", "RSIStrategy")
    assert result is False
    assert len(adapter.active_sessions) == 0

    # Test empty strategy_name
    result = await adapter.start_trading("test_account", "")
    assert result is False
    assert len(adapter.active_sessions) == 0

    # Test both empty
    result = await adapter.start_trading("", "")
    assert result is False
    assert len(adapter.active_sessions) == 0


@pytest.mark.asyncio
async def test_start_trading_with_existing_bot(adapter_with_handlers):
    """Test trading start when FreqtradeBot already exists."""
    event_bus, adapter = adapter_with_handlers

    # Set up existing bot
    mock_bot = Mock()
    adapter.freqtrade_bot = mock_bot

    result = await adapter.start_trading("test_account", "MACDStrategy")

    assert result is True
    assert adapter.freqtrade_bot is mock_bot  # Should use existing bot
    assert len(adapter.active_sessions) == 1


@pytest.mark.asyncio
async def test_stop_trading_success(adapter_with_handlers):
    """Test successful trading stop."""
    event_bus, adapter = adapter_with_handlers

    # Start multiple sessions for the same account
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        await adapter.start_trading("test_account", "Strategy1")
        await adapter.start_trading("test_account", "Strategy2")
        await adapter.start_trading("other_account", "Strategy3")

    assert len(adapter.active_sessions) == 3

    # Stop trading for test_account
    result = await adapter.stop_trading("test_account")

    assert result is True

    # Verify sessions for test_account are stopped
    for session_id, session in adapter.active_sessions.items():
        if session["account_id"] == "test_account":
            assert session["status"] == "stopped"
        else:
            assert session["status"] == "active"


@pytest.mark.asyncio
async def test_stop_trading_no_sessions(adapter_with_handlers):
    """Test stop trading when no sessions exist for account."""
    event_bus, adapter = adapter_with_handlers

    result = await adapter.stop_trading("nonexistent_account")
    assert result is True  # Should succeed even if no sessions


@pytest.mark.asyncio
async def test_emergency_stop(adapter_with_handlers):
    """Test emergency stop functionality."""
    event_bus, adapter = adapter_with_handlers

    # Start multiple sessions
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        await adapter.start_trading("account1", "Strategy1")
        await adapter.start_trading("account2", "Strategy2")
        await adapter.start_trading("account3", "Strategy3")

    assert len(adapter.active_sessions) == 3

    # Mock event bus publish to capture emergency event
    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        await adapter.emergency_stop()

    # Verify all sessions are emergency stopped
    for session in adapter.active_sessions.values():
        assert session["status"] == "emergency_stopped"

    # Verify emergency event was published
    assert len(published_events) == 1
    emergency_event = published_events[0]
    assert isinstance(emergency_event, SystemEvent)
    assert emergency_event.type == EventType.EMERGENCY_STOP
    assert emergency_event.source == "freqtrade_adapter"
    assert "emergency_stop_triggered" in emergency_event.data["reason"]


@pytest.mark.asyncio
async def test_emergency_stop_with_exception(adapter_with_handlers):
    """Test emergency stop handles exceptions gracefully."""
    event_bus, adapter = adapter_with_handlers

    # Start a session
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        await adapter.start_trading("test_account", "TestStrategy")

    # Mock event bus to raise exception
    with patch.object(event_bus, "publish", side_effect=Exception("Publish failed")):
        # Should not raise exception
        await adapter.emergency_stop()

        # Session should still be marked as emergency stopped
        for session in adapter.active_sessions.values():
            assert session["status"] == "emergency_stopped"


@pytest.mark.asyncio
async def test_handle_risk_event(adapter_with_handlers):
    """Test risk event handling triggers emergency stop."""
    event_bus, adapter = adapter_with_handlers

    # Start a session
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        await adapter.start_trading("test_account", "TestStrategy")

    # Mock emergency_stop to verify it's called
    with patch.object(adapter, "emergency_stop") as mock_emergency_stop:
        mock_emergency_stop.return_value = None

        # Create risk event
        risk_event = SystemEvent(
            type=EventType.RISK_LIMIT_BREACHED,
            source="risk_manager",
            component="RiskManager",
            status="critical",
            message="Risk limit breached",
            data={"risk_level": "critical", "breach_type": "max_drawdown"},
        )

        await adapter._handle_risk_event(risk_event)

        # Verify emergency stop was called
        mock_emergency_stop.assert_called_once()


@pytest.mark.asyncio
async def test_handle_non_risk_event(adapter_with_handlers):
    """Test handling of non-risk events."""
    event_bus, adapter = adapter_with_handlers

    # Mock emergency_stop to verify it's NOT called
    with patch.object(adapter, "emergency_stop") as mock_emergency_stop:
        # Create non-risk event
        other_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="order_manager",
            order_id="123",
            account_id="test_account",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("45000.0"),
            data={"order_id": "123"},
        )

        await adapter._handle_risk_event(other_event)

        # Verify emergency stop was NOT called
        mock_emergency_stop.assert_not_called()


@pytest.mark.asyncio
async def test_publish_order_event(adapter_with_handlers):
    """Test order event publishing."""
    event_bus, adapter = adapter_with_handlers

    # Mock event bus publish
    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        order_data = {
            "id": "order_123",
            "account_id": "test_account",
            "symbol": "BTCUSDT",
            "amount": "1.5",
            "price": "45000.0",
        }

        await adapter._publish_order_event(order_data, "BUY")

    # Verify order event was published
    assert len(published_events) == 1
    order_event = published_events[0]
    assert isinstance(order_event, OrderEvent)
    assert order_event.type == EventType.ORDER_CREATED
    assert order_event.source == "freqtrade_adapter"
    assert order_event.order_id == "order_123"
    assert order_event.account_id == "test_account"
    assert order_event.symbol == "BTCUSDT"
    assert order_event.side.value == "buy"
    assert order_event.quantity == Decimal("1.5")
    assert order_event.price == Decimal("45000.0")


@pytest.mark.asyncio
async def test_publish_order_event_sell(adapter_with_handlers):
    """Test sell order event publishing."""
    event_bus, adapter = adapter_with_handlers

    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        order_data = {
            "id": "order_456",
            "account_id": "test_account",
            "symbol": "ETHUSDT",
            "amount": "2.0",
            "price": "3000.0",
        }

        await adapter._publish_order_event(order_data, "SELL")

    # Verify sell order event
    order_event = published_events[0]
    assert order_event.side.value == "sell"


@pytest.mark.asyncio
async def test_publish_order_event_with_exception(adapter_with_handlers):
    """Test order event publishing handles exceptions."""
    event_bus, adapter = adapter_with_handlers

    # Mock event bus to raise exception
    with patch.object(event_bus, "publish", side_effect=Exception("Publish failed")):
        order_data = {"id": "order_123", "symbol": "BTCUSDT", "amount": "1.0", "price": "45000.0"}

        # Should not raise exception
        await adapter._publish_order_event(order_data, "BUY")


@pytest.mark.asyncio
async def test_publish_strategy_event(adapter_with_handlers):
    """Test strategy event publishing."""
    event_bus, adapter = adapter_with_handlers

    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        await adapter._publish_strategy_event("STRATEGY_STARTED", "test_account", "TestStrategy")

    # Verify strategy event was published
    assert len(published_events) == 1
    strategy_event = published_events[0]
    assert isinstance(strategy_event, SystemEvent)
    assert strategy_event.type == EventType.STRATEGY_STARTED
    assert strategy_event.source == "freqtrade_adapter"
    assert strategy_event.data["account_id"] == "test_account"
    assert strategy_event.data["strategy_name"] == "TestStrategy"


@pytest.mark.asyncio
async def test_setup_freqtrade_hooks_no_bot(adapter_setup):
    """Test hook setup when no FreqtradeBot exists."""
    event_bus, adapter = adapter_setup

    # Should not raise exception when no bot exists
    adapter._setup_freqtrade_hooks()


@pytest.mark.asyncio
async def test_setup_freqtrade_hooks_with_bot(adapter_setup):
    """Test hook setup with FreqtradeBot."""
    event_bus, adapter = adapter_setup

    # Create mock bot with execute methods
    mock_bot = Mock()
    original_execute_entry = AsyncMock()
    original_execute_exit = AsyncMock()
    mock_bot.execute_entry = original_execute_entry
    mock_bot.execute_exit = original_execute_exit

    adapter.freqtrade_bot = mock_bot

    # Setup hooks
    adapter._setup_freqtrade_hooks()

    # Verify methods were replaced with hooks
    assert adapter.freqtrade_bot.execute_entry is not original_execute_entry
    assert adapter.freqtrade_bot.execute_exit is not original_execute_exit


@pytest.mark.asyncio
async def test_freqtrade_hooks_execution(adapter_setup):
    """Test execution of hooked Freqtrade methods."""
    event_bus, adapter = adapter_setup
    await adapter.setup_event_handlers()

    # Create mock bot with execute methods
    mock_bot = Mock()
    original_execute_entry = AsyncMock()
    original_execute_exit = AsyncMock()

    # Mock successful order results
    entry_result = {
        "id": "entry_order_123",
        "account_id": "test_account",
        "symbol": "BTCUSDT",
        "amount": "1.0",
        "price": "45000.0",
    }
    exit_result = {
        "id": "exit_order_456",
        "account_id": "test_account",
        "symbol": "ETHUSDT",
        "amount": "0.5",
        "price": "3000.0",
    }

    original_execute_entry.return_value = entry_result
    original_execute_exit.return_value = exit_result

    mock_bot.execute_entry = original_execute_entry
    mock_bot.execute_exit = original_execute_exit

    adapter.freqtrade_bot = mock_bot

    # Setup hooks
    adapter._setup_freqtrade_hooks()

    # Mock event publishing to capture events
    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        # Test entry execution
        result = await adapter.freqtrade_bot.execute_entry("test_args")
        assert result == entry_result

        # Test exit execution
        result = await adapter.freqtrade_bot.execute_exit("test_args")
        assert result == exit_result

    # Verify events were published
    assert len(published_events) == 2
    assert published_events[0].order_id == "entry_order_123"
    assert published_events[1].order_id == "exit_order_456"


@pytest.mark.asyncio
async def test_freqtrade_hooks_no_result(adapter_setup):
    """Test hooked methods when no result is returned."""
    event_bus, adapter = adapter_setup
    await adapter.setup_event_handlers()

    # Create mock bot with execute methods that return None
    mock_bot = Mock()
    original_execute_entry = AsyncMock(return_value=None)
    original_execute_exit = AsyncMock(return_value=None)

    mock_bot.execute_entry = original_execute_entry
    mock_bot.execute_exit = original_execute_exit

    adapter.freqtrade_bot = mock_bot

    # Setup hooks
    adapter._setup_freqtrade_hooks()

    # Mock event publishing to ensure no events are published
    published_events = []

    async def mock_publish(event):
        published_events.append(event)
        return Mock(success=True)

    with patch.object(event_bus, "publish", side_effect=mock_publish):
        # Test entry execution with no result
        result = await adapter.freqtrade_bot.execute_entry("test_args")
        assert result is None

        # Test exit execution with no result
        result = await adapter.freqtrade_bot.execute_exit("test_args")
        assert result is None

    # Verify no events were published since results were None
    assert len(published_events) == 0


@pytest.mark.asyncio
async def test_multiple_session_management(adapter_with_handlers):
    """Test managing multiple trading sessions."""
    event_bus, adapter = adapter_with_handlers

    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        # Start multiple sessions
        assert await adapter.start_trading("account1", "Strategy1") is True
        assert await adapter.start_trading("account1", "Strategy2") is True
        assert await adapter.start_trading("account2", "Strategy1") is True
        assert await adapter.start_trading("account3", "Strategy3") is True

    assert len(adapter.active_sessions) == 4

    # Stop trading for account1 only
    assert await adapter.stop_trading("account1") is True

    # Verify correct sessions were stopped
    stopped_sessions = [s for s in adapter.active_sessions.values() if s["status"] == "stopped"]
    active_sessions = [s for s in adapter.active_sessions.values() if s["status"] == "active"]

    assert len(stopped_sessions) == 2  # account1 had 2 strategies
    assert len(active_sessions) == 2  # account2 and account3

    # Verify the right accounts were stopped
    for session in stopped_sessions:
        assert session["account_id"] == "account1"

    for session in active_sessions:
        assert session["account_id"] in ["account2", "account3"]


@pytest.mark.asyncio
async def test_adapter_error_handling(adapter_with_handlers):
    """Test adapter handles various error conditions gracefully."""
    event_bus, adapter = adapter_with_handlers

    # Test start_trading with bot initialization failure
    with patch(
        "xline.core.adapters.freqtrade_adapter.FreqtradeBot",
        side_effect=Exception("Bot init failed"),
    ):
        result = await adapter.start_trading("test_account", "TestStrategy")
        assert result is False
        assert len(adapter.active_sessions) == 0

    # Test stop_trading with exception in cleanup
    with patch("xline.core.adapters.freqtrade_adapter.FreqtradeBot"):
        await adapter.start_trading("test_account", "TestStrategy")

    # Mock _publish_strategy_event to raise exception
    with patch.object(
        adapter, "_publish_strategy_event", side_effect=Exception("Event publish failed")
    ):
        result = await adapter.stop_trading("test_account")
        assert result is False  # Should return False on exception

    # Test _handle_risk_event with exception
    with patch.object(adapter, "emergency_stop", side_effect=Exception("Emergency stop failed")):
        risk_event = SystemEvent(
            type=EventType.RISK_LIMIT_BREACHED,
            source="test",
            component="TestComponent",
            status="test",
            message="Test risk event",
            data={},
        )
        # Should not raise exception
        await adapter._handle_risk_event(risk_event)
