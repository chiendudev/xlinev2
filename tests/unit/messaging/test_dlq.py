"""Tests for Dead Letter Queue (DLQ) functionality."""

import asyncio
import pytest
import time
from unittest.mock import Mock

from xline.core.events.bus_interface import Envelope
from xline.infrastructure.messaging.dlq import (
    DLQEntry,
    DLQError,
    DLQProcessor,
    DLQProcessingError,
    DLQStats,
    DLQStorageError,
    create_age_filter,
    create_reason_filter,
    create_retry_filter,
    create_tag_filter,
)


class TestDLQEntry:
    """Test DLQ entry functionality."""
    
    def test_entry_creation_with_defaults(self):
        """Test creating DLQ entry with default values."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"}
        )
        
        entry = DLQEntry(envelope=envelope, reason="Test failure")
        
        assert entry.envelope == envelope
        assert entry.reason == "Test failure"
        assert entry.retry_count == 0
        assert isinstance(entry.timestamp, float)
        assert entry.last_attempt is None
        assert entry.tags == set()
    
    def test_entry_creation_with_all_fields(self):
        """Test creating DLQ entry with all fields specified."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"},
            retry_count=2
        )
        
        tags = {"category", "urgent"}
        entry = DLQEntry(
            envelope=envelope,
            reason="Connection timeout",
            retry_count=3,
            timestamp=1234567890.0,
            last_attempt=1234567900.0,
            tags=tags
        )
        
        assert entry.envelope == envelope
        assert entry.reason == "Connection timeout"
        assert entry.retry_count == 3
        assert entry.timestamp == 1234567890.0
        assert entry.last_attempt == 1234567900.0
        assert entry.tags == tags
    
    def test_entry_validation_negative_retry_count(self):
        """Test validation fails for negative retry count."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"}
        )
        
        with pytest.raises(ValueError, match="retry_count must be non-negative"):
            DLQEntry(envelope=envelope, reason="Test", retry_count=-1)
    
    def test_entry_validation_empty_reason(self):
        """Test validation fails for empty reason."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"}
        )
        
        with pytest.raises(ValueError, match="reason cannot be empty"):
            DLQEntry(envelope=envelope, reason="   ")
    
    def test_age_calculation(self):
        """Test age calculation for DLQ entry."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"}
        )
        
        past_time = time.time() - 100  # 100 seconds ago
        entry = DLQEntry(envelope=envelope, reason="Test", timestamp=past_time)
        
        age = entry.age_seconds
        assert 99 <= age <= 101  # Allow for small timing differences
    
    def test_should_retry_logic(self):
        """Test should_retry property logic."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"}
        )
        
        # Should retry with low retry count
        entry = DLQEntry(envelope=envelope, reason="Test", retry_count=2)
        assert entry.should_retry is True
        
        # Should not retry with high retry count
        entry = DLQEntry(envelope=envelope, reason="Test", retry_count=3)
        assert entry.should_retry is False
        
        entry = DLQEntry(envelope=envelope, reason="Test", retry_count=5)
        assert entry.should_retry is False
    
    def test_to_dict_conversion(self):
        """Test converting entry to dictionary."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"key": "value"},
            source="test-source",
            correlation_id="corr-456",
            retry_count=1,
            headers={"custom": "header"}
        )
        
        tags = {"category", "urgent"}
        entry = DLQEntry(
            envelope=envelope,
            reason="Test failure",
            retry_count=2,
            timestamp=1234567890.0,
            last_attempt=1234567900.0,
            tags=tags
        )
        
        data = entry.to_dict()
        
        assert data["envelope"]["event_id"] == "test-123"
        assert data["envelope"]["event_type"] == "test.event"
        assert data["envelope"]["data"] == {"key": "value"}
        assert data["envelope"]["source"] == "test-source"
        assert data["envelope"]["correlation_id"] == "corr-456"
        assert data["envelope"]["retry_count"] == 1
        assert data["envelope"]["headers"] == {"custom": "header"}
        assert data["reason"] == "Test failure"
        assert data["retry_count"] == 2
        assert data["timestamp"] == 1234567890.0
        assert data["last_attempt"] == 1234567900.0
        assert set(data["tags"]) == tags
    
    def test_from_dict_conversion(self):
        """Test creating entry from dictionary."""
        data = {
            "envelope": {
                "event_id": "test-123",
                "event_type": "test.event",
                "data": {"key": "value"},
                "source": "test-source",
                "correlation_id": "corr-456",
                "retry_count": 1,
                "headers": {"custom": "header"}
            },
            "reason": "Test failure",
            "retry_count": 2,
            "timestamp": 1234567890.0,
            "last_attempt": 1234567900.0,
            "tags": ["category", "urgent"]
        }
        
        entry = DLQEntry.from_dict(data)
        
        assert entry.envelope.event_id == "test-123"
        assert entry.envelope.event_type == "test.event"
        assert entry.envelope.data == {"key": "value"}
        assert entry.envelope.source == "test-source"
        assert entry.envelope.correlation_id == "corr-456"
        assert entry.envelope.retry_count == 1
        assert entry.envelope.headers == {"custom": "header"}
        assert entry.reason == "Test failure"
        assert entry.retry_count == 2
        assert entry.timestamp == 1234567890.0
        assert entry.last_attempt == 1234567900.0
        assert entry.tags == {"category", "urgent"}
    
    def test_roundtrip_conversion(self):
        """Test converting to dict and back preserves data."""
        envelope = Envelope(
            event_id="test-123",
            event_type="test.event",
            data={"nested": {"key": "value"}},
            source="test-source"
        )
        
        original = DLQEntry(
            envelope=envelope,
            reason="Connection timeout",
            retry_count=1,
            tags={"network", "timeout"}
        )
        
        data = original.to_dict()
        restored = DLQEntry.from_dict(data)
        
        assert restored.envelope.event_id == original.envelope.event_id
        assert restored.envelope.event_type == original.envelope.event_type
        assert restored.envelope.data == original.envelope.data
        assert restored.envelope.source == original.envelope.source
        assert restored.reason == original.reason
        assert restored.retry_count == original.retry_count
        assert restored.tags == original.tags


class TestDLQStats:
    """Test DLQ statistics functionality."""
    
    def test_default_stats(self):
        """Test default statistics values."""
        stats = DLQStats()
        
        assert stats.total_entries == 0
        assert stats.entries_by_reason == {}
        assert stats.entries_by_retry_count == {}
        assert stats.oldest_entry_age is None
        assert stats.newest_entry_age is None
        assert stats.requeue_candidates == 0
        assert stats.expired_entries == 0


@pytest.fixture
async def dlq_processor():
    """Create DLQ processor for testing."""
    processor = DLQProcessor(
        max_entries=100,
        default_ttl_seconds=3600,
        cleanup_interval_seconds=60
    )
    await processor.start()
    yield processor
    await processor.stop()


@pytest.fixture
def sample_envelope():
    """Create sample envelope for testing."""
    return Envelope(
        event_id="test-123",
        event_type="test.event",
        data={"key": "value"},
        source="test-source"
    )


class TestDLQProcessor:
    """Test DLQ processor functionality."""
    
    async def test_processor_lifecycle(self):
        """Test processor start and stop."""
        processor = DLQProcessor()
        
        # Initially stopped
        assert processor._cleanup_task is None
        
        # Start processor
        await processor.start()
        assert processor._cleanup_task is not None
        assert not processor._cleanup_task.done()
        
        # Stop processor
        await processor.stop()
        assert processor._cleanup_task is None
    
    async def test_add_entry(self, dlq_processor, sample_envelope):
        """Test adding entry to DLQ."""
        entry_id = await dlq_processor.add_entry(
            envelope=sample_envelope,
            reason="Connection failed",
            tags={"network", "timeout"}
        )
        
        assert entry_id == sample_envelope.event_id
        assert len(dlq_processor._entries) == 1
        
        entry = dlq_processor._entries[entry_id]
        assert entry.envelope == sample_envelope
        assert entry.reason == "Connection failed"
        assert entry.tags == {"network", "timeout"}
    
    async def test_add_entry_capacity_limit(self, sample_envelope):
        """Test DLQ respects capacity limit."""
        processor = DLQProcessor(max_entries=2)
        await processor.start()
        
        try:
            # Add entries up to capacity
            envelope1 = Envelope(event_id="1", event_type="test", data={})
            envelope2 = Envelope(event_id="2", event_type="test", data={})
            envelope3 = Envelope(event_id="3", event_type="test", data={})
            
            await processor.add_entry(envelope1, "reason1")
            await processor.add_entry(envelope2, "reason2")
            assert len(processor._entries) == 2
            
            # Adding third entry should evict oldest
            await processor.add_entry(envelope3, "reason3")
            assert len(processor._entries) == 2
            assert "1" not in processor._entries  # Oldest evicted
            assert "2" in processor._entries
            assert "3" in processor._entries
            
        finally:
            await processor.stop()
    
    async def test_requeue_all_entries(self, dlq_processor):
        """Test requeuing all eligible entries."""
        # Add entries with different retry counts
        envelope1 = Envelope(event_id="1", event_type="test", data={}, retry_count=1)
        envelope2 = Envelope(event_id="2", event_type="test", data={}, retry_count=2)
        envelope3 = Envelope(event_id="3", event_type="test", data={}, retry_count=3)  # Max retries
        
        await dlq_processor.add_entry(envelope1, "reason1")
        await dlq_processor.add_entry(envelope2, "reason2")
        await dlq_processor.add_entry(envelope3, "reason3")
        
        # Requeue all
        requeued = await dlq_processor.requeue()
        
        assert len(requeued) == 2  # Only first two are eligible
        assert requeued[0].event_id == "1"
        assert requeued[0].retry_count == 2  # Incremented
        assert requeued[1].event_id == "2"
        assert requeued[1].retry_count == 3  # Incremented
        
        # Entry with max retries should be removed
        assert len(dlq_processor._entries) == 2  # Third entry removed
        assert "3" not in dlq_processor._entries
    
    async def test_requeue_with_filter(self, dlq_processor):
        """Test requeuing with filter function."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "network_error")
        await dlq_processor.add_entry(envelope2, "parse_error")
        
        # Requeue only network errors
        def network_filter(entry):
            return entry.reason == "network_error"
        
        requeued = await dlq_processor.requeue(filter_fn=network_filter)
        
        assert len(requeued) == 1
        assert requeued[0].event_id == "1"
    
    async def test_requeue_with_max_count(self, dlq_processor):
        """Test requeuing with max count limit."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        envelope3 = Envelope(event_id="3", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "reason1")
        await dlq_processor.add_entry(envelope2, "reason2")
        await dlq_processor.add_entry(envelope3, "reason3")
        
        # Requeue max 2 entries
        requeued = await dlq_processor.requeue(max_count=2)
        
        assert len(requeued) == 2
    
    async def test_purge_by_age(self, dlq_processor):
        """Test purging entries by age."""
        old_envelope = Envelope(event_id="old", event_type="test", data={})
        new_envelope = Envelope(event_id="new", event_type="test", data={})
        
        # Add old entry
        await dlq_processor.add_entry(old_envelope, "old_reason")
        # Manually set old timestamp
        dlq_processor._entries["old"].timestamp = time.time() - 7200  # 2 hours ago
        
        # Add new entry
        await dlq_processor.add_entry(new_envelope, "new_reason")
        
        # Purge entries older than 1 hour
        purged_count = await dlq_processor.purge(max_age_seconds=3600)
        
        assert purged_count == 1
        assert "old" not in dlq_processor._entries
        assert "new" in dlq_processor._entries
    
    async def test_purge_with_filter(self, dlq_processor):
        """Test purging with custom filter."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "network_error")
        await dlq_processor.add_entry(envelope2, "parse_error")
        
        # Purge network errors
        def network_filter(entry):
            return entry.reason == "network_error"
        
        purged_count = await dlq_processor.purge(filter_fn=network_filter)
        
        assert purged_count == 1
        assert "1" not in dlq_processor._entries
        assert "2" in dlq_processor._entries
    
    async def test_get_stats(self, dlq_processor):
        """Test getting DLQ statistics."""
        # Add entries with various characteristics
        envelope1 = Envelope(event_id="1", event_type="test", data={}, retry_count=1)
        envelope2 = Envelope(event_id="2", event_type="test", data={}, retry_count=2)
        envelope3 = Envelope(event_id="3", event_type="test", data={}, retry_count=3)
        
        await dlq_processor.add_entry(envelope1, "network_error")
        await dlq_processor.add_entry(envelope2, "network_error")
        await dlq_processor.add_entry(envelope3, "parse_error")
        
        # Make one entry old to test expiration
        dlq_processor._entries["1"].timestamp = time.time() - 25 * 3600  # 25 hours ago
        
        stats = await dlq_processor.get_stats()
        
        assert stats.total_entries == 3
        assert stats.entries_by_reason["network_error"] == 2
        assert stats.entries_by_reason["parse_error"] == 1
        assert stats.entries_by_retry_count[1] == 1
        assert stats.entries_by_retry_count[2] == 1
        assert stats.entries_by_retry_count[3] == 1
        assert stats.requeue_candidates == 2  # retry_count < 3
        assert stats.expired_entries == 1  # One entry is > 24 hours old
        assert stats.oldest_entry_age is not None
        assert stats.newest_entry_age is not None
    
    async def test_get_entries_with_filter(self, dlq_processor):
        """Test getting entries with filter."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "network_error", tags={"urgent"})
        await dlq_processor.add_entry(envelope2, "parse_error")
        
        # Get urgent entries
        def urgent_filter(entry):
            return "urgent" in entry.tags
        
        entries = await dlq_processor.get_entries(filter_fn=urgent_filter)
        
        assert len(entries) == 1
        assert entries[0].envelope.event_id == "1"
    
    async def test_get_entries_with_limit(self, dlq_processor):
        """Test getting entries with limit."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        envelope3 = Envelope(event_id="3", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "reason1")
        await dlq_processor.add_entry(envelope2, "reason2")
        await dlq_processor.add_entry(envelope3, "reason3")
        
        entries = await dlq_processor.get_entries(limit=2)
        
        assert len(entries) == 2
    
    async def test_clear(self, dlq_processor):
        """Test clearing all entries."""
        envelope1 = Envelope(event_id="1", event_type="test", data={})
        envelope2 = Envelope(event_id="2", event_type="test", data={})
        
        await dlq_processor.add_entry(envelope1, "reason1")
        await dlq_processor.add_entry(envelope2, "reason2")
        
        assert len(dlq_processor._entries) == 2
        
        cleared_count = await dlq_processor.clear()
        
        assert cleared_count == 2
        assert len(dlq_processor._entries) == 0
    
    async def test_cleanup_expired_entries(self):
        """Test automatic cleanup of expired entries."""
        processor = DLQProcessor(
            default_ttl_seconds=1,  # 1 second TTL
            cleanup_interval_seconds=0.1  # Fast cleanup
        )
        await processor.start()
        
        try:
            envelope = Envelope(event_id="test", event_type="test", data={})
            await processor.add_entry(envelope, "test_reason")
            
            assert len(processor._entries) == 1
            
            # Wait for entry to expire and cleanup to run
            await asyncio.sleep(1.2)
            
            # Entry should be cleaned up
            assert len(processor._entries) == 0
            
        finally:
            await processor.stop()


class TestFilterUtilities:
    """Test filter utility functions."""
    
    def test_create_reason_filter(self):
        """Test reason filter creation."""
        envelope = Envelope(event_id="test", event_type="test", data={})
        entry1 = DLQEntry(envelope=envelope, reason="network_error")
        entry2 = DLQEntry(envelope=envelope, reason="parse_error")
        
        filter_fn = create_reason_filter("network_error")
        
        assert filter_fn(entry1) is True
        assert filter_fn(entry2) is False
    
    def test_create_tag_filter(self):
        """Test tag filter creation."""
        envelope = Envelope(event_id="test", event_type="test", data={})
        entry1 = DLQEntry(envelope=envelope, reason="error", tags={"urgent", "network"})
        entry2 = DLQEntry(envelope=envelope, reason="error", tags={"network"})
        
        filter_fn = create_tag_filter("urgent")
        
        assert filter_fn(entry1) is True
        assert filter_fn(entry2) is False
    
    def test_create_age_filter(self):
        """Test age filter creation."""
        envelope = Envelope(event_id="test", event_type="test", data={})
        old_entry = DLQEntry(envelope=envelope, reason="error", timestamp=time.time() - 3600)
        new_entry = DLQEntry(envelope=envelope, reason="error")
        
        filter_fn = create_age_filter(1800)  # 30 minutes
        
        assert filter_fn(old_entry) is True  # Older than 30 minutes
        assert filter_fn(new_entry) is False  # Newer than 30 minutes
    
    def test_create_retry_filter(self):
        """Test retry filter creation."""
        envelope = Envelope(event_id="test", event_type="test", data={})
        low_retry_entry = DLQEntry(envelope=envelope, reason="error", retry_count=1)
        high_retry_entry = DLQEntry(envelope=envelope, reason="error", retry_count=5)
        
        filter_fn = create_retry_filter(3)
        
        assert filter_fn(low_retry_entry) is True
        assert filter_fn(high_retry_entry) is False
