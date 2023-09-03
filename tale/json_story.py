import tale
from tale.base import Location, Item, Living
from tale.driver import Driver
from tale.llm_ext import DynamicStory
from tale.player import Player
from tale.story import StoryBase, StoryConfig
import tale.parse_utils as parse_utils

class JsonStory(DynamicStory):
    
    def __init__(self, path: str, config: StoryConfig):
        self.config = config
        self.path = path
        locs = {}
        for zone in self.config.zones:
            zones, exits = parse_utils.load_locations(parse_utils.load_json(self.path +'zones/'+zone + '.json'))
        for name in zones.keys():
            zone = zones[name]
            for loc in zone.locations.values():
                locs[loc.name] = loc
        self._locations = locs
        self._zones = zones # type: dict(str, dict)
        self._npcs = parse_utils.load_npcs(parse_utils.load_json(self.path +'npcs/'+self.config.npcs + '.json'), self._zones)
        self._items = parse_utils.load_items(parse_utils.load_json(self.path + self.config.items + '.json'), self._zones)
        
    def init(self, driver) -> None:
        pass
        

    def welcome(self, player: Player) -> str:
        player.tell("<bright>Welcome to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        return ""  # not supported in demo

    def goodbye(self, player: Player) -> None:
        player.tell("Thanks for trying out Tale!")

    def get_location(self, zone: str, name: str) -> Location:
        """ Find a location by name in a zone."""
        return self._zones[zone].get_location(name)
    
    def find_location(self, name: str) -> Location:
        """ Find a location by name in any zone."""
        for zone in self._zones.values():
            location = zone.get_location(name)
            if location:
                return location
    
    def find_zone(self, location: str) -> str:
        """ Find a zone by location."""
        for zone in self._zones.values():
            if zone.get_location(location):
                return zone
        return None
                
    def add_location(self, location: Location, zone: str = '') -> None:
        """ Add a location to the story. 
        If zone is specified, add to that zone, otherwise add to first zone.
        """
        if zone:
            self._zones[zone].add_location(location)
            return
        for zone in self._zones:
            self._zones[zone].add_location(location)
            break

    def races_for_zone(self, zone: str) -> [str]:
        return self._zones[zone].races
   
    def items_for_zone(self, zone: str) -> [str]:
        return self._zones[zone].items

    def zone_info(self, zone_name: str = '', location: str = '') -> dict():
        if not zone_name and location:
            zone = self.find_zone(location)
        else:
            zone = self._zones[zone_name]
        return zone.info()

    def get_npc(self, npc: str) -> Living:
        return self._npcs[npc]
    
    def get_item(self, item: str) -> Item:
        return self._items[item]

    @property
    def locations(self) -> dict:
        return self._locations

    @property
    def npcs(self) -> dict:
        return self._npcs

    @property
    def items(self) -> dict:
        return self._items

