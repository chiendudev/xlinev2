"""
Market Data Processor for Xline Trading System.

Processes market data events with latency tracking and statistical analysis.
Integrates with event bus for real-time processing.
"""

import asyncio
import logging
from typing import Any

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType
from xline.core.market_data.types import MarketDepthEvent, PriceTickEvent

logger = logging.getLogger(__name__)


class PriceTickHandler:
    """Handler wrapper for price tick events."""
    
    def __init__(self, process_func):
        self.process_func = process_func
    
    async def handle(self, event):
        """Handle price tick event."""
        await self.process_func(event)


class MarketDepthHandler:
    """Handler wrapper for market depth events."""
    
    def __init__(self, process_func):
        self.process_func = process_func
    
    async def handle(self, event):
        """Handle market depth event."""
        await self.process_func(event)


class MarketDataProcessor:
    """
    Process and analyze market data events with latency tracking.
    
    Subscribes to market data events from the event bus and maintains
    price cache and processing statistics for performance monitoring.
    
    Example:
        >>> event_bus = InMemoryEventBus()
        >>> processor = MarketDataProcessor(event_bus)
        >>> await processor.start()
        >>> stats = processor.get_processing_stats()
        >>> assert stats["events_processed"] >= 0
    """
    
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        """
        Initialize market data processor.
        
        Args:
            event_bus: Event bus for subscribing to market data events
        """
        self.event_bus = event_bus
        self.price_cache: dict[str, PriceTickEvent] = {}
        self.depth_cache: dict[str, MarketDepthEvent] = {}
        self.processing_stats = {
            "events_processed": 0,
            "price_events_processed": 0,
            "depth_events_processed": 0,
            "avg_latency_ms": 0.0,
            "total_latency_ms": 0.0,
            "min_latency_ms": float('inf'),
            "max_latency_ms": 0.0
        }
        self.is_running = False
        self._price_subscription_id = None
        self._depth_subscription_id = None
        
        logger.info("MarketDataProcessor initialized")
    
    async def start(self) -> None:
        """
        Start processing market data events.
        
        Subscribes to price tick and market depth events from the event bus.
        """
        if self.is_running:
            logger.warning("Market data processor is already running")
            return
        
        self.is_running = True
        
        # Subscribe to market data events with proper handlers
        self._price_subscription_id = await self.event_bus.subscribe(
            EventType.PRICE_TICK.value,
            PriceTickHandler(self._process_tick)
        )
        self._depth_subscription_id = await self.event_bus.subscribe(
            EventType.MARKET_DEPTH.value,
            MarketDepthHandler(self._process_depth)
        )
        
        logger.info("Market data processor started")
    
    async def stop(self) -> None:
        """
        Stop processing market data events.
        
        Unsubscribes from all market data events.
        """
        if not self.is_running:
            logger.warning("Market data processor is not running")
            return
        
        self.is_running = False
        
        # Unsubscribe from market data events using subscription IDs
        if self._price_subscription_id:
            await self.event_bus.unsubscribe(self._price_subscription_id)
        if self._depth_subscription_id:
            await self.event_bus.unsubscribe(self._depth_subscription_id)
        
        logger.info("Market data processor stopped")
    
    async def _process_tick(self, event: PriceTickEvent) -> None:
        """
        Process price tick event with latency tracking.
        
        Args:
            event: Price tick event to process
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Validate event
            if not isinstance(event, PriceTickEvent):
                logger.error(f"Invalid event type: {type(event)}")
                return
            
            # Update price cache
            self.price_cache[event.symbol] = event
            
            # Calculate processing latency
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_latency_stats(latency_ms)
            
            # Update processing stats
            self.processing_stats["events_processed"] += 1
            self.processing_stats["price_events_processed"] += 1
            
            # Log high latency events
            if latency_ms > 5.0:  # 5ms threshold
                logger.warning(
                    f"High latency processing {event.symbol}: {latency_ms:.2f}ms"
                )
            
        except Exception as e:
            logger.error(f"Failed to process price tick for {event.symbol}: {e}")
    
    async def _process_depth(self, event: MarketDepthEvent) -> None:
        """
        Process market depth event with latency tracking.
        
        Args:
            event: Market depth event to process
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Validate event
            if not isinstance(event, MarketDepthEvent):
                logger.error(f"Invalid event type: {type(event)}")
                return
            
            # Update depth cache
            self.depth_cache[event.symbol] = event
            
            # Calculate processing latency
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_latency_stats(latency_ms)
            
            # Update processing stats
            self.processing_stats["events_processed"] += 1
            self.processing_stats["depth_events_processed"] += 1
            
            # Log high latency events
            if latency_ms > 5.0:  # 5ms threshold
                logger.warning(
                    f"High latency processing depth for {event.symbol}: {latency_ms:.2f}ms"
                )
            
        except Exception as e:
            logger.error(f"Failed to process market depth for {event.symbol}: {e}")
    
    def _update_latency_stats(self, latency_ms: float) -> None:
        """
        Update latency statistics.
        
        Args:
            latency_ms: Processing latency in milliseconds
        """
        # Update total latency
        self.processing_stats["total_latency_ms"] += latency_ms
        
        # Update min/max latency
        if latency_ms < self.processing_stats["min_latency_ms"]:
            self.processing_stats["min_latency_ms"] = latency_ms
        if latency_ms > self.processing_stats["max_latency_ms"]:
            self.processing_stats["max_latency_ms"] = latency_ms
        
        # Update average latency
        total_events = self.processing_stats["events_processed"] + 1
        self.processing_stats["avg_latency_ms"] = (
            self.processing_stats["total_latency_ms"] / total_events
        )
    
    def get_processing_stats(self) -> dict[str, Any]:
        """
        Get current processing statistics.
        
        Returns:
            Dictionary containing processing performance metrics
        """
        stats = self.processing_stats.copy()
        
        # Add cache statistics
        stats.update({
            "cached_symbols": len(self.price_cache),
            "depth_cached_symbols": len(self.depth_cache),
            "is_running": self.is_running
        })
        
        # Handle infinite min_latency for empty stats
        if stats["min_latency_ms"] == float('inf'):
            stats["min_latency_ms"] = 0.0
        
        return stats
    
    def get_latest_price(self, symbol: str) -> PriceTickEvent | None:
        """
        Get latest price tick for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price tick event or None if not available
        """
        return self.price_cache.get(symbol)
    
    def get_latest_depth(self, symbol: str) -> MarketDepthEvent | None:
        """
        Get latest market depth for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest market depth event or None if not available
        """
        return self.depth_cache.get(symbol)
    
    def get_cached_symbols(self) -> list[str]:
        """
        Get list of symbols with cached price data.
        
        Returns:
            List of symbols with cached price data
        """
        return list(self.price_cache.keys())
    
    def clear_cache(self) -> None:
        """Clear all cached market data."""
        self.price_cache.clear()
        self.depth_cache.clear()
        logger.info("Market data cache cleared")
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.processing_stats = {
            "events_processed": 0,
            "price_events_processed": 0,
            "depth_events_processed": 0,
            "avg_latency_ms": 0.0,
            "total_latency_ms": 0.0,
            "min_latency_ms": float('inf'),
            "max_latency_ms": 0.0
        }
        logger.info("Processing statistics reset")
