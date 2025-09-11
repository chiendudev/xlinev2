"""
Dead Letter Queue (DLQ) processor for handling failed message processing.

This module provides functionality to:
- Store failed messages with failure reasons and metadata
- Requeue messages back to the main processing stream with filtering
- Purge expired or permanently failed messages
- Provide statistics on DLQ contents
"""

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from xline.core.events.bus_interface import Envelope, EventBusError

logger = structlog.get_logger(__name__)


class DLQError(EventBusError):
    """Base exception for DLQ operations."""
    pass


class DLQProcessingError(DLQError):
    """Raised when DLQ processing fails."""
    pass


class DLQStorageError(DLQError):
    """Raised when DLQ storage operations fail."""
    pass


@dataclass
class DLQEntry:
    """Represents a dead letter queue entry with metadata."""
    
    envelope: Envelope
    reason: str
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    last_attempt: float | None = None
    tags: set[str] = field(default_factory=set)
    
    def __post_init__(self) -> None:
        """Validate entry data after initialization."""
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if not self.reason.strip():
            raise ValueError("reason cannot be empty")
    
    @property
    def age_seconds(self) -> float:
        """Get the age of this entry in seconds."""
        return time.time() - self.timestamp
    
    @property
    def should_retry(self) -> bool:
        """Check if this entry should be retried based on retry count."""
        # Default max retries is 3
        return self.retry_count < 3
    
    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            'envelope': {
                'event_id': self.envelope.event_id,
                'event_type': self.envelope.event_type,
                'data': self.envelope.data,
                'source': self.envelope.source,
                'timestamp': (
                    self.envelope.timestamp.isoformat() 
                    if hasattr(self.envelope.timestamp, 'isoformat') 
                    else self.envelope.timestamp
                ),
                'correlation_id': self.envelope.correlation_id,
                'retry_count': self.envelope.retry_count,
                'headers': self.envelope.headers
            },
            'reason': self.reason,
            'retry_count': self.retry_count,
            'timestamp': self.timestamp,
            'last_attempt': self.last_attempt,
            'tags': list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'DLQEntry':
        """Create entry from dictionary."""
        from datetime import datetime, UTC
        
        envelope_data = data['envelope']
        
        # Handle timestamp conversion
        timestamp = envelope_data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(UTC)
        
        envelope = Envelope(
            event_id=envelope_data['event_id'],
            event_type=envelope_data['event_type'],
            data=envelope_data['data'],
            source=envelope_data.get('source', 'xline'),
            timestamp=timestamp,
            correlation_id=envelope_data.get('correlation_id'),
            retry_count=envelope_data.get('retry_count', 0),
            headers=envelope_data.get('headers', {})
        )
        
        return cls(
            envelope=envelope,
            reason=data['reason'],
            retry_count=data.get('retry_count', 0),
            timestamp=data.get('timestamp', time.time()),
            last_attempt=data.get('last_attempt'),
            tags=set(data.get('tags', []))
        )


@dataclass
class DLQStats:
    """Statistics about DLQ contents."""
    
    total_entries: int = 0
    entries_by_reason: dict[str, int] = field(default_factory=dict)
    entries_by_retry_count: dict[int, int] = field(default_factory=dict)
    oldest_entry_age: float | None = None
    newest_entry_age: float | None = None
    requeue_candidates: int = 0
    expired_entries: int = 0


class DLQProcessor:
    """
    Dead Letter Queue processor for handling failed message processing.
    
    Provides functionality to store, requeue, and manage failed messages
    with comprehensive filtering and statistics capabilities.
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        default_ttl_seconds: float = 86400,  # 24 hours
        cleanup_interval_seconds: float = 300,  # 5 minutes
    ) -> None:
        """
        Initialize DLQ processor.
        
        Args:
            max_entries: Maximum number of entries to store
            default_ttl_seconds: Default TTL for entries
            cleanup_interval_seconds: How often to run cleanup
        """
        self._entries: dict[str, DLQEntry] = {}
        self._max_entries = max_entries
        self._default_ttl = default_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        
        logger.info(
            "DLQ processor initialized",
            max_entries=max_entries,
            default_ttl=default_ttl_seconds
        )
    
    async def start(self) -> None:
        """Start the DLQ processor and background cleanup."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("DLQ processor started")
    
    async def stop(self) -> None:
        """Stop the DLQ processor and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("DLQ processor stopped")
    
    async def add_entry(
        self,
        envelope: Envelope,
        reason: str,
        tags: set[str] | None = None
    ) -> str:
        """
        Add a failed message to the DLQ.
        
        Args:
            envelope: The failed message envelope
            reason: Reason for failure
            tags: Optional tags for categorization
            
        Returns:
            Entry ID
            
        Raises:
            DLQStorageError: If storage fails
        """
        try:
            async with self._lock:
                # Check if we're at capacity
                if len(self._entries) >= self._max_entries:
                    await self._evict_oldest()
                
                # Create entry
                entry = DLQEntry(
                    envelope=envelope,
                    reason=reason,
                    retry_count=envelope.retry_count,
                    tags=tags or set()
                )
                
                # Use envelope ID as entry key
                entry_id = envelope.event_id
                self._entries[entry_id] = entry
                
                logger.info(
                    "Message added to DLQ",
                    entry_id=entry_id,
                    reason=reason,
                    retry_count=envelope.retry_count,
                    tags=list(tags) if tags else []
                )
                
                return entry_id
                
        except Exception as e:
            raise DLQStorageError(f"Failed to add entry to DLQ: {e}") from e
    
    async def requeue(
        self,
        filter_fn: Callable[[DLQEntry], bool] | None = None,
        max_count: int | None = None
    ) -> list[Envelope]:
        """
        Requeue entries back to main processing stream.
        
        Args:
            filter_fn: Optional filter function for selecting entries
            max_count: Maximum number of entries to requeue
            
        Returns:
            List of envelopes that were requeued
            
        Raises:
            DLQProcessingError: If requeue operation fails
        """
        try:
            async with self._lock:
                # Find entries to requeue and clean up non-retryable entries
                candidates = []
                to_remove = []
                
                for entry_id, entry in list(self._entries.items()):
                    # Apply filter if provided
                    if filter_fn and not filter_fn(entry):
                        continue
                    
                    # Check if should retry
                    if not entry.should_retry:
                        # Mark non-retryable entries for removal
                        to_remove.append(entry_id)
                        continue
                    
                    candidates.append((entry_id, entry))
                    
                    # Respect max count
                    if max_count and len(candidates) >= max_count:
                        break
                
                # Remove non-retryable entries
                for entry_id in to_remove:
                    entry = self._entries[entry_id]
                    del self._entries[entry_id]
                    logger.info(
                        "Entry removed from DLQ after max retries",
                        entry_id=entry_id,
                        retry_count=entry.retry_count
                    )
                
                # Requeue selected entries
                requeued = []
                for entry_id, entry in candidates:
                    # Create new envelope with incremented retry count
                    new_envelope = Envelope(
                        event_id=entry.envelope.event_id,
                        event_type=entry.envelope.event_type,
                        data=entry.envelope.data,
                        source=entry.envelope.source,
                        timestamp=entry.envelope.timestamp,
                        correlation_id=entry.envelope.correlation_id,
                        retry_count=entry.envelope.retry_count + 1,
                        headers=entry.envelope.headers
                    )
                    
                    requeued.append(new_envelope)
                    
                    # Update entry metadata
                    entry.retry_count += 1
                    entry.last_attempt = time.time()
                    entry.tags.add('requeued')
                    
                    # Note: We keep the entry in DLQ even if it reaches max retries
                    # The entry will be cleaned up during the next cleanup cycle
                
                logger.info(
                    "DLQ requeue completed",
                    requeued_count=len(requeued),
                    remaining_entries=len(self._entries)
                )
                
                return requeued
                
        except Exception as e:
            raise DLQProcessingError(f"Failed to requeue entries: {e}") from e
    
    async def purge(
        self,
        filter_fn: Callable[[DLQEntry], bool] | None = None,
        max_age_seconds: float | None = None
    ) -> int:
        """
        Permanently remove entries from DLQ.
        
        Args:
            filter_fn: Optional filter function for selecting entries
            max_age_seconds: Remove entries older than this age
            
        Returns:
            Number of purged entries
        """
        try:
            async with self._lock:
                to_remove = []
                
                for entry_id, entry in self._entries.items():
                    should_remove = False
                    
                    # Apply age filter
                    if max_age_seconds and entry.age_seconds > max_age_seconds:
                        should_remove = True
                    
                    # Apply custom filter
                    if filter_fn and filter_fn(entry):
                        should_remove = True
                    
                    if should_remove:
                        to_remove.append(entry_id)
                
                # Remove selected entries
                for entry_id in to_remove:
                    del self._entries[entry_id]
                
                logger.info(
                    "DLQ purge completed",
                    purged_count=len(to_remove),
                    remaining_entries=len(self._entries)
                )
                
                return len(to_remove)
                
        except Exception as e:
            logger.error("Failed to purge DLQ entries", error=str(e))
            return 0
    
    async def get_stats(self) -> DLQStats:
        """Get comprehensive statistics about DLQ contents."""
        async with self._lock:
            stats = DLQStats()
            
            if not self._entries:
                return stats
            
            stats.total_entries = len(self._entries)
            
            # Analyze entries
            ages = []
            for entry in self._entries.values():
                # Count by reason
                stats.entries_by_reason[entry.reason] = (
                    stats.entries_by_reason.get(entry.reason, 0) + 1
                )
                
                # Count by retry count
                stats.entries_by_retry_count[entry.retry_count] = (
                    stats.entries_by_retry_count.get(entry.retry_count, 0) + 1
                )
                
                # Track ages
                age = entry.age_seconds
                ages.append(age)
                
                # Count requeue candidates
                if entry.should_retry:
                    stats.requeue_candidates += 1
                
                # Count expired entries
                if age > self._default_ttl:
                    stats.expired_entries += 1
            
            if ages:
                stats.oldest_entry_age = max(ages)
                stats.newest_entry_age = min(ages)
            
            return stats
    
    async def get_entries(
        self,
        filter_fn: Callable[[DLQEntry], bool] | None = None,
        limit: int | None = None
    ) -> list[DLQEntry]:
        """
        Retrieve DLQ entries with optional filtering.
        
        Args:
            filter_fn: Optional filter function
            limit: Maximum number of entries to return
            
        Returns:
            List of matching DLQ entries
        """
        async with self._lock:
            entries = []
            
            for entry in self._entries.values():
                if filter_fn and not filter_fn(entry):
                    continue
                
                entries.append(entry)
                
                if limit and len(entries) >= limit:
                    break
            
            return entries
    
    async def clear(self) -> int:
        """Clear all entries from DLQ."""
        async with self._lock:
            count = len(self._entries)
            self._entries.clear()
            logger.info("DLQ cleared", removed_count=count)
            return count
    
    async def _evict_oldest(self) -> None:
        """Evict the oldest entry to make room for new ones."""
        if not self._entries:
            return
        
        oldest_id = min(
            self._entries.keys(),
            key=lambda k: self._entries[k].timestamp
        )
        
        del self._entries[oldest_id]
        logger.debug("Evicted oldest DLQ entry", entry_id=oldest_id)
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
        except asyncio.CancelledError:
            logger.debug("DLQ cleanup loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in DLQ cleanup loop", error=str(e))
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries from DLQ."""
        try:
            purged = await self.purge(max_age_seconds=self._default_ttl)
            if purged > 0:
                logger.debug("Cleaned up expired DLQ entries", count=purged)
        except Exception as e:
            logger.error("Failed to cleanup expired entries", error=str(e))


# Utility functions for common filtering operations

def create_reason_filter(reason: str) -> Callable[[DLQEntry], bool]:
    """Create a filter function for entries with specific reason."""
    def filter_fn(entry: DLQEntry) -> bool:
        return entry.reason == reason
    return filter_fn


def create_tag_filter(tag: str) -> Callable[[DLQEntry], bool]:
    """Create a filter function for entries with specific tag."""
    def filter_fn(entry: DLQEntry) -> bool:
        return tag in entry.tags
    return filter_fn


def create_age_filter(max_age_seconds: float) -> Callable[[DLQEntry], bool]:
    """Create a filter function for entries older than specified age."""
    def filter_fn(entry: DLQEntry) -> bool:
        return entry.age_seconds > max_age_seconds
    return filter_fn


def create_retry_filter(max_retries: int) -> Callable[[DLQEntry], bool]:
    """Create a filter function for entries with retry count below threshold."""
    def filter_fn(entry: DLQEntry) -> bool:
        return entry.retry_count < max_retries
    return filter_fn
