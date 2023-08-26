import tale
from tale.base import Location, Item, Living
from tale.driver import Driver
from tale.player import Player
from tale.story import StoryBase, StoryConfig
import tale.parse_utils as parse_utils

class JsonStory(StoryBase):
    
    def __init__(self, path: str, config: StoryConfig):
        self.config = config
        self.path = path
        locs = {}
        for zone in self.config.zones:
            locs, exits = parse_utils.load_locations(parse_utils.load_json(self.path +'zones/'+zone + '.json'))
        self._locations = locs
        self._zones = locs
        self._npcs = parse_utils.load_npcs(parse_utils.load_json(self.path +'npcs/'+self.config.npcs + '.json'), self._locations)
        self._items = parse_utils.load_items(parse_utils.load_json(self.path + self.config.items + '.json'), self._locations)
        
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
        return self._zones[zone][name]
    
    def find_location(self, name: str) -> Location:
        """ Find a location by name in any zone."""
        for zone in self._zones:
            for loc in zone.values():
                if loc.name == name:
                    return loc
                
    def add_location(self, location: Location, zone: str = '') -> None:
        """ Add a location to the story. 
        If zone is specified, add to that zone, otherwise add to first zone.
        """
        if zone:
            self._zones[zone][location.name] = location
            return
        for zone in self._zones:
            self._zones[zone][location.name] = location
            break

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

