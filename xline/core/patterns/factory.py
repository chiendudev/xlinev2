# File: xline/core/patterns/factory.py
"""
TieredComponentFactory pattern for reliable component instantiation with fallback strategies.
Implements production → development → mock fallback chain.
"""
from __future__ import annotations

import asyncio
import structlog
from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, TypeVar

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ComponentTier(Enum):
    """Component implementation tiers in fallback order."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    MOCK = "mock"


class TieredComponentFactory(ABC, Generic[T]):
    """
    Abstract factory for creating components with tiered fallback strategy.

    Fallback order: Production → Development → Mock
    The mock implementation MUST ALWAYS WORK and cannot fail.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._current_tier: ComponentTier | None = None
        self._current_implementation: T | None = None

    async def create(self, force_tier: ComponentTier | None = None) -> T:
        """
        Create component instance with fallback strategy.

        Args:
            force_tier: Force specific tier (for testing)

        Returns:
            Component instance

        Raises:
            RuntimeError: If all tiers fail (should never happen - mock must work)
        """
        if force_tier:
            instance = await self._create_for_tier(force_tier)
            self._current_tier = force_tier
            self._current_implementation = instance

            logger.info(
                "Component created successfully (forced tier)",
                tier=force_tier.value,
                component_type=type(self).__name__,
            )
            return instance  # Try production first
        for tier in ComponentTier:
            try:
                instance = await self._create_for_tier(tier)
                self._current_tier = tier
                self._current_implementation = instance

                logger.info(
                    "Component created successfully",
                    tier=tier.value,
                    component_type=type(self).__name__,
                )
                return instance

            except Exception as e:
                logger.warning(
                    "Failed to create component at tier",
                    tier=tier.value,
                    error=str(e),
                    component_type=type(self).__name__,
                )

                # If mock tier fails, this is a critical error
                if tier == ComponentTier.MOCK:
                    logger.critical(
                        "Mock implementation failed - this should never happen",
                        error=str(e),
                        component_type=type(self).__name__,
                    )
                    raise RuntimeError(f"Mock implementation failed: {e}")

                # Continue to next tier
                continue

        # This should never be reached due to mock fallback
        raise RuntimeError("All component tiers failed")

    async def _create_for_tier(self, tier: ComponentTier) -> T:
        """Create component for specific tier with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if tier == ComponentTier.PRODUCTION:
                    return await self._create_production_implementation()
                elif tier == ComponentTier.DEVELOPMENT:
                    return await self._create_development_implementation()
                elif tier == ComponentTier.MOCK:
                    return await self._create_mock_implementation()
                else:
                    raise ValueError(f"Unknown tier: {tier}")

            except Exception as e:
                last_exception = e
                logger.warning(
                    "Component creation attempt failed",
                    tier=tier.value,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )

                # Don't retry mock implementation - it should work immediately
                if tier == ComponentTier.MOCK:
                    raise

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        # All retries exhausted
        raise last_exception or RuntimeError(f"Failed to create {tier.value} implementation")

    @abstractmethod
    async def _create_production_implementation(self) -> T:
        """
        Create production implementation (e.g., Redis-based).

        Returns:
            Production component instance

        Raises:
            Exception: If production implementation cannot be created
        """
        ...

    @abstractmethod
    async def _create_development_implementation(self) -> T:
        """
        Create development implementation (e.g., NATS-based).

        Returns:
            Development component instance

        Raises:
            Exception: If development implementation cannot be created
        """
        ...

    @abstractmethod
    async def _create_mock_implementation(self) -> T:
        """
        Create mock implementation (e.g., in-memory).

        This implementation MUST ALWAYS WORK and cannot raise exceptions.
        It serves as the ultimate fallback.

        Returns:
            Mock component instance
        """
        ...

    @property
    def current_tier(self) -> ComponentTier | None:
        """Get current active tier."""
        return self._current_tier

    @property
    def current_implementation(self) -> T | None:
        """Get current implementation instance."""
        return self._current_implementation

    async def health_check(self) -> bool:
        """
        Check health of current implementation.

        Returns:
            True if healthy, False otherwise
        """
        if not self._current_implementation:
            return False

        try:
            # Try to call health_check method if available
            if hasattr(self._current_implementation, "health_check"):
                health_result = await self._current_implementation.health_check()
                return bool(health_result)
            else:
                # Basic check - if we have an implementation, assume healthy
                return True
        except Exception:
            return False

    async def restart_with_fallback(self) -> T:
        """
        Restart component with next tier if current fails.

        Returns:
            New component instance
        """
        if not self._current_tier:
            return await self.create()

        # Try next tier in fallback order
        current_index = list(ComponentTier).index(self._current_tier)
        remaining_tiers = list(ComponentTier)[current_index + 1 :]

        for tier in remaining_tiers:
            try:
                instance = await self._create_for_tier(tier)
                self._current_tier = tier
                self._current_implementation = instance

                logger.info(
                    "Component restarted with fallback tier",
                    new_tier=tier.value,
                    component_type=type(self).__name__,
                )
                return instance

            except Exception as e:
                logger.warning("Fallback tier also failed", tier=tier.value, error=str(e))
                continue

        # No fallback available
        raise RuntimeError("All fallback tiers exhausted")
