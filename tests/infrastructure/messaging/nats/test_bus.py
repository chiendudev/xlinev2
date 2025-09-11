# File: tests/infrastructure/messaging/nats/test_bus.py
"""
Tests for NATS JetStream Event Bus implementation.
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from xline.core.events.bus import Event
from xline.infrastructure.messaging.nats.bus import NATSEventBus


@pytest.mark.asyncio
class TestNATSEventBus:
    """Test NATS JetStream Event Bus functionality."""

    @pytest.fixture
    def sample_event(self) -> Event:
        """Create sample event for testing."""
        return Event(
            id=str(uuid4()),
            type="trading.order.created",
            source="test",
            timestamp=datetime.utcnow(),
            data={"symbol": "BTC/USDT", "side": "buy", "amount": 1.0},
        )

    @pytest.fixture
    def nats_bus(self) -> NATSEventBus:
        """Create NATS Event Bus instance."""
        return NATSEventBus(
            nats_url="nats://localhost:4222",
            cluster_name="test-cluster",
            max_retries=2,
            retry_delay=0.1,
        )

    async def test_nats_bus_initialization_success(self, nats_bus: NATSEventBus):
        """Test successful NATS bus initialization."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())

            result = await nats_bus.initialize()

            assert result is True
            assert nats_bus._initialized is True
            mock_connect.assert_called_once()

    async def test_nats_bus_initialization_failure(self, nats_bus: NATSEventBus):
        """Test NATS bus initialization failure."""
        with patch("nats.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            result = await nats_bus.initialize()

            assert result is False
            assert nats_bus._initialized is False

    async def test_nats_bus_health_check(self, nats_bus: NATSEventBus):
        """Test NATS bus health check."""
        # Before initialization
        assert await nats_bus.health_check() is False

        # Mock successful initialization
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_client.is_connected = True
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())

            await nats_bus.initialize()

            # Health check should work
            assert await nats_bus.health_check() is True

    async def test_subject_mapping(self, nats_bus: NATSEventBus):
        """Test event type to NATS subject mapping."""
        # Trading events
        assert (
            nats_bus._get_subject_for_event_type("trading.order.created")
            == "trading.trading.order.created"
        )

        # Risk events
        assert (
            nats_bus._get_subject_for_event_type("risk.limit.exceeded")
            == "risk.risk.limit.exceeded"
        )

        # Accounts events
        assert (
            nats_bus._get_subject_for_event_type("accounts.balance.updated")
            == "accounts.accounts.balance.updated"
        )

        # System events
        assert nats_bus._get_subject_for_event_type("system.startup") == "system.system.startup"

        # Unknown domain defaults to system
        assert nats_bus._get_subject_for_event_type("unknown.event") == "system.unknown.event"

    async def test_nats_bus_publish_success(self, nats_bus: NATSEventBus, sample_event: Event):
        """Test successful event publishing to NATS."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())

            # Mock publish operation
            mock_ack = MagicMock()
            mock_ack.stream = "TRADING"
            mock_ack.seq = 123
            mock_jetstream.publish.return_value = mock_ack

            # Initialize bus
            await nats_bus.initialize()

            # Publish event
            result = await nats_bus.publish(sample_event)

            assert result.success is True
            assert result.event_id == sample_event.id
            assert result.message_id == "TRADING:123"

            # Verify publish was called with correct parameters
            mock_jetstream.publish.assert_called_once()
            call_args = mock_jetstream.publish.call_args
            assert call_args.kwargs["subject"] == "trading.trading.order.created"

    async def test_nats_bus_publish_not_initialized(
        self, nats_bus: NATSEventBus, sample_event: Event
    ):
        """Test publishing when bus is not initialized."""
        result = await nats_bus.publish(sample_event)

        assert result.success is False
        assert result.error == "NATS EventBus not initialized"

    async def test_nats_bus_publish_failure(self, nats_bus: NATSEventBus, sample_event: Event):
        """Test publishing failure handling."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())

            # Mock publish failure
            mock_jetstream.publish.side_effect = Exception("Publish failed")

            # Initialize bus
            await nats_bus.initialize()

            # Publish event
            result = await nats_bus.publish(sample_event)

            assert result.success is False
            assert "Publish failed" in result.error

    async def test_nats_bus_subscribe(self, nats_bus: NATSEventBus):
        """Test event subscription."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())
            mock_jetstream.pull_subscribe.return_value = MagicMock()

            # Initialize bus
            await nats_bus.initialize()

            # Create test handler
            received_events = []

            class TestHandler:
                async def handle(self, event: Event):
                    received_events.append(event)

            handler = TestHandler()

            # Subscribe
            subscription_id = await nats_bus.subscribe("trading.order.created", handler)

            assert subscription_id is not None
            assert subscription_id.id in nats_bus._subscriptions
            assert nats_bus._subscriptions[subscription_id.id] == "trading.order.created"
            assert "trading.order.created" in nats_bus._subscribers

    async def test_nats_bus_subscribe_not_initialized(self, nats_bus: NATSEventBus):
        """Test subscribing when bus is not initialized."""

        class TestHandler:
            async def handle(self, event: Event):
                pass

        handler = TestHandler()

        with pytest.raises(RuntimeError, match="NATS EventBus not initialized"):
            await nats_bus.subscribe("test.event", handler)

    async def test_nats_bus_unsubscribe(self, nats_bus: NATSEventBus):
        """Test event unsubscription."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())
            mock_jetstream.pull_subscribe.return_value = MagicMock()

            # Initialize bus
            await nats_bus.initialize()

            # Create test handler
            class TestHandler:
                async def handle(self, event: Event):
                    pass

            handler = TestHandler()

            # Subscribe then unsubscribe
            subscription_id = await nats_bus.subscribe("test.event", handler)
            result = await nats_bus.unsubscribe(subscription_id)

            assert result is True
            assert subscription_id.id not in nats_bus._subscriptions

    async def test_nats_bus_unsubscribe_invalid_id(self, nats_bus: NATSEventBus):
        """Test unsubscribing with invalid subscription ID."""
        from xline.core.events.bus import SubscriptionId

        invalid_id = SubscriptionId(id="invalid-id")
        result = await nats_bus.unsubscribe(invalid_id)

        assert result is False

    async def test_nats_bus_cleanup(self, nats_bus: NATSEventBus):
        """Test NATS bus cleanup."""
        with patch("nats.connect") as mock_connect:
            mock_client = AsyncMock()
            mock_jetstream = AsyncMock()
            mock_client.jetstream = MagicMock(return_value=mock_jetstream)
            mock_client.is_closed = False
            mock_connect.return_value = mock_client

            # Mock stream operations
            mock_jetstream.stream_info.side_effect = Exception("Stream not found")
            mock_jetstream.add_stream = AsyncMock(return_value=MagicMock())

            # Initialize bus
            await nats_bus.initialize()
            assert nats_bus._initialized is True

            # Cleanup
            await nats_bus.cleanup()

            assert nats_bus._initialized is False
            assert nats_bus._client is None
            assert nats_bus._jetstream is None
            assert len(nats_bus._subscribers) == 0
            assert len(nats_bus._subscriptions) == 0
            mock_client.close.assert_called_once()

    async def test_stream_configurations(self, nats_bus: NATSEventBus):
        """Test that stream configurations are properly defined."""
        configs = nats_bus._stream_configs

        # Check all required streams are configured
        assert "TRADING" in configs
        assert "RISK" in configs
        assert "ACCOUNTS" in configs
        assert "SYSTEM" in configs

        # Check TRADING stream config
        trading_config = configs["TRADING"]
        assert trading_config.name == "TRADING"
        assert "trading.>" in trading_config.subjects
        assert trading_config.max_msgs == 1000000
        assert trading_config.storage == "file"

        # Check RISK stream config
        risk_config = configs["RISK"]
        assert risk_config.name == "RISK"
        assert "risk.>" in risk_config.subjects

    async def test_callback_functions(self, nats_bus: NATSEventBus):
        """Test NATS callback functions."""
        # Test error callback
        await nats_bus._error_callback(Exception("Test error"))
        # Should log error without raising

        # Test disconnected callback
        await nats_bus._disconnected_callback()
        # Should log warning without raising

        # Test reconnected callback
        await nats_bus._reconnected_callback()
        # Should log info without raising
