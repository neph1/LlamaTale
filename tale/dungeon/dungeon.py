"""
Reusable dungeon implementation for LlamaTale.

Dungeons can be attached to any story and provide procedurally generated
levels with rooms, corridors, mobs, and loot.
"""

import random
from typing import TYPE_CHECKING, Sequence, Tuple, Union

from tale.base import Door, Exit, Location
from tale.coord import Coord
from tale.dungeon.dungeon_generator import ItemPopulator, Layout, LayoutGenerator, MobPopulator
from tale.zone import Zone

if TYPE_CHECKING:
    from tale.llm.dynamic_story import DynamicStory


class Dungeon:
    """
    A self-contained dungeon that can be attached to any story.
    
    Dungeons generate procedural levels with rooms, corridors, doors, 
    keys, mobs, and items. They maintain their own zones and are 
    connected to the main world via a DungeonEntrance.
    """
    
    def __init__(self, 
                 name: str,
                 story: 'DynamicStory',
                 llm_util=None,
                 layout_generator: LayoutGenerator = None,
                 mob_populator: MobPopulator = None,
                 item_populator: ItemPopulator = None,
                 max_depth: int = 5):
        """
        Initialize a dungeon.
        
        Args:
            name: Name of the dungeon
            story: The story this dungeon belongs to
            llm_util: LLM utility for generating descriptions (optional)
            layout_generator: Generator for dungeon layouts (optional)
            mob_populator: Populator for mobs (optional)
            item_populator: Populator for items (optional)
            max_depth: Maximum depth/levels of the dungeon
        """
        self.name = name
        self.story = story
        self.llm_util = llm_util
        self.layout_generator = layout_generator or LayoutGenerator()
        self.mob_populator = mob_populator or MobPopulator()
        self.item_populator = item_populator or ItemPopulator()
        self.max_depth = max_depth
        self.current_depth = 0
        self.zones = []  # type: list[Zone]
        self._grid = dict() # type: dict[Coord, Location]
        
    def generate_level(self, zone: Zone, depth: int = 0) -> bool:
        """
        Generate a single dungeon level.
        
        Args:
            zone: The zone to populate with dungeon content
            depth: The current depth level
            
        Returns:
            True if generation was successful
        """
        if zone.locations:
            # Zone already has locations, don't regenerate
            return True
            
        self.current_depth = depth
        zone.size_z = 1
        
        # Determine starting coordinate based on depth
        start_coord = Coord(0, 0, depth)
        
        # Generate the layout
        layout = self.layout_generator.generate(start_coord=start_coord)
        
        # Prepare location descriptions
        rooms = self._prepare_locations(layout=layout, first_zone=(depth == 0))
        
        # Generate room descriptions
        self._describe_rooms(zone=zone, layout=layout, rooms=rooms)
        
        # Connect the locations
        self._connect_locations(layout=layout)
        
        # Populate with mobs
        mob_spawners = self.mob_populator.populate(zone=zone, layout=layout, story=self.story)
        for mob_spawner in mob_spawners:
            self.story.world.add_mob_spawner(mob_spawner)
        
        # Populate with items
        item_spawners = self.item_populator.populate(zone=zone, story=self.story)
        for item_spawner in item_spawners:
            self.story.world.add_item_spawner(item_spawner)
        
        # Add gold if not the first level
        if depth > 0:
            self._spawn_gold(zone=zone)
        
        self.zones.append(zone)
        return True
    
    def _prepare_locations(self, layout: Layout, first_zone: bool = False) -> list:
        """Prepare location data for description generation."""
        index = 0
        rooms = []
        for cell in list(layout.cells.values()):
            if cell.is_dungeon_entrance:
                rooms.append(f'{{"index": {index}, "name": "Entrance to dungeon"}}')
            elif cell.is_entrance:
                rooms.append(f'{{"index": {index}, "name": "Room with pathway leading up to this level."}}')
            elif cell.is_exit:
                rooms.append(f'{{"index": {index}, "name": "Room with pathway leading down"}}')
            elif cell.is_room:
                rooms.append(f'{{"index": {index}, "name": "Room"}}')
            else:
                rooms.append(f'{{"index": {index}, "name": "Hallway", "description": "A hallway"}}')
            index += 1
        return rooms
    
    def _describe_rooms(self, zone: Zone, layout: Layout, rooms: list):
        """Generate descriptions for rooms using LLM."""
        described_rooms = []
        sliced_rooms = []
        
        # Check if we have llm_util available
        if not self.llm_util:
            # Fallback to basic descriptions if no LLM available
            import json
            for i, room_json in enumerate(rooms):
                room_data = json.loads(room_json)
                room_name = room_data.get("name", f"Room {i}")
                
                # Ensure unique names
                name_counter = 1
                unique_name = room_name
                while zone.get_location(unique_name):
                    unique_name = f"{room_name}({name_counter})"
                    name_counter += 1
                
                location = Location(
                    name=unique_name,
                    descr=room_data.get("description", "A dungeon room.")
                )
                location.world_location = list(layout.cells.values())[i].coord
                zone.add_location(location=location)
                self.story.add_location(zone=zone.name, location=location, add_to_grid=False)
                self._grid[location.world_location.as_tuple()] = location
            return
        
        # Process rooms in batches of 10
        for num in range(0, len(rooms), 10):
            sliced_rooms.extend(rooms[num:num+10])
            for i in range(3):
                described_rooms_slice = self.llm_util.generate_dungeon_locations(
                    zone_info=zone.get_info(), 
                    locations=sliced_rooms, 
                    depth=self.current_depth, 
                    max_depth=self.max_depth
                )
                if described_rooms_slice.valid:
                    described_rooms.extend(described_rooms_slice.location_descriptions)
                    sliced_rooms = []
                    break
        
        if len(rooms) != len(described_rooms):
            print(f'Rooms list not same length: {len(rooms)} vs {len(described_rooms)}')
        
        # Create location objects
        for room in described_rooms:
            i = 1
            room_name = room.name
            while zone.get_location(room_name):
                # Ensure unique names
                room_name = f'{room.name}({i})'
                i += 1
            
            location = Location(name=room_name, descr=room.description)
            location.world_location = list(layout.cells.values())[room.index].coord
            zone.add_location(location=location)
            self.story.add_location(zone=zone.name, location=location, add_to_grid=False)
            self._grid[location.world_location.as_tuple()] = location
        
        return described_rooms
    
    def _connect_locations(self, layout: Layout) -> None:
        """Connect locations based on the layout."""
        connections = layout.connections
        for connection in connections:
            cell_location = self._grid.get(connection.coord.as_tuple(), None)
            parent_location = self._grid.get(connection.other.as_tuple(), None)
            
            if not cell_location or not parent_location:
                continue
                
            # Skip if already connected
            if cell_location.exits.get(parent_location.name, None):
                continue
            elif parent_location.exits.get(cell_location.name, None):
                continue
            
            # Create connection
            if connection.door:
                Door.connect(
                    cell_location, parent_location.name, '', None,
                    parent_location, cell_location.name, '', None,
                    opened=False, locked=connection.locked, key_code=connection.key_code
                )
            else:
                Exit.connect(
                    cell_location, parent_location.name, '', None,
                    parent_location, cell_location.name, '', None
                )
    
    def _spawn_gold(self, zone: Zone):
        """Spawn gold containers in the zone."""
        from tale.base import Container
        from tale.items.basic import Money
        
        max_gold = 5
        container_names = ["Box", "Pouch", "Chest", "Bag"]
        
        for i in range(max_gold):
            money = Money(name="money", value=random.randrange(5, 25) * zone.level)
            container = Container(random.choice(container_names))
            container.init_inventory([money])
            location = random.choice(list(zone.locations.values()))
            location.insert(container, None)
    
    def get_entrance_location(self) -> Location:
        """
        Get the entrance location of the dungeon.
        
        Returns:
            The first location in the first zone (entrance)
        """
        if not self.zones or not self.zones[0].locations:
            return None
        return list(self.zones[0].locations.values())[0]


class DungeonEntrance(Exit):
    """
    A special exit that leads to a dungeon.
    
    This can be added to any normal location to provide access to a dungeon.
    """

    def build_dungeon(self, story: 'DynamicStory', llm_util) -> None:
        """
        Build the dungeon if not already built.
        """

        # Create the first zone for the dungeon
        self.dungeon = Dungeon(
        name=self.short_description,
        story=story,
        llm_util=llm_util,
        layout_generator=LayoutGenerator(),
        mob_populator=MobPopulator(),
        item_populator=ItemPopulator(),
        max_depth=3
        )
                # Create the first zone for the dungeon
        zone = Zone(f"{self.name}_level_0", f"Level 0 of {self.name}")
        zone.level = 1
        zone.center = Coord(0, 0, 0)
        # Set default creatures and items for the dungeon
        zone.races = ["bat", "wolf"]
        zone.items = ["torch"]
        
        # Add zone to story
        self.dungeon.story.add_zone(zone)
        
        # Generate the first level
        self.dungeon.generate_level(zone, depth=0)
        
        # Get the entrance location and update the target
        self.target = self.dungeon.get_entrance_location()
