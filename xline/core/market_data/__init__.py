"""
Xline Market Data Processing Module.

High-performance real-time market data pipeline with event-driven architecture.
Supports 1000+ ticks/second throughput with sub-5ms latency.
"""

from .feed import MarketDataFeed
from .processor import MarketDataProcessor
from .types import MarketDepthEvent, PriceTickEvent

__all__ = [
    "PriceTickEvent",
    "MarketDepthEvent",
    "MarketDataFeed",
    "MarketDataProcessor"
]
