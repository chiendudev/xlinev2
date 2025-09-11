"""
Strategy Bridge for Xline Trading System
File: xline/core/adapters/strategy_bridge.py

Dynamic strategy deployment and lifecycle management with event integration.
"""

import asyncio
import logging
import uuid
from typing import Any

from xline.core.events.bus import InMemoryEventBus
from xline.core.events.types import EventType, SystemEvent

logger = logging.getLogger(__name__)


class StrategyBridge:
    """
    Dynamic strategy deployment and lifecycle management.
    
    Example usage:
        bridge = StrategyBridge(event_bus)
        strategy_id = await bridge.deploy_strategy(strategy_config)
        await bridge.start_strategy(strategy_id)
    """
    
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        """
        Initialize strategy bridge with event bus.
        
        Args:
            event_bus: InMemoryEventBus instance for event publishing
        """
        self.event_bus = event_bus
        self.deployed_strategies: dict[str, dict[str, Any]] = {}
        self.active_strategies: dict[str, bool] = {}
        self._lock = asyncio.Lock()
        
    async def deploy_strategy(self, strategy_config: dict[str, Any]) -> str:
        """
        Deploy new strategy with configuration validation.
        
        Args:
            strategy_config: Strategy configuration dictionary with required fields:
                - name: Strategy name (str)
                - class_name: Strategy class name (str)
                - parameters: Strategy parameters (dict)
                
        Returns:
            str: Unique strategy ID
            
        Raises:
            ValueError: If configuration is invalid or missing required fields
            
        Example:
            >>> config = {
            ...     "name": "MovingAverageCrossover",
            ...     "class_name": "MAStrategy",
            ...     "parameters": {"fast_period": 10, "slow_period": 20}
            ... }
            >>> strategy_id = await bridge.deploy_strategy(config)
            >>> assert strategy_id in bridge.deployed_strategies
        """
        try:
            async with self._lock:
                # Validate required fields
                required_fields = ["name", "class_name", "parameters"]
                for field in required_fields:
                    if field not in strategy_config:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate field types
                if not isinstance(strategy_config["name"], str):
                    raise ValueError("Strategy name must be a string")
                if not isinstance(strategy_config["class_name"], str):
                    raise ValueError("Strategy class_name must be a string")
                if not isinstance(strategy_config["parameters"], dict):
                    raise ValueError("Strategy parameters must be a dictionary")
                
                # Generate unique strategy ID
                strategy_id = str(uuid.uuid4())
                current_time = asyncio.get_event_loop().time()
                
                # Store strategy configuration
                self.deployed_strategies[strategy_id] = {
                    "id": strategy_id,
                    "config": strategy_config.copy(),
                    "deploy_time": current_time,
                    "status": "deployed",
                    "last_updated": current_time
                }
                
                # Initialize as inactive
                self.active_strategies[strategy_id] = False
                
                # Publish deployment event
                deploy_event = SystemEvent(
                    type=EventType.STRATEGY_DEPLOYED,
                    source="strategy_bridge",
                    component="strategy_manager",
                    status="deployed",
                    message=f"Strategy '{strategy_config['name']}' deployed successfully",
                    data={
                        "strategy_id": strategy_id,
                        "strategy_name": strategy_config["name"],
                        "strategy_class": strategy_config["class_name"],
                        "timestamp": current_time,
                        "parameters": strategy_config["parameters"]
                    }
                )
                await self.event_bus.publish(deploy_event)
                
                logger.info(f"Strategy deployed: {strategy_id} ({strategy_config['name']})")
                return strategy_id
                
        except Exception as e:
            logger.error(f"Failed to deploy strategy: {e}")
            raise
            
    async def start_strategy(self, strategy_id: str) -> bool:
        """
        Start deployed strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            
        Returns:
            bool: True if strategy started successfully
            
        Raises:
            ValueError: If strategy not found
            
        Example:
            >>> success = await bridge.start_strategy(strategy_id)
            >>> assert success is True
            >>> assert bridge.active_strategies[strategy_id] is True
        """
        try:
            async with self._lock:
                if strategy_id not in self.deployed_strategies:
                    raise ValueError(f"Strategy not found: {strategy_id}")
                    
                if self.active_strategies.get(strategy_id, False):
                    logger.warning(f"Strategy already active: {strategy_id}")
                    return True
                
                # Update strategy status
                self.active_strategies[strategy_id] = True
                self.deployed_strategies[strategy_id]["status"] = "active"
                self.deployed_strategies[strategy_id]["last_updated"] = asyncio.get_event_loop().time()
                
                # Publish start event
                start_event = SystemEvent(
                    type=EventType.STRATEGY_STARTED,
                    source="strategy_bridge",
                    component="strategy_manager",
                    status="started",
                    message=(
                        f"Strategy '{self.deployed_strategies[strategy_id]['config']['name']}' "
                        "started successfully"
                    ),
                    data={
                        "strategy_id": strategy_id,
                        "strategy_name": self.deployed_strategies[strategy_id]["config"]["name"],
                        "timestamp": asyncio.get_event_loop().time()
                    }
                )
                await self.event_bus.publish(start_event)
                
                logger.info(f"Strategy started: {strategy_id}")
                return True
                
        except ValueError:
            # Re-raise ValueError for not found cases
            raise
        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {e}")
            return False
            
    async def stop_strategy(self, strategy_id: str) -> bool:
        """
        Stop active strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            
        Returns:
            bool: True if strategy stopped successfully
            
        Raises:
            ValueError: If strategy not found
            
        Example:
            >>> success = await bridge.stop_strategy(strategy_id)
            >>> assert success is True
            >>> assert bridge.active_strategies[strategy_id] is False
        """
        try:
            async with self._lock:
                if strategy_id not in self.deployed_strategies:
                    raise ValueError(f"Strategy not found: {strategy_id}")
                
                # Update strategy status
                self.active_strategies[strategy_id] = False
                self.deployed_strategies[strategy_id]["status"] = "stopped"
                self.deployed_strategies[strategy_id]["last_updated"] = asyncio.get_event_loop().time()
                
                # Publish stop event
                stop_event = SystemEvent(
                    type=EventType.STRATEGY_STOPPED,
                    source="strategy_bridge",
                    component="strategy_manager",
                    status="stopped",
                    message=(
                        f"Strategy '{self.deployed_strategies[strategy_id]['config']['name']}' "
                        "stopped successfully"
                    ),
                    data={
                        "strategy_id": strategy_id,
                        "strategy_name": self.deployed_strategies[strategy_id]["config"]["name"],
                        "timestamp": asyncio.get_event_loop().time()
                    }
                )
                await self.event_bus.publish(stop_event)
                
                logger.info(f"Strategy stopped: {strategy_id}")
                return True
                
        except ValueError:
            # Re-raise ValueError for not found cases
            raise
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return False
            
    async def undeploy_strategy(self, strategy_id: str) -> bool:
        """
        Remove deployed strategy completely.
        
        Args:
            strategy_id: Unique strategy identifier
            
        Returns:
            bool: True if strategy undeployed successfully
            
        Raises:
            ValueError: If strategy not found or still active
        """
        try:
            # First stop the strategy if it's active (without lock to avoid deadlock)
            if (strategy_id in self.deployed_strategies and
                self.active_strategies.get(strategy_id, False)):
                await self.stop_strategy(strategy_id)
            
            async with self._lock:
                if strategy_id not in self.deployed_strategies:
                    raise ValueError(f"Strategy not found: {strategy_id}")
                
                # Remove strategy from tracking
                del self.deployed_strategies[strategy_id]
                if strategy_id in self.active_strategies:
                    del self.active_strategies[strategy_id]
                
                logger.info(f"Strategy undeployed: {strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to undeploy strategy {strategy_id}: {e}")
            return False
            
    async def list_strategies(self) -> list[dict[str, Any]]:
        """
        List all deployed strategies.
        
        Returns:
            list[dict[str, Any]]: List of strategy configurations with status
            
        Example:
            >>> strategies = await bridge.list_strategies()
            >>> assert isinstance(strategies, list)
            >>> if strategies:
            ...     assert "id" in strategies[0]
            ...     assert "status" in strategies[0]
        """
        async with self._lock:
            strategies = []
            for strategy_id, strategy_info in self.deployed_strategies.items():
                strategy_copy = strategy_info.copy()
                strategy_copy["active"] = self.active_strategies.get(strategy_id, False)
                strategies.append(strategy_copy)
            return strategies
        
    async def get_strategy_status(self, strategy_id: str) -> dict[str, Any]:
        """
        Get detailed strategy status.
        
        Args:
            strategy_id: Unique strategy identifier
            
        Returns:
            dict[str, Any]: Detailed strategy status information
            
        Raises:
            ValueError: If strategy not found
            
        Example:
            >>> status = await bridge.get_strategy_status(strategy_id)
            >>> assert status["id"] == strategy_id
            >>> assert "active" in status
            >>> assert "config" in status
        """
        async with self._lock:
            if strategy_id not in self.deployed_strategies:
                raise ValueError(f"Strategy not found: {strategy_id}")
                
            strategy = self.deployed_strategies[strategy_id]
            return {
                "id": strategy_id,
                "status": strategy["status"],
                "active": self.active_strategies.get(strategy_id, False),
                "config": strategy["config"].copy(),
                "deploy_time": strategy["deploy_time"],
                "last_updated": strategy["last_updated"]
            }
    
    async def get_active_strategies(self) -> list[str]:
        """
        Get list of currently active strategy IDs.
        
        Returns:
            list[str]: List of active strategy IDs
        """
        async with self._lock:
            return [
                strategy_id for strategy_id, is_active 
                in self.active_strategies.items() 
                if is_active
            ]
    
    async def get_strategy_count(self) -> dict[str, int]:
        """
        Get count of strategies by status.
        
        Returns:
            dict[str, int]: Count of strategies by status
        """
        async with self._lock:
            active_count = sum(1 for is_active in self.active_strategies.values() if is_active)
            total_count = len(self.deployed_strategies)
            
            return {
                "total": total_count,
                "active": active_count,
                "inactive": total_count - active_count
            }
    
    async def update_strategy_config(
        self, 
        strategy_id: str, 
        new_config: dict[str, Any]
    ) -> bool:
        """
        Update strategy configuration (only when stopped).
        
        Args:
            strategy_id: Unique strategy identifier
            new_config: New configuration parameters
            
        Returns:
            bool: True if update successful
            
        Raises:
            ValueError: If strategy not found or is active
        """
        try:
            async with self._lock:
                if strategy_id not in self.deployed_strategies:
                    raise ValueError(f"Strategy not found: {strategy_id}")
                
                if self.active_strategies.get(strategy_id, False):
                    raise ValueError("Cannot update configuration of active strategy")
                
                # Validate new configuration
                required_fields = ["name", "class_name", "parameters"]
                for field in required_fields:
                    if field not in new_config:
                        raise ValueError(f"Missing required field in new config: {field}")
                
                # Update configuration
                self.deployed_strategies[strategy_id]["config"] = new_config.copy()
                self.deployed_strategies[strategy_id]["last_updated"] = asyncio.get_event_loop().time()
                
                logger.info(f"Strategy configuration updated: {strategy_id}")
                return True
                
        except ValueError:
            # Re-raise ValueError for validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to update strategy config {strategy_id}: {e}")
            return False
    
    async def bulk_operation(
        self, 
        operation: str, 
        strategy_ids: list[str]
    ) -> dict[str, bool]:
        """
        Perform bulk operations on multiple strategies.
        
        Args:
            operation: Operation to perform ("start", "stop")
            strategy_ids: List of strategy IDs
            
        Returns:
            dict[str, bool]: Results for each strategy ID
        """
        results = {}
        
        for strategy_id in strategy_ids:
            try:
                if operation == "start":
                    results[strategy_id] = await self.start_strategy(strategy_id)
                elif operation == "stop":
                    results[strategy_id] = await self.stop_strategy(strategy_id)
                else:
                    results[strategy_id] = False
                    logger.error(f"Unknown operation: {operation}")
            except Exception as e:
                logger.error(f"Bulk operation {operation} failed for {strategy_id}: {e}")
                results[strategy_id] = False
        
        return results
    
    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on strategy bridge.
        
        Returns:
            dict[str, Any]: Health status information
        """
        try:
            counts = await self.get_strategy_count()
            active_strategies = await self.get_active_strategies()
            
            return {
                "status": "healthy",
                "total_strategies": counts["total"],
                "active_strategies": counts["active"],
                "inactive_strategies": counts["inactive"],
                "active_strategy_ids": active_strategies,
                "event_bus_connected": self.event_bus is not None
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
