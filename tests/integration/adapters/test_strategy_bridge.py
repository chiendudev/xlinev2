"""
Integration tests for StrategyBridge
File: tests/integration/adapters/test_strategy_bridge.py

Tests strategy lifecycle management and event integration.
"""

import asyncio
from typing import Any

import pytest

from xline.core.adapters.strategy_bridge import StrategyBridge
from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import Event, EventType


class TestStrategyBridge:
    """Integration test cases for StrategyBridge class."""

    @pytest.fixture
    async def event_bus(self) -> InMemoryEventBus:
        """Create and initialize event bus for testing."""
        bus = InMemoryEventBus()
        await bus.initialize()
        return bus

    @pytest.fixture
    async def strategy_bridge(self, event_bus: InMemoryEventBus) -> StrategyBridge:
        """Create strategy bridge for testing."""
        return StrategyBridge(event_bus)

    @pytest.fixture
    def sample_strategy_config(self) -> dict[str, Any]:
        """Sample strategy configuration for testing."""
        return {
            "name": "TestStrategy",
            "class_name": "TestStrategyClass",
            "parameters": {
                "param1": "value1",
                "param2": 42,
                "param3": True
            }
        }

    async def test_deploy_strategy_success(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test successful strategy deployment."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Verify strategy ID is returned
        assert isinstance(strategy_id, str)
        assert len(strategy_id) > 0
        
        # Verify strategy is in deployed strategies
        assert strategy_id in strategy_bridge.deployed_strategies
        
        # Verify strategy configuration
        deployed_strategy = strategy_bridge.deployed_strategies[strategy_id]
        assert deployed_strategy["id"] == strategy_id
        assert deployed_strategy["config"] == sample_strategy_config
        assert deployed_strategy["status"] == "deployed"
        assert "deploy_time" in deployed_strategy
        
        # Verify strategy is initially inactive
        assert strategy_bridge.active_strategies[strategy_id] is False

    async def test_deploy_strategy_missing_required_fields(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test strategy deployment with missing required fields."""
        # Missing 'name' field
        incomplete_config = {
            "class_name": "TestClass",
            "parameters": {}
        }
        
        with pytest.raises(ValueError, match="Missing required field: name"):
            await strategy_bridge.deploy_strategy(incomplete_config)
        
        # Missing 'class_name' field
        incomplete_config = {
            "name": "TestStrategy",
            "parameters": {}
        }
        
        with pytest.raises(ValueError, match="Missing required field: class_name"):
            await strategy_bridge.deploy_strategy(incomplete_config)
        
        # Missing 'parameters' field
        incomplete_config = {
            "name": "TestStrategy",
            "class_name": "TestClass"
        }
        
        with pytest.raises(ValueError, match="Missing required field: parameters"):
            await strategy_bridge.deploy_strategy(incomplete_config)

    async def test_deploy_strategy_invalid_field_types(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test strategy deployment with invalid field types."""
        # Invalid name type
        invalid_config = {
            "name": 123,  # Should be string
            "class_name": "TestClass",
            "parameters": {}
        }
        
        with pytest.raises(ValueError, match="Strategy name must be a string"):
            await strategy_bridge.deploy_strategy(invalid_config)
        
        # Invalid class_name type
        invalid_config = {
            "name": "TestStrategy",
            "class_name": 123,  # Should be string
            "parameters": {}
        }
        
        with pytest.raises(ValueError, match="Strategy class_name must be a string"):
            await strategy_bridge.deploy_strategy(invalid_config)
        
        # Invalid parameters type
        invalid_config = {
            "name": "TestStrategy",
            "class_name": "TestClass",
            "parameters": "not_a_dict"  # Should be dict
        }
        
        with pytest.raises(ValueError, match="Strategy parameters must be a dictionary"):
            await strategy_bridge.deploy_strategy(invalid_config)

    async def test_start_strategy_success(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test successful strategy start."""
        # Deploy strategy first
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Start strategy
        result = await strategy_bridge.start_strategy(strategy_id)
        
        # Verify start was successful
        assert result is True
        
        # Verify strategy is active
        assert strategy_bridge.active_strategies[strategy_id] is True
        
        # Verify strategy status updated
        deployed_strategy = strategy_bridge.deployed_strategies[strategy_id]
        assert deployed_strategy["status"] == "active"

    async def test_start_strategy_not_found(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test starting non-existent strategy."""
        with pytest.raises(ValueError, match="Strategy not found"):
            await strategy_bridge.start_strategy("non_existent_id")

    async def test_start_already_active_strategy(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test starting already active strategy."""
        # Deploy and start strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Try to start again
        result = await strategy_bridge.start_strategy(strategy_id)
        
        # Should return True without error
        assert result is True
        assert strategy_bridge.active_strategies[strategy_id] is True

    async def test_stop_strategy_success(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test successful strategy stop."""
        # Deploy and start strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Stop strategy
        result = await strategy_bridge.stop_strategy(strategy_id)
        
        # Verify stop was successful
        assert result is True
        
        # Verify strategy is inactive
        assert strategy_bridge.active_strategies[strategy_id] is False
        
        # Verify strategy status updated
        deployed_strategy = strategy_bridge.deployed_strategies[strategy_id]
        assert deployed_strategy["status"] == "stopped"

    async def test_stop_strategy_not_found(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test stopping non-existent strategy."""
        with pytest.raises(ValueError, match="Strategy not found"):
            await strategy_bridge.stop_strategy("non_existent_id")

    async def test_undeploy_strategy_success(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test successful strategy undeployment."""
        # Deploy and start strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Undeploy strategy
        result = await strategy_bridge.undeploy_strategy(strategy_id)
        
        # Verify undeploy was successful
        assert result is True
        
        # Verify strategy is removed
        assert strategy_id not in strategy_bridge.deployed_strategies
        assert strategy_id not in strategy_bridge.active_strategies

    async def test_list_strategies(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test listing all strategies."""
        # Initially empty
        strategies = await strategy_bridge.list_strategies()
        assert strategies == []
        
        # Deploy multiple strategies
        strategy_id1 = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        config2 = sample_strategy_config.copy()
        config2["name"] = "TestStrategy2"
        await strategy_bridge.deploy_strategy(config2)
        
        # Start one strategy
        await strategy_bridge.start_strategy(strategy_id1)
        
        # List strategies
        strategies = await strategy_bridge.list_strategies()
        
        # Verify both strategies are listed
        assert len(strategies) == 2
        
        # Find strategies by name
        strategy1 = next(s for s in strategies if s["config"]["name"] == "TestStrategy")
        strategy2 = next(s for s in strategies if s["config"]["name"] == "TestStrategy2")
        
        # Verify strategy1 (active)
        assert strategy1["active"] is True
        assert strategy1["status"] == "active"
        assert strategy1["config"]["name"] == "TestStrategy"
        
        # Verify strategy2 (inactive)
        assert strategy2["active"] is False
        assert strategy2["status"] == "deployed"
        assert strategy2["config"]["name"] == "TestStrategy2"

    async def test_get_strategy_status(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test getting strategy status."""
        # Deploy strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Get status
        status = await strategy_bridge.get_strategy_status(strategy_id)
        
        # Verify status information
        assert status["id"] == strategy_id
        assert status["status"] == "deployed"
        assert status["active"] is False
        assert status["config"] == sample_strategy_config
        assert "deploy_time" in status
        assert "last_updated" in status

    async def test_get_strategy_status_not_found(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test getting status of non-existent strategy."""
        with pytest.raises(ValueError, match="Strategy not found"):
            await strategy_bridge.get_strategy_status("non_existent_id")

    async def test_get_active_strategies(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test getting list of active strategies."""
        # Initially empty
        active_strategies = await strategy_bridge.get_active_strategies()
        assert active_strategies == []
        
        # Deploy multiple strategies
        strategy_id1 = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        config2 = sample_strategy_config.copy()
        config2["name"] = "TestStrategy2"
        strategy_id2 = await strategy_bridge.deploy_strategy(config2)
        
        # Start only one strategy
        await strategy_bridge.start_strategy(strategy_id1)
        
        # Get active strategies
        active_strategies = await strategy_bridge.get_active_strategies()
        
        # Verify only one active strategy
        assert len(active_strategies) == 1
        assert strategy_id1 in active_strategies
        assert strategy_id2 not in active_strategies

    async def test_get_strategy_count(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test getting strategy counts."""
        # Initially empty
        counts = await strategy_bridge.get_strategy_count()
        assert counts == {"total": 0, "active": 0, "inactive": 0}
        
        # Deploy strategies
        strategy_id1 = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        config2 = sample_strategy_config.copy()
        config2["name"] = "TestStrategy2"
        await strategy_bridge.deploy_strategy(config2)
        
        # Start one strategy
        await strategy_bridge.start_strategy(strategy_id1)
        
        # Get counts
        counts = await strategy_bridge.get_strategy_count()
        
        # Verify counts
        assert counts["total"] == 2
        assert counts["active"] == 1
        assert counts["inactive"] == 1

    async def test_update_strategy_config(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test updating strategy configuration."""
        # Deploy strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # New configuration
        new_config = {
            "name": "UpdatedStrategy",
            "class_name": "UpdatedClass",
            "parameters": {"new_param": "new_value"}
        }
        
        # Update configuration
        result = await strategy_bridge.update_strategy_config(strategy_id, new_config)
        
        # Verify update was successful
        assert result is True
        
        # Verify configuration was updated
        deployed_strategy = strategy_bridge.deployed_strategies[strategy_id]
        assert deployed_strategy["config"] == new_config

    async def test_update_strategy_config_active_strategy(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test updating configuration of active strategy (should fail)."""
        # Deploy and start strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Try to update configuration
        new_config = sample_strategy_config.copy()
        new_config["name"] = "UpdatedStrategy"
        
        with pytest.raises(ValueError, match="Cannot update configuration of active strategy"):
            await strategy_bridge.update_strategy_config(strategy_id, new_config)

    async def test_bulk_operation_start(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test bulk start operation."""
        # Deploy multiple strategies
        strategy_id1 = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        config2 = sample_strategy_config.copy()
        config2["name"] = "TestStrategy2"
        strategy_id2 = await strategy_bridge.deploy_strategy(config2)
        
        # Bulk start
        results = await strategy_bridge.bulk_operation("start", [strategy_id1, strategy_id2])
        
        # Verify results
        assert results[strategy_id1] is True
        assert results[strategy_id2] is True
        
        # Verify both strategies are active
        assert strategy_bridge.active_strategies[strategy_id1] is True
        assert strategy_bridge.active_strategies[strategy_id2] is True

    async def test_bulk_operation_stop(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test bulk stop operation."""
        # Deploy and start multiple strategies
        strategy_id1 = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        config2 = sample_strategy_config.copy()
        config2["name"] = "TestStrategy2"
        strategy_id2 = await strategy_bridge.deploy_strategy(config2)
        
        await strategy_bridge.start_strategy(strategy_id1)
        await strategy_bridge.start_strategy(strategy_id2)
        
        # Bulk stop
        results = await strategy_bridge.bulk_operation("stop", [strategy_id1, strategy_id2])
        
        # Verify results
        assert results[strategy_id1] is True
        assert results[strategy_id2] is True
        
        # Verify both strategies are inactive
        assert strategy_bridge.active_strategies[strategy_id1] is False
        assert strategy_bridge.active_strategies[strategy_id2] is False

    async def test_bulk_operation_invalid_operation(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test bulk operation with invalid operation."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        results = await strategy_bridge.bulk_operation("invalid_op", [strategy_id])
        
        assert results[strategy_id] is False

    async def test_health_check_healthy(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test health check with healthy system."""
        # Deploy and start strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Health check
        health = await strategy_bridge.health_check()
        
        # Verify health status
        assert health["status"] == "healthy"
        assert health["total_strategies"] == 1
        assert health["active_strategies"] == 1
        assert health["inactive_strategies"] == 0
        assert strategy_id in health["active_strategy_ids"]
        assert health["event_bus_connected"] is True

    async def test_concurrent_strategy_operations(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test concurrent strategy operations."""
        # Deploy multiple strategies concurrently
        configs = []
        for i in range(5):
            config = sample_strategy_config.copy()
            config["name"] = f"TestStrategy{i}"
            configs.append(config)
        
        # Deploy all strategies concurrently
        deploy_tasks = [
            strategy_bridge.deploy_strategy(config) 
            for config in configs
        ]
        strategy_ids = await asyncio.gather(*deploy_tasks)
        
        # Verify all strategies deployed
        assert len(strategy_ids) == 5
        assert len(strategy_bridge.deployed_strategies) == 5
        
        # Start all strategies concurrently
        start_tasks = [
            strategy_bridge.start_strategy(strategy_id) 
            for strategy_id in strategy_ids
        ]
        results = await asyncio.gather(*start_tasks)
        
        # Verify all strategies started
        assert all(results)
        assert len(await strategy_bridge.get_active_strategies()) == 5

    async def test_event_publishing(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test that events are properly published to event bus."""
        # Mock event handler to capture events
        published_events = []
        
        class MockHandler:
            async def handle(self, event: Event) -> None:
                published_events.append(event)
        
        mock_handler = MockHandler()
        
        # Subscribe to all strategy events
        await strategy_bridge.event_bus.subscribe(EventType.STRATEGY_DEPLOYED, mock_handler)
        await strategy_bridge.event_bus.subscribe(EventType.STRATEGY_STARTED, mock_handler)
        await strategy_bridge.event_bus.subscribe(EventType.STRATEGY_STOPPED, mock_handler)
        
        # Deploy, start, and stop strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        await strategy_bridge.stop_strategy(strategy_id)
        
        # Give some time for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify events were published
        assert len(published_events) == 3
        
        # Verify event types and data
        deploy_event = published_events[0]
        start_event = published_events[1]
        stop_event = published_events[2]
        
        assert deploy_event.type == EventType.STRATEGY_DEPLOYED
        assert deploy_event.source == "strategy_bridge"
        assert deploy_event.data["strategy_id"] == strategy_id
        
        assert start_event.type == EventType.STRATEGY_STARTED
        assert start_event.source == "strategy_bridge"
        assert start_event.data["strategy_id"] == strategy_id
        
        assert stop_event.type == EventType.STRATEGY_STOPPED
        assert stop_event.source == "strategy_bridge"
        assert stop_event.data["strategy_id"] == strategy_id

    async def test_thread_safety_with_locks(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test thread safety with concurrent access."""
        # Multiple concurrent operations on same strategy
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Attempt concurrent start/stop operations
        async def toggle_strategy() -> list[bool]:
            results = []
            for _ in range(10):
                start_result = await strategy_bridge.start_strategy(strategy_id)
                stop_result = await strategy_bridge.stop_strategy(strategy_id)
                results.extend([start_result, stop_result])
            return results
        
        # Run multiple toggle operations concurrently
        tasks = [toggle_strategy() for _ in range(3)]
        all_results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded (no race conditions)
        for results in all_results:
            assert all(results)
        
        # Verify final state is consistent
        status = await strategy_bridge.get_strategy_status(strategy_id)
        assert status["id"] == strategy_id
        assert status["active"] in [True, False]  # Either state is valid

    async def test_start_strategy_exception_handling(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test lines 178-180 - exception handling in start_strategy."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Mock a scenario that causes exception during event publishing
        from unittest.mock import patch

        with patch.object(
            strategy_bridge.event_bus,
            'publish',
            side_effect=RuntimeError("Event bus error")
        ):
            result = await strategy_bridge.start_strategy(strategy_id)
            assert result is False  # Should return False on exception

    async def test_stop_strategy_exception_handling(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test lines 234-236 - exception handling in stop_strategy."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        await strategy_bridge.start_strategy(strategy_id)
        
        # Mock a scenario that causes exception during event publishing
        from unittest.mock import patch

        with patch.object(
            strategy_bridge.event_bus,
            'publish',
            side_effect=RuntimeError("Event bus error")
        ):
            result = await strategy_bridge.stop_strategy(strategy_id)
            assert result is False  # Should return False on exception

    async def test_undeploy_strategy_validation_error(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test line 259 - validation error in undeploy_strategy."""
        # Try to undeploy non-existent strategy - should return False, not raise
        result = await strategy_bridge.undeploy_strategy("non_existent_id")
        assert result is False

    async def test_undeploy_strategy_exception_handling(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test lines 269-271 - exception handling in undeploy_strategy."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Mock a scenario that causes exception during undeployment
        from unittest.mock import patch

        # Start strategy first so it triggers stop_strategy in undeploy
        await strategy_bridge.start_strategy(strategy_id)

        with patch.object(
            strategy_bridge,
            'stop_strategy',
            side_effect=RuntimeError("Stop strategy error")
        ):
            result = await strategy_bridge.undeploy_strategy(strategy_id)
            assert result is False  # Should return False on exception

    async def test_update_strategy_config_validation_error(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test line 380 - validation error in update_strategy_config."""
        # Try to update non-existent strategy
        with pytest.raises(ValueError, match="Strategy not found"):
            await strategy_bridge.update_strategy_config("non_existent_id", {"new_param": "value"})

    async def test_update_strategy_config_exception_handling(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test line 389 - exception handling in update_strategy_config."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Use valid config with all required fields to avoid config validation error
        valid_config = {
            "name": "UpdatedTestStrategy",
            "class_name": "UpdatedTestStrategyClass",
            "parameters": {"new_param": "value"}
        }
        
        # Mock a scenario that causes exception
        import asyncio
        from unittest.mock import patch

        # Mock asyncio to cause exception in update_strategy_config
        with patch.object(
            asyncio,
            'get_event_loop',
            side_effect=RuntimeError("Event loop error")
        ):
            result = await strategy_bridge.update_strategy_config(strategy_id, valid_config)
            assert result is False  # Should return False on exception

    async def test_bulk_operation_invalid_operation_exception(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test lines 401-403 - exception handling in bulk_operation for invalid operation."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # The method logs error but returns results dict
        result = await strategy_bridge.bulk_operation("invalid_operation", [strategy_id])
        assert isinstance(result, dict)
        assert strategy_id in result
        assert result[strategy_id] is False  # Should be False for invalid operation

    async def test_bulk_operation_exception_handling(
        self,
        strategy_bridge: StrategyBridge,
        sample_strategy_config: dict[str, any]
    ) -> None:
        """Test lines 431-433 - general exception handling in bulk_operation."""
        strategy_id = await strategy_bridge.deploy_strategy(sample_strategy_config)
        
        # Use invalid operation to trigger exception handling
        result = await strategy_bridge.bulk_operation("invalid_op", [strategy_id])
        assert isinstance(result, dict)
        assert strategy_id in result
        assert result[strategy_id] is False  # Should return False on exception

    async def test_health_check_exception_handling(
        self,
        strategy_bridge: StrategyBridge
    ) -> None:
        """Test lines 456-458 - exception handling in health_check."""
        # Mock a scenario that causes exception
        from unittest.mock import patch

        with patch.object(
            strategy_bridge,
            'get_strategy_count',
            side_effect=RuntimeError("Internal error")
        ):
            result = await strategy_bridge.health_check()
            assert result["status"] == "unhealthy"  # Should return unhealthy on exception
            assert "error" in result
