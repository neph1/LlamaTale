import pathlib
import random
import sys
from typing import Generator

from tale import parse_utils
from tale import lang
from tale.base import Door, Exit, Location
from tale.charbuilder import PlayerNaming
from tale.driver import Driver
from tale.dungeon.dungeon_generator import ItemPopulator, Layout, LayoutGenerator, MobPopulator
from tale.items.basic import Money
from tale.json_story import JsonStory
from tale.skills.magic import MagicType
from tale.main import run_from_cmdline
from tale.npc_defs import RoamingMob
from tale.player import Player, PlayerConnection
from tale.skills.skills import SkillType
from tale.story import *
from tale.skills.weapon_type import WeaponType
from tale.zone import Zone

class Story(JsonStory):

    driver = None  # type: Driver

    def __init__(self, path = '', layout_generator = LayoutGenerator(), mob_populator = MobPopulator(), item_populator = ItemPopulator(), config: StoryConfig = None) -> None:
        super(Story, self).__init__(path, config or parse_utils.load_story_config(parse_utils.load_json('story_config.json')))
        self.layout_generator = layout_generator
        self.mob_populator = mob_populator
        self.item_populator = item_populator
        self.max_depth = 5
        self.depth = 0
        

    def init(self, driver: Driver) -> None:
        self.llm_util = driver.llm_util
        super(Story, self).init(driver)

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=random.randint(20, 30))
        player.stats.magic_skills.set(MagicType.HEAL, 30)
        player.stats.magic_skills.set(MagicType.BOLT, 30)
        player.stats.magic_skills.set(MagicType.DRAIN, 30)
        player.stats.magic_skills.set(MagicType.REJUVENATE, 30)
        pass

    def create_account_dialog(self, playerconnection: PlayerConnection, playernaming: PlayerNaming) -> Generator:
        """
        Override to add extra dialog options to the character creation process.
        Because there's no actual player yet, you receive PlayerConnection and PlayerNaming arguments.
        Write stuff to the user via playerconnection.output(...)
        Ask questions using the yield "input", "question?"  mechanism.
        Return True to declare all is well, and False to abort the player creation process.
        """
        ranged = yield "input", ("Do you prefer ranged over close combat? (yes/no)", lang.yesno)
        if ranged:
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(20, 40))
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(20, 40))
        else:
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED, value=random.randint(20, 40))
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED, value=random.randint(20, 40))
        stealth = yield "input", ("Are you sneaky? (yes/no)", lang.yesno)
        if stealth:
            if stealth:
                playerconnection.player.stats.set(SkillType.HIDE, random.randint(30, 50))
                playerconnection.player.stats.set(SkillType.PICK_LOCK, random.randint(30, 50))
            else:
                playerconnection.player.stats.set(SkillType.HIDE, random.randint(10, 30))
                playerconnection.player.stats.set(SkillType.PICK_LOCK, random.randint(10, 30))
            playerconnection.player.stats.set(SkillType.SEARCH, random.randint(20, 40))
        
        return True

    def welcome(self, player: Player) -> str:
        """welcome text when player enters a new game"""
        player.tell("<bright>Hello, %s! Welcome to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        player.tell(self.config.context)
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        """welcome text when player enters the game after loading a saved game"""
        player.tell("<bright>Hello %s, welcome back to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        return ""

    def goodbye(self, player: Player) -> None:
        """goodbye text when player quits the game"""
        player.tell("Goodbye, %s. Please come back again soon." % player.title)
        player.tell("\n")

    def add_zone(self, zone: Zone) -> bool:
        if not super(Story, self).add_zone(zone):
            return False
        if zone.locations != {}:
            return True
        first_zone = len(self._zones.values()) == 0
        zone.size_z = 1
        layout = self.layout_generator.generate()

        rooms = self._prepare_locations(layout=layout, first_zone=first_zone)

        self._describe_rooms(zone=zone, layout=layout, rooms=rooms)
        
        self._connect_locations(layout=layout)

        mob_spawners = self.mob_populator.populate(zone=zone, layout=layout, story=self)
        for mob_spawner in mob_spawners:
            self.world.add_mob_spawner(mob_spawner)

        item_spawners = self.item_populator.populate(zone=zone, story=self)
        for item_spawner in item_spawners:
            self.world.add_item_spawner(item_spawner)

        if zone.center.z == self.max_depth:
            self._generate_boss(zone=zone)

        if not first_zone:
            self.layout_generator.spawn_gold(zone=zone)
    
        return True
    
    def _describe_rooms(self, zone: Zone, layout: Layout, rooms: list):
        described_rooms = []
        sliced_rooms = []
        for num in range(0, len(rooms), 10):
            sliced_rooms.extend(rooms[num:num+10])
            for i in range(3):
                described_rooms_slice = self.llm_util.generate_dungeon_locations(zone_info=zone.get_info(), locations=sliced_rooms, depth = self.depth, max_depth=self.max_depth) # type LocationDescriptionResponse
                if described_rooms_slice.valid:
                    described_rooms.extend(described_rooms_slice.location_descriptions)
                    sliced_rooms = []
                    break
        if len(rooms) != len(described_rooms):
            print(f'Rooms list not same length: {len(rooms)} vs {len(described_rooms)}')
        for room in described_rooms:
            i = 1
            if zone.get_location(room.name):
                # ensure unique names
                room.name = f'{room.name}({i})'
                i += 1
            location = Location(name=room.name, descr=room.description)
            location.world_location = list(layout.cells.values())[room.index].coord
            zone.add_location(location=location)
            self.add_location(zone=zone.name, location=location)
        return described_rooms

    
    def _prepare_locations(self, layout: Layout, first_zone: bool = False) -> list:
        index = 0
        rooms = []
        for cell in list(layout.cells.values()):
            if cell.is_dungeon_entrance:
                rooms.append(f'{{"index": {index}, "name": "Entrance to dungeon"}}')
            if cell.is_entrance:
                rooms.append(f'{{"index": {index}, "name": "Room with pathway leading up to this level."}}')
            elif cell.is_exit:
                rooms.append(f'{{"index": {index}, "name": "Room with pathway leading down"}}')
            elif cell.is_room:
                rooms.append(f'{{"index": {index}, "name": "Room"}}')
            else:
                rooms.append(f'{{"index": {index}, "name": "Hallway", "description": "A hallway"}}')
            index += 1
        return rooms
    
    def _connect_locations(self, layout: Layout) -> None:
        connections = layout.connections
        for connection in connections:
            cell_location = self.world._grid.get(connection.coord.as_tuple(), None) # type: Location
            parent_location = self.world._grid.get(connection.other.as_tuple(), None) # type: Location
            if cell_location.exits.get(parent_location.name, None):
                continue
            elif parent_location.exits.get(cell_location.name, None):
                continue
            if connection.door:
                Door.connect(cell_location, parent_location.name, '', None, parent_location, cell_location.name, '', None, opened=False, locked=connection.locked, key_code=connection.key_code)
            else:
                Exit.connect(cell_location, parent_location.name, '', None, parent_location, cell_location.name, '', None)

    def _generate_boss(self, zone: Zone) -> bool:
        character = self.llm_util.generate_character(keywords=['final boss']) # Characterv2
        if character:
            boss = RoamingMob(character.name, 
                            gender=character.gender, 
                            title=lang.capital(character.name), 
                            descr=character.description, 
                            short_descr=character.appearance, 
                            age=character.age,
                            personality=character.personality)
            boss.aliases = [character.name.split(' ')[0]]
            boss.stats.level = self.max_depth
            location = random.choice(list(zone.locations.values()))
            location.insert(boss, None)
            return True
        return False

if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)