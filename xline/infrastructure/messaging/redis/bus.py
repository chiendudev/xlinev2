"""Redis Event Bus Implementation - Redis Streams with Consumer Groups.

Implements EventBusInterface using Redis Streams for high-throughput,
persistent event messaging with at-least-once delivery guarantees.

Features:
- Redis Streams (XADD/XREADGROUP) for event publishing/consuming
- Consumer groups for load balancing and fault tolerance
- Dead letter queue for failed messages
- Circuit breaker for resilience
- Exponential backoff retry logic
- Health monitoring and metrics
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import redis.asyncio as redis
import structlog

from xline.core.events import (
    Envelope,
    EventBusConnectionError,
    EventBusError,
    PublishResult,
    SubscribeError,
)
from xline.core.events.utils import CircuitBreaker, CircuitBreakerConfig

# Configure structured logging
logger = structlog.get_logger(__name__)


class RedisEventBus:
    """Redis Streams-based event bus implementation.

    Provides reliable event messaging using Redis Streams with consumer groups,
    dead letter queues, and circuit breaker protection.

    Configuration via environment variables:
    - REDIS_URL: Redis connection string (default: redis://localhost:6379)
    - REDIS_STREAM_PREFIX: Stream name prefix (default: xline:events:)
    - REDIS_CONSUMER_GROUP: Consumer group name (default: xline-consumers)
    - REDIS_DLQ_MAX_RETRIES: Max retries before DLQ (default: 3)
    - REDIS_BATCH_SIZE: Max messages per read (default: 10)
    - REDIS_BLOCK_TIME_MS: Block time for XREADGROUP (default: 1000)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream_prefix: str = "xline:events:",
        consumer_group: str = "xline-consumers",
        dlq_max_retries: int = 3,
        batch_size: int = 10,
        block_time_ms: int = 1000,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        self.redis_url = redis_url
        self.stream_prefix = stream_prefix
        self.consumer_group = consumer_group
        self.dlq_max_retries = dlq_max_retries
        self.batch_size = batch_size
        self.block_time_ms = block_time_ms

        self._redis: redis.Redis | None = None
        self._is_connected = False
        self._subscriptions: dict[str, bool] = {}
        self._circuit_breaker = CircuitBreaker(
            circuit_breaker_config or CircuitBreakerConfig()
        )

        # Metrics tracking
        self._publish_count = 0
        self._consume_count = 0
        self._error_count = 0
        self._dlq_count = 0

    async def connect(self) -> None:
        """Establish Redis connection and initialize consumer groups."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            await self._redis.ping()
            self._is_connected = True

            logger.info("Redis event bus connected", redis_url=self.redis_url)

        except Exception as e:
            self._error_count += 1
            logger.error("Failed to connect to Redis", error=str(e))
            raise EventBusConnectionError(f"Redis connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Close Redis connection gracefully."""
        if self._redis:
            try:
                await self._redis.aclose()
                self._is_connected = False
                logger.info("Redis event bus disconnected")
            except Exception as e:
                logger.warning("Error during Redis disconnect", error=str(e))

    @asynccontextmanager
    async def _get_redis(self):
        """Get Redis connection with automatic reconnection."""
        if not self._is_connected or not self._redis:
            await self.connect()
        yield self._redis

    def _get_stream_name(self, event_type: str) -> str:
        """Get Redis stream name for event type."""
        return f"{self.stream_prefix}{event_type}"

    def _get_dlq_name(self, stream_name: str) -> str:
        """Get dead letter queue name for stream."""
        return f"{stream_name}:dlq"

    async def _ensure_consumer_group(self, stream_name: str) -> None:
        """Ensure consumer group exists for stream."""
        try:
            async with self._get_redis() as redis_client:
                await redis_client.xgroup_create(
                    stream_name, self.consumer_group, id="0", mkstream=True
                )
        except redis.ResponseError as e:
            # Group already exists
            if "BUSYGROUP" not in str(e):
                raise

    async def publish(self, envelope: Envelope) -> PublishResult:
        """Publish event to Redis stream.

        Args:
            envelope: Event envelope to publish

        Returns:
            PublishResult with success status and message ID

        Raises:
            PublishError: If publish operation fails
        """
        try:
            # Execute publish through circuit breaker
            return await self._circuit_breaker.call(self._do_publish, envelope)

        except Exception as e:
            self._error_count += 1
            logger.error(
                "Event publish failed",
                event_type=envelope.event_type,
                event_id=envelope.event_id,
                error=str(e)
            )
            return PublishResult(
                success=False,
                event_id=envelope.event_id,
                error=f"Publish failed: {e}"
            )

    async def _do_publish(self, envelope: Envelope) -> PublishResult:
        """Internal publish implementation."""
        stream_name = self._get_stream_name(envelope.event_type)

        # Prepare message data
        message_data = {
            "event_id": envelope.event_id,
            "event_type": envelope.event_type,
            "data": json.dumps(envelope.data),
            "timestamp": envelope.timestamp.isoformat(),
            "source": envelope.source,
            "correlation_id": envelope.correlation_id or "",
            "headers": json.dumps(envelope.headers),
            "retry_count": str(envelope.retry_count),
        }

        async with self._get_redis() as redis_client:
            message_id = await redis_client.xadd(stream_name, message_data)

        self._publish_count += 1
        logger.info(
            "Event published",
            event_type=envelope.event_type,
            event_id=envelope.event_id,
            message_id=message_id,
            stream=stream_name
        )

        return PublishResult(
            success=True,
            message_id=message_id,
            event_id=envelope.event_id
        )

    async def subscribe(
        self,
        event_types: list[str],
        consumer_group: str,
        consumer_name: str
    ) -> AsyncIterator[Envelope]:
        """Subscribe to events using Redis consumer group.

        Args:
            event_types: List of event types to subscribe to
            consumer_group: Consumer group name
            consumer_name: Unique consumer name

        Yields:
            Envelope: Received event envelopes

        Raises:
            SubscribeError: If subscription fails
        """
        if not event_types:
            raise SubscribeError("No event types specified for subscription")

        try:
            # Prepare stream mapping for XREADGROUP
            streams = {}
            for event_type in event_types:
                stream_name = self._get_stream_name(event_type)
                await self._ensure_consumer_group(stream_name)
                streams[stream_name] = ">"
                self._subscriptions[f"{consumer_group}:{consumer_name}:{event_type}"] = True

            logger.info(
                "Starting event subscription",
                event_types=event_types,
                consumer_group=consumer_group,
                consumer_name=consumer_name
            )

            # Subscribe loop
            async for envelope in self._consume_messages(streams, consumer_group, consumer_name):
                yield envelope

        except Exception as e:
            self._error_count += 1
            logger.error(
                "Subscription failed",
                event_types=event_types,
                consumer_group=consumer_group,
                consumer_name=consumer_name,
                error=str(e)
            )
            raise SubscribeError(f"Subscription failed: {e}") from e

    async def _consume_messages(
        self,
        streams: dict[str, str],
        consumer_group: str,
        consumer_name: str
    ) -> AsyncIterator[Envelope]:
        """Internal message consumption loop."""
        while any(self._subscriptions.values()):
            try:
                async with self._get_redis() as redis_client:
                    # Read messages from streams
                    messages = await redis_client.xreadgroup(
                        consumer_group,
                        consumer_name,
                        streams,
                        count=self.batch_size,
                        block=self.block_time_ms
                    )

                    for stream_name, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                envelope = await self._parse_message(fields)
                                self._consume_count += 1

                                logger.debug(
                                    "Message consumed",
                                    stream=stream_name,
                                    message_id=message_id,
                                    event_type=envelope.event_type,
                                    event_id=envelope.event_id
                                )

                                yield envelope

                                # Acknowledge message
                                await redis_client.xack(stream_name, consumer_group, message_id)

                            except Exception as e:
                                await self._handle_message_error(
                                    redis_client, stream_name, consumer_group,
                                    message_id, fields, e
                                )

            except Exception as e:
                self._error_count += 1
                logger.error("Error in consume loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _parse_message(self, fields: dict[str, str]) -> Envelope:
        """Parse Redis message fields into Envelope."""
        try:
            return Envelope(
                event_type=fields["event_type"],
                data=json.loads(fields["data"]),
                event_id=fields["event_id"],
                timestamp=datetime.fromisoformat(fields["timestamp"]),
                source=fields["source"],
                correlation_id=fields["correlation_id"] or None,
                headers=json.loads(fields["headers"]),
                retry_count=int(fields["retry_count"])
            )
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise SubscribeError(f"Invalid message format: {e}") from e

    async def _handle_message_error(
        self,
        redis_client: redis.Redis,
        stream_name: str,
        consumer_group: str,
        message_id: str,
        fields: dict[str, str],
        error: Exception
    ) -> None:
        """Handle message processing errors with retry/DLQ logic."""
        try:
            retry_count = int(fields.get("retry_count", "0"))
            self._error_count += 1

            if retry_count >= self.dlq_max_retries:
                # Send to dead letter queue
                dlq_name = self._get_dlq_name(stream_name)
                await redis_client.xadd(dlq_name, {
                    **fields,
                    "error": str(error),
                    "failed_at": time.time(),
                    "original_stream": stream_name,
                    "original_message_id": message_id
                })

                self._dlq_count += 1
                logger.warning(
                    "Message moved to DLQ",
                    stream=stream_name,
                    message_id=message_id,
                    retry_count=retry_count,
                    error=str(error)
                )

                # Acknowledge to remove from pending
                await redis_client.xack(stream_name, consumer_group, message_id)

            else:
                # Retry message with incremented count
                updated_fields = {
                    **fields,
                    "retry_count": str(retry_count + 1),
                    "last_error": str(error),
                    "retry_at": time.time()
                }
                await redis_client.xadd(stream_name, updated_fields)

                # Acknowledge original message
                await redis_client.xack(stream_name, consumer_group, message_id)

                logger.info(
                    "Message scheduled for retry",
                    stream=stream_name,
                    message_id=message_id,
                    retry_count=retry_count + 1
                )

        except Exception as dlq_error:
            logger.error(
                "Failed to handle message error",
                stream=stream_name,
                message_id=message_id,
                original_error=str(error),
                dlq_error=str(dlq_error)
            )

    async def unsubscribe(self, consumer_group: str, consumer_name: str) -> None:
        """Unsubscribe consumer from all event types.

        Args:
            consumer_group: Consumer group name
            consumer_name: Consumer name to unsubscribe

        Raises:
            SubscribeError: If unsubscribe fails
        """
        try:
            # Mark subscriptions as inactive
            for key in list(self._subscriptions.keys()):
                if key.startswith(f"{consumer_group}:{consumer_name}:"):
                    self._subscriptions[key] = False

            logger.info(
                "Consumer unsubscribed",
                consumer_group=consumer_group,
                consumer_name=consumer_name
            )

        except Exception as e:
            logger.error(
                "Unsubscribe failed",
                consumer_group=consumer_group,
                consumer_name=consumer_name,
                error=str(e)
            )
            raise SubscribeError(f"Unsubscribe failed: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check Redis event bus health.

        Returns:
            Dictionary with health status and metrics

        Raises:
            EventBusError: If health check fails
        """
        try:
            start_time = time.time()

            async with self._get_redis() as redis_client:
                # Test basic connectivity
                await redis_client.ping()

                # Get Redis info
                info = await redis_client.info()

            response_time = time.time() - start_time

            status = {
                "status": "healthy",
                "timestamp": time.time(),
                "response_time_ms": round(response_time * 1000, 2),
                "redis_connected": self._is_connected,
                "circuit_breaker": self._circuit_breaker.get_status(),
                "metrics": {
                    "publish_count": self._publish_count,
                    "consume_count": self._consume_count,
                    "error_count": self._error_count,
                    "dlq_count": self._dlq_count,
                },
                "redis_info": {
                    "version": info.get("redis_version"),
                    "memory_used": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                }
            }

            # Check if circuit breaker is open
            if self._circuit_breaker.is_open:
                status["status"] = "degraded"
                status["circuit_breaker_open"] = True

            return status

        except Exception as e:
            self._error_count += 1
            logger.error("Health check failed", error=str(e))
            raise EventBusError(f"Health check failed: {e}") from e

    async def close(self) -> None:
        """Close event bus and cleanup resources.

        Raises:
            EventBusError: If close operation fails
        """
        try:
            # Stop all subscriptions
            for key in self._subscriptions:
                self._subscriptions[key] = False

            # Close Redis connection
            await self.disconnect()

            logger.info("Redis event bus closed")

        except Exception as e:
            logger.error("Error closing event bus", error=str(e))
            raise EventBusError(f"Close failed: {e}") from e


# Alias for EventBusInterface compatibility
RedisEventBusInterface = RedisEventBus
