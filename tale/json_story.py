from tale.items import generic
from tale.items.basic import Note
from tale.llm.llm_ext import DynamicStory
from tale.player import Player
from tale.story import StoryConfig
import tale.parse_utils as parse_utils
import tale.llm.llm_cache as llm_cache

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
        if world.get('catalogue', None):
            if world['catalogue']['creatures']:
                self._catalogue._creatures = world['catalogue']['creatures']
            if  world['catalogue']['items']:
                self._catalogue._items = world['catalogue']['items']
        if world.get('world', None):
            if world['world']['npcs']:
                self._world.npcs = parse_utils.load_npcs(world['world']['npcs'].values(), self.locations)
            if  world['world']['items']:
                self._world.items = parse_utils.load_items(world['world']['items'].values(), self.locations)
            if world['world']['spawners']:
                self._world.mob_spawners = parse_utils.load_mob_spawners(world['world']['spawners'], self.locations)

        llm_cache.load(parse_utils.load_json(self.path +'llm_cache.json'))

        # check if there are predefined items for the setting
        extra_items = generic.generic_items.get(self.check_setting(self.config.type), [])
        if extra_items:
            for item in extra_items:
                self._catalogue.add_item(item)

    def welcome(self, player: Player) -> str:
        player.tell("<bright>Welcome to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        return ""  # not supported in demo

    def goodbye(self, player: Player) -> None:
        player.tell("Thanks for trying out Tale!")


