"""Unit tests for message serialization module."""

import gzip
import json
import os
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from xline.core.events.bus_interface import Envelope
from xline.infrastructure.messaging.serialization import (
    CompressedSerializer,
    JsonSerializer,
    MsgPackSerializer,
    SerializationError,
    SerializerRegistry,
    get_compressed_serializer,
    get_serializer,
    register_serializer,
)


class TestJsonSerializer:
    """Test JSON serialization."""

    def test_serialize_deserialize_round_trip(self):
        """Test complete round-trip serialization."""
        serializer = JsonSerializer()
        
        envelope = Envelope(
            event_type="test.event",
            data={"key": "value", "number": 42},
            event_id="test-id",
            correlation_id="corr-id",
            source="test-source",
            headers={"custom": "header"},
            retry_count=3
        )
        
        # Serialize
        serialized = serializer.dumps(envelope)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = serializer.loads(serialized)
        
        # Verify all fields match
        assert deserialized.event_type == envelope.event_type
        assert deserialized.data == envelope.data
        assert deserialized.event_id == envelope.event_id
        assert deserialized.correlation_id == envelope.correlation_id
        assert deserialized.source == envelope.source
        assert deserialized.headers == envelope.headers
        assert deserialized.retry_count == envelope.retry_count

    def test_timestamp_handling(self):
        """Test datetime timestamp serialization."""
        serializer = JsonSerializer()
        
        # Create envelope with specific timestamp
        test_time = datetime.now()
        envelope = Envelope(
            event_type="test.time",
            data={},
            timestamp=test_time
        )
        
        # Serialize and deserialize
        serialized = serializer.dumps(envelope)
        deserialized = serializer.loads(serialized)
        
        # Timestamps should be approximately equal (within 1 second)
        time_diff = abs((deserialized.timestamp - test_time).total_seconds())
        assert time_diff < 1.0

    def test_content_type(self):
        """Test content type property."""
        serializer = JsonSerializer()
        assert serializer.content_type == "application/json"

    def test_defaults_added_on_deserialize(self):
        """Test that missing fields get proper defaults."""
        serializer = JsonSerializer()
        
        # Create minimal data
        minimal_data = {
            "event_type": "test.minimal",
            "data": {"test": "value"}
        }
        
        serialized = json.dumps(minimal_data).encode('utf-8')
        envelope = serializer.loads(serialized)
        
        # Check defaults are applied
        assert envelope.event_id is not None
        assert envelope.source == "xline"
        assert envelope.headers == {}
        assert envelope.retry_count == 0

    def test_serialization_error(self):
        """Test serialization error handling."""
        serializer = JsonSerializer()
        
        # Create envelope with non-serializable data
        envelope = Envelope(
            event_type="test.error",
            data={"bad": object()}  # object() is not JSON serializable
        )
        
        with pytest.raises(SerializationError):
            serializer.dumps(envelope)

    def test_deserialization_error(self):
        """Test deserialization error handling."""
        serializer = JsonSerializer()
        
        # Invalid JSON bytes
        with pytest.raises(SerializationError):
            serializer.loads(b'invalid json')


class TestMsgPackSerializer:
    """Test MessagePack serialization."""

    def test_msgpack_not_available(self):
        """Test behavior when msgpack is not installed."""
        with patch('xline.infrastructure.messaging.serialization.msgpack', None):
            with patch.dict('sys.modules', {'msgpack': None}):
                with pytest.raises(SerializationError, match="msgpack library not installed"):
                    MsgPackSerializer()

    @pytest.mark.skipif(
        os.getenv("SKIP_MSGPACK_TESTS", "0") == "1",
        reason="MessagePack tests skipped (library not available)"
    )
    def test_msgpack_round_trip(self):
        """Test MessagePack round-trip if library is available."""
        try:
            import msgpack
        except ImportError:
            pytest.skip("msgpack library not available")
        
        serializer = MsgPackSerializer()
        
        envelope = Envelope(
            event_type="test.msgpack",
            data={"binary": b"data", "text": "string"},
        )
        
        # Serialize and deserialize
        serialized = serializer.dumps(envelope)
        deserialized = serializer.loads(serialized)
        
        assert deserialized.event_type == envelope.event_type
        assert deserialized.data == envelope.data

    @pytest.mark.skipif(
        os.getenv("SKIP_MSGPACK_TESTS", "0") == "1",
        reason="MessagePack tests skipped"
    )
    def test_msgpack_content_type(self):
        """Test MessagePack content type."""
        try:
            serializer = MsgPackSerializer()
            assert serializer.content_type == "application/msgpack"
        except SerializationError:
            pytest.skip("msgpack library not available")


class TestCompressedSerializer:
    """Test compression wrapper."""

    def test_compression_above_threshold(self):
        """Test compression is applied for large payloads."""
        base_serializer = JsonSerializer()
        compressed = CompressedSerializer(base_serializer, threshold=100)
        
        # Create envelope with large data
        large_data = {"big": "x" * 200}  # Should exceed 100 byte threshold
        envelope = Envelope(event_type="test.large", data=large_data)
        
        # Serialize
        serialized = compressed.dumps(envelope)
        
        # Should be compressed (starts with gzip header)
        assert serialized.startswith(b'\x1f\x8b')
        
        # Deserialize should work
        deserialized = compressed.loads(serialized)
        assert deserialized.data == large_data

    def test_no_compression_below_threshold(self):
        """Test no compression for small payloads."""
        base_serializer = JsonSerializer()
        compressed = CompressedSerializer(base_serializer, threshold=1000)
        
        # Create envelope with small data
        small_data = {"small": "data"}
        envelope = Envelope(event_type="test.small", data=small_data)
        
        # Serialize
        serialized = compressed.dumps(envelope)
        
        # Should not be compressed
        assert not serialized.startswith(b'\x1f\x8b')
        
        # Should still deserialize correctly
        deserialized = compressed.loads(serialized)
        assert deserialized.data == small_data

    def test_decompression_detection(self):
        """Test automatic decompression detection."""
        base_serializer = JsonSerializer()
        compressed = CompressedSerializer(base_serializer, threshold=0)  # Always compress
        
        envelope = Envelope(event_type="test.compress", data={"test": "data"})
        
        # Compress manually to test detection
        base_serialized = base_serializer.dumps(envelope)
        manually_compressed = gzip.compress(base_serialized)
        
        # Should decompress automatically
        deserialized = compressed.loads(manually_compressed)
        assert deserialized.event_type == "test.compress"

    def test_content_type_passthrough(self):
        """Test content type is passed through from base serializer."""
        base_serializer = JsonSerializer()
        compressed = CompressedSerializer(base_serializer)
        
        assert compressed.content_type == "application/json"


class TestSerializerRegistry:
    """Test serializer registry."""

    def test_default_serializers(self):
        """Test default serializers are registered."""
        registry = SerializerRegistry()
        
        # JSON should always be available
        json_serializer = registry.get("json")
        assert isinstance(json_serializer, JsonSerializer)
        
        # Should have at least JSON
        available = registry.list_available()
        assert "json" in available

    def test_register_custom_serializer(self):
        """Test registering custom serializers."""
        registry = SerializerRegistry()
        
        # Register mock serializer
        mock_serializer = JsonSerializer()  # Use JSON as mock
        registry.register("custom", mock_serializer)
        
        # Should be retrievable
        retrieved = registry.get("custom")
        assert retrieved is mock_serializer
        
        # Should appear in list
        assert "custom" in registry.list_available()

    def test_default_serializer(self):
        """Test default serializer behavior."""
        registry = SerializerRegistry()
        
        # Default should be JSON
        default = registry.get()
        assert isinstance(default, JsonSerializer)

    def test_set_default(self):
        """Test changing default serializer."""
        registry = SerializerRegistry()
        
        # Register new serializer
        mock_serializer = JsonSerializer()
        registry.register("mock", mock_serializer)
        
        # Set as default
        registry.set_default("mock")
        
        # Should now be default
        default = registry.get()
        assert default is mock_serializer

    def test_set_default_unknown(self):
        """Test error when setting unknown serializer as default."""
        registry = SerializerRegistry()
        
        with pytest.raises(SerializationError, match="Cannot set default to unknown"):
            registry.set_default("nonexistent")

    def test_get_unknown_serializer(self):
        """Test error when getting unknown serializer."""
        registry = SerializerRegistry()
        
        with pytest.raises(SerializationError, match="Serializer 'unknown' not found"):
            registry.get("unknown")

    def test_compressed_serializer(self):
        """Test getting compressed serializer."""
        registry = SerializerRegistry()
        
        compressed = registry.get_compressed("json", threshold=500)
        assert isinstance(compressed, CompressedSerializer)
        assert compressed.threshold == 500

    @patch.dict(os.environ, {"ENABLE_MSGPACK": "1"})
    def test_msgpack_registration_when_enabled(self):
        """Test MessagePack is registered when enabled."""
        with patch('xline.infrastructure.messaging.serialization.MsgPackSerializer') as mock_msgpack:
            # Mock successful creation
            mock_instance = mock_msgpack.return_value
            
            registry = SerializerRegistry()
            
            # Should have attempted to register MessagePack
            mock_msgpack.assert_called_once()

    @patch.dict(os.environ, {"ENABLE_MSGPACK": "0"})
    def test_msgpack_not_registered_when_disabled(self):
        """Test MessagePack is not registered when disabled."""
        registry = SerializerRegistry()
        
        # Should only have JSON
        available = registry.list_available()
        assert available == ["json"]


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_serializer(self):
        """Test global get_serializer function."""
        serializer = get_serializer()
        assert isinstance(serializer, JsonSerializer)
        
        # Should be able to specify name
        json_serializer = get_serializer("json")
        assert isinstance(json_serializer, JsonSerializer)

    def test_get_compressed_serializer(self):
        """Test global get_compressed_serializer function."""
        compressed = get_compressed_serializer()
        assert isinstance(compressed, CompressedSerializer)

    @patch.dict(os.environ, {"COMPRESS_THRESHOLD": "2048"})
    def test_compressed_serializer_uses_env_threshold(self):
        """Test compressed serializer uses environment variable."""
        compressed = get_compressed_serializer()
        assert compressed.threshold == 2048

    def test_register_serializer_global(self):
        """Test global register_serializer function."""
        mock_serializer = JsonSerializer()
        register_serializer("test_global", mock_serializer)
        
        # Should be retrievable
        retrieved = get_serializer("test_global")
        assert retrieved is mock_serializer


class TestIntegration:
    """Integration tests for serialization components."""

    def test_full_workflow(self):
        """Test complete serialization workflow."""
        # Create envelope
        envelope = Envelope(
            event_type="integration.test",
            data={"workflow": "complete", "numbers": [1, 2, 3]},
            headers={"integration": "true"}
        )
        
        # Use compressed serializer
        serializer = get_compressed_serializer(threshold=50)
        
        # Serialize
        serialized = serializer.dumps(envelope)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = serializer.loads(serialized)
        
        # Verify integrity
        assert deserialized.event_type == envelope.event_type
        assert deserialized.data == envelope.data
        assert deserialized.headers == envelope.headers

    def test_error_propagation(self):
        """Test error propagation through layers."""
        # Bad envelope data
        envelope = Envelope(
            event_type="error.test",
            data={"bad": object()}  # Will fail JSON serialization
        )
        
        compressed = get_compressed_serializer()
        
        # Should propagate SerializationError
        with pytest.raises(SerializationError):
            compressed.dumps(envelope)

if __name__ == "__main__":
    pytest.main([__file__])
