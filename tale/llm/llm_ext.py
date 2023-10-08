import json
from tale.base import Item, Living, Location
from tale.story import StoryBase

from tale.zone import Zone

class DynamicStory(StoryBase):

    def __init__(self) -> None:
        self._zones = dict() # type: dict[str, Zone]
        self._world = dict() # type: dict[str, any]
        self._world["creatures"] = dict()
        self._world["items"] = dict()

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
        return self._world["creatures"][npc]
    
    def get_item(self, item: str) -> Item:
        return self._world["items"][item]

    @property
    def world_creatures(self) -> dict:
        return self._world["creatures"]
    
    @world_creatures.setter
    def world_creatures(self, value: dict):
        self._world["creatures"] = value

    @property
    def world_items(self) -> dict:
        return self._world["items"]
    
    @world_items.setter
    def world_items(self, value: dict):
        self._world["items"] = value

    def save(self) -> None:
        """ Save the story to disk."""
        story = dict()
        story["zones"] = dict()
        story["world"] = self._world
        for zone in self._zones.values():
            story["zones"][zone.name] = zone.get_info()

        with open(self.config.name, "w") as fp:
            json.dump(story , fp) 
        

