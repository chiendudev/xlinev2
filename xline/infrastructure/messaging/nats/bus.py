"""NATS JetStream Event Bus implementation."""

import asyncio
import json
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from nats import connect
from nats.js.api import ConsumerConfig, StreamConfig
from nats.js.client import JetStreamContext

from xline.core.events.bus import Event, EventBusInterface, EventHandler, PublishResult, SubscriptionId
from xline.core.events.utils import CircuitBreaker

logger = structlog.get_logger(__name__)


class NATSEventBus(EventBusInterface):
    """NATS JetStream Event Bus implementation."""

    def __init__(
        self,
        nats_url: str | None = None,
        stream_name: str | None = None,
        consumer_group: str | None = None,
        batch_size: int | None = None,
        timeout: float | None = None,
        dlq_max_retries: int | None = None
    ) -> None:
        """Initialize NATS Event Bus with configuration parameters."""
        self._url = nats_url or os.getenv("NATS_URL", "nats://localhost:4222")
        self._stream_name = stream_name or os.getenv("NATS_STREAM_NAME", "xline-events")
        self._consumer_group = consumer_group or os.getenv("NATS_CONSUMER_GROUP", "xline-consumer")
        self._batch_size = batch_size or int(os.getenv("NATS_BATCH_SIZE", "50"))
        self._timeout = timeout or float(os.getenv("NATS_TIMEOUT", "30.0"))
        self._dlq_max_retries = dlq_max_retries or int(os.getenv("DLQ_MAX_RETRIES", "3"))

        self._client = None
        self._js: JetStreamContext | None = None
        self._handlers: dict[str, list[Callable[[Event], Any]]] = {}
        self._running = False
        self._pull_sub = None
        self._circuit_breaker = CircuitBreaker()

        logger.info(
            "NATS Event Bus initialized",
            url=self._url,
            stream=self._stream_name,
            consumer=self._consumer_group,
            batch_size=self._batch_size
        )

    async def initialize(self) -> bool:
        """Initialize NATS connection and setup JetStream."""
        try:
            await self._do_connect()
            return True
        except Exception:
            return False

    async def connect(self) -> None:
        """Connect to NATS server (compatibility method)."""
        await self._do_connect()

    async def _do_connect(self) -> None:
        """Internal connection implementation."""
        logger.info("Connecting to NATS server", url=self._url)

        # Connect to NATS
        self._client = await connect(self._url)

        # Get JetStream context
        self._js = self._client.jetstream()

        # Ensure stream exists
        try:
            await self._js.stream_info(self._stream_name)
            logger.debug("Stream exists", stream=self._stream_name)
        except Exception:
            # Create stream if it doesn't exist
            stream_config = StreamConfig(
                name=self._stream_name,
                subjects=[f"{self._stream_name}.*"]
            )
            await self._js.add_stream(config=stream_config)
            logger.info("Created stream", stream=self._stream_name)

        # Setup consumer
        try:
            await self._js.consumer_info(self._stream_name, self._consumer_group)
            logger.debug("Consumer exists", consumer=self._consumer_group)
        except Exception:
            # Create consumer if it doesn't exist
            consumer_config = ConsumerConfig(
                durable_name=self._consumer_group,
                deliver_policy="all",
                ack_policy="explicit",
                max_deliver=self._dlq_max_retries + 1
            )
            await self._js.add_consumer(
                self._stream_name,
                config=consumer_config
            )
            logger.info("Created consumer", consumer=self._consumer_group)

        # Create pull subscription
        self._pull_sub = await self._js.pull_subscribe(
            f"{self._stream_name}.*",
            self._consumer_group
        )

        self._running = True
        logger.info("Connected to NATS JetStream successfully")

    async def health_check(self) -> bool:
        """Check if NATS connection is healthy."""
        try:
            if not self._client or not self._js:
                return False
            await self._js.stream_info(self._stream_name)
            return True
        except Exception:
            return False

    async def cleanup(self) -> None:
        """Cleanup NATS resources and connections."""
        await self._do_cleanup()

    async def disconnect(self) -> None:
        """Disconnect from NATS server (compatibility method)."""
        await self._do_cleanup()

    async def _do_cleanup(self) -> None:
        """Internal cleanup implementation."""
        logger.info("Cleaning up NATS resources")
        self._running = False

        if self._client:
            try:
                await self._client.close()
            except Exception as exc:
                logger.debug("Error closing connection", error=str(exc))

        self._client = None
        self._js = None
        self._pull_sub = None
        self._handlers.clear()
        logger.info("NATS cleanup completed")

    async def publish(self, event: Event) -> PublishResult:
        """Publish an event to the bus."""
        if not self._js:
            return PublishResult(
                success=False,
                event_id=event.id,
                error="Not connected to NATS"
            )

        try:
            # Convert event to JSON
            event_data = {
                "id": event.id,
                "type": event.type,
                "source": event.source,
                "data": event.data,
                "timestamp": (
                    event.timestamp.isoformat()
                    if hasattr(event.timestamp, 'isoformat')
                    else str(event.timestamp)
                ),
                "correlation_id": event.correlation_id,
                "version": event.version
            }

            payload = json.dumps(event_data).encode()

            # Publish to stream
            ack = await self._js.publish(
                subject=f"{self._stream_name}.{event.type}",
                payload=payload,
                timeout=self._timeout
            )

            return PublishResult(
                success=True,
                event_id=event.id,
                message_id=str(ack.seq)
            )

        except Exception as exc:
            logger.error("Failed to publish event", event_id=event.id, error=str(exc))
            return PublishResult(
                success=False,
                event_id=event.id,
                error=str(exc)
            )

    async def subscribe(self, event_type: str, handler: EventHandler) -> SubscriptionId:
        """Subscribe to events of a specific type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        subscription_id = SubscriptionId(id=f"{event_type}_{len(self._handlers[event_type])}")

        logger.info(
            "Subscribed to event type",
            event_type=event_type,
            subscription_id=subscription_id.id,
            handler_count=len(self._handlers[event_type])
        )

        return subscription_id

    async def unsubscribe(self, subscription_id: SubscriptionId) -> bool:
        """Unsubscribe from events."""
        logger.info("Unsubscribed", subscription_id=subscription_id.id)
        return True
