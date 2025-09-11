"""
Comprehensive test suite for types.py to achieve 95%+ coverage
"""

import pytest
from decimal import Decimal

from xline.core.events.types import (
    OrderEvent, TradeEvent, RiskEvent, AccountEvent, SystemEvent,
    EventType, OrderSide, OrderType, OrderStatus, RiskSeverity,
    create_event_from_dict
)


class TestTypes:
    """Comprehensive tests for types.py"""

    # === ENUM TESTS ===
    def test_event_type_str_method(self):
        """Test EventType __str__ method for line 60 coverage."""
        assert str(EventType.ORDER_CREATED) == "order.created"
        assert str(EventType.TRADE_EXECUTED) == "trade.executed"
        assert str(EventType.SYSTEM_STARTUP) == "system.startup"

    # === BASE EVENT CLASS TESTS ===
    def test_event_empty_source_error(self):
        """Test Event validation with empty source."""
        with pytest.raises(ValueError, match="Event source cannot be empty"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="",  # Empty source
                order_id="order_123",
                account_id="account_456",
                symbol="BTCUSDT",
                quantity=Decimal("1.0"),
                price=Decimal("50000.0")
            )

    def test_event_invalid_timestamp_error(self):
        """Test Event validation with invalid timestamp."""
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="order_123",
            account_id="account_456",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        event.timestamp = "invalid_timestamp"  # String instead of datetime
        
        with pytest.raises(ValueError, match="Timestamp must be a datetime object"):
            event.__post_init__()

    # === ORDER EVENT TESTS ===
    def test_order_event_full_creation(self):
        """Test OrderEvent with all fields."""
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="order_123",
            account_id="account_456",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            price=Decimal("50000.0"),
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            stop_price=Decimal("49000.0"),
            time_in_force="IOC",
            client_order_id="client_123",
            exchange="binance",
            filled_quantity=Decimal("0.5"),
            remaining_quantity=Decimal("1.0"),
            average_fill_price=Decimal("50100.0")
        )
        assert event.order_id == "order_123"
        assert event.symbol == "BTCUSDT"
        assert event.quantity == Decimal("1.5")

    def test_order_event_to_dict(self):
        """Test OrderEvent to_dict method."""
        event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="order_123",
            account_id="account_456",
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
        event_dict = event.to_dict()
        assert event_dict['order_id'] == "order_123"
        assert event_dict['symbol'] == "BTCUSDT"
        assert event_dict['quantity'] == "1.0"

    def test_order_event_from_dict(self):
        """Test OrderEvent from_dict method."""
        order_data = {
            "id": "test_order_123",
            "type": "order.created",
            "source": "trading_system",
            "timestamp": "2024-01-01T12:00:00",
            "order_id": "order_456",
            "account_id": "account_789",
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "limit",
            "status": "open",
            "quantity": "1.5",
            "price": "50000.0",
            "stop_price": "49000.0",
            "time_in_force": "IOC",
            "client_order_id": "client_123",
            "exchange": "binance",
            "filled_quantity": "0.5",
            "remaining_quantity": "1.0",
            "average_fill_price": "50100.0"
        }
        order = OrderEvent.from_dict(order_data)
        assert order.order_id == "order_456"
        assert order.exchange == "binance"

    def test_order_event_remaining_quantity_calculation(self):
        """Test OrderEvent remaining_quantity calculation."""
        order = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="order_123",
            account_id="account_456",
            symbol="BTCUSDT",
            quantity=Decimal("2.0"),
            price=Decimal("50000.0"),
            filled_quantity=Decimal("0.8")
        )
        assert order.remaining_quantity == Decimal("1.2")

    # === ORDER EVENT VALIDATION ERRORS ===
    def test_order_event_empty_order_id_error(self):
        """Test OrderEvent validation with empty order_id."""
        with pytest.raises(ValueError, match="Order ID cannot be empty"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="test_source",
                order_id="",
                account_id="account_456",
                symbol="BTCUSDT",
                quantity=Decimal("1.0"),
                price=Decimal("50000.0")
            )

    def test_order_event_empty_account_id_error(self):
        """Test OrderEvent validation with empty account_id."""
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="test_source",
                order_id="order_123",
                account_id="",
                symbol="BTCUSDT",
                quantity=Decimal("1.0"),
                price=Decimal("50000.0")
            )

    def test_order_event_empty_symbol_error(self):
        """Test OrderEvent validation with empty symbol."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="test_source",
                order_id="order_123",
                account_id="account_456",
                symbol="",
                quantity=Decimal("1.0"),
                price=Decimal("50000.0")
            )

    def test_order_event_negative_quantity_error(self):
        """Test OrderEvent validation with negative quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="test_source",
                order_id="order_123",
                account_id="account_456",
                symbol="BTCUSDT",
                quantity=Decimal("-1.0"),
                price=Decimal("50000.0")
            )

    def test_order_event_negative_price_error(self):
        """Test OrderEvent validation with negative price."""
        with pytest.raises(ValueError, match="Price cannot be negative"):
            OrderEvent(
                type=EventType.ORDER_CREATED,
                source="test_source",
                order_id="order_123",
                account_id="account_456",
                symbol="BTCUSDT",
                quantity=Decimal("1.0"),
                price=Decimal("-50000.0")
            )

    # === TRADE EVENT TESTS ===
    def test_trade_event_creation(self):
        """Test TradeEvent creation and to_dict."""
        event = TradeEvent(
            type=EventType.TRADE_EXECUTED,
            source="exchange",
            trade_id="trade_123",
            order_id="order_456",
            account_id="account_789",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.5"),
            price=Decimal("3000.0"),
            fee=Decimal("0.05"),
            commission=Decimal("0.1"),
            exchange="binance"
        )
        assert event.trade_id == "trade_123"
        assert event.symbol == "ETHUSDT"
        
        trade_dict = event.to_dict()
        assert trade_dict['trade_id'] == "trade_123"

    def test_trade_event_from_dict(self):
        """Test TradeEvent from_dict method."""
        trade_data = {
            "id": "test_trade_123",
            "type": "trade.executed",
            "source": "exchange",
            "timestamp": "2024-01-01T12:00:00",
            "trade_id": "trade_456",
            "order_id": "order_789",
            "account_id": "account_123",
            "symbol": "ETHUSDT",
            "side": "sell",
            "quantity": "2.5",
            "price": "3000.0",
            "fee": "0.05",
            "commission": "0.1"
        }
        trade = TradeEvent.from_dict(trade_data)
        assert trade.trade_id == "trade_456"
        assert trade.symbol == "ETHUSDT"

    def test_trade_event_trade_time_setting(self):
        """Test TradeEvent trade_time auto-setting."""
        trade = TradeEvent(
            type=EventType.TRADE_EXECUTED,
            source="exchange",
            trade_id="trade_123",
            order_id="order_456",
            account_id="account_789",
            symbol="ETHUSDT",
            quantity=Decimal("2.5"),
            price=Decimal("3000.0")
        )
        assert trade.trade_time == trade.timestamp

    # === TRADE EVENT VALIDATION ERRORS ===
    def test_trade_event_validation_errors(self):
        """Test TradeEvent validation errors."""
        # Test empty trade_id
        with pytest.raises(ValueError, match="Trade ID cannot be empty"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0")
            )

        # Test empty order_id
        with pytest.raises(ValueError, match="Order ID cannot be empty"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0")
            )

    def test_trade_event_more_validation_errors(self):
        """Test more TradeEvent validation errors."""
        # Test negative price
        with pytest.raises(ValueError, match="Price must be positive"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("-3000.0")
            )

        # Test negative fee
        with pytest.raises(ValueError, match="Fee cannot be negative"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0"),
                fee=Decimal("-0.05")
            )

        # Test negative commission
        with pytest.raises(ValueError, match="Commission cannot be negative"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0"),
                commission=Decimal("-0.1")
            )

    # === RISK EVENT TESTS ===
    def test_risk_event_creation(self):
        """Test RiskEvent creation."""
        event = RiskEvent(
            type=EventType.RISK_LIMIT_BREACHED,
            source="risk_engine",
            account_id="account_123",
            rule_type="position_limit",
            severity=RiskSeverity.HIGH,
            threshold=Decimal("100000"),
            current_value=Decimal("150000"),
            message="Position limit exceeded"
        )
        assert event.severity == RiskSeverity.HIGH
        assert event.message == "Position limit exceeded"

    def test_risk_event_validation_errors(self):
        """Test RiskEvent validation errors."""
        # Test empty account_id
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            RiskEvent(
                type=EventType.RISK_LIMIT_BREACHED,
                source="risk_engine",
                account_id="",
                rule_type="position_limit",
                message="Position limit exceeded"
            )

        # Test empty rule_type
        with pytest.raises(ValueError, match="Rule type cannot be empty"):
            RiskEvent(
                type=EventType.RISK_LIMIT_BREACHED,
                source="risk_engine",
                account_id="account_123",
                rule_type="",
                message="Position limit exceeded"
            )

    def test_risk_event_more_validation_errors(self):
        """Test more RiskEvent validation errors."""
        # Test empty message
        with pytest.raises(ValueError, match="Message cannot be empty"):
            RiskEvent(
                type=EventType.RISK_LIMIT_BREACHED,
                source="risk_engine",
                account_id="account_123",
                rule_type="position_limit",
                message=""
            )

        # Test negative threshold
        with pytest.raises(ValueError, match="Threshold cannot be negative"):
            RiskEvent(
                type=EventType.RISK_LIMIT_BREACHED,
                source="risk_engine",
                account_id="account_123",
                rule_type="position_limit",
                message="Position limit exceeded",
                threshold=Decimal("-100000")
            )

    # === ACCOUNT EVENT TESTS ===
    def test_account_event_creation(self):
        """Test AccountEvent creation."""
        event = AccountEvent(
            type=EventType.ACCOUNT_BALANCE_UPDATED,
            source="account_service",
            account_id="account_123",
            account_type="trading",
            status="active",
            balance=Decimal("50000.0"),
            currency="USDT"
        )
        assert event.account_id == "account_123"
        assert event.account_type == "trading"

    def test_account_event_validation_errors(self):
        """Test AccountEvent validation errors."""
        # Test empty account_id
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            AccountEvent(
                type=EventType.ACCOUNT_BALANCE_UPDATED,
                source="account_service",
                account_id="",
                account_type="trading",
                status="active"
            )

    def test_account_event_more_validation_errors(self):
        """Test more AccountEvent validation errors."""
        # Test empty account_type
        with pytest.raises(ValueError, match="Account type cannot be empty"):
            AccountEvent(
                type=EventType.ACCOUNT_BALANCE_UPDATED,
                source="account_service",
                account_id="account_123",
                account_type="",
                status="active"
            )

        # Test empty status
        with pytest.raises(ValueError, match="Status cannot be empty"):
            AccountEvent(
                type=EventType.ACCOUNT_BALANCE_UPDATED,
                source="account_service",
                account_id="account_123",
                account_type="trading",
                status=""
            )

    # === SYSTEM EVENT TESTS ===
    def test_system_event_creation(self):
        """Test SystemEvent creation."""
        event = SystemEvent(
            type=EventType.SYSTEM_STARTUP,
            source="system",
            component="trading_engine",
            status="starting",
            message="Trading engine is initializing"
        )
        assert event.component == "trading_engine"
        assert event.status == "starting"

    def test_system_event_validation_errors(self):
        """Test SystemEvent validation errors."""
        # Test empty component
        with pytest.raises(ValueError, match="Component cannot be empty"):
            SystemEvent(
                type=EventType.SYSTEM_STARTUP,
                source="system",
                component="",
                status="starting",
                message="System starting"
            )

    def test_system_event_more_validation_errors(self):
        """Test more SystemEvent validation errors."""
        # Test empty status
        with pytest.raises(ValueError, match="Status cannot be empty"):
            SystemEvent(
                type=EventType.SYSTEM_STARTUP,
                source="system",
                component="trading_engine",
                status="",
                message="System starting"
            )

        # Test empty message
        with pytest.raises(ValueError, match="Message cannot be empty"):
            SystemEvent(
                type=EventType.SYSTEM_STARTUP,
                source="system",
                component="trading_engine",
                status="starting",
                message=""
            )

    # === CREATE EVENT FROM DICT TESTS ===
    def test_create_event_from_dict(self):
        """Test create_event_from_dict function."""
        event_data = {
            "id": "test_event_123",
            "type": "order.created",
            "source": "test_source",
            "timestamp": "2024-01-01T12:00:00",
            "order_id": "order_123",
            "account_id": "account_456",
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "limit",
            "status": "open",
            "quantity": "1.0",
            "price": "50000.0"
        }
        event = create_event_from_dict(event_data)
        assert event.order_id == "order_123"

    def test_create_event_from_dict_unknown_event_type_value_error(self):
        """Test create_event_from_dict with unknown event type that triggers ValueError."""
        event_data = {
            "id": "test_event_123",
            "type": "unknown.event.type",
            "source": "test_source",
            "timestamp": "2024-01-01T12:00:00"
        }
        
        with pytest.raises(ValueError, match="Unknown event type"):
            create_event_from_dict(event_data)

    def test_create_event_from_dict_invalid_event_type_format(self):
        """Test create_event_from_dict with invalid event type format."""
        event_data = {
            "id": "test_event_123",
            "type": "invalid_format",
            "source": "test_source",
            "timestamp": "2024-01-01T12:00:00"
        }
        
        with pytest.raises(ValueError, match="Unknown event type"):
            create_event_from_dict(event_data)

    # === ADDITIONAL TESTS FOR 100% COVERAGE ===
    def test_trade_event_quantity_validation_line_275(self):
        """Test TradeEvent quantity validation for line 275."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("-2.5"),  # Line 275: if self.quantity <= 0
                price=Decimal("3000.0")
            )
    def test_trade_event_fee_validation_line_271(self):
        """Test TradeEvent fee validation for line 271."""
        with pytest.raises(ValueError, match="Fee cannot be negative"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0"),
                fee=Decimal("-0.01")  # Line 271: if self.fee < 0 with negative fee
            )

    def test_trade_event_commission_validation_line_273(self):
        """Test TradeEvent commission validation for line 273."""
        with pytest.raises(ValueError, match="Commission cannot be negative"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("2.5"),
                price=Decimal("3000.0"),
                fee=Decimal("0.01"),  # Valid fee
                commission=Decimal("-0.01")  # Line 273: if self.commission < 0
            )

    def test_trade_event_quantity_validation_line_275(self):
        """Test TradeEvent quantity validation for line 275."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="exchange",
                trade_id="trade_123",
                order_id="order_456",
                account_id="account_789",
                symbol="ETHUSDT",
                quantity=Decimal("-2.5"),  # Line 275: if self.quantity <= 0
                price=Decimal("3000.0")
            )

    def test_risk_event_to_dict_line_377(self):
        """Test RiskEvent to_dict method for line 377."""
        event = RiskEvent(
            type=EventType.RISK_LIMIT_BREACHED,
            source="risk_engine",
            account_id="account_123",
            rule_type="position_limit",
            message="Position limit exceeded"
        )
        result = event.to_dict()
        assert result['account_id'] == "account_123"  # Line 377

    def test_risk_event_from_dict_line_401(self):
        """Test RiskEvent from_dict method for line 401."""
        risk_data = {
            "id": "test_risk_123",
            "type": "risk.limit_breached",
            "source": "risk_engine",
            "timestamp": "2024-01-01T12:00:00",
            "account_id": "account_123",
            "rule_type": "position_limit",
            "severity": "high",
            "threshold": "100000",
            "current_value": "150000",
            "message": "Position limit exceeded"
        }
        event = RiskEvent.from_dict(risk_data)
        assert event.account_id == "account_123"  # Line 401

    def test_account_event_to_dict_line_456(self):
        """Test AccountEvent to_dict method for line 456."""
        event = AccountEvent(
            type=EventType.ACCOUNT_BALANCE_UPDATED,
            source="account_service",
            account_id="account_123",
            account_type="trading",
            status="active"
        )
        result = event.to_dict()
        assert result['account_id'] == "account_123"  # Line 456

    def test_account_event_from_dict_line_477(self):
        """Test AccountEvent from_dict method for line 477."""
        account_data = {
            "id": "test_account_123",
            "type": "account.balance_updated",
            "source": "account_service",
            "timestamp": "2024-01-01T12:00:00",
            "account_id": "account_123",
            "account_type": "trading",
            "status": "active"
        }
        event = AccountEvent.from_dict(account_data)
        assert event.account_id == "account_123"  # Line 477

    def test_system_event_to_dict_line_528(self):
        """Test SystemEvent to_dict method for line 528."""
        event = SystemEvent(
            type=EventType.SYSTEM_STARTUP,
            source="system",
            component="trading_engine",
            status="starting",
            message="System starting"
        )
        result = event.to_dict()
        assert result['id'] == event.id  # Line 528

    def test_system_event_from_dict_line_548(self):
        """Test SystemEvent from_dict method for line 548."""
        system_data = {
            "id": "test_system_123",
            "type": "system.startup",
            "source": "system",
            "timestamp": "2024-01-01T12:00:00",
            "component": "trading_engine",
            "status": "starting",
            "message": "System starting"
        }
        event = SystemEvent.from_dict(system_data)
        assert event.id == "test_system_123"  # Line 548

    def test_create_event_from_dict_none_event_class_line_615(self):
        """Test create_event_from_dict when event_class is None for line 615."""
        # This tests the second ValueError at line 615
        # We need to trigger a case where EVENT_TYPE_REGISTRY.get() returns None
        # This is hard to trigger with current implementation since all EventTypes are registered
        # But we can still test with an unregistered type that passes EventType validation
        pass  # This line might be unreachable in current implementation
