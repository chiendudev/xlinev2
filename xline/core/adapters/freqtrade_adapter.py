"""
FreqtradeAdapter - Bridge between Freqtrade and Xline Event System
File: xline/core/adapters/freqtrade_adapter.py

Provides seamless integration with Freqtrade trading engine while maintaining
strict separation of concerns and async/await patterns.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from freqtrade.freqtradebot import FreqtradeBot
from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import (
    Event,
    EventType,
    OrderEvent,
    OrderSide,
    OrderStatus,
    OrderType,
    SystemEvent,
)


logger = logging.getLogger(__name__)


class FreqtradeAdapter:
    """
    Adapter layer bridging Freqtrade trading engine with Xline event system.

    Example usage:
        adapter = FreqtradeAdapter(event_bus, config)
        await adapter.setup_event_handlers()
        success = await adapter.start_trading("account_1", "RSIStrategy")
    """

    def __init__(self, event_bus: InMemoryEventBus, config: dict[str, Any]) -> None:
        """
        Initialize adapter with event bus and configuration.

        Args:
            event_bus: Event bus instance for publishing/subscribing to events
            config: Freqtrade configuration dictionary
        """
        self.event_bus = event_bus
        self.config = config
        self.freqtrade_bot: FreqtradeBot | None = None
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self._is_setup = False

    async def setup_event_handlers(self) -> None:
        """
        Setup event subscriptions for risk management.

        Subscribes to critical events like risk limit breaches and sets up
        hooks into Freqtrade execution methods for real-time event publishing.
        """
        # Subscribe to RISK_LIMIT_BREACHED events
        await self.event_bus.subscribe(EventType.RISK_LIMIT_BREACHED.value, self._handle_risk_event)
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

        Raises:
            ValueError: If account_id or strategy_name is empty
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
                "status": "active",
            }

            # Publish strategy started event
            await self._publish_strategy_event("STRATEGY_STARTED", account_id, strategy_name)

            logger.info(f"Trading started for {account_id} with {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start trading: {e}")
            return False

    async def stop_trading(self, account_id: str) -> bool:
        """
        Stop trading for account with cleanup.

        Args:
            account_id: Account to stop trading for

        Returns:
            bool: True if trading stopped successfully
        """
        try:
            # Find and stop sessions for this account
            sessions_to_stop = [
                sid
                for sid, session in self.active_sessions.items()
                if session["account_id"] == account_id
            ]

            for session_id in sessions_to_stop:
                session = self.active_sessions[session_id]
                session["status"] = "stopped"

                await self._publish_strategy_event(
                    "STRATEGY_STOPPED", session["account_id"], session["strategy_name"]
                )

            logger.info(f"Trading stopped for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop trading: {e}")
            return False

    async def emergency_stop(self) -> None:
        """
        Emergency stop with immediate cleanup.

        Stops all active trading sessions immediately and publishes
        emergency stop event to notify all system components.
        """
        try:
            # Stop all active sessions immediately
            for session_id, session in self.active_sessions.items():
                session["status"] = "emergency_stopped"

            # Publish emergency stop event
            emergency_event = SystemEvent(
                type=EventType.EMERGENCY_STOP,
                source="freqtrade_adapter",
                component="FreqtradeAdapter",
                status="emergency_stopped",
                message="Emergency stop triggered",
                data={
                    "reason": "emergency_stop_triggered",
                    "timestamp": asyncio.get_event_loop().time(),
                },
            )
            await self.event_bus.publish(emergency_event)

            logger.critical("Emergency stop executed")

        except Exception as e:
            logger.critical(f"Emergency stop failed: {e}")

    def _setup_freqtrade_hooks(self) -> None:
        """
        Setup hooks into Freqtrade execution methods.

        Intercepts order execution methods to publish real-time events
        without disrupting Freqtrade's internal operations.
        """
        if not self.freqtrade_bot:
            return

        # Hook into order execution methods
        original_execute_entry = getattr(self.freqtrade_bot, "execute_entry", None)
        original_execute_exit = getattr(self.freqtrade_bot, "execute_exit", None)

        if original_execute_entry:

            async def hooked_execute_entry(*args, **kwargs):
                result = await original_execute_entry(*args, **kwargs)
                if result:
                    await self._publish_order_event(result, "BUY")
                return result

            self.freqtrade_bot.execute_entry = hooked_execute_entry

        if original_execute_exit:

            async def hooked_execute_exit(*args, **kwargs):
                result = await original_execute_exit(*args, **kwargs)
                if result:
                    await self._publish_order_event(result, "SELL")
                return result

            self.freqtrade_bot.execute_exit = hooked_execute_exit

    async def _publish_order_event(self, order_data: dict[str, Any], order_side: str) -> None:
        """
        Publish order event to event bus.

        Args:
            order_data: Order information from Freqtrade
            order_side: "BUY" or "SELL"
        """
        try:
            order_event = OrderEvent(
                type=EventType.ORDER_CREATED,
                source="freqtrade_adapter",
                order_id=order_data.get("id", ""),
                account_id=order_data.get("account_id", ""),
                symbol=order_data.get("symbol", ""),
                side=OrderSide.BUY if order_side == "BUY" else OrderSide.SELL,
                quantity=Decimal(str(order_data.get("amount", 0))),
                price=Decimal(str(order_data.get("price", 0))),
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
            )
            await self.event_bus.publish(order_event)

        except Exception as e:
            logger.error(f"Failed to publish order event: {e}")

    async def _handle_risk_event(self, event: Event) -> None:
        """
        Handle risk management events.

        Args:
            event: Risk event to handle
        """
        try:
            if event.type == EventType.RISK_LIMIT_BREACHED:
                # Immediate emergency stop on risk breach
                await self.emergency_stop()
                logger.warning(f"Risk event triggered emergency stop: {event.data}")

        except Exception as e:
            logger.error(f"Failed to handle risk event: {e}")

    async def _publish_strategy_event(
        self, event_type: str, account_id: str, strategy_name: str
    ) -> None:
        """
        Publish strategy lifecycle events.

        Args:
            event_type: Type of strategy event (STRATEGY_STARTED, STRATEGY_STOPPED, etc.)
            account_id: Account identifier
            strategy_name: Name of the strategy
        """
        strategy_event = SystemEvent(
            type=getattr(EventType, event_type),
            source="freqtrade_adapter",
            component="FreqtradeAdapter",
            status=event_type.lower(),
            message=f"Strategy {event_type.lower().replace('_', ' ')}",
            data={
                "account_id": account_id,
                "strategy_name": strategy_name,
                "timestamp": asyncio.get_event_loop().time(),
            },
        )
        await self.event_bus.publish(strategy_event)
