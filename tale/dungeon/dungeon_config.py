"""
Configuration for dungeon generation.

This configuration is stored in the Zone and defines how dungeons
should be generated for that zone.
"""


class DungeonConfig:
    """
    Configuration for dungeon generation.
    
    This config defines properties for procedurally generated dungeons
    attached to a zone.
    """
    
    def __init__(self, 
                 name: str = "Dungeon",
                 description: str = "A dark dungeon",
                 races: list = None,
                 items: list = None,
                 max_depth: int = 3):
        """
        Initialize a dungeon configuration.
        
        Args:
            name: Name of the dungeon
            description: Description of the dungeon
            races: List of creature races that can spawn in the dungeon
            items: List of items that can spawn in the dungeon
            max_depth: Maximum number of levels in the dungeon
        """
        self.name = name
        self.description = description
        self.races = races or ["bat", "wolf"]
        self.items = items or ["torch"]
        self.max_depth = max_depth
    
    def to_json(self) -> dict:
        """Serialize the dungeon config to JSON."""
        return {
            "name": self.name,
            "description": self.description,
            "races": self.races,
            "items": self.items,
            "max_depth": self.max_depth
        }
    
    @staticmethod
    def from_json(data: dict) -> 'DungeonConfig':
        """Deserialize a dungeon config from JSON."""
        if not data:
            return None
        return DungeonConfig(
            name=data.get("name", "Dungeon"),
            description=data.get("description", "A dark dungeon"),
            races=data.get("races", ["bat", "wolf"]),
            items=data.get("items", ["torch"]),
            max_depth=data.get("max_depth", 3)
        )
