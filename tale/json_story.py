import tale
from tale.base import Location, Item, Living
from tale.driver import Driver
from tale.llm.llm_ext import DynamicStory
from tale.player import Player
from tale.story import StoryBase, StoryConfig
import tale.parse_utils as parse_utils
from tale.zone import Zone

class JsonStory(DynamicStory):
    
    def __init__(self, path: str, config: StoryConfig):
        super(JsonStory, self).__init__()
        self.config = config
        self.path = path
        
    
    def init(self, driver) -> None:
        self.driver = driver
        locs = {}
        zones = []
        world = parse_utils.load_json(self.path +'world.json')
        for zone in world['zones'].values():
            zones, exits = parse_utils.load_locations(zone)
        if len(zones) < 1:
            print("No zones found in story config")
            return
        for name in zones.keys():
            zone = zones[name]
            self.add_zone(zone)
            for loc in zone.locations.values():
                self.add_location(loc, name)
        
        if world['world']['creatures']:
            self._world.creatures = parse_utils.load_npcs(world['world']['creatures'].values(), self.locations)
        if  world['world']['items']:
            self._world.items = parse_utils.load_items(world['world']['items'].values(), self.locations)
        

    def welcome(self, player: Player) -> str:
        player.tell("<bright>Welcome to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        return ""  # not supported in demo

    def goodbye(self, player: Player) -> None:
        player.tell("Thanks for trying out Tale!")


