import json
import os
import random
import shutil
from tale import parse_utils
from tale.base import Item, Living, Location
from tale.coord import Coord
from tale.llm.LivingNpc import LivingNpc
from tale.quest import Quest, QuestType
from tale.story import StoryBase

from tale.zone import Zone
import tale.llm.llm_cache as llm_cache

class DynamicStory(StoryBase):

    def __init__(self) -> None:
        self._zones = dict() # type: dict[str, Zone]
        self._world = WorldInfo()
        self._catalogue = Catalogue()

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
        return self._world.get_npc(npc)
    
    def get_item(self, item: str) -> Item:
        return self._world.get_item(item)
    
    @property
    def locations(self) -> dict:
        return self._world._locations
    
    @property
    def world(self) -> 'WorldInfo':
        return self._world
    
    @property
    def catalogue(self) -> 'Catalogue':
        return self._catalogue

    def neighbors_for_location(self, location: Location) -> dict:
        """ Return a dict of neighboring locations for a given location."""
        neighbors = dict() # type: dict[str, Location]
        for dir in ['north', 'east', 'south', 'west', 'up', 'down']:
            dir_coord = parse_utils.coordinates_from_direction(location.world_location, dir)
            coord = location.world_location.add(dir_coord)
            neighbors[dir] = self._world._grid.get(coord.as_tuple(), None)
        return neighbors
    
    def save(self, save_name: str = '') -> None:
        """ Save the story to disk."""
        story = dict()
        story["story"] = dict()
        story["story"]["name"] = self.config.name

        story["zones"] = dict()
        story["world"] = self._world.to_json()
        story["catalogue"] = self._catalogue.to_json()
        for zone in self._zones.values():
            story["zones"][zone.name] = zone.get_info()
            story["zones"][zone.name]["name"] = zone.name
            story["zones"][zone.name]["locations"] = parse_utils.save_locations(zone.locations.values())
        print(story)
        save_path = os.path.join(os.getcwd(), '../', save_name) if save_name else './'
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        with open(os.path.join(save_path, 'world.json'), "w") as fp:
            json.dump(story , fp, indent=4)

        with open(os.path.join(save_path, 'story_config.json'), "w") as fp:
            json.dump(parse_utils.save_story_config(self.config), fp, indent=4)

        with open(os.path.join(save_path, 'llm_cache.json'), "w") as fp:
            json.dump(llm_cache.json_dump(), fp, indent=4)

        if save_name:
            resource_path = os.path.join(save_path, 'resources')
            if not os.path.exists(resource_path):
                os.mkdir(resource_path)
            shutil.copy(os.path.join(os.getcwd(), 'story.py'), os.path.join(save_path, 'story.py'))
            if os.path.exists(os.path.join(os.getcwd(), 'resources')):
                shutil.copytree(os.path.join(os.getcwd(), 'resources'), resource_path, dirs_exist_ok=True)

    
    def generate_quest(self, npc: LivingNpc, type: QuestType = QuestType.GIVE) -> Quest:
        """ Generate a quest for the npc. """
        if type == QuestType.GIVE:
            target = random.choice(list(self._catalogue.get_items())) # type: dict
            return Quest(name='quest', type=type, target=target['name'], giver=npc.name)
        if type == QuestType.TALK:
            target = random.choice(list(self._world.npcs.values())) # type: LivingNpc
            return Quest(name='quest', type=type, target=target.name, giver=npc.name)
        if type == QuestType.KILL:
            target = random.choice(list(self._catalogue.get_creatures())) # type: dict
            return Quest(name='quest', type=type, target=target['name'], giver=npc.name)
        
    @property
    def get_catalogue(self) -> 'Catalogue':
        return self._catalogue
    

    def check_setting(self, story_type: str):
        if 'fantasy' in story_type:
            return 'fantasy'
        if 'modern' in story_type or 'contemporary' in story_type:
            return 'modern'
        if 'scifi' in story_type or 'sci-fi' in story_type:
            return 'scifi'
        if 'postapoc' in story_type or 'post-apoc' in story_type:
            return 'postapoc'
        return ''


class WorldInfo():

    def __init__(self) -> None:
        self._items = dict() # type: dict[str, Item]
        self._npcs  = dict() # type: dict[str, Living]
        self._locations = dict() # type: dict[str, Location]
        self._grid = dict() # type: dict[Coord, Location]

    @property
    def npcs(self) -> dict:
        return self._npcs

    @npcs.setter
    def npcs(self, value: dict):
        self._npcs = value

    def get_npc(self, npc: str) -> Living:
        return self._npcs[npc]
    
    def add_npc(self, npc: Living) -> bool:
        if npc.name in self._npcs:
            return False
        self._npcs[npc.name] = npc
        return True
    
    @property
    def items(self) -> dict:
        return self._items
    
    @items.setter
    def items(self, value: dict):
        self._items = value

    def get_item(self, item: str) -> Item:
        return self._items[item]
    
    def to_json(self) -> dict:
        return dict(
                    npcs=parse_utils.save_npcs(self._npcs.values()),
                    items=parse_utils.save_items(self._items.values()))
    
class Catalogue():
    """ A catalogue of all creatures and items in the world. Used by
    the LLM to generate random creatures and items. All are stored as
    dicts."""
    def __init__(self) -> None:
        self._items = [] # type: list[dict]
        self._creatures =[] # type: list[dict]

    def add_item(self, item: dict) -> bool:
        for world_item in self._items:
            if item['name'] == world_item['name']:
                return False
        self._items.append(item)
        return True
    
    def add_creature(self, creature: dict) -> bool:
        for world_creature in self._creatures:
            if creature['name'] == world_creature['name']:
                return False
        self._creatures.append(creature)
        return True
    
    def get_creatures(self) -> []:
        return self._creatures
    
    def get_items(self) -> []:
        return self._items
    
    def get_item(self, name: str) -> dict:
        for item in self._items:
            if item['name'] == name:
                return item
            
    def get_creature(self, name: str) -> dict:
        for creature in self._creatures:
            if creature['name'] == name:
                return creature
    
    def to_json(self) -> dict:
        return dict(items=self._items, creatures=self._creatures)
