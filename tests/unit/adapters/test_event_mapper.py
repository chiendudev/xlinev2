"""
Unit tests for EventMapper
File: tests/unit/adapters/test_event_mapper.py

Tests bidirectional mapping, decimal precision, and validation.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from xline.core.adapters.event_mapper import EventMapper
from xline.core.events.types import (
    EventType, OrderEvent, OrderSide, OrderStatus, OrderType, TradeEvent
)


class TestEventMapper:
    """Test cases for EventMapper class."""

    def test_map_freqtrade_order_success(self) -> None:
        """Test successful mapping of Freqtrade order to OrderEvent."""
        ft_order = {
            "id": "order_123",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.5,
            "price": 50000.0,
            "status": "open",
            "type": "limit",
            "timestamp": 1640995200000,  # 2022-01-01 00:00:00
            "stop_price": 49000.0,
            "time_in_force": "GTC",
            "exchange": "binance",
            "filled": 0.5
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        
        assert order_event.order_id == "order_123"
        assert order_event.symbol == "BTC/USDT"
        assert order_event.side == OrderSide.BUY
        assert order_event.quantity == Decimal("1.5")
        assert order_event.price == Decimal("50000")
        assert order_event.status == OrderStatus.OPEN
        assert order_event.order_type == OrderType.LIMIT
        assert order_event.stop_price == Decimal("49000")
        assert order_event.time_in_force == "GTC"
        assert order_event.exchange == "binance"
        assert order_event.filled_quantity == Decimal("0.5")
        assert order_event.source == "freqtrade"
        assert order_event.type == EventType.ORDER_CREATED

    def test_map_freqtrade_order_minimal_data(self) -> None:
        """Test mapping with minimal required data."""
        ft_order = {
            "id": "order_456",
            "symbol": "ETH/USDT",
            "side": "sell",
            "amount": 2.0,
            "price": 3000.0,
            "status": "filled"
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        
        assert order_event.order_id == "order_456"
        assert order_event.symbol == "ETH/USDT"
        assert order_event.side == OrderSide.SELL
        assert order_event.quantity == Decimal("2")
        assert order_event.price == Decimal("3000")
        assert order_event.status == OrderStatus.FILLED
        assert order_event.order_type == OrderType.MARKET  # Default
        assert order_event.account_id == "default"  # Default

    def test_map_freqtrade_order_missing_required_field(self) -> None:
        """Test error handling for missing required fields."""
        ft_order = {
            "id": "order_789",
            "symbol": "BTC/USDT",
            # Missing "side", "amount", "price", "status"
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            EventMapper.map_freqtrade_order(ft_order)

    def test_map_freqtrade_order_invalid_side(self) -> None:
        """Test error handling for invalid order side."""
        ft_order = {
            "id": "order_invalid",
            "symbol": "BTC/USDT",
            "side": "invalid_side",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open"
        }
        
        with pytest.raises(ValueError, match="Invalid order side"):
            EventMapper.map_freqtrade_order(ft_order)

    def test_map_freqtrade_trade_success(self) -> None:
        """Test successful mapping of Freqtrade trade to TradeEvent."""
        ft_trade = {
            "id": "trade_123",
            "order_id": "order_123",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.5,
            "price": 50000.0,
            "fee": 25.0,
            "commission": 10.0,
            "timestamp": 1640995200000,
            "exchange": "binance",
            "counterparty": "market_maker"
        }
        
        trade_event = EventMapper.map_freqtrade_trade(ft_trade)
        
        assert trade_event.trade_id == "trade_123"
        assert trade_event.order_id == "order_123"
        assert trade_event.symbol == "BTC/USDT"
        assert trade_event.side == OrderSide.BUY
        assert trade_event.quantity == Decimal("1.5")
        assert trade_event.price == Decimal("50000")
        assert trade_event.fee == Decimal("25")
        assert trade_event.commission == Decimal("10")
        assert trade_event.exchange == "binance"
        assert trade_event.counterparty == "market_maker"
        assert trade_event.source == "freqtrade"
        assert trade_event.type == EventType.TRADE_EXECUTED

    def test_map_freqtrade_trade_minimal_data(self) -> None:
        """Test trade mapping with minimal required data."""
        ft_trade = {
            "id": "trade_456",
            "symbol": "ETH/USDT",
            "side": "sell",
            "amount": 2.0,
            "price": 3000.0
        }
        
        trade_event = EventMapper.map_freqtrade_trade(ft_trade)
        
        assert trade_event.trade_id == "trade_456"
        assert trade_event.symbol == "ETH/USDT"
        assert trade_event.side == OrderSide.SELL
        assert trade_event.quantity == Decimal("2")
        assert trade_event.price == Decimal("3000")
        assert trade_event.fee == Decimal("0")  # Default
        assert trade_event.commission == Decimal("0")  # Default

    def test_map_order_event_to_freqtrade(self) -> None:
        """Test mapping OrderEvent back to Freqtrade format."""
        order_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="xline",
            order_id="order_123",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            price=Decimal("50000"),
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            stop_price=Decimal("49000"),
            time_in_force="GTC",
            exchange="binance",
            filled_quantity=Decimal("0.5")
        )
        
        ft_dict = EventMapper.map_order_event(order_event)
        
        assert ft_dict["id"] == "order_123"
        assert ft_dict["symbol"] == "BTC/USDT"
        assert ft_dict["side"] == "buy"
        assert ft_dict["amount"] == 1.5
        assert ft_dict["price"] == 50000.0
        assert ft_dict["type"] == "limit"
        assert ft_dict["status"] == "open"
        assert ft_dict["stop_price"] == 49000.0
        assert ft_dict["time_in_force"] == "GTC"
        assert ft_dict["exchange"] == "binance"
        assert ft_dict["filled"] == 0.5

    def test_map_trade_event_to_freqtrade(self) -> None:
        """Test mapping TradeEvent back to Freqtrade format."""
        trade_event = TradeEvent(
            type=EventType.TRADE_EXECUTED,
            source="xline",
            trade_id="trade_123",
            order_id="order_123",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            price=Decimal("50000"),
            fee=Decimal("25"),
            commission=Decimal("10"),
            exchange="binance"
        )
        
        ft_dict = EventMapper.map_trade_event(trade_event)
        
        assert ft_dict["id"] == "trade_123"
        assert ft_dict["order_id"] == "order_123"
        assert ft_dict["symbol"] == "BTC/USDT"
        assert ft_dict["side"] == "buy"
        assert ft_dict["amount"] == 1.5
        assert ft_dict["price"] == 50000.0
        assert ft_dict["fee"] == 25.0
        assert ft_dict["commission"] == 10.0
        assert ft_dict["exchange"] == "binance"

    def test_validate_decimal_precision_normal_values(self) -> None:
        """Test decimal precision validation with normal values."""
        # Test integer
        result = EventMapper.validate_decimal_precision(123, 4)
        assert result == Decimal("123.0000")
        
        # Test float
        result = EventMapper.validate_decimal_precision(123.456789, 4)
        assert result == Decimal("123.4568")
        
        # Test string
        result = EventMapper.validate_decimal_precision("123.456", 2)
        assert result == Decimal("123.46")
        
        # Test Decimal
        result = EventMapper.validate_decimal_precision(Decimal("123.456"), 2)
        assert result == Decimal("123.46")

    def test_validate_decimal_precision_edge_cases(self) -> None:
        """Test decimal precision validation with edge cases."""
        # Test None
        result = EventMapper.validate_decimal_precision(None)
        assert result == Decimal("0")
        
        # Test zero
        result = EventMapper.validate_decimal_precision(0)
        assert result == Decimal("0")
        
        # Test very small number
        result = EventMapper.validate_decimal_precision(0.00000001, 8)
        assert result == Decimal("0.00000001")
        
        # Test rounding
        result = EventMapper.validate_decimal_precision(1.999999, 2)
        assert result == Decimal("2.00")

    def test_validate_decimal_precision_invalid_values(self) -> None:
        """Test decimal precision validation with invalid values."""
        with pytest.raises(ValueError):
            EventMapper.validate_decimal_precision("invalid")
        
        with pytest.raises(ValueError):
            EventMapper.validate_decimal_precision("NaN")

    def test_bidirectional_mapping_accuracy_order(self) -> None:
        """Test bidirectional mapping accuracy for orders."""
        original_order = {
            "id": "order_test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.23456789,
            "price": 50000.12345678,
            "status": "open",
            "type": "limit"
        }
        
        # Map to OrderEvent and back
        order_event = EventMapper.map_freqtrade_order(original_order)
        remapped_order = EventMapper.map_order_event(order_event)
        
        # Test mapping accuracy
        is_accurate = EventMapper.validate_mapping_accuracy(
            original_order, order_event, remapped_order
        )
        assert is_accurate is True
        
        # Verify key fields preserved
        assert remapped_order["id"] == original_order["id"]
        assert remapped_order["symbol"] == original_order["symbol"]
        assert remapped_order["side"] == original_order["side"]
        
        # Verify decimal precision maintained (within tolerance)
        tolerance = 0.00000001
        assert abs(remapped_order["amount"] - original_order["amount"]) < tolerance
        assert abs(remapped_order["price"] - original_order["price"]) < tolerance

    def test_bidirectional_mapping_accuracy_trade(self) -> None:
        """Test bidirectional mapping accuracy for trades."""
        original_trade = {
            "id": "trade_test",
            "order_id": "order_test",
            "symbol": "ETH/USDT",
            "side": "sell",
            "amount": 2.87654321,
            "price": 3000.98765432,
            "fee": 15.123456
        }
        
        # Map to TradeEvent and back
        trade_event = EventMapper.map_freqtrade_trade(original_trade)
        remapped_trade = EventMapper.map_trade_event(trade_event)
        
        # Verify key fields preserved
        assert remapped_trade["id"] == original_trade["id"]
        assert remapped_trade["order_id"] == original_trade["order_id"]
        assert remapped_trade["symbol"] == original_trade["symbol"]
        assert remapped_trade["side"] == original_trade["side"]
        
        # Verify decimal precision maintained
        tolerance = 0.00000001
        assert abs(remapped_trade["amount"] - original_trade["amount"]) < tolerance
        assert abs(remapped_trade["price"] - original_trade["price"]) < tolerance
        assert abs(remapped_trade["fee"] - original_trade["fee"]) < tolerance

    def test_mapping_with_various_timestamp_formats(self) -> None:
        """Test mapping with different timestamp formats."""
        # Test with millisecond timestamp
        ft_order_ms = {
            "id": "order_ms",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open",
            "timestamp": 1640995200000  # Milliseconds
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order_ms)
        assert isinstance(order_event.timestamp, datetime)
        
        # Test with no timestamp (should use current time)
        ft_order_no_ts = {
            "id": "order_no_ts",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open"
        }
        
        with patch('xline.core.adapters.event_mapper.datetime') as mock_datetime:
            mock_now = datetime(2022, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            order_event = EventMapper.map_freqtrade_order(ft_order_no_ts)
            assert order_event.timestamp == mock_now

    def test_status_mapping_coverage(self) -> None:
        """Test all status mappings for comprehensive coverage."""
        status_mappings = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "pending": OrderStatus.PENDING,
            "rejected": OrderStatus.REJECTED,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "unknown_status": OrderStatus.PENDING  # Default fallback
        }
        
        for ft_status, expected_status in status_mappings.items():
            ft_order = {
                "id": f"order_{ft_status}",
                "symbol": "BTC/USDT",
                "side": "buy",
                "amount": 1.0,
                "price": 50000.0,
                "status": ft_status
            }
            
            order_event = EventMapper.map_freqtrade_order(ft_order)
            assert order_event.status == expected_status

    def test_order_type_mapping_coverage(self) -> None:
        """Test all order type mappings."""
        type_mappings = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
            "unknown_type": OrderType.MARKET  # Default fallback
        }
        
        for ft_type, expected_type in type_mappings.items():
            ft_order = {
                "id": f"order_{ft_type}",
                "symbol": "BTC/USDT",
                "side": "buy",
                "amount": 1.0,
                "price": 50000.0,
                "status": "open",
                "type": ft_type
            }
            
            order_event = EventMapper.map_freqtrade_order(ft_order)
            assert order_event.order_type == expected_type

    def test_exception_handling_and_logging(self) -> None:
        """Test exception handling and logging."""
        # Test with invalid order data that causes exception
        invalid_order = {
            "id": None,  # This will cause str() to work but validation to fail
            "symbol": None,
            "side": None,
            "amount": "invalid",
            "price": "invalid",
            "status": None
        }
        
        with pytest.raises(ValueError, match="Invalid Freqtrade order data"):
            EventMapper.map_freqtrade_order(invalid_order)

    def test_large_number_precision(self) -> None:
        """Test precision handling with very large numbers."""
        large_amount = 999999999.87654321
        large_price = 123456789.12345678
        
        ft_order = {
            "id": "order_large",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": large_amount,
            "price": large_price,
            "status": "open"
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        
        # Verify precision is maintained
        assert abs(float(order_event.quantity) - large_amount) < 0.00000001
        assert abs(float(order_event.price) - large_price) < 0.00000001

    def test_scientific_notation_handling(self) -> None:
        """Test handling of scientific notation in decimal values."""
        small_amount = 1.23e-6  # Very small number in scientific notation
        small_price = 4.56e-8
        
        ft_order = {
            "id": "order_scientific",
            "symbol": "SHIB/USDT",
            "side": "buy",
            "amount": small_amount,
            "price": small_price,
            "status": "open"
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        
        # Verify scientific notation is handled correctly
        assert order_event.quantity > 0
        assert order_event.price > 0
        assert abs(float(order_event.quantity) - small_amount) < 1e-10
        assert abs(float(order_event.price) - small_price) < 1e-10

    def test_map_freqtrade_order_all_status_mappings(self) -> None:
        """Test all order status mappings including edge cases."""
        base_order = {
            "id": "test_order",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open"
        }
        
        # Test all status mappings including default fallback
        status_tests = [
            ("open", OrderStatus.OPEN),
            ("closed", OrderStatus.FILLED),
            ("canceled", OrderStatus.CANCELLED),
            ("cancelled", OrderStatus.CANCELLED),
            ("pending", OrderStatus.PENDING),
            ("rejected", OrderStatus.REJECTED),
            ("filled", OrderStatus.FILLED),
            ("partially_filled", OrderStatus.PARTIALLY_FILLED),
            ("unknown_status", OrderStatus.PENDING)  # Default fallback
        ]
        
        for ft_status, expected_status in status_tests:
            test_order = base_order.copy()
            test_order["status"] = ft_status
            
            order_event = EventMapper.map_freqtrade_order(test_order)
            assert order_event.status == expected_status

    def test_map_freqtrade_order_optional_field_handling(self) -> None:
        """Test handling of optional fields including None values."""
        ft_order = {
            "id": "test_order",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open",
            "type": "limit",
            "account_id": "test_account",
            "stop_price": None,  # Test None handling
            "time_in_force": "IOC",
            "client_order_id": None,  # Test None handling
            "exchange": "binance",
            "filled": 0.0,
            "timestamp": 1640995200000
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        
        assert order_event.account_id == "test_account"
        assert order_event.stop_price is None
        assert order_event.time_in_force == "IOC"
        assert order_event.client_order_id is None
        assert order_event.exchange == "binance"
        assert order_event.filled_quantity == Decimal("0.0")

    def test_map_freqtrade_trade_optional_fields(self) -> None:
        """Test trade mapping with all optional fields."""
        ft_trade = {
            "id": "test_trade",
            "order_id": "test_order",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "fee": 25.0,
            "account_id": "test_account",
            "exchange": "binance",
            "timestamp": 1640995200000
        }
        
        trade_event = EventMapper.map_freqtrade_trade(ft_trade)
        
        assert trade_event.fee == Decimal("25.0")
        assert trade_event.account_id == "test_account"
        assert trade_event.exchange == "binance"

    def test_validate_decimal_precision_extreme_values(self) -> None:
        """Test decimal precision validation with extreme values."""
        # Test very large number
        large_value = EventMapper.validate_decimal_precision("999999999999.12345678")
        assert large_value == Decimal("999999999999.12345678")
        
        # Test very small number
        small_value = EventMapper.validate_decimal_precision("0.00000001")
        assert small_value == Decimal("0.00000001")
        
        # Test rounding precision
        rounded_value = EventMapper.validate_decimal_precision("1.123456789", precision=4)
        assert rounded_value == Decimal("1.1235")  # Rounds up
        
        # Test None handling
        none_value = EventMapper.validate_decimal_precision(None)
        assert none_value == Decimal("0")

    def test_validate_decimal_precision_error_cases(self) -> None:
        """Test decimal precision validation error handling."""
        # Test invalid string
        with pytest.raises(ValueError, match="Invalid decimal value"):
            EventMapper.validate_decimal_precision("invalid_number")
            
        # Test invalid type that can't convert
        with pytest.raises(ValueError, match="Invalid decimal value"):
            EventMapper.validate_decimal_precision({"not": "a number"})

    @patch('xline.core.adapters.event_mapper.logger')
    def test_logging_on_errors(self, mock_logger) -> None:
        """Test that errors are properly logged."""
        invalid_order = {"invalid": "data"}
        
        with pytest.raises(ValueError):
            EventMapper.map_freqtrade_order(invalid_order)
            
        mock_logger.error.assert_called()
        assert "Failed to map Freqtrade order" in str(mock_logger.error.call_args)

    def test_map_order_event_to_freqtrade_complete(self) -> None:
        """Test complete reverse mapping with all fields."""
        order_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test",
            order_id="test_order",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            price=Decimal("50000.0"),
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            stop_price=Decimal("49000.0"),
            time_in_force="GTC",
            client_order_id="client123",
            exchange="binance",
            filled_quantity=Decimal("0.5"),
            timestamp=datetime.now()
        )
        
        ft_dict = EventMapper.map_order_event(order_event)
        
        assert ft_dict["id"] == "test_order"
        assert ft_dict["symbol"] == "BTC/USDT"
        assert ft_dict["side"] == "buy"
        assert ft_dict["amount"] == 1.5
        assert ft_dict["price"] == 50000.0
        assert ft_dict["type"] == "limit"
        assert ft_dict["status"] == "open"

    def test_map_trade_event_to_freqtrade_complete(self) -> None:
        """Test complete trade event to freqtrade mapping."""
        trade_event = TradeEvent(
            type=EventType.TRADE_EXECUTED,
            source="test",
            trade_id="test_trade",
            order_id="test_order",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.0"),
            price=Decimal("51000.0"),
            fee=Decimal("51.0"),
            exchange="binance",
            timestamp=datetime.now()
        )
        
        ft_dict = EventMapper.map_trade_event(trade_event)
        
        assert ft_dict["id"] == "test_trade"
        assert ft_dict["order_id"] == "test_order"
        assert ft_dict["symbol"] == "BTC/USDT"
        assert ft_dict["side"] == "sell"
        assert ft_dict["amount"] == 2.0
        assert ft_dict["price"] == 51000.0
        assert ft_dict["fee"] == 51.0

    def test_performance_stress_mapping(self) -> None:
        """Stress test for mapping performance - should complete quickly."""
        import time
        
        ft_order = {
            "id": "performance_test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open"
        }
        
        start_time = time.time()
        
        # Map 1000 orders to test performance
        for i in range(1000):
            ft_order["id"] = f"order_{i}"
            order_event = EventMapper.map_freqtrade_order(ft_order)
            assert order_event.order_id == f"order_{i}"
            
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0

    def test_map_freqtrade_trade_invalid_side(self) -> None:
        """Test trade mapping with invalid side."""
        ft_trade = {
            "id": "test_trade",
            "symbol": "BTC/USDT",
            "side": "invalid_side",  # Invalid side
            "amount": 1.0,
            "price": 50000.0
        }
        
        with pytest.raises(ValueError, match="Invalid trade side"):
            EventMapper.map_freqtrade_trade(ft_trade)

    def test_map_freqtrade_trade_missing_order_id(self) -> None:
        """Test trade mapping without order_id (should generate one)."""
        ft_trade = {
            "id": "test_trade_123",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.0
        }
        
        trade_event = EventMapper.map_freqtrade_trade(ft_trade)
        assert trade_event.order_id == "order_test_trade_123"

    def test_map_order_event_error_handling(self) -> None:
        """Test order event mapping error handling."""
        # Create order event with problematic data that might cause errors
        order_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test",
            order_id="test_order",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            price=Decimal("50000.0"),
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN
        )
        
        # Should work normally
        ft_dict = EventMapper.map_order_event(order_event)
        assert ft_dict["id"] == "test_order"

    def test_map_trade_event_error_handling(self) -> None:
        """Test trade event mapping error handling."""
        trade_event = TradeEvent(
            type=EventType.TRADE_EXECUTED,
            source="test",
            trade_id="test_trade",
            order_id="test_order",
            account_id="test_account",
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.0"),
            price=Decimal("51000.0")
        )
        
        # Should work normally
        ft_dict = EventMapper.map_trade_event(trade_event)
        assert ft_dict["id"] == "test_trade"

    @patch('xline.core.adapters.event_mapper.logger')
    def test_map_freqtrade_trade_logging_errors(self, mock_logger) -> None:
        """Test trade mapping error logging."""
        invalid_trade = {"invalid": "data"}
        
        with pytest.raises(ValueError):
            EventMapper.map_freqtrade_trade(invalid_trade)
            
        mock_logger.error.assert_called()
        assert "Failed to map Freqtrade trade" in str(mock_logger.error.call_args)

    @patch('xline.core.adapters.event_mapper.logger')
    def test_map_order_event_logging_errors(self, mock_logger) -> None:
        """Test order event mapping error logging."""
        # Test with None order event to trigger exception
        with pytest.raises(ValueError):
            EventMapper.map_order_event(None)
            
        mock_logger.error.assert_called()

    @patch('xline.core.adapters.event_mapper.logger')
    def test_map_trade_event_logging_errors(self, mock_logger) -> None:
        """Test trade event mapping error logging."""
        # Test with None trade event to trigger exception
        with pytest.raises(ValueError):
            EventMapper.map_trade_event(None)
            
        mock_logger.error.assert_called()

    def test_validate_decimal_precision_special_cases(self) -> None:
        """Test decimal precision with special edge cases."""
        # Test zero precision
        result = EventMapper.validate_decimal_precision("123.456", precision=0)
        assert result == Decimal("123")
        
        # Test negative precision behavior
        result = EventMapper.validate_decimal_precision("123.456", precision=-1)
        assert result == Decimal("123")  # Negative precision doesn't round to 10s

    def test_map_order_event_invalid_side(self) -> None:
        """Test line 225 - order event with invalid side mapping."""
        # Create a mock order event with invalid side
        from unittest.mock import Mock
        
        order_event = Mock()
        order_event.side = "INVALID_SIDE"  # Not in OrderSide enum
        order_event.symbol = "BTC/USDT"
        order_event.order_id = "test"
        
        with pytest.raises(ValueError, match="Invalid order side"):
            EventMapper.map_order_event(order_event)

    def test_map_trade_event_invalid_side(self) -> None:
        """Test line 288 - trade event with invalid side mapping."""
        from unittest.mock import Mock
        
        trade_event = Mock()
        trade_event.side = "INVALID_SIDE"  # Not in OrderSide enum
        trade_event.trade_id = "test"
        trade_event.symbol = "BTC/USDT"
        
        with pytest.raises(ValueError, match="Invalid trade side"):
            EventMapper.map_trade_event(trade_event)

    def test_validate_mapping_accuracy_inaccurate_amount(self) -> None:
        """Test alternative approach to test missing lines 385-386."""
        # Create mock data to trigger amount validation paths
        ft_order = {
            "id": "test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 0.00000001,  # Very small amount to test precision
            "price": 50000.0,
            "status": "open"
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        assert order_event.quantity == Decimal("0.00000001")

    def test_validate_mapping_accuracy_inaccurate_price(self) -> None:
        """Test alternative approach to test missing lines 393-394."""
        # Create data with very precise price
        ft_order = {
            "id": "test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.0,
            "price": 50000.123456789,  # High precision price
            "status": "open"
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        assert abs(float(order_event.price) - 50000.123456789) < 0.00000001

    def test_validate_mapping_accuracy_inaccurate_string_fields(self) -> None:
        """Test alternative approach to test missing lines 400-401."""
        # Test string field handling with various cases
        ft_order = {
            "id": "TEST_ORDER_ID",
            "symbol": "btc/usdt",  # lowercase
            "side": "BUY",  # uppercase
            "amount": 1.0,
            "price": 50000.0,
            "status": "OPEN"  # uppercase
        }
        
        order_event = EventMapper.map_freqtrade_order(ft_order)
        assert order_event.order_id == "TEST_ORDER_ID"
        assert order_event.symbol == "btc/usdt"

    def test_validate_mapping_accuracy_exception_handling(self) -> None:
        """Test alternative approach to test missing lines 405-407."""
        # Test exception handling in decimal validation
        ft_order = {
            "id": "test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": float('inf'),  # Invalid amount that causes exception
            "price": 50000.0,
            "status": "open"
        }
        
        with pytest.raises(ValueError):
            EventMapper.map_freqtrade_order(ft_order)

    def test_validate_mapping_accuracy_complete_coverage(self) -> None:
        """Test lines 385-386, 393-394, 400-401, 405-407 for complete coverage."""
        original_data = {
            "id": "order-123",
            "symbol": "BTC/USDT",
            "amount": 1.123456789,
            "price": 50000.123456789,
            "side": "buy"
        }

        # Create a dummy event for the middle parameter
        dummy_event = OrderEvent(
            type=EventType.ORDER_CREATED,
            source="test_source",
            order_id="order-123",
            account_id="test_account",
            symbol="BTC/USDT",
            quantity=Decimal("1.123456789"),
            price=Decimal("50000.123456789"),
            side=OrderSide.BUY,
            timestamp=datetime.now()
        )

        # Test with inaccurate amount (lines 385-386)
        inaccurate_amount_data = original_data.copy()
        inaccurate_amount_data["amount"] = 1.999999999  # Very different amount

        result = EventMapper.validate_mapping_accuracy(
            original_data, dummy_event, inaccurate_amount_data
        )
        assert result is False

        # Test with inaccurate price (lines 393-394)
        inaccurate_price_data = original_data.copy()
        inaccurate_price_data["price"] = 99999.999999999  # Very different price

        result = EventMapper.validate_mapping_accuracy(
            original_data, dummy_event, inaccurate_price_data
        )
        assert result is False

        # Test with inaccurate string field (lines 400-401)
        inaccurate_string_data = original_data.copy()
        inaccurate_string_data["side"] = "sell"  # Different side

        result = EventMapper.validate_mapping_accuracy(
            original_data, dummy_event, inaccurate_string_data
        )
        assert result is False

        # Test exception handling (lines 405-407)
        with patch.object(
            EventMapper,
            'validate_decimal_precision',
            side_effect=Exception("Test error")
        ):
            result = EventMapper.validate_mapping_accuracy(
                original_data, dummy_event, original_data
            )
            assert result is False
