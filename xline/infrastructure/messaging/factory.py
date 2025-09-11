"""
Message Bus Factory for backend selection and management.

Provides a factory pattern for creating event bus instances based on
environment configuration. Supports Redis Streams and NATS JetStream
backends with fallback capabilities.

Environment Variables:
- XLINE_MESSAGE_BUS: Backend selector (redis|nats, default: redis)
- ENABLE_FAILOVER: Allow runtime backend failover (0|1, default: 0)
"""

import asyncio
import os

import structlog

from xline.core.events.bus_interface import EventBusInterface
from xline.infrastructure.messaging.redis.bus import RedisEventBus
# Configure structured logging
logger = structlog.get_logger(__name__)

# Lazy import for NATS to avoid ImportError if not installed
_NATSEventBus = None


def _get_nats_event_bus() -> type[EventBusInterface] | None:
    """Lazy import NATS EventBus to handle optional dependency."""
    global _NATSEventBus
    if _NATSEventBus is None:
        try:
            from xline.infrastructure.messaging.nats.bus import NATSEventBus
            _NATSEventBus = NATSEventBus
        except ImportError as e:
            logger.warning("NATS EventBus not available", error=str(e))
            _NATSEventBus = False
    return _NATSEventBus if _NATSEventBus is not False else None


class MessageBusFactory:
    """Factory for creating and managing event bus instances."""

    _instance: "MessageBusFactory | None" = None
    _message_bus: EventBusInterface | None = None
    _init_lock = asyncio.Lock()
    _connected = False

    def __new__(cls) -> "MessageBusFactory":
        """Singleton pattern to ensure single factory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_message_bus(cls) -> EventBusInterface:
        """Get configured message bus instance with async initialization guard."""
        factory = cls()

        async with cls._init_lock:
            if cls._message_bus is None or not cls._connected:
                await factory._initialize_bus()

        if cls._message_bus is None:
            raise RuntimeError("Failed to initialize message bus")

        return cls._message_bus

    async def _initialize_bus(self) -> None:
        """Initialize the message bus based on environment configuration."""
        backend = os.getenv("XLINE_MESSAGE_BUS", "redis").lower()
        enable_failover = os.getenv("ENABLE_FAILOVER", "0") == "1"

        logger.info("Initializing message bus", backend=backend, failover=enable_failover)

        # Primary backend initialization
        bus = await self._create_backend(backend)

        if bus is not None:
            try:
                await bus.connect()
                self._message_bus = bus
                self._connected = True
                logger.info("Message bus initialized successfully", backend=backend)
                return
            except Exception as e:
                logger.error("Failed to connect to primary backend", backend=backend, error=str(e))
                if bus:
                    try:
                        await bus.disconnect()
                    except Exception as exc:
                        logger.debug("Error during disconnection cleanup", error=str(exc))

        # Failover logic if enabled
        if enable_failover:
            fallback_backend = "nats" if backend == "redis" else "redis"
            logger.warning("Attempting failover", fallback_backend=fallback_backend)

            fallback_bus = await self._create_backend(fallback_backend)
            if fallback_bus is not None:
                try:
                    await fallback_bus.connect()
                    self._message_bus = fallback_bus
                    self._connected = True
                    logger.info("Failover successful", backend=fallback_backend)
                    return
                except Exception as e:
                    logger.error("Failover also failed", backend=fallback_backend, error=str(e))
                    if fallback_bus:
                        try:
                            await fallback_bus.disconnect()
                        except Exception as exc:
                            logger.debug(
                                "Error during fallback disconnection cleanup",
                                error=str(exc)
                            )

        raise RuntimeError("Failed to initialize any message bus backend")

    async def _create_backend(self, backend: str) -> EventBusInterface | None:
        """Create a specific backend instance."""
        try:
            if backend == "redis":
                return RedisEventBus(
                    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    stream_prefix=os.getenv("REDIS_STREAM_PREFIX", "xline:events:"),
                    consumer_group=os.getenv("REDIS_CONSUMER_GROUP", "xline_consumer"),
                )

            elif backend == "nats":
                nats_class = _get_nats_event_bus()
                if nats_class is None:
                    logger.warning("NATS backend requested but not available")
                    return None

                return nats_class(
                    nats_url=os.getenv("NATS_URL", "nats://127.0.0.1:4222"),
                    stream_name=os.getenv("NATS_STREAM_NAME", "XLINE_EVENTS"),
                    consumer_group=os.getenv("NATS_CONSUMER_GROUP", "xline_consumer"),
                    batch_size=int(os.getenv("NATS_BATCH_SIZE", "50")),
                    timeout=float(os.getenv("NATS_TIMEOUT", "1.0")),
                    dlq_max_retries=int(os.getenv("DLQ_MAX_RETRIES", "5")),
                )

            else:
                logger.error("Unsupported backend", backend=backend)
                return None

        except Exception as e:
            logger.error("Failed to create backend", backend=backend, error=str(e))
            return None

    @classmethod
    async def close_message_bus(cls) -> None:
        """Close the current message bus instance."""
        async with cls._init_lock:
            if cls._message_bus is not None:
                try:
                    await cls._message_bus.close()
                    logger.info("Message bus closed")
                except Exception as e:
                    logger.error("Error closing message bus", error=str(e))
                finally:
                    cls._message_bus = None
                    cls._connected = False

    @classmethod
    def reset(cls) -> None:
        """Reset factory state (primarily for testing)."""
        cls._instance = None
        cls._message_bus = None
        cls._connected = False


# Convenience functions for direct access
async def get_message_bus() -> EventBusInterface:
    """Get the configured message bus instance."""
    return await MessageBusFactory.get_message_bus()


async def close_message_bus() -> None:
    """Close the current message bus instance."""
    await MessageBusFactory.close_message_bus()


def reset_factory() -> None:
    """Reset factory state (primarily for testing)."""
    MessageBusFactory.reset()
