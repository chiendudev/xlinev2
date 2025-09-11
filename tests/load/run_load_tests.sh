#!/bin/bash
# Load Test Script for Event Bus
# File: tests/load/run_load_tests.sh

set -e

echo "🚀 Starting Event Bus Load Tests..."

# Configuration
TARGET_EPS=${1:-1000}  # Target events per second
DURATION=${2:-30}      # Test duration in seconds
PYTHON_CMD=".venv/bin/python"

echo "📊 Configuration:"
echo "  Target: ${TARGET_EPS} events/second"
echo "  Duration: ${DURATION} seconds"

# Check if virtual environment exists
if [ ! -f "$PYTHON_CMD" ]; then
    echo "❌ Virtual environment not found at .venv/"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Run enhanced load tests
echo "🧪 Running enhanced load tests..."
$PYTHON_CMD -m pytest tests/load/test_event_bus_load_enhanced.py -v --tb=short

# Run performance benchmarks
echo "⚡ Running performance benchmarks..."
$PYTHON_CMD -m pytest tests/performance/test_event_bus_performance_enhanced.py -v --tb=short

# Check if psutil is available for system monitoring
echo "📈 System Resource Check:"
$PYTHON_CMD -c "
import psutil
process = psutil.Process()
print(f'  Memory Usage: {process.memory_info().rss / (1024*1024):.1f} MB')
print(f'  CPU Percent: {process.cpu_percent(interval=1):.1f}%')
print(f'  Available Memory: {psutil.virtual_memory().available / (1024*1024*1024):.1f} GB')
"

# Performance validation
echo "🎯 Performance Validation:"

# Run specific throughput test
echo "  Testing sustained throughput..."
$PYTHON_CMD -c "
import asyncio
import time
import psutil
from xline.core.events.factory import EventBusFactory
from xline.core.events.types import OrderEvent
from decimal import Decimal
from datetime import datetime, UTC

async def throughput_test():
    config = {'type': 'inmemory', 'buffer_size': 100000}
    bus = await EventBusFactory.create_event_bus(config)
    await bus.initialize()
    
    try:
        events_sent = 0
        events_received = 0
        
        class ThroughputHandler:
            async def handle(self, event):
                nonlocal events_received
                events_received += 1
        
        handler = ThroughputHandler()
        await bus.subscribe('order', handler)
        
        # Test for specified duration
        start_time = time.perf_counter()
        target_time = start_time + ${DURATION}
        
        while time.perf_counter() < target_time:
            # Send batch
            for i in range(100):
                event = OrderEvent(
                    id=f'perf-{events_sent}',
                    order_id=f'order-{events_sent}',
                    account_id='test-account',
                    symbol='BTCUSDT',
                    side='buy',
                    order_type='limit',
                    quantity=Decimal('1.0'),
                    price=Decimal('50000'),
                    status='new',
                    timestamp=datetime.now(UTC),
                    source='load_test'
                )
                await bus.publish(event)
                events_sent += 1
            
            await asyncio.sleep(0.01)  # Brief pause
        
        # Wait for processing
        await asyncio.sleep(2)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        throughput = events_received / duration
        
        print(f'  Events Sent: {events_sent}')
        print(f'  Events Received: {events_received}')
        print(f'  Test Duration: {duration:.1f}s')
        print(f'  Throughput: {throughput:.1f} events/second')
        
        # Check against target
        if throughput >= ${TARGET_EPS}:
            print('  ✅ Sustained throughput target met')
            exit(0)
        else:
            print(f'  ❌ Throughput {throughput:.1f} below target ${TARGET_EPS}')
            exit(1)
            
    finally:
        await bus.cleanup()

asyncio.run(throughput_test())
"

THROUGHPUT_RESULT=$?

# Memory usage test
echo "  Testing memory usage..."
$PYTHON_CMD -c "
import asyncio
import gc
import psutil
from xline.core.events.factory import EventBusFactory
from xline.core.events.types import OrderEvent
from decimal import Decimal
from datetime import datetime, UTC

async def memory_test():
    config = {'type': 'inmemory', 'buffer_size': 100000}
    bus = await EventBusFactory.create_event_bus(config)
    await bus.initialize()
    
    try:
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        class MemoryHandler:
            def __init__(self):
                self.events = []
            async def handle(self, event):
                self.events.append(event)
                if len(self.events) > 1000:
                    self.events = self.events[-500:]  # Keep recent
        
        handler = MemoryHandler()
        await bus.subscribe('order', handler)
        
        # Send many events
        for i in range(5000):
            event = OrderEvent(
                id=f'mem-{i}',
                order_id=f'order-{i}',
                account_id='test-account',
                symbol='BTCUSDT',
                side='buy',
                order_type='limit',
                quantity=Decimal('1.0'),
                price=Decimal('50000'),
                status='new',
                timestamp=datetime.now(UTC),
                source='memory_test'
            )
            await bus.publish(event)
            
            if i % 1000 == 0:
                gc.collect()
        
        await asyncio.sleep(2)
        gc.collect()
        
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory
        
        print(f'  Initial Memory: {initial_memory:.1f} MB')
        print(f'  Final Memory: {final_memory:.1f} MB')
        print(f'  Memory Increase: {memory_increase:.1f} MB')
        
        if final_memory < 100:
            print('  ✅ Memory usage target met')
            exit(0)
        else:
            print(f'  ❌ Memory usage {final_memory:.1f} MB above 100 MB target')
            exit(1)
            
    finally:
        await bus.cleanup()

asyncio.run(memory_test())
"

MEMORY_RESULT=$?

# Final validation
echo ""
echo "📋 Load Test Summary:"
if [ $THROUGHPUT_RESULT -eq 0 ]; then
    echo "  ✅ Sustained ${TARGET_EPS}+ events/second"
else
    echo "  ❌ Failed to sustain ${TARGET_EPS} events/second"
fi

if [ $MEMORY_RESULT -eq 0 ]; then
    echo "  ✅ Memory usage <100MB"
else
    echo "  ❌ Memory usage exceeded 100MB"
fi

if [ $THROUGHPUT_RESULT -eq 0 ] && [ $MEMORY_RESULT -eq 0 ]; then
    echo ""
    echo "🎉 All load test targets achieved!"
    exit 0
else
    echo ""
    echo "❌ Some load test targets not met"
    exit 1
fi
