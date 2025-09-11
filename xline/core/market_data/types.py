"""
Market Data Event Types for Xline Trading System.

High-performance event types for real-time market data processing.
All types support async event bus integration and decimal precision.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from xline.core.events.types import Event, EventType


@dataclass
class PriceTickEvent(Event):
    """
    Real-time price tick event with bid/ask/volume data.
    
    Used for high-frequency market data processing with decimal precision
    to avoid floating point rounding errors in financial calculations.
    
    Example:
        >>> tick = PriceTickEvent(
        ...     type=EventType.PRICE_TICK,
        ...     source="market_data",
        ...     symbol="BTCUSD",
        ...     bid=Decimal("50000.50"),
        ...     ask=Decimal("50001.00"),
        ...     volume=Decimal("1.5"),
        ...     tick_timestamp=1694649600.123
        ... )
        >>> assert tick.spread == Decimal("0.50")
    """
    
    symbol: str = ""
    bid: Decimal = field(default_factory=lambda: Decimal('0'))
    ask: Decimal = field(default_factory=lambda: Decimal('0'))
    volume: Decimal = field(default_factory=lambda: Decimal('0'))
    tick_timestamp: float = 0.0
    
    def __post_init__(self) -> None:
        """Set default values and validate data."""
        if not hasattr(self, 'type') or not self.type:
            self.type = EventType.PRICE_TICK
        if not self.source:
            self.source = "market_data"
        super().__post_init__()
        
        # Validate market data
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.bid < 0 or self.ask < 0 or self.volume < 0:
            raise ValueError("Price and volume must be non-negative")
        if self.ask > 0 and self.bid > 0 and self.ask < self.bid:
            raise ValueError("Ask price cannot be less than bid price")
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask - self.bid
    
    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price between bid and ask."""
        return (self.bid + self.ask) / Decimal('2')
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "type": self.type.value,
            "source": self.source,
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "bid": str(self.bid),
            "ask": str(self.ask),
            "volume": str(self.volume),
            "tick_timestamp": self.tick_timestamp,
            "correlation_id": self.correlation_id,
            "version": self.version,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PriceTickEvent':
        """Create event from dictionary."""
        from datetime import datetime
        
        return cls(
            type=EventType(data["type"]),
            source=data["source"],
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbol=data["symbol"],
            bid=Decimal(data["bid"]),
            ask=Decimal(data["ask"]),
            volume=Decimal(data["volume"]),
            tick_timestamp=data["tick_timestamp"],
            correlation_id=data.get("correlation_id"),
            version=data.get("version", "1.0.0"),
            data=data.get("data", {})
        )


@dataclass
class MarketDepthEvent(Event):
    """
    Market depth/order book event with bid/ask levels.
    
    Represents full order book state with multiple price levels
    for advanced trading strategies and market analysis.
    
    Example:
        >>> depth = MarketDepthEvent(
        ...     type=EventType.MARKET_DEPTH,
        ...     source="market_data",
        ...     symbol="ETHUSDT",
        ...     bids={"2000.00": "10.5", "1999.50": "5.2"},
        ...     asks={"2001.00": "8.3", "2001.50": "12.1"},
        ...     depth_timestamp=1694649600.456
        ... )
        >>> assert depth.best_bid == Decimal("2000.00")
    """
    
    symbol: str = ""
    bids: dict[str, Decimal] = field(default_factory=dict)  # price -> volume
    asks: dict[str, Decimal] = field(default_factory=dict)  # price -> volume
    depth_timestamp: float = 0.0
    
    def __post_init__(self) -> None:
        """Set default values and validate data."""
        if not hasattr(self, 'type') or not self.type:
            self.type = EventType.MARKET_DEPTH
        if not self.source:
            self.source = "market_data"
        super().__post_init__()
        
        # Validate market depth data
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
    
    @property
    def best_bid(self) -> Decimal:
        """Get best (highest) bid price."""
        if not self.bids:
            return Decimal('0')
        return max(Decimal(price) for price in self.bids.keys())
    
    @property
    def best_ask(self) -> Decimal:
        """Get best (lowest) ask price."""
        if not self.asks:
            return Decimal('0')
        return min(Decimal(price) for price in self.asks.keys())
    
    @property
    def spread(self) -> Decimal:
        """Calculate best bid-ask spread."""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid > 0 and best_ask > 0:
            return best_ask - best_bid
        return Decimal('0')
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "type": self.type.value,
            "source": self.source,
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "bids": {price: str(volume) for price, volume in self.bids.items()},
            "asks": {price: str(volume) for price, volume in self.asks.items()},
            "depth_timestamp": self.depth_timestamp,
            "correlation_id": self.correlation_id,
            "version": self.version,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'MarketDepthEvent':
        """Create event from dictionary."""
        from datetime import datetime
        
        return cls(
            type=EventType(data["type"]),
            source=data["source"],
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbol=data["symbol"],
            bids={price: Decimal(volume) for price, volume in data["bids"].items()},
            asks={price: Decimal(volume) for price, volume in data["asks"].items()},
            depth_timestamp=data["depth_timestamp"],
            correlation_id=data.get("correlation_id"),
            version=data.get("version", "1.0.0"),
            data=data.get("data", {})
        )
