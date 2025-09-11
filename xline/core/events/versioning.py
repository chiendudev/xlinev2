"""
Event Versioning System for Xline Trading System
File: xline/core/events/versioning.py

Handles event schema evolution and backward compatibility.
Provides semantic versioning for events and migration support.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .types import Event, EventType, create_event_from_dict


logger = logging.getLogger(__name__)


class VersionedEventError(Exception):
    """Exception raised for versioned event operations"""
    pass


@dataclass
class SchemaVersion:
    """
    Schema version for event types.
    
    Uses semantic versioning: MAJOR.MINOR.PATCH
    - MAJOR: Breaking changes (incompatible)
    - MINOR: New features (backward compatible)
    - PATCH: Bug fixes (backward compatible)
    """
    
    major: int
    minor: int
    patch: int
    
    def __post_init__(self) -> None:
        """Validate version numbers"""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version numbers must be non-negative")
    
    def __str__(self) -> str:
        """String representation of version"""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __eq__(self, other: object) -> bool:
        """Check version equality"""
        if not isinstance(other, SchemaVersion):
            return False
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch
        )
    
    def __lt__(self, other: 'SchemaVersion') -> bool:
        """Check if this version is less than other"""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch
    
    def __le__(self, other: 'SchemaVersion') -> bool:
        """Check if this version is less than or equal to other"""
        return self < other or self == other
    
    def __gt__(self, other: 'SchemaVersion') -> bool:
        """Check if this version is greater than other"""
        return not self <= other
    
    def __ge__(self, other: 'SchemaVersion') -> bool:
        """Check if this version is greater than or equal to other"""
        return not self < other
    
    def is_compatible_with(self, other: 'SchemaVersion') -> bool:
        """
        Check if this version is backward compatible with other.
        
        Compatible if major version is same and this version >= other.
        """
        return self.major == other.major and self >= other
    
    @classmethod
    def from_string(cls, version_str: str) -> 'SchemaVersion':
        """Create SchemaVersion from string representation"""
        try:
            parts = version_str.split('.')
            if len(parts) != 3:
                raise ValueError("Version must have exactly 3 parts")
            
            major, minor, patch = map(int, parts)
            return cls(major=major, minor=minor, patch=patch)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid version string '{version_str}': {e}")


# Migration function type
MigrationFunction = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class EventMigration:
    """
    Event migration definition for schema evolution.
    
    Defines how to migrate event data from one version to another.
    """
    
    from_version: SchemaVersion
    to_version: SchemaVersion
    event_type: EventType
    migration_func: MigrationFunction
    description: str
    
    def __post_init__(self) -> None:
        """Validate migration definition"""
        if self.from_version >= self.to_version:
            raise ValueError("Migration must be to a newer version")
        
        if not callable(self.migration_func):
            raise ValueError("Migration function must be callable")


class EventVersionManager:
    """
    Manages event versioning and migrations.
    
    Provides functionality to:
    - Register event versions and migrations
    - Migrate events between versions
    - Validate event compatibility
    """
    
    def __init__(self) -> None:
        """Initialize version manager"""
        self._current_versions: dict[EventType, SchemaVersion] = {}
        self._migrations: dict[tuple[EventType, str, str], EventMigration] = {}
        self._version_history: dict[EventType, list[SchemaVersion]] = {}
        
        # Register default versions for all event types
        self._register_default_versions()
    
    def _register_default_versions(self) -> None:
        """Register default versions for all event types"""
        default_version = SchemaVersion(1, 0, 0)
        
        for event_type in EventType:
            self._current_versions[event_type] = default_version
            self._version_history[event_type] = [default_version]
    
    def register_version(
        self,
        event_type: EventType,
        version: SchemaVersion,
        make_current: bool = True
    ) -> None:
        """
        Register a new version for an event type.
        
        Args:
            event_type: Event type to register version for
            version: New version to register
            make_current: Whether to make this the current version
        """
        if event_type not in self._version_history:
            self._version_history[event_type] = []
        
        # Check if version already exists
        if version in self._version_history[event_type]:
            logger.warning(f"Version {version} already registered for {event_type}")
            return
        
        # Add to version history in sorted order
        self._version_history[event_type].append(version)
        self._version_history[event_type].sort()
        
        if make_current:
            self._current_versions[event_type] = version
        
        logger.info(f"Registered version {version} for {event_type}")
    
    def register_migration(self, migration: EventMigration) -> None:
        """
        Register a migration between event versions.
        
        Args:
            migration: Migration definition
        """
        key = (
            migration.event_type,
            str(migration.from_version),
            str(migration.to_version)
        )
        
        if key in self._migrations:
            logger.warning(f"Migration {key} already registered")
            return
        
        self._migrations[key] = migration
        logger.info(f"Registered migration for {migration.event_type} "
                   f"from {migration.from_version} to {migration.to_version}")
    
    def get_current_version(self, event_type: EventType) -> SchemaVersion:
        """Get current version for event type"""
        return self._current_versions.get(event_type, SchemaVersion(1, 0, 0))
    
    def get_all_versions(self, event_type: EventType) -> list[SchemaVersion]:
        """Get all registered versions for event type"""
        return self._version_history.get(event_type, [SchemaVersion(1, 0, 0)])
    
    def is_version_supported(
        self,
        event_type: EventType,
        version: SchemaVersion
    ) -> bool:
        """Check if a version is supported for an event type"""
        supported_versions = self.get_all_versions(event_type)
        return version in supported_versions
    
    def can_migrate(
        self,
        event_type: EventType,
        from_version: SchemaVersion,
        to_version: SchemaVersion
    ) -> bool:
        """Check if migration is possible between versions"""
        if from_version == to_version:
            return True
        
        # Check direct migration
        direct_key = (event_type, str(from_version), str(to_version))
        if direct_key in self._migrations:
            return True
        
        # Check if we can find a migration path
        return self._find_migration_path(event_type, from_version, to_version) is not None
    
    def _find_migration_path(
        self,
        event_type: EventType,
        from_version: SchemaVersion,
        to_version: SchemaVersion
    ) -> list[EventMigration] | None:
        """
        Find a migration path between versions.
        
        Uses a simple greedy approach to find migration path.
        """
        if from_version == to_version:
            return []
        
        # Get all migrations for this event type
        available_migrations = [
            migration for key, migration in self._migrations.items()
            if key[0] == event_type
        ]
        
        # Simple greedy search
        current_version = from_version
        path = []
        
        while current_version < to_version:
            # Find next migration step
            next_migration = None
            for migration in available_migrations:
                if (migration.from_version == current_version and
                    migration.to_version <= to_version):
                    if (next_migration is None or
                        migration.to_version > next_migration.to_version):
                        next_migration = migration
            
            if next_migration is None:
                return None  # No migration path found
            
            path.append(next_migration)
            current_version = next_migration.to_version
        
        return path if current_version == to_version else None
    
    def migrate_event_data(
        self,
        event_data: dict[str, Any],
        target_version: SchemaVersion | None = None
    ) -> dict[str, Any]:
        """
        Migrate event data to target version.
        
        Args:
            event_data: Event data dictionary
            target_version: Target version (current if None)
            
        Returns:
            Migrated event data
            
        Raises:
            VersionedEventError: If migration fails
        """
        # Extract event type and current version
        event_type_str = event_data.get('type')
        if not event_type_str:
            raise VersionedEventError("Event data missing 'type' field")
        
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            raise VersionedEventError(f"Unknown event type: {event_type_str}")
        
        current_version_str = event_data.get('version', '1.0.0')
        try:
            current_version = SchemaVersion.from_string(current_version_str)
        except ValueError:
            raise VersionedEventError(f"Invalid version: {current_version_str}")
        
        # Use current version if target not specified
        if target_version is None:
            target_version = self.get_current_version(event_type)
        
        # Check if migration is needed
        if current_version == target_version:
            return event_data
        
        # Find migration path
        migration_path = self._find_migration_path(
            event_type, current_version, target_version
        )
        
        if migration_path is None:
            raise VersionedEventError(
                f"No migration path from {current_version} to {target_version} "
                f"for {event_type}"
            )
        
        # Apply migrations
        migrated_data = event_data.copy()
        for migration in migration_path:
            try:
                migrated_data = migration.migration_func(migrated_data)
                migrated_data['version'] = str(migration.to_version)
                logger.debug(f"Applied migration from {migration.from_version} "
                           f"to {migration.to_version} for {event_type}")
            except Exception as e:
                raise VersionedEventError(
                    f"Migration failed from {migration.from_version} "
                    f"to {migration.to_version}: {e}"
                )
        
        return migrated_data
    
    def migrate_event(
        self,
        event: Event,
        target_version: SchemaVersion | None = None
    ) -> Event:
        """
        Migrate event object to target version.
        
        Args:
            event: Event to migrate
            target_version: Target version (current if None)
            
        Returns:
            Migrated event object
        """
        # Convert to dict, migrate, and convert back
        event_data = event.to_dict()
        migrated_data = self.migrate_event_data(event_data, target_version)
        return create_event_from_dict(migrated_data)


# Global version manager instance
version_manager = EventVersionManager()


# Example migration functions for common schema changes

def add_field_migration(field_name: str, default_value: Any) -> MigrationFunction:
    """Create a migration function that adds a new field"""
    def migration_func(data: dict[str, Any]) -> dict[str, Any]:
        if field_name not in data:
            data[field_name] = default_value
        return data
    return migration_func


def rename_field_migration(old_name: str, new_name: str) -> MigrationFunction:
    """Create a migration function that renames a field"""
    def migration_func(data: dict[str, Any]) -> dict[str, Any]:
        if old_name in data:
            data[new_name] = data.pop(old_name)
        return data
    return migration_func


def transform_field_migration(
    field_name: str,
    transform_func: Callable[[Any], Any]
) -> MigrationFunction:
    """Create a migration function that transforms a field value"""
    def migration_func(data: dict[str, Any]) -> dict[str, Any]:
        if field_name in data:
            data[field_name] = transform_func(data[field_name])
        return data
    return migration_func


# Register some example migrations for OrderEvent
def register_order_event_migrations() -> None:
    """Register example migrations for OrderEvent"""
    # Example: Add exchange field in v1.1.0
    version_manager.register_version(
        EventType.ORDER_CREATED,
        SchemaVersion(1, 1, 0)
    )
    
    migration_1_0_to_1_1 = EventMigration(
        from_version=SchemaVersion(1, 0, 0),
        to_version=SchemaVersion(1, 1, 0),
        event_type=EventType.ORDER_CREATED,
        migration_func=add_field_migration('exchange', None),
        description="Add exchange field to order events"
    )
    
    version_manager.register_migration(migration_1_0_to_1_1)


# Initialize with example migrations
register_order_event_migrations()
