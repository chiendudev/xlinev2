# AI AGENT IMPLEMENTATION TEMPLATES FOR WEEK 1
# Reference templates cho AI Agent để implement đúng standards

## 🔧 PYPROJECT.TOML TEMPLATE

```toml
[tool.poetry]
name = "xline-enterprise"
version = "0.1.0"
description = "XlineV2 Enterprise Trading System"
authors = ["XlineV2 Team"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
redis = "^5.0.1"
nats-py = "^2.6.0"
pydantic = "^2.5.0"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
asyncpg = "^0.29.0"
structlog = "^23.2.0"
opentelemetry-api = "^1.21.0"
opentelemetry-sdk = "^1.21.0"
opentelemetry-exporter-jaeger = "^1.21.0"
opentelemetry-instrumentation-fastapi = "^0.42b0"
opentelemetry-instrumentation-sqlalchemy = "^0.42b0"
hvac = "^2.0.0"
aioboto3 = "^12.0.0"
psutil = "^5.9.6"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
pytest-xdist = "^3.5.0"
mypy = "^1.7.1"
black = "^23.11.0"
flake8 = "^6.1.0"
bandit = "^1.7.5"
pre-commit = "^3.6.0"
locust = "^2.17.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=xline --cov-report=term-missing --cov-fail-under=90"
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
strict = true
disallow_any_generics = true
disallow_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true

[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.flake8]
max-line-length = 100
max-complexity = 10
exclude = [".git", "__pycache__", "build", "dist"]
ignore = ["E203", "W503"]

[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101", "B601"]
```

## 🚌 EVENT BUS INTERFACE TEMPLATE

```python
# File: xline/core/events/bus.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, TypeVar, Generic
from dataclasses import dataclass
from uuid import uuid4, UUID
from datetime import datetime
import asyncio
import structlog
from enum import Enum

logger = structlog.get_logger(__name__)

# Type definitions
EventHandler = TypeVar('EventHandler')

@dataclass
class Event:
    """Base event class for all system events."""
    id: str
    type: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    version: str = "1.0"
    
    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = str(uuid4())

@dataclass
class PublishResult:
    """Result of event publishing operation."""
    success: bool
    event_id: str
    error: Optional[str] = None
    message_id: Optional[str] = None
    handlers_notified: int = 0

@dataclass
class SubscriptionId:
    """Unique identifier for event subscription."""
    id: str

class EventBusInterface(Protocol):
    """Protocol defining event bus interface that ALL implementations must follow."""
    
    async def initialize(self) -> bool:
        """Initialize the event bus."""
        ...
    
    async def health_check(self) -> bool:
        """Check if event bus is healthy."""
        ...
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        ...
    
    async def publish(self, event: Event) -> PublishResult:
        """Publish an event to the bus.
        
        Args:
            event: Event to publish
            
        Returns:
            PublishResult with success status and metadata
        """
        ...
    
    async def subscribe(self, event_type: str, handler: 'EventHandler') -> SubscriptionId:
        """Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Handler function to process events
            
        Returns:
            SubscriptionId for the subscription
        """
        ...
    
    async def unsubscribe(self, subscription_id: SubscriptionId) -> bool:
        """Unsubscribe from events.
        
        Args:
            subscription_id: Subscription to cancel
            
        Returns:
            True if successfully unsubscribed
        """
        ...

class EventHandler(Protocol):
    """Protocol for event handlers."""
    
    async def handle(self, event: Event) -> None:
        """Handle an event.
        
        Args:
            event: Event to process
        """
        ...
```

## 🔄 CIRCUIT BREAKER TEMPLATE

```python
# File: xline/core/patterns/circuit_breaker.py
import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Type, Union
import structlog

logger = structlog.get_logger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit breaker tripped
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass

class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient external calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Type[Exception], tuple] = Exception,
        name: Optional[str] = None
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker half-open", name=self.name)
                else:
                    raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self._last_failure_time:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker closed", name=self.name)
    
    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker opened",
                    name=self.name,
                    failure_count=self._failure_count
                )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

# Decorator for easy use
def circuit_breaker_async(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Union[Type[Exception], tuple] = Exception
):
    """Decorator for async functions with circuit breaker protection."""
    def decorator(func):
        cb = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=func.__name__
        )
        
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        return wrapper
    return decorator
```

## 🧪 TEST TEMPLATE

```python
# File: tests/core/events/test_event_bus.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime
from xline.core.events.bus import Event, EventBusInterface, EventHandler, PublishResult, SubscriptionId

@pytest.mark.asyncio
class TestEventBusInterface:
    """Test event bus interface compliance."""
    
    @pytest.fixture
    async def mock_event_bus(self) -> EventBusInterface:
        """Create mock event bus for testing."""
        # Return implementation based on what's available
        pass
    
    @pytest.fixture
    def sample_event(self) -> Event:
        """Create sample event for testing."""
        return Event(
            id=str(uuid4()),
            type="test.event",
            source="test",
            timestamp=datetime.utcnow(),
            data={"test": "data"}
        )
    
    async def test_event_bus_initialization(self, mock_event_bus):
        """Test event bus can be initialized."""
        result = await mock_event_bus.initialize()
        assert result is True
    
    async def test_health_check(self, mock_event_bus):
        """Test health check returns status."""
        await mock_event_bus.initialize()
        health = await mock_event_bus.health_check()
        assert isinstance(health, bool)
    
    async def test_publish_event(self, mock_event_bus, sample_event):
        """Test event publishing."""
        await mock_event_bus.initialize()
        result = await mock_event_bus.publish(sample_event)
        
        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.event_id == sample_event.id
    
    async def test_subscribe_and_receive(self, mock_event_bus, sample_event):
        """Test event subscription and receiving."""
        await mock_event_bus.initialize()
        
        received_events = []
        
        class TestHandler:
            async def handle(self, event: Event):
                received_events.append(event)
        
        handler = TestHandler()
        subscription_id = await mock_event_bus.subscribe("test.event", handler)
        
        assert isinstance(subscription_id, SubscriptionId)
        
        # Publish event
        await mock_event_bus.publish(sample_event)
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].id == sample_event.id
    
    async def test_unsubscribe(self, mock_event_bus):
        """Test unsubscribing from events."""
        await mock_event_bus.initialize()
        
        class TestHandler:
            async def handle(self, event: Event):
                pass
        
        handler = TestHandler()
        subscription_id = await mock_event_bus.subscribe("test.event", handler)
        
        result = await mock_event_bus.unsubscribe(subscription_id)
        assert result is True
    
    async def test_cleanup(self, mock_event_bus):
        """Test cleanup releases resources."""
        await mock_event_bus.initialize()
        await mock_event_bus.cleanup()
        
        # After cleanup, health check should indicate not healthy
        health = await mock_event_bus.health_check()
        assert health is False
```

## 🐳 DOCKER COMPOSE TEMPLATE

```yaml
# File: docker-compose.dev.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  nats:
    image: nats:2.10-alpine
    ports:
      - "4222:4222"
      - "8222:8222"
    command: ["-js", "-m", "8222"]
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8222/varz"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: xline_dev
      POSTGRES_USER: xline
      POSTGRES_PASSWORD: xline_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U xline"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  postgres_data:
```

## 📊 MONITORING CONFIG TEMPLATE

```yaml
# File: infrastructure/observability/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'xline-enterprise'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:6379']
      
  - job_name: 'nats'
    static_configs:
      - targets: ['localhost:8222']
    metrics_path: '/varz'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```
