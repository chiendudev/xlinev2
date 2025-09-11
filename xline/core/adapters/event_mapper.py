"""
Event Mapper for Xline Trading System
File: xline/core/adapters/event_mapper.py

Bidirectional translation between Freqtrade and Xline event formats
with precise decimal handling for financial data.
"""

import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from xline.core.events.types import (
    Event, EventType, OrderEvent, OrderSide, OrderStatus, OrderType, TradeEvent
)

logger = logging.getLogger(__name__)


class EventMapper:
    """
    Bidirectional translation between Freqtrade and Xline event formats.
    
    Example usage:
        order_event = EventMapper.map_freqtrade_order(ft_order_dict)
        ft_dict = EventMapper.map_order_event(order_event)
    """
    
    @staticmethod
    def map_freqtrade_order(ft_order: dict[str, Any]) -> OrderEvent:
        """
        Convert Freqtrade order to Xline OrderEvent.
        
        Args:
            ft_order: Dictionary containing Freqtrade order data
            
        Returns:
            OrderEvent: Xline order event with validated data
            
        Raises:
            ValueError: If order data is invalid or missing required fields
            
        Example:
            >>> ft_order = {
            ...     "id": "order123",
            ...     "symbol": "BTC/USDT",
            ...     "side": "buy",
            ...     "amount": 1.5,
            ...     "price": 50000.0,
            ...     "status": "open"
            ... }
            >>> order_event = EventMapper.map_freqtrade_order(ft_order)
            >>> assert order_event.order_id == "order123"
        """
        try:
            # Validate required fields
            required_fields = ["id", "symbol", "side", "amount", "price", "status"]
            for field in required_fields:
                if field not in ft_order:
                    raise ValueError(f"Missing required field: {field}")
            
            # Map order side
            side_mapping = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}
            side = side_mapping.get(str(ft_order["side"]).lower())
            if side is None:
                raise ValueError(f"Invalid order side: {ft_order['side']}")
            
            # Map order status
            status_mapping = {
                "open": OrderStatus.OPEN,
                "closed": OrderStatus.FILLED,
                "canceled": OrderStatus.CANCELLED,
                "cancelled": OrderStatus.CANCELLED,
                "pending": OrderStatus.PENDING,
                "rejected": OrderStatus.REJECTED,
                "filled": OrderStatus.FILLED,
                "partially_filled": OrderStatus.PARTIALLY_FILLED
            }
            status = status_mapping.get(str(ft_order["status"]).lower())
            if status is None:
                status = OrderStatus.PENDING
            
            # Map order type
            order_type_mapping = {
                "market": OrderType.MARKET,
                "limit": OrderType.LIMIT,
                "stop": OrderType.STOP,
                "stop_limit": OrderType.STOP_LIMIT
            }
            order_type = order_type_mapping.get(
                str(ft_order.get("type", "market")).lower(), 
                OrderType.MARKET
            )
            
            return OrderEvent(
                type=EventType.ORDER_CREATED,
                source="freqtrade",
                order_id=str(ft_order["id"]),
                account_id=str(ft_order.get("account_id", "default")),
                symbol=str(ft_order["symbol"]),
                side=side,
                quantity=EventMapper.validate_decimal_precision(ft_order["amount"]),
                price=EventMapper.validate_decimal_precision(ft_order["price"]),
                order_type=order_type,
                status=status,
                stop_price=EventMapper.validate_decimal_precision(
                    ft_order.get("stop_price")
                ) if ft_order.get("stop_price") else None,
                time_in_force=str(ft_order.get("time_in_force", "GTC")),
                client_order_id=str(ft_order.get("client_order_id")) if ft_order.get("client_order_id") else None,
                exchange=str(ft_order.get("exchange")) if ft_order.get("exchange") else None,
                filled_quantity=EventMapper.validate_decimal_precision(
                    ft_order.get("filled", 0)
                ),
                timestamp=datetime.fromtimestamp(
                    ft_order.get("timestamp", datetime.now().timestamp()) / 1000
                ) if isinstance(ft_order.get("timestamp"), int | float) else datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to map Freqtrade order: {e}")
            raise ValueError(f"Invalid Freqtrade order data: {e}")
            
    @staticmethod
    def map_freqtrade_trade(ft_trade: dict[str, Any]) -> TradeEvent:
        """
        Convert Freqtrade trade to Xline TradeEvent.
        
        Args:
            ft_trade: Dictionary containing Freqtrade trade data
            
        Returns:
            TradeEvent: Xline trade event with validated data
            
        Raises:
            ValueError: If trade data is invalid or missing required fields
            
        Example:
            >>> ft_trade = {
            ...     "id": "trade123",
            ...     "order_id": "order123", 
            ...     "symbol": "BTC/USDT",
            ...     "side": "buy",
            ...     "amount": 1.5,
            ...     "price": 50000.0,
            ...     "fee": 25.0
            ... }
            >>> trade_event = EventMapper.map_freqtrade_trade(ft_trade)
            >>> assert trade_event.trade_id == "trade123"
        """
        try:
            # Validate required fields
            required_fields = ["id", "symbol", "side", "amount", "price"]
            for field in required_fields:
                if field not in ft_trade:
                    raise ValueError(f"Missing required field: {field}")
            
            # Map trade side
            side_mapping = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}
            side = side_mapping.get(str(ft_trade["side"]).lower())
            if side is None:
                raise ValueError(f"Invalid trade side: {ft_trade['side']}")
                
            return TradeEvent(
                type=EventType.TRADE_EXECUTED,
                source="freqtrade",
                trade_id=str(ft_trade["id"]),
                order_id=str(ft_trade.get("order_id", f"order_{ft_trade['id']}")),
                account_id=str(ft_trade.get("account_id", "default")),
                symbol=str(ft_trade["symbol"]),
                side=side,
                quantity=EventMapper.validate_decimal_precision(ft_trade["amount"]),
                price=EventMapper.validate_decimal_precision(ft_trade["price"]),
                fee=EventMapper.validate_decimal_precision(ft_trade.get("fee", 0)),
                commission=EventMapper.validate_decimal_precision(
                    ft_trade.get("commission", 0)
                ),
                exchange=str(ft_trade.get("exchange")) if ft_trade.get("exchange") else None,
                counterparty=(
                    str(ft_trade.get("counterparty"))
                    if ft_trade.get("counterparty") else None
                ),
                timestamp=datetime.fromtimestamp(
                    ft_trade.get("timestamp", datetime.now().timestamp()) / 1000
                ) if isinstance(ft_trade.get("timestamp"), int | float) else datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Failed to map Freqtrade trade: {e}")
            raise ValueError(f"Invalid Freqtrade trade data: {e}")
            
    @staticmethod
    def map_order_event(order_event: OrderEvent) -> dict[str, Any]:
        """
        Convert Xline OrderEvent to Freqtrade format.
        
        Args:
            order_event: Xline OrderEvent instance
            
        Returns:
            Dict[str, Any]: Freqtrade-compatible order dictionary
            
        Raises:
            ValueError: If order event data is invalid
            
        Example:
            >>> order_event = OrderEvent(
            ...     type=EventType.ORDER_CREATED,
            ...     source="xline",
            ...     order_id="order123",
            ...     symbol="BTC/USDT",
            ...     side=OrderSide.BUY,
            ...     quantity=Decimal("1.5"),
            ...     price=Decimal("50000")
            ... )
            >>> ft_dict = EventMapper.map_order_event(order_event)
            >>> assert ft_dict["id"] == "order123"
        """
        try:
            # Map order side back to Freqtrade format
            side_mapping = {OrderSide.BUY: "buy", OrderSide.SELL: "sell"}
            side = side_mapping.get(order_event.side)
            if side is None:
                raise ValueError(f"Invalid order side: {order_event.side}")
            
            # Map order status back to Freqtrade format
            status_mapping = {
                OrderStatus.OPEN: "open",
                OrderStatus.FILLED: "closed",
                OrderStatus.CANCELLED: "canceled",
                OrderStatus.PENDING: "pending",
                OrderStatus.REJECTED: "rejected",
                OrderStatus.PARTIALLY_FILLED: "partially_filled"
            }
            status = status_mapping.get(order_event.status, "pending")
            
            # Map order type back to Freqtrade format
            type_mapping = {
                OrderType.MARKET: "market",
                OrderType.LIMIT: "limit", 
                OrderType.STOP: "stop",
                OrderType.STOP_LIMIT: "stop_limit"
            }
            order_type = type_mapping.get(order_event.order_type, "market")
            
            return {
                "id": order_event.order_id,
                "symbol": order_event.symbol,
                "side": side,
                "amount": float(order_event.quantity),
                "price": float(order_event.price),
                "type": order_type,
                "status": status,
                "timestamp": int(order_event.timestamp.timestamp() * 1000),
                "stop_price": float(order_event.stop_price) if order_event.stop_price else None,
                "time_in_force": order_event.time_in_force,
                "client_order_id": order_event.client_order_id,
                "exchange": order_event.exchange,
                "filled": float(order_event.filled_quantity),
                "remaining": float(order_event.remaining_quantity) if order_event.remaining_quantity else None,
                "average_price": float(order_event.average_fill_price) if order_event.average_fill_price else None
            }
            
        except Exception as e:
            logger.error(f"Failed to map order event: {e}")
            raise ValueError(f"Invalid OrderEvent data: {e}")
            
    @staticmethod
    def map_trade_event(trade_event: TradeEvent) -> dict[str, Any]:
        """
        Convert Xline TradeEvent to Freqtrade format.
        
        Args:
            trade_event: Xline TradeEvent instance
            
        Returns:
            Dict[str, Any]: Freqtrade-compatible trade dictionary
            
        Raises:
            ValueError: If trade event data is invalid
        """
        try:
            # Map trade side back to Freqtrade format
            side_mapping = {OrderSide.BUY: "buy", OrderSide.SELL: "sell"}
            side = side_mapping.get(trade_event.side)
            if side is None:
                raise ValueError(f"Invalid trade side: {trade_event.side}")
                
            return {
                "id": trade_event.trade_id,
                "order_id": trade_event.order_id,
                "symbol": trade_event.symbol,
                "side": side,
                "amount": float(trade_event.quantity),
                "price": float(trade_event.price),
                "fee": float(trade_event.fee),
                "commission": float(trade_event.commission),
                "timestamp": int(trade_event.timestamp.timestamp() * 1000),
                "exchange": trade_event.exchange,
                "counterparty": trade_event.counterparty
            }
            
        except Exception as e:
            logger.error(f"Failed to map trade event: {e}")
            raise ValueError(f"Invalid TradeEvent data: {e}")
            
    @staticmethod
    def validate_decimal_precision(value: Any, precision: int = 8) -> Decimal:
        """
        Validate and convert to Decimal with specified precision.
        
        Args:
            value: Value to convert to Decimal
            precision: Number of decimal places to maintain
            
        Returns:
            Decimal: Validated decimal value with specified precision
            
        Raises:
            ValueError: If value cannot be converted to valid decimal
            
        Example:
            >>> result = EventMapper.validate_decimal_precision(123.456789, 4)
            >>> assert result == Decimal("123.4568")
        """
        try:
            if value is None:
                return Decimal("0")
                
            # Convert to Decimal directly to preserve precision
            if isinstance(value, int | float):
                # For scientific notation, use string conversion to preserve precision
                if isinstance(value, float) and (abs(value) < 1e-10 or abs(value) > 1e10):
                    # Use higher precision for very small or large numbers
                    decimal_value = Decimal(f"{value:.15e}")
                else:
                    decimal_value = Decimal(str(value))
            else:
                decimal_value = Decimal(str(value))
            
            # For very small numbers, preserve more precision
            if abs(decimal_value) < Decimal("1e-6"):
                working_precision = max(precision, 15)
            else:
                working_precision = precision
            
            # Quantize to specified precision with proper rounding
            quantized = decimal_value.quantize(
                Decimal(10) ** -working_precision,
                rounding=ROUND_HALF_UP
            )
            return quantized
            
        except Exception as e:
            logger.error(f"Failed to validate decimal precision for value {value}: {e}")
            raise ValueError(f"Invalid decimal value: {value}")
    
    @staticmethod
    def validate_mapping_accuracy(
        original_data: dict[str, Any],
        mapped_event: Event,
        remapped_data: dict[str, Any]
    ) -> bool:
        """
        Validate bidirectional mapping accuracy for testing.
        
        Args:
            original_data: Original Freqtrade data
            mapped_event: Mapped Xline event
            remapped_data: Remapped Freqtrade data
            
        Returns:
            bool: True if mapping is accurate within tolerance
        """
        try:
            # Check key fields for consistency
            tolerance = Decimal("0.00000001")  # 8 decimal places
            
            # Validate amounts with decimal precision
            original_amount = EventMapper.validate_decimal_precision(original_data.get("amount", 0))
            remapped_amount = EventMapper.validate_decimal_precision(remapped_data.get("amount", 0))
            
            if abs(original_amount - remapped_amount) > tolerance:
                logger.warning(f"Amount mapping inaccuracy: {original_amount} != {remapped_amount}")
                return False
                
            # Validate prices with decimal precision
            original_price = EventMapper.validate_decimal_precision(original_data.get("price", 0))
            remapped_price = EventMapper.validate_decimal_precision(remapped_data.get("price", 0))
            
            if abs(original_price - remapped_price) > tolerance:
                logger.warning(f"Price mapping inaccuracy: {original_price} != {remapped_price}")
                return False
                
            # Check string fields
            string_fields = ["id", "symbol", "side"]
            for field in string_fields:
                if str(original_data.get(field, "")).lower() != str(remapped_data.get(field, "")).lower():
                    logger.warning(f"String field mapping inaccuracy: {field}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate mapping accuracy: {e}")
            return False
