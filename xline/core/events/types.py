"""
Event Type Definitions for Xline Trading System
File: xline/core/events/types.py

Type-safe event     # Optional fields with defaults  
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    version: str = "1.0.0" with proper serialization support.
Compliant with AI_AGENT_IMPLEMENTATION_ROADMAP.md specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import json
from abc import ABC, abstractmethod


class EventType(str, Enum):
    """Event type enumeration for type-safe event handling"""
    
    # Trading Events
    ORDER_CREATED = "order.created"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"
    ORDER_MODIFIED = "order.modified"
    TRADE_EXECUTED = "trade.executed"
    
    # Market Data Events
    PRICE_TICK = "market_data.price_tick"
    MARKET_DEPTH = "market_data.depth"
    
    # Risk Events
    RISK_LIMIT_BREACHED = "risk.limit_breached"
    POSITION_LIMIT_EXCEEDED = "position.limit_exceeded"
    RISK_DRAWDOWN_ALERT = "risk.drawdown_alert"
    RISK_MARGIN_CALL = "risk.margin_call"
    RISK_STOP_LOSS_TRIGGERED = "risk.stop_loss_triggered"
    
    # Account Events
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    ACCOUNT_BALANCE_UPDATED = "account.balance_updated"
    ACCOUNT_SUSPENDED = "account.suspended"
    ACCOUNT_ACTIVATED = "account.activated"
    
    # System Events
    STRATEGY_DEPLOYED = "strategy.deployed"
    STRATEGY_STARTED = "strategy.started"
    STRATEGY_STOPPED = "strategy.stopped"
    STRATEGY_PAUSED = "strategy.paused"
    STRATEGY_ERROR = "strategy.error"
    EMERGENCY_STOP = "emergency.stop"
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    
    def __str__(self) -> str:
        """Return the string value for compatibility"""
        return self.value


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class RiskSeverity(str, Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event(ABC):
    """
    Base event class for all events in the system.
    
    All events must inherit from this class and provide proper type hints.
    Includes correlation tracking and versioning support.
    """
    
    # All required fields come first
    type: EventType
    source: str
    
    # Optional fields with defaults come last  
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    version: str = "1.0.0"
    
    def __post_init__(self) -> None:
        """Post-initialization validation"""
        if not self.source:
            raise ValueError("Event source cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
    
    def _generate_timestamp(self) -> datetime:
        """Generate a new timestamp for event reuse"""
        return datetime.utcnow()
    
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        pass


@dataclass
class OrderEvent(Event):
    """
    Trading order event with precise decimal handling.
    
    Represents all order lifecycle events including creation,
    modification, execution, and cancellation.
    """
    
    # All fields must have defaults when parent has fields with defaults
    order_id: str = ""
    account_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    price: Decimal = field(default_factory=lambda: Decimal('0'))
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    
    # Optional fields for additional order details
    stop_price: Decimal | None = None
    time_in_force: str = "GTC"  # Good Till Cancelled
    client_order_id: str | None = None
    exchange: str | None = None
    filled_quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    remaining_quantity: Decimal | None = None
    average_fill_price: Decimal | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for OrderEvent"""
        super().__post_init__()
        
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        
        # Calculate remaining quantity if not provided
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity - self.filled_quantity
    
    def __hash__(self) -> int:
        """Make OrderEvent hashable using event ID"""
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        """Compare events by ID"""
        if not isinstance(other, OrderEvent):
            return False
        return self.id == other.id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert OrderEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'order_id': self.order_id,
            'account_id': self.account_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'price': str(self.price),
            'order_type': self.order_type.value,
            'status': self.status.value,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'time_in_force': self.time_in_force,
            'client_order_id': self.client_order_id,
            'exchange': self.exchange,
            'filled_quantity': str(self.filled_quantity),
            'remaining_quantity': str(self.remaining_quantity) if self.remaining_quantity else None,
            'average_fill_price': str(self.average_fill_price) if self.average_fill_price else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OrderEvent':
        """Create OrderEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            order_id=data['order_id'],
            account_id=data['account_id'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            quantity=Decimal(data['quantity']),
            price=Decimal(data['price']),
            order_type=OrderType(data['order_type']),
            status=OrderStatus(data['status']),
            stop_price=Decimal(data['stop_price']) if data.get('stop_price') else None,
            time_in_force=data.get('time_in_force', 'GTC'),
            client_order_id=data.get('client_order_id'),
            exchange=data.get('exchange'),
            filled_quantity=Decimal(data.get('filled_quantity', '0')),
            remaining_quantity=Decimal(data['remaining_quantity']) if data.get('remaining_quantity') else None,
            average_fill_price=Decimal(data['average_fill_price']) if data.get('average_fill_price') else None,
        )


@dataclass
class TradeEvent(Event):
    """
    Trade execution event with commission tracking.
    
    Represents completed trade executions with precise
    financial calculations and fee tracking.
    """
    
    trade_id: str = ""
    order_id: str = ""
    account_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    price: Decimal = field(default_factory=lambda: Decimal('0'))
    fee: Decimal = field(default_factory=lambda: Decimal('0'))
    commission: Decimal = field(default_factory=lambda: Decimal('0'))
    
    # Additional trade details
    exchange: str | None = None
    trade_time: datetime | None = None
    settlement_date: datetime | None = None
    counterparty: str | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for TradeEvent"""
        super().__post_init__()
        
        if not self.trade_id:
            raise ValueError("Trade ID cannot be empty")
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.fee < 0:
            raise ValueError("Fee cannot be negative")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")
        
        # Set trade time to event timestamp if not provided
        if self.trade_time is None:
            self.trade_time = self.timestamp
    
    def to_dict(self) -> dict[str, Any]:
        """Convert TradeEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'account_id': self.account_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'price': str(self.price),
            'fee': str(self.fee),
            'commission': str(self.commission),
            'exchange': self.exchange,
            'trade_time': self.trade_time.isoformat() if self.trade_time else None,
            'settlement_date': self.settlement_date.isoformat() if self.settlement_date else None,
            'counterparty': self.counterparty,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TradeEvent':
        """Create TradeEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            trade_id=data['trade_id'],
            order_id=data['order_id'],
            account_id=data['account_id'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            quantity=Decimal(data['quantity']),
            price=Decimal(data['price']),
            fee=Decimal(data['fee']),
            commission=Decimal(data['commission']),
            exchange=data.get('exchange'),
            trade_time=datetime.fromisoformat(data['trade_time']) if data.get('trade_time') else None,
            settlement_date=datetime.fromisoformat(data['settlement_date']) if data.get('settlement_date') else None,
            counterparty=data.get('counterparty'),
        )


@dataclass
class RiskEvent(Event):
    """
    Risk management event for monitoring and alerting.
    
    Tracks risk rule violations, threshold breaches,
    and risk management actions.
    """
    
    account_id: str = ""
    rule_type: str = ""
    severity: RiskSeverity = RiskSeverity.LOW
    threshold: Decimal = field(default_factory=lambda: Decimal('0'))
    current_value: Decimal = field(default_factory=lambda: Decimal('0'))
    message: str = ""
    
    # Additional risk details
    rule_id: str | None = None
    position_id: str | None = None
    symbol: str | None = None
    action_required: bool = False
    auto_action_taken: str | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for RiskEvent"""
        super().__post_init__()
        
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if not self.rule_type:
            raise ValueError("Rule type cannot be empty")
        if not self.message:
            raise ValueError("Message cannot be empty")
        if self.threshold < 0:
            raise ValueError("Threshold cannot be negative")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert RiskEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'account_id': self.account_id,
            'rule_type': self.rule_type,
            'severity': self.severity.value,
            'threshold': str(self.threshold),
            'current_value': str(self.current_value),
            'message': self.message,
            'rule_id': self.rule_id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'action_required': self.action_required,
            'auto_action_taken': self.auto_action_taken,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'RiskEvent':
        """Create RiskEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            account_id=data['account_id'],
            rule_type=data['rule_type'],
            severity=RiskSeverity(data['severity']),
            threshold=Decimal(data['threshold']),
            current_value=Decimal(data['current_value']),
            message=data['message'],
            rule_id=data.get('rule_id'),
            position_id=data.get('position_id'),
            symbol=data.get('symbol'),
            action_required=data.get('action_required', False),
            auto_action_taken=data.get('auto_action_taken'),
        )


@dataclass
class AccountEvent(Event):
    """
    Account lifecycle event for account management.
    
    Tracks account creation, updates, balance changes,
    and status modifications.
    """
    
    account_id: str = ""
    account_type: str = ""
    status: str = ""
    
    # Optional account details
    balance: Decimal | None = None
    currency: str | None = None
    margin_available: Decimal | None = None
    previous_status: str | None = None
    reason: str | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for AccountEvent"""
        super().__post_init__()
        
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if not self.account_type:
            raise ValueError("Account type cannot be empty")
        if not self.status:
            raise ValueError("Status cannot be empty")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert AccountEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'account_id': self.account_id,
            'account_type': self.account_type,
            'status': self.status,
            'balance': str(self.balance) if self.balance else None,
            'currency': self.currency,
            'margin_available': str(self.margin_available) if self.margin_available else None,
            'previous_status': self.previous_status,
            'reason': self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AccountEvent':
        """Create AccountEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            account_id=data['account_id'],
            account_type=data['account_type'],
            status=data['status'],
            balance=Decimal(data['balance']) if data.get('balance') else None,
            currency=data.get('currency'),
            margin_available=Decimal(data['margin_available']) if data.get('margin_available') else None,
            previous_status=data.get('previous_status'),
            reason=data.get('reason'),
        )


@dataclass
class SystemEvent(Event):
    """
    System lifecycle event for monitoring and alerting.
    
    Tracks system startup, shutdown, errors, and
    operational status changes.
    """
    
    component: str = ""
    status: str = ""
    message: str = ""
    
    # Optional system details
    error_code: str | None = None
    stack_trace: str | None = None
    severity: RiskSeverity = RiskSeverity.LOW
    recovery_action: str | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for SystemEvent"""
        super().__post_init__()
        
        if not self.component:
            raise ValueError("Component cannot be empty")
        if not self.status:
            raise ValueError("Status cannot be empty")
        if not self.message:
            raise ValueError("Message cannot be empty")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert SystemEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'component': self.component,
            'status': self.status,
            'message': self.message,
            'error_code': self.error_code,
            'stack_trace': self.stack_trace,
            'severity': self.severity.value,
            'recovery_action': self.recovery_action,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SystemEvent':
        """Create SystemEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            component=data['component'],
            status=data['status'],
            message=data['message'],
            error_code=data.get('error_code'),
            stack_trace=data.get('stack_trace'),
            severity=RiskSeverity(data.get('severity', 'low')),
            recovery_action=data.get('recovery_action'),
        )


@dataclass
class PriceTickEvent(Event):
    """
    Market data price tick event.
    
    Represents real-time price updates from market data feeds.
    """
    
    symbol: str = ""
    price: Decimal = field(default_factory=lambda: Decimal('0'))
    volume: Decimal = field(default_factory=lambda: Decimal('0'))
    timestamp_ms: int = 0
    
    # Optional market data fields
    bid: Decimal | None = None
    ask: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    open_price: Decimal | None = None
    close_price: Decimal | None = None
    exchange: str | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation for PriceTickEvent"""
        super().__post_init__()
        
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        if self.timestamp_ms <= 0:
            raise ValueError("Timestamp must be positive")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert PriceTickEvent to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'version': self.version,
            'symbol': self.symbol,
            'price': str(self.price),
            'volume': str(self.volume),
            'timestamp_ms': self.timestamp_ms,
            'bid': str(self.bid) if self.bid else None,
            'ask': str(self.ask) if self.ask else None,
            'high': str(self.high) if self.high else None,
            'low': str(self.low) if self.low else None,
            'open_price': str(self.open_price) if self.open_price else None,
            'close_price': str(self.close_price) if self.close_price else None,
            'exchange': self.exchange,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PriceTickEvent':
        """Create PriceTickEvent from dictionary"""
        return cls(
            id=data['id'],
            type=EventType(data['type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            version=data.get('version', '1.0.0'),
            symbol=data['symbol'],
            price=Decimal(data['price']),
            volume=Decimal(data['volume']),
            timestamp_ms=data['timestamp_ms'],
            bid=Decimal(data['bid']) if data.get('bid') else None,
            ask=Decimal(data['ask']) if data.get('ask') else None,
            high=Decimal(data['high']) if data.get('high') else None,
            low=Decimal(data['low']) if data.get('low') else None,
            open_price=Decimal(data['open_price']) if data.get('open_price') else None,
            close_price=Decimal(data['close_price']) if data.get('close_price') else None,
            exchange=data.get('exchange'),
        )


# Event type registry for factory pattern
EVENT_TYPE_REGISTRY = {
    EventType.ORDER_CREATED: OrderEvent,
    EventType.ORDER_FILLED: OrderEvent,
    EventType.ORDER_CANCELLED: OrderEvent,
    EventType.ORDER_REJECTED: OrderEvent,
    EventType.ORDER_MODIFIED: OrderEvent,
    EventType.TRADE_EXECUTED: TradeEvent,
    EventType.PRICE_TICK: PriceTickEvent,
    EventType.RISK_LIMIT_BREACHED: RiskEvent,
    EventType.POSITION_LIMIT_EXCEEDED: RiskEvent,
    EventType.RISK_DRAWDOWN_ALERT: RiskEvent,
    EventType.RISK_MARGIN_CALL: RiskEvent,
    EventType.RISK_STOP_LOSS_TRIGGERED: RiskEvent,
    EventType.ACCOUNT_CREATED: AccountEvent,
    EventType.ACCOUNT_UPDATED: AccountEvent,
    EventType.ACCOUNT_BALANCE_UPDATED: AccountEvent,
    EventType.ACCOUNT_SUSPENDED: AccountEvent,
    EventType.ACCOUNT_ACTIVATED: AccountEvent,
    EventType.STRATEGY_DEPLOYED: SystemEvent,
    EventType.STRATEGY_STARTED: SystemEvent,
    EventType.STRATEGY_STOPPED: SystemEvent,
    EventType.STRATEGY_PAUSED: SystemEvent,
    EventType.STRATEGY_ERROR: SystemEvent,
    EventType.EMERGENCY_STOP: SystemEvent,
    EventType.SYSTEM_ERROR: SystemEvent,
    EventType.SYSTEM_STARTUP: SystemEvent,
    EventType.SYSTEM_SHUTDOWN: SystemEvent,
}


def create_event_from_dict(data: dict[str, Any]) -> Event:
    """
    Factory function to create appropriate event type from dictionary.
    
    Args:
        data: Dictionary containing event data
        
    Returns:
        Event instance of appropriate type
        
    Raises:
        ValueError: If event type is not recognized
    """
    try:
        event_type = EventType(data['type'])
    except ValueError:
        raise ValueError(f"Unknown event type: {data['type']}")
    
    event_class = EVENT_TYPE_REGISTRY.get(event_type)
    
    if event_class is None:
        raise ValueError(f"Unknown event type: {event_type}")
    
    return event_class.from_dict(data)
