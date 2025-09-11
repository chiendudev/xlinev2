# File: xline/core/events/factory.py
"""
EventBusFactory with tiered fallback strategy.
Production (Redis) → Development (NATS) → Mock (InMemory)
"""
from __future__ import annotations

import structlog

from xline.core.events.bus import EventBusInterface, InMemoryEventBus
from xline.core.patterns.factory import TieredComponentFactory
from xline.infrastructure.messaging.nats.bus import NATSEventBus

logger = structlog.get_logger(__name__)


class EventBusFactory(TieredComponentFactory[EventBusInterface]):
    """
    Factory for creating EventBus instances with tiered fallback strategy.

    Fallback order:
    1. Production: Redis-based event bus (primary choice)
    2. Development: NATS-based event bus (development/staging)
    3. Mock: In-memory event bus (MUST ALWAYS WORK)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        nats_url: str = "nats://localhost:4222",
        cluster_name: str = "xline-cluster",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        super().__init__(max_retries=max_retries, retry_delay=retry_delay)
        self.redis_url = redis_url
        self.nats_url = nats_url
        self.cluster_name = cluster_name

    async def _create_production_implementation(self) -> EventBusInterface:
        """
        Create Redis-based production implementation.

        Returns:
            Redis EventBus instance

        Raises:
            Exception: If Redis connection fails
        """
        try:
            # Import here to avoid circular imports and handle missing dependencies
            from xline.infrastructure.messaging.redis.bus import RedisEventBus

            bus = RedisEventBus(
                redis_url=self.redis_url,
                max_retries=self.max_retries,
            )

            # Test initialization
            if not await bus.initialize():
                raise RuntimeError("Failed to initialize Redis EventBus")

            logger.info(
                "Production EventBus (Redis) created successfully", redis_url=self.redis_url
            )
            return bus

        except ImportError as e:
            logger.error("Redis EventBus not available - missing dependencies", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to create Redis EventBus", error=str(e), redis_url=self.redis_url)
            raise

    async def _create_development_implementation(self) -> EventBusInterface:
        """
        Create NATS-based development implementation.

        Returns:
            NATS EventBus instance

        Raises:
            Exception: If NATS connection fails
        """
        try:
            bus = NATSEventBus(
                nats_url=self.nats_url,
                cluster_name=self.cluster_name,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
            )

            # Test initialization
            if not await bus.initialize():
                raise RuntimeError("Failed to initialize NATS EventBus")

            logger.info(
                "Development EventBus (NATS) created successfully",
                nats_url=self.nats_url,
                cluster_name=self.cluster_name,
            )
            return bus

        except Exception as e:
            logger.error("Failed to create NATS EventBus", error=str(e), nats_url=self.nats_url)
            raise

    async def _create_mock_implementation(self, enable_dlq: bool = True) -> EventBusInterface:
        """
        Create in-memory mock implementation.

        This implementation MUST ALWAYS WORK and serves as the ultimate fallback.

        Args:
            enable_dlq: Whether to enable Dead Letter Queue functionality

        Returns:
            InMemory EventBus instance
        """
        bus = InMemoryEventBus(enable_dlq=enable_dlq)

        # Initialize (should never fail)
        await bus.initialize()

        logger.info("Mock EventBus (InMemory) created successfully")
        return bus
