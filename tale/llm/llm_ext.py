import json
import typing
from tale import parse_utils
from tale.base import Item, Living, Location
from tale.coord import Coord
from tale.story import StoryBase

from tale.zone import Zone

class DynamicStory(StoryBase):

    def __init__(self) -> None:
        self._zones = dict() # type: dict[str, Zone]
        self._world = WorldInfo()

    def get_zone(self, name: str) -> Zone:
        """ Find a zone by name."""
        return self._zones[name]
    
    def add_zone(self, zone: Zone) -> bool:
        
        if zone.name in self._zones:
            return False
        self._zones[zone.name] = zone
        return True

    def get_location(self, zone: str, name: str) -> Location:
        """ Find a location by name in a zone."""
        return self._zones[zone].get_location(name)
    
    def find_location(self, name: str) -> Location:
        """ Find a location by name in any zone."""
        for zone in self._zones.values():
            location = zone.get_location(name)
            if location:
                return location
    
    def find_zone(self, location: str) -> Zone:
        """ Find a zone by location."""
        for zone in self._zones.values():
            if zone.get_location(location):
                return zone
        return None
    
    def add_location(self, location: Location, zone: str = '') -> bool:
        """ Add a location to the story. 
        If zone is specified, add to that zone, otherwise add to first zone.
        """
        self._world._locations[location.name] = location
        coord = location.world_location
        self._world._grid[coord.as_tuple()] = location
        if zone:
            return self._zones[zone].add_location(location)
        for zone in self._zones:
            return self._zones[zone].add_location(location)

    def races_for_zone(self, zone: str) -> [str]:
        return self._zones[zone].races
   
    def items_for_zone(self, zone: str) -> [str]:
        return self._zones[zone].items

    def zone_info(self, zone_name: str = '', location: str = '') -> dict():
        if not zone_name and location:
            zone = self.find_zone(location)
        else:
            zone = self._zones[zone_name]
        return zone.get_info()

    def get_npc(self, npc: str) -> Living:
        return self._world.creatures[npc]
    
    def get_item(self, item: str) -> Item:
        return self._world.items[item]
    
    @property
    def locations(self) -> dict:
        return self._world._locations
    
    @property
    def world(self) -> 'WorldInfo':
        return self._world
    

    def neighbors_for_location(self, location: Location) -> dict:
        """ Return a dict of neighboring locations for a given location."""
        neighbors = dict() # type: dict[str, Location]
        for dir in ['north', 'east', 'south', 'west', 'up', 'down']:
            neighbors[dir] = self._world._grid[Coord(location.world_location.add(parse_utils.coordinates_from_direction(dir))).as_tuple()]
        return neighbors
    
    def save(self) -> None:
        """ Save the story to disk."""
        story = dict()
        story["story"] = dict()
        story["story"]["name"] = self.config.name

        story["zones"] = dict()
        story["world"] = self._world.to_json()
        for zone in self._zones.values():
            story["zones"][zone.name] = zone.get_info()
            story["zones"][zone.name]["name"] = zone.name
            story["zones"][zone.name]["locations"] = parse_utils.save_locations(zone.locations.values())
        print(story)
        with open('world.json', "w") as fp:
            json.dump(story , fp, indent=4)

        with open('story_config.json', "w") as fp:
            json.dump(parse_utils.save_story_config(self.config) , fp, indent=4)
        

class WorldInfo():

    def __init__(self) -> None:
        self._creatures = dict()
        self._items = dict()
        self._locations = dict() # type: dict[str, Location]
        self._grid = dict() # type: dict[Coord, Location]

    @property
    def creatures(self) -> dict:
        return self._creatures
    
    @creatures.setter
    def creatures(self, value: dict):
        self._creatures = value

    @property
    def items(self) -> dict:
        return self._items
    
    @items.setter
    def items(self, value: dict):
        self._items = value

    def get_npc(self, npc: str) -> Living:
        return self._creatures[npc]
    
    def get_item(self, item: str) -> Item:
        return self._items[item]
    
    def to_json(self) -> dict:
        return dict(creatures=parse_utils.save_creatures(self._creatures.values()), 
                    items=parse_utils.save_items(self._items.values()), 
                    locations=parse_utils.save_locations(self._locations.values()))
