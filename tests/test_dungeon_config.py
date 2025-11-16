"""
Tests for DungeonConfig and Zone integration.
"""

import json
from tale.coord import Coord
from tale.dungeon.dungeon_config import DungeonConfig
from tale.zone import Zone, from_json


class TestDungeonConfig:
    """Test the DungeonConfig class."""

    def test_dungeon_config_creation(self):
        """Test creating a dungeon config."""
        config = DungeonConfig(
            name="Test Dungeon",
            description="A test dungeon",
            races=["bat", "wolf"],
            items=["torch", "sword"],
            max_depth=5
        )
        
        assert config.name == "Test Dungeon"
        assert config.description == "A test dungeon"
        assert config.races == ["bat", "wolf"]
        assert config.items == ["torch", "sword"]
        assert config.max_depth == 5

    def test_dungeon_config_to_json(self):
        """Test serializing a dungeon config to JSON."""
        config = DungeonConfig(
            name="Test Dungeon",
            description="A test dungeon",
            races=["bat", "wolf"],
            items=["torch"],
            max_depth=3
        )
        
        json_data = config.to_json()
        
        assert json_data["name"] == "Test Dungeon"
        assert json_data["description"] == "A test dungeon"
        assert json_data["races"] == ["bat", "wolf"]
        assert json_data["items"] == ["torch"]
        assert json_data["max_depth"] == 3

    def test_dungeon_config_from_json(self):
        """Test deserializing a dungeon config from JSON."""
        json_data = {
            "name": "Test Dungeon",
            "description": "A test dungeon",
            "races": ["bat", "wolf"],
            "items": ["torch"],
            "max_depth": 3
        }
        
        config = DungeonConfig.from_json(json_data)
        
        assert config.name == "Test Dungeon"
        assert config.description == "A test dungeon"
        assert config.races == ["bat", "wolf"]
        assert config.items == ["torch"]
        assert config.max_depth == 3

    def test_zone_with_dungeon_config(self):
        """Test a zone with a dungeon config."""
        zone = Zone("Test Zone", "A test zone")
        zone.dungeon_config = DungeonConfig(
            name="Test Dungeon",
            description="A test dungeon",
            races=["bat"],
            items=["torch"],
            max_depth=3
        )
        
        # Verify the config is stored
        assert zone.dungeon_config is not None
        assert zone.dungeon_config.name == "Test Dungeon"

    def test_zone_serialization_with_dungeon_config(self):
        """Test serializing a zone with dungeon config."""
        zone = Zone("Test Zone", "A test zone")
        zone.center = Coord(0, 0, 0)
        zone.dungeon_config = DungeonConfig(
            name="Test Dungeon",
            description="A test dungeon",
            races=["bat"],
            items=["torch"],
            max_depth=3
        )
        
        # Serialize to JSON
        zone_data = zone.get_info()
        
        # Verify dungeon_config is in the serialized data
        assert "dungeon_config" in zone_data
        assert zone_data["dungeon_config"]["name"] == "Test Dungeon"
        assert zone_data["dungeon_config"]["races"] == ["bat"]
        assert zone_data["dungeon_config"]["max_depth"] == 3

    def test_zone_deserialization_with_dungeon_config(self):
        """Test deserializing a zone with dungeon config."""
        zone_data = {
            "name": "Test Zone",
            "description": "A test zone",
            "level": 1,
            "mood": 0,
            "items": [],
            "races": [],
            "size": 5,
            "center": [0, 0, 0],
            "lore": "",
            "dungeon_config": {
                "name": "Test Dungeon",
                "description": "A test dungeon",
                "races": ["bat", "wolf"],
                "items": ["torch"],
                "max_depth": 5
            }
        }
        
        # Deserialize from JSON
        zone = from_json(zone_data)
        
        # Verify dungeon_config was loaded
        assert zone.dungeon_config is not None
        assert zone.dungeon_config.name == "Test Dungeon"
        assert zone.dungeon_config.description == "A test dungeon"
        assert zone.dungeon_config.races == ["bat", "wolf"]
        assert zone.dungeon_config.items == ["torch"]
        assert zone.dungeon_config.max_depth == 5

    def test_zone_without_dungeon_config(self):
        """Test a zone without dungeon config."""
        zone_data = {
            "name": "Test Zone",
            "description": "A test zone",
            "level": 1,
            "mood": 0,
            "items": [],
            "races": [],
            "size": 5,
            "center": [0, 0, 0],
            "lore": ""
        }
        
        # Deserialize from JSON
        zone = from_json(zone_data)
        
        # Verify dungeon_config is None
        assert zone.dungeon_config is None
