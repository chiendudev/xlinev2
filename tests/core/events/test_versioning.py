"""
Unit tests for Event Versioning System
File: tests/unit/events/test_versioning.py

Comprehensive tests for event schema evolution and backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch

from xline.core.events.versioning import (
    SchemaVersion,
    EventMigration,
    EventVersionManager,
    VersionedEventError,
    add_field_migration,
    rename_field_migration,
    transform_field_migration,
    version_manager,
)
from xline.core.events.types import EventType


class TestSchemaVersion:
    """Test SchemaVersion class functionality"""

    def test_schema_version_creation_valid(self):
        """Test creating valid SchemaVersion instances"""
        # Test normal versions
        v1 = SchemaVersion(1, 0, 0)
        assert v1.major == 1
        assert v1.minor == 0
        assert v1.patch == 0

        v2 = SchemaVersion(2, 5, 3)
        assert v2.major == 2
        assert v2.minor == 5
        assert v2.patch == 3

    def test_schema_version_creation_invalid(self):
        """Test creating invalid SchemaVersion instances"""
        # Test negative numbers
        with pytest.raises(ValueError, match="Version numbers must be non-negative"):
            SchemaVersion(-1, 0, 0)

        with pytest.raises(ValueError, match="Version numbers must be non-negative"):
            SchemaVersion(1, -1, 0)

        with pytest.raises(ValueError, match="Version numbers must be non-negative"):
            SchemaVersion(1, 0, -1)

    def test_schema_version_string_representation(self):
        """Test string representation of SchemaVersion"""
        v1 = SchemaVersion(1, 2, 3)
        assert str(v1) == "1.2.3"

        v2 = SchemaVersion(0, 0, 1)
        assert str(v2) == "0.0.1"

    def test_schema_version_equality(self):
        """Test SchemaVersion equality comparison"""
        v1 = SchemaVersion(1, 2, 3)
        v2 = SchemaVersion(1, 2, 3)
        v3 = SchemaVersion(1, 2, 4)

        # Test equality
        assert v1 == v2
        assert v1 != v3

        # Test with non-SchemaVersion objects
        assert v1 != "1.2.3"
        assert v1 != 123
        assert v1 is not None

    def test_schema_version_comparison_operators(self):
        """Test SchemaVersion comparison operators"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_0_1 = SchemaVersion(1, 0, 1)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v2_0_0 = SchemaVersion(2, 0, 0)

        # Test less than
        assert v1_0_0 < v1_0_1
        assert v1_0_0 < v1_1_0
        assert v1_0_0 < v2_0_0
        assert v1_0_1 < v1_1_0
        assert v1_1_0 < v2_0_0

        # Test less than or equal
        assert v1_0_0 <= v1_0_0
        assert v1_0_0 <= v1_0_1
        assert v1_0_0 <= v2_0_0

        # Test greater than
        assert v1_0_1 > v1_0_0
        assert v1_1_0 > v1_0_0
        assert v2_0_0 > v1_0_0

        # Test greater than or equal
        assert v1_0_1 >= v1_0_1
        assert v1_0_1 >= v1_0_0
        assert v2_0_0 >= v1_0_0

    def test_schema_version_compatibility(self):
        """Test version compatibility checking"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)
        v2_0_0 = SchemaVersion(2, 0, 0)

        # Same major version, newer minor -> compatible
        assert v1_1_0.is_compatible_with(v1_0_0)
        assert v1_2_0.is_compatible_with(v1_0_0)
        assert v1_2_0.is_compatible_with(v1_1_0)

        # Same version -> compatible
        assert v1_0_0.is_compatible_with(v1_0_0)

        # Older version -> not compatible
        assert not v1_0_0.is_compatible_with(v1_1_0)

        # Different major version -> not compatible
        assert not v2_0_0.is_compatible_with(v1_0_0)
        assert not v1_0_0.is_compatible_with(v2_0_0)

    def test_schema_version_from_string_valid(self):
        """Test creating SchemaVersion from valid string"""
        v1 = SchemaVersion.from_string("1.2.3")
        assert v1.major == 1
        assert v1.minor == 2
        assert v1.patch == 3

        v2 = SchemaVersion.from_string("0.0.1")
        assert v2.major == 0
        assert v2.minor == 0
        assert v2.patch == 1

    def test_schema_version_from_string_invalid(self):
        """Test creating SchemaVersion from invalid string"""
        # Test invalid formats
        with pytest.raises(ValueError, match="Version must have exactly 3 parts"):
            SchemaVersion.from_string("1.2")

        with pytest.raises(ValueError, match="Version must have exactly 3 parts"):
            SchemaVersion.from_string("1.2.3.4")

        with pytest.raises(ValueError, match="Invalid version string"):
            SchemaVersion.from_string("1.a.3")

        with pytest.raises(ValueError, match="Invalid version string"):
            SchemaVersion.from_string("not.a.version")

        with pytest.raises(ValueError, match="Invalid version string"):
            SchemaVersion.from_string("")


class TestEventMigration:
    """Test EventMigration class functionality"""

    def test_event_migration_creation_valid(self):
        """Test creating valid EventMigration instances"""
        v1 = SchemaVersion(1, 0, 0)
        v2 = SchemaVersion(1, 1, 0)
        
        def dummy_migration(data):
            return data

        migration = EventMigration(
            from_version=v1,
            to_version=v2,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration,
            description="Test migration"
        )

        assert migration.from_version == v1
        assert migration.to_version == v2
        assert migration.event_type == EventType.ORDER_CREATED
        assert migration.migration_func == dummy_migration
        assert migration.description == "Test migration"

    def test_event_migration_creation_invalid(self):
        """Test creating invalid EventMigration instances"""
        v1 = SchemaVersion(1, 1, 0)
        v2 = SchemaVersion(1, 0, 0)  # Lower version

        def dummy_migration(data):
            return data

        # Test from_version >= to_version
        with pytest.raises(ValueError, match="Migration must be to a newer version"):
            EventMigration(
                from_version=v1,
                to_version=v2,
                event_type=EventType.ORDER_CREATED,
                migration_func=dummy_migration,
                description="Invalid migration"
            )

        # Test same version
        with pytest.raises(ValueError, match="Migration must be to a newer version"):
            EventMigration(
                from_version=v1,
                to_version=v1,
                event_type=EventType.ORDER_CREATED,
                migration_func=dummy_migration,
                description="Invalid migration"
            )

        # Test non-callable migration function
        with pytest.raises(ValueError, match="Migration function must be callable"):
            EventMigration(
                from_version=SchemaVersion(1, 0, 0),
                to_version=SchemaVersion(1, 1, 0),
                event_type=EventType.ORDER_CREATED,
                migration_func="not_callable",
                description="Invalid migration"
            )


class TestEventVersionManager:
    """Test EventVersionManager class functionality"""

    def setup_method(self):
        """Set up fresh version manager for each test"""
        self.manager = EventVersionManager()

    def test_initialization(self):
        """Test EventVersionManager initialization"""
        manager = EventVersionManager()
        
        # Check that all event types have default version 1.0.0
        for event_type in EventType:
            current_version = manager.get_current_version(event_type)
            assert current_version == SchemaVersion(1, 0, 0)
            
            all_versions = manager.get_all_versions(event_type)
            assert SchemaVersion(1, 0, 0) in all_versions

    def test_register_version(self):
        """Test registering new versions"""
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)

        # Register version and make it current
        self.manager.register_version(EventType.ORDER_CREATED, v1_1_0, make_current=True)
        assert self.manager.get_current_version(EventType.ORDER_CREATED) == v1_1_0
        
        all_versions = self.manager.get_all_versions(EventType.ORDER_CREATED)
        assert v1_1_0 in all_versions

        # Register version without making it current
        self.manager.register_version(EventType.ORDER_CREATED, v1_2_0, make_current=False)
        # Still old current
        assert self.manager.get_current_version(EventType.ORDER_CREATED) == v1_1_0
        
        all_versions = self.manager.get_all_versions(EventType.ORDER_CREATED)
        assert v1_2_0 in all_versions

    def test_register_version_duplicate(self):
        """Test registering duplicate version"""
        v1_1_0 = SchemaVersion(1, 1, 0)

        with patch('xline.core.events.versioning.logger') as mock_logger:
            # Register same version twice
            self.manager.register_version(EventType.ORDER_CREATED, v1_1_0)
            self.manager.register_version(EventType.ORDER_CREATED, v1_1_0)
            
            # Should log warning
            expected_msg = f"Version {v1_1_0} already registered for {EventType.ORDER_CREATED}"
            mock_logger.warning.assert_called_with(expected_msg)

    def test_register_migration(self):
        """Test registering migrations"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def dummy_migration(data):
            return data

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration,
            description="Test migration"
        )

        with patch('xline.core.events.versioning.logger') as mock_logger:
            self.manager.register_migration(migration)
            
            # Should log info
            mock_logger.info.assert_called_with(
                f"Registered migration for {EventType.ORDER_CREATED} from {v1_0_0} to {v1_1_0}"
            )

    def test_register_migration_duplicate(self):
        """Test registering duplicate migration"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def dummy_migration(data):
            return data

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration,
            description="Test migration"
        )

        with patch('xline.core.events.versioning.logger') as mock_logger:
            # Register same migration twice
            self.manager.register_migration(migration)
            self.manager.register_migration(migration)
            
            # Should log warning
            mock_logger.warning.assert_called()

    def test_is_version_supported(self):
        """Test checking if version is supported"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v2_0_0 = SchemaVersion(2, 0, 0)

        # Default version should be supported
        assert self.manager.is_version_supported(EventType.ORDER_CREATED, v1_0_0)

        # Unregistered version should not be supported
        assert not self.manager.is_version_supported(EventType.ORDER_CREATED, v1_1_0)

        # Register version and check again
        self.manager.register_version(EventType.ORDER_CREATED, v1_1_0)
        assert self.manager.is_version_supported(EventType.ORDER_CREATED, v1_1_0)

        # Different version still not supported
        assert not self.manager.is_version_supported(EventType.ORDER_CREATED, v2_0_0)

    def test_can_migrate_same_version(self):
        """Test migration check for same version"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        
        # Same version should always be migratable
        assert self.manager.can_migrate(EventType.ORDER_CREATED, v1_0_0, v1_0_0)

    def test_can_migrate_direct(self):
        """Test migration check with direct migration"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def dummy_migration(data):
            return data

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration,
            description="Test migration"
        )

        # Should not be able to migrate without registered migration
        assert not self.manager.can_migrate(EventType.ORDER_CREATED, v1_0_0, v1_1_0)

        # Register migration and check again
        self.manager.register_migration(migration)
        assert self.manager.can_migrate(EventType.ORDER_CREATED, v1_0_0, v1_1_0)

    def test_find_migration_path_empty(self):
        """Test finding migration path for same version"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        
        path = self.manager._find_migration_path(EventType.ORDER_CREATED, v1_0_0, v1_0_0)
        assert path == []

    def test_find_migration_path_direct(self):
        """Test finding direct migration path"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def dummy_migration(data):
            return data

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration,
            description="Test migration"
        )

        self.manager.register_migration(migration)
        
        path = self.manager._find_migration_path(EventType.ORDER_CREATED, v1_0_0, v1_1_0)
        assert path == [migration]

    def test_find_migration_path_multi_step(self):
        """Test finding multi-step migration path"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)

        def dummy_migration_1(data):
            return data

        def dummy_migration_2(data):
            return data

        migration1 = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration_1,
            description="Test migration 1"
        )

        migration2 = EventMigration(
            from_version=v1_1_0,
            to_version=v1_2_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=dummy_migration_2,
            description="Test migration 2"
        )

        self.manager.register_migration(migration1)
        self.manager.register_migration(migration2)
        
        path = self.manager._find_migration_path(EventType.ORDER_CREATED, v1_0_0, v1_2_0)
        assert path == [migration1, migration2]

    def test_find_migration_path_none(self):
        """Test finding migration path when none exists"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v2_0_0 = SchemaVersion(2, 0, 0)
        
        path = self.manager._find_migration_path(EventType.ORDER_CREATED, v1_0_0, v2_0_0)
        assert path is None

    def test_migrate_event_data_no_migration_needed(self):
        """Test migrating event data when no migration is needed"""
        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id',
            'source': 'test'
        }

        result = self.manager.migrate_event_data(event_data)
        assert result == event_data

    def test_migrate_event_data_missing_type(self):
        """Test migrating event data with missing type field"""
        event_data = {
            'version': '1.0.0',
            'id': 'test-id'
        }

        with pytest.raises(VersionedEventError, match="Event data missing 'type' field"):
            self.manager.migrate_event_data(event_data)

    def test_migrate_event_data_invalid_type(self):
        """Test migrating event data with invalid event type"""
        event_data = {
            'type': 'invalid.type',
            'version': '1.0.0',
            'id': 'test-id'
        }

        with pytest.raises(VersionedEventError, match="Unknown event type"):
            self.manager.migrate_event_data(event_data)

    def test_migrate_event_data_invalid_version(self):
        """Test migrating event data with invalid version"""
        event_data = {
            'type': 'order.created',
            'version': 'invalid.version',
            'id': 'test-id'
        }

        with pytest.raises(VersionedEventError, match="Invalid version"):
            self.manager.migrate_event_data(event_data)

    def test_migrate_event_data_default_version(self):
        """Test migrating event data with default version"""
        event_data = {
            'type': 'order.created',
            'id': 'test-id',
            'source': 'test'
        }

        # Should use default version 1.0.0
        result = self.manager.migrate_event_data(event_data)
        assert result == event_data

    def test_migrate_event_data_no_migration_path(self):
        """Test migrating event data with no available migration path"""
        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id'
        }

        target_version = SchemaVersion(2, 0, 0)

        with pytest.raises(VersionedEventError, match="No migration path"):
            self.manager.migrate_event_data(event_data, target_version)

    def test_migrate_event_data_successful(self):
        """Test successful event data migration"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def add_exchange_field(data):
            data['exchange'] = 'binance'
            return data

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=add_exchange_field,
            description="Add exchange field"
        )

        self.manager.register_migration(migration)

        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id',
            'source': 'test'
        }

        result = self.manager.migrate_event_data(event_data, v1_1_0)
        
        assert result['exchange'] == 'binance'
        assert result['version'] == '1.1.0'
        assert result['id'] == 'test-id'  # Original data preserved

    def test_migrate_event_data_migration_failure(self):
        """Test event data migration with failing migration function"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)

        def failing_migration(data):
            raise RuntimeError("Migration failed")

        migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=failing_migration,
            description="Failing migration"
        )

        self.manager.register_migration(migration)

        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id'
        }

        with pytest.raises(VersionedEventError, match="Migration failed"):
            self.manager.migrate_event_data(event_data, v1_1_0)

    def test_migrate_event(self):
        """Test migrating event object"""
        # Create a mock event object
        mock_event = Mock()
        mock_event.to_dict.return_value = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id'
        }

        with patch('xline.core.events.versioning.create_event_from_dict') as mock_create:
            mock_migrated_event = Mock()
            mock_create.return_value = mock_migrated_event

            result = self.manager.migrate_event(mock_event)

            # Should call to_dict on original event
            mock_event.to_dict.assert_called_once()
            
            # Should create new event from migrated data
            mock_create.assert_called_once()
            
            assert result == mock_migrated_event


class TestMigrationHelpers:
    """Test migration helper functions"""

    def test_add_field_migration(self):
        """Test add_field_migration helper"""
        migration_func = add_field_migration('new_field', 'default_value')
        
        # Test adding new field
        data = {'existing_field': 'value'}
        result = migration_func(data)
        assert result['new_field'] == 'default_value'
        assert result['existing_field'] == 'value'

        # Test with field already present
        data = {'new_field': 'existing_value', 'other_field': 'value'}
        result = migration_func(data)
        assert result['new_field'] == 'existing_value'  # Should not overwrite

    def test_rename_field_migration(self):
        """Test rename_field_migration helper"""
        migration_func = rename_field_migration('old_name', 'new_name')
        
        # Test renaming existing field
        data = {'old_name': 'value', 'other_field': 'other_value'}
        result = migration_func(data)
        assert 'old_name' not in result
        assert result['new_name'] == 'value'
        assert result['other_field'] == 'other_value'

        # Test with field not present
        data = {'other_field': 'value'}
        result = migration_func(data)
        assert 'new_name' not in result
        assert result['other_field'] == 'value'

    def test_transform_field_migration(self):
        """Test transform_field_migration helper"""
        def uppercase_transform(value):
            return value.upper()

        migration_func = transform_field_migration('field_name', uppercase_transform)
        
        # Test transforming existing field
        data = {'field_name': 'hello', 'other_field': 'world'}
        result = migration_func(data)
        assert result['field_name'] == 'HELLO'
        assert result['other_field'] == 'world'

        # Test with field not present
        data = {'other_field': 'world'}
        result = migration_func(data)
        assert 'field_name' not in result
        assert result['other_field'] == 'world'

    def test_transform_field_migration_complex(self):
        """Test transform_field_migration with complex transformation"""
        def parse_decimal(value):
            return float(str(value)) * 2

        migration_func = transform_field_migration('price', parse_decimal)
        
        data = {'price': '100.50', 'symbol': 'BTCUSDT'}
        result = migration_func(data)
        assert result['price'] == 201.0
        assert result['symbol'] == 'BTCUSDT'


class TestGlobalVersionManager:
    """Test global version manager and initialization"""

    def test_global_version_manager_exists(self):
        """Test that global version manager exists"""
        assert version_manager is not None
        assert isinstance(version_manager, EventVersionManager)

    def test_register_order_event_migrations(self):
        """Test that order event migrations are registered correctly"""
        # Check that version 1.1.0 is registered
        v1_1_0 = SchemaVersion(1, 1, 0)
        assert version_manager.is_version_supported(EventType.ORDER_CREATED, v1_1_0)
        
        # Check that migration from 1.0.0 to 1.1.0 exists
        v1_0_0 = SchemaVersion(1, 0, 0)
        assert version_manager.can_migrate(EventType.ORDER_CREATED, v1_0_0, v1_1_0)
        
        # Test the actual migration
        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id'
        }
        
        result = version_manager.migrate_event_data(event_data, v1_1_0)
        assert result['exchange'] is None  # Should add exchange field with None value
        assert result['version'] == '1.1.0'


class TestIntegrationScenarios:
    """Integration tests for complex versioning scenarios"""

    def setup_method(self):
        """Set up fresh version manager for integration tests"""
        self.manager = EventVersionManager()

    def test_complete_migration_chain(self):
        """Test a complete migration chain from v1.0.0 to v1.3.0"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)
        v1_3_0 = SchemaVersion(1, 3, 0)

        # Migration 1: Add exchange field
        migration1 = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=add_field_migration('exchange', 'binance'),
            description="Add exchange field"
        )

        # Migration 2: Rename order_id to id
        migration2 = EventMigration(
            from_version=v1_1_0,
            to_version=v1_2_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=rename_field_migration('order_id', 'order_identifier'),
            description="Rename order_id field"
        )

        # Migration 3: Transform price to float
        def price_to_float(data):
            if 'price' in data:
                data['price'] = float(data['price'])
            return data

        migration3 = EventMigration(
            from_version=v1_2_0,
            to_version=v1_3_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=price_to_float,
            description="Convert price to float"
        )

        # Register all migrations
        self.manager.register_migration(migration1)
        self.manager.register_migration(migration2)
        self.manager.register_migration(migration3)

        # Original event data
        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id',
            'order_id': 'ord-123',
            'price': '100.50',
            'symbol': 'BTCUSDT'
        }

        # Migrate to v1.3.0
        result = self.manager.migrate_event_data(event_data, v1_3_0)

        # Verify all migrations were applied
        assert result['version'] == '1.3.0'
        assert result['exchange'] == 'binance'  # Added in v1.1.0
        assert 'order_id' not in result  # Renamed in v1.2.0
        assert result['order_identifier'] == 'ord-123'  # New name
        assert result['price'] == 100.5  # Converted to float in v1.3.0
        assert result['symbol'] == 'BTCUSDT'  # Unchanged

    def test_branching_migration_paths(self):
        """Test scenario with multiple possible migration paths"""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)

        # Direct migration from 1.0.0 to 1.2.0
        direct_migration = EventMigration(
            from_version=v1_0_0,
            to_version=v1_2_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=add_field_migration('direct_field', 'direct'),
            description="Direct migration"
        )

        # Step migration 1.0.0 -> 1.1.0 -> 1.2.0
        step_migration1 = EventMigration(
            from_version=v1_0_0,
            to_version=v1_1_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=add_field_migration('step_field1', 'step1'),
            description="Step migration 1"
        )

        step_migration2 = EventMigration(
            from_version=v1_1_0,
            to_version=v1_2_0,
            event_type=EventType.ORDER_CREATED,
            migration_func=add_field_migration('step_field2', 'step2'),
            description="Step migration 2"
        )

        # Register direct migration (should be preferred)
        self.manager.register_migration(direct_migration)
        self.manager.register_migration(step_migration1)
        self.manager.register_migration(step_migration2)

        event_data = {
            'type': 'order.created',
            'version': '1.0.0',
            'id': 'test-id'
        }

        result = self.manager.migrate_event_data(event_data, v1_2_0)

        # Should use direct migration path (greedy algorithm prefers larger jumps)
        assert result['direct_field'] == 'direct'
        assert 'step_field1' not in result
        assert 'step_field2' not in result

    def test_version_compatibility_scenarios(self):
        """Test various version compatibility scenarios"""
        # Test backward compatibility within same major version
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_5_2 = SchemaVersion(1, 5, 2)
        
        assert v1_5_2.is_compatible_with(v1_0_0)
        assert not v1_0_0.is_compatible_with(v1_5_2)

        # Test incompatibility across major versions
        v2_0_0 = SchemaVersion(2, 0, 0)
        
        assert not v2_0_0.is_compatible_with(v1_0_0)
        assert not v1_0_0.is_compatible_with(v2_0_0)

    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        # Test migration with malformed event data
        malformed_data = {
            'type': 'order.created',
            'version': '1.0.0'
            # Missing required fields
        }

        def strict_migration(data):
            if 'required_field' not in data:
                raise ValueError("Required field missing")
            return data

        migration = EventMigration(
            from_version=SchemaVersion(1, 0, 0),
            to_version=SchemaVersion(1, 1, 0),
            event_type=EventType.ORDER_CREATED,
            migration_func=strict_migration,
            description="Strict migration"
        )

        self.manager.register_migration(migration)

        with pytest.raises(VersionedEventError, match="Migration failed"):
            self.manager.migrate_event_data(malformed_data, SchemaVersion(1, 1, 0))
