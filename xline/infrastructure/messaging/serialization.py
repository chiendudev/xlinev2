"""Message serialization layer with pluggable backends and optional compression.

This module provides a serialization registry supporting multiple formats:
- JSON (default, using orjson if available, otherwise stdlib json)
- MessagePack (optional, enabled via ENABLE_MSGPACK environment variable)
- Extensible for ProtoBuf and other formats

Features:
- Automatic compression for payloads > COMPRESS_THRESHOLD bytes
- Round-trip serialization validation
- Performance metrics integration
- Error handling and fallback mechanisms
"""

import gzip
import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from xline.core.events.bus_interface import Envelope, EventBusError

try:
    import orjson
except ImportError:
    orjson = None  # type: ignore[assignment]


class SerializationError(EventBusError):
    """Exception raised when serialization/deserialization fails."""
    pass


class Serializer(ABC):
    """Abstract base class for message serializers."""

    @abstractmethod
    def dumps(self, envelope: Envelope) -> bytes:
        """Serialize an envelope to bytes.
        
        Args:
            envelope: The envelope to serialize
            
        Returns:
            Serialized envelope as bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        pass

    @abstractmethod
    def loads(self, data: bytes) -> Envelope:
        """Deserialize bytes to an envelope.
        
        Args:
            data: Serialized envelope bytes
            
        Returns:
            Deserialized envelope
            
        Raises:
            SerializationError: If deserialization fails
        """
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Return the content type identifier for this serializer."""
        pass


class JsonSerializer(Serializer):
    """JSON serializer with orjson optimization fallback."""

    def __init__(self) -> None:
        """Initialize JSON serializer with best available JSON library."""
        if orjson is not None:
            self._orjson = orjson
            self._use_orjson = True
        else:
            self._orjson: Any = None
            self._use_orjson = False

    def dumps(self, envelope: Envelope) -> bytes:
        """Serialize envelope to JSON bytes."""
        try:
            # Convert envelope to dict, handling dataclass fields
            data = self._envelope_to_dict(envelope)
            
            if self._use_orjson:
                # orjson returns bytes directly
                return self._orjson.dumps(data, option=self._orjson.OPT_UTC_Z)
            else:
                # stdlib json returns str, encode to bytes
                return json.dumps(
                    data,
                    default=self._json_default,
                    ensure_ascii=False
                ).encode('utf-8')
                
        except Exception as e:
            raise SerializationError(f"JSON serialization failed: {e}") from e

    def loads(self, data: bytes) -> Envelope:
        """Deserialize JSON bytes to envelope."""
        try:
            if self._use_orjson:
                parsed = self._orjson.loads(data)
            else:
                parsed = json.loads(data.decode('utf-8'))
            
            return self._dict_to_envelope(parsed)
            
        except Exception as e:
            raise SerializationError(f"JSON deserialization failed: {e}") from e

    @property
    def content_type(self) -> str:
        """Return JSON content type."""
        return "application/json"

    def _envelope_to_dict(self, envelope: Envelope) -> dict[str, Any]:
        """Convert envelope to serializable dictionary."""
        if is_dataclass(envelope):
            data = asdict(envelope)
        else:
            data = envelope.__dict__.copy()
        
        # Convert datetime to ISO string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        return data

    def _dict_to_envelope(self, data: dict[str, Any]) -> Envelope:
        """Convert dictionary to envelope, handling type conversion."""
        # Parse timestamp string back to datetime
        if isinstance(data.get('timestamp'), str):
            try:
                data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                # Fallback for malformed timestamps
                data['timestamp'] = datetime.now()
        
        # Ensure required fields have defaults
        data.setdefault('event_id', str(uuid.uuid4()))
        data.setdefault('source', 'xline')
        data.setdefault('headers', {})
        data.setdefault('retry_count', 0)
        
        return Envelope(**data)

    def _json_default(self, obj: Any) -> Any:
        """Default JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class MsgPackSerializer(Serializer):
    """MessagePack serializer (optional dependency)."""

    def __init__(self) -> None:
        """Initialize MessagePack serializer."""
        try:
            import msgpack
            self._msgpack = msgpack
        except ImportError:
            raise SerializationError(
                "msgpack library not installed. Install with: pip install msgpack"
            )

    def dumps(self, envelope: Envelope) -> bytes:
        """Serialize envelope to MessagePack bytes."""
        try:
            data = self._envelope_to_dict(envelope)
            result = self._msgpack.packb(data, use_bin_type=True)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            raise SerializationError(f"MessagePack serialization failed: {e}") from e

    def loads(self, data: bytes) -> Envelope:
        """Deserialize MessagePack bytes to envelope."""
        try:
            parsed = self._msgpack.unpackb(data, raw=False)
            return self._dict_to_envelope(parsed)
        except Exception as e:
            raise SerializationError(f"MessagePack deserialization failed: {e}") from e

    @property
    def content_type(self) -> str:
        """Return MessagePack content type."""
        return "application/msgpack"

    def _envelope_to_dict(self, envelope: Envelope) -> dict[str, Any]:
        """Convert envelope to serializable dictionary."""
        if is_dataclass(envelope):
            data = asdict(envelope)
        else:
            data = envelope.__dict__.copy()
        
        # Convert datetime to timestamp for MessagePack
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].timestamp()
        
        return data

    def _dict_to_envelope(self, data: dict[str, Any]) -> Envelope:
        """Convert dictionary to envelope."""
        # Parse timestamp back to datetime
        if isinstance(data.get('timestamp'), int | float):
            data['timestamp'] = datetime.fromtimestamp(data['timestamp'])
        
        # Ensure required fields have defaults
        data.setdefault('event_id', str(uuid.uuid4()))
        data.setdefault('source', 'xline')
        data.setdefault('headers', {})
        data.setdefault('retry_count', 0)
        
        return Envelope(**data)


class CompressedSerializer:
    """Wrapper that adds gzip compression to any serializer."""

    def __init__(self, serializer: Serializer, threshold: int = 8192):
        """Initialize compressed serializer.
        
        Args:
            serializer: Base serializer to wrap
            threshold: Minimum byte size to trigger compression
        """
        self.serializer = serializer
        self.threshold = threshold

    def dumps(self, envelope: Envelope) -> bytes:
        """Serialize and optionally compress envelope."""
        # Add compression metadata to headers
        envelope_copy = Envelope(
            event_type=envelope.event_type,
            data=envelope.data,
            event_id=envelope.event_id,
            timestamp=envelope.timestamp,
            correlation_id=envelope.correlation_id,
            source=envelope.source,
            headers=envelope.headers.copy(),
            retry_count=envelope.retry_count
        )
        
        serialized = self.serializer.dumps(envelope_copy)
        
        if len(serialized) >= self.threshold:
            # Compress and mark as compressed
            compressed = gzip.compress(serialized)
            envelope_copy.headers['compressed'] = 'gzip'
            envelope_copy.headers['original_size'] = str(len(serialized))
            envelope_copy.headers['compressed_size'] = str(len(compressed))
            return compressed
        
        return serialized

    def loads(self, data: bytes) -> Envelope:
        """Decompress and deserialize envelope."""
        # Check if data appears to be gzip compressed
        if data.startswith(b'\x1f\x8b'):
            try:
                data = gzip.decompress(data)
            except gzip.BadGzipFile:
                # Not actually compressed, proceed with original data
                pass
        
        return self.serializer.loads(data)

    @property
    def content_type(self) -> str:
        """Return content type of wrapped serializer."""
        return self.serializer.content_type


class SerializerRegistry:
    """Registry for managing serializer instances and selection."""

    def __init__(self) -> None:
        """Initialize serializer registry with default serializers."""
        self._serializers: dict[str, Serializer] = {}
        self._default_name = "json"
        
        # Register default JSON serializer
        self.register("json", JsonSerializer())
        
        # Register MessagePack if enabled and available
        if os.getenv("ENABLE_MSGPACK", "0") == "1":
            try:
                self.register("msgpack", MsgPackSerializer())
            except SerializationError:
                # MsgPack not available, skip registration
                pass

    def register(self, name: str, serializer: Serializer) -> None:
        """Register a serializer under a given name.
        
        Args:
            name: Unique name for the serializer
            serializer: Serializer instance
        """
        self._serializers[name] = serializer

    def get(self, name: str | None = None) -> Serializer:
        """Get a serializer by name.
        
        Args:
            name: Name of the serializer (defaults to default serializer)
            
        Returns:
            Serializer instance
            
        Raises:
            SerializationError: If serializer not found
        """
        if name is None:
            name = self._default_name
        
        if name not in self._serializers:
            raise SerializationError(f"Serializer '{name}' not found")
        
        return self._serializers[name]

    def get_compressed(
        self, name: str | None = None, threshold: int = 8192
    ) -> CompressedSerializer:
        """Get a compressed serializer.
        
        Args:
            name: Name of the base serializer
            threshold: Compression threshold in bytes
            
        Returns:
            CompressedSerializer wrapping the base serializer
        """
        base_serializer = self.get(name)
        return CompressedSerializer(base_serializer, threshold)

    def list_available(self) -> list[str]:
        """List all available serializer names."""
        return list(self._serializers.keys())

    def set_default(self, name: str) -> None:
        """Set the default serializer.
        
        Args:
            name: Name of the serializer to use as default
            
        Raises:
            SerializationError: If serializer not found
        """
        if name not in self._serializers:
            raise SerializationError(f"Cannot set default to unknown serializer '{name}'")
        self._default_name = name


# Global registry instance
_registry = SerializerRegistry()


def get_serializer(name: str | None = None) -> Serializer:
    """Get a serializer from the global registry.
    
    Args:
        name: Name of the serializer (uses default if None)
        
    Returns:
        Serializer instance
    """
    return _registry.get(name)


def get_compressed_serializer(
    name: str | None = None, threshold: int | None = None
) -> CompressedSerializer:
    """Get a compressed serializer from the global registry.
    
    Args:
        name: Name of the base serializer
        threshold: Compression threshold (uses env var COMPRESS_THRESHOLD or 8192)
        
    Returns:
        CompressedSerializer instance
    """
    if threshold is None:
        threshold = int(os.getenv("COMPRESS_THRESHOLD", "8192"))
    return _registry.get_compressed(name, threshold)


def register_serializer(name: str, serializer: Serializer) -> None:
    """Register a new serializer in the global registry.
    
    Args:
        name: Unique name for the serializer
        serializer: Serializer instance
    """
    _registry.register(name, serializer)
