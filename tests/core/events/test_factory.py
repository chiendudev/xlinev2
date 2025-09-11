"""
Comprehensive test coverage for factory.py to achieve 95%+ coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from xline.core.events.factory import EventBusFactory
from xline.core.patterns.factory import ComponentTier


class TestFactory:
    """Comprehensive factory tests for 95%+ coverage"""

    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = EventBusFactory()
        assert factory is not None
        assert factory.redis_url == "redis://localhost:6379/0"
        assert factory.nats_url == "nats://localhost:4222"
        assert factory.cluster_name == "xline-cluster"

    def test_factory_initialization_with_custom_params(self):
        """Test factory initialization with custom parameters."""
        factory = EventBusFactory(
            redis_url="redis://custom:6380/1",
            nats_url="nats://custom:4223",
            cluster_name="custom-cluster",
            max_retries=5,
            retry_delay=2.0
        )
        assert factory.redis_url == "redis://custom:6380/1"
        assert factory.nats_url == "nats://custom:4223"
        assert factory.cluster_name == "custom-cluster"

    @pytest.mark.asyncio
    async def test_factory_create_mock_implementation(self):
        """Test factory create mock implementation."""
        factory = EventBusFactory()
        
        # Test create mock implementation directly (lines 120-126)
        result = await factory._create_mock_implementation()
        assert result is not None
        assert hasattr(result, 'initialize')

    @pytest.mark.asyncio
    async def test_factory_create_mock_implementation_with_dlq_disabled(self):
        """Test factory create mock implementation with DLQ disabled."""
        factory = EventBusFactory()
        
        # Test create mock implementation with DLQ disabled
        result = await factory._create_mock_implementation(enable_dlq=False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_factory_create_production_implementation_redis_import_error(self):
        """Test production implementation when Redis dependencies missing (lines 50-67)."""
        factory = EventBusFactory()

        # Mock ImportError for Redis dependencies directly at import location
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus', side_effect=ImportError("redis dependency missing")):
            with pytest.raises(ImportError):
                await factory._create_production_implementation()    @pytest.mark.asyncio
    async def test_factory_create_production_implementation_redis_init_fail(self):
        """Test production implementation when Redis initialization fails (lines 58-59)."""
        factory = EventBusFactory()

        # Mock Redis EventBus that fails to initialize
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus') as mock_redis_cls:
            mock_bus = AsyncMock()
            mock_bus.initialize.return_value = False
            mock_redis_cls.return_value = mock_bus

            with pytest.raises(RuntimeError, match="Failed to initialize Redis EventBus"):
                await factory._create_production_implementation()

    @pytest.mark.asyncio
    async def test_factory_create_production_implementation_redis_success(self):
        """Test successful production implementation creation (lines 50-65)."""
        factory = EventBusFactory()

        # Mock successful Redis EventBus
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus') as mock_redis_cls:
            mock_bus = AsyncMock()
            mock_bus.initialize.return_value = True
            mock_redis_cls.return_value = mock_bus

            result = await factory._create_production_implementation()
            assert result is mock_bus
            mock_redis_cls.assert_called_once_with(
                redis_url="redis://localhost:6379/0",
                max_retries=3
            )
            mock_bus.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_factory_create_production_implementation_redis_exception(self):
        """Test production implementation when Redis throws exception (lines 69-71)."""
        factory = EventBusFactory()

        # Mock Redis EventBus that throws exception
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus') as mock_redis_cls:
            mock_redis_cls.side_effect = RuntimeError("Redis connection failed")

            with pytest.raises(RuntimeError, match="Redis connection failed"):
                await factory._create_production_implementation()

    @pytest.mark.asyncio
    async def test_factory_create_development_implementation_nats_init_fail(self):
        """Test development implementation when NATS initialization fails (lines 93-94)."""
        factory = EventBusFactory()

        # Mock NATS EventBus that fails to initialize
        with patch('xline.infrastructure.messaging.nats.bus.NATSEventBus') as mock_nats_cls:
            mock_bus = AsyncMock()
            mock_bus.initialize.return_value = False
            mock_nats_cls.return_value = mock_bus

            with pytest.raises(RuntimeError, match="Failed to initialize NATS EventBus"):
                await factory._create_development_implementation()

    @pytest.mark.asyncio
    async def test_factory_create_development_implementation_nats_success(self):
        """Test successful development implementation creation (lines 85-100)."""
        factory = EventBusFactory()

        # Mock the NATSEventBus import to avoid actual network connection
        with patch('xline.core.events.factory.NATSEventBus') as mock_nats_cls:
            mock_bus = AsyncMock()
            mock_bus.initialize.return_value = True
            mock_nats_cls.return_value = mock_bus

            result = await factory._create_development_implementation()
            assert result is mock_bus
            mock_nats_cls.assert_called_once_with(
                nats_url="nats://localhost:4222",
                cluster_name="xline-cluster",
                max_retries=3,
                retry_delay=1.0,
            )
            mock_bus.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_factory_create_development_implementation_nats_exception(self):
        """Test development implementation when NATS throws exception (lines 104-106)."""
        factory = EventBusFactory()

        # Mock the NATSEventBus import to throw exception during instantiation
        with patch('xline.core.events.factory.NATSEventBus') as mock_nats_cls:
            mock_nats_cls.side_effect = RuntimeError("NATS connection failed")

            with pytest.raises(RuntimeError, match="NATS connection failed"):
                await factory._create_development_implementation()

    @pytest.mark.asyncio
    async def test_factory_create_production_implementation_general_exception(self):
        """Test production implementation Redis general exception (line 70)."""
        factory = EventBusFactory()

        # Mock Redis EventBus that throws a general exception (not initialization failure)
        with patch('xline.infrastructure.messaging.redis.bus.RedisEventBus') as mock_redis_cls:
            mock_redis_cls.side_effect = ValueError("Invalid Redis configuration")

            with pytest.raises(ValueError, match="Invalid Redis configuration"):
                await factory._create_production_implementation()

    @pytest.mark.asyncio
    async def test_factory_create_development_implementation_success_with_logging(self):
        """Test successful NATS creation with success logging (lines 97-102)."""
        factory = EventBusFactory()

        # Mock the NATSEventBus to capture success logging
        with patch('xline.core.events.factory.NATSEventBus') as mock_nats_cls:
            mock_bus = AsyncMock()
            mock_bus.initialize.return_value = True
            mock_nats_cls.return_value = mock_bus

            with patch('xline.core.events.factory.logger') as mock_logger:
                result = await factory._create_development_implementation()
                
                # Verify success logging was called (lines 97-102)
                mock_logger.info.assert_called_once_with(
                    "Development EventBus (NATS) created successfully",
                    nats_url="nats://localhost:4222",
                    cluster_name="xline-cluster",
                )
                assert result is mock_bus

    @pytest.mark.asyncio
    async def test_factory_create_with_mock_tier(self):
        """Test factory create with mock tier."""
        factory = EventBusFactory()

        with patch.object(factory, '_create_mock_implementation') as mock_create:
            mock_instance = Mock()
            mock_create.return_value = mock_instance

            result = await factory.create(ComponentTier.MOCK)
            assert result == mock_instance
            mock_create.assert_called_once()

    def test_component_tier_enum(self):
        """Test ComponentTier enum values."""
        assert ComponentTier.DEVELOPMENT.value == "development"
        assert ComponentTier.PRODUCTION.value == "production"
        assert ComponentTier.MOCK.value == "mock"
