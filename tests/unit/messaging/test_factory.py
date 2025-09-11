"""Tests for messaging factory."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from xline.infrastructure.messaging.factory import MessageBusFactory, get_message_bus


class TestMessageBusFactory:
    """Test suite for MessageBusFactory."""

    def teardown_method(self):
        """Reset factory singleton between tests."""
        MessageBusFactory._instance = None
        MessageBusFactory._message_bus = None
        MessageBusFactory._connected = False

    def test_singleton_pattern(self):
        """Test factory uses singleton pattern."""
        factory1 = MessageBusFactory()
        factory2 = MessageBusFactory()
        assert factory1 is factory2

    @patch.dict(os.environ, {'XLINE_MESSAGE_BUS': 'redis'})
    async def test_create_redis_bus(self):
        """Test creating Redis event bus."""
        factory = MessageBusFactory()
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus') as mock_redis:
            mock_instance = AsyncMock()
            mock_redis.return_value = mock_instance
            
            bus = await factory.create_bus()
            assert bus == mock_instance
            mock_redis.assert_called_once()

    @patch.dict(os.environ, {'XLINE_MESSAGE_BUS': 'nats'})
    async def test_create_nats_bus_not_available(self):
        """Test creating NATS bus when not available."""
        factory = MessageBusFactory()
        with patch('xline.infrastructure.messaging.factory._get_nats_event_bus', return_value=None):
            with pytest.raises(RuntimeError, match="NATS backend not available"):
                await factory.create_bus()

    @patch.dict(os.environ, {'XLINE_MESSAGE_BUS': 'invalid'})
    async def test_create_bus_invalid_backend(self):
        """Test creating bus with invalid backend."""
        factory = MessageBusFactory()
        with pytest.raises(ValueError, match="Unsupported message bus backend"):
            await factory.create_bus()

    async def test_get_message_bus_creates_new(self):
        """Test get_message_bus creates new instance."""
        factory = MessageBusFactory()
        with patch.object(factory, 'create_bus') as mock_create:
            mock_instance = AsyncMock()
            mock_create.return_value = mock_instance
            
            bus = await factory.get_message_bus()
            assert bus == mock_instance
            mock_create.assert_called_once()

    async def test_get_message_bus_returns_existing(self):
        """Test get_message_bus returns existing instance."""
        factory = MessageBusFactory()
        factory._message_bus = AsyncMock()
        
        bus = await factory.get_message_bus()
        assert bus == factory._message_bus

    async def test_close_bus(self):
        """Test closing bus."""
        factory = MessageBusFactory()
        mock_bus = AsyncMock()
        factory._message_bus = mock_bus
        factory._connected = True
        
        await factory.close()
        mock_bus.close.assert_called_once()
        assert factory._message_bus is None
        assert factory._connected is False


class TestGlobalFunctions:
    """Test global factory functions."""

    def teardown_method(self):
        """Reset factory singleton between tests."""
        MessageBusFactory._instance = None
        MessageBusFactory._message_bus = None
        MessageBusFactory._connected = False

    async def test_get_message_bus_function(self):
        """Test global get_message_bus function."""
        with patch.object(MessageBusFactory, 'get_message_bus') as mock_get:
            mock_instance = AsyncMock()
            mock_get.return_value = mock_instance
            
            bus = await get_message_bus()
            assert bus == mock_instance

    async def test_create_bus_function(self):
        """Test get message bus via factory."""
        with patch.object(MessageBusFactory, 'get_message_bus') as mock_get:
            mock_instance = AsyncMock()
            mock_get.return_value = mock_instance
            
            bus = await get_message_bus()
            assert bus == mock_instance
