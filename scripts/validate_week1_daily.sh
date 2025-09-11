#!/bin/bash
# Week 1 Daily Validation Scripts for AI Agent
# File: scripts/validate_week1_daily.sh

set -e

DAY=${1:-1}
WEEK=1

echo "🔍 Validating Week $WEEK - Day $DAY Implementation..."

case $DAY in
    1)
        echo "📅 Day 1: Project Foundation & Event Bus Core"
        
        # Check project structure
        echo "📁 Checking project structure..."
        required_dirs=(
            "xline/core/events"
            "xline/core/adapters" 
            "xline/core/engine"
            "xline/enterprise/accounts"
            "xline/enterprise/auth"
            "xline/enterprise/risk"
            "xline/enterprise/analytics"
            "xline/enterprise/compliance"
            "xline/enterprise/secrets"
            "xline/infrastructure/observability"
            "xline/infrastructure/messaging"
            "xline/infrastructure/security"
            "xline/infrastructure/docker"
            "xline/infrastructure/kubernetes"
            "xline/api"
            "xline/web"
            "tests"
        )
        
        for dir in "${required_dirs[@]}"; do
            if [ ! -d "$dir" ]; then
                echo "❌ Missing directory: $dir"
                exit 1
            fi
            echo "✅ Directory exists: $dir"
        done
        
        # Check pyproject.toml exists and has required dependencies
        echo "📦 Checking pyproject.toml..."
        if [ ! -f "pyproject.toml" ]; then
            echo "❌ Missing pyproject.toml"
            exit 1
        fi
        
        required_deps=("fastapi" "uvicorn" "redis" "nats-py" "pydantic" "sqlalchemy" "asyncpg" "structlog" "opentelemetry-api" "hvac" "pytest" "pytest-asyncio" "pytest-cov" "mypy" "black")
        for dep in "${required_deps[@]}"; do
            if ! grep -q "$dep" pyproject.toml; then
                echo "❌ Missing dependency: $dep"
                exit 1
            fi
            echo "✅ Dependency found: $dep"
        done
        
        # Check event bus core exists
        echo "🚌 Checking event bus core..."
        if [ ! -f "xline/core/events/bus.py" ]; then
            echo "❌ Missing file: xline/core/events/bus.py"
            exit 1
        fi
        
        # Validate imports work
        echo "🔍 Testing imports..."
        .venv/bin/python -c "import xline.core.events.bus; print('✅ Event bus import successful')" || exit 1
        
        # Run basic tests
        echo "🧪 Running tests..."
        .venv/bin/python -m pytest tests/core/events/ --cov=95 || exit 1
        
        # Type checking
        echo "🔍 Type checking..."
        .venv/bin/python -m mypy xline/core/events/ --strict || exit 1
        
        echo "✅ Day 1 validation successful!"
        ;;
        
    2)
        echo "📅 Day 2: Redis Streams Implementation"
        
        # Check Redis implementation exists
        echo "🔍 Checking Redis implementation..."
        if [ ! -f "xline/infrastructure/messaging/redis/bus.py" ]; then
            echo "❌ Missing file: xline/infrastructure/messaging/redis/bus.py"
            exit 1
        fi
        
        # Check circuit breaker implementation
        echo "🔧 Checking circuit breaker..."
        if ! grep -q "CircuitBreaker" xline/infrastructure/messaging/redis/bus.py; then
            echo "❌ Missing CircuitBreaker implementation"
            exit 1
        fi
        
        # Check dead letter queue
        echo "📮 Checking DLQ implementation..."
        if ! grep -q "dlq" xline/infrastructure/messaging/redis/bus.py; then
            echo "❌ Missing Dead Letter Queue implementation"
            exit 1
        fi
        
        # Test Redis integration (if Redis available)
        echo "🧪 Testing Redis integration..."
        .venv/bin/python -c "
import asyncio
from xline.infrastructure.messaging.redis.bus import RedisEventBus
async def test():
    try:
        bus = RedisEventBus('redis://localhost:6379')
        result = await bus.initialize()
        print(f'✅ Redis initialization: {result}')
        health = await bus.health_check()
        print(f'✅ Redis health check: {health}')
        await bus.cleanup()
    except Exception as e:
        print(f'⚠️ Redis not available (expected in test environment): {e}')
asyncio.run(test())
"
        
        echo "✅ Day 2 validation successful!"
        ;;
        
    3)
        echo "📅 Day 3: NATS Alternative Implementation"
        
        # Check NATS implementation
        echo "🔍 Checking NATS implementation..."
        if [ ! -f "xline/infrastructure/messaging/nats/bus.py" ]; then
            echo "❌ Missing file: xline/infrastructure/messaging/nats/bus.py"
            exit 1
        fi
        
        # Check EventBusFactory
        echo "🏭 Checking EventBusFactory..."
        if [ ! -f "xline/core/events/factory.py" ]; then
            echo "❌ Missing file: xline/core/events/factory.py"
            exit 1
        fi
        
        # Check fallback chain implementation
        echo "🔄 Checking fallback chain..."
        if ! grep -q "TieredComponentFactory" xline/core/events/factory.py; then
            echo "❌ Missing TieredComponentFactory implementation"
            exit 1
        fi
        
        # Test failover logic
        echo "🧪 Testing failover logic..."
        .venv/bin/python -c "
import asyncio
from xline.core.events.factory import EventBusFactory
async def test():
    config = {'environment': 'test'}
    factory = EventBusFactory(config)
    bus = await factory.create_with_fallbacks()
    health = await bus.health_check()
    print(f'✅ Event bus failover test: {health}')
asyncio.run(test())
        "
        
        echo "✅ Day 3 validation successful!"
        ;;
        
    4)
        echo "📅 Day 4: Event Types & Serialization"
        
        # Check event types file
        echo "🏷️ Checking event types..."
        if [ ! -f "xline/core/events/types.py" ]; then
            echo "❌ Missing file: xline/core/events/types.py"
            exit 1
        fi
        
        # Check required event types exist
        required_events=("Event" "OrderEvent" "TradeEvent" "RiskEvent" "AccountEvent")
        for event in "${required_events[@]}"; do
            if ! grep -q "class $event" xline/core/events/types.py; then
                echo "❌ Missing event type: $event"
                exit 1
            fi
            echo "✅ Event type found: $event"
        done
        
        # Check versioning support
        echo "📐 Checking versioning..."
        if [ ! -f "xline/core/events/versioning.py" ]; then
            echo "❌ Missing file: xline/core/events/versioning.py"
            exit 1
        fi
        
        # Check validation
        echo "✅ Checking validation..."
        if [ ! -f "xline/core/events/validation.py" ]; then
            echo "❌ Missing file: xline/core/events/validation.py"
            exit 1
        fi
        
        # Test event serialization
        echo "🧪 Testing event serialization..."
        .venv/bin/python -c "
from xline.core.events.types import OrderEvent, EventType, OrderSide, OrderType, OrderStatus
import json
from decimal import Decimal
from datetime import datetime

# Test OrderEvent with Decimal and proper enums
order_event = OrderEvent(
    type=EventType.ORDER_CREATED,
    source='trading',
    order_id='order-123',
    account_id='acc-123',
    symbol='BTCUSDT',
    side=OrderSide.BUY,
    quantity=Decimal('1.5'),
    price=Decimal('50000.00'),
    order_type=OrderType.LIMIT,
    status=OrderStatus.PENDING
)
print('✅ OrderEvent with Decimal creation successful')

# Test serialization round-trip
order_dict = order_event.to_dict()
print('✅ Event serialization successful')

restored_event = OrderEvent.from_dict(order_dict)
print('✅ Event deserialization successful')
        "
        
        echo "✅ Day 4 validation successful!"
        ;;
        
    5)
        echo "📅 Day 5: Integration Testing & Performance"
        
        # Check integration tests exist
        echo "🔗 Checking integration tests..."
        if [ ! -f "tests/integration/events/test_event_bus_integration.py" ]; then
            echo "❌ Missing integration tests"
            exit 1
        fi
        
        # Check performance tests
        echo "⚡ Checking performance tests..."
        if [ ! -f "tests/performance/test_event_bus_performance.py" ]; then
            echo "❌ Missing performance tests"
            exit 1
        fi
        
        # Check load tests
        echo "📈 Checking load tests..."
        if [ ! -f "tests/load/test_event_bus_load.py" ]; then
            echo "❌ Missing load tests"
            exit 1
        fi
        
        # Run integration tests
        echo "🧪 Running integration tests..."
        .venv/bin/python -m pytest tests/integration/events/ -v || exit 1
        
        # Run performance tests
        echo "⚡ Running performance tests..."
        .venv/bin/python -m pytest tests/performance/ -v || exit 1
        
        # Run load tests (if enabled)
        echo "📈 Running load tests..."
        if [ -f "tests/load/run_load_tests.sh" ]; then
            ./tests/load/run_load_tests.sh || exit 1
        fi
        
        echo "✅ Day 5 validation successful!"
        ;;
        
    *)
        echo "❌ Invalid day: $DAY"
        exit 1
        ;;
esac

echo "🎉 Week $WEEK Day $DAY validation completed successfully!"
