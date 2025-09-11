# Performance Tuning Guide

## Overview

This guide provides comprehensive strategies for optimizing Xline's performance in production environments. It covers system-level optimizations, algorithmic improvements, resource management, and monitoring techniques to achieve maximum throughput and minimum latency.

## Performance Metrics & Targets

### Key Performance Indicators (KPIs)

| Metric | Target | Critical Threshold | Measurement Method |
|--------|--------|-------------------|-------------------|
| Event Processing Latency | < 10ms | > 100ms | Event bus timing |
| Order Execution Time | < 500ms | > 2000ms | Adapter response time |
| Memory Usage | < 512MB | > 1GB | System monitoring |
| CPU Usage | < 50% | > 80% | Process monitoring |
| Throughput | > 1000 events/sec | < 100 events/sec | Event counter |
| Error Rate | < 0.1% | > 1% | Error tracking |

### Performance Baseline

Before optimization, establish baseline performance:

```python
import asyncio
import time
from collections import defaultdict
from typing import Dict, List

class PerformanceBaseline:
    """Establish performance baseline for optimization."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_time = None
        self.end_time = None
        
    async def run_baseline_test(self, duration_seconds: int = 300) -> Dict[str, float]:
        """Run baseline performance test."""
        self.start_time = time.time()
        
        # Test event processing
        event_latency = await self._test_event_processing()
        
        # Test order execution
        order_latency = await self._test_order_execution()
        
        # Test memory usage
        memory_usage = await self._test_memory_usage()
        
        # Test throughput
        throughput = await self._test_throughput()
        
        self.end_time = time.time()
        
        return {
            "event_latency_ms": event_latency,
            "order_latency_ms": order_latency,
            "memory_usage_mb": memory_usage,
            "throughput_events_per_sec": throughput,
            "test_duration_sec": self.end_time - self.start_time
        }
    
    async def _test_event_processing(self) -> float:
        """Test event processing latency."""
        latencies = []
        
        for _ in range(1000):
            start = time.perf_counter()
            
            # Simulate event processing
            await asyncio.sleep(0.001)  # 1ms simulated processing
            
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        return sum(latencies) / len(latencies)
```

## System-Level Optimizations

### Operating System Configuration

#### Linux Kernel Parameters

```bash
# /etc/sysctl.conf optimizations for high-frequency trading

# Network performance
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_rmem = 4096 87380 268435456
net.ipv4.tcp_wmem = 4096 65536 268435456
net.ipv4.tcp_congestion_control = bbr

# Memory management
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# CPU scheduling
kernel.sched_migration_cost_ns = 5000000
kernel.sched_autogroup_enabled = 0

# Apply changes
sudo sysctl -p
```

#### Process Isolation

```bash
# CPU isolation for trading process
# Add to /etc/default/grub
GRUB_CMDLINE_LINUX="isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7"

# Update grub
sudo update-grub
sudo reboot

# Pin trading process to isolated CPUs
taskset -c 2-7 python xline.py start
```

### Python Runtime Optimization

#### Python Configuration

```python
# xline/config/runtime_optimization.py
import gc
import sys
import threading
from typing import Dict, Any

class PythonRuntimeOptimizer:
    """Optimize Python runtime for performance."""
    
    @staticmethod
    def optimize_gc() -> None:
        """Optimize garbage collection settings."""
        # Disable automatic garbage collection for gen 2
        gc.set_threshold(700, 10, 0)
        
        # Enable garbage collection debugging (development only)
        if __debug__:
            gc.set_debug(gc.DEBUG_STATS)
    
    @staticmethod
    def optimize_threading() -> None:
        """Optimize threading settings."""
        # Reduce thread switching overhead
        threading.stack_size(32768)  # 32KB stack size
        
        # Set thread priority (Unix only)
        import os
        try:
            os.nice(-10)  # Higher priority
        except PermissionError:
            pass
    
    @staticmethod
    def configure_asyncio() -> None:
        """Configure asyncio for optimal performance."""
        import asyncio
        import uvloop  # Optional: high-performance event loop
        
        try:
            # Use uvloop for better performance
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            # Fallback to default event loop
            pass
        
        # Configure event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Optimize loop settings
        loop.set_debug(False)  # Disable debug mode in production
    
    @classmethod
    def apply_all_optimizations(cls) -> None:
        """Apply all runtime optimizations."""
        cls.optimize_gc()
        cls.optimize_threading()
        cls.configure_asyncio()

# Apply optimizations at startup
PythonRuntimeOptimizer.apply_all_optimizations()
```

## Memory Management

### Memory Pool Implementation

```python
import mmap
from typing import Optional, Union
from dataclasses import dataclass

@dataclass
class MemoryBlock:
    """Represents a memory block in the pool."""
    size: int
    offset: int
    is_free: bool = True

class HighPerformanceMemoryPool:
    """High-performance memory pool for frequent allocations."""
    
    def __init__(self, pool_size: int = 1024 * 1024 * 100):  # 100MB
        self.pool_size = pool_size
        self.memory_map = mmap.mmap(-1, pool_size)
        self.blocks = [MemoryBlock(size=pool_size, offset=0)]
        self.allocated_blocks = {}
        
    def allocate(self, size: int) -> Optional[memoryview]:
        """Allocate memory block from pool."""
        # Find suitable free block
        for i, block in enumerate(self.blocks):
            if block.is_free and block.size >= size:
                # Split block if necessary
                if block.size > size:
                    # Create new block for remaining space
                    new_block = MemoryBlock(
                        size=block.size - size,
                        offset=block.offset + size,
                        is_free=True
                    )
                    self.blocks.insert(i + 1, new_block)
                
                # Mark block as allocated
                block.size = size
                block.is_free = False
                
                # Create memory view
                mem_view = memoryview(self.memory_map[block.offset:block.offset + size])
                self.allocated_blocks[id(mem_view)] = i
                
                return mem_view
        
        # No suitable block found
        return None
    
    def deallocate(self, mem_view: memoryview) -> None:
        """Deallocate memory block."""
        block_index = self.allocated_blocks.pop(id(mem_view), None)
        if block_index is not None:
            self.blocks[block_index].is_free = True
            self._merge_adjacent_blocks()
    
    def _merge_adjacent_blocks(self) -> None:
        """Merge adjacent free blocks to reduce fragmentation."""
        i = 0
        while i < len(self.blocks) - 1:
            current = self.blocks[i]
            next_block = self.blocks[i + 1]
            
            if (current.is_free and next_block.is_free and 
                current.offset + current.size == next_block.offset):
                # Merge blocks
                current.size += next_block.size
                self.blocks.pop(i + 1)
            else:
                i += 1

# Global memory pool instance
memory_pool = HighPerformanceMemoryPool()
```

### Object Pooling

```python
from collections import deque
from typing import Generic, TypeVar, Callable, Optional

T = TypeVar('T')

class ObjectPool(Generic[T]):
    """Generic object pool for reusing expensive objects."""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self.pool = deque()
        self.created_count = 0
        
    def acquire(self) -> T:
        """Acquire object from pool."""
        if self.pool:
            return self.pool.popleft()
        else:
            self.created_count += 1
            return self.factory()
    
    def release(self, obj: T) -> None:
        """Return object to pool."""
        if len(self.pool) < self.max_size:
            # Reset object state if needed
            if hasattr(obj, 'reset'):
                obj.reset()
            self.pool.append(obj)
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            "pool_size": len(self.pool),
            "max_size": self.max_size,
            "created_count": self.created_count,
            "hit_rate": (self.created_count - len(self.pool)) / max(1, self.created_count)
        }

# Example: Event object pool
from xline.core.events.types import PriceTickEvent

def create_price_tick_event() -> PriceTickEvent:
    """Factory for creating PriceTickEvent objects."""
    return PriceTickEvent(
        source="",
        symbol="",
        price=Decimal("0"),
        volume=Decimal("0"),
        timestamp_ms=0
    )

# Global event pool
price_tick_pool = ObjectPool(create_price_tick_event, max_size=1000)
```

## Event System Optimization

### High-Performance Event Bus

```python
import asyncio
import weakref
from collections import defaultdict
from typing import Dict, List, Callable, Any
import uvloop

class OptimizedEventBus:
    """High-performance event bus with optimization features."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[weakref.ref]] = defaultdict(list)
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.processing_tasks = []
        self.stats = EventBusStats()
        
        # Performance optimizations
        self.batch_size = 100
        self.processing_workers = 4
        
        # Start processing workers
        self._start_workers()
    
    def _start_workers(self) -> None:
        """Start event processing workers."""
        for i in range(self.processing_workers):
            task = asyncio.create_task(self._process_events())
            self.processing_tasks.append(task)
    
    async def _process_events(self) -> None:
        """Process events in batches for better performance."""
        batch = []
        
        while True:
            try:
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=0.1
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    # Process partial batch on timeout
                    if batch:
                        await self._process_batch(batch)
                        batch.clear()
                    continue
                
                # Process full batch
                if len(batch) >= self.batch_size:
                    await self._process_batch(batch)
                    batch.clear()
                
            except Exception as e:
                self.stats.record_error(e)
    
    async def _process_batch(self, events: List[Any]) -> None:
        """Process a batch of events."""
        start_time = asyncio.get_event_loop().time()
        
        # Group events by type for efficient processing
        events_by_type = defaultdict(list)
        for event in events:
            events_by_type[event.event_type].append(event)
        
        # Process each event type
        for event_type, type_events in events_by_type.items():
            await self._process_events_of_type(event_type, type_events)
        
        # Update statistics
        processing_time = asyncio.get_event_loop().time() - start_time
        self.stats.record_batch_processing(len(events), processing_time)
    
    async def _process_events_of_type(self, event_type: str, events: List[Any]) -> None:
        """Process events of a specific type."""
        subscribers = self.subscribers.get(event_type, [])
        
        # Clean up dead references
        active_subscribers = []
        for sub_ref in subscribers:
            callback = sub_ref()
            if callback is not None:
                active_subscribers.append(callback)
        
        # Update subscriber list
        self.subscribers[event_type] = [weakref.ref(sub) for sub in active_subscribers]
        
        # Call subscribers for each event
        for event in events:
            await self._notify_subscribers(active_subscribers, event)
    
    async def _notify_subscribers(self, subscribers: List[Callable], event: Any) -> None:
        """Notify subscribers about an event."""
        if not subscribers:
            return
        
        # Call subscribers concurrently
        tasks = [subscriber(event) for subscriber in subscribers]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def publish(self, event: Any) -> None:
        """Publish event to the bus."""
        try:
            self.event_queue.put_nowait(event)
            self.stats.record_event_published()
        except asyncio.QueueFull:
            self.stats.record_queue_full()
            # Drop oldest event and add new one
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass

class EventBusStats:
    """Statistics tracking for event bus performance."""
    
    def __init__(self):
        self.events_published = 0
        self.events_processed = 0
        self.processing_times = deque(maxlen=1000)
        self.errors = deque(maxlen=100)
        self.queue_full_count = 0
        
    def record_event_published(self) -> None:
        """Record that an event was published."""
        self.events_published += 1
    
    def record_batch_processing(self, batch_size: int, processing_time: float) -> None:
        """Record batch processing statistics."""
        self.events_processed += batch_size
        self.processing_times.append(processing_time)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        if not self.processing_times:
            return {}
        
        return {
            "events_published": self.events_published,
            "events_processed": self.events_processed,
            "avg_processing_time_ms": sum(self.processing_times) / len(self.processing_times) * 1000,
            "max_processing_time_ms": max(self.processing_times) * 1000,
            "min_processing_time_ms": min(self.processing_times) * 1000,
            "queue_full_events": self.queue_full_count,
            "error_count": len(self.errors)
        }
```

## Database Optimization

### Connection Pooling

```python
import asyncio
import aiopg
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

class OptimizedDatabasePool:
    """Optimized database connection pool."""
    
    def __init__(self, database_url: str, 
                 min_size: int = 10, max_size: int = 50):
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[aiopg.Pool] = None
        
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        self.pool = await aiopg.create_pool(
            self.database_url,
            minsize=self.min_size,
            maxsize=self.max_size,
            # Performance optimizations
            command_timeout=30,
            server_settings={
                'application_name': 'xline_trading_system',
                'tcp_keepalives_idle': '600',
                'tcp_keepalives_interval': '30',
                'tcp_keepalives_count': '3',
            }
        )
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire a database connection."""
        async with self.pool.acquire() as conn:
            # Optimize connection settings
            async with conn.cursor() as cur:
                await cur.execute("SET synchronous_commit = off")
                await cur.execute("SET wal_buffers = '16MB'")
                await cur.execute("SET checkpoint_segments = 32")
            
            yield conn
    
    async def execute_batch(self, queries: List[str]) -> List[Any]:
        """Execute multiple queries in a batch."""
        results = []
        
        async with self.acquire_connection() as conn:
            async with conn.cursor() as cur:
                # Begin transaction
                await cur.execute("BEGIN")
                
                try:
                    for query in queries:
                        await cur.execute(query)
                        if cur.description:
                            result = await cur.fetchall()
                            results.append(result)
                    
                    # Commit transaction
                    await cur.execute("COMMIT")
                    
                except Exception:
                    # Rollback on error
                    await cur.execute("ROLLBACK")
                    raise
        
        return results

# Global database pool
db_pool = OptimizedDatabasePool(
    "postgresql://user:pass@localhost/xline",
    min_size=20,
    max_size=100
)
```

### Query Optimization

```python
class OptimizedQueries:
    """Optimized database queries for trading operations."""
    
    # Prepared statements for frequent queries
    QUERIES = {
        "insert_trade": """
            INSERT INTO trades (symbol, side, quantity, price, timestamp, strategy_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING trade_id
        """,
        
        "get_portfolio": """
            SELECT symbol, SUM(quantity * CASE WHEN side = 'BUY' THEN 1 ELSE -1 END) as position
            FROM trades 
            WHERE strategy_id = $1 
            GROUP BY symbol
            HAVING SUM(quantity * CASE WHEN side = 'BUY' THEN 1 ELSE -1 END) != 0
        """,
        
        "get_recent_prices": """
            SELECT symbol, price, timestamp
            FROM price_ticks
            WHERE symbol = ANY($1) AND timestamp > $2
            ORDER BY timestamp DESC
        """
    }
    
    @classmethod
    async def insert_trade_optimized(cls, conn, trade_data: Dict[str, Any]) -> int:
        """Insert trade with optimized query."""
        async with conn.cursor() as cur:
            await cur.execute(
                cls.QUERIES["insert_trade"],
                (
                    trade_data["symbol"],
                    trade_data["side"],
                    trade_data["quantity"],
                    trade_data["price"],
                    trade_data["timestamp"],
                    trade_data["strategy_id"]
                )
            )
            result = await cur.fetchone()
            return result[0]
    
    @classmethod
    async def bulk_insert_trades(cls, conn, trades: List[Dict[str, Any]]) -> None:
        """Bulk insert trades for better performance."""
        if not trades:
            return
        
        # Prepare data for bulk insert
        trade_tuples = [
            (
                trade["symbol"],
                trade["side"],
                trade["quantity"],
                trade["price"],
                trade["timestamp"],
                trade["strategy_id"]
            )
            for trade in trades
        ]
        
        async with conn.cursor() as cur:
            # Use COPY for maximum performance
            await cur.copy_to_table(
                "trades",
                trade_tuples,
                columns=["symbol", "side", "quantity", "price", "timestamp", "strategy_id"]
            )
```

## Network Optimization

### Connection Management

```python
import aiohttp
import asyncio
from typing import Optional
from aiohttp_retry import RetryClient, ExponentialRetry

class OptimizedHttpClient:
    """Optimized HTTP client for trading APIs."""
    
    def __init__(self):
        self.session: Optional[RetryClient] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        
    async def __aenter__(self):
        # Configure TCP connector for optimal performance
        self.connector = aiohttp.TCPConnector(
            # Connection pool settings
            limit=200,  # Total connection pool size
            limit_per_host=50,  # Connections per host
            ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
            use_dns_cache=True,
            
            # TCP settings
            keepalive_timeout=60,  # Keep connections alive
            enable_cleanup_closed=True,
            force_close=False,
            
            # SSL settings
            ssl=False,  # Disable for internal APIs
            
            # Socket settings
            family=socket.AF_INET,  # IPv4 only for speed
            local_addr=None,
            resolver=None,
            sock_read=None,
            sock_connect=None,
        )
        
        # Configure timeouts
        timeout = aiohttp.ClientTimeout(
            total=30,     # Total timeout
            connect=5,    # Connection timeout
            sock_read=10, # Socket read timeout
            sock_connect=5  # Socket connect timeout
        )
        
        # Configure retry policy
        retry_options = ExponentialRetry(
            attempts=3,
            start_timeout=0.1,
            max_timeout=2.0,
            factor=2.0
        )
        
        # Create session
        self.session = RetryClient(
            connector=self.connector,
            timeout=timeout,
            retry_options=retry_options,
            
            # Additional optimizations
            cookie_jar=aiohttp.DummyCookieJar(),  # Disable cookies
            headers={
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=60, max=100'
            }
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()

# Global HTTP client
http_client = OptimizedHttpClient()
```

### WebSocket Optimization

```python
import websockets
import asyncio
import ujson  # Faster JSON library
from typing import Callable, Optional

class OptimizedWebSocketClient:
    """High-performance WebSocket client."""
    
    def __init__(self, url: str, message_handler: Callable):
        self.url = url
        self.message_handler = message_handler
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        self.message_queue = asyncio.Queue(maxsize=1000)
        
    async def connect(self) -> None:
        """Connect to WebSocket with optimizations."""
        connection_params = {
            # Performance optimizations
            'ping_interval': 20,
            'ping_timeout': 10,
            'close_timeout': 10,
            'max_size': 2**20,  # 1MB max message size
            'max_queue': 100,   # Message queue size
            'read_limit': 2**16,  # 64KB read buffer
            'write_limit': 2**16, # 64KB write buffer
            
            # Compression (disable for lowest latency)
            'compression': None,
            
            # Headers
            'extra_headers': {
                'User-Agent': 'Xline-Trading-System/1.0'
            }
        }
        
        self.websocket = await websockets.connect(self.url, **connection_params)
        
        # Start message processing
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._message_receiver())
    
    async def _message_receiver(self) -> None:
        """Receive messages from WebSocket."""
        try:
            async for message in self.websocket:
                # Use faster JSON parser
                try:
                    data = ujson.loads(message)
                    await self.message_queue.put(data)
                except ujson.JSONDecodeError:
                    # Handle non-JSON messages
                    await self.message_queue.put(message)
                    
        except websockets.exceptions.ConnectionClosed:
            await self._handle_disconnect()
    
    async def _message_processor(self) -> None:
        """Process received messages."""
        while True:
            try:
                # Process messages in batches
                messages = []
                
                # Collect batch of messages
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=0.01  # 10ms timeout
                    )
                    messages.append(message)
                    
                    # Try to get more messages without blocking
                    while len(messages) < 50:  # Max batch size
                        try:
                            message = self.message_queue.get_nowait()
                            messages.append(message)
                        except asyncio.QueueEmpty:
                            break
                            
                except asyncio.TimeoutError:
                    continue
                
                # Process batch
                if messages:
                    await self._process_message_batch(messages)
                    
            except Exception as e:
                logger.error(f"Message processing error: {e}")
    
    async def _process_message_batch(self, messages: list) -> None:
        """Process a batch of messages efficiently."""
        # Group messages by type for efficient processing
        message_groups = {}
        
        for message in messages:
            if isinstance(message, dict) and 'type' in message:
                msg_type = message['type']
                if msg_type not in message_groups:
                    message_groups[msg_type] = []
                message_groups[msg_type].append(message)
        
        # Process each group
        for msg_type, group_messages in message_groups.items():
            await self.message_handler(msg_type, group_messages)
```

## Algorithmic Optimization

### Fast Data Structures

```python
import numpy as np
from numba import jit
from collections import deque
import bisect

class RingBuffer:
    """High-performance ring buffer for time series data."""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer = np.zeros(size, dtype=np.float64)
        self.index = 0
        self.count = 0
    
    def append(self, value: float) -> None:
        """Add value to ring buffer."""
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
        self.count = min(self.count + 1, self.size)
    
    def get_array(self) -> np.ndarray:
        """Get buffer contents as numpy array."""
        if self.count < self.size:
            return self.buffer[:self.count]
        else:
            # Reconstruct correct order
            return np.concatenate([
                self.buffer[self.index:],
                self.buffer[:self.index]
            ])
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self.count == self.size

@jit(nopython=True)
def fast_moving_average(prices: np.ndarray, window: int) -> np.ndarray:
    """Optimized moving average calculation using Numba."""
    n = len(prices)
    result = np.zeros(n)
    
    if n < window:
        return result
    
    # Calculate first window
    window_sum = np.sum(prices[:window])
    result[window-1] = window_sum / window
    
    # Sliding window calculation
    for i in range(window, n):
        window_sum = window_sum - prices[i-window] + prices[i]
        result[i] = window_sum / window
    
    return result

@jit(nopython=True)
def fast_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Optimized RSI calculation using Numba."""
    n = len(prices)
    if n < period + 1:
        return np.zeros(n)
    
    # Calculate price changes
    deltas = np.diff(prices)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    # Calculate initial averages
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi = np.zeros(n)
    
    for i in range(period, n-1):
        # Smoothed moving averages
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Calculate RSI
        if avg_loss == 0:
            rsi[i+1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i+1] = 100.0 - (100.0 / (1.0 + rs))
    
    return rsi

class OptimizedOrderBook:
    """High-performance order book implementation."""
    
    def __init__(self):
        self.bids = []  # (price, quantity) sorted by price desc
        self.asks = []  # (price, quantity) sorted by price asc
        self.bid_prices = {}  # price -> index mapping
        self.ask_prices = {}  # price -> index mapping
    
    def add_bid(self, price: float, quantity: float) -> None:
        """Add bid order."""
        if price in self.bid_prices:
            # Update existing price level
            idx = self.bid_prices[price]
            self.bids[idx] = (price, self.bids[idx][1] + quantity)
        else:
            # Insert new price level (maintain sorted order)
            idx = bisect.bisect_left([p for p, q in self.bids], price)
            self.bids.insert(idx, (price, quantity))
            # Update price mappings
            for p in self.bid_prices:
                if self.bid_prices[p] >= idx:
                    self.bid_prices[p] += 1
            self.bid_prices[price] = idx
    
    def add_ask(self, price: float, quantity: float) -> None:
        """Add ask order."""
        if price in self.ask_prices:
            # Update existing price level
            idx = self.ask_prices[price]
            self.asks[idx] = (price, self.asks[idx][1] + quantity)
        else:
            # Insert new price level (maintain sorted order)
            idx = bisect.bisect_left([p for p, q in self.asks], price)
            self.asks.insert(idx, (price, quantity))
            # Update price mappings
            for p in self.ask_prices:
                if self.ask_prices[p] >= idx:
                    self.ask_prices[p] += 1
            self.ask_prices[price] = idx
    
    def get_best_bid(self) -> Optional[tuple]:
        """Get best bid price and quantity."""
        return self.bids[0] if self.bids else None
    
    def get_best_ask(self) -> Optional[tuple]:
        """Get best ask price and quantity."""
        return self.asks[0] if self.asks else None
    
    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return None
```

## Monitoring & Profiling

### Performance Profiler

```python
import cProfile
import pstats
import time
import psutil
import threading
from typing import Dict, Any, Callable
from functools import wraps

class PerformanceProfiler:
    """Comprehensive performance profiler."""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.start_time = None
        self.metrics = {}
        self.monitoring_thread = None
        self.monitoring_active = False
        
    def start_profiling(self) -> None:
        """Start performance profiling."""
        self.start_time = time.time()
        self.profiler.enable()
        
        # Start resource monitoring
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_resources)
        self.monitoring_thread.start()
    
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return results."""
        self.profiler.disable()
        self.monitoring_active = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        # Generate profiling report
        stats = pstats.Stats(self.profiler)
        stats.sort_stats('cumulative')
        
        # Get top functions by time
        top_functions = []
        for func_info, (cc, nc, tt, ct, callers) in stats.stats.items():
            top_functions.append({
                'function': f"{func_info[0]}:{func_info[1]}({func_info[2]})",
                'calls': nc,
                'total_time': tt,
                'cumulative_time': ct,
                'time_per_call': tt / nc if nc > 0 else 0
            })
        
        # Sort by total time
        top_functions.sort(key=lambda x: x['total_time'], reverse=True)
        
        return {
            'duration': time.time() - self.start_time,
            'top_functions': top_functions[:20],  # Top 20 functions
            'resource_metrics': self.metrics
        }
    
    def _monitor_resources(self) -> None:
        """Monitor system resources during profiling."""
        process = psutil.Process()
        
        cpu_samples = []
        memory_samples = []
        
        while self.monitoring_active:
            try:
                # CPU usage
                cpu_percent = process.cpu_percent()
                cpu_samples.append(cpu_percent)
                
                # Memory usage
                memory_info = process.memory_info()
                memory_samples.append(memory_info.rss / 1024 / 1024)  # MB
                
                time.sleep(1)  # Sample every second
                
            except Exception as e:
                print(f"Monitoring error: {e}")
        
        # Calculate statistics
        if cpu_samples:
            self.metrics['cpu'] = {
                'avg': sum(cpu_samples) / len(cpu_samples),
                'max': max(cpu_samples),
                'min': min(cpu_samples)
            }
        
        if memory_samples:
            self.metrics['memory'] = {
                'avg': sum(memory_samples) / len(memory_samples),
                'max': max(memory_samples),
                'min': min(memory_samples)
            }

def profile_function(func: Callable) -> Callable:
    """Decorator to profile individual functions."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # ms
            print(f"{func.__name__} took {execution_time:.2f}ms")
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # ms
            print(f"{func.__name__} took {execution_time:.2f}ms")
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
```

### Real-time Monitoring Dashboard

```python
import asyncio
import time
from typing import Dict, Any
import json

class RealTimeMonitor:
    """Real-time performance monitoring dashboard."""
    
    def __init__(self):
        self.metrics = {}
        self.metric_history = {}
        self.alerts = []
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 1024.0,  # MB
            'event_latency': 100.0,  # ms
            'error_rate': 1.0  # %
        }
    
    async def start_monitoring(self) -> None:
        """Start real-time monitoring."""
        monitoring_tasks = [
            self._monitor_system_metrics(),
            self._monitor_event_latency(),
            self._monitor_error_rates(),
            self._check_thresholds(),
            self._update_dashboard()
        ]
        
        await asyncio.gather(*monitoring_tasks)
    
    async def _monitor_system_metrics(self) -> None:
        """Monitor system-level metrics."""
        while True:
            try:
                process = psutil.Process()
                
                # CPU usage
                cpu_usage = process.cpu_percent()
                self._record_metric('cpu_usage', cpu_usage)
                
                # Memory usage
                memory_info = process.memory_info()
                memory_usage = memory_info.rss / 1024 / 1024  # MB
                self._record_metric('memory_usage', memory_usage)
                
                # Network I/O
                net_io = psutil.net_io_counters()
                self._record_metric('bytes_sent', net_io.bytes_sent)
                self._record_metric('bytes_received', net_io.bytes_recv)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                print(f"System monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_event_latency(self) -> None:
        """Monitor event processing latency."""
        # This would integrate with the event bus to track latency
        while True:
            try:
                # Get latency metrics from event bus
                # latency_metrics = event_bus.get_latency_metrics()
                # self._record_metric('event_latency', latency_metrics['avg'])
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Latency monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _check_thresholds(self) -> None:
        """Check if metrics exceed thresholds."""
        while True:
            try:
                for metric_name, threshold in self.thresholds.items():
                    current_value = self.metrics.get(metric_name, 0)
                    
                    if current_value > threshold:
                        alert = {
                            'timestamp': time.time(),
                            'metric': metric_name,
                            'value': current_value,
                            'threshold': threshold,
                            'severity': 'WARNING'
                        }
                        self.alerts.append(alert)
                        
                        # Keep only recent alerts
                        self.alerts = self.alerts[-100:]
                        
                        print(f"ALERT: {metric_name} = {current_value} exceeds threshold {threshold}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Threshold checking error: {e}")
                await asyncio.sleep(10)
    
    def _record_metric(self, name: str, value: float) -> None:
        """Record a metric value."""
        self.metrics[name] = value
        
        # Keep history
        if name not in self.metric_history:
            self.metric_history[name] = deque(maxlen=1000)
        
        self.metric_history[name].append({
            'timestamp': time.time(),
            'value': value
        })
    
    async def _update_dashboard(self) -> None:
        """Update monitoring dashboard."""
        while True:
            try:
                # Generate dashboard data
                dashboard_data = {
                    'timestamp': time.time(),
                    'metrics': self.metrics,
                    'alerts': self.alerts[-10:],  # Recent alerts
                    'system_health': self._calculate_system_health()
                }
                
                # Save to file or send to dashboard service
                with open('/tmp/xline_dashboard.json', 'w') as f:
                    json.dump(dashboard_data, f, indent=2)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                print(f"Dashboard update error: {e}")
                await asyncio.sleep(5)
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health."""
        if len(self.alerts) > 0:
            recent_alerts = [a for a in self.alerts if time.time() - a['timestamp'] < 300]  # Last 5 minutes
            if len(recent_alerts) > 5:
                return "CRITICAL"
            elif len(recent_alerts) > 2:
                return "WARNING"
        
        return "HEALTHY"
```

## Benchmarking & Testing

### Performance Benchmarks

```python
import asyncio
import time
import statistics
from typing import List, Callable, Dict, Any

class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""
    
    def __init__(self):
        self.results = {}
        
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks."""
        benchmarks = [
            self.benchmark_event_processing,
            self.benchmark_order_execution,
            self.benchmark_database_operations,
            self.benchmark_network_operations,
            self.benchmark_memory_operations
        ]
        
        results = {}
        for benchmark in benchmarks:
            try:
                result = await benchmark()
                results[benchmark.__name__] = result
            except Exception as e:
                results[benchmark.__name__] = {"error": str(e)}
        
        return results
    
    async def benchmark_event_processing(self) -> Dict[str, float]:
        """Benchmark event processing performance."""
        from xline.core.events.bus import InMemoryEventBus
        from xline.core.events.types import PriceTickEvent
        
        event_bus = InMemoryEventBus()
        
        # Benchmark event publication
        events = [
            PriceTickEvent(
                source="benchmark",
                symbol="BTCUSD",
                price=Decimal("50000"),
                volume=Decimal("1.0"),
                timestamp_ms=int(time.time() * 1000)
            )
            for _ in range(10000)
        ]
        
        start_time = time.perf_counter()
        
        for event in events:
            await event_bus.publish(event)
        
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        events_per_second = len(events) / total_time
        
        return {
            "total_events": len(events),
            "total_time_seconds": total_time,
            "events_per_second": events_per_second,
            "average_latency_ms": (total_time / len(events)) * 1000
        }
    
    async def benchmark_order_execution(self) -> Dict[str, float]:
        """Benchmark order execution performance."""
        # This would test the FreqtradeAdapter performance
        latencies = []
        
        for i in range(1000):
            start_time = time.perf_counter()
            
            # Simulate order execution
            await asyncio.sleep(0.001)  # 1ms simulated processing
            
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)
        
        return {
            "total_orders": len(latencies),
            "average_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": self._percentile(latencies, 95),
            "p99_latency_ms": self._percentile(latencies, 99),
            "max_latency_ms": max(latencies),
            "min_latency_ms": min(latencies)
        }
    
    async def benchmark_database_operations(self) -> Dict[str, float]:
        """Benchmark database operation performance."""
        # Simulate database operations
        insert_times = []
        select_times = []
        
        for _ in range(100):
            # Benchmark insert
            start_time = time.perf_counter()
            await asyncio.sleep(0.005)  # 5ms simulated insert
            end_time = time.perf_counter()
            insert_times.append((end_time - start_time) * 1000)
            
            # Benchmark select
            start_time = time.perf_counter()
            await asyncio.sleep(0.002)  # 2ms simulated select
            end_time = time.perf_counter()
            select_times.append((end_time - start_time) * 1000)
        
        return {
            "insert_avg_ms": statistics.mean(insert_times),
            "insert_p95_ms": self._percentile(insert_times, 95),
            "select_avg_ms": statistics.mean(select_times),
            "select_p95_ms": self._percentile(select_times, 95)
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

# Usage example
async def run_benchmarks():
    """Run performance benchmarks."""
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()
    
    print("Performance Benchmark Results:")
    print("=" * 50)
    
    for benchmark_name, result in results.items():
        print(f"\n{benchmark_name}:")
        for metric, value in result.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.2f}")
            else:
                print(f"  {metric}: {value}")
```

## Production Deployment Optimization

### Docker Optimization

```dockerfile
# Multi-stage Dockerfile for optimal performance
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir --user -r requirements-xline.txt

# Production stage
FROM python:3.12-slim

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash xline

# Copy application
WORKDIR /app
COPY . .
RUN chown -R xline:xline /app

# Switch to non-root user
USER xline

# Performance optimizations
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Memory optimization
ENV MALLOC_ARENA_MAX=2
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_MMAP_MAX_=65536

# Set CPU affinity for multi-core systems
ENV GOMAXPROCS=4

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start with optimized settings
CMD ["python", "-O", "-m", "xline.main", "start", "--config", "config/production.json"]
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: xline-trading-system
  namespace: trading
spec:
  replicas: 3
  selector:
    matchLabels:
      app: xline
  template:
    metadata:
      labels:
        app: xline
    spec:
      containers:
      - name: xline
        image: xline:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: MALLOC_ARENA_MAX
          value: "2"
        ports:
        - containerPort: 8080
        - containerPort: 8081
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: config
        configMap:
          name: xline-config
      - name: logs
        emptyDir: {}
      nodeSelector:
        node-type: compute-optimized
      tolerations:
      - key: "trading-workload"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

## Conclusion

This performance tuning guide provides comprehensive strategies for optimizing Xline's performance across all system levels. Key takeaways:

1. **System-Level**: OS configuration, CPU isolation, and process optimization
2. **Application-Level**: Memory management, event processing, and algorithmic optimization
3. **Network-Level**: Connection pooling, WebSocket optimization, and protocol tuning
4. **Database-Level**: Query optimization, connection pooling, and indexing strategies
5. **Monitoring**: Real-time performance tracking and alerting
6. **Deployment**: Containerization and orchestration optimizations

Regular benchmarking and monitoring are essential for maintaining optimal performance in production environments. Use the provided tools and techniques to continuously optimize your Xline deployment for maximum trading performance.
